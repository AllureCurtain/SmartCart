"""
SmartCart Backend API 接口定义

编排交给 AgentRuntime，任务持久化交给 TaskStore，技能调用走 SkillRegistry，
main.py 只负责 HTTP 边界与装配。
"""
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models import (
    SearchRequest,
    SearchResult,
    UserAction,
    APIResponse,
    ParsedQuery,
)
from services.query_parser import QueryParserService
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.task_store import TaskStore, is_valid_task_id
from services.agent_runtime import AgentRuntime
from services.device_pool import device_pool
from skills.taobao_search import TaobaoSearchSkill, JDSearchSkill
from skills.catalog import build_registry
from config import ADB_PATH, RETURN_DEEPLINK, RETURN_PACKAGE, RETURN_REVERSE_PORTS
from datetime import datetime
from pathlib import Path
import os
import subprocess
import uuid
import logging
import uvicorn

from app_logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="SmartCart API", version="2.0.0")

# CORS 配置（允许 React Native 调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 装配 ====================
query_parser = QueryParserService()
preference_service = PreferenceService()
task_store = TaskStore()
memory_service = MemoryContextService(preference_service)
taobao_skill = TaobaoSearchSkill()
jd_skill = JDSearchSkill()
registry = build_registry(taobao_skill, preference_service, task_store, memory_service, jd_skill=jd_skill)
agent = AgentRuntime(query_parser, memory_service, registry)


# ==================== 搜索相关 ====================

def _ensure_reverse_tunnels(adb_exe: str) -> None:
    """重建 USB 反向隧道（best-effort，失败只记日志）。

    AutoGLM 接管手机搜索时会高频调用 adb（输入/截屏/控件操作），把 adb reverse
    建立的端口映射重置掉。切回前把 Metro/后端端口重新反向隧道一遍，确保 Expo Go
    重载时经 localhost 能连上两个服务、恢复出刚搜到的结果。
    """
    if not RETURN_REVERSE_PORTS:
        return
    for port in RETURN_REVERSE_PORTS:
        try:
            subprocess.run(
                [adb_exe, "reverse", f"tcp:{port}", f"tcp:{port}"],
                capture_output=True, timeout=10,
            )
        except Exception:
            logger.exception("重建反向隧道失败 tcp:%s（不影响切回）", port)
    logger.info("USB 反向隧道已重建：%s", RETURN_REVERSE_PORTS)


def _return_to_app() -> None:
    """搜索结束后把手机焦点切回 SmartCart（best-effort，失败只记日志不影响结果）。

    单手机架构下 AutoGLM 接管手机做搜索，结束时手机停在淘宝/京东页面。
    这里用 adb 重新打开 App 的 deep link 把焦点切回：开发模式(Expo Go)下
    重开 experience 会让 Expo Go 重连 Metro、重载，并从 task_store 恢复刚
    完成的结果——顺带消除长时间后台导致的 "Cannot connect to Expo CLI"。
    未配置 SMARTCART_RETURN_DEEPLINK 时直接跳过。
    """
    if not RETURN_DEEPLINK:
        return
    adb_name = "adb.exe" if os.name == "nt" else "adb"
    adb_exe = str(Path(ADB_PATH) / adb_name)
    # 切回前先重建隧道：搜索期被 AutoGLM 清掉的 adb reverse 必须在
    # Expo Go 重载、发起恢复请求之前就位，否则走 localhost 连不上后端。
    _ensure_reverse_tunnels(adb_exe)
    cmd = [adb_exe, "shell", "am", "start",
           "-a", "android.intent.action.VIEW", "-d", RETURN_DEEPLINK]
    if RETURN_PACKAGE:
        cmd.append(RETURN_PACKAGE)
    try:
        subprocess.run(cmd, capture_output=True, timeout=15)
        logger.info("已切回 App：%s", RETURN_DEEPLINK)
    except Exception:
        logger.exception("切回 App 失败（不影响搜索结果）")


def execute_search_task(task_id: str, request: SearchRequest):
    """后台执行搜索任务：AgentRuntime 编排解析→记忆→搜索→重排，进度落盘。

    完成（无论成败）后把手机焦点切回 App：单手机下 AutoGLM 会把手机留在
    淘宝/京东页面，不主动切回则用户看不到结果、Expo Go 也会掉线。
    """
    try:
        outcome = agent.run_search(
            request.query,
            user_id=request.user_id,
            max_products=10,
            on_progress=lambda stage: task_store.update(task_id, progress=stage),
            platform=request.platform,
        )
        task_store.write(SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=outcome.parsed_query,
            products=outcome.products,
            total_count=len(outcome.products),
            status="completed",
            progress="completed",
            is_demo=outcome.is_demo,
            agent_trace=outcome.agent_trace,
            memory_context=outcome.memory_context,
            effective_query=outcome.effective_query,
            elapsed_seconds=outcome.elapsed_seconds,
            created_at=datetime.now(),
        ))
    except Exception as e:
        logger.exception("Search task %s failed", task_id)
        task_store.write(SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=ParsedQuery(category=request.query, keywords=[request.query]),
            products=[],
            total_count=0,
            status="failed",
            progress="failed",
            error=str(e),
            created_at=datetime.now(),
        ))
    finally:
        _return_to_app()


