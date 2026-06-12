/**
 * API 服务 - 与后端通信
 */
import axios from 'axios';

// 配置后端地址（开发时需要修改为你的电脑 IP）
const API_BASE_URL = 'http://localhost:8000';

export interface SearchRequest {
  query: string;
  user_id?: string;
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
}

export interface SearchResult {
  task_id: string;
  status: string;
  products?: Product[];
  error?: string;
  is_demo?: boolean;
}

export interface UserPreference {
  user_id: string;
  brand_preferences: Record<string, any>;
  price_preference?: any;
  feature_preferences: Record<string, number>;
  search_history: string[];
}

class ApiService {
  /**
   * 创建搜索任务
   */
  async createSearch(query: string): Promise<{ task_id: string; status: string }> {
    const response = await axios.post(`${API_BASE_URL}/api/search`, {
      query,
      user_id: 'default',
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
