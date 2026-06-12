# SmartCart - 智能购物助手

> 基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 的移动端 AI 购物助手
>
> 智谱 AI Agent 全栈开发实习生作业项目，采用 Vibe Coding（Claude Code / Codex）开发

## 项目简介

SmartCart 让用户用一句自然语言描述购物需求，例如“我想买 500 元左右的蓝牙耳机”，由 Agent 自动完成：

1. **需求理解**：GLM 解析自然语言，提取品类、预算和特性偏好。
2. **自动化搜索**：Open-AutoGLM 通过 ADB 控制 Android 手机打开淘宝并搜索。
3. **商品提取**：后端主动截取淘宝结果页，调用 GLM-4V 解析截图并输出结构化商品。
4. **Memory 学习**：记录搜索历史和商品点击行为，学习品牌、价格和特性偏好。
5. **自进化推荐**：基于偏好权重对后续搜索结果重排序。

## 当前状态

**已完成并验收：**

- FastAPI 后端：搜索任务创建、任务查询、最近结果恢复、偏好查询、行为上报 API。
- 淘宝搜索 Skill：封装 Open-AutoGLM，支持真机控制、ADB 截屏、GLM-4V 商品提取。
- React Native App：Expo Go 真机运行、搜索页、真实进度、结果页、偏好页，含加载骨架、空状态和商品缩略占位。
- Memory 闭环：App 点击商品后写入偏好，后续搜索按偏好重排。
- 单机演示稳定性：同一台手机既运行 Expo Go 又被 AutoGLM 切到淘宝时，App 可恢复最近搜索结果。

**2026-06-12 真机验收记录：**

- 设备：Android 真机，电脑与手机同一 WiFi，ADB 已连接。
- 输入：`蓝牙耳机`
- 结果：Open-AutoGLM 控制淘宝完成搜索，后端截屏并由 `glm-4v-flash` 提取 3 个真实商品。
- App 展示：`is_demo=false`，恢复并显示真实结果列表。
- 示例商品：华为 FreeBuds 7i 智慧降噪蓝牙耳机，价格 `443.01` 元。

## 系统架构

```text
React Native App (Expo Go)
        │ REST API
        ▼
FastAPI 后端
  ├─ QueryParserService      自然语言需求解析
  ├─ TaobaoSearchSkill       Skill 机制：淘宝搜索自动化
  ├─ PreferenceService       Memory 与推荐权重
  └─ latest result API       真机演示结果恢复
        │ subprocess + ADB
        ▼
Open-AutoGLM ──► Android 手机（淘宝 App）
        │
        ▼
ADB 截屏 ──► GLM-4V 商品结构化提取
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
