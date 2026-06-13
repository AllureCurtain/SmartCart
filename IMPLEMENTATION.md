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
| 淘宝搜索 Skill | `backend/skills/taobao_search.py` | ✅ 真机控制、后端截屏、GLM-4V 商品提取已打通 |
| App 搜索页/偏好页 | `app/src/screens/` | ✅ Expo Go 真机运行、结果恢复、Memory 可视化可用 |
| 演示模式 | `demo_mode=True` | ✅ 模拟数据降级路径带 `is_demo=True` 标记 |

### 已解决断点

**断点 1：真实模式的商品提取永远拿不到截图**
`taobao_search.py` 的 `_extract_products_from_screenshot()` 在 `Open-AutoGLM/screenshots/` 目录找截图，但 Open-AutoGLM 不会把截图持久化到磁盘（截图只在内存中传给模型）。因此真实模式必然静默降级到模拟数据——手机真的在搜索，App 显示的却是假商品。

**状态**：已解决。后端在 AutoGLM 控制淘宝结束后自行执行 `adb exec-out screencap -p`，再调用 GLM-4V 解析截图。

**断点 2：用户行为记录是空壳**
`main.py` 的 `POST /api/preference/action` 两个分支都是 `TODO: pass`，且前端商品卡片没有点击事件、从未调用 `recordAction`。Memory 的 view/click 学习在产品流程中不会发生。

**状态**：已解决。前端点击真实商品后上报 `task_id + product_id`，后端回查任务文件并写入 Memory；演示数据不上报。

**断点 3：推荐权重没有消费方**
`get_recommendation_weights()` 已实现，但搜索结果排序完全没有使用它，"自进化"未闭环。

**状态**：已解决。搜索结果保存前调用 `preference_service.rank_products()`，按品牌、特性和价格偏好重排序。

**断点 4：前端进度提示与真实状态无关**
`HomeScreen.tsx` 按轮询次数猜测进度（"正在打开淘宝…"），后端失败时界面仍在演进度。

**状态**：已解决。任务创建即落盘，后端写入 `queued / controlling_phone / extracting / ranking`，前端读取真实阶段。

**断点 5：真机 App 未验证**
只测过 `npm run web`。`api.ts` 硬编码 `localhost:8000`，真机上无法连接后端。

**状态**：已解决。Expo Go 真机已验证，App 通过 `expo-constants` 自动取开发机局域网 IP。

### 当前剩余风险

- 单台手机同时运行 Expo Go 和淘宝时，AutoGLM 会把 App 切后台。已增加最近结果恢复接口和前端恢复逻辑，但正式录制时仍建议保持网络稳定，或使用两台手机分别展示 App 与被控淘宝。
- 当前只提取淘宝首屏商品，一屏约 3 个；滚动多屏采集可作为后续扩展。
- Expo Go 为开发模式运行，Metro 断连时会出现 "Cannot connect to Expo CLI" 提示（不影响功能）；正式提交应构建 release APK 消除此依赖。

### 2026-06-13 修复记录（解析与提取链路）

| 问题 | 根因 | 修复 |
|------|------|------|
| 淘宝搜索框被输入整句自然语言 | 需求解析用了 `autoglm-phone`（手机 Agent 模型）必然失败，静默降级成整句搜索 | 新增 `ZHIPU_TEXT_MODEL`（默认免费 glm-4-flash），降级不再静默 |
| 执行速度比之前慢很多 | 同上——长句让 Agent 任务含糊、步骤膨胀；解析本身还白耗 8s | 解析 2-4s 出关键词；AutoGLM 加 `--max-steps 30` 防徘徊；端到端实测约 60s |
| 提取随机降级为演示数据 | 模型返回 JSON 后带尾随文字，`json.loads` 严格模式抛错 | 改 `raw_decode` 容错解析 |
| "天猫/百亿补贴"被当品牌写入 Memory | 视觉模型把平台标签当品牌 | 提示词约束 + `_clean_brand` 黑名单双保险 |
| 解析过程对用户不可见 | — | AGENT TRACE 第一行显示解析结果（`解析需求 → 蓝牙耳机 · ¥400-600`） |

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

- [x] `TaobaoSearchSkill` 增加 `_capture_screenshot()`（adb screencap，含 PNG 校验、跨平台 adb、超时独立报错）
- [x] 截图提取改为显式路径传入
- [x] `Product`/`SearchResult` 增加 `is_demo` 字段，降级路径全部标记
- [x] 前端展示"演示数据"横幅与角标
- [x] 安全加固：搜索关键词清洗（防提示词注入）、请求长度限制、真机操作加设备锁
- [x] 真机端到端测试一次：输入需求 → 手机自动搜淘宝 → GLM-4V 提取 → App 显示真实商品

**验收**：App 中显示的商品标题/价格与手机淘宝页面实际内容一致。

