"""
配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 Open-AutoGLM 的 .env 文件
env_path = Path(__file__).parent.parent.parent / "Open-AutoGLM" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    raise FileNotFoundError(f".env 文件不存在: {env_path}")

# 验证必需的配置
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')
ZHIPU_BASE_URL = os.getenv('ZHIPU_BASE_URL')
ZHIPU_MODEL = os.getenv('ZHIPU_MODEL', 'autoglm-phone')
# 截图商品提取用的多模态模型（glm-4v-flash 免费）
ZHIPU_VISION_MODEL = os.getenv('ZHIPU_VISION_MODEL', 'glm-4v-flash')
# 需求解析用的对话模型（glm-4-flash 免费）。
# 注意不能用 ZHIPU_MODEL：autoglm-phone 是手机操作 Agent 模型，
# 不输出常规 JSON，解析必然失败并降级成整句搜索
ZHIPU_TEXT_MODEL = os.getenv('ZHIPU_TEXT_MODEL', 'glm-4-flash')

if not ZHIPU_API_KEY:
    raise ValueError("ZHIPU_API_KEY 未设置")
if not ZHIPU_BASE_URL:
    raise ValueError("ZHIPU_BASE_URL 未设置")

# ADB platform-tools 目录；未配置时保留当前开发机默认路径作为本地 fallback
ADB_PATH = os.getenv(
    'ADB_PATH',
    r"C:\Users\AllureLove\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools",
)

print(f"Config loaded successfully (Model: {ZHIPU_MODEL})")
