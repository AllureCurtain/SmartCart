"""
Skill 机制 - 抽象基类

每个 Skill 用声明式的方式描述自己（名称、说明、参数 JSON Schema），
并实现统一的 run() 入口。这样 AgentRuntime / MCP / REST 都能以同一套
契约发现并调用技能，而不必硬编码每个技能的细节。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class Skill(ABC):
    """可被 Agent 发现和调用的技能。"""

    #: 唯一技能名（同时作为 MCP tool 名）
    name: str = ""
    #: 给 LLM / MCP 客户端看的能力说明
    description: str = ""
    #: 入参的 JSON Schema（即 MCP tool 的 inputSchema）
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """执行技能。kwargs 由 parameters schema 约束。"""
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        """导出技能描述，供注册表 / MCP 工具列表使用。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
