"""LLM 設定：``config/llm.toml``＋環境變數覆寫。"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal

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
    ("enable_thinking", "TRPG_LLM_ENABLE_THINKING"),
    ("reasoning_effort", "TRPG_LLM_REASONING_EFFORT"),
    ("generate", "TRPG_LLM_GENERATE"),
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
    max_tokens: int = Field(default=1024, ge=1)
    json_schema_mode: Literal["auto", "response_format", "guided_json", "none"] = "auto"
    fallback_alert_permille: int = Field(default=200, ge=0, le=1000)
    probe_timeout_s: float = Field(default=3.0, gt=0)
    """伺服器檢查本機模型連不連得上（``GET {base_url}/models``）最多等幾秒（HC-7 b 從
    ``trpg.api.llm_source`` 的常數搬來，預設同原值）。"""
    situation_attempts: int = Field(default=2, ge=1)
    """情境判定提議每題最多嘗試幾次（HC-7 b 從 ``trpg.llm.situation`` 搬來，預設同原值）。"""
    story_attempts: int = Field(default=2, ge=1)
    """大世界說書人每次最多嘗試幾次（HC-7 b 從 ``trpg.narrative.storyteller`` 搬來，預設同
    原值）。"""
    generate: bool = False
    """LLM 生成開關（Phase 4-L6）：打開時 ``trpg run`` 的候選請本機模型提議技能；預設關
    （沒有本機模型時照舊）。命令列 ``--llm`` 也能打開；環境變數 ``TRPG_LLM_GENERATE``
    （true／false）可覆寫。"""
    enable_thinking: bool = False
    """Qwen3 等模型預設會先「思考」而把 ``max_tokens`` 用光；請求一律帶
    ``chat_template_kwargs: {"enable_thinking": …}``（Phase 4-L5 實測）。"""
    reasoning_effort: str | None = None
    """有值時請求多帶 ``reasoning_effort``；LM Studio 上的 Gemma 不認 ``chat_template_kwargs``，
    要 ``"none"`` 才不思考（2026-11-03 實測）。預設不送（vLLM 不一定接受 ``none``）。"""
    oneof_as_anyof: bool = True
    """送出 JSON schema 前把所有 ``oneOf`` 改寫成 ``anyOf``（MAC-2）：LM Studio 的 MLX 引擎不支援
    ``oneOf``（帶 ``oneOf`` 的 ``response_format`` 回 HTTP 400，退到 ``guided_json`` 又會被
    整個忽略，模型自由發揮）。專案的 schema 只用 ``oneOf`` 做判別式 union（各分支的 ``kind``
    互斥），改成 ``anyOf`` 語意相同；vLLM 的 xgrammar 本來就是這樣近似的。"""


LLM_DEFAULTS: Final = LLMConfig()
"""``config/llm.toml`` 沒寫時的值（schema 的預設）。程式裡要預設值的地方一律讀這裡，不另寫數字
（HC-7 b）；伺服器與命令列照設定檔讀到的 :class:`LLMConfig` 帶。"""


def client_config(client: object) -> LLMConfig:
    """``client`` 帶的設定（:class:`~trpg.llm.client.OpenAICompatClient` 的 ``config``）；Mock 等
    沒有設定的 client 用 :data:`LLM_DEFAULTS`。"""
    config = getattr(client, "config", None)
    return config if isinstance(config, LLMConfig) else LLM_DEFAULTS


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
