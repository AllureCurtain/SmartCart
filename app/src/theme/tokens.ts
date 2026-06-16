/**
 * SmartCart Design Tokens — 方向 A「Agent 控制台」
 *
 * 设计立场：克制电商 × Agent 终端，但把 Agent 提到结构主角。
 * - 骨架：中性 off-white（chroma 0，避开 2026 的 AI 暖米白默认味）+ 纯白卡片面
 * - 唯一"重"元素：AGENT TRACE 深色终端窗口（GitHub Dark 系），反差即记忆点
 * - 语义色只给三处：偏好命中（绿）、演示数据（琥珀）、失败（红）
 * - 中性文字两级（sub/meta）都过 WCAG AA 4.5:1
 *
 * 设计契约见 design/DESIGN.md；唯一事实来源本文件，组件禁止裸 hex / 裸数值。
 */
import { Platform } from 'react-native';

export const colors = {
  // —— 中性骨架（chroma 0，非暖米白） ——
  bg: '#FAFAFA',         // 页面背景：中性 off-white
  surface: '#FFFFFF',    // 输入框、卡片面（靠 border 与 bg 区分）
  ink: '#111418',        // 主文字、价格、主按钮
  sub: '#555A61',        // 次级正文（≈6.8:1，过 AA）
  meta: '#6B7178',       // 元数据、占位符（≈4.9:1，过 AA）
  hairline: '#ECECEC',   // 列表分隔线
  border: '#E2E2E2',     // 输入框、容器描边
  skeleton: '#EFEFEF',   // 骨架屏、缩略占位
  accentOn: '#FFFFFF',   // 深色按钮 / 终端强调上的文字

  // —— 语义色（仅三处） ——
  prefFg: '#0E7A4A',     // 偏好命中文字 / 偏好进度条
  prefBg: '#E9F6EF',     // 偏好命中底色
  warnFg: '#B54708',     // 演示数据文字
  warnBg: '#FFFAEB',     // 演示数据底色
  warnBorder: '#FEDF89', // 演示数据描边
  dangerFg: '#B42318',   // 失败文字
  dangerBg: '#FEF3F2',   // 失败底色

  // —— Agent 终端窗口（GitHub Dark 系） ——
  termBg: '#0D1117',     // 终端背景
  termBorder: '#30363D', // 终端描边、内部分隔
  termText: '#C9D1D9',   // 终端正文
  termDim: '#7D8590',    // 终端弱化文字（标签、耗时、待执行步骤）
  termGreen: '#3FB950',  // 已完成步骤、成功
  termAmber: '#E3B341',  // 进行中步骤
  termRed: '#F85149',    // 终端内失败信息
} as const;

export const fontSize = {
  display: 32,  // 页面大标题（放大，强化"控制台"自信）
  title: 20,    // 区块标题
  price: 22,    // 价格（tabular 对齐）
  body: 16,     // 输入框、正文
  item: 15,     // 商品标题
  label: 14,    // 按钮辅助、说明文字
  micro: 12,    // 元数据、徽标
  caption: 11,  // 徽标内文、小号辅助（tag / 终端标签）
  term: 13.5,   // 终端日志行（放大，让 AGENT TRACE 更可读）
} as const;

export const fontFamily = {
  // 终端窗口专用等宽字体
  mono: Platform.select({ ios: 'Menlo', default: 'monospace' }),
} as const;

// OpenType 数字特性：价格/进度等需对齐的数字
type FontVariant = 'small-caps' | 'oldstyle-nums' | 'lining-nums' | 'tabular-nums' | 'proportional-nums';
export const fontVariant: Record<string, FontVariant[]> = {
  tabular: ['tabular-nums'],
};

export const spacing = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  pageTop: 56,   // 页面顶部安全距离 + 标题留白（xxxl + xxl）
  touchTarget: 44, // 无障碍最小触摸目标（WCAG / Apple HIG）
} as const;

export const radius = {
  xs: 4,    // 徽标、小 pill 角
  sm: 8,    // 历史条目、小徽标
  md: 12,   // 终端窗口、缩略占位、卡片
  lg: 14,   // 输入框、主按钮
  pill: 999,
} as const;
