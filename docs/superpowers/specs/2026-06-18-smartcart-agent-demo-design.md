# SmartCart Agent Demo Design

## Goal

Turn SmartCart into a small, recordable mobile Agent demo for job submission: a real phone can run a natural-language shopping task in `综合` mode, return to the app with cross-platform results, and expose enough `Trace / Skills / Memory` detail to prove this is an Agent system rather than a plain search UI.

This design intentionally optimizes for a stable demo video and a clear GitHub story. It does not aim to become a broad multi-scenario agent platform in this iteration.

## Product Positioning

The product should be presented as:

**A mobile consumer-decision Agent demo that runs on a real phone.**

It has two visible layers:

1. **Product layer**: the user enters a natural-language shopping request, the app performs real cross-platform search, and the app returns understandable recommendations.
2. **Agent layer**: the app exposes planning trace, skill execution, and learned preference memory so reviewers can see a real `memory + skill + mobile execution` system behind the UI.

The key review signals are:

- it runs on a phone
- it drives real shopping apps through Open-AutoGLM
- it has visible `memory / skill / trace`
- user behavior can influence a later search

## Demo Scope

This submission is deliberately narrow.

The primary scenario is:

- user enters `我想要800元左右的蓝牙耳机`
- app runs `综合` mode against JD and Taobao
- app returns to foreground and shows ranked results
- reviewer expands `Trace / Skills / Memory`
- reviewer taps one product
- a second similar search shows memory influence

This is the full story. The app does not need more scenarios for this submission.

## Non-Goals

- No multi-scenario expansion beyond shopping.
- No standalone admin console or backend dashboard.
- No heavy self-evolution UI.
- No generic agent platform packaging.
- No large frontend redesign unrelated to the demo.
- No full replacement of Open-AutoGLM with deterministic scripts.
- No broad architecture refactor beyond what directly supports the demo.

## Experience Design

### Search Home

The home screen has one job: start a shopping task.

Required elements:

- natural-language input
- platform selector with default `综合`
- start button
- a very small recent-preference summary, such as `最近偏好：OPPO / 640-960`

This screen should feel like a product entry point, not a developer console.

### In-Progress State

This is a lightweight transition state, not a large separate page.

It should show:

- current task phase such as `解析需求 / 调用技能 / 排序中`
- task recovery state after the app returns from background

This is necessary because Open-AutoGLM takes over the phone during real execution and the app must recover cleanly afterward.

### Result Screen

The result screen is split into two layers.

#### Product Layer

The upper half is the reviewer-friendly product surface:

- parsed intent summary, for example `蓝牙耳机 · ¥640-960`
- product cards
- recommendation reason
- budget hit marker
- platform label
- lowest-price tag when available

#### Agent Layer

The lower half is a collapsible technical section with three tabs:

- `Trace`
- `Skills`
- `Memory`

This section must be visible enough for technical reviewers, but it must not dominate the first impression of the screen.

## Agent Observability Design

### Trace Tab

`Trace` shows the execution summary of the current task.

It should include:

- parsed intent
- effective query
- source execution summary
- ranking summary
- total elapsed time

It should use compact user-facing lines, not raw internal logs.

Primary data source:

- existing `agent_trace`
- existing `effective_query`
- existing `elapsed_seconds`

### Skills Tab

`Skills` makes the skill system visible without exposing raw debug dumps.

It should show, for each skill run:

- skill name
- platform
- query
- status
- elapsed seconds
- product count

This requires one new structured field in search results:

- `skill_runs`

Recommended shape:

```json
[
  {
    "skill_name": "jd_search",
    "platform": "jd",
    "query": "蓝牙耳机",
    "status": "completed",
    "duration_seconds": 94.0,
    "product_count": 8
  }
]
```

The frontend should read this directly instead of re-parsing strings from `agent_trace`.

### Memory Tab

`Memory` shows what the system currently knows about the user.

It should display:

- learned brand preferences
- learned price range
- recent queries
- whether this task matched memory signals

Primary data source:

