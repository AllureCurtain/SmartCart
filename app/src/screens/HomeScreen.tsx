import React, { useState } from 'react';
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

// 后端任务阶段 → 用户可读文案
const PROGRESS_TEXT: Record<string, string> = {
  queued: '任务排队中...',
  controlling_phone: '正在控制手机搜索淘宝...',
  extracting: '正在提取商品信息...',
  ranking: '正在按你的偏好排序...',
};

export default function HomeScreen() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [searchStatus, setSearchStatus] = useState('');
  const [isDemo, setIsDemo] = useState(false);
  const [taskId, setTaskId] = useState('');
  const [clickedIds, setClickedIds] = useState<string[]>([]);

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
    setSearchStatus('正在创建搜索任务...');

    try {
      // 1. 创建搜索任务
      const { task_id } = await ApiService.createSearch(query);
      setTaskId(task_id);
      setSearchStatus('正在连接手机...');

      // 2. 轮询获取结果
      let attempts = 0;
      const maxAttempts = 150; // 最多等待 5 分钟（每 2 秒一次）

      const pollResult = async () => {
        if (attempts >= maxAttempts) {
          setSearchStatus('搜索超时，请重试');
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
          setSearchStatus(`✅ 搜索完成！找到 ${result.products?.length || 0} 个商品`);
          setLoading(false);
        } else if (result.status === 'failed') {
          setSearchStatus(`❌ 搜索失败: ${result.error}`);
          setLoading(false);
        } else {
          // 显示后端汇报的真实阶段
          const stageText =
            PROGRESS_TEXT[result.progress ?? ''] ?? '正在搜索...';
          setSearchStatus(`${stageText} (${elapsed}秒)`);
          setTimeout(pollResult, 2000);
        }
      };

      pollResult();
    } catch (error: any) {
      Alert.alert('错误', error.message || '搜索失败');
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🛒 SmartCart</Text>
        <Text style={styles.subtitle}>智能购物助手</Text>
      </View>

      <View style={styles.searchBox}>
        <TextInput
          style={styles.input}
          placeholder="告诉我你想买什么..."
          value={query}
          onChangeText={setQuery}
          multiline
        />
        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSearch}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading ? '搜索中...' : '🔍 开始搜索'}
          </Text>
        </TouchableOpacity>
      </View>

      {searchStatus ? (
        <View style={styles.statusBox}>
          <Text style={styles.statusText}>{searchStatus}</Text>
          {loading && <ActivityIndicator size="small" color="#007AFF" />}
        </View>
      ) : null}

      {products.length > 0 && (
        <View style={styles.resultsContainer}>
          <Text style={styles.resultsTitle}>搜索结果</Text>
          {isDemo && (
            <View style={styles.demoBanner}>
              <Text style={styles.demoBannerText}>
                ⚠️ 当前为演示数据，非真实商品（真机搜索失败或处于演示模式）
              </Text>
            </View>
          )}
          {products.map((product) => (
            <TouchableOpacity
              key={product.id}
              style={styles.productCard}
              activeOpacity={0.7}
              onPress={() => handleProductClick(product)}
            >
              {product.is_demo && (
                <View style={styles.demoBadge}>
                  <Text style={styles.demoBadgeText}>演示数据</Text>
                </View>
              )}
              <Text style={styles.productTitle} numberOfLines={2}>
                {product.title}
              </Text>
              <View style={styles.productInfo}>
                <Text style={styles.productPrice}>¥{product.price}</Text>
                {product.rating && (
                  <Text style={styles.productRating}>⭐ {product.rating}</Text>
                )}
              </View>
              {product.brand && (
                <Text style={styles.productBrand}>品牌: {product.brand}</Text>
              )}
              <View style={styles.productFooter}>
                <Text style={styles.productPlatform}>平台: {product.platform}</Text>
                {clickedIds.includes(product.id) && (
                  <Text style={styles.likedText}>❤️ 已记录偏好</Text>
                )}
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
    backgroundColor: '#F5F5F5',
  },
  header: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: '#007AFF',
    alignItems: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFF',
  },
  subtitle: {
    fontSize: 16,
    color: '#FFF',
    marginTop: 8,
  },
  searchBox: {
    padding: 20,
    backgroundColor: '#FFF',
    marginTop: -20,
    borderRadius: 20,
    marginHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  input: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  button: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#999',
  },
  buttonText: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: '600',
  },
  statusBox: {
    margin: 16,
    padding: 16,
    backgroundColor: '#FFF',
    borderRadius: 12,
    alignItems: 'center',
  },
  statusText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 8,
  },
  resultsContainer: {
    padding: 16,
  },
  resultsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  demoBanner: {
    backgroundColor: '#FFF3E0',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FFB74D',
    padding: 12,
    marginBottom: 12,
  },
  demoBannerText: {
    fontSize: 13,
    color: '#E65100',
  },
  demoBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#FFB74D',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginBottom: 6,
  },
  demoBadgeText: {
    fontSize: 11,
    color: '#FFF',
    fontWeight: '600',
  },
  productCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  productTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  productInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  productPrice: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FF3B30',
    marginRight: 16,
  },
  productRating: {
    fontSize: 14,
    color: '#666',
  },
  productBrand: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  productPlatform: {
    fontSize: 12,
    color: '#999',
  },
  productFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  likedText: {
    fontSize: 12,
    color: '#FF3B30',
  },
});
