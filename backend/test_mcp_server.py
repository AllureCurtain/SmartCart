"""
MCP Server 单测：从注册表生成 MCP 工具定义、转发调用。
用 mock 淘宝技能，不触发真机/网络。
"""
from models import Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.task_store import TaskStore
from skills.catalog import build_registry
import mcp_server


class _FakeTaobao:
    def search(self, keyword, max_products=10, on_progress=None):
        return [Product(id="p1", title=f"{keyword}", price=300, brand="华为", platform="taobao")]


def _registry(tmp_path):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    memory = MemoryContextService(pref)
    return build_registry(_FakeTaobao(), pref, TaskStore(root=str(tmp_path / "t")), memory)


def test_tool_definitions_from_registry(tmp_path):
    tools = mcp_server.tool_definitions(_registry(tmp_path))
    names = {t.name for t in tools}
    assert names == {"taobao_search", "get_preference_insight",
                     "record_product_action", "rerank_products"}
    # 每个工具都有 MCP 要求的 inputSchema
    for t in tools:
        assert t.inputSchema["type"] == "object"
        assert t.description


def test_invoke_tool_forwards_to_registry(tmp_path):
    reg = _registry(tmp_path)
    out = mcp_server.invoke_tool(reg, "taobao_search", {"keyword": "蓝牙耳机", "max_products": 1})
    assert isinstance(out, list) and out[0]["id"] == "p1"


def test_invoke_unknown_tool_raises(tmp_path):
    import pytest
    with pytest.raises(KeyError):
        mcp_server.invoke_tool(_registry(tmp_path), "nope", {})


def test_create_server_builds(tmp_path):
    server = mcp_server.create_server(_registry(tmp_path))
    assert server.name == "smartcart"
