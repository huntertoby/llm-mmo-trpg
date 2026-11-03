"""Bot 設定（Phase 5E-2；``docs/phases/Phase5計畫.md`` 29.3）。

- 範本 ``config/bot.example.toml`` 進版控（沒有真的值）；真的值放 ``config/bot.local.toml``
  （``.gitignore`` 的 ``*.local.*`` 已排除）或環境變數，由使用者自己填。
- 讀取順序：``TRPG_BOT_CONFIG``（設定檔路徑）→ ``config/bot.local.toml``（不存在就略過）；
  環境變數 ``TRPG_BOT_TOKEN``、``TRPG_BOT_GUILD_ID``、``TRPG_BOT_ROLE_ID``、
  ``TRPG_BOT_ANNOUNCE_CHANNEL_ID`` 覆寫。
- 缺值或 ID 不是數字 → :class:`BotConfigError`，列出全部缺的欄位與環境變數，**不印 token**。
- 遊戲伺服器不讀這個設定：Bot 設定缺值不影響伺服器。
- ``[announce]``（5E-3，計畫 31.2）：每日公告的時區與時間（:func:`load_announce_settings`；沒填用
  預設 ``Asia/Taipei`` 6 點）。系統沒有時區資料（Windows 沒裝 ``tzdata``）時用
  ``utc_offset_minutes``。
"""

from __future__ import annotations

import datetime as dt
import os
import tomllib
import zoneinfo
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from trpg.shared.errors import TrpgError

__all__ = [
    "BOT_CONFIG_ENV",
    "EXAMPLE_CONFIG_PATH",
    "FIELD_ENV",
    "LOCAL_CONFIG_PATH",
    "AnnounceSettings",
    "BotConfigError",
    "BotSettings",
    "load_announce_settings",
    "load_bot_settings",
]

CONFIG_DIR: Final = Path(__file__).resolve().parents[3] / "config"
LOCAL_CONFIG_PATH: Final = CONFIG_DIR / "bot.local.toml"
EXAMPLE_CONFIG_PATH: Final = CONFIG_DIR / "bot.example.toml"
BOT_CONFIG_ENV: Final = "TRPG_BOT_CONFIG"
FIELD_ENV: Final = {
    "token": "TRPG_BOT_TOKEN",
    "guild_id": "TRPG_BOT_GUILD_ID",
    "role_id": "TRPG_BOT_ROLE_ID",
    "announce_channel_id": "TRPG_BOT_ANNOUNCE_CHANNEL_ID",
}
"""設定欄位 → 覆寫用的環境變數（依這個順序檢查與列出）。"""
ID_FIELDS: Final = ("guild_id", "role_id", "announce_channel_id")
_MASK_LEN: Final = 8
_SHOWN: Final = 4


class BotConfigError(TrpgError):
    """Bot 設定缺值或不合法（訊息不含 token）。"""


class BotSettings(BaseModel):
    """Bot 的連線設定。``token`` 是 :class:`SecretStr`（``repr``、log 都不會出現原文）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: SecretStr
    guild_id: str
    """Discord 伺服器 ID。"""
    role_id: str
    """能領帳號的身分組 ID。"""
    announce_channel_id: str
    """公告頻道 ID（5E-3 才用）。"""

    def masked_token(self) -> str:
        """只露最後 4 字。"""
        raw = self.token.get_secret_value()
        mask = "*" * _MASK_LEN
        return mask + raw[-_SHOWN:] if len(raw) > _MASK_LEN else mask


class AnnounceSettings(BaseModel):
    """每日公告的時間（5E-3）：每天 ``hour`` 點（``timezone``）貼今日公告。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    timezone: str = "Asia/Taipei"
    utc_offset_minutes: int = Field(default=480, ge=-14 * 60, le=14 * 60)
    """系統沒有 ``timezone`` 的時區資料時用的固定時差（台灣沒有日光節約，480＝UTC+8）。"""
    hour: int = Field(default=6, ge=0, le=23)

    def tzinfo(self) -> dt.tzinfo:
        try:
            return zoneinfo.ZoneInfo(self.timezone)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            return dt.timezone(dt.timedelta(minutes=self.utc_offset_minutes))


def _load_toml(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise BotConfigError(f"無法讀取 Bot 設定檔 {path}：{exc}") from exc


def _read_file(path: Path) -> dict[str, object]:
    raw = _load_toml(path)
    section = raw.get("discord", {})
    if not isinstance(section, dict):
        raise BotConfigError(f"Bot 設定檔 {path} 的 [discord] 不是表格")
    unknown = sorted(set(section) - set(FIELD_ENV))
    if unknown:
        raise BotConfigError(f"Bot 設定檔 {path} 有不認得的欄位：{'、'.join(unknown)}")
    return dict(section)


def _config_path(environ: Mapping[str, str]) -> Path | None:
    override = environ.get(BOT_CONFIG_ENV)
    if override:
        path = Path(override)
        if not path.is_file():
            raise BotConfigError(f"找不到 Bot 設定檔：{path}（環境變數 {BOT_CONFIG_ENV}）")
        return path
    return LOCAL_CONFIG_PATH if LOCAL_CONFIG_PATH.is_file() else None


def load_bot_settings(
    path: Path | None = None, env: Mapping[str, str] | None = None
) -> BotSettings:
    """讀 Bot 設定；缺值或不合法時 :class:`BotConfigError` 一次列出全部問題。"""
    environ = os.environ if env is None else env
    source = path if path is not None else _config_path(environ)
    data: dict[str, object] = _read_file(source) if source is not None else {}
    for field, name in FIELD_ENV.items():
        if environ.get(name):
            data[field] = environ[name]
    values = {field: str(data.get(field, "") or "").strip() for field in FIELD_ENV}
    problems = [
        f"{field}（設定檔 [discord] {field}，或環境變數 {FIELD_ENV[field]}）"
        for field, value in values.items()
        if not value
    ]
    problems += [
        f"{field} 要是數字（Discord 的 ID；在 Discord 開啟開發者模式後右鍵「複製 ID」）"
        for field in ID_FIELDS
        if values[field] and not values[field].isdigit()
    ]
    if problems:
        where = str(source) if source is not None else f"沒有設定檔（可建 {LOCAL_CONFIG_PATH}）"
        lines = "\n".join(f"  - {p}" for p in problems)
        raise BotConfigError(f"Bot 設定不完整（{where}）：\n{lines}\n範本：{EXAMPLE_CONFIG_PATH}")
    return BotSettings(
        token=SecretStr(values["token"]),
        guild_id=values["guild_id"],
        role_id=values["role_id"],
        announce_channel_id=values["announce_channel_id"],
    )


def load_announce_settings(
    path: Path | None = None, env: Mapping[str, str] | None = None
) -> AnnounceSettings:
    """讀 ``[announce]``（同一個 Bot 設定檔；沒有檔案或沒有這節＝預設值）。不需要 token。"""
    environ = os.environ if env is None else env
    source = path if path is not None else _config_path(environ)
    if source is None:
        return AnnounceSettings()
    section = _load_toml(source).get("announce", {})
    if not isinstance(section, dict):
        raise BotConfigError(f"Bot 設定檔 {source} 的 [announce] 不是表格")
    try:
        return AnnounceSettings.model_validate(section)
    except ValidationError as exc:
        raise BotConfigError(f"Bot 設定檔 {source} 的 [announce] 不合法：{exc}") from exc
