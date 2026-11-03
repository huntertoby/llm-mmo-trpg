"""經 Tunnel 時的真實 IP 與網路設定（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.2、31.3）。"""

from __future__ import annotations

import ipaddress
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trpg.api.account_config import AccountSettings
from trpg.api.app import create_app
from trpg.api.client_ip import client_ip
from trpg.api.login_limit import LoginLimiter
from trpg.api.server_config import (
    ServerConfigError,
    ServerSettings,
    load_server_settings,
)
from trpg.content.library import ContentLibrary

LOCAL = (ipaddress.ip_network("127.0.0.1/32"), ipaddress.ip_network("::1/128"))


def test_no_trusted_proxies_ignores_headers() -> None:
    headers = {"X-Forwarded-For": "5.5.5.5", "CF-Connecting-IP": "6.6.6.6"}
    assert client_ip("127.0.0.1", headers, ()) == "127.0.0.1"


def test_untrusted_peer_ignores_headers() -> None:
    headers = {"X-Forwarded-For": "5.5.5.5", "CF-Connecting-IP": "6.6.6.6"}
    assert client_ip("9.9.9.9", headers, LOCAL) == "9.9.9.9"


def test_cf_header_first_when_peer_trusted() -> None:
    headers = {"X-Forwarded-For": "5.5.5.5", "CF-Connecting-IP": "6.6.6.6"}
    assert client_ip("127.0.0.1", headers, LOCAL) == "6.6.6.6"


def test_forwarded_for_right_to_left_skipping_trusted() -> None:
    trusted = (*LOCAL, ipaddress.ip_network("10.0.0.0/8"))
    headers = {"x-forwarded-for": "1.2.3.4, 7.7.7.7, 10.1.2.3"}
    assert client_ip("127.0.0.1", headers, trusted) == "7.7.7.7"  # 最左邊的可以偽造，不取
    all_trusted = {"x-forwarded-for": "10.0.0.5, 10.0.0.6"}
    assert client_ip("127.0.0.1", all_trusted, trusted) == "10.0.0.5"


def test_invalid_headers_fall_back_to_peer() -> None:
    headers = {"CF-Connecting-IP": "not-an-ip", "X-Forwarded-For": "5.5.5.5, junk"}
    assert client_ip("127.0.0.1", headers, LOCAL) == "127.0.0.1"
    assert client_ip("::1", {}, LOCAL) == "::1"
    assert client_ip(None, {"CF-Connecting-IP": "6.6.6.6"}, LOCAL) is None
    assert client_ip("testclient", {"CF-Connecting-IP": "6.6.6.6"}, LOCAL) == "testclient"


def test_server_settings_defaults_and_env(tmp_path: Path) -> None:
    default = load_server_settings(env={})
    assert default.trusted_proxies == () and default.public_url == ""
    assert default.llm_health_interval_s == 60
    path = tmp_path / "server.toml"
    path.write_text(
        '[network]\npublic_url = "https://x.example.com/"\ntrusted_proxies = ["127.0.0.1"]\n'
        "[llm_health]\ninterval_s = 0\n",
        encoding="utf-8",
    )
    loaded = load_server_settings(path, env={})
    assert loaded.public_url == "https://x.example.com"
    assert loaded.trusted_proxies == ("127.0.0.1",) and loaded.llm_health_interval_s == 0
    env = {"TRPG_TRUSTED_PROXIES": "10.0.0.0/8, ::1", "TRPG_PUBLIC_URL": "https://y.example.com"}
    over = load_server_settings(path, env=env)
    assert over.trusted_proxies == ("10.0.0.0/8", "::1")
    assert over.public_url == "https://y.example.com"


def test_server_settings_rejects_bad_values(tmp_path: Path) -> None:
    with pytest.raises(ServerConfigError, match="trusted_proxies"):
        load_server_settings(env={"TRPG_TRUSTED_PROXIES": "nonsense"})
    with pytest.raises(ServerConfigError, match="public_url"):
        load_server_settings(env={"TRPG_PUBLIC_URL": "trpg.example.com"})
    path = tmp_path / "server.toml"
    path.write_text("[network]\nwhat = 1\n", encoding="utf-8")
    with pytest.raises(ServerConfigError, match=r"network\.what"):
        load_server_settings(path, env={})


def _app(library: ContentLibrary, tmp_path: Path, trusted: tuple[str, ...]) -> TestClient:
    app = create_app(
        library,
        save_dir=tmp_path,
        accounts=AccountSettings(dev_mode=False, login_ip_max_failures=2, login_max_failures=99),
        server=ServerSettings(trusted_proxies=trusted, llm_health_interval_s=0),
    )
    app.state.login_limiter = LoginLimiter(max_failures=99, ip_max_failures=2, window_s=600)
    return TestClient(app, client=("127.0.0.1", 50000))


def _fail(client: TestClient, user: str, real_ip: str) -> int:
    body = {"username": user, "password": secrets.token_urlsafe(12)}
    reply = client.post("/api/auth/login", json=body, headers={"CF-Connecting-IP": real_ip})
    return int(reply.status_code)


def test_login_limit_uses_real_ip_behind_trusted_proxy(
    library: ContentLibrary, tmp_path: Path
) -> None:
    client = _app(library, tmp_path, ("127.0.0.1",))
    assert _fail(client, "user_a", "5.5.5.5") == 401
    assert _fail(client, "user_b", "5.5.5.5") == 401
    assert _fail(client, "user_c", "5.5.5.5") == 429  # 同一個真實 IP
    assert _fail(client, "user_d", "6.6.6.6") == 401  # 經同一個 Tunnel 的別人不受影響


def test_login_limit_ignores_headers_without_trusted_proxy(
    library: ContentLibrary, tmp_path: Path
) -> None:
    client = _app(library, tmp_path, ())
    assert _fail(client, "user_a", "5.5.5.5") == 401
    assert _fail(client, "user_b", "6.6.6.6") == 401
    assert _fail(client, "user_c", "7.7.7.7") == 429  # 標頭被忽略：全部算 127.0.0.1
