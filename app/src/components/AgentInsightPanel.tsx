import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { MemoryContext, ParsedQuery, SkillRun } from '../services/api';
import { colors, fontSize, radius, spacing } from '../theme/tokens';

type InsightTab = 'trace' | 'skills' | 'memory';

interface AgentInsightPanelProps {
  parsedQuery: ParsedQuery | null;
  effectiveQuery: string;
  elapsedSeconds: number | null;
  agentTrace: string[];
  skillRuns: SkillRun[];
  memoryContext: MemoryContext | null;
}

function summarizeParsedQuery(parsedQuery: ParsedQuery | null): string {
  if (!parsedQuery) {
    return '暂无';
  }
  const budget =
    parsedQuery.price_min != null && parsedQuery.price_max != null
      ? ` · ¥${Math.round(parsedQuery.price_min)}-${Math.round(parsedQuery.price_max)}`
      : '';
  return `${parsedQuery.category}${budget}`;
}

function platformLabel(platform: string): string {
  if (platform === 'taobao') {
    return '淘宝';
  }
  if (platform === 'jd') {
    return '京东';
  }
  return platform;
}

function formatSeconds(value: number | undefined): string {
  return `${(value ?? 0).toFixed(1)}s`;
}

export default function AgentInsightPanel({
  parsedQuery,
  effectiveQuery,
  elapsedSeconds,
  agentTrace,
  skillRuns,
  memoryContext,
}: AgentInsightPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<InsightTab>('trace');

  const hasContent = Boolean(
    parsedQuery ||
      effectiveQuery ||
      elapsedSeconds != null ||
      agentTrace.length ||
      skillRuns.length ||
      memoryContext
  );

  const memorySignals = memoryContext?.matched_signals;
  const topBrands = memoryContext?.top_brands || [];
  const recentQueries = memoryContext?.recent_queries || [];
  const signalItems = useMemo(
    () => [
      { label: '品牌', active: !!memorySignals?.brand },
      { label: '特性', active: !!memorySignals?.feature },
      { label: '价格区间', active: !!memorySignals?.price_range },
    ],
    [memorySignals]
  );

  if (!hasContent) {
    return null;
  }

  return (
    <View style={styles.panel}>
      <TouchableOpacity
        style={styles.header}
        activeOpacity={0.85}
        onPress={() => setExpanded((prev) => !prev)}
        accessibilityRole="button"
        accessibilityLabel={expanded ? '收起 Agent 视角' : '展开 Agent 视角'}
      >
        <View>
          <Text style={styles.eyebrow}>Agent 视角</Text>
          <Text style={styles.title}>Trace / Skills / Memory</Text>
        </View>
        <Text style={styles.toggleText}>{expanded ? '收起' : '展开'}</Text>
      </TouchableOpacity>

      {expanded ? (
        <>
          <View style={styles.tabRow}>
            {(['trace', 'skills', 'memory'] as const).map((tab) => (
              <TouchableOpacity
                key={tab}
                style={[styles.tab, activeTab === tab && styles.tabActive]}
                activeOpacity={0.85}
                onPress={() => setActiveTab(tab)}
                accessibilityRole="tab"
                accessibilityState={{ selected: activeTab === tab }}
              >
                <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                  {tab === 'trace' ? 'Trace' : tab === 'skills' ? 'Skills' : 'Memory'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {activeTab === 'trace' ? (
            <View>
              <View style={styles.summaryGrid}>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>解析需求</Text>
                  <Text style={styles.summaryValue}>{summarizeParsedQuery(parsedQuery)}</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>有效搜索词</Text>
                  <Text style={styles.summaryValue}>{effectiveQuery || '暂无'}</Text>
                </View>
                <View style={styles.summaryItem}>
                  <Text style={styles.summaryLabel}>总耗时</Text>
                  <Text style={styles.summaryValue}>
                    {elapsedSeconds != null ? `${elapsedSeconds.toFixed(1)}s` : '暂无'}
                  </Text>
                </View>
              </View>

              <View style={styles.traceList}>
                {agentTrace.length ? (
                  agentTrace.map((line, index) => (
                    <View key={`${line}-${index}`} style={styles.traceRow}>
                      <Text style={styles.traceBullet}>·</Text>
                      <Text style={styles.traceText}>{line}</Text>
                    </View>
                  ))
                ) : (
                  <Text style={styles.emptyText}>当前任务还没有可展示的执行摘要。</Text>
                )}
              </View>
            </View>
          ) : null}

          {activeTab === 'skills' ? (
            <View>
              {skillRuns.length ? (
                skillRuns.map((run) => {
                  const hasTimingBreakdown = [
                    run.wait_seconds,
                    run.control_seconds,
                    run.extract_seconds,
                  ].some((value) => typeof value === 'number');

                  return (
                    <View key={`${run.platform}-${run.skill_name}`} style={styles.skillCard}>
                      <View style={styles.skillTopRow}>
                        <Text style={styles.skillName}>{run.skill_name}</Text>
                        <Text
                          style={[
                            styles.skillStatus,
                            run.status === 'completed'
                              ? styles.skillStatusOk
                              : styles.skillStatusFail,
                          ]}
                        >
                          {run.status === 'completed' ? '完成' : '失败'}
                        </Text>
                      </View>
                      <Text style={styles.skillMeta}>
                        {platformLabel(run.platform)} · {run.product_count} 个商品 ·{' '}
                        {run.duration_seconds.toFixed(1)}s
                      </Text>
                      {hasTimingBreakdown ? (
                        <Text style={styles.skillTiming}>
                          等待 {formatSeconds(run.wait_seconds)} · 控制{' '}
                          {formatSeconds(run.control_seconds)} · 提取{' '}
                          {formatSeconds(run.extract_seconds)}
                        </Text>
                      ) : null}
                      <Text style={styles.skillQuery} numberOfLines={2}>
                        {run.query}
                      </Text>
                    </View>
                  );
                })
              ) : (
                <Text style={styles.emptyText}>本次任务还没有技能执行记录。</Text>
              )}
            </View>
          ) : null}

          {activeTab === 'memory' ? (
            <View>
              <View style={styles.memorySection}>
                <Text style={styles.memoryLabel}>学习到的品牌</Text>
                <Text style={styles.memoryValue}>
                  {topBrands.length
                    ? topBrands
                        .map((item) => `${item.brand} (${Math.round(item.score * 100)}%)`)
                        .join(' / ')
                    : '暂无明显品牌偏好'}
                </Text>
              </View>

              <View style={styles.memorySection}>
                <Text style={styles.memoryLabel}>价格区间</Text>
                <Text style={styles.memoryValue}>
                  {memoryContext?.price_range
                    ? `¥${Math.round(memoryContext.price_range.min)}-${Math.round(memoryContext.price_range.max)}`
                    : '暂无'}
                </Text>
              </View>

              <View style={styles.memorySection}>
                <Text style={styles.memoryLabel}>近期搜索</Text>
                <Text style={styles.memoryValue}>
                  {recentQueries.length ? recentQueries.join(' / ') : '暂无'}
                </Text>
              </View>

              <View style={styles.memorySection}>
                <Text style={styles.memoryLabel}>本次命中信号</Text>
                <View style={styles.signalRow}>
                  {signalItems.map((item) => (
                    <View
                      key={item.label}
                      style={[styles.signalBadge, item.active && styles.signalBadgeActive]}
                    >
                      <Text
                        style={[
                          styles.signalBadgeText,
                          item.active && styles.signalBadgeTextActive,
                        ]}
                      >
                        {item.label}
                      </Text>
                    </View>
                  ))}
                </View>
                <Text style={styles.signalSummary}>
                  {memorySignals?.has_match ? '这次搜索已经明显用到了记忆信号。' : '这次搜索暂未命中明显记忆信号。'}
                </Text>
              </View>
            </View>
          ) : null}
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    marginTop: spacing.l,
    marginBottom: spacing.xl,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.l,
  },
  eyebrow: {
    color: colors.meta,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  title: {
    color: colors.ink,
    fontSize: fontSize.body,
    fontWeight: '800',
    marginTop: spacing.xs,
  },
  toggleText: {
    color: colors.meta,
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  tabRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.l,
    paddingBottom: spacing.l,
  },
  tab: {
    paddingHorizontal: spacing.l,
    paddingVertical: spacing.s,
    borderRadius: radius.sm,
    backgroundColor: colors.bg,
    marginRight: spacing.s,
  },
  tabActive: {
    backgroundColor: colors.ink,
  },
  tabText: {
    color: colors.meta,
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  tabTextActive: {
    color: colors.accentOn,
  },
  summaryGrid: {
    paddingHorizontal: spacing.l,
  },
  summaryItem: {
    paddingVertical: spacing.s,
    borderTopWidth: 1,
    borderTopColor: colors.hairline,
  },
  summaryLabel: {
    color: colors.meta,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  summaryValue: {
    color: colors.ink,
    fontSize: fontSize.label,
    marginTop: spacing.xs,
    lineHeight: 20,
  },
  traceList: {
    paddingHorizontal: spacing.l,
    paddingBottom: spacing.l,
    paddingTop: spacing.s,
  },
  traceRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: spacing.xs,
  },
  traceBullet: {
    color: colors.meta,
    fontSize: fontSize.label,
    width: 14,
    lineHeight: 20,
  },
  traceText: {
    color: colors.sub,
    fontSize: fontSize.label,
    lineHeight: 20,
    flex: 1,
  },
  skillCard: {
    marginHorizontal: spacing.l,
    marginBottom: spacing.m,
    padding: spacing.l,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    backgroundColor: colors.bg,
  },
  skillTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  skillName: {
    color: colors.ink,
    fontSize: fontSize.label,
    fontWeight: '800',
    flex: 1,
  },
  skillStatus: {
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  skillStatusOk: {
    color: colors.prefFg,
  },
  skillStatusFail: {
    color: colors.dangerFg,
  },
  skillMeta: {
    color: colors.meta,
    fontSize: fontSize.caption,
    marginTop: spacing.s,
  },
  skillTiming: {
    color: colors.sub,
    fontSize: fontSize.micro,
    lineHeight: 18,
    marginTop: spacing.xs,
  },
  skillQuery: {
    color: colors.sub,
    fontSize: fontSize.label,
    lineHeight: 20,
    marginTop: spacing.s,
  },
  memorySection: {
    paddingHorizontal: spacing.l,
    paddingBottom: spacing.l,
  },
  memoryLabel: {
    color: colors.meta,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  memoryValue: {
    color: colors.ink,
    fontSize: fontSize.label,
    lineHeight: 20,
    marginTop: spacing.xs,
  },
  signalRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.s,
  },
  signalBadge: {
    backgroundColor: colors.bg,
    borderRadius: radius.xs,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
    marginBottom: spacing.s,
  },
  signalBadgeActive: {
    backgroundColor: colors.prefBg,
    borderColor: colors.prefBg,
  },
  signalBadgeText: {
    color: colors.meta,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  signalBadgeTextActive: {
    color: colors.prefFg,
  },
  signalSummary: {
    color: colors.sub,
    fontSize: fontSize.micro,
    lineHeight: 18,
    marginTop: spacing.xs,
  },
  emptyText: {
    color: colors.meta,
    fontSize: fontSize.label,
    lineHeight: 20,
    paddingHorizontal: spacing.l,
    paddingBottom: spacing.l,
  },
});
