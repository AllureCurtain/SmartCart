# SmartCart - 智能购物助手

> 基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 的 AI 购物助手移动应用
>
> 智谱 AI Agent 全栈开发实习生作业项目，采用 Vibe Coding（Claude Code）开发

## 项目简介

SmartCart 让用户用一句自然语言描述购物需求（如"我想买500元左右的蓝牙耳机"），由 Agent 自动完成：

1. **需求理解** — GLM 解析自然语言，提取品类、价格区间、特性偏好
2. **自动化搜索** — Open-AutoGLM 通过 ADB 控制 Android 手机，打开淘宝完成搜索
3. **商品提取** — GLM-4V 多模态模型解析搜索结果截图，输出结构化商品数据
4. **偏好学习（Memory）** — 记录搜索历史和点击行为，学习品牌/价格/特性偏好
5. **个性化推荐（自进化）** — 基于学习到的偏好权重对结果重排序

## 系统架构

```
React Native App (Expo)
        │ REST API
        ▼
FastAPI 后端
  ├─ QueryParserService   需求解析（GLM）
  ├─ TaobaoSearchSkill    搜索技能（Skill 机制）
  └─ PreferenceService    偏好学习（Memory 机制）
        │ subprocess + ADB
        ▼
Open-AutoGLM ──► Android 手机（淘宝 App）
```

## 技术栈

| 层 | 技术 |
|----|------|
| 移动端 | React Native + Expo + TypeScript |
| 后端 | Python + FastAPI + Pydantic |
| Agent | Open-AutoGLM (autoglm-phone) + GLM-4V |
| 设备控制 | ADB (Android Debug Bridge) |
| 开发方式 | Vibe Coding（Claude Code，约 70% 代码由 AI 生成） |

## 当前状态

**已实现：**
- ✅ FastAPI 后端：搜索任务创建/查询、偏好查询 API
- ✅ 自然语言需求解析（GLM API，含降级策略）
- ✅ 淘宝搜索 Skill 封装（调用 Open-AutoGLM 控制真机）
- ✅ 偏好学习服务：搜索历史、品牌/价格/特性偏好、推荐权重生成
- ✅ React Native App：搜索页（输入/进度/结果）、偏好页（Memory 可视化）
- ✅ 演示模式：无手机环境下用模拟数据快速验证完整流程

**进行中（见 [IMPLEMENTATION.md](IMPLEMENTATION.md)）：**
- 🔄 真机搜索结果截图 → GLM-4V 商品提取的端到端打通
- 🔄 用户行为记录闭环（App 点击 → 后端 Memory）
- 🔄 偏好权重应用于搜索结果排序
- 🔄 真机（Expo Go / APK）运行验证与演示视频

## 快速开始

### 前置要求

- Python 3.10+、Node.js 18+
- Android 手机（开启开发者模式 + USB 调试）
- ADB（[下载 platform-tools](https://developer.android.com/tools/releases/platform-tools)）
- 智谱 API Key（[申请地址](https://open.bigmodel.cn)）

### 1. 安装 Open-AutoGLM

```bash
# 与本项目同级目录克隆
git clone https://github.com/zai-org/Open-AutoGLM.git
cd Open-AutoGLM
pip install -r requirements.txt
pip install -e .
```

配置 API Key（参考本项目 `.env.example`）：

```bash
# Open-AutoGLM/.env
ZHIPU_API_KEY=your-api-key-here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=autoglm-phone
```

Android 设备还需安装 [ADB Keyboard](https://github.com/senzhk/ADBKeyBoard) 用于文本输入。

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

# Web 快速预览
npm run web

# Android 真机（需先把 app/src/services/api.ts 中的
# API_BASE_URL 改为电脑的局域网 IP）
npm run android
```

### 4. 验证

1. 手机连接电脑，`adb devices` 确认设备在线
2. App 首页输入"我想买蓝牙耳机"，点击搜索
3. 观察手机被自动控制打开淘宝搜索
4. 等待结果返回，切换到偏好页查看 Memory 学习结果

## 项目结构

```
SmartCart/
├── README.md
├── IMPLEMENTATION.md         # 实现文档与开发路线
├── .env.example              # API 配置模板
├── app/                      # React Native 前端
│   └── src/
│       ├── screens/          # HomeScreen / PreferenceScreen
│       └── services/         # API 封装
└── backend/                  # Python 后端
    ├── main.py               # FastAPI 入口
    ├── models.py             # Pydantic 数据模型
    ├── config.py             # 配置加载
    ├── services/             # 需求解析 / 偏好学习
    └── skills/               # 淘宝搜索 Skill
```

## License

MIT
