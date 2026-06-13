"""
Regression check for Windows subprocess encoding.

Open-AutoGLM prints emoji during startup. On Windows shells using GBK stdout,
the child process can crash unless PYTHONIOENCODING is forced to utf-8.
"""
from pathlib import Path

import skills.taobao_search as taobao_search
from skills.taobao_search import TaobaoSearchSkill


def test_autoglm_subprocess_uses_utf8_io_encoding():
    captured = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        captured["encoding"] = kwargs.get("encoding")

        class Result:
            returncode = 0
            stderr = ""

        return Result()

    original_run = taobao_search.subprocess.run
    try:
        taobao_search.subprocess.run = fake_run
        skill = TaobaoSearchSkill()
        skill._capture_screenshot = lambda: Path("dummy.png")
        skill._extract_products_from_screenshot = lambda *_args: []

        skill.search("蓝牙耳机")
    finally:
        taobao_search.subprocess.run = original_run

    # 子进程输出 UTF-8，父进程也必须按 UTF-8 解码——
    # 缺任何一半都会在中文 Windows (GBK) 上导致读取线程崩溃、管道堵塞超时
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["encoding"] == "utf-8"
