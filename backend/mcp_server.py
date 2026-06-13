"""
SmartCart MCP Server

把 SkillRegistry 里的技能以 MCP 工具的形式暴露给任意 MCP 客户端
（如 Claude Desktop）。MCP 层不感知淘宝/偏好/任务文件/GLM 细节，
只负责"列工具 + 转发调用"，因此与 FastAPI 共享同一套技能实现。

运行（stdio 传输）：
    python mcp_server.py
"""
import asyncio
import json
import logging
from typing import Any, Dict, List

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

SERVER_NAME = "smartcart"


def tool_definitions(registry: SkillRegistry) -> List[types.Tool]:
    """把注册表技能描述转换为 MCP Tool 定义。"""
    return [
        types.Tool(
            name=d["name"],
            description=d["description"],
            inputSchema=d["parameters"],
        )
        for d in registry.descriptions()
    ]


def invoke_tool(registry: SkillRegistry, name: str, arguments: Dict[str, Any] | None) -> Any:
    """把 MCP 工具调用转发回注册表。"""
    return registry.invoke(name, **(arguments or {}))


def create_server(registry: SkillRegistry) -> Server:
    """基于注册表创建已接好 list_tools / call_tool 的 MCP Server。"""
    server: Server = Server(SERVER_NAME)

    @server.list_tools()
    async def _list_tools() -> List[types.Tool]:
        return tool_definitions(registry)

    @server.call_tool()
    async def _call_tool(name: str, arguments: Dict[str, Any] | None) -> List[types.TextContent]:
        try:
            result = invoke_tool(registry, name, arguments)
            text = json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:  # 工具异常以文本回传，不让 server 崩
            logger.exception("MCP tool %s failed", name)
            text = json.dumps({"error": str(e)}, ensure_ascii=False)
        return [types.TextContent(type="text", text=text)]

    return server


def build_default_registry() -> SkillRegistry:
    """用真实服务组装注册表（供 stdio 入口使用；需要 .env 配置）。"""
    from skills.catalog import build_registry
    from skills.taobao_search import TaobaoSearchSkill
    from services.preference_service import PreferenceService
    from services.memory_context import MemoryContextService
    from services.task_store import TaskStore

    preference_service = PreferenceService()
    task_store = TaskStore()
    memory_service = MemoryContextService(preference_service)
    return build_registry(TaobaoSearchSkill(), preference_service, task_store, memory_service)


async def run_stdio() -> None:
    registry = build_default_registry()
    server = create_server(registry)
    logger.info("SmartCart MCP server started with tools: %s",
                ", ".join(s.name for s in registry.list()))
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    from app_logging import setup_logging
    setup_logging()
    asyncio.run(run_stdio())
