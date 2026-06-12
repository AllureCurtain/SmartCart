"""
淘宝搜索 Skill - 封装 Open-AutoGLM
"""
import os
import sys
import subprocess
import base64
import json
from pathlib import Path
from typing import List
from openai import OpenAI

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from models import Product
from config import ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_MODEL, ADB_PATH

# 添加 Open-AutoGLM 到路径
AUTOGLM_PATH = Path(__file__).parent.parent.parent.parent / "Open-AutoGLM"


class TaobaoSearchSkill:
    """淘宝搜索技能"""

    def __init__(self, demo_mode: bool = False):
        """
        初始化淘宝搜索技能

        Args:
            demo_mode: 演示模式，使用模拟数据（快速测试），默认 False
        """
        self.autoglm_path = AUTOGLM_PATH
        self.adb_path = ADB_PATH
        self.api_key = ZHIPU_API_KEY
        self.base_url = ZHIPU_BASE_URL
        self.model = ZHIPU_MODEL
        self.demo_mode = demo_mode

    def search(self, keyword: str, max_products: int = 10) -> List[Product]:
        """
        在淘宝搜索商品

        Args:
            keyword: 搜索关键词
            max_products: 最多返回商品数

        Returns:
            商品列表
        """
        # 演示模式：直接返回模拟数据
        if self.demo_mode:
            print(f"[演示模式] 模拟搜索: {keyword}")
            return self._extract_products_from_screenshot(keyword, max_products)

        # 真实模式：调用 Open-AutoGLM
        instruction = f"打开淘宝搜索{keyword}，然后截图显示搜索结果"

        # 设置环境变量
        env = os.environ.copy()
        env['PATH'] = self.adb_path + os.pathsep + env.get('PATH', '')

        try:
            # 执行 Open-AutoGLM
            result = subprocess.run([
                sys.executable,
                str(self.autoglm_path / 'main.py'),
                '--base-url', self.base_url,
                '--model', self.model,
                '--apikey', self.api_key,
                instruction
            ], cwd=str(self.autoglm_path), env=env, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise Exception(f"搜索失败: {result.stderr}")

            # 提取商品信息
            products = self._extract_products_from_screenshot(keyword, max_products)

            return products

        except subprocess.TimeoutExpired:
            raise Exception("搜索超时（300秒）")
        except Exception as e:
            raise Exception(f"搜索出错: {str(e)}")

    def _extract_products_from_screenshot(self, keyword: str, max_count: int) -> List[Product]:
        """
        从截图中提取商品信息 - 调用 GLM 多模态 API
        """
        # 演示模式：返回模拟数据
        if self.demo_mode:
            return self._get_mock_products(keyword, max_count)

        # 真实模式：从 Open-AutoGLM 截图中提取
        # 查找最新的截图
        screenshot_dir = self.autoglm_path / "screenshots"
        if not screenshot_dir.exists():
            print("⚠️  未找到截图目录，使用模拟数据")
            return self._get_mock_products(keyword, max_count)

        screenshots = sorted(screenshot_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not screenshots:
            print("⚠️  未找到截图，使用模拟数据")
            return self._get_mock_products(keyword, max_count)

        # 使用最新的截图
        screenshot_path = screenshots[0]
        print(f"📸 分析截图: {screenshot_path.name}")

        try:
            # 读取截图并编码为 base64
            with open(screenshot_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 调用 GLM 多模态 API
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            response = client.chat.completions.create(
                model="glm-4v",  # 多模态模型
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": f"""这是淘宝搜索"{keyword}"的结果页面截图。
请提取前{max_count}个商品的信息，返回 JSON 格式：
[
  {{
    "title": "商品标题",
    "price": 价格数字,
    "rating": 评分（如果有）,
    "review_count": 评价数（如果有）,
    "sales": 销量（如果有）,
    "brand": "品牌（如果能识别）"
  }}
]

只返回 JSON 数组，不要其他文字。如果某个字段无法识别，设为 null。"""
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )

            # 解析返回的 JSON
            content = response.choices[0].message.content.strip()

            # 移除可能的 markdown 代码块标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            products_data = json.loads(content)

            # 转换为 Product 对象
            products = []
            for i, p in enumerate(products_data[:max_count], 1):
                products.append(Product(
                    id=f"tb_{i}_{hash(p.get('title', ''))}",
                    title=p.get('title', f'商品 {i}'),
                    price=float(p.get('price', 0)),
                    original_price=None,
                    rating=float(p.get('rating')) if p.get('rating') else None,
                    review_count=int(p.get('review_count')) if p.get('review_count') else None,
                    sales=int(p.get('sales')) if p.get('sales') else None,
                    brand=p.get('brand'),
                    platform="taobao"
                ))

            print(f"✅ 提取了 {len(products)} 个商品")
            return products

        except Exception as e:
            print(f"⚠️  商品信息提取失败: {e}")
            print("   使用模拟数据作为降级方案")
            return self._get_mock_products(keyword, max_count)

    def _get_mock_products(self, keyword: str, max_count: int) -> List[Product]:
        """生成模拟商品数据"""
        return [
            Product(
                id=f"tb_{i}",
                title=f"【{keyword}】商品 {i} - 高品质推荐",
                price=99.0 + i * 50,
                original_price=199.0 + i * 50,
                rating=4.5 + (i % 5) * 0.1,
                review_count=1000 + i * 500,
                sales=500 + i * 100,
                brand=f"Brand{i % 3 + 1}",
                platform="taobao"
            )
            for i in range(1, max_count + 1)
        ]


# 测试代码
if __name__ == "__main__":
    skill = TaobaoSearchSkill()
    products = skill.search("蓝牙耳机", max_products=5)

    print(f"搜索到 {len(products)} 个商品:")
    for p in products:
        print(f"- {p.title} | ¥{p.price} | ⭐{p.rating}")
