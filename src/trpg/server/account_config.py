"""帳號設定：``config/server.toml`` 的 ``[accounts]``＋環境變數覆寫（Phase 5E-1，計畫 28.2）。

機器相關的值（帳號存檔資料夾）放設定檔，不寫死在程式裡（5E-4 的預留，計畫 28.12）。
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.shared.errors import TrpgError

__all__ = [
    "ACCOUNTS_DIR_ENV",
    "CONFIG_ENV",
    "DEFAULT_CONFIG_PATH",
    "DEV_MODE_ENV",
    "AccountConfigError",
    "AccountSettings",
    "load_account_settings",
]

CONFIG_ENV: Final = "TRPG_SERVER_CONFIG"
DEV_MODE_ENV: Final = "TRPG_DEV_MODE"
ACCOUNTS_DIR_ENV: Final = "TRPG_ACCOUNTS_DIR"
DEFAULT_CONFIG_PATH: Final = Path(__file__).resolve().parents[3] / "config" / "server.toml"


class AccountConfigError(TrpgError):
    """設定檔或環境變數無法使用。"""


class AccountSettings(BaseModel):
    """帳號與登入的設定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dev_mode: bool = True
    """開發模式：開著時大世界 API 不用登入（照 5A-5）；帶了有效 token 照樣依帳號存取
    （代決 5E1-1）。"""
    max_characters: int = Field(default=3, ge=1, le=10)
    """一個帳號最多幾個角色（3.1「2～3 個」）。"""
    session_ttl_hours: int = Field(default=168, ge=1)
    """session 有效時間（小時）。"""
    dir: str = ""
    """帳號存檔資料夾；空字串＝``<存檔資料夾>/accounts``。"""
    login_max_failures: int = Field(default=5, ge=1)
    """同一帳號名稱在視窗內最多失敗幾次（5E-2，計畫 29.7）。"""
    login_ip_max_failures: int = Field(default=5, ge=1)
    """同一 IP 在視窗內最多失敗幾次。"""
    login_window_minutes: int = Field(default=15, ge=1)
    """登入失敗的計數視窗（分鐘）。"""

    @property
    def session_ttl_s(self) -> int:
        return self.session_ttl_hours * 3600

    @property
    def login_window_s(self) -> int:
        return self.login_window_minutes * 60

    def accounts_dir(self, save_dir: Path) -> Path:
        return Path(self.dir) if self.dir else save_dir / "accounts"


def _parse_bool(name: str, raw: str) -> bool:
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise AccountConfigError(f"環境變數 {name} 要是 true 或 false")


def load_account_settings(
    path: Path | None = None, env: Mapping[str, str] | None = None
) -> AccountSettings:
    """讀設定檔的 ``[accounts]``（預設檔不存在時用預設值），再套用環境變數覆寫。"""
    environ = os.environ if env is None else env
    if path is None:
        override = environ.get(CONFIG_ENV)
        path = Path(override) if override else DEFAULT_CONFIG_PATH
    data: dict[str, object] = {}
    if path.is_file():
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            raise AccountConfigError(f"無法讀取伺服器設定檔 {path}：{exc}") from exc
        section = raw.get("accounts", {})
        if not isinstance(section, dict):
            raise AccountConfigError(f"伺服器設定檔 {path} 的 [accounts] 不是表格")
        data.update(section)
    elif path != DEFAULT_CONFIG_PATH:
        raise AccountConfigError(f"找不到伺服器設定檔：{path}")
    if environ.get(DEV_MODE_ENV):
        data["dev_mode"] = _parse_bool(DEV_MODE_ENV, environ[DEV_MODE_ENV])
    if environ.get(ACCOUNTS_DIR_ENV):
        data["dir"] = environ[ACCOUNTS_DIR_ENV]
    try:
        return AccountSettings.model_validate(data)
    except ValidationError as exc:
        raise AccountConfigError(f"伺服器設定不合法（{path}）：{exc}") from exc
