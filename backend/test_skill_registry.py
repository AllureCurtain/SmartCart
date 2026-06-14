"""
SkillRegistry 单测：注册 / 去重 / 未知报错 / MCP 兼容描述 / 调用。
"""
import pytest

from skills.base import Skill
from skills.registry import SkillRegistry


class _EchoSkill(Skill):
    name = "echo"
    description = "回显输入"
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, **kwargs):
        return kwargs.get("text", "")


def test_register_and_invoke():
    reg = SkillRegistry()
    reg.register(_EchoSkill())
    assert reg.invoke("echo", text="hi") == "hi"


def test_duplicate_name_rejected():
    reg = SkillRegistry()
    reg.register(_EchoSkill())
    with pytest.raises(ValueError):
        reg.register(_EchoSkill())


def test_unknown_skill_raises_clear_error():
    reg = SkillRegistry()
    with pytest.raises(KeyError) as exc:
        reg.get("nope")
    assert "Unknown skill" in str(exc.value)


def test_empty_name_rejected():
    class _NoName(Skill):
        name = ""
        def run(self, **kwargs):
            return None

    with pytest.raises(ValueError):
        SkillRegistry().register(_NoName())


def test_descriptions_are_mcp_tool_compatible():
    reg = SkillRegistry()
    reg.register(_EchoSkill())
    desc = reg.descriptions()
    assert len(desc) == 1
    tool = desc[0]
    # MCP tool 三要素：name / description / inputSchema(=parameters)
    assert tool["name"] == "echo"
    assert isinstance(tool["description"], str) and tool["description"]
    assert tool["parameters"]["type"] == "object"
    assert "text" in tool["parameters"]["properties"]


def test_list_is_sorted_by_name():
    class _ASkill(_EchoSkill):
        name = "alpha"

    class _ZSkill(_EchoSkill):
        name = "zeta"

    reg = SkillRegistry()
    reg.register(_ZSkill())
    reg.register(_ASkill())
    assert [s.name for s in reg.list()] == ["alpha", "zeta"]