@app.post("/api/search", response_model=APIResponse)
async def search_products(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    创建搜索任务并立即返回 task_id；解析/搜索/重排在后台执行，
    前端轮询 /api/search/{task_id} 获取 agent_trace 与结果。
    """
    try:
        task_id = str(uuid.uuid4())
        # 立即落盘占位任务，轮询端点从创建起就能查到状态
        task_store.write(SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=ParsedQuery(category=request.query, keywords=[request.query]),
            products=[],
            total_count=0,
            status="processing",
            progress="queued",
            created_at=datetime.now(),
        ))
        background_tasks.add_task(execute_search_task, task_id, request)

        return APIResponse(
            success=True,
            data={"task_id": task_id, "status": "processing"},
            message="搜索任务已创建",
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@app.get("/api/search/{task_id}", response_model=APIResponse)
async def get_search_result(task_id: str):
    """获取搜索结果（含 agent_trace / effective_query / memory_context）。"""
    if not is_valid_task_id(task_id):
        return APIResponse(success=False, error="非法的任务 ID")
    data = task_store.read_raw(task_id)
    if data is None:
        return APIResponse(success=False, error="任务不存在")
    return APIResponse(success=True, data=data)


@app.get("/api/search/latest/{user_id}", response_model=APIResponse)
async def get_latest_search_result(user_id: str):
    """
    获取最近一次已完成搜索结果。

    Expo Go 真机验证时，App 会被 AutoGLM 切后台并可能重载，运行时 state 丢失，
    此端点用于恢复。当前单用户 demo，返回全局最新 completed 任务。
    """
    data = task_store.latest_completed()
    if data is None:
        return APIResponse(success=False, error="暂无已完成搜索结果")
    return APIResponse(success=True, data=data)


# ==================== 偏好相关 ====================

@app.get("/api/preference/{user_id}", response_model=APIResponse)
async def get_user_preference(user_id: str):
    """获取用户偏好（Memory 可视化数据源）。"""
    try:
        pref = preference_service.get_preference(user_id)
        data = pref.model_dump()
        data['updated_at'] = data['updated_at'].isoformat()
        for brand_key in data.get('brand_preferences', {}):
            data['brand_preferences'][brand_key]['last_updated'] = \
                data['brand_preferences'][brand_key]['last_updated'].isoformat()
        return APIResponse(success=True, data=data)
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@app.post("/api/preference/action", response_model=APIResponse)
async def record_user_action(action: UserAction):
    """
    记录用户行为（写入 Memory）。委托给 record_product_action 技能，
    与 MCP 工具共用同一实现，避免逻辑重复。
    """
    try:
        if not action.product_id or not action.task_id:
            return APIResponse(success=False, error="缺少 product_id 或 task_id")
        result = registry.invoke(
            "record_product_action",
            user_id=action.user_id,
            task_id=action.task_id,
            product_id=action.product_id,
            action_type=action.action_type,
        )
        if not result.get("recorded"):
            return APIResponse(success=False, error=result.get("error", "记录失败"))
        return APIResponse(success=True, message="已记录行为", data=result.get("insight"))
    except Exception as e:
        return APIResponse(success=False, error=str(e))


# ==================== 诊断 / 健康检查 ====================

@app.get("/api/skills", response_model=APIResponse)
async def list_skills():
    """列出已注册技能（同时也是 MCP 暴露的工具），体现 Skill 机制。"""
    return APIResponse(success=True, data={"skills": registry.descriptions()})


@app.get("/api/system/concurrency", response_model=APIResponse)
async def concurrency_status():
    """并发与设备占用指标：体现"并发编排 + 串行设备资源池"。

    device_pool.in_use/waiting 反映多用户/多源争用同一部手机时的排队；
    扩容设备（capacity）或改用平台 API 数据源即可获得真并行。
    """
    return APIResponse(success=True, data={
        "device_pool": device_pool.stats(),
        "tasks": {"processing": task_store.count_processing()},
        "note": "单手机=容量1：真机源在池上串行排队；编排层并发，扩容设备或改用平台 API 源即真并行",
    })


@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
