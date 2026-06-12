# SmartCart 实现文档

本文档记录项目的真实现状、技术方案和分阶段开发路线。每完成一个阶段，更新对应的验收清单。

---

## 一、现状评估（2026-06-12）

### 已可用

| 模块 | 文件 | 状态 |
|------|------|------|
| FastAPI 后端框架 | `backend/main.py` | ✅ 搜索任务创建/查询、偏好查询 API 可用 |
| 需求解析 | `backend/services/query_parser.py` | ✅ GLM 解析 + 失败降级 |
| 偏好学习服务 | `backend/services/preference_service.py` | ✅ 逻辑完整，含权重生成 |
| 淘宝搜索 Skill | `backend/skills/taobao_search.py` | ⚠️ 能驱动真机操作，但见下方断点 1 |
| App 搜索页/偏好页 | `app/src/screens/` | ✅ 界面与轮询逻辑可用 |
| 演示模式 | `demo_mode=True` | ✅ 模拟数据跑通全流程 |

### 已知断点（按严重程度排序）

**断点 1：真实模式的商品提取永远拿不到截图**
`taobao_search.py` 的 `_extract_products_from_screenshot()` 在 `Open-AutoGLM/screenshots/` 目录找截图，但 Open-AutoGLM 不会把截图持久化到磁盘（截图只在内存中传给模型）。因此真实模式必然静默降级到模拟数据——手机真的在搜索，App 显示的却是假商品。

**断点 2：用户行为记录是空壳**
`main.py` 的 `POST /api/preference/action` 两个分支都是 `TODO: pass`，且前端商品卡片没有点击事件、从未调用 `recordAction`。Memory 的 view/click 学习在产品流程中不会发生。

**断点 3：推荐权重没有消费方**
`get_recommendation_weights()` 已实现，但搜索结果排序完全没有使用它，"自进化"未闭环。

**断点 4：前端进度提示与真实状态无关**
`HomeScreen.tsx` 按轮询次数猜测进度（"正在打开淘宝…"），后端失败时界面仍在演进度。

**断点 5：真机 App 未验证**
只测过 `npm run web`。`api.ts` 硬编码 `localhost:8000`，真机上无法连接后端。

---

## 二、技术方案

### 断点 1 的修复方案：后端自行截屏

不依赖 Open-AutoGLM 保存截图。在 subprocess 执行完毕（手机停留在淘宝搜索结果页）后，由后端直接截屏：

```
adb exec-out screencap -p > screenshot.png
```

然后将截图喂给 GLM-4V 提取商品。改动集中在 `TaobaoSearchSkill`：

1. `search()` 中 subprocess 成功返回后，调用新方法 `_capture_screenshot()`（用 `config.ADB_PATH` 下的 adb）
2. `_extract_products_from_screenshot()` 改为接收明确的截图路径，不再扫目录
3. 任何降级到模拟数据的路径，必须在返回结果中带 `is_demo=True` 标记（模型 `Product` 或 `SearchResult` 增加字段），前端显式展示"演示数据"角标

### 断点 2/3 的修复方案：Memory 闭环

1. 后端：`record_user_action` 根据 `task_id` + `product_id` 从 `data/tasks/*.json` 中找到商品对象，调用 `preference_service.record_product_view/click`（请求体需带 `task_id`）
2. 前端：商品卡片加 `onPress`，调用 `ApiService.recordAction({action_type: 'click', product_id, task_id})`
3. 排序：`execute_search_task` 在保存结果前，用 `get_recommendation_weights(user_id)` 对 products 计算得分（品牌命中加权 + 价格落在偏好区间加权）并排序

### 断点 4 的修复方案：真实进度状态

后端任务文件增加 `progress` 字段（`parsing / controlling_phone / extracting / completed / failed`），`execute_search_task` 在每个阶段更新任务 JSON；前端轮询时直接显示后端返回的阶段文案。

### 断点 5 的修复方案：真机连接

`api.ts` 的 `API_BASE_URL` 改为可配置（Expo 的 `app.json` extra 字段或环境变量），文档写明如何填局域网 IP。

---

## 三、开发路线

### Phase 1：打通真实链路（最高优先级）

- [ ] `TaobaoSearchSkill` 增加 `_capture_screenshot()`（adb screencap）
- [ ] 截图提取改为显式路径传入
- [ ] `Product`/`SearchResult` 增加 `is_demo` 字段，降级路径全部标记
- [ ] 前端展示"演示数据"角标
- [ ] 真机端到端测试一次：输入需求 → 手机自动搜淘宝 → GLM-4V 提取 → App 显示真实商品

**验收**：App 中显示的商品标题/价格与手机淘宝页面实际内容一致。

### Phase 2：Memory 与自进化闭环

- [ ] `record_user_action` 实现（从任务文件查商品 → 调 preference_service）
- [ ] `UserAction` 模型增加 `task_id` 字段
- [ ] 前端商品卡片 onPress 上报点击
- [ ] 搜索结果按偏好权重重排序
- [ ] 验证：点击某品牌商品 2-3 次后，再次搜索时该品牌排序明显靠前

**验收**：演示"搜索 → 点击 → 再搜索，排序变化"的完整故事线。

### Phase 3：真实进度与真机运行

- [ ] 后端任务增加 `progress` 阶段字段并逐阶段更新
- [ ] 前端进度文案改为读后端状态
- [ ] `API_BASE_URL` 可配置
- [ ] Expo Go 真机运行验证（App 与被控手机可以是同一台或两台）

**验收**：手机上的 App 完成一次真实搜索全流程。

### Phase 4：打磨与提交材料

- [ ] UI 优化：商品图片占位、加载骨架屏、空状态
- [ ] 录制演示视频（建议分镜：真机自动操作画面 + App 画面同框）
- [ ] README 状态区更新（"进行中"项移入"已实现"）
- [ ] 可选加分项：京东搜索 Skill（验证 Skill 机制的可复用性）

**验收**：演示视频 + GitHub 仓库可以直接作为作业提交。

---

## 四、约定

- **诚实原则**：任何降级/模拟行为必须对用户可见，文档不写未实现的功能
- **密钥安全**：API Key 只存在于 `Open-AutoGLM/.env`（已 gitignore），任何文档/代码/日志不得出现 Key 内容
- **提交规范**：conventional commits（feat / fix / docs / test / chore）
