# SmartCart Agent Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved SmartCart job-submission demo so a real phone can run one `综合` shopping task, return product-first results, and expose `Trace / Skills / Memory` clearly enough for recording and review.

**Architecture:** Keep the existing FastAPI + `AgentRuntime` + `TaskStore` flow intact, and add only the minimum new result metadata needed for the demo: structured `skill_runs`, stable progress stages, and explicit memory-match signals. On the app side, keep `HomeScreen` as the orchestration surface but split the result UI into a product layer plus a collapsible technical layer rendered by small reusable components.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest, React Native Expo, TypeScript, Axios, Open-AutoGLM real-device control.

---

## Baseline

Run from `D:\Study\project\SmartCart`.

- Backend baseline:

```powershell
cd backend
python -m pytest -q
```

Current result: `94 passed, 1 warning`.

- Frontend baseline:

```powershell
cd app
npx tsc --noEmit
```

Current result: typecheck succeeds; npm prints the existing warning `Unknown user config "sass_binary_site"`.

- Existing unrelated-but-required dirty files must be preserved exactly as-is unless a task below explicitly edits them:
  - `.env.example`
  - `backend/config.py`
  - `backend/skills/taobao_search.py`
  - `backend/test_config_return.py`
  - `backend/test_taobao_search_env.py`

These files already contain the current return-to-app and performance-tuning work. Do not revert them while implementing this plan.

## File Structure

Create:

- `app/src/components/AgentInsightPanel.tsx` - collapsible result-page technical layer with `Trace / Skills / Memory` tabs.
- `app/src/components/ProductResultCard.tsx` - product-facing result card used by `HomeScreen`.

Modify:

- `backend/models.py:11-61` - add structured `SkillRun` payload and persist it on `SearchResult`.
- `backend/services/agent_runtime.py:27-206` - capture per-skill timing/status, forward child progress safely, and add memory-match summary.
- `backend/main.py:109-193` - write `skill_runs` into finished tasks and keep API payloads aligned with the model.
- `backend/test_models_agent_fields.py:1-61` - assert `skill_runs` defaults and serialization.
- `backend/test_agent_runtime.py:1-80` - assert runtime emits structured skill runs, child stages, and memory-match signals.
- `backend/test_search_api.py:1-66` - assert search API returns `skill_runs` and memory-match fields.
- `backend/test_multi_source.py:1-107` - assert multi-source runs expose both successful and failed source summaries.
- `app/package.json:17-23` - add a stable `typecheck` script.
- `app/src/services/api.ts:24-154` - add TypeScript types for `ParsedQuery`, `SkillRun`, `matched_signals`, and `recordAction` response data.
- `app/src/screens/HomeScreen.tsx:17-795` - load the new payloads, show recent preference hints, recover on app resume, and render the new result layout.
- `app/App.tsx:13-47` - simplify the app shell to the single-screen demo flow.
- `README.md:1-170` - update the GitHub story and exact phone-recording workflow.
- `app/README.md:1-83` - align local run instructions with the localhost + adb reverse demo path.

## Task 1: Add Structured `skill_runs` To The Backend Result Model

**Files:**
- Modify: `backend/test_models_agent_fields.py:1-61`
- Modify: `backend/models.py:11-61`

- [ ] **Step 1: Expand the model regression test first**

Update `backend/test_models_agent_fields.py` to this content:

```python
from datetime import datetime

from models import ParsedQuery, Product, SearchResult, SkillRun


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
    assert result.skill_runs == []


def test_search_result_serializes_skill_runs_and_agent_metadata():
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
        memory_context={
            "top_brands": [{"brand": "华为", "score": 0.9, "count": 3}],
            "matched_signals": {
                "brand": True,
                "feature": False,
                "price_range": True,
                "has_match": True,
            },
        },
        effective_query="蓝牙耳机 华为 降噪",
        skill_runs=[
            SkillRun(
                skill_name="jd_search",
                platform="jd",
                query="蓝牙耳机",
                status="completed",
                duration_seconds=94.0,
                product_count=8,
            )
        ],
        created_at=datetime.now(),
    )

    data = result.model_dump(mode="json")
    assert data["agent_trace"] == ["解析需求 -> 蓝牙耳机 · ¥400-600"]
    assert data["memory_context"]["matched_signals"]["has_match"] is True
    assert data["effective_query"] == "蓝牙耳机 华为 降噪"
    assert data["skill_runs"][0]["skill_name"] == "jd_search"
    assert data["products"][0]["recommendation_reason"] == "命中你常看的华为品牌"
```

- [ ] **Step 2: Run the targeted model test and verify it fails**

Run:

```powershell
cd backend
python -m pytest test_models_agent_fields.py -q
```

Expected: failure because `SkillRun` and `SearchResult.skill_runs` do not exist yet.

- [ ] **Step 3: Add the new model**

In `backend/models.py`, insert this class above `SearchResult`:

```python
class SkillRun(BaseModel):
    """单次技能执行摘要，供 Result 页 Skills Tab 直接消费。"""
    skill_name: str
    platform: str
    query: str
    status: str  # completed | failed
    duration_seconds: float
    product_count: int
```

Then update `SearchResult` to this shape:

```python
class SearchResult(BaseModel):
    """搜索结果"""
    task_id: str  # 任务 ID
    query: str  # 原始查询
    parsed_query: ParsedQuery  # 解析后的查询
    products: List[Product]  # 商品列表
    total_count: int  # 总数
    status: str = "completed"  # completed | failed | processing
    progress: Optional[str] = None  # queued | waiting_device | controlling_phone | extracting | ranking
    error: Optional[str] = None  # 错误信息
    is_demo: bool = False  # 结果中包含演示数据
    agent_trace: List[str] = Field(default_factory=list)  # Agent 可见执行轨迹
    memory_context: Dict[str, Any] = Field(default_factory=dict)  # 本次使用的记忆上下文
    effective_query: Optional[str] = None  # 实际输入真机搜索词
    elapsed_seconds: Optional[float] = None  # Agent 端到端总耗时（秒）
    skill_runs: List[SkillRun] = Field(default_factory=list)  # 结构化技能执行摘要
    created_at: datetime  # 创建时间
```

- [ ] **Step 4: Re-run the model test**

Run:

