"""
技能目录 - 把现有能力包装为注册式 Skill，并提供 build_registry 工厂。

适配器只做"委托"，不重写已验证的真机搜索链路。
AgentRuntime 与 MCP Server 都通过 build_registry() 得到同一套技能。
"""
from typing import Any, Dict, List, Optional

from models import ParsedQuery, Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.task_store import TaskStore
from skills.base import Skill
from skills.taobao_search import PhoneSearchSkill


class PlatformSearchTool(Skill):
    """把某个平台的真机搜索技能包装成注册式 Skill（淘宝/京东共用同一个适配器）。"""

    def __init__(self, name: str, description: str, search_skill: PhoneSearchSkill):
        self.name = name
        self.description = description
        self.parameters = {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "商品搜索关键词"},
                "max_products": {"type": "integer", "description": "最多返回商品数", "default": 10},
            },
            "required": ["keyword"],
        }
        self._skill = search_skill

    def run(self, keyword: str, max_products: int = 10, on_progress=None, **_: Any) -> List[Dict[str, Any]]:
        products = self._skill.search(keyword, max_products=max_products, on_progress=on_progress)
        return [p.model_dump() for p in products]


class PreferenceInsightTool(Skill):
    name = "get_preference_insight"
    description = "读取用户记忆，返回紧凑偏好上下文（品牌/价格/特性/近期搜索）"
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "用户标识", "default": "default"},
        },
    }

    def __init__(self, memory_service: MemoryContextService):
        self._memory = memory_service

    def run(self, user_id: str = "default", **_: Any) -> Dict[str, Any]:
        return self._memory.get_context(user_id)


class RecordActionTool(Skill):
    name = "record_product_action"
    description = "记录用户对商品的查看/点击行为，写入偏好记忆，返回更新后的偏好上下文"
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "default": "default"},
            "task_id": {"type": "string", "description": "商品所属搜索任务"},
            "product_id": {"type": "string"},
            "action_type": {"type": "string", "enum": ["view", "click"]},
        },
        "required": ["task_id", "product_id", "action_type"],
    }

    def __init__(
        self,
        preference_service: PreferenceService,
        task_store: TaskStore,
        memory_service: MemoryContextService,
    ):
        self._pref = preference_service
        self._tasks = task_store
        self._memory = memory_service

    def run(
        self,
        task_id: str,
        product_id: str,
        action_type: str,
        user_id: str = "default",
        **_: Any,
    ) -> Dict[str, Any]:
        if action_type not in ("view", "click"):
            return {"recorded": False, "error": f"不支持的行为类型: {action_type}"}
        product = self._tasks.find_product(task_id, product_id)
        if product is None:
            return {"recorded": False, "error": "未找到对应商品"}
        if product.is_demo:
            return {"recorded": False, "error": "演示数据不记录偏好"}

        if action_type == "click":
            self._pref.record_product_click(user_id, product)
        else:
            self._pref.record_product_view(user_id, product)
        return {"recorded": True, "insight": self._memory.get_context(user_id)}


class RerankProductsTool(Skill):
    name = "rerank_products"
    description = "用记忆与当前需求给商品打分并生成推荐理由，返回重排后的商品"
    parameters = {
        "type": "object",
        "properties": {
            "products": {"type": "array", "items": {"type": "object"}, "description": "商品字典列表"},
            "user_id": {"type": "string", "default": "default"},
            "parsed": {"type": "object", "description": "解析后的需求（category/price_min/price_max/features）"},
        },
        "required": ["products"],
    }

    def __init__(self, memory_service: MemoryContextService):
        self._memory = memory_service

    def run(
        self,
        products: List[Dict[str, Any]],
        user_id: str = "default",
        parsed: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> List[Dict[str, Any]]:
        product_objs = [Product(**p) for p in products]
        parsed_query = ParsedQuery(**parsed) if parsed else ParsedQuery(category="", keywords=[])
        context = self._memory.get_context(user_id)
        ranked = self._memory.rerank(product_objs, parsed_query, context)
        return [p.model_dump() for p in ranked]


_TAOBAO_DESC = "通过 Open-AutoGLM 控制真机在淘宝搜索商品，截屏后用 GLM-4V 提取结构化商品"
_JD_DESC = "通过 Open-AutoGLM 控制真机在京东搜索商品，截屏后用 GLM-4V 提取结构化商品"


def build_registry(
    taobao_skill: PhoneSearchSkill,
    preference_service: PreferenceService,
    task_store: TaskStore,
    memory_service: MemoryContextService,
    jd_skill: Optional[PhoneSearchSkill] = None,
):
    """组装并返回包含全部技能的注册表。

    jd_skill 可选：传入即额外暴露 jd_search，使注册表 / MCP 拥有淘宝+京东两个数据源。
    """
    from skills.registry import SkillRegistry

    registry = SkillRegistry()
    registry.register(PlatformSearchTool("taobao_search", _TAOBAO_DESC, taobao_skill))
    if jd_skill is not None:
        registry.register(PlatformSearchTool("jd_search", _JD_DESC, jd_skill))
    registry.register(PreferenceInsightTool(memory_service))
    registry.register(RecordActionTool(preference_service, task_store, memory_service))
    registry.register(RerankProductsTool(memory_service))
    return registry
