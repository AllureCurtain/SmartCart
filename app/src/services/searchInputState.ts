export type SearchResultInputSource = 'restore' | 'submitted';

export const SEARCH_INPUT_PLACEHOLDER = '输入你的购物需求';

/**
 * 切回/重开时，最近一次搜索若在此窗口内，视为"搜索流程内续看"，
 * 把该次搜索词填回输入框；超过窗口（冷启动新 session）则不预填、留空。
 */
export const SEARCH_RESUME_WINDOW_MS = 10 * 60 * 1000;

export function nextSearchInputValue(
  currentValue: string,
  resultQuery: string | null | undefined,
  source: SearchResultInputSource
): string {
  if (source === 'restore') {
    return currentValue;
  }
  return resultQuery || currentValue;
}

/**
 * 最近一次搜索是否在"续看"窗口内（刚搜完切回/重开）。
 * createdAt 缺失或无法解析时按"非新鲜"处理，避免冷启动误预填历史词。
 */
export function isSearchResultFresh(
  createdAt: string | null | undefined
): boolean {
  if (!createdAt) {
    return false;
  }
  const ts = new Date(createdAt).getTime();
  if (Number.isNaN(ts)) {
    return false;
  }
  return Date.now() - ts < SEARCH_RESUME_WINDOW_MS;
}
