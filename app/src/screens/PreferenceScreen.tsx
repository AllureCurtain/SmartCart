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

export default function PreferenceScreen() {
  const [preference, setPreference] = useState<UserPreference | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadPreference = async () => {
    try {
      const pref = await ApiService.getUserPreference('default');
      setPreference(pref);
    } catch (error) {
      console.error('加载偏好失败', error);
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
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!preference) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>暂无数据</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>🎯 我的偏好</Text>
        <Text style={styles.subtitle}>AI 自动学习你的购物习惯</Text>
      </View>

      {/* 搜索历史 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>📝 搜索历史</Text>
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
        <Text style={styles.sectionTitle}>💎 品牌偏好</Text>
        {Object.keys(preference.brand_preferences).length > 0 ? (
          Object.entries(preference.brand_preferences).map(([brand, pref]: [string, any]) => (
            <View key={brand} style={styles.preferenceItem}>
              <Text style={styles.brandName}>{brand}</Text>
              <View style={styles.preferenceBar}>
                <View
                  style={[
                    styles.preferenceBarFill,
                    { width: `${pref.score * 100}%` },
                  ]}
                />
              </View>
              <Text style={styles.preferenceScore}>
                分数: {(pref.score * 100).toFixed(0)}% | 次数: {pref.count}
              </Text>
            </View>
          ))
        ) : (
          <Text style={styles.emptyText}>暂无品牌偏好</Text>
        )}
      </View>

      {/* 价格偏好 */}
      {preference.price_preference && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>💰 价格偏好</Text>
          <View style={styles.priceBox}>
            <Text style={styles.priceText}>
              最低: ¥{preference.price_preference.min.toFixed(0)}
            </Text>
            <Text style={styles.priceText}>
              平均: ¥{preference.price_preference.avg.toFixed(0)}
            </Text>
            <Text style={styles.priceText}>
              最高: ¥{preference.price_preference.max.toFixed(0)}
            </Text>
          </View>
        </View>
      )}

      {/* 特性偏好 */}
      {Object.keys(preference.feature_preferences).length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>⚡ 特性偏好</Text>
          {Object.entries(preference.feature_preferences).map(([feature, score]) => (
            <View key={feature} style={styles.featureItem}>
              <Text style={styles.featureText}>{feature}</Text>
              <Text style={styles.featureScore}>
                {((score as number) * 100).toFixed(0)}%
              </Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#34C759',
    alignItems: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFF',
  },
  subtitle: {
    fontSize: 14,
    color: '#FFF',
    marginTop: 8,
  },
  section: {
    margin: 16,
    padding: 16,
    backgroundColor: '#FFF',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    padding: 20,
  },
  historyItem: {
    padding: 12,
    backgroundColor: '#F8F8F8',
    borderRadius: 8,
    marginBottom: 8,
  },
  historyText: {
    fontSize: 14,
  },
  preferenceItem: {
    marginBottom: 16,
  },
  brandName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  preferenceBar: {
    height: 8,
    backgroundColor: '#E0E0E0',
    borderRadius: 4,
    marginBottom: 8,
  },
  preferenceBarFill: {
    height: '100%',
    backgroundColor: '#34C759',
    borderRadius: 4,
  },
  preferenceScore: {
    fontSize: 12,
    color: '#666',
  },
  priceBox: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  priceText: {
    fontSize: 16,
    fontWeight: '600',
  },
  featureItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#F8F8F8',
    borderRadius: 8,
    marginBottom: 8,
  },
  featureText: {
    fontSize: 14,
  },
  featureScore: {
    fontSize: 14,
    fontWeight: '600',
    color: '#34C759',
  },
});
