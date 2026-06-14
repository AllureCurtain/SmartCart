"""
AgentRuntime - 搜索流程的编排边界

把"解析 → 读记忆 → 调整查询 → 调工具 → 重排"串起来，
产出对用户可见的 agent_trace，并通过注册表调用技能（使 MCP/REST 同源）。
main.py 不再直接拼装这些步骤。

可用 mock 技能单测，不依赖 ADB / 淘宝 / GLM / Open-AutoGLM。
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from models import ParsedQuery, Product

logger = logging.getLogger(__name__)


@dataclass
class AgentSearchOutcome:
    products: List[Product]
    parsed_query: ParsedQuery
    agent_trace: List[str] = field(default_factory=list)
    effective_query: str = ""
    memory_context: Dict[str, Any] = field(default_factory=dict)
    is_demo: bool = False


def _budget_text(parsed: ParsedQuery) -> str:
    if parsed.price_min is not None and parsed.price_max is not None:
        return f" · ¥{int(parsed.price_min)}-{int(parsed.price_max)}"
    return ""


class AgentRuntime:
    def __init__(self, query_parser, memory_service, registry):
        self.parser = query_parser
        self.memory = memory_service
        self.registry = registry

    def run_search(
        self,
        query: str,
        user_id: str = "default",
        max_products: int = 10,
        on_progress: Optional[Callable[[str], None]] = None,
        platform: str = "taobao",
    ) -> AgentSearchOutcome:
        notify = on_progress or (lambda stage: None)
        trace: List[str] = []

        # 1. 解析需求
        parsed = self.parser.parse(query)
        trace.append(f"解析需求 → {parsed.category}{_budget_text(parsed)}")

        # 2. 读取记忆
        context = self.memory.get_context(user_id)
        if context["has_signal"]:
            hints = []
            if context["top_brand"]:
                hints.append(context["top_brand"])
            hints.extend(context.get("features", []))
            trace.append(f"读取记忆 → 偏好 {' / '.join(hints) or '价格区间'}")
        else:
            trace.append("读取记忆 → 暂无明显偏好")

        # 3. 调整搜索（记忆注入，用户意图优先）
        effective_query, injected = self.memory.build_effective_query(parsed, context, query)
        if injected:
            trace.append(f"调整搜索 → {effective_query}（加入 {' '.join(injected)}）")
        else:
            trace.append(f"搜索词 → {effective_query}")

        # 4. 调用工具（真机搜索；platform 决定调淘宝还是京东，进度由内部回调透传）
        notify("controlling_phone")
        tool_name = f"{platform}_search"
        product_dicts: List[Dict[str, Any]] = self.registry.invoke(
            tool_name, keyword=effective_query,
            max_products=max_products, on_progress=notify,
        )
        trace.append(f"调用工具 → {tool_name}（{len(product_dicts)} 个商品）")

        # 5. 重排 + 推荐理由
        notify("ranking")
        ranked_dicts: List[Dict[str, Any]] = self.registry.invoke(
            "rerank_products", products=product_dicts,
            user_id=user_id, parsed=parsed.model_dump(),
        )
        products = [Product(**p) for p in ranked_dicts]
        matched = self.memory.matched_count(products)
        is_demo = any(p.is_demo for p in products)
        trace.append(f"推荐排序 → {len(products)} 个商品，{matched} 个命中偏好")

        # 记录这次搜索到历史（记忆积累）
        try:
            self.memory.pref.record_search(user_id, query, parsed)
        except Exception:
            logger.exception("record_search failed for user %s", user_id)

        return AgentSearchOutcome(
            products=products,
            parsed_query=parsed,
            agent_trace=trace,
            effective_query=effective_query,
            memory_context=context,
            is_demo=is_demo,
        )
