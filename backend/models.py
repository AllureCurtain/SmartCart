"""
SmartCart 数据模型定义
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 商品相关 ====================

class Product(BaseModel):
    """商品信息"""
    id: str  # 商品 ID（从淘宝提取或生成）
    title: str  # 商品标题
    price: float  # 价格
    original_price: Optional[float] = None  # 原价
    rating: Optional[float] = None  # 评分 (0-5)
    review_count: Optional[int] = None  # 评价数
    sales: Optional[int] = None  # 销量
    brand: Optional[str] = None  # 品牌
    image_url: Optional[str] = None  # 图片 URL
    shop_name: Optional[str] = None  # 店铺名称
    platform: str = "taobao"  # 平台
    is_demo: bool = False  # 是否为演示数据（降级/模拟时必须标记）
    recommendation_score: float = 0.0  # 推荐分数（Memory / 当前需求综合）
    recommendation_reason: Optional[str] = None  # 推荐理由，前端展示一行


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, max_length=100)  # 用户输入的自然语言
    user_id: str = Field("default", max_length=64)  # 用户 ID
    platform: str = Field("taobao", pattern="^(taobao|jd)$")  # 搜索平台：taobao | jd


class ParsedQuery(BaseModel):
    """解析后的搜索需求"""
    category: str  # 品类（如"蓝牙耳机"）
    keywords: List[str]  # 关键词
    price_min: Optional[float] = None  # 最低价
    price_max: Optional[float] = None  # 最高价
    features: List[str] = []  # 特性要求（如"降噪"、"音质"）


class SearchResult(BaseModel):
    """搜索结果"""
    task_id: str  # 任务 ID
    query: str  # 原始查询
    parsed_query: ParsedQuery  # 解析后的查询
    products: List[Product]  # 商品列表
    total_count: int  # 总数
    status: str = "completed"  # completed | failed | processing
    progress: Optional[str] = None  # queued | controlling_phone | extracting | ranking
    error: Optional[str] = None  # 错误信息
    is_demo: bool = False  # 结果中包含演示数据
    agent_trace: List[str] = Field(default_factory=list)  # Agent 可见执行轨迹
    memory_context: Dict[str, Any] = Field(default_factory=dict)  # 本次使用的记忆上下文
    effective_query: Optional[str] = None  # 实际输入淘宝的搜索词
    created_at: datetime  # 创建时间


# ==================== 偏好相关 ====================

class BrandPreference(BaseModel):
    """品牌偏好"""
    brand: str
    score: float  # 偏好分数 0-1
    count: int  # 选择次数
    last_updated: datetime


class PricePreference(BaseModel):
    """价格偏好"""
    min: float
    max: float
    avg: float
    median: float


class UserPreference(BaseModel):
    """用户偏好"""
    user_id: str
    brand_preferences: Dict[str, BrandPreference] = {}
    price_preference: Optional[PricePreference] = None
    feature_preferences: Dict[str, float] = {}  # 特性偏好权重
    search_history: List[str] = []  # 搜索历史
    updated_at: datetime


class UserAction(BaseModel):
    """用户行为（用于学习偏好）"""
    user_id: str
    action_type: str  # search | click | view
    product_id: Optional[str] = None
    task_id: Optional[str] = None  # 商品所属的搜索任务，用于回查商品信息
    query: Optional[str] = None
    timestamp: datetime


# ==================== API 响应 ====================

class APIResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    message: Optional[str] = None
