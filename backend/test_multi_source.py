"""
多源并发编排单测：合并、跨平台比价标注、单源回退、单源失败隔离、并发 fan-out。
全部用 fake 源（不占 device_pool，可真并行），不碰真机/网络。
"""
import time

from models import ParsedQuery, Product
from services.preference_service import PreferenceService
from services.memory_context import MemoryContextService
from services.agent_runtime import AgentRuntime, _annotate_deals
from services.task_store import TaskStore
from skills.catalog import build_registry


class _FakeParser:
    def __init__(self, parsed):
        self._p = parsed
    def parse(self, query):
        return self._p


class _FakeSource:
    """假平台源：返回固定商品并打上自身 platform；delay 用于并发计时测试。"""
    def __init__(self, platform, products, delay=0.0):
        self.platform = platform
        self._products = products
        self.delay = delay
        self.calls = 0
    def search(self, keyword, max_products=10, on_progress=None):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        return [Product(platform=self.platform, **p) for p in self._products]


class _FailingSource:
    platform = "jd"
    def search(self, keyword, max_products=10, on_progress=None):
        raise RuntimeError("boom")


def _runtime(tmp_path, taobao, jd=None, parsed=None):
    pref = PreferenceService(storage_path=str(tmp_path / "pref"))
    memory = MemoryContextService(pref)
    reg = build_registry(taobao, pref, TaskStore(root=str(tmp_path / "t")), memory, jd_skill=jd)
    parsed = parsed or ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    return AgentRuntime(_FakeParser(parsed), memory, reg)


def test_multi_source_merges_both_platforms(tmp_path):
    tb = _FakeSource("taobao", [{"id": "t1", "title": "华为耳机", "price": 300, "brand": "华为"}])
    jd = _FakeSource("jd", [{"id": "j1", "title": "小米耳机", "price": 200, "brand": "小米"}])
    out = _runtime(tmp_path, tb, jd).run_search("蓝牙耳机", platform="all")
    assert {p.platform for p in out.products} == {"taobao", "jd"}
    joined = " | ".join(out.agent_trace)
    assert "taobao_search" in joined and "jd_search" in joined
    assert "综合比价" in joined
    assert tb.calls == 1 and jd.calls == 1


def test_cheapest_gets_global_low_tag(tmp_path):
    tb = _FakeSource("taobao", [{"id": "t1", "title": "A", "price": 300, "brand": "华为"}])
    jd = _FakeSource("jd", [{"id": "j1", "title": "B", "price": 200, "brand": "小米"}])
    out = _runtime(tmp_path, tb, jd).run_search("耳机", platform="all")
    cheapest = min(out.products, key=lambda p: p.price)
    assert cheapest.price == 200 and cheapest.deal_tag == "全网最低价"


def test_annotate_deals_same_brand_cross_platform():
    products = [
        Product(id="1", title="华为A", price=500, brand="华为", platform="taobao"),
        Product(id="2", title="华为B", price=400, brand="华为", platform="jd"),
        Product(id="3", title="小米", price=300, brand="小米", platform="taobao"),
    ]
    _annotate_deals(products)
    by_id = {p.id: p for p in products}
    assert by_id["3"].deal_tag == "全网最低价"        # 整体最低
    assert by_id["2"].deal_tag == "华为全网最低"       # 华为跨平台更低者
    assert by_id["1"].deal_tag is None


def test_single_source_skips_compare_and_other_platform(tmp_path):
    tb = _FakeSource("taobao", [{"id": "t1", "title": "A", "price": 300, "brand": "华为"}])
    jd = _FakeSource("jd", [{"id": "j1", "title": "B", "price": 200}])
    out = _runtime(tmp_path, tb, jd).run_search("耳机", platform="taobao")
    assert all(p.platform == "taobao" for p in out.products)
    assert "综合比价" not in " | ".join(out.agent_trace)
    assert all(p.deal_tag is None for p in out.products)
    assert jd.calls == 0  # 单源不应调用京东


def test_one_source_failure_is_isolated(tmp_path):
    tb = _FakeSource("taobao", [{"id": "t1", "title": "A", "price": 300}])
    out = _runtime(tmp_path, tb, _FailingSource()).run_search("耳机", platform="all")
    assert [p.platform for p in out.products] == ["taobao"]  # 京东失败被隔离，不拖垮淘宝


def test_failed_source_still_has_failed_skill_run(tmp_path):
    tb = _FakeSource("taobao", [{"id": "t1", "title": "A", "price": 300}])
    out = _runtime(tmp_path, tb, _FailingSource()).run_search("耳机", platform="all")

    by_platform = {run.platform: run for run in out.skill_runs}
    assert by_platform["taobao"].status == "completed"
    assert by_platform["jd"].status == "failed"
    assert by_platform["jd"].product_count == 0


def test_fan_out_runs_concurrently(tmp_path):
    # 两个各 sleep 0.3s 的非设备源：并发应 ~0.3s 而非串行 ~0.6s
    tb = _FakeSource("taobao", [{"id": "t1", "title": "A", "price": 300}], delay=0.3)
    jd = _FakeSource("jd", [{"id": "j1", "title": "B", "price": 200}], delay=0.3)
    rt = _runtime(tmp_path, tb, jd)
    start = time.perf_counter()
    rt.run_search("耳机", platform="all")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.55  # 证明编排层是真并发
