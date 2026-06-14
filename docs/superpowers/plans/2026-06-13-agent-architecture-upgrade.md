# Agent Architecture Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved single-user SmartCart Agent architecture upgrade with Skill registry, MCP tool exposure, memory-driven effective search, recommendation reasons, frontend trace display, tests, and documentation.

**Architecture:** FastAPI remains the mobile App API. A new `AgentRuntime` orchestrates query parsing, memory insight, conservative query adjustment, registered skill calls, product reranking, and trace generation. `SkillRegistry` is shared by FastAPI and the MCP adapter so MCP exposes real product capabilities rather than a parallel demo path.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest, `mcp.server.fastmcp.FastMCP`, React Native Expo, TypeScript.

---

## Baseline

Run from `D:\Study\project\SmartCart\.worktrees\agent-mcp-skills-evolution`.

- Backend baseline: `cd backend; python -m pytest -q`
- Current result before this plan: `18 passed, 1 warning`
- Frontend baseline: `cd app; npx tsc --noEmit`
- Current result before this plan: typecheck succeeds, npm prints only the existing `sass_binary_site` warning

## File Structure

Create:

- `backend/test_models_agent_fields.py` - regression tests for new response metadata fields.
- `backend/services/task_store.py` - file-backed task persistence and task/product lookup.
- `backend/test_task_store.py` - pure tests for task persistence.
- `backend/skills/base.py` - `Skill` base class and skill errors.
- `backend/skills/registry.py` - registration, discovery, and invocation.
- `backend/skills/__init__.py` - package marker and exports.
- `backend/test_skill_registry.py` - registry unit tests.
- `backend/skills/preference_insight.py` - memory context skill.
- `backend/skills/rerank_products.py` - product ranking and reason skill.
- `backend/test_preference_skills.py` - memory insight and rerank tests.
- `backend/skills/product_action.py` - behavior recording skill.
- `backend/test_product_action_skill.py` - action recording tests.
- `backend/skills/catalog.py` - default skill registry assembly.
- `backend/test_skill_catalog.py` - default registry smoke tests.
- `backend/services/agent_runtime.py` - search orchestration runtime.
- `backend/test_agent_runtime.py` - runtime tests with mock skills.
- `backend/mcp_adapter.py` - registry-backed MCP tool descriptions and calls.
- `backend/mcp_server.py` - FastMCP runtime entry point.
- `backend/test_mcp_server.py` - MCP adapter/server tests.
- `backend/test_main_agent_integration.py` - FastAPI integration tests with fake runtime.

Modify:

- `backend/models.py` - add trace, memory, effective query, score, and reason fields.
- `backend/skills/taobao_search.py` - make existing Taobao class a registered `Skill` while preserving `search()`.
- `backend/main.py` - delegate to `TaskStore`, `AgentRuntime`, and registry-backed action skill.
- `backend/requirements.txt` - add the official `mcp` package dependency.
- `app/package.json` - add `typecheck` script.
- `app/src/services/api.ts` - add new response fields to TypeScript types.
- `app/src/screens/HomeScreen.tsx` - render returned trace and recommendation reasons.
- `README.md` - document Agent Runtime, Skill Registry, MCP, and trace demo.
- `IMPLEMENTATION.md` - add Phase 6 status and acceptance checklist.

## Task 1: Add Agent Metadata To Models

**Files:**
- Create: `backend/test_models_agent_fields.py`
- Modify: `backend/models.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/test_models_agent_fields.py`:

```python
from datetime import datetime

from models import ParsedQuery, Product, SearchResult


def test_product_has_recommendation_metadata_defaults():
    product = Product(
        id="p1",
        title="华为 FreeBuds 蓝牙耳机",
        price=499,
        brand="华为",
        platform="taobao",
    )

    assert product.recommendation_score == 0.0
    assert product.recommendation_reason is None


def test_search_result_has_agent_metadata_defaults():
    result = SearchResult(
        task_id="task-1",
        query="蓝牙耳机",
        parsed_query=ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"]),
        products=[],
        total_count=0,
        status="processing",
        created_at=datetime.now(),
    )

    assert result.agent_trace == []
    assert result.memory_context == {}
    assert result.effective_query is None


def test_search_result_serializes_agent_metadata():
    result = SearchResult(
        task_id="task-2",
        query="我想买 500 元左右的蓝牙耳机",
        parsed_query=ParsedQuery(
            category="蓝牙耳机",
            keywords=["蓝牙耳机"],
            price_min=400,
            price_max=600,
            features=["降噪"],
        ),
        products=[
            Product(
                id="p1",
                title="华为 FreeBuds 蓝牙耳机",
                price=499,
                brand="华为",
                platform="taobao",
                recommendation_score=1.2,
                recommendation_reason="命中你常看的华为品牌",
            )
        ],
        total_count=1,
        status="completed",
        agent_trace=["解析需求 -> 蓝牙耳机 · ¥400-600"],
        memory_context={"preferred_brands": [{"brand": "华为", "score": 0.9}]},
        effective_query="蓝牙耳机 华为 降噪",
        created_at=datetime.now(),
    )

    data = result.model_dump(mode="json")
    assert data["agent_trace"] == ["解析需求 -> 蓝牙耳机 · ¥400-600"]
    assert data["memory_context"]["preferred_brands"][0]["brand"] == "华为"
    assert data["effective_query"] == "蓝牙耳机 华为 降噪"
    assert data["products"][0]["recommendation_reason"] == "命中你常看的华为品牌"
```

- [ ] **Step 2: Run model tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_models_agent_fields.py -q
```

Expected: fails because `Product` has no `recommendation_score` attribute and `SearchResult` has no `agent_trace` attribute.

- [ ] **Step 3: Update `backend/models.py`**

Change the import line:

```python
from typing import List, Optional, Dict, Any
```

Update `Product` by adding these fields after `is_demo`:

```python
    recommendation_score: float = 0.0  # 推荐分数（Memory / 当前需求综合）
    recommendation_reason: Optional[str] = None  # 推荐理由，前端展示一行
```

Update `SearchResult` by adding these fields before `created_at`:

```python
    agent_trace: List[str] = Field(default_factory=list)  # Agent 可见执行轨迹
    memory_context: Dict[str, Any] = Field(default_factory=dict)  # 本次使用的记忆上下文
    effective_query: Optional[str] = None  # 实际输入淘宝的搜索词
```

- [ ] **Step 4: Run model tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_models_agent_fields.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Run full backend baseline**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all existing tests plus `test_models_agent_fields.py` pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/models.py backend/test_models_agent_fields.py
git commit -m "feat: add agent metadata fields to search models"
```

## Task 2: Introduce TaskStore For File-Backed Task Persistence

**Files:**
- Create: `backend/services/task_store.py`
- Create: `backend/test_task_store.py`

- [ ] **Step 1: Write failing TaskStore tests**

Create `backend/test_task_store.py`:

```python
from datetime import datetime

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


def test_find_product_rejects_invalid_task_id(tmp_path):
    store = TaskStore(tmp_path)
    store.write(_result())

    assert store.find_product("../bad", "p1") is None
    assert store.find_product("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "p1").brand == "华为"


def test_latest_completed_returns_newest_completed_task(tmp_path):
    store = TaskStore(tmp_path)
    older = _result("11111111-1111-1111-1111-111111111111")
    older.status = "completed"
    newer = _result("22222222-2222-2222-2222-222222222222")
    newer.status = "completed"

    store.write(older)
    store.write(newer)

    latest = store.latest_completed()
    assert latest["task_id"] == "22222222-2222-2222-2222-222222222222"
```

- [ ] **Step 2: Run TaskStore tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_task_store.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'services.task_store'`.

- [ ] **Step 3: Implement `backend/services/task_store.py`**

Create `backend/services/task_store.py`:

```python
import json
import re
from pathlib import Path
from typing import Any

