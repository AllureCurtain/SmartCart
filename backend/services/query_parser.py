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
from config import ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_TEXT_MODEL


class QueryParserService:
    """查询解析服务"""

    def __init__(self):
        self.client = OpenAI(
            api_key=ZHIPU_API_KEY,
            base_url=ZHIPU_BASE_URL
        )
        # 必须用对话模型；autoglm-phone 是手机 Agent 模型，解析必然失败
        self.model = ZHIPU_TEXT_MODEL

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
- category: 商品搜索关键词（字符串）。必须是适合直接输入淘宝搜索框的具体商品词，
  保留品牌和品类（如"苹果手机壳"就返回"苹果手机壳"，不要抽象成"手机配件"），
  但去掉"我想买"、价格、语气词等非商品信息
- keywords: 搜索关键词列表（数组）
- price_min: 最低价格（数字，可为 null）
- price_max: 最高价格（数字，可为 null）
- 价格规则：用户明确给出区间（如"预算1000-2000"）时原样使用；
  只说"X元左右"时取 X*0.8 到 X*1.2
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
            # 解析失败，降级为整句搜索（不可静默：会导致淘宝收到自然语言长句）
            print(f"Query parse failed, fallback to raw query: {e}")
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
