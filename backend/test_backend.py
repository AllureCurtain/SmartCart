"""
测试后端服务
"""
import sys
sys.path.insert(0, '.')

from services.query_parser import QueryParserService
from services.preference_service import PreferenceService
from models import Product, ParsedQuery

print("=" * 50)
print("SmartCart 后端服务测试")
print("=" * 50)

# 测试 1: 查询解析
print("\n[测试 1] 查询解析服务")
print("-" * 50)
parser = QueryParserService()

test_query = "我想买500元左右的蓝牙耳机，音质要好"
print(f"输入: {test_query}")

try:
    result = parser.parse(test_query)
    print(f"✅ 解析成功:")
    print(f"   品类: {result.category}")
    print(f"   关键词: {result.keywords}")
    print(f"   价格: {result.price_min} - {result.price_max}")
    print(f"   特性: {result.features}")
except Exception as e:
    print(f"❌ 解析失败: {e}")

# 测试 2: 偏好学习
print("\n[测试 2] 偏好学习服务")
print("-" * 50)
pref_service = PreferenceService()

# 记录搜索
parsed = ParsedQuery(
    category="蓝牙耳机",
    keywords=["蓝牙", "耳机"],
    price_min=400,
    price_max=600,
    features=["音质"]
)
pref_service.record_search("test_user", test_query, parsed)
print("✅ 搜索已记录")

# 记录商品查看
product1 = Product(
    id="test1",
    title="Sony WH-1000XM5 蓝牙耳机",
    price=1899.0,
    brand="Sony",
    platform="taobao"
)
pref_service.record_product_view("test_user", product1)
print("✅ 商品查看已记录")

# 记录商品点击
product2 = Product(
    id="test2",
    title="Bose QC45 降噪耳机",
    price=1999.0,
    brand="Bose",
    platform="taobao"
)
pref_service.record_product_click("test_user", product2)
print("✅ 商品点击已记录")

# 获取偏好
pref = pref_service.get_preference("test_user")
print(f"\n用户偏好:")
print(f"  搜索历史: {len(pref.search_history)} 条")
print(f"  品牌偏好:")
for brand, brand_pref in pref.brand_preferences.items():
    print(f"    - {brand}: 分数 {brand_pref.score:.2f}, 次数 {brand_pref.count}")
if pref.price_preference:
    print(f"  价格偏好: ¥{pref.price_preference.min} - ¥{pref.price_preference.max}")
print(f"  特性偏好: {pref.feature_preferences}")

# 测试 3: 推荐权重
print("\n[测试 3] 推荐权重")
print("-" * 50)
weights = pref_service.get_recommendation_weights("test_user")
print("推荐权重:")
for key, weight in weights.items():
    print(f"  {key}: {weight:.2f}")

print("\n" + "=" * 50)
print("✅ 所有测试完成!")
print("=" * 50)