from models import Product, SearchResult


TASK_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{8,64}$")


def is_valid_task_id(task_id: str) -> bool:
    return bool(TASK_ID_PATTERN.fullmatch(task_id))


class TaskStore:
    """File-backed task persistence used by FastAPI and skills."""

    def __init__(self, root: str | Path = "data/tasks"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self.root / f"{task_id}.json"

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
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, task_id: str, **changes: Any) -> None:
        data = self.read_raw(task_id)
        if data is None:
            return
        data.update(changes)
        self._path(task_id).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def find_product(self, task_id: str, product_id: str) -> Product | None:
        data = self.read_raw(task_id)
        if data is None:
            return None
        for product_data in data.get("products", []):
            if product_data.get("id") == product_id:
                return Product(**product_data)
        return None

    def latest_completed(self) -> dict[str, Any] | None:
        task_files = sorted(
            self.root.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for task_file in task_files:
            data = json.loads(task_file.read_text(encoding="utf-8"))
            if data.get("status") == "completed":
                return data
        return None
```

- [ ] **Step 4: Run TaskStore tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_task_store.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/services/task_store.py backend/test_task_store.py
git commit -m "feat: add file backed task store"
```

## Task 3: Add Skill Base And Registry

**Files:**
- Create: `backend/skills/base.py`
- Create: `backend/skills/registry.py`
- Create: `backend/skills/__init__.py`
- Create: `backend/test_skill_registry.py`

- [ ] **Step 1: Write failing registry tests**

Create `backend/test_skill_registry.py`:

```python
from typing import Any

import pytest

from skills.base import Skill, SkillRegistrationError, SkillNotFoundError
from skills.registry import SkillRegistry


class EchoSkill(Skill):
    name = "echo"
    description = "Return the input text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, **kwargs: Any) -> dict[str, str]:
        return {"text": kwargs["text"]}


def test_register_describe_and_invoke_skill():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    descriptions = registry.describe_tools()
    assert descriptions == [
        {
            "name": "echo",
            "description": "Return the input text.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }
    ]
    assert registry.invoke("echo", text="hello") == {"text": "hello"}


def test_duplicate_skill_name_is_rejected():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    with pytest.raises(SkillRegistrationError, match="already registered"):
        registry.register(EchoSkill())


def test_unknown_skill_raises_clear_error():
    registry = SkillRegistry()

    with pytest.raises(SkillNotFoundError, match="unknown"):
        registry.invoke("unknown")


def test_invalid_skill_without_name_is_rejected():
    class NamelessSkill(EchoSkill):
        name = ""

    registry = SkillRegistry()

    with pytest.raises(SkillRegistrationError, match="non-empty name"):
        registry.register(NamelessSkill())
```

- [ ] **Step 2: Run registry tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_skill_registry.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'skills.base'`.

- [ ] **Step 3: Implement skill base**

Create `backend/skills/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Any


class SkillError(Exception):
    """Base exception for skill infrastructure failures."""


class SkillRegistrationError(SkillError):
    """Raised when a skill cannot be registered."""


class SkillNotFoundError(SkillError):
    """Raised when a caller asks for an unknown skill."""


class Skill(ABC):
    """A discoverable capability that can be invoked by AgentRuntime or MCP."""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {"type": "object", "properties": {}}

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
```

- [ ] **Step 4: Implement registry**

Create `backend/skills/registry.py`:

```python
from typing import Any, Iterable

from skills.base import Skill, SkillNotFoundError, SkillRegistrationError


class SkillRegistry:
    """Registry for discoverable Agent skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if not skill.name:
            raise SkillRegistrationError("Skill must have a non-empty name")
        if skill.name in self._skills:
            raise SkillRegistrationError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill

    def register_many(self, skills: Iterable[Skill]) -> None:
        for skill in skills:
            self.register(skill)

    def get(self, name: str) -> Skill:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillNotFoundError(f"Unknown skill: {name}") from exc

    def invoke(self, name: str, **kwargs: Any) -> Any:
        return self.get(name).run(**kwargs)

    def describe_tools(self) -> list[dict[str, Any]]:
        return [self._skills[name].describe() for name in sorted(self._skills)]

    def names(self) -> list[str]:
        return sorted(self._skills)
```

- [ ] **Step 5: Add package exports**

Create `backend/skills/__init__.py`:

```python
from skills.base import Skill, SkillError, SkillNotFoundError, SkillRegistrationError
from skills.registry import SkillRegistry

__all__ = [
    "Skill",
    "SkillError",
    "SkillNotFoundError",
    "SkillRegistrationError",
    "SkillRegistry",
]
```

- [ ] **Step 6: Run registry tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_skill_registry.py -q
```

Expected: `4 passed`.

- [ ] **Step 7: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```powershell
git add backend/skills/base.py backend/skills/registry.py backend/skills/__init__.py backend/test_skill_registry.py
git commit -m "feat: add skill base and registry"
```

## Task 4: Add Preference Insight And Rerank Skills

**Files:**
- Create: `backend/skills/preference_insight.py`
- Create: `backend/skills/rerank_products.py`
- Create: `backend/test_preference_skills.py`

- [ ] **Step 1: Write failing preference skill tests**

Create `backend/test_preference_skills.py`:

```python
from datetime import datetime

from models import BrandPreference, ParsedQuery, PricePreference, Product
from services.preference_service import PreferenceService
from skills.preference_insight import PreferenceInsightSkill
from skills.rerank_products import RerankProductsSkill


def _product(pid: str, title: str, price: float, brand: str | None = None) -> Product:
    return Product(id=pid, title=title, price=price, brand=brand, platform="taobao")


def test_preference_insight_returns_compact_memory_context(tmp_path):
    service = PreferenceService(storage_path=str(tmp_path))
    pref = service.get_preference("default")
    pref.brand_preferences["华为"] = BrandPreference(
        brand="华为", score=0.9, count=3, last_updated=datetime.now()
    )
    pref.price_preference = PricePreference(min=400, max=600, avg=500, median=500)
    pref.feature_preferences["降噪"] = 0.8
    pref.search_history = ["蓝牙耳机", "降噪耳机"]
    service.save_preference(pref)

    insight = PreferenceInsightSkill(service).run(user_id="default")

    assert insight["has_memory"] is True
    assert insight["preferred_brands"][0] == {"brand": "华为", "score": 0.9, "count": 3}
    assert insight["price_range"] == {"min": 400, "max": 600, "avg": 500}
    assert insight["preferred_features"][0] == {"feature": "降噪", "score": 0.8}
    assert insight["recent_searches"] == ["蓝牙耳机", "降噪耳机"]


def test_preference_insight_empty_memory_is_valid(tmp_path):
    service = PreferenceService(storage_path=str(tmp_path))

    insight = PreferenceInsightSkill(service).run(user_id="new-user")

    assert insight == {
        "has_memory": False,
        "preferred_brands": [],
        "price_range": None,
        "preferred_features": [],
        "recent_searches": [],
    }


def test_rerank_products_adds_scores_and_reasons(tmp_path):
    service = PreferenceService(storage_path=str(tmp_path))
    pref = service.get_preference("default")
    pref.brand_preferences["华为"] = BrandPreference(
        brand="华为", score=0.9, count=3, last_updated=datetime.now()
    )
    pref.price_preference = PricePreference(min=400, max=600, avg=500, median=500)
    pref.feature_preferences["降噪"] = 0.8
    service.save_preference(pref)

    products = [
        _product("plain", "普通蓝牙耳机", 199, "其他"),
        _product("hw", "华为主动降噪蓝牙耳机", 499, "华为"),
    ]
    parsed = ParsedQuery(
        category="蓝牙耳机",
        keywords=["蓝牙耳机"],
        price_min=400,
        price_max=600,
        features=["降噪"],
    )

    result = RerankProductsSkill(service).run(
        user_id="default",
        products=products,
        parsed_query=parsed,
        memory_context={},
    )

    assert result["products"][0].id == "hw"
    assert result["products"][0].recommendation_score > 0
    assert "华为" in result["products"][0].recommendation_reason
    assert result["matched_count"] == 1
```

- [ ] **Step 2: Run preference skill tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_preference_skills.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'skills.preference_insight'`.

- [ ] **Step 3: Implement `PreferenceInsightSkill`**

Create `backend/skills/preference_insight.py`:

```python
from typing import Any

from services.preference_service import PreferenceService
from skills.base import Skill


class PreferenceInsightSkill(Skill):
    name = "get_preference_insight"
    description = "Read learned shopping preferences and return compact memory context."
    parameters = {
        "type": "object",
        "properties": {"user_id": {"type": "string"}},
        "required": ["user_id"],
    }

    def __init__(self, preference_service: PreferenceService):
        self.preference_service = preference_service

    def run(self, **kwargs: Any) -> dict[str, Any]:
        user_id = kwargs["user_id"]
        pref = self.preference_service.get_preference(user_id)

        preferred_brands = [
            {"brand": item.brand, "score": item.score, "count": item.count}
            for item in sorted(
                pref.brand_preferences.values(),
                key=lambda brand_pref: brand_pref.score,
                reverse=True,
            )
        ][:3]

        preferred_features = [
            {"feature": feature, "score": score}
            for feature, score in sorted(
                pref.feature_preferences.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ][:3]

        price_range = None
        if pref.price_preference:
            price_range = {
                "min": pref.price_preference.min,
                "max": pref.price_preference.max,
                "avg": pref.price_preference.avg,
            }

        recent_searches = pref.search_history[-5:]

        return {
            "has_memory": bool(preferred_brands or preferred_features or price_range or recent_searches),
            "preferred_brands": preferred_brands,
            "price_range": price_range,
            "preferred_features": preferred_features,
            "recent_searches": recent_searches,
        }
```

- [ ] **Step 4: Implement `RerankProductsSkill`**

Create `backend/skills/rerank_products.py`:

```python
from typing import Any

from models import ParsedQuery, Product
from services.preference_service import PreferenceService
from skills.base import Skill


def _coerce_parsed_query(value: ParsedQuery | dict[str, Any]) -> ParsedQuery:
    if isinstance(value, ParsedQuery):
        return value
    return ParsedQuery(**value)


class RerankProductsSkill(Skill):
    name = "rerank_products"
    description = "Rerank products with learned memory and current intent, returning reasons."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "products": {"type": "array"},
            "parsed_query": {"type": "object"},
            "memory_context": {"type": "object"},
        },
        "required": ["user_id", "products", "parsed_query"],
    }

    def __init__(self, preference_service: PreferenceService):
        self.preference_service = preference_service

    def run(self, **kwargs: Any) -> dict[str, Any]:
        user_id = kwargs["user_id"]
        parsed_query = _coerce_parsed_query(kwargs["parsed_query"])
        raw_products = kwargs.get("products", [])
        products = [
            product if isinstance(product, Product) else Product(**product)
            for product in raw_products
        ]
        pref = self.preference_service.get_preference(user_id)

        scored: list[Product] = []
        matched_count = 0
        for product in products:
            score, reasons = self._score_product(product, parsed_query, pref)
            product.recommendation_score = round(score, 4)
            product.recommendation_reason = self._format_reason(reasons, score)
            if score > 0:
                matched_count += 1
            scored.append(product)

        return {
            "products": sorted(scored, key=lambda item: item.recommendation_score, reverse=True),
            "matched_count": matched_count,
        }

    def _score_product(self, product: Product, parsed_query: ParsedQuery, pref) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        if product.brand and product.brand in pref.brand_preferences:
            brand_score = pref.brand_preferences[product.brand].score
            score += brand_score
            reasons.append(f"命中你常看的{product.brand}品牌")

        for feature, weight in pref.feature_preferences.items():
            if feature and feature in product.title:
                score += weight
                reasons.append(f"标题包含你常关注的{feature}特性")

        if parsed_query.price_min is not None and parsed_query.price_max is not None:
            if parsed_query.price_min <= product.price <= parsed_query.price_max:
                score += 0.25
                reasons.append("价格接近本次预算")
        elif pref.price_preference and pref.price_preference.min <= product.price <= pref.price_preference.max:
            score += 0.2
            reasons.append(
                f"价格接近你最近偏好的 {pref.price_preference.min:.0f}-{pref.price_preference.max:.0f} 元区间"
            )

        return score, reasons

    @staticmethod
    def _format_reason(reasons: list[str], score: float) -> str | None:
        if reasons:
            return "；".join(reasons[:2])
        if score == 0:
            return "探索项：保留原始搜索结果"
        return "根据你的偏好排序"
```

- [ ] **Step 5: Run preference skill tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_preference_skills.py -q
```

Expected: `3 passed`.

- [ ] **Step 6: Run existing preference ranking tests**

Run:

```powershell
cd backend
python -m pytest test_preference_ranking.py test_preference_skills.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/skills/preference_insight.py backend/skills/rerank_products.py backend/test_preference_skills.py
git commit -m "feat: add memory insight and rerank skills"
```

## Task 5: Add Product Action Skill

**Files:**
- Create: `backend/skills/product_action.py`
- Create: `backend/test_product_action_skill.py`

- [ ] **Step 1: Write failing product action tests**

Create `backend/test_product_action_skill.py`:

```python
from datetime import datetime

from models import ParsedQuery, Product, SearchResult
from services.preference_service import PreferenceService
from services.task_store import TaskStore
from skills.product_action import RecordProductActionSkill


def _write_task(store: TaskStore, product: Product) -> str:
    task_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    store.write(
        SearchResult(
            task_id=task_id,
            query="蓝牙耳机",
            parsed_query=ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"]),
            products=[product],
            total_count=1,
            status="completed",
            created_at=datetime.now(),
        )
    )
    return task_id


def test_record_click_updates_brand_preference(tmp_path):
    task_store = TaskStore(tmp_path / "tasks")
    preference_service = PreferenceService(storage_path=str(tmp_path / "prefs"))
    task_id = _write_task(
        task_store,
        Product(id="p1", title="华为 FreeBuds", price=499, brand="华为", platform="taobao"),
    )

    result = RecordProductActionSkill(preference_service, task_store).run(
        user_id="default",
        action_type="click",
        task_id=task_id,
        product_id="p1",
    )

    pref = preference_service.get_preference("default")
    assert result["success"] is True
    assert pref.brand_preferences["华为"].score == 0.3


def test_demo_product_is_not_recorded(tmp_path):
    task_store = TaskStore(tmp_path / "tasks")
    preference_service = PreferenceService(storage_path=str(tmp_path / "prefs"))
    task_id = _write_task(
        task_store,
        Product(
            id="p1",
            title="演示商品",
            price=99,
            brand="DemoBrand",
            platform="taobao",
            is_demo=True,
        ),
    )

    result = RecordProductActionSkill(preference_service, task_store).run(
        user_id="default",
        action_type="click",
        task_id=task_id,
        product_id="p1",
    )

    assert result == {"success": False, "error": "演示数据不记录偏好"}
    assert preference_service.get_preference("default").brand_preferences == {}
```

- [ ] **Step 2: Run product action tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_product_action_skill.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'skills.product_action'`.

- [ ] **Step 3: Implement `RecordProductActionSkill`**

Create `backend/skills/product_action.py`:

```python
from typing import Any

from services.preference_service import PreferenceService
from services.task_store import TaskStore
from skills.base import Skill


class RecordProductActionSkill(Skill):
    name = "record_product_action"
    description = "Record product view or click behavior into preference memory."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "action_type": {"type": "string", "enum": ["view", "click"]},
            "task_id": {"type": "string"},
            "product_id": {"type": "string"},
        },
        "required": ["user_id", "action_type", "task_id", "product_id"],
    }

    def __init__(self, preference_service: PreferenceService, task_store: TaskStore):
        self.preference_service = preference_service
        self.task_store = task_store

    def run(self, **kwargs: Any) -> dict[str, Any]:
        action_type = kwargs["action_type"]
        if action_type not in ("view", "click"):
            return {"success": False, "error": f"不支持的行为类型: {action_type}"}

        product = self.task_store.find_product(kwargs["task_id"], kwargs["product_id"])
        if product is None:
            return {"success": False, "error": "未找到对应商品"}
        if product.is_demo:
            return {"success": False, "error": "演示数据不记录偏好"}

        if action_type == "click":
            self.preference_service.record_product_click(kwargs["user_id"], product)
        else:
            self.preference_service.record_product_view(kwargs["user_id"], product)

        return {
            "success": True,
            "message": f"已记录 {action_type} 行为: {product.title[:20]}",
        }
```

- [ ] **Step 4: Run product action tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_product_action_skill.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/skills/product_action.py backend/test_product_action_skill.py
git commit -m "feat: add product action skill"
```

## Task 6: Register Existing Taobao Search As A Skill And Add Catalog

**Files:**
- Modify: `backend/skills/taobao_search.py`
- Create: `backend/skills/catalog.py`
- Create: `backend/test_skill_catalog.py`
- Modify: `backend/test_taobao_parsing.py`

- [ ] **Step 1: Add failing tests for Taobao skill metadata and catalog**

Append to `backend/test_taobao_parsing.py`:

```python
class TestTaobaoSkillContract:
    def test_taobao_skill_describes_mcp_compatible_contract(self):
        skill = TaobaoSearchSkill(demo_mode=True)

        description = skill.describe()

        assert description["name"] == "taobao_search"
        assert "keyword" in description["parameters"]["properties"]
        assert "max_products" in description["parameters"]["properties"]

    def test_taobao_skill_run_delegates_to_search(self):
        skill = TaobaoSearchSkill(demo_mode=True)

        products = skill.run(keyword="蓝牙耳机", max_products=2)

        assert len(products) == 2
        assert all(product.is_demo for product in products)
```

Create `backend/test_skill_catalog.py`:

```python
from services.preference_service import PreferenceService
from services.task_store import TaskStore
from skills.catalog import create_default_registry
from skills.taobao_search import TaobaoSearchSkill


def test_default_registry_contains_product_skills(tmp_path):
    registry = create_default_registry(
        preference_service=PreferenceService(storage_path=str(tmp_path / "prefs")),
        task_store=TaskStore(tmp_path / "tasks"),
        taobao_skill=TaobaoSearchSkill(demo_mode=True),
    )

    assert registry.names() == [
        "get_preference_insight",
        "record_product_action",
        "rerank_products",
        "taobao_search",
    ]
```

- [ ] **Step 2: Run new catalog tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_taobao_parsing.py::TestTaobaoSkillContract test_skill_catalog.py -q
```

Expected: fails because `TaobaoSearchSkill` does not inherit `Skill` and `skills.catalog` does not exist.

- [ ] **Step 3: Update `TaobaoSearchSkill` contract**

In `backend/skills/taobao_search.py`, add this import near the existing model import:

```python
from skills.base import Skill
```

Change the class definition and add class attributes:

```python
class TaobaoSearchSkill(Skill):
    """淘宝搜索技能"""

    name = "taobao_search"
    description = "Control Taobao on a connected Android phone and extract products from the result screenshot."
    parameters = {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "Search keyword to input into Taobao."},
            "max_products": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
        },
        "required": ["keyword"],
    }
```

Add this method directly before `search()`:

```python
    def run(self, **kwargs):
        return self.search(
            kwargs["keyword"],
            max_products=kwargs.get("max_products", 10),
            on_progress=kwargs.get("on_progress"),
        )
```

- [ ] **Step 4: Implement default registry catalog**

Create `backend/skills/catalog.py`:

```python
from services.preference_service import PreferenceService
from services.task_store import TaskStore
from skills.preference_insight import PreferenceInsightSkill
from skills.product_action import RecordProductActionSkill
from skills.registry import SkillRegistry
from skills.rerank_products import RerankProductsSkill
from skills.taobao_search import TaobaoSearchSkill


def create_default_registry(
    preference_service: PreferenceService | None = None,
    task_store: TaskStore | None = None,
    taobao_skill: TaobaoSearchSkill | None = None,
) -> SkillRegistry:
    preference_service = preference_service or PreferenceService()
    task_store = task_store or TaskStore()
    registry = SkillRegistry()
    registry.register_many(
        [
            taobao_skill or TaobaoSearchSkill(),
            PreferenceInsightSkill(preference_service),
            RecordProductActionSkill(preference_service, task_store),
            RerankProductsSkill(preference_service),
        ]
    )
    return registry
```

- [ ] **Step 5: Run catalog and Taobao contract tests**

Run:

```powershell
cd backend
python -m pytest test_taobao_parsing.py::TestTaobaoSkillContract test_skill_catalog.py -q
```

Expected: `3 passed`.

- [ ] **Step 6: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/skills/taobao_search.py backend/skills/catalog.py backend/test_taobao_parsing.py backend/test_skill_catalog.py
git commit -m "feat: register taobao search in skill catalog"
```

## Task 7: Add AgentRuntime

**Files:**
- Create: `backend/services/agent_runtime.py`
- Create: `backend/test_agent_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

Create `backend/test_agent_runtime.py`:

```python
from typing import Any

from models import ParsedQuery, Product, SearchRequest
from services.agent_runtime import AgentRuntime
from skills.base import Skill
from skills.registry import SkillRegistry


class FakeParser:
    def parse(self, query: str) -> ParsedQuery:
        return ParsedQuery(
            category="蓝牙耳机",
            keywords=["蓝牙耳机"],
            price_min=400,
            price_max=600,
            features=["降噪"],
        )


class FakePreferenceService:
    def __init__(self):
        self.recorded = []

    def record_search(self, user_id, query, parsed_query):
        self.recorded.append((user_id, query, parsed_query.category))


class MemorySkill(Skill):
    name = "get_preference_insight"
    description = "memory"
    parameters = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "has_memory": True,
            "preferred_brands": [{"brand": "华为", "score": 0.9, "count": 3}],
            "preferred_features": [{"feature": "降噪", "score": 0.8}],
            "price_range": {"min": 400, "max": 600, "avg": 500},
            "recent_searches": ["蓝牙耳机"],
        }


class SearchSkill(Skill):
    name = "taobao_search"
    description = "search"
    parameters = {"type": "object", "properties": {}}

    def __init__(self):
        self.keywords = []

    def run(self, **kwargs: Any):
        self.keywords.append(kwargs["keyword"])
        return [
            Product(id="p1", title="普通蓝牙耳机", price=199, brand="其他", platform="taobao"),
            Product(id="p2", title="华为主动降噪蓝牙耳机", price=499, brand="华为", platform="taobao"),
        ]


class RerankSkill(Skill):
    name = "rerank_products"
    description = "rerank"
    parameters = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any):
        products = list(kwargs["products"])
        products[1].recommendation_score = 1.95
        products[1].recommendation_reason = "命中你常看的华为品牌；标题包含你常关注的降噪特性"
        return {"products": [products[1], products[0]], "matched_count": 1}


def _runtime():
    registry = SkillRegistry()
    search_skill = SearchSkill()
    registry.register_many([MemorySkill(), search_skill, RerankSkill()])
    preference_service = FakePreferenceService()
    return AgentRuntime(FakeParser(), registry, preference_service), search_skill, preference_service


def test_prepare_search_builds_effective_query_and_trace():
    runtime, _, _ = _runtime()

    prepared = runtime.prepare_search(
        SearchRequest(query="我想买 500 元左右的蓝牙耳机", user_id="default")
    )

    assert prepared.effective_query == "蓝牙耳机 华为 降噪"
    assert prepared.agent_trace == [
        "解析需求 -> 蓝牙耳机 · ¥400-600 · 降噪",
        "读取记忆 -> 偏好 华为 / 降噪",
        "调整搜索 -> 蓝牙耳机 华为 降噪",
    ]


def test_user_explicit_exclusion_blocks_memory_brand_injection():
    runtime, _, _ = _runtime()

    prepared = runtime.prepare_search(
        SearchRequest(query="我想买 500 元左右的蓝牙耳机，不要华为", user_id="default")
    )

    assert prepared.effective_query == "蓝牙耳机 降噪"


def test_execute_search_calls_skills_and_returns_result_with_reasons():
    runtime, search_skill, preference_service = _runtime()
    request = SearchRequest(query="我想买 500 元左右的蓝牙耳机", user_id="default")
    prepared = runtime.prepare_search(request)
    progress = []

    result = runtime.execute_search(
        task_id="task-1",
        request=request,
        prepared=prepared,
        max_products=10,
        on_progress=lambda stage, trace: progress.append((stage, list(trace))),
    )

    assert search_skill.keywords == ["蓝牙耳机 华为 降噪"]
    assert result.status == "completed"
    assert result.products[0].id == "p2"
    assert result.products[0].recommendation_reason.startswith("命中你常看的华为品牌")
    assert result.agent_trace[-2] == "调用工具 -> taobao_search"
    assert result.agent_trace[-1] == "推荐排序 -> 2 个商品，1 个命中偏好"
    assert progress[-1][0] == "ranking"
    assert preference_service.recorded == [("default", "我想买 500 元左右的蓝牙耳机", "蓝牙耳机")]
```

- [ ] **Step 2: Run runtime tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_agent_runtime.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'services.agent_runtime'`.

- [ ] **Step 3: Implement `AgentRuntime`**

Create `backend/services/agent_runtime.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from models import ParsedQuery, SearchRequest, SearchResult
from services.preference_service import PreferenceService
from skills.registry import SkillRegistry


ProgressCallback = Callable[[str, list[str]], None]


@dataclass
class PreparedSearch:
    parsed_query: ParsedQuery
    memory_context: dict[str, Any]
    effective_query: str
    agent_trace: list[str]


class AgentRuntime:
    def __init__(
        self,
        query_parser,
        registry: SkillRegistry,
        preference_service: PreferenceService,
    ):
        self.query_parser = query_parser
        self.registry = registry
        self.preference_service = preference_service

    def prepare_search(self, request: SearchRequest) -> PreparedSearch:
        parsed_query = self.query_parser.parse(request.query)
        memory_context = self.registry.invoke("get_preference_insight", user_id=request.user_id)
        effective_query = self.build_effective_query(request.query, parsed_query, memory_context)

        agent_trace = [
            f"解析需求 -> {self._summarize_parsed_query(parsed_query)}",
            f"读取记忆 -> {self._summarize_memory(memory_context)}",
            f"调整搜索 -> {effective_query}",
        ]
        return PreparedSearch(
            parsed_query=parsed_query,
            memory_context=memory_context,
            effective_query=effective_query,
            agent_trace=agent_trace,
        )

    def execute_search(
        self,
        task_id: str,
        request: SearchRequest,
        prepared: PreparedSearch,
        max_products: int = 10,
        on_progress: ProgressCallback | None = None,
    ) -> SearchResult:
        trace = list(prepared.agent_trace)

        def notify(stage: str) -> None:
            if on_progress:
                on_progress(stage, trace)

        trace.append("调用工具 -> taobao_search")
        notify("controlling_phone")
        products = self.registry.invoke(
            "taobao_search",
            keyword=prepared.effective_query,
            max_products=max_products,
            on_progress=lambda stage: notify(stage),
        )

        notify("ranking")
        reranked = self.registry.invoke(
            "rerank_products",
            user_id=request.user_id,
            products=products,
            parsed_query=prepared.parsed_query,
            memory_context=prepared.memory_context,
        )
        products = reranked["products"]
        matched_count = reranked.get("matched_count", 0)
        trace.append(f"推荐排序 -> {len(products)} 个商品，{matched_count} 个命中偏好")

        self.preference_service.record_search(request.user_id, request.query, prepared.parsed_query)

        return SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=prepared.parsed_query,
            products=products,
            total_count=len(products),
            status="completed",
            is_demo=any(product.is_demo for product in products),
            agent_trace=trace,
            memory_context=prepared.memory_context,
            effective_query=prepared.effective_query,
            created_at=datetime.now(),
        )

    def build_effective_query(
        self,
        raw_query: str,
        parsed_query: ParsedQuery,
        memory_context: dict[str, Any],
    ) -> str:
        parts = [parsed_query.category.strip()]

        brand = self._select_brand(raw_query, memory_context)
        if brand and brand not in parts[0]:
            parts.append(brand)

        feature = self._select_feature(memory_context)
        if feature and feature not in " ".join(parts):
            parts.append(feature)

        return " ".join(part for part in parts if part).strip()

    def _select_brand(self, raw_query: str, memory_context: dict[str, Any]) -> str | None:
        if any(token in raw_query for token in ("不限品牌", "随便看看", "都可以", "任意品牌")):
            return None
        for item in memory_context.get("preferred_brands", []):
            brand = item.get("brand")
            score = float(item.get("score", 0))
            if brand and score >= 0.5 and f"不要{brand}" not in raw_query and f"不买{brand}" not in raw_query:
                return brand
        return None

    @staticmethod
    def _select_feature(memory_context: dict[str, Any]) -> str | None:
        for item in memory_context.get("preferred_features", []):
            feature = item.get("feature")
            score = float(item.get("score", 0))
            if feature and score >= 0.5:
                return feature
        return None

    @staticmethod
    def _summarize_parsed_query(parsed_query: ParsedQuery) -> str:
        parts = [parsed_query.category]
        if parsed_query.price_min is not None or parsed_query.price_max is not None:
            price_min = "?" if parsed_query.price_min is None else f"{parsed_query.price_min:.0f}"
            price_max = "?" if parsed_query.price_max is None else f"{parsed_query.price_max:.0f}"
            parts.append(f"¥{price_min}-{price_max}")
        if parsed_query.features:
            parts.append("/".join(parsed_query.features))
        return " · ".join(part for part in parts if part)

    @staticmethod
    def _summarize_memory(memory_context: dict[str, Any]) -> str:
        brands = [item["brand"] for item in memory_context.get("preferred_brands", [])[:1]]
        features = [item["feature"] for item in memory_context.get("preferred_features", [])[:1]]
        labels = brands + features
        if not labels:
            return "暂无可用偏好"
        return f"偏好 {' / '.join(labels)}"
```

- [ ] **Step 4: Run runtime tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_agent_runtime.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/services/agent_runtime.py backend/test_agent_runtime.py
git commit -m "feat: add agent runtime orchestration"
```

## Task 8: Add MCP Adapter And Server Entry Point

**Files:**
- Create: `backend/mcp_adapter.py`
- Create: `backend/mcp_server.py`
- Create: `backend/test_mcp_server.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add MCP dependency**

Append this line to `backend/requirements.txt`:

```text
mcp>=1.27.0
```

Run:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Expected: `mcp` is installed or already satisfied.

- [ ] **Step 2: Write failing MCP tests**

Create `backend/test_mcp_server.py`:

```python
from typing import Any

from mcp_adapter import call_registry_tool, list_registry_tools, to_jsonable
from mcp_server import create_mcp_server
from models import Product
from skills.base import Skill
from skills.registry import SkillRegistry


class EchoSkill(Skill):
    name = "echo"
    description = "Echo input text."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, **kwargs: Any):
        return {"text": kwargs["text"]}


def test_list_registry_tools_uses_skill_descriptions():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    tools = list_registry_tools(registry)

    assert tools == [
        {
            "name": "echo",
            "description": "Echo input text.",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }
    ]


def test_call_registry_tool_forwards_arguments():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    assert call_registry_tool(registry, "echo", {"text": "hello"}) == {"text": "hello"}


def test_to_jsonable_handles_pydantic_models():
    product = Product(id="p1", title="蓝牙耳机", price=199, platform="taobao")

    assert to_jsonable(product)["title"] == "蓝牙耳机"


def test_create_mcp_server_returns_fastmcp_instance():
    registry = SkillRegistry()
    registry.register(EchoSkill())

    server = create_mcp_server(registry)

    assert hasattr(server, "run")
```

- [ ] **Step 3: Run MCP tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_mcp_server.py -q
```

Expected: fails because `mcp_adapter.py` and `mcp_server.py` do not exist.

- [ ] **Step 4: Implement MCP adapter**

Create `backend/mcp_adapter.py`:

```python
from typing import Any

from pydantic import BaseModel

from skills.registry import SkillRegistry


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


def list_registry_tools(registry: SkillRegistry) -> list[dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "description": item["description"],
            "inputSchema": item["parameters"],
        }
        for item in registry.describe_tools()
    ]


def call_registry_tool(
    registry: SkillRegistry,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> Any:
    return to_jsonable(registry.invoke(name, **(arguments or {})))
```

- [ ] **Step 5: Implement MCP server entry point**

Create `backend/mcp_server.py`:

```python
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_adapter import call_registry_tool, list_registry_tools
from skills.catalog import create_default_registry
from skills.registry import SkillRegistry


def create_mcp_server(registry: SkillRegistry | None = None) -> FastMCP:
    registry = registry or create_default_registry()
    server = FastMCP("SmartCart")

    for tool in list_registry_tools(registry):
        tool_name = tool["name"]
        description = tool["description"]

        def make_handler(name: str):
            def handler(arguments: dict[str, Any] | None = None):
                return call_registry_tool(registry, name, arguments or {})

            handler.__name__ = f"{name}_handler"
            return handler

        server.add_tool(make_handler(tool_name), name=tool_name, description=description)

    return server


def main() -> None:
    create_mcp_server().run("stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run MCP tests to verify pass**

Run:

```powershell
cd backend
python -m pytest test_mcp_server.py -q
```

Expected: `4 passed`.

- [ ] **Step 7: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```powershell
git add backend/requirements.txt backend/mcp_adapter.py backend/mcp_server.py backend/test_mcp_server.py
git commit -m "feat: expose skill registry through mcp"
```

## Task 9: Integrate AgentRuntime Into FastAPI

**Files:**
- Modify: `backend/main.py`
- Create: `backend/test_main_agent_integration.py`
- Modify: `backend/test_latest_task_api.py`

- [ ] **Step 1: Write failing FastAPI integration tests**

Create `backend/test_main_agent_integration.py`:

```python
from datetime import datetime

from fastapi.testclient import TestClient

import main
from models import ParsedQuery, Product, SearchResult
from services.agent_runtime import PreparedSearch
from services.task_store import TaskStore


class FakeRuntime:
    def __init__(self):
        self.executed = []

    def prepare_search(self, request):
        return PreparedSearch(
            parsed_query=ParsedQuery(
                category="蓝牙耳机",
                keywords=["蓝牙耳机"],
                price_min=400,
                price_max=600,
                features=["降噪"],
            ),
            memory_context={"preferred_brands": [{"brand": "华为", "score": 0.9}]},
            effective_query="蓝牙耳机 华为 降噪",
            agent_trace=[
                "解析需求 -> 蓝牙耳机 · ¥400-600 · 降噪",
                "读取记忆 -> 偏好 华为 / 降噪",
                "调整搜索 -> 蓝牙耳机 华为 降噪",
            ],
        )

    def execute_search(self, task_id, request, prepared, max_products=10, on_progress=None):
        self.executed.append((task_id, prepared.effective_query))
        if on_progress:
            on_progress("ranking", prepared.agent_trace)
        return SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=prepared.parsed_query,
            products=[
                Product(
                    id="p1",
                    title="华为 FreeBuds",
                    price=499,
                    brand="华为",
                    platform="taobao",
                    recommendation_score=1.0,
                    recommendation_reason="命中你常看的华为品牌",
                )
            ],
            total_count=1,
            status="completed",
            agent_trace=prepared.agent_trace + [
                "调用工具 -> taobao_search",
                "推荐排序 -> 1 个商品，1 个命中偏好",
            ],
            memory_context=prepared.memory_context,
            effective_query=prepared.effective_query,
            created_at=datetime.now(),
        )


class FakeRegistry:
    def invoke(self, name, **kwargs):
        assert name == "record_product_action"
        return {"success": True, "message": "已记录 click 行为: 华为 FreeBuds"}


def test_search_endpoint_writes_agent_metadata(tmp_path):
    original_store = main.task_store
    original_runtime = main.agent_runtime
    main.task_store = TaskStore(tmp_path)
    main.agent_runtime = FakeRuntime()
    try:
        response = TestClient(main.app).post(
            "/api/search",
            json={"query": "我想买 500 元左右的蓝牙耳机", "user_id": "default"},
        )
        body = response.json()
        task_id = body["data"]["task_id"]
        stored = main.task_store.read_raw(task_id)
    finally:
        main.task_store = original_store
        main.agent_runtime = original_runtime

    assert body["success"] is True
    assert body["data"]["parsed_query"]["category"] == "蓝牙耳机"
    assert body["data"]["effective_query"] == "蓝牙耳机 华为 降噪"
    assert stored["status"] == "completed"
    assert stored["agent_trace"][-1] == "推荐排序 -> 1 个商品，1 个命中偏好"
    assert stored["products"][0]["recommendation_reason"] == "命中你常看的华为品牌"


def test_record_action_endpoint_delegates_to_registry():
    original_registry = main.skill_registry
    main.skill_registry = FakeRegistry()
    try:
        response = TestClient(main.app).post(
            "/api/preference/action",
            json={
                "user_id": "default",
                "action_type": "click",
                "product_id": "p1",
                "task_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "timestamp": "2026-06-13T00:00:00",
            },
        )
    finally:
        main.skill_registry = original_registry

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "已记录 click 行为: 华为 FreeBuds"
```

- [ ] **Step 2: Run FastAPI integration tests to verify failure**

Run:

```powershell
cd backend
python -m pytest test_main_agent_integration.py -q
```

Expected: fails because `main` has no `task_store`, `agent_runtime`, or `skill_registry` globals.

- [ ] **Step 3: Update imports and service initialization in `main.py`**

Replace direct service imports and globals with this block:

```python
from services.query_parser import QueryParserService
from services.preference_service import PreferenceService
from services.task_store import TaskStore, is_valid_task_id
from services.agent_runtime import AgentRuntime, PreparedSearch
from skills.catalog import create_default_registry
```

Replace the current service initialization and `TASKS_DIR` block with:

```python
# 初始化服务
TASKS_DIR = Path("data/tasks")
preference_service = PreferenceService()
task_store = TaskStore(TASKS_DIR)
skill_registry = create_default_registry(
    preference_service=preference_service,
    task_store=task_store,
)
query_parser = QueryParserService()
agent_runtime = AgentRuntime(
    query_parser=query_parser,
    registry=skill_registry,
    preference_service=preference_service,
)
```

Remove the old `TASK_ID_PATTERN`, `write_task`, `update_task_progress`, and `find_product_in_task` definitions from `main.py`.

- [ ] **Step 4: Replace `execute_search_task` in `main.py`**

Replace `execute_search_task` with:

```python
def execute_search_task(task_id: str, request: SearchRequest, prepared: PreparedSearch):
    """后台执行搜索任务"""
    try:
        def update_progress(progress: str, trace: list[str]) -> None:
            task_store.update(task_id, progress=progress, agent_trace=trace)

        result = agent_runtime.execute_search(
            task_id=task_id,
            request=request,
            prepared=prepared,
            max_products=10,
            on_progress=update_progress,
        )
        task_store.write(result)

    except Exception as e:
        logger.exception("Search task %s failed", task_id)
        task_store.write(SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=prepared.parsed_query,
            products=[],
            total_count=0,
            status="failed",
            error=str(e),
            agent_trace=prepared.agent_trace,
            memory_context=prepared.memory_context,
            effective_query=prepared.effective_query,
            created_at=datetime.now()
        ))
```

- [ ] **Step 5: Replace search endpoint preparation in `main.py`**

Inside `search_products`, replace the parse/task creation/background block with:

```python
        prepared = agent_runtime.prepare_search(request)

        task_id = str(uuid.uuid4())
        task_store.write(SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=prepared.parsed_query,
            products=[],
            total_count=0,
            status="processing",
            progress="queued",
            agent_trace=prepared.agent_trace,
            memory_context=prepared.memory_context,
            effective_query=prepared.effective_query,
            created_at=datetime.now()
        ))

        background_tasks.add_task(execute_search_task, task_id, request, prepared)

        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "processing",
                "parsed_query": prepared.parsed_query.model_dump(),
                "agent_trace": prepared.agent_trace,
                "memory_context": prepared.memory_context,
                "effective_query": prepared.effective_query,
            },
            message="搜索任务已创建"
        )
```

- [ ] **Step 6: Replace result and latest endpoints in `main.py`**

In `get_search_result`, replace file access with:

```python
        if not is_valid_task_id(task_id):
            return APIResponse(success=False, error="非法的任务 ID")

        data = task_store.read_raw(task_id)
        if data is None:
            return APIResponse(success=False, error="任务不存在")

        return APIResponse(success=True, data=data)
```

In `get_latest_search_result`, replace the task file scan with:

```python
        data = task_store.latest_completed()
        if data is None:
            return APIResponse(success=False, error="暂无已完成搜索结果")
        return APIResponse(success=True, data=data)
```

- [ ] **Step 7: Replace action endpoint in `main.py`**

Replace the body of `record_user_action` with:

```python
    try:
        if not action.product_id or not action.task_id:
            return APIResponse(success=False, error="缺少 product_id 或 task_id")

        result = skill_registry.invoke(
            "record_product_action",
            user_id=action.user_id,
            action_type=action.action_type,
            product_id=action.product_id,
            task_id=action.task_id,
        )
        return APIResponse(
            success=bool(result.get("success")),
            data=result if result.get("success") else None,
            error=result.get("error"),
            message=result.get("message"),
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))
```

- [ ] **Step 8: Update `test_latest_task_api.py` to patch `task_store`**

Replace the body of `test_latest_search_result_returns_most_recent_completed_task` with:

```python
def test_latest_search_result_returns_most_recent_completed_task(tmp_path):
    original_task_store = main.task_store
    main.task_store = main.TaskStore(tmp_path)
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
        main.task_store.write(result)

        response = TestClient(main.app).get("/api/search/latest/default")
    finally:
        main.task_store = original_task_store

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == "latest-task"
    assert body["data"]["products"][0]["title"] == "华为FreeBuds 7i智慧降噪蓝牙耳机"
```

- [ ] **Step 9: Run FastAPI integration tests**

Run:

```powershell
cd backend
python -m pytest test_main_agent_integration.py test_latest_task_api.py -q
```

Expected: tests pass.

- [ ] **Step 10: Run full backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

```powershell
git add backend/main.py backend/test_main_agent_integration.py backend/test_latest_task_api.py
git commit -m "feat: route fastapi search through agent runtime"
```

## Task 10: Update Frontend Types And Agent Trace UI

**Files:**
- Modify: `app/package.json`
- Modify: `app/src/services/api.ts`
- Modify: `app/src/screens/HomeScreen.tsx`

- [ ] **Step 1: Add typecheck script**

In `app/package.json`, add this script after `web`:

```json
"typecheck": "tsc --noEmit"
```

The `scripts` block should become:

```json
"scripts": {
  "start": "expo start",
  "android": "expo start --android",
  "ios": "expo start --ios",
  "web": "expo start --web",
  "typecheck": "tsc --noEmit"
}
```

- [ ] **Step 2: Update API TypeScript types**

In `app/src/services/api.ts`, add fields to `Product`:

```ts
  recommendation_score?: number;
  recommendation_reason?: string | null;
```

Add fields to `SearchResult`:

```ts
  agent_trace?: string[];
  memory_context?: Record<string, any>;
  effective_query?: string | null;
```

Update `createSearch` return type:

```ts
  async createSearch(
    query: string
  ): Promise<{
    task_id: string;
    status: string;
    parsed_query?: ParsedQuery;
    agent_trace?: string[];
    memory_context?: Record<string, any>;
    effective_query?: string | null;
  }> {
```

- [ ] **Step 3: Add frontend state for returned trace**

In `HomeScreen.tsx`, add state after `parsedSummary`:

```ts
  const [agentTrace, setAgentTrace] = useState<string[]>([]);
  const [effectiveQuery, setEffectiveQuery] = useState('');
```

In latest-result restore, after `setStage('done');`, add:

```ts
        setAgentTrace(result.agent_trace || []);
        setEffectiveQuery(result.effective_query || '');
```

In `handleSearch`, after `setParsedSummary('');`, add:

```ts
    setAgentTrace([]);
    setEffectiveQuery('');
```

In the `createSearch` call, change:

```ts
      const { task_id, parsed_query } = await ApiService.createSearch(query);
```

to:

```ts
      const {
        task_id,
        parsed_query,
        agent_trace,
        effective_query,
      } = await ApiService.createSearch(query);
```

After the parsed summary block, add:

```ts
      setAgentTrace(agent_trace || []);
      setEffectiveQuery(effective_query || '');
```

In completed result handling, after `setIsDemo(!!result.is_demo);`, add:

```ts
          setAgentTrace(result.agent_trace || []);
          setEffectiveQuery(result.effective_query || '');
```

In processing result handling, after `setStage(current);`, add:

```ts
          if (result.agent_trace?.length) {
            setAgentTrace(result.agent_trace);
          }
          if (result.effective_query) {
            setEffectiveQuery(result.effective_query);
          }
```

- [ ] **Step 4: Render returned trace lines**

Before `return (` in `HomeScreen.tsx`, add:

```ts
  const derivedTraceLines =
    agentTrace.length > 0
      ? agentTrace
      : STAGES.map((s, index) => {
          const label =
            s.key === 'queued' && parsedSummary
              ? `解析需求 → ${parsedSummary}`
              : s.label;
          return label;
        });
```

Inside the terminal body, replace the `STAGES.map((s, index) => { ... })` block with:

```tsx
          {derivedTraceLines.map((line, index) => {
            const mark = stageMark(Math.min(index, STAGES.length - 1));
            return (
              <View key={`${line}-${index}`} style={styles.termLine}>
                <Text style={[styles.termIcon, mark.style]}>{mark.icon}</Text>
                <Text style={styles.termStep}>{line}</Text>
              </View>
            );
          })}
          {effectiveQuery ? (
            <View style={styles.effectiveQueryBox}>
              <Text style={styles.effectiveQueryText}>
                实际搜索词：{effectiveQuery}
              </Text>
            </View>
          ) : null}
```

- [ ] **Step 5: Render recommendation reason in product cards**

In `HomeScreen.tsx`, inside `productBody`, after `productPriceRow`, add:

```tsx
                {product.recommendation_reason ? (
                  <Text style={styles.recommendReason} numberOfLines={2}>
                    {product.recommendation_reason}
                  </Text>
                ) : null}
```

Add styles near the other terminal/product styles:

```ts
  effectiveQueryBox: {
    borderTopWidth: 1,
    borderTopColor: colors.termBorder,
    marginTop: spacing.s,
    paddingTop: spacing.s,
  },
  effectiveQueryText: {
    color: colors.termAmber,
    fontSize: fontSize.micro,
    fontFamily: fontFamily.mono,
  },
  recommendReason: {
    color: colors.prefFg,
    fontSize: fontSize.micro + 1,
    lineHeight: 17,
    marginTop: spacing.xs + 2,
  },
```

- [ ] **Step 6: Run frontend typecheck**

Run:

```powershell
cd app
npm run typecheck
```

Expected: TypeScript passes. The existing npm `sass_binary_site` warning may still appear.

- [ ] **Step 7: Run backend tests after frontend-only changes**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all backend tests still pass.

- [ ] **Step 8: Commit**

```powershell
git add app/package.json app/src/services/api.ts app/src/screens/HomeScreen.tsx
git commit -m "feat: show agent trace and recommendation reasons"
```

## Task 11: Update Product Documentation

**Files:**
- Modify: `README.md`
- Modify: `IMPLEMENTATION.md`

- [ ] **Step 1: Update README status section**

In `README.md`, replace the current status list with this content:

```markdown
**已完成并验收：**

- FastAPI 后端：搜索任务创建、任务查询、最近结果恢复、偏好查询、行为上报 API。
- Agent Runtime：统一编排需求解析、Memory 读取、搜索词自进化、Skill 调用和推荐排序。
- Skill Registry：淘宝搜索、偏好洞察、行为记录、商品重排均以声明式 Skill 注册，可被 REST 与 MCP 复用。
- MCP Server：将 Skill Registry 暴露为 MCP tools，支持外部 Agent 工具调用。
- 淘宝搜索 Skill：封装 Open-AutoGLM，支持真机控制、ADB 截屏、GLM-4V 商品提取。
- React Native App：Expo Go 真机运行、搜索页、真实 Agent Trace、结果页、推荐理由、偏好页。
- Memory 闭环：App 点击商品后写入偏好，后续搜索会保守注入高置信偏好并解释排序理由。
- 单机演示稳定性：同一台手机既运行 Expo Go 又被 AutoGLM 切到淘宝时，App 可恢复最近搜索结果。
```

- [ ] **Step 2: Update README architecture diagram**

Replace the architecture code block with:

```text
React Native App (Expo Go)
        │ REST API
        ▼
FastAPI 后端
  ├─ AgentRuntime              统一编排解析、记忆、工具调用与推荐解释
  ├─ QueryParserService        GLM 文本模型解析自然语言需求
  ├─ SkillRegistry             声明式 Skill 注册、发现、调用
  │   ├─ taobao_search         真机淘宝搜索 + 截图 + GLM-4V 提取
  │   ├─ get_preference_insight 读取 Memory 上下文
  │   ├─ record_product_action  点击/查看行为写入 Memory
  │   └─ rerank_products       偏好重排 + 推荐理由
  ├─ PreferenceService         Memory 持久化与偏好权重
  ├─ TaskStore                 文件任务存储与最近结果恢复
  └─ MCP Server                暴露同一批 Skill 给外部 Agent
        │
        ▼
Open-AutoGLM ──► Android 手机（淘宝 App）
        │
        ▼
ADB 截屏 ──► GLM-4V 商品结构化提取
```

- [ ] **Step 3: Add MCP quick start command to README**

After backend startup instructions, add:

````markdown
### 启动 MCP Server（可选，用于展示工具协议能力）

```bash
cd SmartCart/backend
python mcp_server.py
```

MCP Server 暴露的工具来自同一套 `SkillRegistry`：`taobao_search`、`get_preference_insight`、`record_product_action`、`rerank_products`。
````

- [ ] **Step 4: Update README demo script**

Replace the final demo explanation line with:

```markdown
7. 简短说明：本项目覆盖移动端真机运行、多模态商品提取、Memory、Skill Registry、MCP tools、自进化搜索词、推荐理由和可见 Agent Trace。
```

- [ ] **Step 5: Update IMPLEMENTATION Phase 6**

Append to `IMPLEMENTATION.md`:

```markdown
### Phase 6：Agent 架构升级（进行中）

- [x] 设计文档：单用户完整产品边界，明确 AgentRuntime / SkillRegistry / MCP / Memory 自进化。
- [x] Skill 机制：基类、注册表、默认 catalog，淘宝搜索 / 偏好洞察 / 行为记录 / 商品重排统一注册。
- [x] AgentRuntime：统一编排解析、记忆读取、保守搜索词注入、工具调用、推荐排序和 trace。
- [x] MCP Server：通过同一套 SkillRegistry 暴露工具能力。
- [x] 前端：展示后端返回的真实 Agent Trace、实际搜索词、推荐理由。
- [x] 测试：SkillRegistry、TaskStore、Preference skills、AgentRuntime、MCP adapter、FastAPI integration。
- [ ] 真机回归：搜索 → 淘宝控制 → 截图提取 → 推荐理由 → 点击学习 → 再搜索记忆注入。

**Phase 6 验收标准：**

- `python -m pytest -q` 全部通过。
- `npm run typecheck` 通过。
- MCP adapter/server 测试能列出并调用 registry-backed tools。
- README 能准确说明这是移动端 AI Agent 产品，而不是单纯 API Demo。
```

- [ ] **Step 6: Run markdown-facing checks through git diff review**

Run:

```powershell
git diff -- README.md IMPLEMENTATION.md
```

Expected: diff only updates status, architecture, MCP startup, demo script, and Phase 6 notes.

- [ ] **Step 7: Commit**

```powershell
git add README.md IMPLEMENTATION.md
git commit -m "docs: document agent architecture upgrade"
```

## Task 12: Final Verification

**Files:**
- No planned code edits.

- [ ] **Step 1: Run backend test suite**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend typecheck**

Run:

```powershell
cd app
npm run typecheck
```

Expected: TypeScript passes.

- [ ] **Step 3: Verify FastAPI imports and starts**

Run:

```powershell
cd backend
python -c "import main; print(main.app.title)"
```

Expected:

```text
SmartCart API
```

- [ ] **Step 4: Verify MCP server imports**

Run:

```powershell
cd backend
python -c "from mcp_server import create_mcp_server; server = create_mcp_server(); print(type(server).__name__)"
```

Expected:

```text
FastMCP
```

- [ ] **Step 5: Review working tree**

Run:

```powershell
git status --short --branch
git log --oneline --max-count=12
```

Expected: clean working tree after task commits, recent commits match the task sequence.

- [ ] **Step 6: Manual true-device acceptance**

Run this manually with the phone connected:

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

In a second terminal:

```powershell
cd app
npm run android
```

Acceptance observations:

- Search `我想买 500 元左右的蓝牙耳机`.
- App shows returned Agent trace, including parse, memory, effective query, tool call, and ranking.
- AutoGLM controls Taobao and stops on the result list.
- App shows real products or visibly marked demo fallback.
- Product cards show recommendation reasons when ranking metadata exists.
- Clicking a non-demo product updates preference memory.
- A similar second search shows memory usage in the trace.

## Plan Self-Review

Spec coverage:

- Skill base and registry: Task 3.
- Taobao as registered Skill and default catalog: Task 6.
- Preference insight, product action, rerank products: Tasks 4 and 5.
- AgentRuntime and conservative memory injection: Task 7.
- MCP tool exposure: Task 8.
- FastAPI integration: Task 9.
- Frontend trace and reasons: Task 10.
- Documentation: Task 11.
- Automated and manual verification: Task 12.

Deferred scope remains outside this plan by design: multi-user accounts, SQLite, production queue, Docker, and cloud deployment.
