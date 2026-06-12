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
import re
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

# task_id 由 uuid4 生成；拼接文件路径前必须校验格式，防止路径遍历
TASK_ID_PATTERN = re.compile(r'^[0-9a-fA-F-]{8,64}$')


def is_valid_task_id(task_id: str) -> bool:
    return bool(TASK_ID_PATTERN.fullmatch(task_id))


# ==================== 搜索相关 ====================

def execute_search_task(task_id: str, request: SearchRequest, parsed_query: ParsedQuery):
    """后台执行搜索任务"""
    try:
        # 1. 执行淘宝搜索
        keyword = parsed_query.category
        products = taobao_skill.search(keyword, max_products=10)

        # 2. 按用户偏好重排序（Memory → 自进化闭环）
        products = preference_service.rank_products(request.user_id, products)

        # 3. 创建结果
        result = SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=parsed_query,
            products=products,
            total_count=len(products),
            status="completed",
            is_demo=any(p.is_demo for p in products),
            created_at=datetime.now()
        )

        # 4. 保存结果
        result_file = TASKS_DIR / f"{task_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            data = result.dict()
            data['created_at'] = data['created_at'].isoformat()
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 5. 记录到偏好系统
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
        if not is_valid_task_id(task_id):
            return APIResponse(success=False, error="非法的任务 ID")

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


def find_product_in_task(task_id: str, product_id: str) -> Product | None:
    """从已保存的搜索任务结果中查找商品"""
    if not is_valid_task_id(task_id):
        return None

    result_file = TASKS_DIR / f"{task_id}.json"
    if not result_file.exists():
        return None

    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for p in data.get('products', []):
        if p.get('id') == product_id:
            return Product(**p)
    return None


@app.post("/api/preference/action", response_model=APIResponse)
async def record_user_action(action: UserAction):
    """
    记录用户行为（用于学习偏好）

    点击/查看商品时，从任务结果中回查商品信息并写入偏好系统（Memory）。
    """
    try:
        if action.action_type not in ("view", "click"):
            return APIResponse(success=False, error=f"不支持的行为类型: {action.action_type}")
        if not action.product_id or not action.task_id:
            return APIResponse(success=False, error="缺少 product_id 或 task_id")

        product = find_product_in_task(action.task_id, action.product_id)
        if product is None:
            return APIResponse(success=False, error="未找到对应商品")
        if product.is_demo:
            # 演示数据的假品牌不能写入偏好系统
            return APIResponse(success=False, error="演示数据不记录偏好")

        if action.action_type == "click":
            preference_service.record_product_click(action.user_id, product)
        else:
            preference_service.record_product_view(action.user_id, product)

        return APIResponse(
            success=True,
            message=f"已记录 {action.action_type} 行为: {product.title[:20]}"
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
