"""登入嘗試次數限制（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.7）。

測試裡的密碼一律用 ``secrets`` 當場產生。
"""

from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trpg.api.account_config import AccountSettings, load_account_settings
from trpg.api.accounts import AccountStore
from trpg.api.app import create_app
from trpg.api.login_limit import LoginLimiter, LoginRateLimitError
from trpg.content.library import ContentLibrary


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _wrong() -> str:
    return secrets.token_urlsafe(12)


def test_limit_per_username_and_window() -> None:
    clock = Clock()
    limiter = LoginLimiter(max_failures=3, ip_max_failures=100, window_s=60, clock=clock)
    for _ in range(3):
        limiter.check("Alice", "1.1.1.1")
        limiter.failed("Alice", "1.1.1.1")
    with pytest.raises(LoginRateLimitError):
        limiter.check("alice", "2.2.2.2")  # 不分大小寫、換 IP 也一樣
    limiter.check("bob", "1.1.1.1")  # 別的帳號不受影響
    clock.now += 61
    limiter.check("alice", "1.1.1.1")  # 視窗過後恢復


def test_limit_per_ip() -> None:
    limiter = LoginLimiter(max_failures=100, ip_max_failures=2, window_s=60, clock=Clock())
    limiter.failed("a1", "9.9.9.9")
    limiter.failed("a2", "9.9.9.9")
    with pytest.raises(LoginRateLimitError):
        limiter.check("a3", "9.9.9.9")
    limiter.check("a3", "8.8.8.8")


def test_success_clears_username_only() -> None:
    limiter = LoginLimiter(max_failures=2, ip_max_failures=3, window_s=60, clock=Clock())
    limiter.failed("alice", "9.9.9.9")
    limiter.failed("alice", "9.9.9.9")
    limiter.succeeded("alice")
    limiter.check("alice", "8.8.8.8")
    limiter.failed("bob", "9.9.9.9")
    with pytest.raises(LoginRateLimitError):
        limiter.check("carol", "9.9.9.9")  # IP 的紀錄沒被清


def test_settings_defaults() -> None:
    settings = load_account_settings(env={})
    assert (settings.login_max_failures, settings.login_ip_max_failures) == (5, 5)
    assert settings.login_window_s == 15 * 60


def test_login_endpoint_returns_429(library: ContentLibrary, tmp_path: Path) -> None:
    settings = AccountSettings(dev_mode=False, login_max_failures=3, login_ip_max_failures=50)
    app = create_app(library, save_dir=tmp_path / "saves", accounts=settings)
    pw = secrets.token_urlsafe(12)
    store = app.state.accounts
    assert isinstance(store, AccountStore)
    store.create("alice", pw)
    with TestClient(app) as client:
        for _ in range(3):
            bad = client.post("/api/auth/login", json={"username": "alice", "password": _wrong()})
            assert bad.status_code == 401
        blocked = client.post("/api/auth/login", json={"username": "alice", "password": pw})
        assert blocked.status_code == 429  # 連正確密碼也先擋
        assert blocked.json() == {"detail": "登入嘗試次數過多，請稍後再試"}
        assert pw not in blocked.text
        # 不存在的帳號也照算（不透露存在）
        for _ in range(3):
            client.post("/api/auth/login", json={"username": "ghost", "password": _wrong()})
        ghost = client.post("/api/auth/login", json={"username": "ghost", "password": _wrong()})
        assert ghost.status_code == 429
