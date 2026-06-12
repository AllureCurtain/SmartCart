"""
需求解析服务 - 使用 GLM API 理解自然语言
"""
import json
from openai import OpenAI
from models import ParsedQuery
import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_MODEL


class QueryParserService:
    """查询解析服务"""

    def __init__(self):
        self.client = OpenAI(
            api_key=ZHIPU_API_KEY,
            base_url=ZHIPU_BASE_URL
        )
        self.model = ZHIPU_MODEL

    def parse(self, query: str) -> ParsedQuery:
        """
        解析用户查询

        Args:
            query: 用户输入的自然语言，如"我想买500元左右的蓝牙耳机，音质要好"

        Returns:
            ParsedQuery 对象
        """
        prompt = f"""
请解析用户的购物需求，提取关键信息。

用户输入: {query}

请以 JSON 格式返回，包含以下字段：
- category: 商品品类（字符串）
- keywords: 搜索关键词列表（数组）
- price_min: 最低价格（数字，可为 null）
- price_max: 最高价格（数字，可为 null）
- features: 特性要求列表（数组，如["音质", "降噪"]）

只返回 JSON，不要其他文字。
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()

            # 去除可能的 markdown 代码块标记
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            # 解析 JSON
            parsed_data = json.loads(result_text)

            return ParsedQuery(
                category=parsed_data.get('category', ''),
                keywords=parsed_data.get('keywords', []),
                price_min=parsed_data.get('price_min'),
                price_max=parsed_data.get('price_max'),
                features=parsed_data.get('features', [])
            )

        except Exception as e:
            # 解析失败，返回简单版本
            return ParsedQuery(
                category=query,
                keywords=[query],
                price_min=None,
                price_max=None,
                features=[]
            )


# 测试代码
if __name__ == "__main__":
    parser = QueryParserService()

    test_queries = [
        "我想买500元左右的蓝牙耳机",
        "找个降噪好的耳机，预算1000-2000",
        "苹果手机壳"
    ]

    for query in test_queries:
        print(f"\n输入: {query}")
        result = parser.parse(query)
        print(f"解析: {result.dict()}")
