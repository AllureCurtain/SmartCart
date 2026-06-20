# SmartCart - 智能购物助手

> 基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 的移动端 AI 购物助手
>
> 智谱 AI Agent 全栈开发实习生作业项目，采用 Vibe Coding（Claude Code / Codex）开发

## 项目简介

SmartCart 让用户在手机上输入一句自然语言购物需求，例如“我想要 800 元左右的蓝牙耳机”，由 Agent 自动完成：

1. **需求理解**：GLM 解析自然语言，提取品类、预算和特性。
2. **读取记忆**：Memory 提供品牌、价格区间和近期查询信号。
3. **综合搜索**：`AgentRuntime` 调度京东和淘宝技能，真实控制手机完成搜索。
4. **商品提取**：后端主动截屏，并用 `glm-4v-flash` 提取结构化商品。
5. **推荐排序**：跨平台结果按当前需求与历史偏好重排，并给出推荐理由。
6. **Agent 可视化**：结果页下半部分可展开 `Trace / Skills / Memory`，直接证明这是一个 Agent 系统。
7. **偏好闭环**：点击商品写回 Memory，第二次相似搜索能看见排序和解释变化。

### Agent 架构（对应岗位四项能力）

| 能力 | 实现 |
|------|------|
| **Memory 记忆机制** | `PreferenceService` 持久化品牌/价格/特性偏好与搜索历史；`MemoryContextService` 产出紧凑记忆上下文 |
| **Skill 机制** | `Skill` 抽象基类 + `SkillRegistry` 注册表；4 个声明式技能（`taobao_search` / `get_preference_insight` / `record_product_action` / `rerank_products`），`GET /api/skills` 可查 |
| **MCP 工具** | `mcp_server.py` 把同一套技能以 MCP 工具形式暴露（stdio），任意 MCP 客户端（如 Claude Desktop）可驱动 |
| **自进化机制** | 搜索前记忆注入有效查询 + 搜索后记忆驱动重排，并把"为什么这么搜/这么排"写进可见的 AGENT TRACE 与推荐理由 |

`AgentRuntime` 作为编排层把上述能力串联，FastAPI 与 MCP 共享同一个 `SkillRegistry`。

`Skills` Tab 中的 `duration_seconds` 是解释慢点的关键证据：`综合` 模式虽然在编排层 fan-out，但单手机真实执行仍要经过设备池串行，所以 reviewer 可以直接看到每个源各花了多久。

## 当前状态

**已完成并验收：**

- Agent 架构：`AgentRuntime` 编排 + `SkillRegistry` 技能注册表 + `MCP Server` + 记忆驱动自进化，后端 61 项单测全绿。
- FastAPI 后端：搜索任务创建、任务查询、最近结果恢复、偏好查询、行为上报、技能列表 API。
- 淘宝搜索 Skill：封装 Open-AutoGLM，支持真机控制、ADB 截屏、GLM-4V 商品提取。
- React Native App：Expo Go 真机运行，AGENT TRACE 展示真实执行轨迹，商品卡片含推荐理由、加载骨架、空状态。
- Memory 闭环 + 自进化：App 点击商品写入偏好，下一次相似搜索可见地注入记忆并重排。
- 单机演示稳定性：同一台手机既运行 Expo Go 又被 AutoGLM 切到淘宝时，App 可恢复最近搜索结果。

**2026-06-12 真机验收记录：**

- 设备：Android 真机，电脑与手机同一 WiFi，ADB 已连接。
- 输入：`蓝牙耳机`
- 结果：Open-AutoGLM 控制淘宝完成搜索，后端截屏并由 `glm-4v-flash` 提取 3 个真实商品。
- App 展示：`is_demo=false`，恢复并显示真实结果列表。
- 示例商品：华为 FreeBuds 7i 智慧降噪蓝牙耳机，价格 `443.01` 元。

## 系统架构

```text
React Native App (Expo Go)            MCP 客户端（如 Claude Desktop）
        │ REST API                              │ MCP (stdio)
        ▼                                       ▼
FastAPI 端点 ──────► AgentRuntime          mcp_server.py
                         │                      │
                         ▼                      ▼
                    SkillRegistry ◄─────────────┘   （FastAPI 与 MCP 共享同一套技能）
                         ├─ taobao_search          → Open-AutoGLM + ADB 截屏 + GLM-4V 提取
                         ├─ get_preference_insight → MemoryContextService
                         ├─ record_product_action  → PreferenceService（Memory）
                         └─ rerank_products        → 记忆驱动打分 + 推荐理由
                         │
                         ▼
            SearchResult + AgentTrace + 推荐理由
                         │ subprocess + ADB
                         ▼
            Open-AutoGLM ──► Android 手机（淘宝 App）
```

