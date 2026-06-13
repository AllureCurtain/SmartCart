/**
 * SmartCart Design Tokens
 *
 * 设计方向：「克制电商 × Agent 终端」
 * - 页面骨架：浅色极简，黑白为骨，信息层级靠字号与字重
 * - Agent 过程：嵌入式深色终端窗口，等宽字体，任务日志式呈现
 * - 语义色只给三处：偏好命中（绿）、演示数据（琥珀）、失败（红）
 *
 * 设计契约详见 design/DESIGN.md，方向对比稿见 design/style-options.html。
 * 规则：组件里禁止写裸 hex / 裸数值，一律引用本文件的 token。
 */
import { Platform } from 'react-native';

export const colors = {
  // —— 浅色骨架 ——
  bg: '#FAFAF8',         // 页面背景
  surface: '#FFFFFF',    // 输入框、卡片
  ink: '#111418',        // 主文字、价格、主按钮
  sub: '#6B7178',        // 次级正文
  meta: '#878D96',       // 元数据、占位符、未激活 tab
  hairline: '#ECECE8',   // 列表分隔线
  border: '#E3E4E0',     // 输入框、容器描边
  skeleton: '#F0F0EC',   // 骨架屏、缩略占位
  accentOn: '#FFFFFF',   // 深色按钮上的文字

  // —— 语义色（仅三处） ——
  prefFg: '#0E7A4A',     // 偏好命中文字 / 偏好进度条
  prefBg: '#E9F6EF',     // 偏好命中底色
  warnFg: '#B54708',     // 演示数据文字
  warnBg: '#FFFAEB',     // 演示数据底色
  warnBorder: '#FEDF89', // 演示数据描边
  dangerFg: '#B42318',   // 失败文字
  dangerBg: '#FEF3F2',   // 失败底色

  // —— Agent 终端窗口 ——
  termBg: '#0D1117',     // 终端背景
  termBorder: '#30363D', // 终端描边、内部分隔
  termText: '#C9D1D9',   // 终端正文
  termDim: '#7D8590',    // 终端弱化文字（标签、耗时、待执行步骤）
  termGreen: '#3FB950',  // 已完成步骤、成功
  termAmber: '#E3B341',  // 进行中步骤
  termRed: '#F85149',    // 终端内失败信息
} as const;

export const fontSize = {
  display: 30,  // 页面大标题
  title: 20,    // 区块标题
  price: 21,    // 价格
  body: 16,     // 输入框、正文
  item: 15,     // 商品标题
  label: 13.5,  // 按钮辅助、说明文字
  micro: 12,    // 元数据、徽标
  term: 12.5,   // 终端日志行
} as const;

export const fontFamily = {
  // 终端窗口专用等宽字体
  mono: Platform.select({ ios: 'Menlo', default: 'monospace' }),
} as const;

export const spacing = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const radius = {
  sm: 8,    // 历史条目、小徽标
  md: 12,   // 终端窗口、缩略占位、卡片
  lg: 14,   // 输入框、主按钮
  pill: 999,
} as const;