> ✅ **2026-06-12 真机验收通过**：AutoGLM 控制真机完成淘宝搜索"蓝牙耳机"，
> 后端截屏后由 glm-4v-flash（免费模型）提取出 3 个真实商品，价格与屏幕
> 完全一致（¥343.82 / ¥131.97 / ¥443.01），is_demo 标记全程正确。
> 已知限制：部分商品品牌识别为空；一屏约提取 3 个商品（可后续加滚动多屏）。

### Phase 2：Memory 与自进化闭环

- [x] `record_user_action` 实现（从任务文件查商品 → 调 preference_service），含 task_id 路径遍历防护
- [x] `UserAction` 模型增加 `task_id` 字段
- [x] 前端商品卡片 onPress 上报点击（演示数据不上报，显示"已记录偏好"反馈）
- [x] 搜索结果按偏好权重重排序（品牌分 + 标题特性命中 + 价格区间）
- [x] 验证：单元测试确认点击华为商品后，重排序使华为从第 2 位升至第 1 位

**验收**：演示"搜索 → 点击 → 再搜索，排序变化"的完整故事线。

> ✅ **2026-06-12 逻辑验收通过**（单元测试级）。App 级完整故事线留待录制演示视频时一并展示。

### Phase 3：真实进度与真机运行

- [x] 后端任务增加 `progress` 阶段字段（queued / controlling_phone / extracting / ranking），任务创建即落盘并逐阶段更新
- [x] 修复隐藏 bug：原实现任务文件在搜索结束才写入，真实模式下轮询拿到"任务不存在"导致前端轮询中断、界面永久卡死
- [x] 前端进度文案改为读后端真实阶段（删除按时间编造的假进度），单次轮询失败自动重试
- [x] `API_BASE_URL` 通过 expo-constants 自动取 Expo 开发机局域网 IP（Web/模拟器降级 localhost），真机免手动配置
- [x] Expo Go 真机运行验证（App 与被控手机可以是同一台或两台）
- [x] 单机演示恢复：增加 `/api/search/latest/{user_id}`，App 重载后恢复最近完成结果

**验收**：手机上的 App 完成一次真实搜索全流程。

> ✅ **2026-06-12 Expo Go 真机验收通过**：手机与电脑同一 WiFi，
> 手机 Expo Go 打开 SmartCart，输入“蓝牙耳机”后创建真实搜索任务；
> AutoGLM 切到淘宝完成搜索，后端截屏并提取 3 个真实商品；
> App 恢复最近结果并展示华为 FreeBuds 7i（¥443.01）等真实商品，`is_demo=false`。

### Phase 4：打磨与提交材料

- [x] UI 优化：商品缩略占位、加载骨架屏、空状态、结果页信息层级打磨
- [x] 后端代码审查遗留项：Windows 控制台编码加固、AutoGLM 子进程 UTF-8 输出、skill 单元测试（mock subprocess）
- [x] 录制演示视频脚本（见 README）
- [x] README 状态区更新（"进行中"项移入"已实现"）
- [ ] 可选加分项：京东搜索 Skill（验证 Skill 机制的可复用性）

**验收**：演示视频 + GitHub 仓库可以直接作为作业提交。

### Phase 5：提交准备（进行中）

- [ ] 构建 release APK：消除 Expo Go 开发模式依赖与 "Cannot connect to Expo CLI" 提示，作业"能在手机上运行"的最强证据
- [x] 真机完整回归一次：解析 → 短关键词搜索 → 真实提取 → 偏好排序（验证 06-13 全部修复）

> ✅ **2026-06-13 回归通过**：输入"我想买500元左右的蓝牙耳机"→ 解析为
> `蓝牙耳机 · ¥400-600` 显示在 AGENT TRACE → 淘宝搜索框收到纯关键词 →
> 提取 3 个真实商品（荣耀 Earbuds S ¥293.02 等），品牌清洗正确（无平台标签）。
> 已知特性：AutoGLM 执行时长波动 1-5 分钟（模型逐步决策 + 淘宝弹窗/加载影响步数），
> 属 Agent 固有特性；已加输出尾部日志便于诊断。
- [x] 后端 print 迁移 logging（新增 app_logging.py 统一 stdout+UTF-8 配置；后台任务异常改 logger.exception 不再静默）
- [x] 测试整顿：三个 ad-hoc 脚本（会真机控制/连服务器）重命名 manual_check_*.py 移出 pytest；新增 test_taobao_parsing / test_preference_ranking，pytest 全绿 18 passed
- [x] 截图保留策略：只留最近 20 张，避免全屏 PNG 无限堆积
- [x] pydantic `.dict()` 全部迁移 `model_dump()`
- [ ] release APK（用户决定：先完成打包前全部工作，APK 最后做）
- [ ] 录制演示视频（脚本见 README；新 UI 的 AGENT TRACE 是主角）
- [ ] 可选：滚动多屏采集更多商品 / 京东搜索 Skill

---

## 四、约定

- **诚实原则**：任何降级/模拟行为必须对用户可见，文档不写未实现的功能
- **密钥安全**：API Key 只存在于 `Open-AutoGLM/.env`（已 gitignore），任何文档/代码/日志不得出现 Key 内容
- **提交规范**：conventional commits（feat / fix / docs / test / chore）
