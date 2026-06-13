# SmartCart Agent Architecture Upgrade Design

## Goal

Upgrade SmartCart from a working mobile shopping demo into a single-user complete product prototype with clear Agent architecture: Skill registry, MCP tool exposure, memory-driven self-evolution, visible reasoning trace, tests, and documentation.

This design intentionally does not introduce multi-user accounts, SQLite persistence, deployment packaging, or a production queue. The current true-device Taobao automation path is valuable and must remain stable.

## Product Scope

SmartCart remains a single-user mobile AI shopping assistant. The user enters a natural-language shopping request, the backend parses the request, reads memory, adjusts the search strategy conservatively, calls registered skills, extracts real Taobao products through Open-AutoGLM and GLM-4V, reranks products with preference evidence, and returns an explanation the App can show.

The target experience is:

1. User searches: `我想买 500 元左右的蓝牙耳机`.
2. App shows an Agent trace such as:
   - `解析需求 -> 蓝牙耳机 · ¥400-600`
   - `读取记忆 -> 偏好 华为 / 降噪`
   - `调整搜索 -> 蓝牙耳机 华为 降噪`
   - `调用工具 -> taobao_search`
   - `推荐排序 -> 3 个商品，2 个命中偏好`
3. User sees real products, recommendation scores, and short recommendation reasons.
4. User clicks a product.
5. Preference memory updates.
6. The next similar search visibly uses memory without overriding explicit user intent.

## Non-Goals

- No user login or account system.
- No SQLite or database migration in this iteration.
- No multi-device concurrency model beyond the existing device lock.
- No Docker or cloud deployment work.
- No replacement of FastAPI with MCP. FastAPI remains the mobile product API.
- No large frontend redesign. UI changes are limited to trace, recommendation reasons, and preference visibility.

## Architecture

Current FastAPI endpoints stay in place for the mobile App. A new `AgentRuntime` layer becomes the orchestration boundary so `main.py` does not directly stitch together parsing, memory, search, ranking, and task tracing.

```text
React Native App
        |
        | REST
        v
FastAPI endpoints
        |
        v
AgentRuntime
  |-- QueryParserService
  |-- MemoryContextService
  |-- SkillRegistry
        |-- taobao_search
        |-- get_preference_insight
        |-- record_product_action
        |-- rerank_products
        |
        v
SearchResult + AgentTrace + RecommendationReason

MCP Server
        |
        v
SkillRegistry tools
```

FastAPI and MCP share the same skill registry. This makes MCP a real tool entry point rather than a parallel demo implementation.

## Backend Components

### AgentRuntime

`AgentRuntime` owns the search workflow:

1. Create trace entries as each stage completes.
2. Parse the user request.
3. Load memory context.
4. Build an effective query from parsed intent and memory.
5. Call `taobao_search` through `SkillRegistry`.
6. Call `rerank_products` through `SkillRegistry`.
7. Return products with trace, effective query, memory context, score, and reason.

`AgentRuntime` should be testable with mock skills. It must not require ADB, Taobao, GLM, or Open-AutoGLM in unit tests.

### Skill Base

Every skill exposes:

- `name`: unique identifier and MCP tool name.
- `description`: human-readable capability description.
- `parameters`: JSON Schema compatible with MCP tool input schema.
- `run(**kwargs)`: execution method.
- `describe()`: stable description used by registry, REST diagnostics, and MCP.

Skill implementation should be synchronous for this iteration, matching current backend style. If a future skill becomes async, the registry can later add async support without changing the product API now.

### SkillRegistry

`SkillRegistry` owns registration, discovery, lookup, and invocation.

Required behavior:

- Register skill instances by unique `name`.
- Reject duplicate names.
- Raise a clear error for unknown skill calls.
- Return a stable list of tool descriptions.
- Invoke skills by name with keyword arguments.

The registry becomes the integration surface for both AgentRuntime and MCP.

### Skills

#### `taobao_search`

Wraps the existing `TaobaoSearchSkill` behavior:

- Runs Open-AutoGLM automation.
- Captures screenshot through ADB.
- Extracts products with GLM-4V.
- Preserves existing demo fallback and `is_demo` visibility.

This skill must not be heavily rewritten. The current true-device path is already validated and should remain the highest-risk area with the smallest change set.

#### `get_preference_insight`

Reads current preference data and returns a compact memory context:

- preferred brands
- preferred price range
- preferred feature keywords
- recent search/click summary
- confidence signals used for query injection

It should be conservative. Empty memory should produce an empty but valid context, not an error.

#### `record_product_action`

Provides a skill-level wrapper for the existing behavior recording flow:

- Accepts `task_id`, `product_id`, and `action_type`.
- Looks up the product from the task result.
- Records click/view into `PreferenceService`.
- Returns updated lightweight preference insight when useful.

FastAPI can keep its existing endpoint contract, but the endpoint should delegate to this skill or a shared service so behavior is not duplicated.

#### `rerank_products`

Reranks products using memory and parsed intent, then returns:

- sorted products
- `recommendation_score`
- `recommendation_reason`
- summary counts for trace, such as number of products matching memory

Reasons should be short and product-facing:

- `命中你常看的华为品牌`
- `价格接近你最近偏好的 400-600 元区间`
- `标题包含你常关注的降噪特性`
- `探索项：价格更接近本次预算`

