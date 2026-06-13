# SmartCart Design System

> 设计方向：**「克制电商 × Agent 终端」**（方向 2 骨架 + 方向 1 终端日志的混搭）
> 方向对比稿：`design/style-options.html` · Token 落地：`app/src/theme/tokens.ts`
> Last updated: 2026-06-12

## 设计立场

SmartCart 的差异化不在配色，而在**它强调了别的购物 App 没有的信息：一个真的在替你操作手机的 Agent**。因此：

1. **页面骨架极简克制**——浅米白底、黑白为骨、hairline 分隔，信息层级全靠字号与字重。商品和价格是主角，不与任何装饰竞争。
2. **Agent 过程是唯一的"重"元素**——嵌入一块深色终端窗口（AGENT TRACE），等宽字体、任务日志式逐条展示真实阶段与真实耗时。浅色页面上唯一的深色块，反差即记忆点。
3. **语义色只给三处**：偏好命中（绿）、演示数据警示（琥珀）、失败（红）。其余一律黑白灰。
4. **把机制写成人话**——自进化不靠图标堆砌，靠一句"已按你的偏好排序——华为排在最前，因为你点过它"。

## Design Tokens

完整数值见 `app/src/theme/tokens.ts`（唯一事实来源），**组件禁止裸 hex / 裸数值**。要点：

| 组 | 关键值 | 说明 |
|----|--------|------|
| 骨架 | `bg #FAFAF8` `ink #111418` `meta #878D96` `hairline #ECECE8` | 浅米白底 + 近黑墨色，主按钮就是 ink 黑 |
| 偏好 | `prefFg #0E7A4A` / `prefBg #E9F6EF` | 仅用于"偏好命中"徽标与偏好页进度条 |
| 警示 | `warnFg #B54708` / `warnBg #FFFAEB` | 仅用于演示数据横幅与徽标 |
| 失败 | `dangerFg #B42318` / `dangerBg #FEF3F2` | 仅用于搜索失败 |
| 终端 | `termBg #0D1117` `termText #C9D1D9` `termGreen #3FB950` `termAmber #E3B341` | GitHub Dark 系；等宽字体 Menlo / monospace |
| 字号 | display 30 · title 20 · price 21 · item 15 · micro 12 | 价格与标题靠字重(800)分层 |
| 圆角 | sm 8 · md 12 · lg 14 | 终端/卡片 md，输入框/主按钮 lg |

## 核心组件规范

### AGENT TRACE 终端窗口（搜索页）
- 深色块 `termBg`，圆角 md，标题行 `AGENT TRACE` + 短 task id（mono、dim）
- 四个阶段行：`✓ 已完成`（绿）→ `● 进行中`（琥珀）→ `○ 待执行`(dim)；文案"解析需求 / 控制手机 · 打开淘宝搜索 / 截屏 → GLM-4V 提取 / 按你的偏好重排序"
- 底部一行状态消息：成功绿 / 失败红 / 演示警示琥珀
- 仅在发起过搜索或恢复结果后出现；空闲首屏不渲染

### 商品行（搜索页）
- hairline 分隔的列表行（非卡片）：缩略占位 64×64 圆角 md `skeleton` 底 + 品牌首字
- 标题 item/600 两行截断 → 价格行：`¥443.01`（price/800 ink）左，元数据（micro meta）右
- 点击后追加绿色 pill「偏好命中 · 已学习」；演示数据追加琥珀 pill「演示数据」
- 结果区头部下方一行排序理由（micro meta，命中品牌加粗 ink）

### 偏好页
- 与搜索页同骨架；区块为白卡 + border 描边（不用阴影）
- 品牌偏好进度条填充 `prefFg` 绿；历史条目 `bg` 底圆角 sm

### Tab 栏
- `bg` 底 + hairline 顶线；激活 ink/800，未激活 meta；纯文字不带 emoji

## 文案声音

- 克制、对用户说人话，不用感叹号堆情绪
- Agent 过程文案以动作为主语（"控制手机 · 打开淘宝搜索"），终端语境内可用英文标签（AGENT TRACE）
- 机制感知文案模板："已按你的偏好排序——{品牌} 排在最前，因为你点过它"
