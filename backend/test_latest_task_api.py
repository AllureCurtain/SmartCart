import json
from datetime import datetime

from fastapi.testclient import TestClient

import main
from models import ParsedQuery, Product, SearchResult


def test_latest_search_result_returns_most_recent_completed_task(tmp_path):
    original_tasks_dir = main.TASKS_DIR
    main.TASKS_DIR = tmp_path
    try:
        result = SearchResult(
            task_id="latest-task",
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
        )
        data = result.model_dump()
        data["created_at"] = data["created_at"].isoformat()
        (tmp_path / "latest-task.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

        response = TestClient(main.app).get("/api/search/latest/default")
    finally:
        main.TASKS_DIR = original_tasks_dir

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == "latest-task"
    assert body["data"]["products"][0]["title"] == "华为FreeBuds 7i智慧降噪蓝牙耳机"