## Memory And Self-Evolution

Memory affects two points in the flow: before search and after product extraction.

### Before Search

The effective query is built from parsed intent plus memory context.

Rules:

- User intent always wins over memory.
- Base category keywords are always preserved.
- Inject at most one brand when brand preference confidence is high.
- Inject at most one feature keyword when feature preference confidence is high.
- Do not inject a brand if the user explicitly excludes it.
- Do not inject a brand if the user asks for broad comparison, such as `不限品牌` or `随便看看`.

Example:

```text
Raw query: 我想买 500 元左右的蓝牙耳机
Parsed intent: 蓝牙耳机, budget 400-600
Memory: prefers 华为, 降噪
Effective query: 蓝牙耳机 华为 降噪
```

### After Search

Products are ranked by:

- direct match to current parsed intent
- price proximity to current budget
- brand preference match
- feature preference match
- exploration fallback when memory is weak

Each product receives a reason so the user can understand why the Agent changed the order.

## API And Data Model Changes

Search task responses should add these fields while preserving existing fields:

- `agent_trace: list[str]`
- `memory_context: dict`
- `effective_query: str`
- `products[].recommendation_score: float`
- `products[].recommendation_reason: str`

The frontend should tolerate missing fields so old task files remain readable.

## MCP Design

Add `backend/mcp_server.py`.

The MCP server should build tools from `SkillRegistry` descriptions and forward calls back to the registry. The MCP layer should not know Taobao internals, preference file formats, task file formats, or GLM details.

First tool set:

- `taobao_search`
- `get_preference_insight`
- `record_product_action`
- `rerank_products`

MCP is accepted when it can list tools and call registry-backed tools in tests without starting a real phone automation session.

## Frontend Changes

The App should show intelligence without becoming a log viewer.

### Search And Result View

Add a compact Agent trace area. It should show only key stages, not raw logs:

- parse result
- memory insight
- effective query
- tool call
- reranking summary

### Product Cards

Each product card shows:

- existing title, price, brand/store information
- demo badge when `is_demo` is true
- one short recommendation reason when present

The recommendation reason should be visually secondary. It must not crowd the product title or price.

### Preference View

Preference page should continue showing learned preferences, and can add a small "Agent 学到了" summary from `memory_context` when available.

## Testing

### Backend Unit Tests

Add or update:

- `backend/test_skill_registry.py`
  - registers a skill
  - rejects duplicate skill names
  - raises clear error for unknown skill
  - exports descriptions compatible with MCP input schema

- `backend/test_agent_runtime.py`
  - generates trace with mocked skills
  - injects memory into effective query conservatively
  - keeps explicit user intent ahead of memory
  - calls rerank skill and returns recommendation reasons

- `backend/test_mcp_server.py`
  - builds MCP tool definitions from registry
  - forwards tool calls to registry
  - does not require true device, Taobao, ADB, or GLM

Keep existing backend tests passing:

- `backend/test_preference_ranking.py`
- `backend/test_taobao_parsing.py`
- `backend/test_taobao_search_env.py`
- `backend/test_latest_task_api.py`

### Frontend Checks

Add `npm run typecheck` if missing. The App must typecheck after adding new response fields.

### Manual True-Device Acceptance

Manual flow:

1. Start backend.
2. Start Expo App.
3. Search `我想买 500 元左右的蓝牙耳机`.
4. Confirm Agent trace shows parse, memory, effective query, skill call, and ranking.
5. Confirm AutoGLM controls Taobao and returns real products.
6. Click a product.
7. Confirm preference memory updates.
8. Run a similar search.
9. Confirm trace shows memory usage and product cards show recommendation reasons.

## Documentation

Update:

- `README.md`
  - current status includes AgentRuntime, SkillRegistry, MCP, and memory self-evolution
  - architecture diagram includes FastAPI, AgentRuntime, SkillRegistry, MCP Server, and App
  - quick start includes MCP server command
  - demo script uses visible Agent trace

- `IMPLEMENTATION.md`
  - add Phase 6: Agent architecture upgrade
  - record completed checks and remaining future extensions honestly

Add:

- `docs/superpowers/plans/2026-06-13-agent-architecture-upgrade.md` after this design is approved.

## Acceptance Criteria

The upgrade is complete only when:

- `pytest` passes.
- `npm run typecheck` passes.
- FastAPI backend starts.
- MCP server can list and call registry-backed tools in tests.
- App can display `agent_trace`, `effective_query`, and product recommendation reasons.
- Existing true-device Taobao search path remains working.
- Existing demo fallback remains visible as demo data.
- README explains the product as a mobile AI Agent, not only an API demo.

## Implementation Order

1. Add Skill base and registry tests.
2. Implement Skill base and registry.
3. Add AgentRuntime tests with mock skills.
4. Implement AgentRuntime and conservative effective query logic.
5. Wrap existing Taobao, preference insight, behavior recording, and reranking as registered skills.
6. Add MCP tests and server wrapper.
7. Update FastAPI endpoints to delegate through AgentRuntime or registry-backed skills.
8. Update frontend types and UI for trace and recommendation reasons.
9. Update README and IMPLEMENTATION.
10. Run automated checks and perform the manual true-device acceptance flow.

