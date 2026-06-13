"""
技能目录单测：用 mock 的淘宝技能，不触发真机/网络。
"""
from datetime import datetime

from models import Product, SearchResult, ParsedQuery
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.task_store import TaskStore
from skills.catalog import build_registry


class _FakeTaobao:
    """假淘宝技能：返回固定商品，避免真机/网络。"""
    def search(self, keyword, max_products=10, on_progress=None):
        if on_progress:
            on_progress("controlling_phone")
        return [
            Product(id="p1", title=f"{keyword} 华为款", price=300, brand="华为", platform="taobao"),
            Product(id="p2", title=f"{keyword} 杂牌款", price=150, brand="杂牌", platform="taobao"),
        ]


def _registry(tmp_path):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    tasks = TaskStore(root=str(tmp_path / "tasks"))
    memory = MemoryContextService(pref)
    reg = build_registry(_FakeTaobao(), pref, tasks, memory)
    return reg, pref, tasks


def test_registry_exposes_four_tools(tmp_path):
    reg, _, _ = _registry(tmp_path)
    names = {s.name for s in reg.list()}
    assert names == {"taobao_search", "get_preference_insight",
                     "record_product_action", "rerank_products"}


def test_taobao_search_returns_dicts(tmp_path):
    reg, _, _ = _registry(tmp_path)
    out = reg.invoke("taobao_search", keyword="蓝牙耳机", max_products=2)
    assert isinstance(out, list) and out[0]["id"] == "p1"


def test_record_action_writes_memory(tmp_path):
    reg, pref, tasks = _registry(tmp_path)
    # 先落一个任务文件
    result = SearchResult(
        task_id="abc12345",
        query="蓝牙耳机",
        parsed_query=ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"]),
        products=[Product(id="p1", title="华为耳机", price=300, brand="华为", platform="taobao")],
        total_count=1,
        status="completed",
        created_at=datetime.now(),
    )
    tasks.write(result)
    res = reg.invoke("record_product_action", task_id="abc12345",
                     product_id="p1", action_type="click")
    assert res["recorded"] is True
    assert any(b["brand"] == "华为" for b in res["insight"]["top_brands"])


def test_record_action_rejects_demo(tmp_path):
    reg, pref, tasks = _registry(tmp_path)
    result = SearchResult(
        task_id="def67890",
        query="x",
        parsed_query=ParsedQuery(category="x", keywords=["x"]),
        products=[Product(id="d1", title="演示", price=99, brand="Brand1",
                          platform="taobao", is_demo=True)],
        total_count=1,
        status="completed",
        created_at=datetime.now(),
    )
    tasks.write(result)
    res = reg.invoke("record_product_action", task_id="def67890",
                     product_id="d1", action_type="click")
    assert res["recorded"] is False


def test_rerank_via_registry(tmp_path):
    reg, _, _ = _registry(tmp_path)
    products = [
        {"id": "a", "title": "便宜款", "price": 100, "platform": "taobao"},
        {"id": "b", "title": "预算款", "price": 500, "platform": "taobao"},
    ]
    out = reg.invoke("rerank_products", products=products,
                     parsed={"category": "耳机", "keywords": ["耳机"],
                             "price_min": 400, "price_max": 600})
    assert out[0]["id"] == "b"
    assert out[0]["recommendation_reason"]
