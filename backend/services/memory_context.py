"""
MemoryContextService - 记忆驱动的自进化逻辑载体

承担两处"自进化"：
1. 搜索前：把记忆保守地注入有效查询（用户意图永远优先）
2. 搜索后：用记忆 + 当前意图给商品打分并给出一句推荐理由

AgentRuntime 与 skills 都复用本服务，保证行为不重复实现。
"""
from typing import Any, Dict, List, Optional, Tuple

from models import ParsedQuery, Product
from services.preference_service import PreferenceService

# 置信阈值：达到才允许把记忆注入搜索词，避免弱信号污染用户意图
_BRAND_INJECT_SCORE = 0.3
_BRAND_INJECT_COUNT = 2
_FEATURE_INJECT_WEIGHT = 0.3

# 用户表达"想广泛比较"时，不注入品牌，尊重探索意图
_BROAD_SIGNALS = ("不限品牌", "随便看看", "都看看", "对比", "比较")


class MemoryContextService:
    def __init__(self, preference_service: PreferenceService):
        self.pref = preference_service

    # ---- 记忆上下文 ----

    def get_context(self, user_id: str) -> Dict[str, Any]:
        """读取偏好，输出紧凑记忆上下文；无记忆时返回空但合法的结构。"""
        pref = self.pref.get_preference(user_id)

        brands = sorted(
            (
                {"brand": b.brand, "score": round(b.score, 3), "count": b.count}
                for b in pref.brand_preferences.values()
            ),
            key=lambda x: x["score"],
            reverse=True,
        )
        top_brand = next(
            (
                b["brand"]
                for b in brands
                if b["score"] >= _BRAND_INJECT_SCORE and b["count"] >= _BRAND_INJECT_COUNT
            ),
            None,
        )
        features = [
            f for f, w in sorted(
                pref.feature_preferences.items(), key=lambda kv: kv[1], reverse=True
            )
            if w >= _FEATURE_INJECT_WEIGHT
        ]
        price_range = None
        if pref.price_preference:
            price_range = {
                "min": pref.price_preference.min,
                "max": pref.price_preference.max,
            }

        return {
            "top_brands": brands[:3],
            "top_brand": top_brand,
            "features": features[:2],
            "price_range": price_range,
            "recent_queries": pref.search_history[-3:][::-1],
            "has_signal": bool(top_brand or features or price_range),
        }

    # ---- 搜索前：构建有效查询 ----

    def build_effective_query(
        self, parsed: ParsedQuery, context: Dict[str, Any], raw_query: str = ""
    ) -> Tuple[str, List[str]]:
        """
        返回 (effective_query, injected_terms)。
        规则：类目永远保留在最前；至多注入一个品牌 + 一个特性；
        用户表达广泛比较时不注入品牌。
        """
        terms: List[str] = [parsed.category]
        injected: List[str] = []
        broad = any(sig in raw_query for sig in _BROAD_SIGNALS)

        brand = context.get("top_brand")
        if brand and not broad and brand not in parsed.category:
            terms.append(brand)
            injected.append(brand)

        for feature in context.get("features", []):
            if feature not in parsed.category and feature not in (parsed.features or []):
                terms.append(feature)
                injected.append(feature)
                break  # 至多注入一个特性

        return " ".join(terms), injected

    # ---- 搜索后：打分 + 理由 + 排序 ----

    def rerank(
        self, products: List[Product], parsed: ParsedQuery, context: Dict[str, Any]
    ) -> List[Product]:
        """给每个商品计算 recommendation_score 与一句 recommendation_reason，降序排序。"""
        brand_scores = {b["brand"]: b["score"] for b in context.get("top_brands", [])}
        pref_range = context.get("price_range")
        features = context.get("features", [])

        scored: List[Tuple[float, Product]] = []
        for p in products:
            score = 0.0
            reasons: List[Tuple[float, str]] = []

            # 当前意图：价格落在本次预算
            if parsed.price_min is not None and parsed.price_max is not None:
                if parsed.price_min <= p.price <= parsed.price_max:
                    score += 0.4
                    reasons.append((0.4, f"价格在你本次预算 {int(parsed.price_min)}-{int(parsed.price_max)} 元内"))

            # 记忆：品牌偏好命中
            if p.brand and p.brand in brand_scores:
                bonus = brand_scores[p.brand]
                score += bonus
                reasons.append((bonus, f"命中你常看的 {p.brand} 品牌"))

            # 记忆：特性命中标题
            for feature in features:
                if feature in p.title:
                    score += 0.25
                    reasons.append((0.25, f"包含你常关注的{feature}"))
                    break

            # 记忆：价格接近历史偏好区间
            if pref_range and pref_range["min"] <= p.price <= pref_range["max"]:
                score += 0.2
                reasons.append((0.2, f"价格接近你常选的 {int(pref_range['min'])}-{int(pref_range['max'])} 元区间"))

            # 探索兜底：无任何命中时给评分/销量一点权重，并标注为探索项
            if not reasons:
                explore = 0.0
                if p.rating:
                    explore += min(p.rating / 5.0, 1.0) * 0.1
                score += explore
                reasons.append((explore, "探索项：综合评分较高"))

            p.recommendation_score = round(score, 3)
            p.recommendation_reason = max(reasons, key=lambda r: r[0])[1]
            scored.append((score, p))

        # 稳定排序：分数降序，分数相同保持原有相对顺序
        scored.sort(key=lambda sp: sp[0], reverse=True)
        return [p for _, p in scored]

    def matched_count(self, products: List[Product]) -> int:
        """统计命中记忆/意图（非探索项）的商品数，供 trace 展示。"""
        return sum(
            1 for p in products
            if p.recommendation_reason and not p.recommendation_reason.startswith("探索")
        )
