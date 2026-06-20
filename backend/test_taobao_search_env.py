"""
Regression check for Windows subprocess encoding.

Open-AutoGLM prints emoji during startup. On Windows shells using GBK stdout,
the child process can crash unless PYTHONIOENCODING is forced to utf-8.
"""
from pathlib import Path

import skills.taobao_search as taobao_search
from skills.taobao_search import TaobaoSearchSkill


class _FakeStdout:
    def __init__(self, lines):
        self._lines = iter(lines)

    def readline(self):
        return next(self._lines, "")

    def close(self):
        return None


class _FakePopen:
    def __init__(self, *args, **kwargs):
        self.args = args[0]
        self.kwargs = kwargs
        self.stdout = _FakeStdout(["step 1\n", "step 2\n"])
        self.returncode = 0
        self.killed = False

    def wait(self, timeout=None):
        self.wait_timeout = timeout
        return self.returncode

    def kill(self):
        self.killed = True


def test_autoglm_subprocess_uses_utf8_io_encoding_and_writes_debug_log(tmp_path):
    captured = {}

    def fake_popen(*args, **kwargs):
        proc = _FakePopen(*args, **kwargs)
        captured["env"] = kwargs["env"]
        captured["encoding"] = kwargs.get("encoding")
        captured["stderr"] = kwargs.get("stderr")
        captured["timeout"] = None
        captured["proc"] = proc
        return proc

    original_popen = taobao_search.subprocess.Popen
    try:
        taobao_search.subprocess.Popen = fake_popen
        skill = TaobaoSearchSkill()
        log_path = tmp_path / "autoglm.log"
        result = skill._run_autoglm("蓝牙耳机", {"PYTHONIOENCODING": "utf-8"}, log_path)
    finally:
        taobao_search.subprocess.Popen = original_popen

    # 子进程输出 UTF-8，父进程也必须按 UTF-8 解码——
    # 缺任何一半都会在中文 Windows (GBK) 上导致读取线程崩溃、管道堵塞超时
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["encoding"] == "utf-8"
    assert result.stdout == "step 1\nstep 2"
    log_text = log_path.read_text(encoding="utf-8")
    assert "step 1" in log_text
    assert "step 2" in log_text
    assert "returncode=0" in log_text


def test_search_uses_debug_runner_and_preserves_utf8_env():
    captured = {}

    def fake_runner(self, instruction, env, log_path, timeout=300):
        captured["instruction"] = instruction
        captured["env"] = env
        captured["log_path"] = log_path
        captured["timeout"] = timeout

        class Result:
            returncode = 0
            stderr = ""
            stdout = "ok"

        return Result()

    original_runner = TaobaoSearchSkill._run_autoglm
    try:
        TaobaoSearchSkill._run_autoglm = fake_runner
        skill = TaobaoSearchSkill()
        skill._capture_screenshot = lambda: Path("dummy.png")
        skill._extract_products_from_screenshot = lambda *_args: []

        skill.search("蓝牙耳机")
    finally:
        TaobaoSearchSkill._run_autoglm = original_runner

    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["env"].get("PHONE_AGENT_SKIP_CHECKS") == "1"
    assert captured["env"].get("PHONE_AGENT_LAUNCH_DELAY") == "0.2"
    assert captured["env"].get("PHONE_AGENT_TAP_DELAY") == "0.2"
    assert captured["env"].get("PHONE_AGENT_KEYBOARD_SWITCH_DELAY") == "0.2"
    assert captured["env"].get("PHONE_AGENT_TEXT_CLEAR_DELAY") == "0.1"
    assert captured["env"].get("PHONE_AGENT_TEXT_INPUT_DELAY") == "0.2"
    assert captured["env"].get("PHONE_AGENT_KEYBOARD_RESTORE_DELAY") == "0.1"
    assert captured["env"].get("PHONE_AGENT_MODEL_TIMEOUT_SECONDS") == "45"
    assert captured["env"].get("PHONE_AGENT_MODEL_MAX_RETRIES") == "0"
    assert captured["timeout"] == 300
    assert "蓝牙耳机" in captured["instruction"]
