"""
京东搜索 Skill 单测：验证多平台复用（淘宝/京东共用同一条真机链路），
以及注册表/AgentRuntime 的平台分发。全部用 demo_mode / mock，不触发真机/网络。
"""
from models import BrandPreference, ParsedQuery, Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.agent_runtime import AgentRuntime
from services.task_store import TaskStore
from skills.catalog import build_registry
from skills.taobao_search import TaobaoSearchSkill, JDSearchSkill, PhoneSearchSkill


# ---- 平台子类只改默认平台，逻辑全继承自 PhoneSearchSkill ----

def test_subclasses_set_platform_and_app_name():
    assert issubclass(TaobaoSearchSkill, PhoneSearchSkill)
    assert issubclass(JDSearchSkill, PhoneSearchSkill)
    assert (TaobaoSearchSkill().platform, TaobaoSearchSkill().app_name) == ("taobao", "淘宝")
    assert (JDSearchSkill().platform, JDSearchSkill().app_name) == ("jd", "京东")


def test_build_instruction_uses_each_app_name():
    jd_instr = JDSearchSkill()._build_instruction("蓝牙耳机")
    assert "京东" in jd_instr and "蓝牙耳机" in jd_instr
    # 回归：淘宝指令仍是淘宝
    assert "淘宝" in TaobaoSearchSkill()._build_instruction("蓝牙耳机")


def test_jd_demo_search_marks_jd_platform():
    products = JDSearchSkill(demo_mode=True).search("耳机", max_products=3)
    assert len(products) == 3
    assert all(p.platform == "jd" for p in products)
    assert all(p.is_demo for p in products)  # 降级数据必须可见


# ---- 注册表：传入 jd_skill 即额外暴露 jd_search ----

def _registry(tmp_path, with_jd: bool):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    memory = MemoryContextService(pref)
    tasks = TaskStore(root=str(tmp_path / "t"))
    jd = JDSearchSkill(demo_mode=True) if with_jd else None
    reg = build_registry(TaobaoSearchSkill(demo_mode=True), pref, tasks, memory, jd_skill=jd)
    return reg


def test_registry_exposes_jd_search_only_when_provided(tmp_path):
    names_with = {s.name for s in _registry(tmp_path, with_jd=True).list()}
    names_without = {s.name for s in _registry(tmp_path, with_jd=False).list()}
    assert "jd_search" in names_with and "taobao_search" in names_with
    assert len(names_with) == 5
    assert "jd_search" not in names_without  # 向后兼容：不传 jd 仍是 4 个
    assert len(names_without) == 4


def test_jd_search_via_registry_returns_jd_products(tmp_path):
    reg = _registry(tmp_path, with_jd=True)
    out = reg.invoke("jd_search", keyword="蓝牙耳机", max_products=2)
    assert isinstance(out, list) and len(out) == 2
    assert all(p["platform"] == "jd" for p in out)


# ---- AgentRuntime 按 platform 分发到对应平台技能 ----

class _FakeParser:
    def __init__(self, parsed):
        self._parsed = parsed
    def parse(self, query):
        return self._parsed


class _RecordingSearch:
    def __init__(self, platform):
        self.platform = platform
        self.last_keyword = None
    def search(self, keyword, max_products=10, on_progress=None):
        self.last_keyword = keyword
        return [Product(id=f"{self.platform}1", title=keyword, price=300,
                        brand="华为", platform=self.platform)]


def test_agent_runtime_dispatches_to_jd(tmp_path):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    memory = MemoryContextService(pref)
    taobao, jd = _RecordingSearch("taobao"), _RecordingSearch("jd")
    reg = build_registry(taobao, pref, TaskStore(root=str(tmp_path / "t")), memory, jd_skill=jd)
    rt = AgentRuntime(_FakeParser(ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])), memory, reg)

    out = rt.run_search("蓝牙耳机", platform="jd")

    assert "jd_search" in " | ".join(out.agent_trace)
    assert jd.last_keyword == "蓝牙耳机"      # 京东技能真的被调用
    assert taobao.last_keyword is None        # 淘宝技能没被调用
    assert out.products[0].platform == "jd"
