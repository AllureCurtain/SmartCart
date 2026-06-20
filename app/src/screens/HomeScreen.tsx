import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  AppState,
  Keyboard,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import AgentInsightPanel from '../components/AgentInsightPanel';
import ProductResultCard from '../components/ProductResultCard';
import { buildProductAppUrl } from '../services/platformLinks';
import { splitDisplayProducts } from '../services/resultDisplay';
import {
  SEARCH_INPUT_PLACEHOLDER,
  SearchResultInputSource,
  isSearchResultFresh,
  nextSearchInputValue,
} from '../services/searchInputState';
import ApiService, {
  MemoryContext,
  ParsedQuery,
  Product,
  SearchResult,
  SkillRun,
  UserPreference,
} from '../services/api';
import { colors, fontSize, fontFamily, radius, spacing } from '../theme/tokens';

const STAGES = [
  { key: 'queued', label: '解析需求，创建搜索任务' },
  { key: 'waiting_device', label: '等待设备空闲，准备执行综合搜索' },
  { key: 'controlling_phone', label: '控制手机，进入购物 App 搜索' },
  { key: 'extracting', label: '截屏并提取商品内容' },
  { key: 'ranking', label: '综合排序并生成解释' },
] as const;

const PLATFORM_LABELS = { all: '综合', taobao: '淘宝', jd: '京东' } as const;

type Platform = keyof typeof PLATFORM_LABELS;
type StatusTone = 'info' | 'success' | 'warning' | 'error';

function summarizePreference(preference: UserPreference | null): string {
  if (!preference) {
    return '暂无明显偏好';
  }
  const topBrand = Object.values(preference.brand_preferences)
    .sort((a, b) => b.score - a.score)[0]?.brand;
  const price = preference.price_preference
    ? `${Math.round(preference.price_preference.min)}-${Math.round(preference.price_preference.max)}`
    : '';
  const parts = [topBrand, price ? `¥${price}` : ''].filter(Boolean);
  return parts.length ? parts.join(' / ') : '暂无明显偏好';
}

function summarizeParsedQuery(parsedQuery: ParsedQuery | null): string {
  if (!parsedQuery) {
    return '';
  }
  const budget =
    parsedQuery.price_min != null && parsedQuery.price_max != null
      ? ` · ¥${Math.round(parsedQuery.price_min)}-${Math.round(parsedQuery.price_max)}`
      : '';
  return `${parsedQuery.category}${budget}`;
}

function isBudgetHit(product: Product, parsedQuery: ParsedQuery | null): boolean {
  if (
    !parsedQuery ||
    parsedQuery.price_min == null ||
    parsedQuery.price_max == null
  ) {
    return false;
  }
  return product.price >= parsedQuery.price_min && product.price <= parsedQuery.price_max;
}

function sourceLabel(products: Product[]): string {
  const platforms = Array.from(new Set(products.map((product) => product.platform)));
  if (platforms.length > 1) {
    return `多源综合（${platforms.map((p) => PLATFORM_LABELS[p as Platform] || p).join('+')}）`;
  }
  const platform = platforms[0];
  return `来自${PLATFORM_LABELS[platform as Platform] || platform || '搜索'}`;
}

