# SmartCart - 智能购物助手

> 基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 的移动端 AI 购物助手
>
> 智谱 AI Agent 全栈开发实习生作业项目，采用 Vibe Coding（Claude Code / Codex）开发

## 项目简介

SmartCart 让用户用一句自然语言描述购物需求，例如“我想买 500 元左右的蓝牙耳机”，由 Agent 自动完成：

1. **需求理解**：GLM 解析自然语言，提取品类、预算和特性偏好。
2. **读取记忆**：从 Memory 取出用户偏好（常看品牌 / 价格区间 / 特性）。
3. **调整搜索**：把记忆保守地注入搜索词（用户意图永远优先），并在 AGENT TRACE 中说明。
4. **自动化搜索**：Open-AutoGLM 通过 ADB 控制 Android 手机打开淘宝并搜索。
5. **商品提取**：后端主动截取淘宝结果页，调用 GLM-4V 解析截图并输出结构化商品。
6. **推荐重排**：用记忆 + 当前意图给商品打分并给出一句推荐理由。
7. **记忆更新**：点击商品写回 Memory，下一次相似搜索可见地用上记忆。

### Agent 架构（对应岗位四项能力）

| 能力 | 实现 |
|------|------|
| **Memory 记忆机制** | `PreferenceService` 持久化品牌/价格/特性偏好与搜索历史；`MemoryContextService` 产出紧凑记忆上下文 |
| **Skill 机制** | `Skill` 抽象基类 + `SkillRegistry` 注册表；4 个声明式技能（`taobao_search` / `get_preference_insight` / `record_product_action` / `rerank_products`），`GET /api/skills` 可查 |
| **MCP 工具** | `mcp_server.py` 把同一套技能以 MCP 工具形式暴露（stdio），任意 MCP 客户端（如 Claude Desktop）可驱动 |
| **自进化机制** | 搜索前记忆注入有效查询 + 搜索后记忆驱动重排，并把"为什么这么搜/这么排"写进可见的 AGENT TRACE 与推荐理由 |

`AgentRuntime` 作为编排层把上述能力串联，FastAPI 与 MCP 共享同一个 `SkillRegistry`。

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

### 3. 启动移动端

```bash
cd SmartCart/app
npm install

# Expo Go 真机
npm run android

# 或 Web 快速预览
npm run web
```

Expo Go 真机调试时，App 会通过 `expo-constants` 自动读取开发机局域网 IP，并访问 `http://<开发机 IP>:8000`。后端必须使用 `--host 0.0.0.0` 启动。

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

建议录制 60-90 秒，画面尽量同时包含电脑终端和手机：

1. 展示 `adb devices`、后端 `uvicorn`、Expo 启动成功。
2. 手机 Expo Go 打开 SmartCart，输入“蓝牙耳机”。
3. 点击搜索，展示真实进度文案。
4. 手机自动切到淘宝并完成搜索。
5. App 恢复最近结果，展示 `is_demo=false` 的真实商品列表。
6. 点击一个商品，切到“偏好”页展示 Memory 变化。
7. 简短说明：Skill、Memory、自进化、真机控制、多模态提取均已覆盖岗位要求。

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