## 技术栈

| 层 | 技术 |
|----|------|
| 移动端 | React Native + Expo + TypeScript |
| 后端 | Python + FastAPI + Pydantic |
| Agent | Open-AutoGLM (`autoglm-phone`) + GLM-4V |
| 设备控制 | ADB + ADB Keyboard |
| AI 开发方式 | Vibe Coding，使用 Claude Code / Codex 辅助迭代 |

## 快速开始

### 前置要求

- Python 3.10+、Node.js 18+
- Android 手机，开启开发者模式和 USB 调试
- ADB platform-tools
- ADB Keyboard，用于 AutoGLM 输入中文
- 智谱 API Key
- 与本项目同级目录存在 `Open-AutoGLM/`

推荐目录结构：

```text
project/
├── Open-AutoGLM/
└── SmartCart/
```

### 1. 安装 Open-AutoGLM

```bash
git clone https://github.com/zai-org/Open-AutoGLM.git
cd Open-AutoGLM
pip install -r requirements.txt
pip install -e .
```

在 `Open-AutoGLM/.env` 配置：

```bash
ZHIPU_API_KEY=your-api-key-here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=autoglm-phone
ZHIPU_VISION_MODEL=glm-4v-flash

# Windows 示例；也可以不配，默认使用系统 PATH 中的 adb
ADB_PATH=C:\path\to\platform-tools
```

### 2. 启动后端

```bash
cd SmartCart/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

可选验证：`GET /api/skills` 列出已注册技能；`pytest` 跑后端单测。

### 2b.（可选）启动 MCP Server

把 SmartCart 的技能以 MCP 工具暴露给任意 MCP 客户端（stdio 传输）：

```bash
cd SmartCart/backend
python mcp_server.py
```

接入 Claude Desktop 时，在其 MCP 配置中加入：

```json
{
  "mcpServers": {
    "smartcart": {
      "command": "python",
      "args": ["D:/Study/project/SmartCart/backend/mcp_server.py"]
    }
  }
}
```

连上后即可在客户端直接调用 `taobao_search` / `get_preference_insight` /
`record_product_action` / `rerank_products` 四个工具。

### 3. 启动移动端（真机录屏路径）

```bash
cd SmartCart/app
npm install
npx expo start --android --host localhost
```

这里必须使用 `--host localhost`，配合现有 `adb reverse` 与 `exp://localhost:8081` 切回链路，确保 AutoGLM 接管手机后还能稳定返回 SmartCart。

### 4. 真机验证步骤

1. 手机和电脑连接同一 WiFi。
2. USB 连接手机，运行 `adb devices`，确认设备为 `device`。
3. 确认手机安装淘宝和 ADB Keyboard。
4. 启动后端与 Expo。
5. 在 App 首页输入“蓝牙耳机”，点击搜索。
6. 观察手机被 AutoGLM 控制到淘宝结果页。
7. 回到 App，查看真实商品结果；如果 App 因切后台重载，会自动恢复最近完成的搜索结果。
8. 点击真实商品，切到“偏好”页查看 Memory 更新。

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

## 已知限制

- 一次只截取当前屏幕，通常提取首屏约 3 个商品；后续可增加滚动多屏采集。
- GLM-4V 对品牌字段可能识别为店铺/标签，例如“天猫”“百亿补贴”，因此品牌学习仍需进一步清洗。
- 当前 demo 以单用户 `default` 为主，`latest result` 接口用于真机演示恢复，未做多用户隔离。
- ADB 真机操作需要串行执行，后端已加设备锁避免并发任务互相干扰。

## 项目结构

```text
SmartCart/
├── README.md
├── IMPLEMENTATION.md
├── .env.example
├── app/
│   ├── App.tsx
│   └── src/
│       ├── screens/
│       └── services/
└── backend/
    ├── main.py
    ├── models.py
    ├── config.py
    ├── services/
    ├── skills/
    └── test_*.py
```

## License

MIT