export default function HomeScreen() {
  const scrollViewRef = useRef<ScrollView>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [searchStatus, setSearchStatus] = useState('');
  const [statusTone, setStatusTone] = useState<StatusTone>('info');
  const [isDemo, setIsDemo] = useState(false);
  const [taskId, setTaskId] = useState('');
  const [clickedIds, setClickedIds] = useState<string[]>([]);
  const [hasSubmittedSearch, setHasSubmittedSearch] = useState(false);
  const [stage, setStage] = useState('');
  const [agentTrace, setAgentTrace] = useState<string[]>([]);
  const [platform, setPlatform] = useState<Platform>('all');
  const [elapsedSeconds, setElapsedSeconds] = useState<number | null>(null);
  const [parsedQuery, setParsedQuery] = useState<ParsedQuery | null>(null);
  const [skillRuns, setSkillRuns] = useState<SkillRun[]>([]);
  const [memoryContext, setMemoryContext] = useState<MemoryContext | null>(null);
  const [preferenceHint, setPreferenceHint] = useState('暂无明显偏好');
  const [actionMessage, setActionMessage] = useState('');
  const [effectiveQuery, setEffectiveQuery] = useState('');
  const [productsExpanded, setProductsExpanded] = useState(false);

  const scrollToTop = (animated: boolean = true) => {
    requestAnimationFrame(() => {
      scrollViewRef.current?.scrollTo({ y: 0, animated });
    });
  };

  const applySearchResult = (
    result: SearchResult,
    message?: string,
    inputSource: SearchResultInputSource = 'submitted'
  ) => {
    setTaskId(result.task_id);
    setProducts(result.products || []);
    setProductsExpanded(false);
    setIsDemo(!!result.is_demo);
    setQuery((currentValue) =>
      nextSearchInputValue(currentValue, result.query, inputSource)
    );
    setParsedQuery(result.parsed_query || null);
    setStage(result.status === 'completed' ? 'done' : result.progress || '');
    setAgentTrace(result.agent_trace || []);
    setElapsedSeconds(result.elapsed_seconds ?? null);
    setSkillRuns(result.skill_runs || []);
    setMemoryContext(result.memory_context || null);
    setEffectiveQuery(result.effective_query || '');
    setStatusTone(result.is_demo ? 'warning' : 'success');
    setSearchStatus(message || `搜索完成，找到 ${result.products?.length || 0} 个商品`);
    setLoading(false);
    setHasSubmittedSearch(true);
    scrollToTop(inputSource === 'submitted');
  };

  const applyInFlightSnapshot = (result: SearchResult, message?: string) => {
    setTaskId(result.task_id);
    setQuery((currentValue) =>
      nextSearchInputValue(currentValue, result.query, 'restore')
    );
    setParsedQuery(result.parsed_query || null);
    setStage(result.progress || 'queued');
    setAgentTrace(result.agent_trace || []);
    setElapsedSeconds(result.elapsed_seconds ?? null);
    setSkillRuns(result.skill_runs || []);
    setMemoryContext(result.memory_context || null);
    setEffectiveQuery(result.effective_query || '');
    setStatusTone('info');
    setSearchStatus(message || '已恢复当前搜索任务');
    setLoading(true);
  };

  const loadPreferenceHint = async () => {
    try {
      const pref = await ApiService.getUserPreference('default');
      setPreferenceHint(summarizePreference(pref));
    } catch {
      setPreferenceHint('暂无明显偏好');
    }
  };

  const restoreLatestResult = async (
    message?: string,
    opts?: { fillQueryIfFresh?: boolean }
  ) => {
    const result = await ApiService.getLatestSearchResult('default');
    if (!result || result.status !== 'completed') {
      return;
    }
    // 刚搜完(续看窗口内)切回/重开：填回本次搜索词；冷启动超时：留空不预填
    const fill = !!opts?.fillQueryIfFresh && isSearchResultFresh(result.created_at);
    applySearchResult(result, message, fill ? 'submitted' : 'restore');
  };

  const restoreTaskState = async (messages?: { active?: string; fallback?: string }) => {
    if (taskId) {
      try {
        const result = await ApiService.getSearchResult(taskId);
        if (result.status === 'completed') {
          applySearchResult(result, messages?.active || '已恢复当前搜索任务', 'restore');
          return;
        }
        if (result.status === 'failed') {
          setStage('failed');
          setStatusTone('error');
          setSearchStatus(
            `${messages?.active || '已恢复当前搜索任务'}：${result.error || '未知错误'}`
          );
          setParsedQuery(result.parsed_query || null);
          setSkillRuns(result.skill_runs || []);
          setMemoryContext(result.memory_context || null);
          setEffectiveQuery(result.effective_query || '');
          setLoading(false);
          return;
        }
        applyInFlightSnapshot(result, messages?.active || '已恢复当前搜索任务');
        return;
      } catch {
        // 回退到最近已完成结果。
      }
    }
    await restoreLatestResult(messages?.fallback || '已恢复最近搜索结果');
  };

  useEffect(() => {
    let cancelled = false;

    const boot = async () => {
      await loadPreferenceHint();
      try {
        if (!cancelled) {
          await restoreLatestResult('已恢复最近搜索结果', { fillQueryIfFresh: true });
        }
      } catch {
        // 首屏恢复失败不阻断新搜索。
      }
    };

    boot();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state !== 'active') {
        return;
      }
      if (loading || taskId) {
        restoreTaskState({
          active: '已从后台恢复当前任务',
          fallback: '已从后台恢复最近结果',
        }).catch(() => undefined);
        return;
      }
      restoreLatestResult('已从后台恢复最近结果').catch(() => undefined);
    });

    return () => {
      subscription.remove();
    };
  }, [loading, taskId]);

  const openProductOnPlatform = async (product: Product) => {
    const linkInput = {
      platform: product.platform === 'jd' ? 'jd' : 'taobao',
      title: product.title,
    } as const;
    const appUrl = buildProductAppUrl(linkInput);

    try {
      await Linking.openURL(appUrl);
    } catch {
      Alert.alert('提示', '无法打开购物 App，请确认已安装并允许跳转');
    }
  };

  const handleProductClick = async (product: Product) => {
    if (!product.is_demo && !clickedIds.includes(product.id)) {
      setClickedIds((prev) => [...prev, product.id]);
      try {
        const insight = await ApiService.recordAction({
          user_id: 'default',
          action_type: 'click',
          product_id: product.id,
          task_id: taskId,
        });
        if (insight) {
          setMemoryContext(insight);
        }
        setActionMessage('已记录你的偏好');
        await loadPreferenceHint();
      } catch {
        setActionMessage('偏好记录失败，请稍后重试');
      }
    }
    await openProductOnPlatform(product);
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      Alert.alert('提示', '请输入搜索内容');
      return;
    }

    Keyboard.dismiss();
    scrollToTop();

    setLoading(true);
    setProducts([]);
    setProductsExpanded(false);
    setIsDemo(false);
    setClickedIds([]);
    setHasSubmittedSearch(true);
    setStage('queued');
    setAgentTrace([]);
    setElapsedSeconds(null);
    setParsedQuery(null);
    setSkillRuns([]);
    setMemoryContext(null);
    setActionMessage('');
    setEffectiveQuery('');
    setStatusTone('info');
    setSearchStatus('正在创建搜索任务...');

    try {
      const { task_id } = await ApiService.createSearch(query, platform);
      setTaskId(task_id);
      setSearchStatus('任务已创建，等待执行');

      let attempts = 0;
      const maxAttempts = 150;

      const pollResult = async () => {
        if (attempts >= maxAttempts) {
          setSearchStatus('搜索超时，请重试');
          setStatusTone('error');
          setStage('failed');
          setLoading(false);
          return;
        }

        attempts += 1;
        const elapsed = Math.floor(attempts * 2);

        let result: SearchResult | null = null;
        try {
          result = await ApiService.getSearchResult(task_id);
        } catch {
          setTimeout(pollResult, 2000);
          return;
        }

        if (!result) {
          setTimeout(pollResult, 2000);
          return;
        }

        if (result.status === 'completed') {
          applySearchResult(result, undefined, 'submitted');
          await loadPreferenceHint();
        } else if (result.status === 'failed') {
          setTaskId(result.task_id);
          setParsedQuery(result.parsed_query || null);
          setSkillRuns(result.skill_runs || []);
          setMemoryContext(result.memory_context || null);
          setEffectiveQuery(result.effective_query || '');
          setStage('failed');
          setStatusTone('error');
          setSearchStatus(`搜索失败：${result.error || '未知错误'}`);
          setLoading(false);
        } else {
          setTaskId(result.task_id);
          setParsedQuery(result.parsed_query || null);
          setSkillRuns(result.skill_runs || []);
          setMemoryContext(result.memory_context || null);
          setEffectiveQuery(result.effective_query || '');
          const current = result.progress || 'queued';
          setStage(current);
          const label = STAGES.find((s) => s.key === current)?.label ?? '正在搜索';
          setSearchStatus(`${label} (${elapsed}s)`);
          setTimeout(pollResult, 2000);
        }
      };

      pollResult();
    } catch (error: any) {
      setStage('failed');
      setStatusTone('error');
      Alert.alert('错误', error.message || '搜索失败');
      setLoading(false);
    }
  };

  const stageIndex = STAGES.findIndex((s) => s.key === stage);
  const stageState = (index: number) => {
    if (stage === 'done' || index < stageIndex) {
      return { label: '完成', style: styles.stageDone };
    }
    if (index === stageIndex && loading) {
      return { label: '当前', style: styles.stageActive };
    }
    if (stage === 'failed' && index === stageIndex) {
      return { label: '失败', style: styles.stageFailed };
    }
    return { label: '待执行', style: styles.stagePending };
  };

  const statusMessageStyle = {
    info: styles.progressMessageInfo,
    success: styles.progressMessageSuccess,
    warning: styles.progressMessageWarning,
    error: styles.progressMessageError,
  }[statusTone];
  const displayedProducts = splitDisplayProducts(products, productsExpanded);
  const canToggleProducts = products.length > displayedProducts.limit;
  const primaryProductCount = Math.min(products.length, displayedProducts.limit);
  const resultsTitle =
    canToggleProducts && !productsExpanded
      ? `优先推荐 ${primaryProductCount} 件`
      : `为你找到 ${products.length} 件`;

  return (
    <ScrollView
      ref={scrollViewRef}
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      keyboardShouldPersistTaps="handled"
      keyboardDismissMode="on-drag"
    >
      <View style={styles.header}>
        <Text style={styles.title}>SmartCart</Text>
        <Text style={styles.subtitle}>说出需求，剩下的交给 Agent</Text>
      </View>

      <View style={styles.searchBox}>
        <TextInput
          style={styles.input}
          placeholder={SEARCH_INPUT_PLACEHOLDER}
          placeholderTextColor={colors.meta}
          value={query}
          onChangeText={setQuery}
          multiline
          accessibilityLabel="搜索输入框"
        />
        <View style={styles.platformRow}>
          {(['all', 'taobao', 'jd'] as const).map((p) => (
            <TouchableOpacity
              key={p}
              style={[styles.platformPill, platform === p && styles.platformPillActive]}
              onPress={() => setPlatform(p)}
              disabled={loading}
              activeOpacity={0.7}
              accessibilityRole="radio"
              accessibilityState={{ selected: platform === p }}
              accessibilityLabel={`搜索平台：${PLATFORM_LABELS[p]}`}
            >
              <Text
                style={[
                  styles.platformPillText,
                  platform === p && styles.platformPillTextActive,
                ]}
              >
                {PLATFORM_LABELS[p]}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={styles.preferenceHint}>最近偏好：{preferenceHint}</Text>
        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSearch}
          disabled={loading}
          activeOpacity={0.85}
          accessibilityRole="button"
          accessibilityLabel={loading ? '搜索中，请稍候' : '开始搜索'}
          accessibilityState={{ disabled: loading }}
        >
          <Text style={styles.buttonText}>{loading ? '搜索中' : '开始搜索'}</Text>
        </TouchableOpacity>
      </View>

      {searchStatus && (loading || stage === 'failed' || products.length === 0) ? (
        <View style={styles.progressCard} accessibilityLabel={`当前搜索状态：${searchStatus}`}>
          <Text style={styles.progressTitle}>{loading ? '搜索进行中' : '搜索状态'}</Text>
          <Text style={[styles.progressMessage, statusMessageStyle]}>{searchStatus}</Text>
          {loading ? (
            <View style={styles.progressStages}>
              {STAGES.map((s, index) => {
                const mark = stageState(index);
                return (
                  <View key={s.key} style={styles.stageLine}>
                    <Text style={[styles.stageBadge, mark.style]}>{mark.label}</Text>
                    <Text style={styles.stageText}>{s.label}</Text>
                  </View>
                );
              })}
            </View>
          ) : null}
        </View>
      ) : null}

      {actionMessage ? (
        <View style={styles.actionBanner}>
          <Text style={styles.actionBannerText}>{actionMessage}</Text>
        </View>
      ) : null}

      {loading && products.length === 0 ? (
        <View style={styles.skeletonList}>
          {[0, 1, 2].map((item) => (
            <View key={item} style={styles.skeletonRow}>
              <View style={styles.skeletonThumb} />
              <View style={styles.skeletonBody}>
                <View style={styles.skeletonLineWide} />
                <View style={styles.skeletonLineShort} />
              </View>
            </View>
          ))}
        </View>
      ) : null}

      {hasSubmittedSearch && !loading && products.length === 0 && statusTone === 'success' ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyTitle}>这次搜索没有找到商品</Text>
          <Text style={styles.emptyText}>
            试试更具体的描述，比如品牌、预算或用途。
          </Text>
        </View>
      ) : null}

      {products.length > 0 ? (
        <View style={styles.resultsContainer}>
          <View style={styles.resultsHeader}>
            <View style={styles.resultsTitleBlock}>
              <Text style={styles.resultsTitle}>{resultsTitle}</Text>
              {parsedQuery ? (
                <Text style={styles.intentSummary}>{summarizeParsedQuery(parsedQuery)}</Text>
              ) : null}
            </View>
            <Text style={styles.resultsCount}>
              {isDemo ? '演示数据' : `${sourceLabel(products)} · 真实数据`}
            </Text>
          </View>

          {!isDemo ? (
            <Text style={styles.sortHint}>
              按需求与偏好排序，点击会学习偏好
            </Text>
          ) : null}

          {isDemo ? (
            <View style={styles.demoBanner}>
              <Text style={styles.demoBannerText}>
                当前为演示数据，非真实商品。
              </Text>
            </View>
          ) : null}

          {displayedProducts.visibleProducts.map((product) => (
            <ProductResultCard
              key={product.id}
              product={product}
              clicked={clickedIds.includes(product.id)}
              budgetHit={isBudgetHit(product, parsedQuery)}
              onPress={() => handleProductClick(product)}
            />
          ))}

          {canToggleProducts ? (
            <TouchableOpacity
              style={styles.moreResultsButton}
              activeOpacity={0.85}
              onPress={() => setProductsExpanded((prev) => !prev)}
              accessibilityRole="button"
              accessibilityLabel={
                productsExpanded
                  ? `收起到前 ${displayedProducts.limit} 件商品`
                  : `展开其余 ${displayedProducts.hiddenCount} 件商品`
              }
            >
              <Text style={styles.moreResultsButtonText}>
                {productsExpanded
                  ? `收起到前 ${displayedProducts.limit} 件`
                  : `展开其余 ${displayedProducts.hiddenCount} 件`}
              </Text>
            </TouchableOpacity>
          ) : null}

          <AgentInsightPanel
            parsedQuery={parsedQuery}
            effectiveQuery={effectiveQuery}
            elapsedSeconds={elapsedSeconds}
            agentTrace={agentTrace}
            skillRuns={skillRuns}
            memoryContext={memoryContext}
          />
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  contentContainer: {
    paddingBottom: spacing.xxxl,
  },
  header: {
    paddingHorizontal: spacing.xxl,
    paddingTop: spacing.pageTop,
    paddingBottom: spacing.l,
  },
  title: {
    fontSize: fontSize.display,
    fontWeight: '800',
    color: colors.ink,
  },
  subtitle: {
    fontSize: fontSize.label,
    color: colors.meta,
    marginTop: spacing.s,
  },
  searchBox: {
    paddingHorizontal: spacing.xl,
    marginBottom: spacing.l,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.l,
    fontSize: fontSize.body,
    minHeight: 80,
    color: colors.ink,
    textAlignVertical: 'top',
  },
  platformRow: {
    flexDirection: 'row',
    marginTop: spacing.m,
  },
  platformPill: {
    paddingHorizontal: spacing.l,
    paddingVertical: spacing.m,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    marginRight: spacing.s,
    minHeight: spacing.touchTarget,
    alignItems: 'center',
    justifyContent: 'center',
  },
  platformPillActive: {
    backgroundColor: colors.ink,
    borderColor: colors.ink,
  },
  platformPillText: {
    fontSize: fontSize.label,
    color: colors.sub,
    fontWeight: '700',
  },
  platformPillTextActive: {
    color: colors.accentOn,
  },
  preferenceHint: {
    marginTop: spacing.m,
    color: colors.meta,
    fontSize: fontSize.micro,
  },
  button: {
    backgroundColor: colors.ink,
    borderRadius: radius.lg,
    padding: spacing.l,
    marginTop: spacing.m,
    alignItems: 'center',
    minHeight: spacing.touchTarget,
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  buttonText: {
    color: colors.accentOn,
    fontSize: fontSize.item,
    fontWeight: '800',
  },
  progressCard: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.l,
  },
  progressTitle: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '800',
  },
  progressMessage: {
    marginTop: spacing.s,
    fontSize: fontSize.micro,
    lineHeight: 18,
  },
  progressMessageInfo: { color: colors.meta },
  progressMessageSuccess: { color: colors.prefFg },
  progressMessageWarning: { color: colors.warnFg },
  progressMessageError: { color: colors.dangerFg },
  progressStages: {
    marginTop: spacing.m,
  },
  stageLine: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  stageBadge: {
    width: 48,
    fontSize: fontSize.caption,
    fontFamily: fontFamily.mono,
    fontWeight: '700',
  },
  stageDone: { color: colors.prefFg },
  stageActive: { color: colors.warnFg },
  stageFailed: { color: colors.dangerFg },
  stagePending: { color: colors.meta },
  stageText: {
    color: colors.sub,
    fontSize: fontSize.micro,
    flex: 1,
    lineHeight: 18,
  },
  actionBanner: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    backgroundColor: colors.prefBg,
    borderRadius: radius.sm,
    padding: spacing.m,
  },
  actionBannerText: {
    color: colors.prefFg,
    fontSize: fontSize.label,
    fontWeight: '800',
  },
  skeletonList: {
    paddingHorizontal: spacing.xl,
  },
  skeletonRow: {
    flexDirection: 'row',
    paddingVertical: spacing.l,
    borderBottomWidth: 1,
    borderBottomColor: colors.hairline,
  },
  skeletonThumb: {
    width: 64,
    height: 64,
    borderRadius: radius.md,
    backgroundColor: colors.skeleton,
    marginRight: spacing.l,
  },
  skeletonBody: {
    flex: 1,
    justifyContent: 'center',
  },
  skeletonLineWide: {
    height: 13,
    borderRadius: radius.xs,
    backgroundColor: colors.skeleton,
    marginBottom: spacing.m,
    width: '88%',
  },
  skeletonLineShort: {
    height: 13,
    borderRadius: radius.xs,
    backgroundColor: colors.skeleton,
    width: '42%',
  },
  emptyState: {
    marginHorizontal: spacing.xl,
    padding: spacing.xl,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  emptyTitle: {
    fontSize: fontSize.body,
    fontWeight: '800',
    color: colors.ink,
    marginBottom: spacing.s,
  },
  emptyText: {
    fontSize: fontSize.label,
    color: colors.sub,
    lineHeight: 20,
  },
  resultsContainer: {
    paddingHorizontal: spacing.xl,
  },
  resultsHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingTop: spacing.s,
  },
  resultsTitleBlock: {
    flex: 1,
    paddingRight: spacing.m,
  },
  resultsTitle: {
    fontSize: fontSize.title,
    fontWeight: '800',
    color: colors.ink,
  },
  resultsCount: {
    color: colors.meta,
    fontSize: fontSize.micro,
    textAlign: 'right',
    maxWidth: 132,
    lineHeight: 17,
  },
  intentSummary: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '700',
    marginTop: spacing.s,
  },
  sortHint: {
    color: colors.meta,
    fontSize: fontSize.micro,
    marginTop: spacing.s,
    marginBottom: spacing.m,
    lineHeight: 18,
  },
  demoBanner: {
    backgroundColor: colors.warnBg,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.warnBorder,
    padding: spacing.m,
    marginTop: spacing.m,
    marginBottom: spacing.m,
  },
  demoBannerText: {
    fontSize: fontSize.term,
    color: colors.warnFg,
    lineHeight: 18,
  },
  moreResultsButton: {
    minHeight: spacing.touchTarget,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.s,
    marginBottom: spacing.l,
    paddingHorizontal: spacing.l,
    paddingVertical: spacing.m,
  },
  moreResultsButtonText: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '800',
  },
});
