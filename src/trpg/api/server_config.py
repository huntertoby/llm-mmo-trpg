"""伺服器的網路與健康檢查設定：``config/server.toml`` 的 ``[network]``、``[llm_health]``
（Phase 5E-3，計畫 30.2）。

- ``public_url``：Tunnel 給的外部網址（只用來顯示與部署檢查，不影響綁定）。
- ``trusted_proxies``：可信任的轉發來源（IP 或 CIDR）；空＝不信任任何轉發標頭（30.3）。
- ``llm_health.interval_s``：定期 ping 本機模型的間隔（秒）；0＝只在啟動時 ping（30.4）。

環境變數覆寫：``TRPG_PUBLIC_URL``、``TRPG_TRUSTED_PROXIES``（逗號分隔）。設定檔路徑和帳號設定相同
（``TRPG_SERVER_CONFIG``，預設 ``config/server.toml``）。
"""

from __future__ import annotations

import ipaddress
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from trpg.api.account_config import CONFIG_ENV, DEFAULT_CONFIG_PATH
from trpg.shared.errors import TrpgError

__all__ = [
    "PUBLIC_URL_ENV",
    "TRUSTED_PROXIES_ENV",
    "IpNetwork",
    "ServerConfigError",
    "ServerSettings",
    "load_server_settings",
]

PUBLIC_URL_ENV: Final = "TRPG_PUBLIC_URL"
TRUSTED_PROXIES_ENV: Final = "TRPG_TRUSTED_PROXIES"
DEFAULT_HEALTH_INTERVAL_S: Final = 60

type IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class ServerConfigError(TrpgError):
    """伺服器設定（網路、健康檢查）無法使用。"""


class ServerSettings(BaseModel):
    """網路與本機模型健康檢查的設定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    public_url: str = ""
    """Tunnel 給的外部網址；空＝還沒設定（部署檢查會提醒）。"""
    trusted_proxies: tuple[str, ...] = ()
    """可信任的轉發來源（IP 或 CIDR）。"""
    llm_health_interval_s: int = Field(default=DEFAULT_HEALTH_INTERVAL_S, ge=0)
    """定期 ping 本機模型的間隔（秒）；0＝只在啟動時 ping。"""

    @field_validator("trusted_proxies")
    @classmethod
    def _valid_networks(cls, proxies: tuple[str, ...]) -> tuple[str, ...]:
        for proxy in proxies:
            try:
                ipaddress.ip_network(proxy.strip(), strict=False)
            except ValueError as exc:
                raise ValueError(f"trusted_proxies 的 {proxy!r} 不是 IP 或 CIDR") from exc
        return tuple(p.strip() for p in proxies)

    @field_validator("public_url")
    @classmethod
    def _valid_url(cls, url: str) -> str:
        url = url.strip()
        if url and not url.startswith(("https://", "http://")):
            raise ValueError("public_url 要以 https:// 或 http:// 開頭")
        return url.rstrip("/")

    def proxy_networks(self) -> tuple[IpNetwork, ...]:
        return tuple(ipaddress.ip_network(p, strict=False) for p in self.trusted_proxies)


def _section(raw: dict[str, object], name: str, path: Path) -> dict[str, object]:
    section = raw.get(name, {})
    if not isinstance(section, dict):
        raise ServerConfigError(f"伺服器設定檔 {path} 的 [{name}] 不是表格")
    return dict(section)


def _read(path: Path) -> dict[str, object]:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ServerConfigError(f"無法讀取伺服器設定檔 {path}：{exc}") from exc
    data: dict[str, object] = {}
    network = _section(raw, "network", path)
    health = _section(raw, "llm_health", path)
    unknown = sorted({*(f"network.{k}" for k in network), *(f"llm_health.{k}" for k in health)})
    known = {"network.public_url", "network.trusted_proxies", "llm_health.interval_s"}
    extra = [k for k in unknown if k not in known]
    if extra:
        raise ServerConfigError(f"伺服器設定檔 {path} 有不認得的欄位：{'、'.join(extra)}")
    if "public_url" in network:
        data["public_url"] = network["public_url"]
    if "trusted_proxies" in network:
        data["trusted_proxies"] = network["trusted_proxies"]
    if "interval_s" in health:
        data["llm_health_interval_s"] = health["interval_s"]
    return data


def load_server_settings(
    path: Path | None = None, env: Mapping[str, str] | None = None
) -> ServerSettings:
    """讀設定檔的 ``[network]``、``[llm_health]``（預設檔不存在時用預設值），再套用環境變數覆寫。"""
    environ = os.environ if env is None else env
    if path is None:
        override = environ.get(CONFIG_ENV)
        path = Path(override) if override else DEFAULT_CONFIG_PATH
    data: dict[str, object] = {}
    if path.is_file():
        data.update(_read(path))
    elif path != DEFAULT_CONFIG_PATH:
        raise ServerConfigError(f"找不到伺服器設定檔：{path}")
    if environ.get(PUBLIC_URL_ENV):
        data["public_url"] = environ[PUBLIC_URL_ENV]
    if environ.get(TRUSTED_PROXIES_ENV):
        data["trusted_proxies"] = [
            p.strip() for p in environ[TRUSTED_PROXIES_ENV].split(",") if p.strip()
        ]
    try:
        return ServerSettings.model_validate(data)
    except ValidationError as exc:
        raise ServerConfigError(f"伺服器設定不合法（{path}）：{exc}") from exc
