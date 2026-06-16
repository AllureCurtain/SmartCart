# Product

> SmartCart 根项目战略文件（impeccable register 锚点）。视觉细节见 `design/DESIGN.md`，token 见 `app/src/theme/tokens.ts`。

## Register

product

## Users

**Primary**: 智谱 AI 招聘评委 / 技术面试官。1–2 分钟内在演示视频或真机展示里快速评估：真实的 Agent 能力（控手机、多模态提取、记忆学习）、完整产品闭环、设计品味。

**End user（产品定位）**: 单用户（`default`）。碎片时间（通勤、午休）用自然语言说出购物需求，期待"懂我"的个性化推荐，而不是自己翻页比价。

**Context**: 评委要在一眼内确认"这是真在跑的 AI，不是套壳"；终端用户要的是被理解、被省心。

## Product Purpose

SmartCart 是基于 Open-AutoGLM 的移动端 AI 购物助手：把"自然语言需求"转成"个性化商品推荐"。

链路本身是产品差异化的核心，也是设计必须**强化而非弱化**的信息：Open-AutoGLM **控制物理手机**打开淘宝/京东搜索 → 后端 adb 截屏 → **GLM-4V 从截图提取真实商品** → Memory 按点击学习偏好 → 重排序 + 跨平台比价。App 内的「AGENT TRACE」终端逐条展示真实阶段与真实耗时——这是别家购物 App 没有的东西。

成功标准：评委判定"真 AI 在干活 + 设计有品味"；用户感到"它真的懂我"。

## Brand Personality

克制 · 说人话 · 专业自信。

不堆砌情绪、不用感叹号；以动作为主语描述 Agent（"控制手机 · 打开淘宝搜索"）；机制感知写成一句人话（"已按你的偏好排序——华为排在最前，因为你点过它"）。

> 视觉人格：restrained Agent console。购物界面保持克制，AGENT TRACE 成为可信度锚点。

## Anti-references

- **密集信息流**：淘宝/拼多多式一屏 5+ 商品、价格/标签/文案拥挤、促销紧迫感（红倒计时、闪烁角标）。
- **赛博/霓虹/渐变文字/玻璃态**：装饰性技术风，与"专业可信"冲突。
- **冷冰冰工具感**：纯黑白灰、无任何品牌识别，像记事本/计算器。
- **AI 默认米白底**：暖中性 near-white 是 2026 的 AI 默认味（impeccable 明确标记的 tell），要避免。

## Design Principles

1. **Show the Intelligence** —— Agent 替你操作手机的过程必须可见、可信、被强化，而非黑盒输出。AGENT TRACE 是叙事主角，不是状态条。
2. **Confidence Through Restraint** —— 克制不是无聊。用更大留白、更少颜色、更精准层级传递专业自信。
3. **Memory is Visible** —— 偏好学习不是隐藏功能；"偏好命中"、品牌进度条、推荐理由都在强化"AI 在学习你"。
4. **Earned Familiarity** —— 产品型 UI，标准 affordance 一致，让工具消失在任务里；不给标准操作发明花哨新控件。
5. **Every Detail Tells Quality** —— 对比度、触控尺寸、数字对齐、空状态、reduced-motion，每个细节都说"精心打磨"。

## Accessibility & Inclusion

- **WCAG 2.1 AA**：正文 ≥4.5:1，大字/粗体 ≥3:1，占位符同样 ≥4.5:1；当前 token 已把 `sub/meta` 调整到 AA 范围。
- **触控目标 ≥44×44 dp**。
- **Reduced motion**：任何动效提供降级（当前无动效，由缺失满足；新增动效必须兼容 `AccessibilityInfo.isReduceMotionEnabled`）。
- **Screen reader**：可交互元素提供 `accessibilityLabel` / `accessibilityRole`（当前全缺，必修项）。
- **不仅靠颜色区分状态**（如"偏好命中"同时用图标 + 文字 + 底色）。
