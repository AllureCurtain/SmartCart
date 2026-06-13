from datetime import datetime

from fastapi.testclient import TestClient

import main
from models import ParsedQuery, Product, SearchResult
from services.task_store import TaskStore


def test_latest_search_result_returns_most_recent_completed_task(tmp_path):
    original_store = main.task_store
    main.task_store = TaskStore(root=str(tmp_path))
    try:
        main.task_store.write(SearchResult(
            task_id="aaaa1111-bbbb-2222-cccc-333344445555",
            query="蓝牙耳机",
            parsed_query=ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"]),
            products=[
                Product(
                    id="p1",
                    title="华为FreeBuds 7i智慧降噪蓝牙耳机",
                    price=443.01,
                    brand="华为",
                    platform="taobao",
                )
            ],
            total_count=1,
            status="completed",
            created_at=datetime.now(),
        ))

        response = TestClient(main.app).get("/api/search/latest/default")
    finally:
        main.task_store = original_store

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["products"][0]["title"] == "华为FreeBuds 7i智慧降噪蓝牙耳机"
