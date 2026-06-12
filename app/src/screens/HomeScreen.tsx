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

// 后端任务阶段 → 用户可读文案
const PROGRESS_TEXT: Record<string, string> = {
  queued: '任务排队中...',
  controlling_phone: '正在控制手机搜索淘宝...',
  extracting: '正在提取商品信息...',
  ranking: '正在按你的偏好排序...',
};

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

  const statusToneStyle = {
    info: styles.statusInfo,
    success: styles.statusSuccess,
    warning: styles.statusWarning,
    error: styles.statusError,
  }[statusTone];

  useEffect(() => {
    ApiService.getLatestSearchResult('default')
      .then((result) => {
        if (!result || result.status !== 'completed') {
          return;
        }
        setTaskId(result.task_id);
        setProducts(result.products || []);
        setIsDemo(!!result.is_demo);
        setQuery(result.query || '');
        setStatusTone(result.is_demo ? 'warning' : 'success');
        setSearchStatus(
          `已恢复最近搜索结果，找到 ${result.products?.length || 0} 个商品`
        );
      })
      .catch(() => {
        // 恢复最近结果是辅助能力，失败不影响新搜索。
      });
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
    setStatusTone('info');
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
          setStatusTone('error');
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
          setStatusTone(result.is_demo ? 'warning' : 'success');
          setSearchStatus(`搜索完成，找到 ${result.products?.length || 0} 个商品`);
          setLoading(false);
        } else if (result.status === 'failed') {
          setStatusTone('error');
          setSearchStatus(`搜索失败：${result.error}`);
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
      setStatusTone('error');
      Alert.alert('错误', error.message || '搜索失败');
      setLoading(false);
    }
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
    >
      <View style={styles.header}>
        <Text style={styles.title}>SmartCart</Text>
        <Text style={styles.subtitle}>移动端 AI 购物助手</Text>
      </View>

      <View style={styles.searchBox}>
        <Text style={styles.inputLabel}>购物需求</Text>
        <TextInput
          style={styles.input}
          placeholder="告诉我你想买什么..."
          placeholderTextColor="#8A8F98"
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
            {loading ? '搜索中...' : '开始搜索'}
          </Text>
        </TouchableOpacity>
      </View>

      {searchStatus ? (
        <View style={[styles.statusBox, statusToneStyle]}>
          <View style={styles.statusHeader}>
            <View style={[styles.statusDot, statusToneStyle]} />
            <Text style={styles.statusLabel}>任务状态</Text>
          </View>
          <Text style={styles.statusText}>{searchStatus}</Text>
          {loading && <ActivityIndicator size="small" color="#176B87" />}
        </View>
      ) : null}

      {loading && products.length === 0 && (
        <View style={styles.skeletonList}>
          {[0, 1, 2].map((item) => (
            <View key={item} style={styles.skeletonCard}>
              <View style={styles.skeletonThumb} />
              <View style={styles.skeletonBody}>
                <View style={styles.skeletonLineWide} />
                <View style={styles.skeletonLineShort} />
                <View style={styles.skeletonMetaRow}>
                  <View style={styles.skeletonChip} />
                  <View style={styles.skeletonChip} />
                </View>
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
            <Text style={styles.emptyTitle}>暂无可展示商品</Text>
            <Text style={styles.emptyText}>这次搜索没有提取到结构化结果。</Text>
          </View>
        )}

      {products.length > 0 && (
        <View style={styles.resultsContainer}>
          <View style={styles.resultsHeader}>
            <Text style={styles.resultsTitle}>搜索结果</Text>
            <Text style={styles.resultsCount}>{products.length} 件</Text>
          </View>
          {isDemo && (
            <View style={styles.demoBanner}>
              <Text style={styles.demoBannerText}>
                当前为演示数据，非真实商品（真机搜索失败或处于演示模式）
              </Text>
            </View>
          )}
          {products.map((product) => (
            <TouchableOpacity
              key={product.id}
              style={[
                styles.productCard,
                clickedIds.includes(product.id) && styles.productCardSelected,
              ]}
              activeOpacity={0.7}
              onPress={() => handleProductClick(product)}
            >
              <View
                style={[
                  styles.productThumb,
                  product.is_demo && styles.productThumbDemo,
                ]}
              >
                <Text style={styles.productThumbText}>
                  {getProductInitial(product)}
                </Text>
              </View>
              <View style={styles.productBody}>
                <View style={styles.productTopRow}>
                  {product.is_demo && (
                    <View style={styles.demoBadge}>
                      <Text style={styles.demoBadgeText}>演示数据</Text>
                    </View>
                  )}
                  {clickedIds.includes(product.id) && (
                    <View style={styles.preferenceBadge}>
                      <Text style={styles.preferenceBadgeText}>已记录偏好</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.productTitle} numberOfLines={2}>
                  {product.title}
                </Text>
                <Text style={styles.productPrice}>¥{formatPrice(product.price)}</Text>
                <View style={styles.metaRow}>
                  {product.brand && (
                    <Text style={styles.metaChip} numberOfLines={1}>
                      {product.brand}
                    </Text>
                  )}
                  <Text style={styles.metaChip}>{product.platform}</Text>
                  {product.rating ? (
                    <Text style={styles.metaChip}>{product.rating} 分</Text>
                  ) : null}
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
    backgroundColor: '#F6F7F9',
  },
  contentContainer: {
    paddingBottom: 32,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 42,
    backgroundColor: '#203034',
  },
  title: {
    fontSize: 34,
    fontWeight: '800',
    color: '#FFF',
  },
  subtitle: {
    fontSize: 16,
    color: '#D8E1E4',
    marginTop: 6,
  },
  searchBox: {
    padding: 16,
    backgroundColor: '#FFF',
    marginTop: -22,
    borderRadius: 8,
    marginHorizontal: 16,
    shadowColor: '#1D2B2F',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  inputLabel: {
    color: '#2E3A3E',
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#DDE3E6',
    borderRadius: 8,
    padding: 14,
    fontSize: 16,
    minHeight: 80,
    color: '#1E2528',
    textAlignVertical: 'top',
    backgroundColor: '#FAFBFC',
  },
  button: {
    backgroundColor: '#176B87',
    borderRadius: 8,
    padding: 15,
    marginTop: 12,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#87959A',
  },
  buttonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '700',
  },
  statusBox: {
    margin: 16,
    padding: 16,
    backgroundColor: '#FFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#DDE3E6',
  },
  statusInfo: {
    borderColor: '#B8D7E3',
    backgroundColor: '#F3FAFC',
  },
  statusSuccess: {
    borderColor: '#A8D5BE',
    backgroundColor: '#F3FBF7',
  },
  statusWarning: {
    borderColor: '#E2C27C',
    backgroundColor: '#FFF8E8',
  },
  statusError: {
    borderColor: '#E0A5A5',
    backgroundColor: '#FFF5F5',
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusLabel: {
    color: '#2E3A3E',
    fontSize: 13,
    fontWeight: '700',
  },
  statusText: {
    fontSize: 14,
    color: '#435057',
    lineHeight: 20,
    marginBottom: 8,
  },
  skeletonList: {
    paddingHorizontal: 16,
    marginTop: 2,
  },
  skeletonCard: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E6EBEE',
    padding: 12,
    marginBottom: 10,
  },
  skeletonThumb: {
    width: 58,
    height: 58,
    borderRadius: 8,
    backgroundColor: '#E7ECEF',
    marginRight: 12,
  },
  skeletonBody: {
    flex: 1,
    justifyContent: 'center',
  },
  skeletonLineWide: {
    height: 12,
    borderRadius: 6,
    backgroundColor: '#E7ECEF',
    marginBottom: 10,
    width: '86%',
  },
  skeletonLineShort: {
    height: 12,
    borderRadius: 6,
    backgroundColor: '#EDF1F3',
    marginBottom: 12,
    width: '46%',
  },
  skeletonMetaRow: {
    flexDirection: 'row',
  },
  skeletonChip: {
    width: 54,
    height: 20,
    borderRadius: 8,
    backgroundColor: '#EDF1F3',
    marginRight: 8,
  },
  emptyState: {
    marginHorizontal: 16,
    marginTop: 2,
    padding: 18,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E1E6E9',
    backgroundColor: '#FFF',
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1E2528',
    marginBottom: 6,
  },
  emptyText: {
    fontSize: 14,
    color: '#667178',
    lineHeight: 20,
  },
  resultsContainer: {
    paddingHorizontal: 16,
    paddingTop: 4,
  },
  resultsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  resultsTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1E2528',
  },
  resultsCount: {
    color: '#667178',
    fontSize: 13,
    fontWeight: '700',
  },
  demoBanner: {
    backgroundColor: '#FFF8E8',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E2C27C',
    padding: 12,
    marginBottom: 12,
  },
  demoBannerText: {
    fontSize: 13,
    color: '#76520B',
    lineHeight: 18,
  },
  demoBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#E9D6A3',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginRight: 6,
    marginBottom: 8,
  },
  demoBadgeText: {
    fontSize: 11,
    color: '#6C4D09',
    fontWeight: '700',
  },
  preferenceBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#DDEFE7',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginBottom: 8,
  },
  preferenceBadgeText: {
    fontSize: 11,
    color: '#25664B',
    fontWeight: '700',
  },
  productCard: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E1E6E9',
  },
  productCardSelected: {
    borderColor: '#A8D5BE',
    backgroundColor: '#FBFFFD',
  },
  productThumb: {
    width: 58,
    height: 58,
    borderRadius: 8,
    backgroundColor: '#E3EEF1',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  productThumbDemo: {
    backgroundColor: '#F1E4C0',
  },
  productThumbText: {
    color: '#176B87',
    fontSize: 20,
    fontWeight: '800',
  },
  productBody: {
    flex: 1,
    minWidth: 0,
  },
  productTopRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  productTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#20272A',
    lineHeight: 21,
    marginBottom: 8,
  },
  productPrice: {
    fontSize: 22,
    fontWeight: '800',
    color: '#C83A3A',
    marginBottom: 8,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  metaChip: {
    fontSize: 12,
    color: '#546168',
    backgroundColor: '#F0F3F5',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 6,
    marginBottom: 6,
    maxWidth: 116,
  },
});
