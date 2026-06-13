"""
AgentRuntime 单测：mock 解析器 + mock 淘宝技能，验证 trace、记忆注入、
用户意图优先、重排接入与进度回调。不触发真机/网络。
"""
from datetime import datetime

from models import BrandPreference, ParsedQuery, Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.agent_runtime import AgentRuntime
from skills.catalog import build_registry
from services.task_store import TaskStore


class _FakeParser:
    def __init__(self, parsed):
        self._parsed = parsed
    def parse(self, query):
        return self._parsed


class _FakeTaobao:
    def __init__(self):
        self.last_keyword = None
    def search(self, keyword, max_products=10, on_progress=None):
        self.last_keyword = keyword
        if on_progress:
            on_progress("controlling_phone")
            on_progress("extracting")
        return [
            Product(id="p1", title=f"{keyword} 华为款", price=500, brand="华为", platform="taobao"),
            Product(id="p2", title=f"{keyword} 杂牌款", price=150, brand="杂牌", platform="taobao"),
        ]


def _runtime(tmp_path, parsed, seed_brand=None):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    if seed_brand:
        p = pref.get_preference("default")
        p.brand_preferences[seed_brand] = BrandPreference(
            brand=seed_brand, score=0.6, count=3, last_updated=datetime.now())
        pref.save_preference(p)
    memory = MemoryContextService(pref)
    fake_taobao = _FakeTaobao()
    reg = build_registry(fake_taobao, pref, TaskStore(root=str(tmp_path / "t")), memory)
    return AgentRuntime(_FakeParser(parsed), memory, reg), fake_taobao


def test_trace_has_all_stages(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"], price_min=400, price_max=600)
    rt, _ = _runtime(tmp_path, parsed)
    out = rt.run_search("我想买500元左右的蓝牙耳机")
    joined = " | ".join(out.agent_trace)
    assert "解析需求" in joined
    assert "读取记忆" in joined
    assert "taobao_search" in joined
    assert "推荐排序" in joined


def test_memory_injects_brand_into_effective_query(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    rt, fake = _runtime(tmp_path, parsed, seed_brand="华为")
    out = rt.run_search("蓝牙耳机")
    assert "华为" in out.effective_query
    assert fake.last_keyword == out.effective_query  # 真机收到的是注入后的词


def test_user_broad_intent_overrides_memory(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    rt, fake = _runtime(tmp_path, parsed, seed_brand="华为")
    out = rt.run_search("蓝牙耳机 不限品牌")
    assert "华为" not in out.effective_query


def test_rerank_promotes_preferred_brand(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    rt, _ = _runtime(tmp_path, parsed, seed_brand="华为")
    out = rt.run_search("蓝牙耳机")
    assert out.products[0].brand == "华为"
    assert out.products[0].recommendation_reason


def test_progress_callback_receives_stages(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    rt, _ = _runtime(tmp_path, parsed)
    stages = []
    rt.run_search("蓝牙耳机", on_progress=stages.append)
    assert "controlling_phone" in stages
    assert "ranking" in stages
