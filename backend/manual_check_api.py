"""
完整的 API 测试脚本
"""
import requests
import time
import json

API_BASE = "http://localhost:8000"

print("=" * 60)
print("SmartCart 完整 API 测试")
print("=" * 60)

# 测试 1: 健康检查
print("\n[测试 1] 健康检查")
print("-" * 60)
try:
    response = requests.get(f"{API_BASE}/health")
    print(f"✅ 状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试 2: 创建搜索任务
print("\n[测试 2] 创建搜索任务")
print("-" * 60)
try:
    payload = {
        "query": "蓝牙耳机",
        "user_id": "test_user"
    }
    response = requests.post(
        f"{API_BASE}/api/search",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")

    if response.status_code == 200:
        result = response.json()
        print(f"✅ 任务创建成功")
        print(f"   任务 ID: {result.get('data', {}).get('task_id')}")
        task_id = result.get('data', {}).get('task_id')

        # 测试 3: 轮询获取结果
        print("\n[测试 3] 获取搜索结果")
        print("-" * 60)

        for i in range(5):
            time.sleep(3)
            result_response = requests.get(f"{API_BASE}/api/search/{task_id}")
            result_data = result_response.json()

            if result_data.get('success'):
                data = result_data.get('data', {})
                status = data.get('status', 'unknown')
                print(f"   第 {i+1} 次查询: {status}")

                if status == 'completed':
                    print(f"✅ 搜索完成")
                    products = data.get('products', [])
                    print(f"   找到 {len(products)} 个商品")
                    if products:
                        print(f"   示例商品: {products[0].get('title')}")
                    break
                elif status == 'failed':
                    print(f"❌ 搜索失败: {data.get('error')}")
                    break
            else:
                print(f"❌ 获取结果失败: {result_data.get('error')}")
                break
    else:
        print(f"❌ 任务创建失败")

except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 获取用户偏好
print("\n[测试 4] 获取用户偏好")
print("-" * 60)
try:
    response = requests.get(f"{API_BASE}/api/preference/test_user")
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            pref = result.get('data', {})
            print(f"✅ 获取成功")
            print(f"   搜索历史: {len(pref.get('search_history', []))} 条")
            print(f"   品牌偏好: {len(pref.get('brand_preferences', {}))} 个")
        else:
            print(f"❌ 失败: {result.get('error')}")
    else:
        print(f"❌ 请求失败: {response.text}")

except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
