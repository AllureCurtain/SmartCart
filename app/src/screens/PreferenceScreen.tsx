import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import ApiService, { UserPreference } from '../services/api';
import { colors, fontSize, spacing, radius } from '../theme/tokens';

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

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.ink} />
      </View>
    );
  }

  if (loadError || !preference) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>
          {loadError ? '加载失败，下拉刷新或检查后端服务' : '暂无数据'}
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>我的偏好</Text>
        <Text style={styles.subtitle}>Agent 从你的搜索与点击中学到的</Text>
      </View>

      {/* 搜索历史 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>搜索历史</Text>
        {preference.search_history.length > 0 ? (
          preference.search_history.slice(-5).reverse().map((item, index) => (
            <View key={index} style={styles.historyItem}>
              <Text style={styles.historyText}>{item}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.emptyText}>暂无搜索记录</Text>
        )}
      </View>

      {/* 品牌偏好 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>品牌偏好</Text>
        {Object.keys(preference.brand_preferences).length > 0 ? (
          Object.entries(preference.brand_preferences).map(
            ([brand, pref]: [string, any]) => (
              <View key={brand} style={styles.preferenceItem}>
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
          <Text style={styles.sectionTitle}>价格偏好</Text>
          <View style={styles.priceBox}>
            <View style={styles.priceCell}>
              <Text style={styles.priceLabel}>最低</Text>
              <Text style={styles.priceValue}>
                ¥{preference.price_preference.min.toFixed(0)}
              </Text>
            </View>
            <View style={styles.priceCell}>
              <Text style={styles.priceLabel}>平均</Text>
              <Text style={styles.priceValue}>
                ¥{preference.price_preference.avg.toFixed(0)}
              </Text>
            </View>
            <View style={styles.priceCell}>
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
          <Text style={styles.sectionTitle}>特性偏好</Text>
          {Object.entries(preference.feature_preferences).map(
            ([feature, score]) => (
              <View key={feature} style={styles.featureItem}>
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
  },
  header: {
    paddingHorizontal: spacing.xxl,
    paddingTop: spacing.xxxl + spacing.xxl,
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
    marginTop: spacing.xs + 2,
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
  emptyText: {
    fontSize: fontSize.label,
    color: colors.meta,
    lineHeight: 20,
    paddingVertical: spacing.s,
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
  },
  preferenceBar: {
    height: 6,
    backgroundColor: colors.skeleton,
    borderRadius: radius.sm - 5,
    overflow: 'hidden',
  },
  preferenceBarFill: {
    height: '100%',
    backgroundColor: colors.prefFg,
    borderRadius: radius.sm - 5,
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
    fontSize: fontSize.title - 2,
    fontWeight: '800',
    color: colors.ink,
    letterSpacing: -0.3,
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
  },
});
