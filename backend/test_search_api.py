"""
搜索 API 集成测试：POST 创建 → 后台执行 → GET 取回带 agent_trace 的结果。
用 fake 解析器与 fake 淘宝技能替换 main 的全局装配，不触发真机/GLM。
TestClient 会同步执行 BackgroundTasks，因此一次请求后即可查询结果。
"""
from datetime import datetime

from fastapi.testclient import TestClient

import main
from models import ParsedQuery, Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.task_store import TaskStore
from services.agent_runtime import AgentRuntime
from skills.catalog import build_registry


class _FakeParser:
    def parse(self, query):
        return ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"],
                           price_min=400, price_max=600)


class _FakeTaobao:
    def search(self, keyword, max_products=10, on_progress=None):
        if on_progress:
            on_progress("controlling_phone")
            on_progress("extracting")
        return [
            Product(id="p1", title=f"{keyword} 入门款", price=199, brand="杂牌", platform="taobao"),
            Product(id="p2", title=f"{keyword} 预算款", price=500, brand="华为", platform="taobao"),
        ]


def _wire_fakes(tmp_path):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    store = TaskStore(root=str(tmp_path / "tasks"))
    memory = MemoryContextService(pref)
    reg = build_registry(_FakeTaobao(), pref, store, memory)
    main.task_store = store
    main.registry = reg
    main.agent = AgentRuntime(_FakeParser(), memory, reg)
    return store


def test_search_flow_returns_trace_and_ranked_products(tmp_path):
    originals = (main.task_store, main.registry, main.agent)
    _wire_fakes(tmp_path)
    try:
        client = TestClient(main.app)
        post = client.post("/api/search", json={"query": "我想买500元左右的蓝牙耳机"})
        assert post.json()["success"] is True
        task_id = post.json()["data"]["task_id"]

        got = client.get(f"/api/search/{task_id}").json()
        assert got["success"] is True
        data = got["data"]
        assert data["status"] == "completed"
        # AgentTrace 可见
        assert any("解析需求" in line for line in data["agent_trace"])
        assert any("taobao_search" in line for line in data["agent_trace"])
        # 预算内的商品被排到前面并带推荐理由
        assert data["products"][0]["price"] == 500
        assert data["products"][0]["recommendation_reason"]
        assert data["effective_query"]
    finally:
        main.task_store, main.registry, main.agent = originals


def test_list_skills_endpoint(tmp_path):
    originals = (main.task_store, main.registry, main.agent)
    _wire_fakes(tmp_path)
    try:
        body = TestClient(main.app).get("/api/skills").json()
        names = {s["name"] for s in body["data"]["skills"]}
        assert "taobao_search" in names and "rerank_products" in names
    finally:
        main.task_store, main.registry, main.agent = originals
