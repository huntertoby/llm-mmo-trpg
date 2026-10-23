"""LLM 設定：``config/llm.toml``＋環境變數覆寫。"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

__all__ = [
    "CONFIG_ENV",
    "DEFAULT_CONFIG_PATH",
    "LLMConfig",
    "LLMConfigError",
    "load_llm_config",
]

CONFIG_ENV = "TRPG_LLM_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "llm.toml"

_ENV_OVERRIDES = (
    ("base_url", "TRPG_LLM_BASE_URL"),
    ("model", "TRPG_LLM_MODEL"),
    ("timeout_s", "TRPG_LLM_TIMEOUT_S"),
    ("api_key", "TRPG_LLM_API_KEY"),
)


class LLMConfigError(Exception):
    """設定檔或環境變數無法使用。"""


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str = "http://localhost:8001/v1"
    model: str = "swift"
    api_key: str = "local"
    timeout_s: float = Field(default=120.0, gt=0)
    max_retries: int = Field(default=3, ge=1)
    temperature: float = Field(default=0.7, ge=0)
    max_tokens: int = Field(default=2048, ge=1)
    json_schema_mode: Literal["auto", "response_format", "guided_json", "none"] = "auto"
    fallback_alert_permille: int = Field(default=200, ge=0, le=1000)


def load_llm_config(path: Path | None = None, env: Mapping[str, str] | None = None) -> LLMConfig:
    """讀設定檔（預設檔不存在時用預設值），再套用環境變數覆寫。"""
    environ = os.environ if env is None else env
    if path is None:
        override = environ.get(CONFIG_ENV)
        path = Path(override) if override else DEFAULT_CONFIG_PATH
    data: dict[str, object] = {}
    if path.is_file():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as exc:
            raise LLMConfigError(f"無法讀取 LLM 設定檔 {path}：{exc}") from exc
    elif path != DEFAULT_CONFIG_PATH:
        raise LLMConfigError(f"找不到 LLM 設定檔：{path}")
    for key, name in _ENV_OVERRIDES:
        if environ.get(name):
            data[key] = environ[name]
    try:
        return LLMConfig.model_validate(data)
    except ValidationError as exc:
        raise LLMConfigError(f"LLM 設定不合法（{path}）：{exc}") from exc