- existing `memory_context`

This tab is also where the second search should visibly prove that memory influenced the system.

## Data Flow

The main product flow remains the existing backend shape:

1. frontend calls `POST /api/search`
2. backend creates `task_id`
3. `AgentRuntime` performs:
   - query parsing
   - memory lookup
   - effective query construction
   - skill dispatch to JD and Taobao
   - merge and rerank
   - task persistence
4. frontend polls `GET /api/search/{task_id}`
5. after phone execution, the app returns to foreground and restores the result screen

This should be preserved. The MVP should not replace the flow with a new orchestration model.

## Memory Loop

The submission needs only one lightweight memory loop.

### First Search

The user searches and sees results plus current memory state.

### Product Tap

When the user taps a product:

1. frontend sends `/api/preference/action`
2. backend records product interaction
3. preference memory updates
4. frontend shows a small acknowledgment like `已记录你的偏好`

### Second Search

The next similar search should make memory visible through:

- changed `Memory` tab contents
- changed recommendation reasons
- possibly changed product ordering

The MVP does not need an animated live diff system. The effect only needs to be visible on the second run.

## Performance Strategy

The goal is not to remove the agent nature of the product. The goal is to keep the demo stable enough for recording.

### Parts That Must Stay Agent-Driven

These should remain inside the agent story:

- natural-language intent parsing
- memory lookup and use
- skill dispatch
- cross-platform aggregation and ranking
- result explanation
- fallback behavior when execution diverges

### Allowed Controlled Acceleration

These optimizations are acceptable because they do not erase the agent structure:

- skip repeated startup checks
- cap model timeout and retries
- finish early when target page state is already reached
- reduce fixed action waits where safe
- add guarded fast paths for repetitive execution steps

Any fast path must remain a **controlled execution strategy**, not a hard replacement of the agent. If page state does not match expectation, the flow must fall back to Open-AutoGLM.

### Demo Timing Target

For the submission video, the primary `综合` flow should target:

- usually within `90-120s`
- ideally below `2 minutes`

It is acceptable that cold starts occasionally take longer during development, but the final recorded path should be selected from a stable run.

## MVP Implementation Scope

### Required

1. Search home with natural-language input and `综合` default.
2. In-progress state with task recovery.
3. Result screen product layer.
4. Result screen technical layer with `Trace / Skills / Memory`.
5. Structured `skill_runs` in backend search results.
6. Product tap feedback loop through existing preference action endpoint.
7. Second-search memory demonstration.
8. Real-phone `综合` mode retained as the main demo path.

### Explicitly Out of Scope

1. More product categories or scenarios.
2. Rich autonomous self-improvement workflows.
3. Separate technical dashboard.
4. Converting the project into a generic agent platform.
5. Large visual redesign unrelated to the demo story.

## Testing And Validation

### Automated

Backend:

- keep existing backend tests green
- add tests for structured `skill_runs`
- add tests that result payloads include `Trace / Skills / Memory` source fields

Frontend:

- typecheck must pass after adding new result fields

Open-AutoGLM:

- keep the added startup-check and model-config tests passing

### Manual Acceptance

The feature is accepted when this exact recording-friendly flow works on a real phone:

1. open the app on phone
2. enter `我想要800元左右的蓝牙耳机`
3. run `综合`
4. return to the app and show results
5. expand `Trace / Skills / Memory`
6. tap a product
7. search again
8. show visible memory influence

## Acceptance Criteria

The submission-ready demo is complete only when:

- the app runs on a real phone
- `综合` mode returns real JD and Taobao search results
- the result screen exposes `Trace / Skills / Memory`
- product taps update preference memory
- a second search shows memory influence
- the main demo can be recorded end-to-end in roughly two minutes
- the UI still reads as a product first, not a raw debug console

## Recommended Next Step

After this spec, implementation should focus on the smallest shippable path:

1. structure backend `skill_runs`
2. build result-page technical tabs
3. verify tap-to-memory loop
4. tune the real-phone demo path for recording stability
