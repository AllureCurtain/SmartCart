"""
SkillRegistry - 技能注册、发现与调用

AgentRuntime 和 MCP Server 共用同一个注册表，因此 MCP 是真实的工具入口，
而非另起一套并行实现。
"""
from typing import Any, Dict, List

from skills.base import Skill


class SkillRegistry:
    """按名称注册技能，提供发现、查找与调用。"""

    def __init__(self) -> None:
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册技能实例；名称重复时报错。"""
        if not skill.name:
            raise ValueError("Skill must have a non-empty name")
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        """按名称取技能；未知名称给出清晰错误。"""
        if name not in self._skills:
            available = ", ".join(sorted(self._skills)) or "(none)"
            raise KeyError(f"Unknown skill: {name}. Available: {available}")
        return self._skills[name]

    def list(self) -> List[Skill]:
        """返回稳定顺序（按名称）的技能列表。"""
        return [self._skills[name] for name in sorted(self._skills)]

    def descriptions(self) -> List[Dict[str, Any]]:
        """导出全部技能描述，供 MCP 工具列表使用。"""
        return [skill.describe() for skill in self.list()]

    def invoke(self, name: str, **kwargs: Any) -> Any:
        """按名称调用技能。"""
        return self.get(name).run(**kwargs)
