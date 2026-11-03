"""Bot 設定（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.3）。

測試裡的 token 一律用 ``secrets`` 當場產生；設定檔一律指向暫存資料夾（不讀使用者的
``config/bot.local.toml``）。
"""

from __future__ import annotations

import secrets
import subprocess
import tomllib
from pathlib import Path

import pytest

from trpg.bot.config import (
    BOT_CONFIG_ENV,
    EXAMPLE_CONFIG_PATH,
    FIELD_ENV,
    LOCAL_CONFIG_PATH,
    BotConfigError,
    load_bot_settings,
)

REPO = Path(__file__).resolve().parents[2]


def _write(path: Path, **values: str) -> Path:
    lines = ["[discord]"] + [f'{k} = "{v}"' for k, v in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _full(token: str) -> dict[str, str]:
    return {"token": token, "guild_id": "111", "role_id": "222", "announce_channel_id": "333"}


def test_example_has_no_values() -> None:
    raw = tomllib.loads(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"))
    assert set(raw["discord"]) == set(FIELD_ENV)
    assert all(value == "" for value in raw["discord"].values())


def test_local_config_is_gitignored() -> None:
    relative = LOCAL_CONFIG_PATH.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "-q", relative], cwd=REPO, check=False, capture_output=True
    )
    assert result.returncode == 0, f"{relative} 應該被 .gitignore 排除"


def test_missing_values_list_every_field(tmp_path: Path) -> None:
    empty = _write(tmp_path / "bot.toml")
    with pytest.raises(BotConfigError) as info:
        load_bot_settings(empty, env={})
    message = str(info.value)
    for field, env_name in FIELD_ENV.items():
        assert field in message and env_name in message
    assert str(EXAMPLE_CONFIG_PATH) in message


def test_file_values_and_env_override(tmp_path: Path) -> None:
    file_token, env_token = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    path = _write(tmp_path / "bot.toml", **_full(file_token))
    settings = load_bot_settings(path, env={})
    assert settings.token.get_secret_value() == file_token
    assert (settings.guild_id, settings.role_id, settings.announce_channel_id) == (
        "111",
        "222",
        "333",
    )
    env = {"TRPG_BOT_TOKEN": env_token, "TRPG_BOT_ROLE_ID": "999", BOT_CONFIG_ENV: str(path)}
    settings = load_bot_settings(env=env)
    assert settings.token.get_secret_value() == env_token
    assert settings.role_id == "999"


def test_env_only(tmp_path: Path) -> None:
    token = secrets.token_urlsafe(24)
    env = {FIELD_ENV[k]: v for k, v in _full(token).items()}
    settings = load_bot_settings(_write(tmp_path / "bot.toml"), env=env)
    assert settings.guild_id == "111"


def test_ids_must_be_digits_and_token_never_printed(tmp_path: Path) -> None:
    token = secrets.token_urlsafe(24)
    values = _full(token) | {"guild_id": "my-server"}
    with pytest.raises(BotConfigError) as info:
        load_bot_settings(_write(tmp_path / "bot.toml", **values), env={})
    assert "guild_id 要是數字" in str(info.value)
    assert token not in str(info.value)
    settings = load_bot_settings(_write(tmp_path / "ok.toml", **_full(token)), env={})
    assert token not in repr(settings) and token not in str(settings)
    assert settings.masked_token().endswith(token[-4:])
    assert token not in settings.masked_token()


def test_bad_file_and_unknown_field(tmp_path: Path) -> None:
    broken = tmp_path / "broken.toml"
    broken.write_text("[discord\n", encoding="utf-8")
    with pytest.raises(BotConfigError, match="無法讀取"):
        load_bot_settings(broken, env={})
    extra = _write(tmp_path / "extra.toml", tokn="x")
    with pytest.raises(BotConfigError, match="不認得的欄位"):
        load_bot_settings(extra, env={})
    with pytest.raises(BotConfigError, match="找不到 Bot 設定檔"):
        load_bot_settings(env={BOT_CONFIG_ENV: str(tmp_path / "missing.toml")})
