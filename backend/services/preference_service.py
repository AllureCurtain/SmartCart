"""
偏好学习服务 - Memory 机制
"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from collections import Counter

from models import (
    UserPreference,
    BrandPreference,
    PricePreference,
    UserAction,
    Product,
    ParsedQuery
)


class PreferenceService:
    """用户偏好学习服务"""

    def __init__(self, storage_path: str = "data/preferences"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_preference(self, user_id: str) -> UserPreference:
        """获取用户偏好"""
        file_path = self.storage_path / f"{user_id}.json"

        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换字符串时间为 datetime
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                for brand_key, brand_data in data.get('brand_preferences', {}).items():
                    brand_data['last_updated'] = datetime.fromisoformat(brand_data['last_updated'])
                return UserPreference(**data)
        else:
            # 创建新用户偏好
            return UserPreference(
                user_id=user_id,
                updated_at=datetime.now()
            )

    def save_preference(self, preference: UserPreference):
        """保存用户偏好"""
        file_path = self.storage_path / f"{preference.user_id}.json"

        # 转换为可序列化格式
        data = preference.dict()
        data['updated_at'] = data['updated_at'].isoformat()
        for brand_key, brand_data in data.get('brand_preferences', {}).items():
            brand_data['last_updated'] = brand_data['last_updated'].isoformat()

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_search(self, user_id: str, query: str, parsed_query: ParsedQuery):
        """记录搜索行为"""
        pref = self.get_preference(user_id)

        # 添加搜索历史
        pref.search_history.append(query)
        if len(pref.search_history) > 50:  # 保留最近 50 条
            pref.search_history = pref.search_history[-50:]

        # 更新价格偏好
        if parsed_query.price_min or parsed_query.price_max:
            self._update_price_preference(pref, parsed_query)

        # 更新特性偏好
        for feature in parsed_query.features:
            if feature not in pref.feature_preferences:
                pref.feature_preferences[feature] = 0.1
            else:
                pref.feature_preferences[feature] = min(1.0, pref.feature_preferences[feature] + 0.1)

        pref.updated_at = datetime.now()
        self.save_preference(pref)

    def record_product_view(self, user_id: str, product: Product):
        """记录商品查看行为"""
        pref = self.get_preference(user_id)

        # 更新品牌偏好
        if product.brand:
            if product.brand not in pref.brand_preferences:
                pref.brand_preferences[product.brand] = BrandPreference(
                    brand=product.brand,
                    score=0.1,
                    count=1,
                    last_updated=datetime.now()
                )
            else:
                brand_pref = pref.brand_preferences[product.brand]
                brand_pref.count += 1
                brand_pref.score = min(1.0, brand_pref.score + 0.05)
                brand_pref.last_updated = datetime.now()

        pref.updated_at = datetime.now()
        self.save_preference(pref)

    def record_product_click(self, user_id: str, product: Product):
        """记录商品点击行为（权重更高）"""
        pref = self.get_preference(user_id)

        # 更新品牌偏好（点击权重更高）
        if product.brand:
            if product.brand not in pref.brand_preferences:
                pref.brand_preferences[product.brand] = BrandPreference(
                    brand=product.brand,
                    score=0.3,
                    count=1,
                    last_updated=datetime.now()
                )
            else:
                brand_pref = pref.brand_preferences[product.brand]
                brand_pref.count += 1
                brand_pref.score = min(1.0, brand_pref.score + 0.15)
                brand_pref.last_updated = datetime.now()

        pref.updated_at = datetime.now()
        self.save_preference(pref)

    def _update_price_preference(self, pref: UserPreference, parsed_query: ParsedQuery):
        """更新价格偏好"""
        prices = []

        # 从历史记录中提取价格
        if pref.price_preference:
            prices.append(pref.price_preference.avg)

        # 添加当前查询的价格
        if parsed_query.price_min:
            prices.append(parsed_query.price_min)
        if parsed_query.price_max:
            prices.append(parsed_query.price_max)

        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)

            pref.price_preference = PricePreference(
                min=min_price,
                max=max_price,
                avg=avg_price,
                median=sorted(prices)[len(prices) // 2]
            )

    def get_recommendation_weights(self, user_id: str) -> Dict[str, float]:
        """
        获取推荐权重

        Returns:
            {
                "brand:Sony": 0.8,
                "brand:Bose": 0.6,
                "feature:降噪": 0.7,
                ...
            }
        """
        pref = self.get_preference(user_id)
        weights = {}

        # 品牌权重
        for brand, brand_pref in pref.brand_preferences.items():
            weights[f"brand:{brand}"] = brand_pref.score

        # 特性权重
        for feature, score in pref.feature_preferences.items():
            weights[f"feature:{feature}"] = score

        return weights


# 测试代码
if __name__ == "__main__":
    service = PreferenceService()

    # 测试：记录搜索
    parsed = ParsedQuery(
        category="蓝牙耳机",
        keywords=["蓝牙", "耳机"],
        price_min=400,
        price_max=600
    )
    service.record_search("test_user", "我想买500元左右的蓝牙耳机", parsed)

    # 测试：查看商品
    product = Product(
        id="test1",
        title="Sony WH-1000XM5",
        price=1899.0,
        brand="Sony",
        platform="taobao"
    )
    service.record_product_view("test_user", product)

    # 获取偏好
    pref = service.get_preference("test_user")
    print(f"用户偏好: {pref.dict()}")
