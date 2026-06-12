"""
SmartCart Backend API 接口定义
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from models import (
    SearchRequest,
    SearchResult,
    UserPreference,
    UserAction,
    APIResponse,
    ParsedQuery,
    Product
)
from services.query_parser import QueryParserService
from services.preference_service import PreferenceService
from skills.taobao_search import TaobaoSearchSkill
from datetime import datetime
from pathlib import Path
import json
import uuid
import uvicorn

app = FastAPI(title="SmartCart API", version="1.0.0")

# CORS 配置（允许 React Native 调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
query_parser = QueryParserService()
preference_service = PreferenceService()
taobao_skill = TaobaoSearchSkill()

# 任务存储（简单版本，使用文件）
TASKS_DIR = Path("data/tasks")
TASKS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 搜索相关 ====================

def execute_search_task(task_id: str, request: SearchRequest, parsed_query: ParsedQuery):
    """后台执行搜索任务"""
    try:
        # 1. 执行淘宝搜索
        keyword = parsed_query.category
        products = taobao_skill.search(keyword, max_products=10)

        # 2. 创建结果
        result = SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=parsed_query,
            products=products,
            total_count=len(products),
            status="completed",
            created_at=datetime.now()
        )

        # 3. 保存结果
        result_file = TASKS_DIR / f"{task_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            data = result.dict()
            data['created_at'] = data['created_at'].isoformat()
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 4. 记录到偏好系统
        preference_service.record_search(request.user_id, request.query, parsed_query)

    except Exception as e:
        # 保存错误结果
        result = SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=parsed_query,
            products=[],
            total_count=0,
            status="failed",
            error=str(e),
            created_at=datetime.now()
        )
        result_file = TASKS_DIR / f"{task_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            data = result.dict()
            data['created_at'] = data['created_at'].isoformat()
            json.dump(data, f, ensure_ascii=False, indent=2)


@app.post("/api/search", response_model=APIResponse)
async def search_products(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    搜索商品

    流程：
    1. 解析用户查询（调用 GLM）
    2. 后台执行淘宝搜索（Open-AutoGLM）
    3. 提取商品信息
    4. 返回任务 ID
    """
    try:
        # 1. 解析查询
        parsed_query = query_parser.parse(request.query)

        # 2. 创建任务
        task_id = str(uuid.uuid4())

        # 3. 后台执行搜索
        background_tasks.add_task(execute_search_task, task_id, request, parsed_query)

        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "processing",
                "parsed_query": parsed_query.dict()
            },
            message="搜索任务已创建"
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@app.get("/api/search/{task_id}", response_model=APIResponse)
async def get_search_result(task_id: str):
    """
    获取搜索结果
    """
    try:
        result_file = TASKS_DIR / f"{task_id}.json"

        if not result_file.exists():
            return APIResponse(
                success=False,
                error="任务不存在"
            )

        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return APIResponse(
            success=True,
            data=data
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


# ==================== 偏好相关 ====================

@app.get("/api/preference/{user_id}", response_model=APIResponse)
async def get_user_preference(user_id: str):
    """
    获取用户偏好
    """
    try:
        pref = preference_service.get_preference(user_id)
        data = pref.dict()
        data['updated_at'] = data['updated_at'].isoformat()
        for brand_key in data.get('brand_preferences', {}):
            data['brand_preferences'][brand_key]['last_updated'] = \
                data['brand_preferences'][brand_key]['last_updated'].isoformat()

        return APIResponse(
            success=True,
            data=data
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@app.post("/api/preference/action", response_model=APIResponse)
async def record_user_action(action: UserAction):
    """
    记录用户行为（用于学习偏好）
    """
    try:
        if action.action_type == "view" and action.product_id:
            # 需要获取商品信息
            # TODO: 从任务结果中查找商品
            pass
        elif action.action_type == "click" and action.product_id:
            # TODO: 从任务结果中查找商品
            pass

        return APIResponse(
            success=True,
            message="行为已记录"
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
