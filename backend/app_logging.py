"""
统一日志配置。

后端通过 uvicorn 启动，子进程输出在中文 Windows 上易因编码崩溃，
集中配置 stdout handler + UTF-8，确保排障时日志可见。
"""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """初始化根日志器；重复调用安全（已配置则跳过）"""
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s",
                          datefmt="%H:%M:%S")
    )
    root.addHandler(handler)
    root.setLevel(level)
