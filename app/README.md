# SmartCart Mobile App

## 📱 快速开始

### 1. 安装依赖
```bash
npm install
```

### 2. 配置后端地址

App 会在 Expo Go 真机调试时自动读取开发机局域网 IP 并连接 `http://<IP>:8000`。
Web / 模拟器会自动回退到 `http://localhost:8000`。

### 3. 启动后端服务

在 `backend` 目录运行：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. 运行 App

```bash
# Web 版本（快速预览）
npm run web

# Android（需要连接手机或模拟器）
npm run android

# iOS（需要 macOS）
npm run ios
```

## 🎨 功能特性

### 首页 - 搜索
- 📝 自然语言输入（如"我想买500元左右的蓝牙耳机"）
- 🔍 自动解析需求并搜索
- 📦 实时显示搜索进度
- 📋 商品列表展示

### 偏好页 - Memory
- 📝 搜索历史
- 💎 品牌偏好（自动学习）
- 💰 价格偏好范围
- ⚡ 特性偏好权重

## 🔧 开发说明

### 技术栈
- React Native + Expo
- TypeScript
- Axios（HTTP 请求）

### 目录结构
```
app/
├── App.tsx              # 主入口
├── src/
│   ├── screens/         # 页面
│   │   ├── HomeScreen.tsx
│   │   └── PreferenceScreen.tsx
│   └── services/        # 服务
│       └── api.ts       # API 调用
└── package.json
```

### API 端点

- POST `/api/search` - 创建搜索任务
- GET `/api/search/:taskId` - 获取搜索结果
- GET `/api/preference/:userId` - 获取用户偏好

## 📝 注意事项

1. **网络连接**
   - 手机和电脑需要在同一 WiFi 网络
   - 后端服务需要使用 `0.0.0.0` 监听所有接口

2. **调试**
   - 使用 `npm run web` 可以在浏览器中快速预览
   - 使用 Expo Go App 可以在真机上测试

## 🚀 部署

由于需要连接后端和 Open-AutoGLM，本项目主要用于开发演示。

真实部署需要：
1. 后端部署到云服务器
2. 配置域名和 HTTPS
3. 打包 APK/IPA 文件
