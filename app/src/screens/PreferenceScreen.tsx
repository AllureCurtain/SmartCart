import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
} from 'react-native';
import ApiService, { UserPreference } from '../services/api';
import { colors, fontSize, fontVariant, spacing, radius } from '../theme/tokens';

export default function PreferenceScreen() {
  const [preference, setPreference] = useState<UserPreference | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const loadPreference = async () => {
    try {
      const pref = await ApiService.getUserPreference('default');
      setPreference(pref);
      setLoadError(false);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadPreference();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadPreference();
  };

  // 骨架屏加载态（替代 ActivityIndicator spinner）
  if (loading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <View style={styles.skeletonTitle} />
          <View style={styles.skeletonSubtitle} />
        </View>
        {[0, 1, 2].map((i) => (
          <View key={i} style={styles.skeletonSection}>
            <View style={styles.skeletonSectionTitle} />
            <View style={styles.skeletonLine} />
            <View style={styles.skeletonLineShort} />
          </View>
        ))}
      </View>
    );
  }

  // 空态 / 错误态——包裹在 ScrollView 中保持下拉刷新能力
  if (loadError || !preference) {
    return (
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.centered}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <Text style={styles.emptyTitle}>
          {loadError ? '加载失败' : '还没有学到你的偏好'}
        </Text>
        <Text style={styles.emptyText}>
          {loadError
            ? '下拉刷新重试，或检查后端服务是否运行中'
            : '在首页搜索商品并点击感兴趣的结果，Agent 就会学习你的口味'}
        </Text>
      </ScrollView>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
      keyboardShouldPersistTaps="handled"
      keyboardDismissMode="on-drag"
    >
      <View style={styles.header}>
        <Text style={styles.title}>我的偏好</Text>
        <Text style={styles.subtitle}>Agent 从你的搜索与点击中学到的</Text>
      </View>

      {/* 搜索历史 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle} accessibilityRole="header">搜索历史</Text>
        {preference.search_history.length > 0 ? (
          preference.search_history.slice(-5).reverse().map((item, index) => (
            <View
              key={index}
              style={styles.historyItem}
              accessibilityLabel={`搜索历史：${item}`}
            >
              <Text style={styles.historyText}>{item}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.emptyText}>
            还没有搜索记录 · 去首页搜索商品，我会记住你的口味
          </Text>
        )}
      </View>

      {/* 品牌偏好 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle} accessibilityRole="header">品牌偏好</Text>
        {Object.keys(preference.brand_preferences).length > 0 ? (
          Object.entries(preference.brand_preferences).map(
            ([brand, pref]: [string, any]) => (
              <View
                key={brand}
                style={styles.preferenceItem}
                accessibilityLabel={`${brand}，偏好度 ${(pref.score * 100).toFixed(0)}%，点击 ${pref.count} 次`}
              >
                <View style={styles.brandRow}>
                  <Text style={styles.brandName}>{brand}</Text>
                  <Text style={styles.preferenceScore}>
                    {(pref.score * 100).toFixed(0)}% · {pref.count} 次
                  </Text>
                </View>
                <View style={styles.preferenceBar}>
                  <View
                    style={[
                      styles.preferenceBarFill,
                      { width: `${pref.score * 100}%` },
                    ]}
                  />
                </View>
              </View>
            )
          )
        ) : (
          <Text style={styles.emptyText}>
            暂无品牌偏好 · 在搜索结果里点击商品，我就会记住
          </Text>
        )}
      </View>

      {/* 价格偏好 */}
      {preference.price_preference && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle} accessibilityRole="header">价格偏好</Text>
          <View style={styles.priceBox}>
            <View
              style={styles.priceCell}
              accessibilityLabel={`最低 ${preference.price_preference.min.toFixed(0)} 元`}
            >
              <Text style={styles.priceLabel}>最低</Text>
              <Text style={styles.priceValue}>
                ¥{preference.price_preference.min.toFixed(0)}
              </Text>
            </View>
            <View
              style={styles.priceCell}
              accessibilityLabel={`平均 ${preference.price_preference.avg.toFixed(0)} 元`}
            >
              <Text style={styles.priceLabel}>平均</Text>
              <Text style={styles.priceValue}>
                ¥{preference.price_preference.avg.toFixed(0)}
              </Text>
            </View>
            <View
              style={styles.priceCell}
              accessibilityLabel={`最高 ${preference.price_preference.max.toFixed(0)} 元`}
            >
              <Text style={styles.priceLabel}>最高</Text>
              <Text style={styles.priceValue}>
                ¥{preference.price_preference.max.toFixed(0)}
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* 特性偏好 */}
      {Object.keys(preference.feature_preferences).length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle} accessibilityRole="header">特性偏好</Text>
          {Object.entries(preference.feature_preferences).map(
            ([feature, score]) => (
              <View
                key={feature}
                style={styles.featureItem}
                accessibilityLabel={`${feature}，偏好度 ${((score as number) * 100).toFixed(0)}%`}
              >
                <Text style={styles.featureText}>{feature}</Text>
                <Text style={styles.featureScore}>
                  {((score as number) * 100).toFixed(0)}%
                </Text>
              </View>
            )
          )}
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
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bg,
    padding: spacing.xxl,
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
  section: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    padding: spacing.l,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: {
    fontSize: fontSize.body,
    fontWeight: '800',
    color: colors.ink,
    marginBottom: spacing.m,
  },
  emptyTitle: {
    fontSize: fontSize.body,
    fontWeight: '700',
    color: colors.ink,
    marginBottom: spacing.s,
    textAlign: 'center',
  },
  emptyText: {
    fontSize: fontSize.label,
    color: colors.sub,
    lineHeight: 20,
    paddingVertical: spacing.s,
    textAlign: 'center',
  },
  historyItem: {
    padding: spacing.m,
    backgroundColor: colors.bg,
    borderRadius: radius.sm,
    marginBottom: spacing.s,
  },
  historyText: {
    fontSize: fontSize.label,
    color: colors.ink,
  },
  preferenceItem: {
    marginBottom: spacing.l,
  },
  brandRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: spacing.s,
  },
  brandName: {
    fontSize: fontSize.item,
    fontWeight: '700',
    color: colors.ink,
  },
  preferenceScore: {
    fontSize: fontSize.micro,
    color: colors.meta,
    fontVariant: fontVariant.tabular,
  },
  preferenceBar: {
    height: 6,
    backgroundColor: colors.skeleton,
    borderRadius: radius.xs,
    overflow: 'hidden',
  },
  preferenceBarFill: {
    height: '100%',
    backgroundColor: colors.prefFg,
    borderRadius: radius.xs,
  },
  priceBox: {
    flexDirection: 'row',
  },
  priceCell: {
    flex: 1,
    alignItems: 'center',
  },
  priceLabel: {
    fontSize: fontSize.micro,
    color: colors.meta,
    marginBottom: spacing.xs,
  },
  priceValue: {
    fontSize: fontSize.price,
    fontWeight: '800',
    color: colors.ink,
    letterSpacing: -0.3,
    fontVariant: fontVariant.tabular,
  },
  featureItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.m,
    borderBottomWidth: 1,
    borderBottomColor: colors.hairline,
  },
  featureText: {
    fontSize: fontSize.label,
    color: colors.ink,
  },
  featureScore: {
    fontSize: fontSize.label,
    fontWeight: '700',
    color: colors.prefFg,
    fontVariant: fontVariant.tabular,
  },
  // —— 骨架屏 ——
  skeletonTitle: {
    height: 28,
    width: '40%',
    backgroundColor: colors.skeleton,
    borderRadius: radius.xs,
    marginBottom: spacing.s,
  },
  skeletonSubtitle: {
    height: 14,
    width: '65%',
    backgroundColor: colors.skeleton,
    borderRadius: radius.xs,
  },
  skeletonSection: {
    marginHorizontal: spacing.xl,
    marginBottom: spacing.l,
    padding: spacing.l,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  skeletonSectionTitle: {
    height: 16,
    width: '30%',
    backgroundColor: colors.skeleton,
    borderRadius: radius.xs,
    marginBottom: spacing.m,
  },
  skeletonLine: {
    height: 13,
    backgroundColor: colors.skeleton,
    borderRadius: radius.xs,
    marginBottom: spacing.m,
    width: '85%',
  },
  skeletonLineShort: {
    height: 13,
    backgroundColor: colors.skeleton,
    borderRadius: radius.xs,
    width: '50%',
  },
});
