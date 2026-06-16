import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import ApiService, { Product } from '../services/api';
import { colors, fontSize, fontFamily, fontVariant, spacing, radius } from '../theme/tokens';

// 处理中阶段骨架（与后端 progress 字段对应）；完成后改用后端真实 agent_trace
const STAGES = [
  { key: 'queued', label: '解析需求，创建搜索任务' },
  { key: 'controlling_phone', label: '控制手机 · 打开购物 App 搜索' },
  { key: 'extracting', label: '截屏 → GLM-4V 提取商品' },
  { key: 'ranking', label: '按你的偏好重排序' },
] as const;

const PLATFORM_LABELS = { all: '综合', taobao: '淘宝', jd: '京东' } as const;

type StatusTone = 'info' | 'success' | 'warning' | 'error';

function formatPrice(price: number): string {
  return Number.isFinite(price) ? price.toFixed(2) : String(price);
}

function getProductInitial(product: Product): string {
  const label = product.brand || product.platform || product.title || '商';
  return label.trim().slice(0, 1).toUpperCase();
}

export default function HomeScreen() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [searchStatus, setSearchStatus] = useState('');
  const [statusTone, setStatusTone] = useState<StatusTone>('info');
  const [isDemo, setIsDemo] = useState(false);
  const [taskId, setTaskId] = useState('');
  const [clickedIds, setClickedIds] = useState<string[]>([]);
  const [hasSubmittedSearch, setHasSubmittedSearch] = useState(false);
  // 当前 Agent 阶段：STAGES 的 key，或 'done' / 'failed'
  const [stage, setStage] = useState('');
  // 后端返回的真实 Agent 执行轨迹（完成后填充，作为 AGENT TRACE 主体）
  const [agentTrace, setAgentTrace] = useState<string[]>([]);
  // 搜索平台（淘宝/京东）：证明 Skill 机制是多数据源可复用的，而非只绑淘宝
  const [platform, setPlatform] = useState<'all' | 'taobao' | 'jd'>('all');
  // 后端返回的端到端总耗时（秒），展示在 AGENT TRACE 头部（替代无意义的 task#id）
  const [elapsedSeconds, setElapsedSeconds] = useState<number | null>(null);

  useEffect(() => {
    // 恢复最近结果是辅助能力，失败不影响新搜索；但 Expo Go 被 AutoGLM
    // 切后台后经 deep-link 重载时，首次请求可能撞上隧道/重连的瞬态窗口而
    // 失败——给它两次延迟重试，避免刚搜到的结果因重载显示成空首页。
    let cancelled = false;
    const tryRestore = (attempt: number) => {
      ApiService.getLatestSearchResult('default')
        .then((result) => {
          if (cancelled) return;
          if (!result || result.status !== 'completed') {
            return;
          }
          setTaskId(result.task_id);
          setProducts(result.products || []);
          setIsDemo(!!result.is_demo);
          setQuery(result.query || '');
          setStage('done');
          setAgentTrace(result.agent_trace || []);
          setElapsedSeconds(result.elapsed_seconds ?? null);
          setStatusTone(result.is_demo ? 'warning' : 'success');
          setSearchStatus(
            `已恢复最近搜索结果，找到 ${result.products?.length || 0} 个商品`
          );
        })
        .catch(() => {
          if (cancelled || attempt >= 2) return;
          setTimeout(() => tryRestore(attempt + 1), 1500);
        });
    };
    tryRestore(0);
    return () => {
      cancelled = true;
    };
  }, []);

  const handleProductClick = (product: Product) => {
    // 演示数据的假品牌不写入 Memory
    if (product.is_demo) {
      return;
    }
    // 点击行为写入 Memory，用于偏好学习；上报失败不影响浏览
    setClickedIds((prev) =>
      prev.includes(product.id) ? prev : [...prev, product.id]
    );
    ApiService.recordAction({
      user_id: 'default',
      action_type: 'click',
      product_id: product.id,
      task_id: taskId,
    }).catch(() => {
      // 行为上报是非关键路径，失败时静默（不打断用户浏览）
    });
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      Alert.alert('提示', '请输入搜索内容');
      return;
    }

    setLoading(true);
    setProducts([]);
    setIsDemo(false);
    setClickedIds([]);
    setHasSubmittedSearch(true);
    setStage('queued');
    setAgentTrace([]);
    setElapsedSeconds(null);
    setStatusTone('info');
    setSearchStatus('正在创建搜索任务...');

    try {
      // 1. 创建搜索任务（解析/搜索/重排在后台执行）
      const { task_id } = await ApiService.createSearch(query, platform);
      setTaskId(task_id);
      setSearchStatus('任务已创建，等待执行');

      // 2. 轮询获取结果
      let attempts = 0;
      const maxAttempts = 150; // 最多等待 5 分钟（每 2 秒一次）

      const pollResult = async () => {
        if (attempts >= maxAttempts) {
          setSearchStatus('搜索超时，请重试');
          setStatusTone('error');
          setStage('failed');
          setLoading(false);
          return;
        }

        attempts++;
        const elapsed = Math.floor(attempts * 2);

        let result;
        try {
          result = await ApiService.getSearchResult(task_id);
        } catch {
          // 单次轮询失败（网络抖动等）不中断，继续重试
          setTimeout(pollResult, 2000);
          return;
        }

        if (!result) {
          setTimeout(pollResult, 2000);
          return;
        }

        if (result.status === 'completed') {
          setProducts(result.products || []);
          setIsDemo(!!result.is_demo);
          setStage('done');
          setAgentTrace(result.agent_trace || []);
          setElapsedSeconds(result.elapsed_seconds ?? null);
          setStatusTone(result.is_demo ? 'warning' : 'success');
          setSearchStatus(`搜索完成，找到 ${result.products?.length || 0} 个商品`);
          setLoading(false);
        } else if (result.status === 'failed') {
          setStage('failed');
          setStatusTone('error');
          setSearchStatus(`搜索失败：${result.error}`);
          setLoading(false);
        } else {
          // 同步后端汇报的真实阶段
          const current = result.progress || 'queued';
          setStage(current);
          const label =
            STAGES.find((s) => s.key === current)?.label ?? '正在搜索';
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

  // 终端日志行的三种状态
  const stageIndex = STAGES.findIndex((s) => s.key === stage);
  const stageMark = (index: number): { icon: string; style: object } => {
    if (stage === 'done' || index < stageIndex) {
      return { icon: '✓', style: styles.termIconDone };
    }
    if (index === stageIndex && loading) {
      return { icon: '●', style: styles.termIconActive };
    }
    if (stage === 'failed' && index === stageIndex) {
      return { icon: '✕', style: styles.termIconFailed };
    }
    return { icon: '○', style: styles.termIconPending };
  };

  const statusMessageStyle = {
    info: styles.termMsgInfo,
    success: styles.termMsgSuccess,
    warning: styles.termMsgWarning,
    error: styles.termMsgError,
  }[statusTone];

  // 结果来源标签：多平台 → 多源综合；单平台 → 来自某平台
  const resultPlatforms = Array.from(new Set(products.map((p) => p.platform)));
  const sourceLabel =
    resultPlatforms.length > 1
      ? `多源综合（${resultPlatforms.map((p) => (p === 'jd' ? '京东' : '淘宝')).join('+')}）`
      : `来自${resultPlatforms[0] === 'jd' ? '京东' : '淘宝'}`;

  return (
    <ScrollView
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
          placeholder="告诉我你想买什么..."
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
        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSearch}
          disabled={loading}
          accessibilityRole="button"
          accessibilityLabel={loading ? '搜索中，请稍候' : '开始搜索'}
          accessibilityState={{ disabled: loading }}
        >
          <Text style={styles.buttonText}>
            {loading ? '搜索中' : '开始搜索'}
          </Text>
        </TouchableOpacity>
      </View>

      {searchStatus ? (
        <View
          style={styles.terminal}
          accessibilityLabel={`Agent 执行轨迹，当前状态：${searchStatus}`}
        >
          <View style={styles.termHeader}>
            <Text style={styles.termTitle}>AGENT TRACE</Text>
            {elapsedSeconds != null ? (
              <Text style={styles.termTaskId}>⏱ {elapsedSeconds.toFixed(1)}s</Text>
            ) : null}
          </View>
          {agentTrace.length > 0
            ? // 完成后：展示后端真实 Agent 执行轨迹
              agentTrace.map((line, index) => (
                <View key={index} style={styles.termLine}>
                  <Text style={[styles.termIcon, styles.termIconDone]}>✓</Text>
                  <Text style={styles.termStep}>{line}</Text>
                </View>
              ))
            : // 处理中：按 progress 展示阶段骨架
              STAGES.map((s, index) => {
                const mark = stageMark(index);
                return (
                  <View key={s.key} style={styles.termLine}>
                    <Text style={[styles.termIcon, mark.style]}>{mark.icon}</Text>
                    <Text style={styles.termStep}>{s.label}</Text>
                  </View>
                );
              })}
          <View style={styles.termDivider} />
          <View style={styles.termMsgRow}>
            <Text style={[styles.termMsg, statusMessageStyle]}>
              {searchStatus}
            </Text>
            {loading && (
              <ActivityIndicator
                size="small"
                color={colors.termAmber}
                accessibilityLabel="处理中"
              />
            )}
          </View>
        </View>
      ) : null}

      {loading && products.length === 0 && (
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
      )}

      {hasSubmittedSearch &&
        !loading &&
        products.length === 0 &&
        statusTone === 'success' && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyTitle}>这次搜索没有找到商品</Text>
            <Text style={styles.emptyText}>
              试试更具体的描述，比如品牌、预算或用途。{'\n'}
              例如："300 元以内的蓝牙耳机，适合跑步用"
            </Text>
          </View>
        )}

      {products.length > 0 && (
        <View style={styles.resultsContainer}>
          <View style={styles.resultsHeader}>
            <Text style={styles.resultsTitle}>为你找到 {products.length} 件</Text>
            <Text style={styles.resultsCount}>
              {isDemo ? '演示数据' : `${sourceLabel} · 真实数据`}
            </Text>
          </View>
          {!isDemo && (
            <Text style={styles.sortHint}>
              已按你的偏好排序 · 点击商品会继续学习你的口味
            </Text>
          )}
          {isDemo && (
            <View style={styles.demoBanner}>
              <Text style={styles.demoBannerText}>
                当前为演示数据，非真实商品（真机搜索失败或处于演示模式）
              </Text>
            </View>
          )}
          {products.map((product, index) => (
            <TouchableOpacity
              key={product.id}
              style={[
                styles.productRow,
                index === products.length - 1 && styles.productRowLast,
              ]}
              activeOpacity={0.6}
              onPress={() => handleProductClick(product)}
              accessibilityRole="button"
              accessibilityLabel={`${product.title}，价格 ${formatPrice(product.price)} 元${product.brand ? `，品牌 ${product.brand}` : ''}${clickedIds.includes(product.id) ? '，已学习偏好' : ''}`}
            >
              <View style={styles.productThumb}>
                <Text style={styles.productThumbText}>
                  {getProductInitial(product)}
                </Text>
              </View>
              <View style={styles.productBody}>
                <Text style={styles.productTitle} numberOfLines={2}>
                  {product.title}
                </Text>
                <View style={styles.productPriceRow}>
                  <Text style={styles.productPrice}>
                    <Text style={styles.productPriceSymbol}>¥</Text>
                    {formatPrice(product.price)}
                  </Text>
                  <Text style={styles.productMeta} numberOfLines={1}>
                    {[product.brand, product.platform]
                      .filter(Boolean)
                      .join(' · ')}
                  </Text>
                </View>
                {!product.is_demo && product.recommendation_reason ? (
                  <Text style={styles.recReason} numberOfLines={1}>
                    {product.recommendation_reason}
                  </Text>
                ) : null}
                <View style={styles.tagRow}>
                  {!product.is_demo && product.deal_tag ? (
                    <View style={styles.dealTag} accessibilityRole="text">
                      <Text style={styles.dealTagText}>{product.deal_tag}</Text>
                    </View>
                  ) : null}
                  {clickedIds.includes(product.id) && (
                    <View style={styles.prefTag} accessibilityRole="text">
                      <Text style={styles.prefTagText}>偏好命中 · 已学习</Text>
                    </View>
                  )}
                  {product.is_demo && (
                    <View style={styles.demoTag} accessibilityRole="text">
                      <Text style={styles.demoTagText}>演示数据</Text>
                    </View>
                  )}
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      )}
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
    letterSpacing: -0.5,
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
    fontWeight: '700',
    letterSpacing: 2,
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
    fontWeight: '600',
  },
  platformPillTextActive: {
    color: colors.accentOn,
  },
  terminal: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    backgroundColor: colors.termBg,
    borderRadius: radius.md,
    padding: spacing.l,
  },
  termHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.m,
  },
  termTitle: {
    color: colors.termDim,
    fontSize: fontSize.caption,
    fontFamily: fontFamily.mono,
    letterSpacing: 1.5,
  },
  termTaskId: {
    color: colors.termDim,
    fontSize: fontSize.caption,
    fontFamily: fontFamily.mono,
  },
  termLine: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  termIcon: {
    width: 18,
    fontSize: fontSize.term,
    fontFamily: fontFamily.mono,
  },
  termIconDone: { color: colors.termGreen },
  termIconActive: { color: colors.termAmber },
  termIconFailed: { color: colors.termRed },
  termIconPending: { color: colors.termDim },
  termStep: {
    color: colors.termText,
    fontSize: fontSize.term,
    fontFamily: fontFamily.mono,
    flex: 1,
  },
  termDivider: {
    height: 1,
    backgroundColor: colors.termBorder,
    marginVertical: spacing.m,
  },
  termMsgRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  termMsg: {
    fontSize: fontSize.term,
    fontFamily: fontFamily.mono,
    flex: 1,
    lineHeight: 18,
  },
  termMsgInfo: { color: colors.termDim },
  termMsgSuccess: { color: colors.termGreen },
  termMsgWarning: { color: colors.termAmber },
  termMsgError: { color: colors.termRed },
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
    fontWeight: '700',
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
    alignItems: 'baseline',
    justifyContent: 'space-between',
    paddingTop: spacing.s,
  },
  resultsTitle: {
    fontSize: fontSize.title,
    fontWeight: '800',
    color: colors.ink,
    letterSpacing: -0.3,
  },
  resultsCount: {
    color: colors.meta,
    fontSize: fontSize.micro,
  },
  sortHint: {
    color: colors.meta,
    fontSize: fontSize.micro,
    marginTop: spacing.s,
    marginBottom: spacing.xs,
  },
  demoBanner: {
    backgroundColor: colors.warnBg,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.warnBorder,
    padding: spacing.m,
    marginTop: spacing.m,
  },
  demoBannerText: {
    fontSize: fontSize.term,
    color: colors.warnFg,
    lineHeight: 18,
  },
  productRow: {
    flexDirection: 'row',
    paddingVertical: spacing.xl,
    borderBottomWidth: 1,
    borderBottomColor: colors.hairline,
  },
  productRowLast: {
    borderBottomWidth: 0,
  },
  productThumb: {
    width: 64,
    height: 64,
    borderRadius: radius.md,
    backgroundColor: colors.skeleton,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.l,
  },
  productThumbText: {
    color: colors.ink,
    fontSize: fontSize.price,
    fontWeight: '800',
  },
  productBody: {
    flex: 1,
    minWidth: 0,
  },
  productTitle: {
    color: colors.ink,
    fontSize: fontSize.item,
    lineHeight: 22,
    fontWeight: '600',
    marginBottom: spacing.s,
  },
  productPriceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  productPrice: {
    color: colors.ink,
    fontSize: fontSize.price,
    fontWeight: '800',
    letterSpacing: -0.5,
    fontVariant: fontVariant.tabular,
  },
  productPriceSymbol: {
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  productMeta: {
    color: colors.meta,
    fontSize: fontSize.micro,
    marginLeft: spacing.s,
    flexShrink: 1,
  },
  recReason: {
    color: colors.prefFg,
    fontSize: fontSize.micro,
    marginTop: spacing.s,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.s,
  },
  prefTag: {
    backgroundColor: colors.prefBg,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
  },
  prefTagText: {
    fontSize: fontSize.caption,
    color: colors.prefFg,
    fontWeight: '700',
  },
  demoTag: {
    backgroundColor: colors.warnBg,
    borderWidth: 1,
    borderColor: colors.warnBorder,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
  },
  demoTagText: {
    fontSize: fontSize.caption,
    color: colors.warnFg,
    fontWeight: '700',
  },
  dealTag: {
    backgroundColor: colors.ink,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
  },
  dealTagText: {
    fontSize: fontSize.caption,
    color: colors.accentOn,
    fontWeight: '700',
  },
});
