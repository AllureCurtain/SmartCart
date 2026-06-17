"""
配置管理
"""
import logging
import os
import socket
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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

def _detect_lan_ip() -> str | None:
    """探测本机局域网出口 IP（best-effort，不实际发包）。

    用 UDP socket connect 一个公网地址，OS 只查路由表决定出口 IP、不发送数据包，
    因此不依赖该地址可达、也无网络开销。用于自动拼切回 App 的 deep link，
    省去手动配 IP。单测/CI/无网络时返回 None，切回逻辑自动跳过，不影响其他功能。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        return ip if ip and not ip.startswith("127.") else None
    except OSError:
        return None
    finally:
        sock.close()


def _resolve_return_deeplink() -> str | None:
    """切回 App 的 deep link：显式环境变量覆盖 > 自动探测本机 IP 拼开发模式链接 > None。

    开发模式(Expo Go) deep link 形如 exp://<开发机IP>:8081。零配置下用本机出口
    IP 自动拼接，与 App 端 expo-constants 读取的开发机 IP 一致；想覆盖（多网卡、
    指定 IP、生产 APK 自有 scheme）设 SMARTCART_RETURN_DEEPLINK。探测不到 IP
    （CI/单测/无网络）返回 None，切回跳过。
    """
    explicit = os.getenv('SMARTCART_RETURN_DEEPLINK')
    if explicit:
        return explicit
    ip = _detect_lan_ip()
    return f"exp://{ip}:8081" if ip else None


# —— 搜索结束后把手机焦点切回 App（best-effort，失败只记日志不影响结果）——
# 单手机架构下 AutoGLM 接管手机搜索，结束时手机停在淘宝/京东页面，需主动切回；
# 否则用户既看不到结果，开发模式下 Expo Go 还会因长时间后台而 "Cannot connect to Expo CLI"。
# deep link 默认零配置自动探测本机 IP（开发模式 exp://），与 App 端读取的开发机 IP 一致；
# 探测不到或 CI/单测环境自动跳过。SMARTCART_RETURN_DEEPLINK 可显式覆盖（如生产 APK 自有 scheme）。
RETURN_DEEPLINK = _resolve_return_deeplink()
# 约束该 deep link 由哪个包处理；默认 Expo Go（host.exp.exponent），留空交系统解析。
RETURN_PACKAGE = os.getenv('SMARTCART_RETURN_PACKAGE', 'host.exp.exponent')

# 搜索结束、切回 App 前需要重建的 USB 反向隧道端口（逗号分隔）。
# AutoGLM 接管手机搜索期间会高频调用 adb（输入/截屏/控件），把 adb reverse
# 建立的端口映射重置掉；切回会让 Expo Go 经 deep-link 重载，此刻若隧道不在，
# App 走 localhost 既连不到 Metro 也连不到后端 → 恢复最近结果失败、显示空首页。
# 在切回前重建这两个端口即可闭环。默认重建 Metro(8081)+后端(8000)；留空则不重建。
RETURN_REVERSE_PORTS = [
    int(p.strip())
    for p in os.getenv('SMARTCART_RETURN_REVERSE_PORTS', '8081,8000').split(',')
    if p.strip()
]

logger.info("Config loaded (agent=%s, vision=%s, text=%s, return_deeplink=%s)",
            ZHIPU_MODEL, ZHIPU_VISION_MODEL, ZHIPU_TEXT_MODEL, RETURN_DEEPLINK or "(skip)")
