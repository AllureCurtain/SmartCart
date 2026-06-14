import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from models import Product, SearchResult


TASK_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{8,64}$")


def is_valid_task_id(task_id: str) -> bool:
    return bool(TASK_ID_PATTERN.fullmatch(task_id))


def _json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class TaskStore:
    """File-backed task persistence used by FastAPI and skills."""

    def __init__(self, root: str | Path = "data/tasks"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        if not is_valid_task_id(task_id):
            raise ValueError(f"Invalid task_id: {task_id}")
        return self.root / f"{task_id}.json"

    def _read_file(self, path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        return data

    def write(self, result: SearchResult) -> None:
        path = self._path(result.task_id)
        path.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def read_raw(self, task_id: str) -> dict[str, Any] | None:
        if not is_valid_task_id(task_id):
            return None
        path = self._path(task_id)
        if not path.exists():
            return None
        return self._read_file(path)

    def update(self, task_id: str, **changes: Any) -> None:
        data = self.read_raw(task_id)
        if data is None:
            return
        data.update(changes)
        self._path(task_id).write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def find_product(self, task_id: str, product_id: str) -> Product | None:
        data = self.read_raw(task_id)
        if data is None:
            return None
        products = data.get("products", [])
        if not isinstance(products, list):
            return None
        for product_data in products:
            if not isinstance(product_data, dict):
                continue
            if product_data.get("id") == product_id:
                try:
                    return Product(**product_data)
                except ValidationError:
                    return None
        return None

    def latest_completed(self) -> dict[str, Any] | None:
        task_files = sorted(
            self.root.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for task_file in task_files:
            data = self._read_file(task_file)
            if data is None:
                continue
            if data.get("status") == "completed":
                return data
        return None

    def count_processing(self) -> int:
        """在飞（status=processing）任务数，供并发指标展示。"""
        n = 0
        for task_file in self.root.glob("*.json"):
            data = self._read_file(task_file)
            if data is not None and data.get("status") == "processing":
                n += 1
        return n
