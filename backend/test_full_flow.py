"""
同步测试完整搜索流程
"""
import sys
sys.path.insert(0, '.')

from services.query_parser import QueryParserService
from services.preference_service import PreferenceService
from skills.taobao_search import TaobaoSearchSkill
from models import SearchResult, ParsedQuery
from datetime import datetime
import uuid

print("=" * 60)
print("SmartCart 完整流程测试")
print("=" * 60)

# 测试 1: 查询解析
print("\n[步骤 1] 查询解析")
print("-" * 60)
parser = QueryParserService()
query = "我想买蓝牙耳机"
print(f"输入: {query}")

try:
    parsed = parser.parse(query)
    print(f"✅ 解析成功:")
    print(f"   品类: {parsed.category}")
    print(f"   关键词: {parsed.keywords}")
except Exception as e:
    print(f"❌ 解析失败: {e}")
    # 使用降级模式
    parsed = ParsedQuery(
        category=query,
        keywords=[query],
        price_min=None,
        price_max=None,
        features=[]
    )
    print(f"✅ 使用简单解析")

# 测试 2: 淘宝搜索 Skill
print("\n[步骤 2] 淘宝搜索")
print("-" * 60)
print("⚠️  注意: 这会真实控制手机搜索淘宝")
print("确认手机已连接并解锁")

try:
    skill = TaobaoSearchSkill()
    print(f"搜索关键词: {parsed.category}")
    print("正在搜索...")

    products = skill.search(parsed.category, max_products=5)

    print(f"✅ 搜索完成")
    print(f"   找到 {len(products)} 个商品")
    for i, p in enumerate(products[:3], 1):
        print(f"   {i}. {p.title} - ¥{p.price}")

except Exception as e:
    print(f"❌ 搜索失败: {e}")
    import traceback
    traceback.print_exc()
    products = []

# 测试 3: 创建搜索结果
print("\n[步骤 3] 保存搜索结果")
print("-" * 60)
try:
    task_id = str(uuid.uuid4())
    result = SearchResult(
        task_id=task_id,
        query=query,
        parsed_query=parsed,
        products=products,
        total_count=len(products),
        status="completed" if products else "failed",
        created_at=datetime.now()
    )

    # 保存到文件
    from pathlib import Path
    import json

    tasks_dir = Path("data/tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)

    result_file = tasks_dir / f"{task_id}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        data = result.dict()
        data['created_at'] = data['created_at'].isoformat()
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 结果已保存")
    print(f"   任务 ID: {task_id}")
    print(f"   文件: {result_file}")

except Exception as e:
    print(f"❌ 保存失败: {e}")

# 测试 4: 偏好学习
print("\n[步骤 4] 偏好学习")
print("-" * 60)
try:
    pref_service = PreferenceService()

    # 记录搜索
    pref_service.record_search("test_user", query, parsed)
    print(f"✅ 搜索已记录")

    # 记录商品查看（如果有商品）
    if products:
        pref_service.record_product_view("test_user", products[0])
        print(f"✅ 商品查看已记录")

    # 获取偏好
    pref = pref_service.get_preference("test_user")
    print(f"\n用户偏好:")
    print(f"  搜索历史: {len(pref.search_history)} 条")
    print(f"  品牌偏好: {len(pref.brand_preferences)} 个")
    for brand, brand_pref in list(pref.brand_preferences.items())[:3]:
        print(f"    - {brand}: {brand_pref.score:.2f}")

except Exception as e:
    print(f"❌ 偏好学习失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 完整流程测试完成")
print("=" * 60)
