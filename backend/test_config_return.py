"""切回 App 配置的自动探测单元测试。

测 _detect_lan_ip（出口 IP 探测）与 _resolve_return_deeplink（deep link 解析），
验证零配置自动探测 + 环境变量覆盖 + 无网络跳过三条路径，不依赖真实网络/adb。
"""
from unittest.mock import MagicMock, patch

import config


# —— _detect_lan_ip ——

def test_detect_lan_ip_returns_sockname_ip():
    fake = MagicMock()
    fake.getsockname.return_value = ("192.168.43.107", 0)
    with patch("config.socket.socket", return_value=fake):
        assert config._detect_lan_ip() == "192.168.43.107"
    fake.connect.assert_called_once_with(("8.8.8.8", 80))
    fake.close.assert_called_once()


def test_detect_lan_ip_ignores_loopback():
    fake = MagicMock()
    fake.getsockname.return_value = ("127.0.0.1", 0)
    with patch("config.socket.socket", return_value=fake):
        assert config._detect_lan_ip() is None


def test_detect_lan_ip_returns_none_on_oserror():
    fake = MagicMock()
    fake.connect.side_effect = OSError("no network")
    with patch("config.socket.socket", return_value=fake):
        assert config._detect_lan_ip() is None
    fake.close.assert_called_once()


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
