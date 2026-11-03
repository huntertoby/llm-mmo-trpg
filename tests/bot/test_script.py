"""``scripts/discord_bot.py``（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.10）。

設定缺值時腳本清楚報錯（exit 2），遊戲伺服器不讀 Bot 設定、照常啟動。
"""

from __future__ import annotations

import importlib.util
import io
import secrets
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.bot.announcer import Announcer
from trpg.bot.config import BOT_CONFIG_ENV, BotConfigError, BotSettings
from trpg.bot.fake import FakeDiscordGateway
from trpg.bot.gateway import DiscordGateway
from trpg.bot.service import BotService
from trpg.content.library import ContentLibrary
from trpg.server.account_config import AccountSettings


def _script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "discord_bot.py"
    spec = importlib.util.spec_from_file_location("discord_bot", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["discord_bot"] = module
    spec.loader.exec_module(module)
    return module


def _config(path: Path, token: str = "") -> Path:
    body = (
        f'[discord]\ntoken = "{token}"\nguild_id = "1"\nrole_id = "2"\nannounce_channel_id = "3"\n'
    )
    path.write_text(body, encoding="utf-8")
    return path


def test_check_reports_missing_values(tmp_path: Path) -> None:
    script = _script()
    out, err = io.StringIO(), io.StringIO()
    code = script.main(["--config", str(_config(tmp_path / "bot.toml")), "check"], out, err, env={})
    assert code == script.EXIT_CONFIG
    assert "token" in err.getvalue() and "TRPG_DISCORD_TOKEN" in err.getvalue()


def test_check(tmp_path: Path) -> None:
    script = _script()
    token = secrets.token_urlsafe(24)
    env = {BOT_CONFIG_ENV: str(_config(tmp_path / "bot.toml", token))}
    out, err = io.StringIO(), io.StringIO()
    assert script.main(["check"], out, err, env=env) == 0
    assert "設定齊全" in out.getvalue() and token not in out.getvalue()


def test_run_without_token_exits_before_connecting(tmp_path: Path) -> None:
    script = _script()
    calls: list[object] = []
    out, err = io.StringIO(), io.StringIO()
    env = {BOT_CONFIG_ENV: str(_config(tmp_path / "bot.toml"))}
    code = script.main(["run"], out, err, env=env, run_bot=lambda *a: calls.append(a))
    assert code == script.EXIT_CONFIG
    assert "TRPG_DISCORD_TOKEN" in err.getvalue() and ".env" in err.getvalue()
    assert calls == []


@pytest.fixture
def save_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    saves = tmp_path / "saves"
    monkeypatch.setenv("TRPG_SAVE_DIR", str(saves))
    monkeypatch.setenv("TRPG_ACCOUNTS_DIR", str(saves / "accounts"))
    return saves


def test_run_hands_service_and_announcer_to_adapter(tmp_path: Path, save_dir: Path) -> None:
    """``run`` 把設定、BotService、Announcer 交給 run_bot（換成假的，不連線）。"""
    script = _script()
    token = secrets.token_urlsafe(24)
    env = {BOT_CONFIG_ENV: str(_config(tmp_path / "bot.toml", token))}
    seen: dict[str, object] = {}

    def fake_run_bot(
        settings: BotSettings,
        make_service: Callable[[DiscordGateway], BotService],
        make_announcer: Callable[[DiscordGateway], Announcer] | None,
        clock: Callable[[], int],
    ) -> None:
        gateway = FakeDiscordGateway()
        seen["settings"] = settings
        seen["service"] = make_service(gateway)
        assert make_announcer is not None
        seen["announcer"] = make_announcer(gateway)
        seen["now"] = clock()

    out, err = io.StringIO(), io.StringIO()
    assert script.main(["run"], out, err, env=env, run_bot=fake_run_bot) == 0
    settings = seen["settings"]
    assert isinstance(settings, BotSettings) and settings.token.get_secret_value() == token
    service = seen["service"]
    assert isinstance(service, BotService)
    assert (service.guild_id, service.role_id) == ("1", "2")
    announcer = seen["announcer"]
    assert isinstance(announcer, Announcer) and announcer.channel_id == "3"
    assert announcer.state_path.is_relative_to(save_dir)
    assert isinstance(seen["now"], int) and seen["now"] > 0
    assert token not in out.getvalue() + err.getvalue()


def test_run_reports_adapter_config_error(tmp_path: Path, save_dir: Path) -> None:
    script = _script()
    token = secrets.token_urlsafe(24)
    env = {BOT_CONFIG_ENV: str(_config(tmp_path / "bot.toml", token))}

    def failing(*_args: object) -> None:
        raise BotConfigError("Discord 拒絕這個 token")

    out, err = io.StringIO(), io.StringIO()
    assert script.main(["run"], out, err, env=env, run_bot=failing) == script.EXIT_CONFIG
    assert "拒絕" in err.getvalue() and token not in err.getvalue()


def test_server_ignores_bot_config(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bot 設定指向不存在的檔案也不影響遊戲伺服器。"""
    monkeypatch.setenv(BOT_CONFIG_ENV, str(tmp_path / "missing.toml"))
    app = create_app(library, save_dir=tmp_path / "saves", accounts=AccountSettings())
    with TestClient(app) as client:
        assert client.get("/api/auth/status").status_code == 200
