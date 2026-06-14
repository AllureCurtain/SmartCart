"""并发指标端点单测：结构正确 + 真实反映设备占用。导入真实 app（需 .env）。"""
from fastapi.testclient import TestClient

import main
from services.device_pool import device_pool

client = TestClient(main.app)


def test_concurrency_endpoint_shape():
    data = client.get("/api/system/concurrency").json()
    assert data["success"]
    dp = data["data"]["device_pool"]
    assert {"capacity", "in_use", "waiting", "available"} <= set(dp)
    assert "processing" in data["data"]["tasks"]


def test_endpoint_reflects_device_in_use():
    base = client.get("/api/system/concurrency").json()["data"]["device_pool"]["in_use"]
    with device_pool.acquire():
        busy = client.get("/api/system/concurrency").json()["data"]["device_pool"]["in_use"]
    assert busy == base + 1  # 占用一个设备槽时，指标如实 +1
