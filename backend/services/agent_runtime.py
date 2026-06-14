"""
AgentRuntime - 搜索流程的编排边界

把"解析 → 读记忆 → 调整查询 → 调工具 → 重排"串起来，
产出对用户可见的 agent_trace，并通过注册表调用技能（使 MCP/REST 同源）。
main.py 不再直接拼装这些步骤。

可用 mock 技能单测，不依赖 ADB / 淘宝 / GLM / Open-AutoGLM。
"""
import logging
import time
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
    elapsed_seconds: float = 0.0  # 端到端总耗时，前端展示在 AGENT TRACE 头部


def _budget_text(parsed: ParsedQuery) -> str:
    if parsed.price_min is not None and parsed.price_max is not None:
        return f" · ¥{int(parsed.price_min)}-{int(parsed.price_max)}"
    return ""


def _fmt_duration(seconds: float) -> str:
    """毫秒级显示瞬时步骤，秒级显示耗时步骤（如 AutoGLM 真机操作）。"""
    return f"{seconds * 1000:.0f}ms" if seconds < 1 else f"{seconds:.1f}s"


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
        started = time.perf_counter()

        def _step(label: str, start: float) -> None:
            """给某步追加耗时后缀，让轨迹显示每步真实开销。"""
            trace.append(f"{label} · {_fmt_duration(time.perf_counter() - start)}")

        # 1. 解析需求
        t = time.perf_counter()
        parsed = self.parser.parse(query)
        _step(f"解析需求 → {parsed.category}{_budget_text(parsed)}", t)

        # 2. 读取记忆
        t = time.perf_counter()
        context = self.memory.get_context(user_id)
        if context["has_signal"]:
            hints = []
            if context["top_brand"]:
                hints.append(context["top_brand"])
            hints.extend(context.get("features", []))
            _step(f"读取记忆 → 偏好 {' / '.join(hints) or '价格区间'}", t)
        else:
            _step("读取记忆 → 暂无明显偏好", t)

        # 3. 调整搜索（记忆注入，用户意图优先）
        t = time.perf_counter()
        effective_query, injected = self.memory.build_effective_query(parsed, context, query)
        if injected:
            _step(f"调整搜索 → {effective_query}（加入 {' '.join(injected)}）", t)
        else:
            _step(f"搜索词 → {effective_query}", t)

        # 4. 调用工具（真机搜索；platform 决定调淘宝还是京东，进度由内部回调透传）
        notify("controlling_phone")
        tool_name = f"{platform}_search"
        t = time.perf_counter()
        product_dicts: List[Dict[str, Any]] = self.registry.invoke(
            tool_name, keyword=effective_query,
            max_products=max_products, on_progress=notify,
        )
        _step(f"调用工具 → {tool_name}（{len(product_dicts)} 个商品）", t)

        # 5. 重排 + 推荐理由
        notify("ranking")
        t = time.perf_counter()
        ranked_dicts: List[Dict[str, Any]] = self.registry.invoke(
            "rerank_products", products=product_dicts,
            user_id=user_id, parsed=parsed.model_dump(),
        )
        products = [Product(**p) for p in ranked_dicts]
        matched = self.memory.matched_count(products)
        is_demo = any(p.is_demo for p in products)
        _step(f"推荐排序 → {len(products)} 个商品，{matched} 个命中偏好", t)

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
            elapsed_seconds=round(time.perf_counter() - started, 2),
        )
