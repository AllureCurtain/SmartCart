"""
偏好排序（自进化闭环消费端）单测。

验证 rank_products 真正把学到的偏好作用于结果顺序——
这是岗位要求"自进化机制"的核心证据。
"""
from datetime import datetime

from models import Product, BrandPreference, PricePreference
from services.preference_service import PreferenceService


def _product(pid, title, price, brand=None):
    return Product(id=pid, title=title, price=price, brand=brand, platform="taobao")


def test_no_preference_keeps_original_order(tmp_path):
    svc = PreferenceService(storage_path=str(tmp_path))
    products = [_product("1", "A", 100), _product("2", "B", 200)]
    assert [p.id for p in svc.rank_products("newuser", products)] == ["1", "2"]


def test_brand_preference_promotes_matching_product(tmp_path):
    svc = PreferenceService(storage_path=str(tmp_path))
    pref = svc.get_preference("u1")
    pref.brand_preferences["华为"] = BrandPreference(
        brand="华为", score=0.9, count=3, last_updated=datetime.now()
    )
    svc.save_preference(pref)

    products = [
        _product("other", "杂牌耳机", 199),
        _product("hw", "华为 FreeBuds", 443, brand="华为"),
    ]
    ranked = svc.rank_products("u1", products)
    assert ranked[0].id == "hw"  # 偏好品牌被提到首位


def test_price_in_preferred_range_scores_higher(tmp_path):
    svc = PreferenceService(storage_path=str(tmp_path))
    pref = svc.get_preference("u2")
    pref.price_preference = PricePreference(min=400, max=600, avg=500, median=500)
    svc.save_preference(pref)

    products = [
        _product("cheap", "便宜款", 150),
        _product("fit", "区间内款", 500),
    ]
    ranked = svc.rank_products("u2", products)
    assert ranked[0].id == "fit"


def test_feature_hit_in_title_scores_higher(tmp_path):
    svc = PreferenceService(storage_path=str(tmp_path))
    pref = svc.get_preference("u3")
    pref.feature_preferences["降噪"] = 0.8
    svc.save_preference(pref)

    products = [
        _product("plain", "普通蓝牙耳机", 300),
        _product("anc", "主动降噪蓝牙耳机", 300),
    ]
    ranked = svc.rank_products("u3", products)
    assert ranked[0].id == "anc"
