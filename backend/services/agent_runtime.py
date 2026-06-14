"""
AgentRuntime - 搜索流程的编排边界

把"解析 → 读记忆 → 调整查询 → (并发)多源搜索 → 合并比价 → 重排"串起来，
产出对用户可见的 agent_trace，并通过注册表调用技能（使 MCP/REST 同源）。

多源：platform="all" 时并发 fan-out 到所有 *_search 技能（设备绑定的在
device_pool 上串行，编排层并发），合并去重后做跨平台比价标注。
单部手机下真机源仍串行；并发只发生在编排层与非设备步骤——这是诚实边界。

可用 mock 技能单测，不依赖 ADB / 淘宝 / GLM / Open-AutoGLM。
"""
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from models import ParsedQuery, Product

logger = logging.getLogger(__name__)

_SEARCH_SUFFIX = "_search"


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


def _annotate_deals(products: List[Product]) -> None:
    """跨平台比价标注（仅在 ≥2 平台时调用，保守、不臆断"同款"）：
    - 全网最低价：真实商品中价格最低者
    - {品牌}全网最低：同一品牌在 ≥2 平台出现时，标其中最便宜的
    """
    real = [p for p in products if not p.is_demo and p.price > 0]
    if not real:
        return
    cheapest = min(real, key=lambda p: p.price)
    cheapest.deal_tag = "全网最低价"

    by_brand: Dict[str, List[Product]] = defaultdict(list)
    for p in real:
        if p.brand:
            by_brand[p.brand].append(p)
    for brand, items in by_brand.items():
        if len({p.platform for p in items}) >= 2:
            best = min(items, key=lambda p: p.price)
            if best.deal_tag is None:
                best.deal_tag = f"{brand}全网最低"


class AgentRuntime:
    def __init__(self, query_parser, memory_service, registry):
        self.parser = query_parser
        self.memory = memory_service
        self.registry = registry

    def _available_platforms(self) -> List[str]:
        """从注册表里发现所有平台搜索技能（名为 {platform}_search）。"""
        return [
            s.name[: -len(_SEARCH_SUFFIX)]
            for s in self.registry.list()
            if s.name.endswith(_SEARCH_SUFFIX)
        ]

    def _resolve_targets(self, platform: str) -> List[str]:
        available = self._available_platforms()
        if platform == "all":
            return available or ["taobao"]
        if platform in available:
            return [platform]
        return available[:1] or ["taobao"]  # 请求的平台未注册时退化为已有的

    def _search_sources(
        self, targets: List[str], keyword: str, max_products: int
    ) -> List[Tuple[str, List[Dict[str, Any]], float]]:
        """并发调用各平台搜索技能；返回 [(platform, product_dicts, 耗时)]。
        单个源失败不拖垮整体（记日志、该源返回空）。子搜索不写任务进度，
        避免多线程并发写同一任务文件——设备排队由 device_pool 指标体现。
        """
        def one(p: str) -> Tuple[str, List[Dict[str, Any]], float]:
            start = time.perf_counter()
            try:
                dicts = self.registry.invoke(
                    f"{p}{_SEARCH_SUFFIX}", keyword=keyword,
                    max_products=max_products, on_progress=None,
                )
            except Exception:
                logger.exception("source %s search failed", p)
                dicts = []
            return p, dicts, time.perf_counter() - start

        if len(targets) == 1:
            return [one(targets[0])]
        with ThreadPoolExecutor(max_workers=len(targets)) as ex:
            return list(ex.map(one, targets))

    def run_search(
        self,
        query: str,
        user_id: str = "default",
        max_products: int = 10,
        on_progress: Optional[Callable[[str], None]] = None,
        platform: str = "all",
    ) -> AgentSearchOutcome:
        notify = on_progress or (lambda stage: None)
        trace: List[str] = []
        started = time.perf_counter()

        def _step(label: str, start: float) -> None:
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

        # 4. (并发) 多源搜索；设备绑定的源在 device_pool 上串行
        targets = self._resolve_targets(platform)
        notify("controlling_phone")
        results = self._search_sources(targets, effective_query, max_products)
        for p, dicts, dt in sorted(results, key=lambda r: r[0]):
            trace.append(f"调用工具 → {p}{_SEARCH_SUFFIX}（{len(dicts)} 个商品）· {_fmt_duration(dt)}")
        product_dicts = [pd for _p, pds, _dt in results for pd in pds]

        # 5. 重排 + 比价 + 推荐理由
        notify("ranking")
        t = time.perf_counter()
        ranked_dicts: List[Dict[str, Any]] = self.registry.invoke(
            "rerank_products", products=product_dicts,
            user_id=user_id, parsed=parsed.model_dump(),
        )
        products = [Product(**p) for p in ranked_dicts]
        multi = len(targets) >= 2
        if multi:
            _annotate_deals(products)
        rerank_dt = time.perf_counter() - t

        if multi:
            dist = " / ".join(
                f"{p}:{sum(1 for pp in products if pp.platform == p)}" for p in sorted(targets)
            )
            real = [p for p in products if not p.is_demo and p.price > 0]
            cheap = min(real, key=lambda p: p.price) if real else None
            cheap_txt = f"，全网最低 ¥{cheap.price:.0f}（{cheap.platform}）" if cheap else ""
            trace.append(f"综合比价 → {len(products)} 个（{dist}）{cheap_txt}")

        matched = self.memory.matched_count(products)
        is_demo = any(p.is_demo for p in products)
        trace.append(
            f"推荐排序 → {len(products)} 个商品，{matched} 个命中偏好 · {_fmt_duration(rerank_dt)}"
        )

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
