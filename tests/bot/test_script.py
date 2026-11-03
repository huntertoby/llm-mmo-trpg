"""``scripts/discord_bot.py``（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.10）。

設定缺值時腳本清楚報錯（exit 2），遊戲伺服器不讀 Bot 設定、照常啟動。
"""

from __future__ import annotations

import importlib.util
import io
import secrets
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from trpg.api.account_config import AccountSettings
from trpg.api.app import create_app
from trpg.bot.config import BOT_CONFIG_ENV
from trpg.content.library import ContentLibrary


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
    assert "token" in err.getvalue() and "TRPG_BOT_TOKEN" in err.getvalue()


def test_check_and_run(tmp_path: Path) -> None:
    script = _script()
    token = secrets.token_urlsafe(24)
    env = {BOT_CONFIG_ENV: str(_config(tmp_path / "bot.toml", token))}
    out, err = io.StringIO(), io.StringIO()
    assert script.main(["check"], out, err, env=env) == 0
    assert "設定齊全" in out.getvalue() and token not in out.getvalue()
    out, err = io.StringIO(), io.StringIO()
    assert script.main(["run"], out, err, env=env) == script.EXIT_NO_ADAPTER
    assert "DiscordGateway" in err.getvalue()
    assert token not in out.getvalue() + err.getvalue()


def test_server_ignores_bot_config(
    library: ContentLibrary, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bot 設定指向不存在的檔案也不影響遊戲伺服器。"""
    monkeypatch.setenv(BOT_CONFIG_ENV, str(tmp_path / "missing.toml"))
    app = create_app(library, save_dir=tmp_path / "saves", accounts=AccountSettings())
    with TestClient(app) as client:
        assert client.get("/api/auth/status").status_code == 200