```powershell
cd backend
python -m pytest test_models_agent_fields.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```powershell
git add backend/models.py backend/test_models_agent_fields.py
git commit -m "feat: add structured skill run metadata"
```

## Task 2: Instrument `AgentRuntime` With Safe Child Progress, `skill_runs`, And Memory Match Summary

**Files:**
- Modify: `backend/test_agent_runtime.py:1-80`
- Modify: `backend/test_search_api.py:1-66`
- Modify: `backend/test_multi_source.py:1-107`
- Modify: `backend/services/agent_runtime.py:27-206`
- Modify: `backend/main.py:109-193`

- [ ] **Step 1: Add failing runtime and API assertions**

Add these tests to `backend/test_agent_runtime.py`:

```python
def test_runtime_exposes_structured_skill_runs(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    rt, _ = _runtime(tmp_path, parsed, seed_brand="华为")
    out = rt.run_search("蓝牙耳机")

    assert out.skill_runs[0].skill_name == "taobao_search"
    assert out.skill_runs[0].platform == "taobao"
    assert out.skill_runs[0].query == out.effective_query
    assert out.skill_runs[0].status == "completed"
    assert out.memory_context["matched_signals"]["brand"] is True


def test_progress_callback_receives_child_skill_stages(tmp_path):
    parsed = ParsedQuery(category="蓝牙耳机", keywords=["蓝牙耳机"])
    rt, _ = _runtime(tmp_path, parsed)
    stages = []

    rt.run_search("蓝牙耳机", on_progress=stages.append)

    assert "controlling_phone" in stages
    assert "extracting" in stages
    assert stages[-1] == "ranking"
```

Add these assertions to `backend/test_search_api.py` inside `test_search_flow_returns_trace_and_ranked_products`:

```python
        assert data["skill_runs"][0]["skill_name"] == "taobao_search"
        assert data["skill_runs"][0]["query"] == data["effective_query"]
        assert "matched_signals" in data["memory_context"]
```

Add this test to `backend/test_multi_source.py`:

```python
def test_failed_source_still_has_failed_skill_run(tmp_path):
    tb = _FakeSource("taobao", [{"id": "t1", "title": "A", "price": 300}])
    out = _runtime(tmp_path, tb, _FailingSource()).run_search("耳机", platform="all")

    by_platform = {run.platform: run for run in out.skill_runs}
    assert by_platform["taobao"].status == "completed"
    assert by_platform["jd"].status == "failed"
    assert by_platform["jd"].product_count == 0
```

- [ ] **Step 2: Run the targeted backend tests and verify failure**

Run:

```powershell
cd backend
python -m pytest test_agent_runtime.py test_search_api.py test_multi_source.py -q
```

Expected: failures because `AgentSearchOutcome` has no `skill_runs`, the search API payload has no `skill_runs`, and child skill stages are not forwarded.

- [ ] **Step 3: Implement runtime instrumentation**

In `backend/services/agent_runtime.py`, update the imports:

```python
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from models import ParsedQuery, Product, SkillRun
```

Add these helpers above `AgentRuntime`:

```python
_PROGRESS_ORDER = {
    "queued": 0,
    "waiting_device": 1,
    "controlling_phone": 2,
    "extracting": 3,
    "ranking": 4,
}


@dataclass
class SourceRun:
    platform: str
    product_dicts: List[Dict[str, Any]]
    duration_seconds: float
    status: str


def _matched_signals(context: Dict[str, Any], products: List[Product]) -> Dict[str, bool]:
    top_brands = {item["brand"] for item in context.get("top_brands", [])}
    features = context.get("features", [])
    price_range = context.get("price_range")

    brand_hit = any(p.brand in top_brands for p in products if p.brand)
    feature_hit = any(any(feature in p.title for feature in features) for p in products)
    price_hit = bool(price_range) and any(
        price_range["min"] <= p.price <= price_range["max"] for p in products
    )
    return {
        "brand": brand_hit,
        "feature": feature_hit,
        "price_range": price_hit,
        "has_match": brand_hit or feature_hit or price_hit,
    }
```

Extend `AgentSearchOutcome`:

```python
@dataclass
class AgentSearchOutcome:
    products: List[Product]
    parsed_query: ParsedQuery
    agent_trace: List[str] = field(default_factory=list)
    effective_query: str = ""
    memory_context: Dict[str, Any] = field(default_factory=dict)
    is_demo: bool = False
    elapsed_seconds: float = 0.0
    skill_runs: List[SkillRun] = field(default_factory=list)
```

Replace `_search_sources()` with:

```python
    def _search_sources(
        self,
        targets: List[str],
        keyword: str,
        max_products: int,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> List[SourceRun]:
        """并发调用各平台搜索技能，保留结构化执行摘要。"""
        progress_lock = Lock()
        highest_stage = {"value": -1}

        def emit_progress(stage: str) -> None:
            if on_progress is None:
                return
            order = _PROGRESS_ORDER.get(stage, -1)
            with progress_lock:
                if order >= highest_stage["value"]:
                    highest_stage["value"] = order
                    on_progress(stage)

        def one(p: str) -> SourceRun:
            start = time.perf_counter()
            try:
                dicts = self.registry.invoke(
                    f"{p}{_SEARCH_SUFFIX}",
                    keyword=keyword,
                    max_products=max_products,
                    on_progress=emit_progress,
                )
                status = "completed"
            except Exception:
                logger.exception("source %s search failed", p)
                dicts = []
                status = "failed"
            return SourceRun(
                platform=p,
                product_dicts=dicts,
                duration_seconds=time.perf_counter() - start,
                status=status,
            )

        if len(targets) == 1:
            return [one(targets[0])]
        with ThreadPoolExecutor(max_workers=len(targets)) as ex:
            return list(ex.map(one, targets))
```

In `run_search()`, replace the source-search and return block with:

```python
        targets = self._resolve_targets(platform)
        notify("waiting_device")
        results = self._search_sources(
            targets,
            effective_query,
            max_products,
            on_progress=notify,
        )
        for run in sorted(results, key=lambda item: item.platform):
            trace.append(
                f"调用工具 → {run.platform}{_SEARCH_SUFFIX}（{len(run.product_dicts)} 个商品）· "
                f"{_fmt_duration(run.duration_seconds)}"
            )
        skill_runs = [
            SkillRun(
                skill_name=f"{run.platform}{_SEARCH_SUFFIX}",
                platform=run.platform,
                query=effective_query,
                status=run.status,
                duration_seconds=round(run.duration_seconds, 2),
                product_count=len(run.product_dicts),
            )
            for run in sorted(results, key=lambda item: item.platform)
        ]
        product_dicts = [pd for run in results for pd in run.product_dicts]

        notify("ranking")
        t = time.perf_counter()
        ranked_dicts: List[Dict[str, Any]] = self.registry.invoke(
            "rerank_products",
            products=product_dicts,
            user_id=user_id,
            parsed=parsed.model_dump(),
        )
        products = [Product(**p) for p in ranked_dicts]
        multi = len(targets) >= 2
        if multi:
            _annotate_deals(products)
        rerank_dt = time.perf_counter() - t

        if multi:
            dist = " / ".join(
                f"{p}:{sum(1 for pp in products if pp.platform == p)}" for p in sorted(targets)
            )
            real = [p for p in products if not p.is_demo and p.price > 0]
            cheap = min(real, key=lambda p: p.price) if real else None
            cheap_txt = f"，全网最低 ¥{cheap.price:.0f}（{cheap.platform}）" if cheap else ""
            trace.append(f"综合比价 → {len(products)} 个（{dist}）{cheap_txt}")

        matched = self.memory.matched_count(products)
        enriched_context = {
            **context,
            "matched_signals": _matched_signals(context, products),
        }
        is_demo = any(p.is_demo for p in products)
        trace.append(
            f"推荐排序 → {len(products)} 个商品，{matched} 个命中偏好 · {_fmt_duration(rerank_dt)}"
        )
```

And update the return statement:

```python
        return AgentSearchOutcome(
            products=products,
            parsed_query=parsed,
            agent_trace=trace,
            effective_query=effective_query,
            memory_context=enriched_context,
            is_demo=is_demo,
            elapsed_seconds=round(time.perf_counter() - started, 2),
            skill_runs=skill_runs,
        )
```

Then update `backend/main.py` inside `execute_search_task()`:

```python
        task_store.write(SearchResult(
            task_id=task_id,
            query=request.query,
            parsed_query=outcome.parsed_query,
            products=outcome.products,
            total_count=len(outcome.products),
            status="completed",
            progress="completed",
            is_demo=outcome.is_demo,
            agent_trace=outcome.agent_trace,
            memory_context=outcome.memory_context,
            effective_query=outcome.effective_query,
            elapsed_seconds=outcome.elapsed_seconds,
            skill_runs=outcome.skill_runs,
            created_at=datetime.now(),
        ))
```

- [ ] **Step 4: Re-run the targeted backend tests**

Run:

```powershell
cd backend
python -m pytest test_agent_runtime.py test_search_api.py test_multi_source.py -q
```

Expected: the targeted tests pass.

- [ ] **Step 5: Re-run the full backend suite**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all backend tests pass, including the existing return-to-app and environment regression tests.

- [ ] **Step 6: Commit**

```powershell
git add backend/services/agent_runtime.py backend/main.py backend/test_agent_runtime.py backend/test_search_api.py backend/test_multi_source.py
git commit -m "feat: capture skill runs and memory match signals"
```

## Task 3: Extend App API Types And Build Reusable Result Components

**Files:**
- Modify: `app/package.json:17-23`
- Modify: `app/src/services/api.ts:24-154`
- Create: `app/src/components/ProductResultCard.tsx`
- Create: `app/src/components/AgentInsightPanel.tsx`

- [ ] **Step 1: Update the app contract and add a stable typecheck command**

In `app/package.json`, change the scripts block to:

```json
"scripts": {
  "start": "expo start",
  "android": "expo start --android",
  "ios": "expo start --ios",
  "web": "expo start --web",
  "typecheck": "tsc --noEmit"
}
```

In `app/src/services/api.ts`, replace the type section with:

```ts
export interface SearchRequest {
  query: string;
  user_id?: string;
  platform?: string;
}

export interface Product {
  id: string;
  title: string;
  price: number;
  rating?: number;
  review_count?: number;
  brand?: string;
  platform: string;
  is_demo?: boolean;
  recommendation_score?: number;
  recommendation_reason?: string | null;
  deal_tag?: string | null;
}

export interface ParsedQuery {
  category: string;
  keywords: string[];
  price_min?: number | null;
  price_max?: number | null;
  features: string[];
}

export interface SkillRun {
  skill_name: string;
  platform: string;
  query: string;
  status: 'completed' | 'failed';
  duration_seconds: number;
  product_count: number;
}

export interface MemoryMatchedSignals {
  brand: boolean;
  feature: boolean;
  price_range: boolean;
  has_match: boolean;
}

export interface MemoryContext {
  top_brand?: string | null;
  top_brands?: { brand: string; score: number; count: number }[];
  features?: string[];
  price_range?: { min: number; max: number } | null;
  recent_queries?: string[];
  has_signal?: boolean;
  matched_signals?: MemoryMatchedSignals;
}

export interface SearchResult {
  task_id: string;
  query?: string;
  status: string;
  progress?: string;
  parsed_query?: ParsedQuery;
  products?: Product[];
  error?: string;
  is_demo?: boolean;
  agent_trace?: string[];
  effective_query?: string;
  elapsed_seconds?: number;
  memory_context?: MemoryContext;
  skill_runs?: SkillRun[];
}

export interface BrandPreference {
  brand: string;
  score: number;
  count: number;
  last_updated: string;
}

export interface UserPreference {
  user_id: string;
  brand_preferences: Record<string, BrandPreference>;
  price_preference?: {
    min: number;
    max: number;
    avg: number;
    median: number;
  };
  feature_preferences: Record<string, number>;
  search_history: string[];
}
```

Also change `createSearch()` and `recordAction()`:

```ts
  async createSearch(
    query: string,
    platform: string = 'all'
  ): Promise<{ task_id: string; status: string }> {
    const response = await axios.post(`${API_BASE_URL}/api/search`, {
      query,
      user_id: 'default',
      platform,
    });
    return response.data.data;
  }

  async recordAction(action: {
    user_id: string;
    action_type: string;
    product_id?: string;
    task_id?: string;
  }): Promise<MemoryContext | null> {
    const response = await axios.post(`${API_BASE_URL}/api/preference/action`, {
      ...action,
      timestamp: new Date().toISOString(),
    });
    return response.data.data ?? null;
  }
```

- [ ] **Step 2: Create the product-layer card component**

Create `app/src/components/ProductResultCard.tsx`:

```tsx
import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { Product } from '../services/api';
import { colors, fontSize, fontVariant, spacing, radius } from '../theme/tokens';

type Props = {
  product: Product;
  clicked: boolean;
  budgetHit: boolean;
  onPress: () => void;
};

function formatPrice(price: number): string {
  return Number.isFinite(price) ? price.toFixed(2) : String(price);
}

function getProductInitial(product: Product): string {
  const label = product.brand || product.platform || product.title || '商';
  return label.trim().slice(0, 1).toUpperCase();
}

export default function ProductResultCard({ product, clicked, budgetHit, onPress }: Props) {
  return (
    <TouchableOpacity
      style={styles.row}
      activeOpacity={0.7}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${product.title}，价格 ${formatPrice(product.price)} 元`}
    >
      <View style={styles.thumb}>
        <Text style={styles.thumbText}>{getProductInitial(product)}</Text>
      </View>
      <View style={styles.body}>
        <Text style={styles.title} numberOfLines={2}>
          {product.title}
        </Text>
        <View style={styles.priceRow}>
          <Text style={styles.price}>
            <Text style={styles.priceSymbol}>¥</Text>
            {formatPrice(product.price)}
          </Text>
          <Text style={styles.meta} numberOfLines={1}>
            {[product.brand, product.platform === 'jd' ? '京东' : '淘宝'].filter(Boolean).join(' · ')}
          </Text>
        </View>
        {product.recommendation_reason ? (
          <Text style={styles.reason} numberOfLines={2}>
            {product.recommendation_reason}
          </Text>
        ) : null}
        <View style={styles.tagRow}>
          {budgetHit ? (
            <View style={styles.budgetTag}>
              <Text style={styles.budgetTagText}>预算命中</Text>
            </View>
          ) : null}
          {product.deal_tag ? (
            <View style={styles.dealTag}>
              <Text style={styles.dealTagText}>{product.deal_tag}</Text>
            </View>
          ) : null}
          {clicked ? (
            <View style={styles.prefTag}>
              <Text style={styles.prefTagText}>已记录偏好</Text>
            </View>
          ) : null}
          {product.is_demo ? (
            <View style={styles.demoTag}>
              <Text style={styles.demoTagText}>演示数据</Text>
            </View>
          ) : null}
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    paddingVertical: spacing.xl,
    borderBottomWidth: 1,
    borderBottomColor: colors.hairline,
  },
  thumb: {
    width: 64,
    height: 64,
    borderRadius: radius.md,
    backgroundColor: colors.skeleton,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.l,
  },
  thumbText: {
    color: colors.ink,
    fontSize: fontSize.price,
    fontWeight: '800',
  },
  body: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    color: colors.ink,
    fontSize: fontSize.item,
    lineHeight: 22,
    fontWeight: '600',
    marginBottom: spacing.s,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  price: {
    color: colors.ink,
    fontSize: fontSize.price,
    fontWeight: '800',
    fontVariant: fontVariant.tabular,
  },
  priceSymbol: {
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  meta: {
    color: colors.meta,
    fontSize: fontSize.micro,
    marginLeft: spacing.s,
    flexShrink: 1,
  },
  reason: {
    color: colors.prefFg,
    fontSize: fontSize.micro,
    marginTop: spacing.s,
    lineHeight: 18,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.s,
  },
  budgetTag: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.prefFg,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
  },
  budgetTagText: {
    fontSize: fontSize.caption,
    color: colors.prefFg,
    fontWeight: '700',
  },
  dealTag: {
    backgroundColor: colors.ink,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
  },
  dealTagText: {
    fontSize: fontSize.caption,
    color: colors.accentOn,
    fontWeight: '700',
  },
  prefTag: {
    backgroundColor: colors.prefBg,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
  },
  prefTagText: {
    fontSize: fontSize.caption,
    color: colors.prefFg,
    fontWeight: '700',
  },
  demoTag: {
    backgroundColor: colors.warnBg,
    borderWidth: 1,
    borderColor: colors.warnBorder,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
  },
  demoTagText: {
    fontSize: fontSize.caption,
    color: colors.warnFg,
    fontWeight: '700',
  },
});
```

- [ ] **Step 3: Create the collapsible technical panel**

Create `app/src/components/AgentInsightPanel.tsx`:

```tsx
import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { MemoryContext, ParsedQuery, SkillRun } from '../services/api';
import { colors, fontFamily, fontSize, spacing, radius } from '../theme/tokens';

type AgentTab = 'trace' | 'skills' | 'memory';

type Props = {
  parsedQuery?: ParsedQuery | null;
  effectiveQuery?: string;
  elapsedSeconds?: number | null;
  agentTrace: string[];
  skillRuns: SkillRun[];
  memoryContext?: MemoryContext | null;
};

function formatParsedIntent(parsedQuery?: ParsedQuery | null): string {
  if (!parsedQuery) {
    return '待解析';
  }
  const budget =
    parsedQuery.price_min != null && parsedQuery.price_max != null
      ? ` · ¥${Math.round(parsedQuery.price_min)}-${Math.round(parsedQuery.price_max)}`
      : '';
  return `${parsedQuery.category}${budget}`;
}

function formatPriceRange(memoryContext?: MemoryContext | null): string {
  const range = memoryContext?.price_range;
  if (!range) {
    return '暂无';
  }
  return `¥${Math.round(range.min)}-${Math.round(range.max)}`;
}

export default function AgentInsightPanel({
  parsedQuery,
  effectiveQuery,
  elapsedSeconds,
  agentTrace,
  skillRuns,
  memoryContext,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<AgentTab>('trace');

  const rankingSummary = useMemo(() => {
    return [...agentTrace]
      .reverse()
      .find((line) => line.includes('推荐排序') || line.includes('综合比价')) || '待生成';
  }, [agentTrace]);

  const sourceSummary = useMemo(() => {
    if (skillRuns.length === 0) {
      return '暂无';
    }
    const body = skillRuns
      .map((run) => {
        const label = run.platform === 'jd' ? '京东' : '淘宝';
        return `${label} ${run.product_count} 件 / ${run.duration_seconds.toFixed(1)}s`;
      })
      .join(' · ');
    return skillRuns.length > 1 ? `${body}（单设备串行）` : body;
  }, [skillRuns]);

  const matchedSignals = memoryContext?.matched_signals;

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.header}
        onPress={() => setExpanded((value) => !value)}
        accessibilityRole="button"
        accessibilityLabel={expanded ? '收起 Agent 视角' : '展开 Agent 视角'}
      >
        <View>
          <Text style={styles.title}>Agent 视角</Text>
          <Text style={styles.subtitle}>Trace / Skills / Memory</Text>
        </View>
        <Text style={styles.toggle}>{expanded ? '收起' : '展开'}</Text>
      </TouchableOpacity>

      {!expanded ? (
        <Text style={styles.collapsedText}>
          当前解析：{formatParsedIntent(parsedQuery)}{elapsedSeconds != null ? ` · ${elapsedSeconds.toFixed(1)}s` : ''}
        </Text>
      ) : (
        <>
          <View style={styles.tabRow}>
            {(['trace', 'skills', 'memory'] as const).map((tab) => (
              <TouchableOpacity
                key={tab}
                style={[styles.tab, activeTab === tab && styles.tabActive]}
                onPress={() => setActiveTab(tab)}
                accessibilityRole="tab"
                accessibilityState={{ selected: activeTab === tab }}
              >
                <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                  {tab === 'trace' ? 'Trace' : tab === 'skills' ? 'Skills' : 'Memory'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {activeTab === 'trace' ? (
            <View style={styles.section}>
              <Text style={styles.rowLabel}>Parsed Intent</Text>
              <Text style={styles.rowValue}>{formatParsedIntent(parsedQuery)}</Text>

              <Text style={styles.rowLabel}>Effective Query</Text>
              <Text style={styles.rowValue}>{effectiveQuery || '待生成'}</Text>

              <Text style={styles.rowLabel}>Source Summary</Text>
              <Text style={styles.rowValue}>{sourceSummary}</Text>

              <Text style={styles.rowLabel}>Ranking Summary</Text>
              <Text style={styles.rowValue}>{rankingSummary}</Text>

              <Text style={styles.rowLabel}>Elapsed</Text>
              <Text style={styles.rowValue}>
                {elapsedSeconds != null ? `${elapsedSeconds.toFixed(1)}s` : '进行中'}
              </Text>

              <View style={styles.traceList}>
                {agentTrace.map((line, index) => (
                  <Text key={`${line}-${index}`} style={styles.traceLine}>
                    {line}
                  </Text>
                ))}
              </View>
            </View>
          ) : null}

          {activeTab === 'skills' ? (
            <View style={styles.section}>
              {skillRuns.map((run) => (
                <View key={`${run.platform}-${run.skill_name}`} style={styles.skillCard}>
                  <View style={styles.skillHeader}>
                    <Text style={styles.skillName}>{run.skill_name}</Text>
                    <Text style={styles.skillStatus}>{run.status}</Text>
                  </View>
                  <Text style={styles.skillMeta}>平台：{run.platform === 'jd' ? '京东' : '淘宝'}</Text>
                  <Text style={styles.skillMeta}>Query：{run.query}</Text>
                  <Text style={styles.skillMeta}>
                    耗时：{run.duration_seconds.toFixed(1)}s · 商品：{run.product_count} 件
                  </Text>
                </View>
              ))}
            </View>
          ) : null}

          {activeTab === 'memory' ? (
            <View style={styles.section}>
              <Text style={styles.rowLabel}>Top Brands</Text>
              <Text style={styles.rowValue}>
                {memoryContext?.top_brands?.length
                  ? memoryContext.top_brands.map((item) => `${item.brand}(${Math.round(item.score * 100)}%)`).join(' · ')
                  : '暂无'}
              </Text>

              <Text style={styles.rowLabel}>Price Range</Text>
              <Text style={styles.rowValue}>{formatPriceRange(memoryContext)}</Text>

              <Text style={styles.rowLabel}>Recent Queries</Text>
              <Text style={styles.rowValue}>
                {memoryContext?.recent_queries?.length ? memoryContext.recent_queries.join(' / ') : '暂无'}
              </Text>

              <Text style={styles.rowLabel}>Matched Signals</Text>
              <Text style={styles.rowValue}>
                {matchedSignals?.has_match
                  ? `品牌 ${matchedSignals.brand ? '命中' : '未命中'} · 特性 ${matchedSignals.feature ? '命中' : '未命中'} · 价格 ${matchedSignals.price_range ? '命中' : '未命中'}`
                  : '本次任务未命中明显记忆信号'}
              </Text>
            </View>
          ) : null}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: spacing.l,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.l,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: fontSize.body,
    fontWeight: '800',
    color: colors.ink,
  },
  subtitle: {
    fontSize: fontSize.micro,
    color: colors.meta,
    marginTop: spacing.xs,
  },
  toggle: {
    color: colors.prefFg,
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  collapsedText: {
    marginTop: spacing.m,
    color: colors.sub,
    fontSize: fontSize.label,
    lineHeight: 20,
  },
  tabRow: {
    flexDirection: 'row',
    marginTop: spacing.l,
    marginBottom: spacing.m,
  },
  tab: {
    paddingHorizontal: spacing.l,
    paddingVertical: spacing.s,
    borderRadius: radius.sm,
    backgroundColor: colors.bg,
    marginRight: spacing.s,
  },
  tabActive: {
    backgroundColor: colors.ink,
  },
  tabText: {
    color: colors.sub,
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  tabTextActive: {
    color: colors.accentOn,
  },
  section: {
    borderTopWidth: 1,
    borderTopColor: colors.hairline,
    paddingTop: spacing.m,
  },
  rowLabel: {
    color: colors.meta,
    fontSize: fontSize.caption,
    fontFamily: fontFamily.mono,
    marginTop: spacing.m,
  },
  rowValue: {
    color: colors.ink,
    fontSize: fontSize.label,
    lineHeight: 20,
    marginTop: spacing.xs,
  },
  traceList: {
    marginTop: spacing.l,
  },
  traceLine: {
    color: colors.termText,
    backgroundColor: colors.termBg,
    borderRadius: radius.sm,
    fontSize: fontSize.term,
    fontFamily: fontFamily.mono,
    lineHeight: 18,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.s,
    marginBottom: spacing.s,
  },
  skillCard: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    padding: spacing.m,
    marginBottom: spacing.m,
  },
  skillHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: spacing.s,
  },
  skillName: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '800',
  },
  skillStatus: {
    color: colors.meta,
    fontSize: fontSize.micro,
    textTransform: 'uppercase',
  },
  skillMeta: {
    color: colors.sub,
    fontSize: fontSize.micro,
    lineHeight: 18,
    marginTop: spacing.xs,
  },
});
```

- [ ] **Step 4: Verify the new files compile**

Run:

```powershell
cd app
npm run typecheck
```

Expected: TypeScript passes.

- [ ] **Step 5: Commit**

```powershell
git add app/package.json app/src/services/api.ts app/src/components/ProductResultCard.tsx app/src/components/AgentInsightPanel.tsx
git commit -m "feat: add demo result components and typed agent payloads"
```

## Task 4: Rework `HomeScreen` Into The Approved Demo Flow

**Files:**
- Modify: `app/src/screens/HomeScreen.tsx:17-795`
- Modify: `app/App.tsx:13-47`

- [ ] **Step 1: Add the missing state and helper functions to `HomeScreen`**

At the top of `HomeScreen.tsx`, change the imports to:

```tsx
import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  AppState,
  Keyboard,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import AgentInsightPanel from '../components/AgentInsightPanel';
import ProductResultCard from '../components/ProductResultCard';
import ApiService, {
  MemoryContext,
  ParsedQuery,
  Product,
  SearchResult,
  SkillRun,
  UserPreference,
} from '../services/api';
```

Replace `STAGES` with:

```tsx
const STAGES = [
  { key: 'queued', label: '解析需求，创建搜索任务' },
  { key: 'waiting_device', label: '等待设备空闲，准备执行综合搜索' },
  { key: 'controlling_phone', label: '控制手机，进入购物 App 搜索' },
  { key: 'extracting', label: '截屏并提取商品内容' },
  { key: 'ranking', label: '综合排序并生成解释' },
] as const;
```

Add these helpers above the component:

```tsx
function summarizePreference(preference: UserPreference | null): string {
  if (!preference) {
    return '暂无明显偏好';
  }
  const topBrand = Object.values(preference.brand_preferences)
    .sort((a, b) => b.score - a.score)[0]?.brand;
  const price = preference.price_preference
    ? `${Math.round(preference.price_preference.min)}-${Math.round(preference.price_preference.max)}`
    : '';
  const parts = [topBrand, price ? `¥${price}` : ''].filter(Boolean);
  return parts.length ? parts.join(' / ') : '暂无明显偏好';
}

function summarizeParsedQuery(parsedQuery: ParsedQuery | null): string {
  if (!parsedQuery) {
    return '';
  }
  const budget =
    parsedQuery.price_min != null && parsedQuery.price_max != null
      ? ` · ¥${Math.round(parsedQuery.price_min)}-${Math.round(parsedQuery.price_max)}`
      : '';
  return `${parsedQuery.category}${budget}`;
}

function isBudgetHit(product: Product, parsedQuery: ParsedQuery | null): boolean {
  if (
    !parsedQuery ||
    parsedQuery.price_min == null ||
    parsedQuery.price_max == null
  ) {
    return false;
  }
  return product.price >= parsedQuery.price_min && product.price <= parsedQuery.price_max;
}
```

Inside the component, add these state lines:

```tsx
  const [parsedQuery, setParsedQuery] = useState<ParsedQuery | null>(null);
  const [skillRuns, setSkillRuns] = useState<SkillRun[]>([]);
  const [memoryContext, setMemoryContext] = useState<MemoryContext | null>(null);
  const [preferenceHint, setPreferenceHint] = useState('暂无明显偏好');
  const [actionMessage, setActionMessage] = useState('');
  const [effectiveQuery, setEffectiveQuery] = useState('');
```

- [ ] **Step 2: Add result hydration, preference loading, and app-resume recovery**

Inside `HomeScreen`, add these helpers before `useEffect()`:

```tsx
  const applySearchResult = (result: SearchResult, message?: string) => {
    setTaskId(result.task_id);
    setProducts(result.products || []);
    setIsDemo(!!result.is_demo);
    setQuery(result.query || '');
    setParsedQuery(result.parsed_query || null);
    setStage(result.status === 'completed' ? 'done' : result.progress || '');
    setAgentTrace(result.agent_trace || []);
    setElapsedSeconds(result.elapsed_seconds ?? null);
    setSkillRuns(result.skill_runs || []);
    setMemoryContext(result.memory_context || null);
    setEffectiveQuery(result.effective_query || '');
    setStatusTone(result.is_demo ? 'warning' : 'success');
    setSearchStatus(message || `搜索完成，找到 ${result.products?.length || 0} 个商品`);
  };

  const applyInFlightSnapshot = (result: SearchResult, message?: string) => {
    setTaskId(result.task_id);
    setQuery(result.query || query);
    setParsedQuery(result.parsed_query || null);
    setStage(result.progress || 'queued');
    setAgentTrace(result.agent_trace || []);
    setElapsedSeconds(result.elapsed_seconds ?? null);
    setSkillRuns(result.skill_runs || []);
    setMemoryContext(result.memory_context || null);
    setEffectiveQuery(result.effective_query || '');
    setStatusTone('info');
    setSearchStatus(message || '已恢复当前搜索任务');
    setLoading(true);
  };

  const loadPreferenceHint = async () => {
    try {
      const pref = await ApiService.getUserPreference('default');
      setPreferenceHint(summarizePreference(pref));
    } catch {
      setPreferenceHint('暂无明显偏好');
    }
  };

  const restoreLatestResult = async (message?: string) => {
    const result = await ApiService.getLatestSearchResult('default');
    if (!result || result.status !== 'completed') {
      return;
    }
    applySearchResult(result, message);
  };

  const restoreTaskState = async (messages?: { active?: string; fallback?: string }) => {
    if (taskId) {
      try {
        const result = await ApiService.getSearchResult(taskId);
        if (result.status === 'completed') {
          applySearchResult(result, messages?.active || '已恢复当前搜索任务');
          return;
        }
        if (result.status === 'failed') {
          setStage('failed');
          setStatusTone('error');
          setSearchStatus(
            `${messages?.active || '已恢复当前搜索任务'}：${result.error || '未知错误'}`
          );
          setParsedQuery(result.parsed_query || null);
          setSkillRuns(result.skill_runs || []);
          setMemoryContext(result.memory_context || null);
          setEffectiveQuery(result.effective_query || '');
          setLoading(false);
          return;
        }
        applyInFlightSnapshot(result, messages?.active || '已恢复当前搜索任务');
        return;
      } catch {
        // 回退到最近已完成结果
      }
    }
    await restoreLatestResult(messages?.fallback || '已恢复最近搜索结果');
  };
```

Replace the current mount `useEffect()` with:

```tsx
  useEffect(() => {
    let cancelled = false;

    const boot = async () => {
      await loadPreferenceHint();
      try {
        if (!cancelled) {
          await restoreLatestResult('已恢复最近搜索结果');
        }
      } catch {
        // 首屏恢复失败不阻断新搜索
      }
    };

    boot();

    const subscription = AppState.addEventListener('change', (state) => {
      if (state !== 'active') {
        return;
      }
      if (loading || taskId) {
        restoreTaskState({
          active: '已从后台恢复当前任务',
          fallback: '已从后台恢复最近结果',
        }).catch(() => undefined);
        return;
      }
      restoreLatestResult('已从后台恢复最近结果').catch(() => undefined);
    });

    return () => {
      cancelled = true;
      subscription.remove();
    };
  }, [loading, taskId]);
```

- [ ] **Step 3: Update the search and click handlers**

In `handleProductClick()`, replace the body with:

```tsx
  const handleProductClick = async (product: Product) => {
    if (!product.is_demo && !clickedIds.includes(product.id)) {
      setClickedIds((prev) => [...prev, product.id]);
      try {
        const insight = await ApiService.recordAction({
          user_id: 'default',
          action_type: 'click',
          product_id: product.id,
          task_id: taskId,
        });
        if (insight) {
          setMemoryContext(insight);
        }
        setActionMessage('已记录你的偏好');
        await loadPreferenceHint();
      } catch {
        setActionMessage('偏好记录失败，请稍后重试');
      }
    }
    openProductOnPlatform(product);
  };
```

Inside `handleSearch()`, after `setClickedIds([]);`, add:

```tsx
    setParsedQuery(null);
    setSkillRuns([]);
    setMemoryContext(null);
    setActionMessage('');
    setEffectiveQuery('');
```

Inside the `result.status === 'completed'` branch, replace the state updates with:

```tsx
          applySearchResult(result);
          setLoading(false);
          await loadPreferenceHint();
```

Inside the `result.status === 'failed'` branch, add:

```tsx
          setTaskId(result.task_id);
          setParsedQuery(result.parsed_query || null);
          setSkillRuns(result.skill_runs || []);
          setMemoryContext(result.memory_context || null);
          setEffectiveQuery(result.effective_query || '');
```

Inside the `else` branch for in-progress polling, add:

```tsx
          setTaskId(result.task_id);
          setParsedQuery(result.parsed_query || null);
          setSkillRuns(result.skill_runs || []);
          setMemoryContext(result.memory_context || null);
          setEffectiveQuery(result.effective_query || '');
```

- [ ] **Step 4: Replace the progress/status area and result rendering with the product-first + agent-layer layout**

Inside the search box JSX, add the preference hint below the platform selector:

```tsx
        <Text style={styles.preferenceHint}>最近偏好：{preferenceHint}</Text>
```

Replace the current completed-state `AGENT TRACE` terminal block with a compact progress card that only renders while the task is loading, failed, or has no results yet:

```tsx
      {searchStatus && (loading || stage === 'failed' || products.length === 0) ? (
        <View style={styles.progressCard} accessibilityLabel={`当前搜索状态：${searchStatus}`}>
          <Text style={styles.progressTitle}>{loading ? '搜索进行中' : '搜索状态'}</Text>
          <Text style={[styles.progressMessage, statusMessageStyle]}>{searchStatus}</Text>
          {loading ? (
            <View style={styles.progressStages}>
              {STAGES.map((s, index) => {
                const mark = stageMark(index);
                return (
                  <View key={s.key} style={styles.termLine}>
                    <Text style={[styles.termIcon, mark.style]}>{mark.icon}</Text>
                    <Text style={styles.termStep}>{s.label}</Text>
                  </View>
                );
              })}
            </View>
          ) : null}
        </View>
      ) : null}
```

This replaces the old always-visible developer terminal. After completion, technical detail must live only inside `AgentInsightPanel` under the product results.

Below the progress card, add the feedback banner:

```tsx
      {actionMessage ? (
        <View style={styles.actionBanner}>
          <Text style={styles.actionBannerText}>{actionMessage}</Text>
        </View>
      ) : null}
```

Replace the `products.map(...)` block with:

```tsx
          {parsedQuery ? (
            <Text style={styles.intentSummary}>{summarizeParsedQuery(parsedQuery)}</Text>
          ) : null}

          {products.map((product) => (
            <ProductResultCard
              key={product.id}
              product={product}
              clicked={clickedIds.includes(product.id)}
              budgetHit={isBudgetHit(product, parsedQuery)}
              onPress={() => handleProductClick(product)}
            />
          ))}

          <AgentInsightPanel
            parsedQuery={parsedQuery}
            effectiveQuery={effectiveQuery}
            elapsedSeconds={elapsedSeconds}
            agentTrace={agentTrace}
            skillRuns={skillRuns}
            memoryContext={memoryContext}
          />
```

Add these styles near the other `StyleSheet` entries:

```tsx
  preferenceHint: {
    marginTop: spacing.m,
    color: colors.meta,
    fontSize: fontSize.micro,
  },
  actionBanner: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    backgroundColor: colors.prefBg,
    borderRadius: radius.sm,
    padding: spacing.m,
  },
  actionBannerText: {
    color: colors.prefFg,
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  progressCard: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.l,
  },
  progressTitle: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '800',
  },
  progressMessage: {
    marginTop: spacing.s,
    fontSize: fontSize.micro,
  },
  progressStages: {
    marginTop: spacing.m,
  },
  intentSummary: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '700',
    marginTop: spacing.s,
    marginBottom: spacing.s,
  },
```

- [ ] **Step 5: Simplify the app shell to the single-screen demo**

Replace `app/App.tsx` with:

```tsx
import React from 'react';
import { LogBox, StyleSheet } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import HomeScreen from './src/screens/HomeScreen';
import { colors } from './src/theme/tokens';

LogBox.ignoreAllLogs();

export default function App() {
  return (
    <SafeAreaProvider style={styles.provider}>
      <SafeAreaView style={styles.container}>
        <HomeScreen />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  provider: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
});
```

- [ ] **Step 6: Typecheck the app**

Run:

```powershell
cd app
npm run typecheck
```

Expected: TypeScript passes.

- [ ] **Step 7: Commit**

```powershell
git add app/src/screens/HomeScreen.tsx app/App.tsx
git commit -m "feat: ship the single-screen agent demo flow"
```

## Task 5: Update The GitHub Story And Run Final Verification

**Files:**
- Modify: `README.md:1-170`
- Modify: `app/README.md:1-83`

- [ ] **Step 1: Update the root README to match the final demo**

In `README.md`, replace the project intro paragraph with:

```markdown
SmartCart 让用户在手机上输入一句自然语言购物需求，例如“我想要 800 元左右的蓝牙耳机”，由 Agent 自动完成：

1. **需求理解**：GLM 解析自然语言，提取品类、预算和特性。
2. **读取记忆**：Memory 提供品牌、价格区间和近期查询信号。
3. **综合搜索**：`AgentRuntime` 调度京东和淘宝技能，真实控制手机完成搜索。
4. **商品提取**：后端主动截屏，并用 `glm-4v-flash` 提取结构化商品。
5. **推荐排序**：跨平台结果按当前需求与历史偏好重排，并给出推荐理由。
6. **Agent 可视化**：结果页下半部分可展开 `Trace / Skills / Memory`，直接证明这是一个 Agent 系统。
7. **偏好闭环**：点击商品写回 Memory，第二次相似搜索能看见排序和解释变化。
```

Replace the Quick Start app command section with:

```markdown
### 3. 启动移动端（真机录屏路径）

```bash
cd SmartCart/app
npm install
npx expo start --android --host localhost
```

这里必须使用 `--host localhost`，配合现有 `adb reverse` 与 `exp://localhost:8081` 切回链路，确保 AutoGLM 接管手机后还能稳定返回 SmartCart。
```

Replace the demo-script section with:

```markdown
## 演示视频脚本

建议录制 90-120 秒，按下面的完整闭环来拍：

1. 展示 `uvicorn main:app --host 0.0.0.0 --port 8000` 和 `npx expo start --android --host localhost`。
2. 手机打开 SmartCart，首页显示 `综合` 默认选中与最近偏好提示。
3. 输入 `我想要800元左右的蓝牙耳机`，点击搜索。
4. 手机被 Agent 控制到京东 / 淘宝完成搜索。
5. App 回到前台，展示商品层结果。
6. 展开 `Agent 视角`，依次切 `Trace / Skills / Memory`。
7. 点击一个真实商品，看到 `已记录你的偏好`。
8. 再搜一次相似需求，展示 Memory 命中和排序变化。
```

Add this note under the architecture section:

```markdown
`Skills` Tab 中的 `duration_seconds` 是解释慢点的关键证据：`综合` 模式虽然在编排层 fan-out，但单手机真实执行仍要经过设备池串行，所以 reviewer 可以直接看到每个源各花了多久。
```

- [ ] **Step 2: Update `app/README.md` for the same localhost demo path**

In `app/README.md`, replace the backend-address explanation and startup commands with:

```markdown
### 2. 运行 App（真机录屏推荐）

```bash
npx expo start --android --host localhost
```

当前 demo 默认使用 `exp://localhost:8081` 切回 App，并依赖 `adb reverse` 把手机的 `localhost:8081` 和 `localhost:8000` 反向映射到开发机。

结果页中已经内置：

- Product layer：商品卡片、预算命中、推荐理由、最低价标签
- Agent layer：可展开的 `Trace / Skills / Memory`
- Memory feedback：点击商品后立即记录偏好，并用于下一次搜索
```

- [ ] **Step 3: Run the final automated verification**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all backend tests pass.

Run:

```powershell
cd app
npm run typecheck
```

Expected: TypeScript passes.

- [ ] **Step 4: Run the manual phone acceptance flow**

Start the backend:

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Start Expo in localhost mode:

```powershell
cd app
npx expo start --android --host localhost
```

Then verify this exact flow on the connected phone:

1. Open SmartCart and confirm `综合` is the default platform.
2. Enter `我想要800元左右的蓝牙耳机`.
3. Wait for the app to leave to JD/Taobao and return.
4. Confirm the result screen shows:
   - parsed budget summary
   - product cards
   - recommendation reasons
   - collapsible `Agent 视角`
5. Expand `Trace` and confirm:
   - parsed intent
   - effective query
   - source summary
   - ranking summary
   - elapsed seconds
6. Expand `Skills` and confirm there is one row per source with duration and product count.
7. Expand `Memory` and confirm:
   - learned brands
   - learned price range
   - recent queries
   - matched signal summary
8. Tap one real product.
9. Search again with a similar query and confirm `Memory` / explanation / ordering change.

- [ ] **Step 5: Add the timing and log sanity check for slow runs**

If the `综合` run still exceeds 120 seconds, run:

```powershell
Get-ChildItem D:\Study\project\SmartCart\backend\data\debug_logs |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 4 Name, LastWriteTime
```

And compare that with what the app shows in `Skills`:

- if one source is very slow, inspect that source’s newest debug log
- if both sources are moderate but total wall time is large, check whether the app spent time in `waiting_device`
- if extraction is slow, compare `skill_runs.duration_seconds` with the end-to-end `elapsed_seconds`

The submission target is met when the main recorded path is usually within `90-120s` and the UI makes any residual waiting explainable.

- [ ] **Step 6: Commit**

```powershell
git add README.md app/README.md
git commit -m "docs: align the repo story with the agent demo flow"
```

## Final Verification Gate

- [ ] **Step 1: Confirm the working tree only contains plan-approved changes**

Run:

```powershell
git status --short --branch
```

Expected: only the files listed in this plan are modified, plus the pre-existing dirty files called out in Baseline.

- [ ] **Step 2: Confirm the final command set**

Run:

```powershell
cd backend
python -c "import main; print(main.app.title)"
```

Expected:

```text
SmartCart API
```

Run:

```powershell
cd app
npm run typecheck
```

Expected: passes.

## Plan Self-Review

Spec coverage:

- Search home with natural-language input and `综合` default: Task 4.
- In-progress state and recovery after app returns from background: Tasks 2 and 4.
- Result screen product layer: Tasks 3 and 4.
- Result screen technical layer with `Trace / Skills / Memory`: Tasks 3 and 4.
- Structured `skill_runs` in backend results: Tasks 1 and 2.
- Product tap feedback loop through `/api/preference/action`: Task 4.
- Second-search memory demonstration: Tasks 4 and 5.
- Real-phone `综合` path as the main submission flow: Task 5.
- Stable GitHub story and recording instructions: Task 5.
- Budget-hit marker in the product layer: Tasks 3 and 4.

Placeholder scan:

- No `TODO`, `TBD`, “implement later”, or “similar to Task N” placeholders remain.

Consistency checks:

- Backend uses one field name end-to-end: `skill_runs`.
- Memory-tab signal summary uses one nested key end-to-end: `memory_context.matched_signals`.
- Frontend result payload uses backend-native names: `parsed_query`, `effective_query`, `agent_trace`, `elapsed_seconds`, `skill_runs`.
- App resume first attempts the active `task_id`, then falls back to the latest completed result.
