"""
手动演示：多用户并发 + 设备资源池排队（不是 pytest，需后端在跑）。

用法：
    python manual_check_concurrency.py [并发数N] [base_url]

同时发起 N 个搜索请求，并持续打印 /api/system/concurrency：
- 真机源 + 单手机：会看到 processing=N、device_pool.in_use=1、waiting=N-1
  —— 编排层并发、设备层串行排队（诚实）。
- 若后端以 demo 源 / DEVICE_POOL_SIZE>1 启动：in_use 可 >1，体现真并行。

提示：真机源每次 1-5 分钟，演示并发排队建议用 demo 模式后端。
"""
import json
import sys
import threading
import time
import urllib.request


def _post(base, payload):
    req = urllib.request.Request(
        f"{base}/api/search", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def _get(base, path):
    return json.loads(urllib.request.urlopen(f"{base}{path}", timeout=10).read())


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    base = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"

    print(f"同时发起 {n} 个搜索 → {base}")
    for i in range(n):
        threading.Thread(
            target=lambda i=i: _post(base, {
                "query": f"蓝牙耳机 #{i}", "user_id": f"user{i}", "platform": "all",
            }),
            daemon=True,
        ).start()

    # 轮询并发指标 ~30s，观察排队
    for _ in range(15):
        time.sleep(2)
        try:
            d = _get(base, "/api/system/concurrency")["data"]
            dp = d["device_pool"]
            print(f"processing={d['tasks']['processing']:>2} | "
                  f"device in_use={dp['in_use']} waiting={dp['waiting']} "
                  f"capacity={dp['capacity']}")
        except Exception as e:  # noqa: BLE001
            print("指标查询失败:", e)


if __name__ == "__main__":
    main()
