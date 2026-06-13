"""
商品提取链路的纯函数单测：数值容错、品牌清洗、降级数据标记。

均不触发真机或网络，安全在 CI / pytest 中运行。
"""
from skills.taobao_search import (
    _parse_float,
    _parse_int,
    _clean_brand,
    _sanitize_keyword,
    TaobaoSearchSkill,
)


class TestNumericParsing:
    def test_parse_float_strips_currency_symbol(self):
        assert _parse_float("¥343.82") == 343.82
        assert _parse_float("343.82元") == 343.82

    def test_parse_float_passthrough_number(self):
        assert _parse_float(443.01) == 443.01
        assert _parse_float(100) == 100.0

    def test_parse_float_invalid_returns_zero(self):
        assert _parse_float(None) == 0.0
        assert _parse_float("暂无") == 0.0

    def test_parse_int_handles_wan_suffix(self):
        assert _parse_int("1.5万+") == 15000
        assert _parse_int("7万+") == 70000

    def test_parse_int_handles_plus_suffix(self):
        assert _parse_int("6000+") == 6000

    def test_parse_int_none(self):
        assert _parse_int(None) is None
        assert _parse_int("无") is None


class TestBrandCleaning:
    def test_platform_labels_rejected(self):
        for label in ("天猫", "淘宝", "百亿补贴", "旗舰店", "京东自营"):
            assert _clean_brand(label) is None, label

    def test_real_brand_kept(self):
        assert _clean_brand("华为") == "华为"
        assert _clean_brand("  荣耀 ") == "荣耀"

    def test_empty_returns_none(self):
        assert _clean_brand(None) is None
        assert _clean_brand("") is None


class TestKeywordSanitize:
    def test_strips_quotes_and_newlines(self):
        assert "\n" not in _sanitize_keyword("蓝牙\n耳机")
        assert '"' not in _sanitize_keyword('蓝牙"耳机')

    def test_length_capped(self):
        long = "蓝牙耳机" * 20
        assert len(_sanitize_keyword(long)) <= 30


class TestMockDataMarking:
    def test_mock_products_all_flagged_demo(self):
        products = TaobaoSearchSkill(demo_mode=True)._get_mock_products("蓝牙耳机", 5)
        assert len(products) == 5
        assert all(p.is_demo for p in products)
