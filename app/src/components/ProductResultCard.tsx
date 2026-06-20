import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { Product } from '../services/api';
import { colors, fontSize, fontVariant, radius, spacing } from '../theme/tokens';

const PLATFORM_LABELS: Record<string, string> = {
  taobao: '淘宝',
  jd: '京东',
};

function formatPrice(price: number): string {
  return Number.isFinite(price) ? price.toFixed(2) : String(price);
}

function getProductInitial(product: Product): string {
  const label = product.brand || PLATFORM_LABELS[product.platform] || product.title || '商';
  return label.trim().slice(0, 1).toUpperCase();
}

interface ProductResultCardProps {
  product: Product;
  clicked: boolean;
  budgetHit: boolean;
  onPress: () => void;
}

export default function ProductResultCard({
  product,
  clicked,
  budgetHit,
  onPress,
}: ProductResultCardProps) {
  const platformLabel = PLATFORM_LABELS[product.platform] || product.platform;

  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.85}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${product.title}，价格 ${formatPrice(product.price)} 元${product.brand ? `，品牌 ${product.brand}` : ''}${clicked ? '，已记录偏好' : ''}`}
    >
      <View style={styles.thumb}>
        <Text style={styles.thumbText}>{getProductInitial(product)}</Text>
      </View>

      <View style={styles.body}>
        <View style={styles.topRow}>
          <View style={styles.platformBadge}>
            <Text style={styles.platformBadgeText}>{platformLabel}</Text>
          </View>
          {budgetHit ? (
            <View style={styles.budgetBadge}>
              <Text style={styles.budgetBadgeText}>预算内</Text>
            </View>
          ) : null}
        </View>

        <Text style={styles.title} numberOfLines={2}>
          {product.title}
        </Text>

        <View style={styles.priceRow}>
          <Text style={styles.price}>
            <Text style={styles.priceSymbol}>¥</Text>
            {formatPrice(product.price)}
          </Text>
          <Text style={styles.meta} numberOfLines={1}>
            {[product.brand, product.platform].filter(Boolean).join(' · ')}
          </Text>
        </View>

        {!product.is_demo && product.recommendation_reason ? (
          <Text style={styles.reason} numberOfLines={2}>
            {product.recommendation_reason}
          </Text>
        ) : null}

        <View style={styles.tagRow}>
          {!product.is_demo && product.deal_tag ? (
            <View style={styles.dealTag}>
              <Text style={styles.dealTagText}>{product.deal_tag}</Text>
            </View>
          ) : null}
          {clicked ? (
            <View style={styles.prefTag}>
              <Text style={styles.prefTagText}>已记录偏好</Text>
            </View>
          ) : null}
          {product.is_demo ? (
            <View style={styles.demoTag}>
              <Text style={styles.demoTagText}>演示数据</Text>
            </View>
          ) : null}
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.l,
    marginBottom: spacing.m,
  },
  thumb: {
    width: 68,
    height: 68,
    borderRadius: radius.md,
    backgroundColor: colors.skeleton,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.l,
  },
  thumbText: {
    color: colors.ink,
    fontSize: fontSize.price,
    fontWeight: '800',
  },
  body: {
    flex: 1,
    minWidth: 0,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.s,
  },
  platformBadge: {
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
  },
  platformBadgeText: {
    color: colors.meta,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  budgetBadge: {
    backgroundColor: colors.prefBg,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
  },
  budgetBadgeText: {
    color: colors.prefFg,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  title: {
    color: colors.ink,
    fontSize: fontSize.item,
    lineHeight: 22,
    fontWeight: '700',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginTop: spacing.s,
  },
  price: {
    color: colors.ink,
    fontSize: fontSize.price,
    fontWeight: '800',
    fontVariant: fontVariant.tabular,
  },
  priceSymbol: {
    fontSize: fontSize.label,
    fontWeight: '700',
  },
  meta: {
    color: colors.meta,
    fontSize: fontSize.micro,
    marginLeft: spacing.s,
    flexShrink: 1,
  },
  reason: {
    color: colors.prefFg,
    fontSize: fontSize.micro,
    lineHeight: 18,
    marginTop: spacing.s,
  },
  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.s,
  },
  dealTag: {
    backgroundColor: colors.ink,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
    marginBottom: spacing.xs,
  },
  dealTagText: {
    color: colors.accentOn,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  prefTag: {
    backgroundColor: colors.prefBg,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginRight: spacing.s,
    marginBottom: spacing.xs,
  },
  prefTagText: {
    color: colors.prefFg,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
  demoTag: {
    backgroundColor: colors.warnBg,
    borderWidth: 1,
    borderColor: colors.warnBorder,
    borderRadius: radius.xs,
    paddingHorizontal: spacing.m,
    paddingVertical: spacing.xs,
    marginBottom: spacing.xs,
  },
  demoTagText: {
    color: colors.warnFg,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },
});
