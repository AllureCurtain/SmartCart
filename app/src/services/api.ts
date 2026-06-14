/**
 * API 服务 - 与后端通信
 */
import axios from 'axios';
import Constants from 'expo-constants';

/**
 * 后端地址解析：
 * - Expo Go 真机调试时，hostUri 形如 "192.168.x.x:8081"，
 *   自动取开发机的局域网 IP（后端需以 --host 0.0.0.0 启动）
 * - Web / 模拟器降级为 localhost
 */
function resolveBaseUrl(): string {
  const hostUri = Constants.expoConfig?.hostUri;
  const host = hostUri?.split(':')[0];
  if (host && host !== 'localhost' && host !== '127.0.0.1') {
    return `http://${host}:8000`;
  }
  return 'http://localhost:8000';
}

const API_BASE_URL = resolveBaseUrl();

export interface SearchRequest {
  query: string;
  user_id?: string;
  platform?: string;
}

export interface Product {
  id: string;
  title: string;
  price: number;
  rating?: number;
  review_count?: number;
  brand?: string;
  platform: string;
  is_demo?: boolean;
  recommendation_score?: number;
  recommendation_reason?: string | null;
  deal_tag?: string | null;
}

export interface MemoryContext {
  top_brand?: string | null;
  top_brands?: { brand: string; score: number; count: number }[];
  features?: string[];
  price_range?: { min: number; max: number } | null;
  recent_queries?: string[];
  has_signal?: boolean;
}

export interface SearchResult {
  task_id: string;
  query?: string;
  status: string;
  progress?: string;
  products?: Product[];
  error?: string;
  is_demo?: boolean;
  agent_trace?: string[];
  effective_query?: string;
  elapsed_seconds?: number;
  memory_context?: MemoryContext;
}

export interface UserPreference {
  user_id: string;
  brand_preferences: Record<string, any>;
  price_preference?: any;
  feature_preferences: Record<string, number>;
  search_history: string[];
}

export interface ParsedQuery {
  category: string;
  keywords: string[];
  price_min?: number | null;
  price_max?: number | null;
  features: string[];
}

class ApiService {
  /**
   * 创建搜索任务
   */
  async createSearch(
    query: string,
    platform: string = 'taobao'
  ): Promise<{ task_id: string; status: string }> {
    const response = await axios.post(`${API_BASE_URL}/api/search`, {
      query,
      user_id: 'default',
      platform,
    });
    return response.data.data;
  }

  /**
   * 获取搜索结果
   */
  async getSearchResult(taskId: string): Promise<SearchResult> {
    const response = await axios.get(`${API_BASE_URL}/api/search/${taskId}`);
    return response.data.data;
  }

  /**
   * 获取最近一次已完成搜索结果
   */
  async getLatestSearchResult(userId: string = 'default'): Promise<SearchResult | null> {
    const response = await axios.get(`${API_BASE_URL}/api/search/latest/${userId}`);
    if (!response.data.success) {
      return null;
    }
    return response.data.data;
  }

  /**
   * 获取用户偏好
   */
  async getUserPreference(userId: string = 'default'): Promise<UserPreference> {
    const response = await axios.get(`${API_BASE_URL}/api/preference/${userId}`);
    return response.data.data;
  }

  /**
   * 记录用户行为
   */
  async recordAction(action: {
    user_id: string;
    action_type: string;
    product_id?: string;
    task_id?: string;
  }): Promise<void> {
    await axios.post(`${API_BASE_URL}/api/preference/action`, {
      ...action,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data.status === 'ok';
    } catch {
      return false;
    }
  }
}

export default new ApiService();
