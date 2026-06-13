"""
MemoryContextService 单测：记忆上下文、保守查询注入、打分排序与理由。
"""
from datetime import datetime

from models import BrandPreference, ParsedQuery, PricePreference, Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService


def _svc(tmp_path):
    return MemoryContextService(PreferenceService(storage_path=str(tmp_path)))


def _seed_brand(pref_service, user_id, brand, score, count):
    pref = pref_service.get_preference(user_id)
    pref.brand_preferences[brand] = BrandPreference(
        brand=brand, score=score, count=count, last_updated=datetime.now()
    )
    pref_service.save_preference(pref)


def _product(pid, title, price, brand=None, rating=None):
    return Product(id=pid, title=title, price=price, brand=brand, rating=rating, platform="taobao")


def _parsed(category="蓝牙耳机", pmin=None, pmax=None, features=None):
    return ParsedQuery(category=category, keywords=[category],
                       price_min=pmin, price_max=pmax, features=features or [])


class TestContext:
    def test_empty_memory_is_valid(self, tmp_path):
        ctx = _svc(tmp_path).get_context("new")
        assert ctx["has_signal"] is False
        assert ctx["top_brand"] is None
        assert ctx["top_brands"] == []

    def test_confident_brand_surfaces(self, tmp_path):
        svc = _svc(tmp_path)
        _seed_brand(svc.pref, "u", "华为", 0.5, 3)
        ctx = svc.get_context("u")
        assert ctx["top_brand"] == "华为"
        assert ctx["has_signal"] is True

    def test_weak_brand_not_injected(self, tmp_path):
        svc = _svc(tmp_path)
        _seed_brand(svc.pref, "u", "杂牌", 0.1, 1)  # 分数与次数都不够
        assert svc.get_context("u")["top_brand"] is None


class TestEffectiveQuery:
    def test_injects_confident_brand(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brand": "华为", "features": []}
        eq, injected = svc.build_effective_query(_parsed(), ctx)
        assert eq == "蓝牙耳机 华为"
        assert injected == ["华为"]

    def test_user_broad_intent_blocks_injection(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brand": "华为", "features": []}
        eq, injected = svc.build_effective_query(_parsed(), ctx, raw_query="蓝牙耳机 不限品牌")
        assert eq == "蓝牙耳机"
        assert injected == []

    def test_category_always_preserved_first(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brand": "华为", "features": ["降噪"]}
        eq, _ = svc.build_effective_query(_parsed(), ctx)
        assert eq.split()[0] == "蓝牙耳机"

    def test_at_most_one_feature(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brand": None, "features": ["降噪", "入耳", "无线"]}
        eq, injected = svc.build_effective_query(_parsed(), ctx)
        assert injected == ["降噪"]


class TestRerank:
    def test_brand_hit_scores_and_explains(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brands": [{"brand": "华为", "score": 0.6}], "features": [], "price_range": None}
        products = [_product("a", "杂牌耳机", 200), _product("b", "华为耳机", 300, brand="华为")]
        ranked = svc.rerank(products, _parsed(), ctx)
        assert ranked[0].id == "b"
        assert "华为" in ranked[0].recommendation_reason

    def test_budget_hit_scores(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brands": [], "features": [], "price_range": None}
        products = [_product("cheap", "便宜款", 100), _product("fit", "预算款", 500)]
        ranked = svc.rerank(products, _parsed(pmin=400, pmax=600), ctx)
        assert ranked[0].id == "fit"
        assert "预算" in ranked[0].recommendation_reason

    def test_no_memory_marks_exploration(self, tmp_path):
        svc = _svc(tmp_path)
        ctx = {"top_brands": [], "features": [], "price_range": None}
        products = [_product("a", "耳机A", 200, rating=4.8)]
        ranked = svc.rerank(products, _parsed(), ctx)
        assert ranked[0].recommendation_reason.startswith("探索")
        assert svc.matched_count(ranked) == 0
