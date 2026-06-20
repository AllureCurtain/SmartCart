import {
  SEARCH_INPUT_PLACEHOLDER,
  isSearchResultFresh,
  nextSearchInputValue,
} from './searchInputState';

if (SEARCH_INPUT_PLACEHOLDER !== '输入你的购物需求') {
  throw new Error(`expected neutral input placeholder, got ${SEARCH_INPUT_PLACEHOLDER}`);
}

const restored = nextSearchInputValue('', '我想要800元左右的蓝牙耳机', 'restore');

if (restored !== '') {
  throw new Error(`expected restored result to keep input empty, got ${restored}`);
}

const currentDraft = nextSearchInputValue('我自己输入的需求', '历史搜索词', 'restore');

if (currentDraft !== '我自己输入的需求') {
  throw new Error(`expected restored result to preserve current draft, got ${currentDraft}`);
}

const submitted = nextSearchInputValue('', '我想买电脑', 'submitted');

if (submitted !== '我想买电脑') {
  throw new Error(`expected submitted result query to be retained, got ${submitted}`);
}

// isSearchResultFresh：续看窗口内为新鲜，超时/缺失/非法为非新鲜
const freshIso = new Date(Date.now() - 60_000).toISOString();
if (!isSearchResultFresh(freshIso)) {
  throw new Error('expected a 1-min-old search to be fresh');
}

const staleIso = new Date(Date.now() - 30 * 60_000).toISOString();
if (isSearchResultFresh(staleIso)) {
  throw new Error('expected a 30-min-old search to be stale');
}

if (isSearchResultFresh(undefined) || isSearchResultFresh('not-a-date')) {
  throw new Error('expected missing/invalid createdAt to be non-fresh');
}
