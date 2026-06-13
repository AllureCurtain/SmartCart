import os
from datetime import datetime

import pytest

from models import ParsedQuery, Product, SearchResult
from services.task_store import TaskStore


def _result(task_id: str = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") -> SearchResult:
    return SearchResult(
        task_id=task_id,
        query="蓝牙耳机",
        parsed_query=ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"]),
        products=[
            Product(
                id="p1",
                title="华为 FreeBuds 蓝牙耳机",
                price=499,
                brand="华为",
                platform="taobao",
                recommendation_score=1.0,
                recommendation_reason="命中你常看的华为品牌",
            )
        ],
        total_count=1,
        status="processing",
        progress="queued",
        agent_trace=["解析需求 -> 蓝牙耳机"],
        effective_query="蓝牙耳机",
        created_at=datetime.now(),
    )


def test_write_and_read_raw_task(tmp_path):
    store = TaskStore(tmp_path)
    store.write(_result())

    data = store.read_raw("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert data["task_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert data["products"][0]["recommendation_reason"] == "命中你常看的华为品牌"
    assert data["created_at"].count("T") == 1


def test_update_task_fields(tmp_path):
    store = TaskStore(tmp_path)
    store.write(_result())

    store.update(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        progress="ranking",
        agent_trace=["解析需求 -> 蓝牙耳机", "推荐排序 -> 1 个商品，1 个命中偏好"],
    )

    data = store.read_raw("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert data["progress"] == "ranking"
    assert data["agent_trace"][-1] == "推荐排序 -> 1 个商品，1 个命中偏好"


def test_write_rejects_invalid_task_id_without_escaping_root(tmp_path):
    root = tmp_path / "tasks"
    store = TaskStore(root)
    result = _result("../aaaaaaaa")

    with pytest.raises(ValueError, match="Invalid task_id"):
        store.write(result)

    assert not (tmp_path / "aaaaaaaa.json").exists()


def test_read_raw_returns_none_for_malformed_json(tmp_path):
    store = TaskStore(tmp_path)
    (tmp_path / "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.json").write_text(
        "{not-json",
        encoding="utf-8",
    )

    assert store.read_raw("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa") is None


def test_find_product_rejects_invalid_task_id(tmp_path):
    store = TaskStore(tmp_path)
    store.write(_result())

    assert store.find_product("../bad", "p1") is None
    assert store.find_product("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "p1").brand == "华为"


def test_find_product_returns_none_for_invalid_product_payload(tmp_path):
    store = TaskStore(tmp_path)
    store.write(_result())
    store.update("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", products=[{"id": "p1"}])

    assert store.find_product("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "p1") is None


def test_latest_completed_returns_newest_completed_task(tmp_path):
    store = TaskStore(tmp_path)
    newest_by_mtime_id = "11111111-1111-1111-1111-111111111111"
    newest_by_name_write_and_created_at_id = "22222222-2222-2222-2222-222222222222"
    newest_by_mtime = _result(newest_by_mtime_id)
    newest_by_mtime.status = "completed"
    newest_by_mtime.created_at = datetime(2024, 1, 1)
    newest_by_name_write_and_created_at = _result(newest_by_name_write_and_created_at_id)
    newest_by_name_write_and_created_at.status = "completed"
    newest_by_name_write_and_created_at.created_at = datetime(2025, 1, 1)

    store.write(newest_by_mtime)
    store.write(newest_by_name_write_and_created_at)
    os.utime(tmp_path / f"{newest_by_mtime_id}.json", (2000, 2000))
    os.utime(tmp_path / f"{newest_by_name_write_and_created_at_id}.json", (1000, 1000))

    latest = store.latest_completed()
    assert latest["task_id"] == newest_by_mtime_id


def test_latest_completed_skips_newer_malformed_json(tmp_path):
    store = TaskStore(tmp_path)
    completed_id = "11111111-1111-1111-1111-111111111111"
    corrupt_id = "22222222-2222-2222-2222-222222222222"
    completed = _result(completed_id)
    completed.status = "completed"

    store.write(completed)
    (tmp_path / f"{corrupt_id}.json").write_text("{not-json", encoding="utf-8")
    os.utime(tmp_path / f"{completed_id}.json", (1000, 1000))
    os.utime(tmp_path / f"{corrupt_id}.json", (2000, 2000))

    latest = store.latest_completed()
    assert latest["task_id"] == completed_id
