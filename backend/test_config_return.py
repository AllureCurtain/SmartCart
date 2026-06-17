"""切回 App 配置的自动探测单元测试。

测 _is_private_lan（私网判定）、_detect_lan_ip（出口 IP 探测 + 网卡兜底）与
_resolve_return_deeplink（deep link 解析），验证零配置自动探测（含代理 fake-ip
环境退回网卡枚举）+ 环境变量覆盖 + 无网络跳过，不依赖真实网络/adb。
"""
from unittest.mock import MagicMock, patch

import config


# —— _is_private_lan ——

def test_is_private_lan_accepts_rfc1918():
    assert config._is_private_lan("192.168.43.107") is True
    assert config._is_private_lan("10.0.0.1") is True
    assert config._is_private_lan("172.16.0.1") is True
    assert config._is_private_lan("172.31.255.255") is True


def test_is_private_lan_rejects_non_rfc1918():
    assert config._is_private_lan("198.18.0.1") is False       # 代理 fake-ip
    assert config._is_private_lan("100.111.43.110") is False   # Tailscale CGNAT
    assert config._is_private_lan("169.254.1.1") is False      # link-local
    assert config._is_private_lan("127.0.0.1") is False        # loopback
    assert config._is_private_lan("8.8.8.8") is False          # 公网
    assert config._is_private_lan("172.32.0.1") is False       # 172 公网段
    assert config._is_private_lan("not-an-ip") is False


# —— _detect_lan_ip ——

def test_detect_lan_ip_uses_exit_when_private():
    fake = MagicMock()
    fake.getsockname.return_value = ("192.168.43.107", 0)
    with patch("config.socket.socket", return_value=fake), \
         patch("config.socket.getaddrinfo") as gai:
        assert config._detect_lan_ip() == "192.168.43.107"
    gai.assert_not_called()  # 出口已是私网，不退回网卡枚举


def test_detect_lan_ip_falls_back_to_getaddrinfo_on_fakeip():
    # 出口被代理劫持成 fake-ip，枚举网卡时跳过 fake-ip/Tailscale，取真私网
    fake = MagicMock()
    fake.getsockname.return_value = ("198.18.0.1", 0)
    gai_results = [
        (None, None, None, None, ("198.18.0.1", 0)),
        (None, None, None, None, ("100.111.43.110", 0)),
        (None, None, None, None, ("192.168.43.107", 0)),
    ]
    with patch("config.socket.socket", return_value=fake), \
         patch("config.socket.getaddrinfo", return_value=gai_results), \
         patch("config.socket.gethostname", return_value="host"):
        assert config._detect_lan_ip() == "192.168.43.107"


def test_detect_lan_ip_returns_none_when_no_private_anywhere():
    fake = MagicMock()
    fake.getsockname.return_value = ("198.18.0.1", 0)
    gai_results = [
        (None, None, None, None, ("198.18.0.1", 0)),
        (None, None, None, None, ("100.111.43.110", 0)),
    ]
    with patch("config.socket.socket", return_value=fake), \
         patch("config.socket.getaddrinfo", return_value=gai_results), \
         patch("config.socket.gethostname", return_value="host"):
        assert config._detect_lan_ip() is None


def test_detect_lan_ip_returns_none_on_connect_error_and_no_fallback():
    fake = MagicMock()
    fake.connect.side_effect = OSError("no network")
    with patch("config.socket.socket", return_value=fake), \
         patch("config.socket.getaddrinfo", return_value=[]), \
         patch("config.socket.gethostname", return_value="host"):
        assert config._detect_lan_ip() is None


# —— _resolve_return_deeplink ——

def test_resolve_deeplink_explicit_env_overrides_detection(monkeypatch):
    monkeypatch.setenv("SMARTCART_RETURN_DEEPLINK", "myapp://custom-scheme")
    with patch("config._detect_lan_ip") as detect:
        assert config._resolve_return_deeplink() == "myapp://custom-scheme"
        detect.assert_not_called()  # 显式覆盖时不触发探测


def test_resolve_deeplink_auto_detects_ip_when_unset(monkeypatch):
    monkeypatch.delenv("SMARTCART_RETURN_DEEPLINK", raising=False)
    monkeypatch.setattr(config, "_detect_lan_ip", lambda: "192.168.43.107")
    assert config._resolve_return_deeplink() == "exp://192.168.43.107:8081"


def test_resolve_deeplink_none_when_no_ip_and_unset(monkeypatch):
    monkeypatch.delenv("SMARTCART_RETURN_DEEPLINK", raising=False)
    monkeypatch.setattr(config, "_detect_lan_ip", lambda: None)
    assert config._resolve_return_deeplink() is None
