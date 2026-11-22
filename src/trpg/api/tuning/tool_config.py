"""數值工坊這個開發工具自己的設定：``config/tuning.toml``（HC-8）。

不是遊戲規則（不進 ``content/``）：預設種子、模擬場數與工作量上限、樣本小門檻、草稿名字數、
分組改上限。

- 讀法比照 ``config/llm.toml``、``config/server.toml``：pydantic 驗證、``extra="forbid"``
  （打錯鍵名直接報錯），設定檔沒寫的鍵用 :class:`TuningToolSettings` 的預設值（等於 HC-8
  搬家前程式裡的值）。
- 使用者自己的覆寫放 ``config/tuning.local.toml``（``*.local.*`` 已在 ``.gitignore``，同
  ``config/bot.local.toml`` 的慣例）：有寫的鍵蓋過 ``tuning.toml``，沒寫的照 ``tuning.toml``。
- 另可用環境變數 ``TRPG_TUNING_CONFIG`` 指定其他設定檔（同 ``TRPG_LLM_CONFIG``）；
  指定的檔一定要存在。
- 模組載入時讀一次（:data:`TUNING_TOOL`）；改設定要重開伺服器。``api/tuning/schemas.py``、
  ``drafts.py``、``skills.py`` 的常數都從這裡取值。
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from trpg.shared.errors import TrpgError

__all__ = [
    "CONFIG_ENV",
    "DEFAULT_CONFIG_PATH",
    "LOCAL_CONFIG_PATH",
    "TUNING_TOOL",
    "TuningToolConfigError",
    "TuningToolSettings",
    "load_tuning_tool_settings",
]

CONFIG_ENV: Final = "TRPG_TUNING_CONFIG"
CONFIG_DIR: Final = Path(__file__).resolve().parents[4] / "config"
DEFAULT_CONFIG_PATH: Final = CONFIG_DIR / "tuning.toml"
LOCAL_CONFIG_PATH: Final = CONFIG_DIR / "tuning.local.toml"

_SECTIONS: Final = {
    "sim": {
        "default_seeds": "sim_default_seeds",
        "map_default_seeds": "map_default_seeds",
        "max_maps": "max_sim_maps",
        "max_battles": "max_sim_battles",
        "small_sample": "small_sample",
    },
    "ratio": {
        "default_seeds": "ratio_default_seeds",
        "max_seeds": "max_ratio_seeds",
        "max_work": "ratio_max_work",
    },
    "drafts": {"name_max": "draft_name_max"},
    "skills": {"max_group": "max_group"},
}
"""設定檔的 ``[表格] 鍵`` → :class:`TuningToolSettings` 的欄位。"""


class TuningToolConfigError(TrpgError):
    """數值工坊的設定檔無法使用。"""


class TuningToolSettings(BaseModel):
    """數值工坊的工具設定。預設值＝HC-8 搬家前寫在程式裡的值（``config/tuning.toml``
    也寫同樣的值）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sim_default_seeds: int = Field(default=3, ge=1)
    """頭目戰預設種子數：1 個頭目 × 8 build × 3 種子＝24 場（第 0.0 節第 5 點）。"""
    map_default_seeds: int = Field(default=24, ge=1)
    """地圖戰預設種子數：1 張圖 × 24 種子（NW-2 5.6）。"""
    max_sim_maps: int = Field(default=3, ge=1)
    """地圖戰一次最多幾張圖。"""
    max_sim_battles: int = Field(default=160, ge=1)
    """單次模擬的場數上限（改後）。"""
    small_sample: int = Field(default=30, ge=1)
    """分母小於這個數時標「樣本小」（規格 5.4）。"""
    ratio_default_seeds: int = Field(default=50, ge=1)
    """比值情境每組預設種子數（T11；BAL-21e 是 250）。"""
    max_ratio_seeds: int = Field(default=250, ge=1)
    """每組種子數的上限（比值情境與頭目戰、地圖戰的請求共用；NW-2c；BAL-21e 全表用 250）。"""
    ratio_max_work: int = Field(default=40_000, ge=1)
    """比值情境單次上限：組數 × 種子（T11）。"""
    draft_name_max: int = Field(default=40, ge=1)
    """草稿名稱最多幾個字（HC-6b：樣式和畫面的說明都照這個數）。"""
    max_group: int = Field(default=100, ge=1)
    """分組改一次最多幾招。"""

    @model_validator(mode="after")
    def _defaults_within_limit(self) -> Self:
        too_big = [
            name
            for name in ("sim_default_seeds", "map_default_seeds", "ratio_default_seeds")
            if getattr(self, name) > self.max_ratio_seeds
        ]
        if too_big:
            raise ValueError(
                f"{'、'.join(too_big)} 不能大於 ratio.max_seeds（{self.max_ratio_seeds}）"
            )
        return self


def _read(path: Path) -> dict[str, object]:
    """讀一個設定檔，轉成 :class:`TuningToolSettings` 的欄位（只含檔案裡有寫的鍵）。"""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise TuningToolConfigError(f"無法讀取數值工坊設定檔 {path}：{exc}") from exc
    data: dict[str, object] = {}
    unknown: list[str] = []
    for name, section in raw.items():
        keys = _SECTIONS.get(name)
        if keys is None or not isinstance(section, dict):
            unknown.append(name)
            continue
        for key, value in section.items():
            field = keys.get(key)
            if field is None:
                unknown.append(f"{name}.{key}")
            else:
                data[field] = value
    if unknown:
        raise TuningToolConfigError(
            f"數值工坊設定檔 {path} 有不認得的欄位：{'、'.join(sorted(unknown))}"
        )
    return data


def load_tuning_tool_settings(
    path: Path | None = None,
    local: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> TuningToolSettings:
    """讀 ``path``（預設 ``config/tuning.toml``，``TRPG_TUNING_CONFIG`` 可改；預設檔不存在時
    用預設值），再用 ``local``（預設 ``config/tuning.local.toml``，不存在就略過）有寫的鍵覆寫。"""
    environ = os.environ if env is None else env
    if path is None:
        override = environ.get(CONFIG_ENV)
        path = Path(override) if override else DEFAULT_CONFIG_PATH
    data: dict[str, object] = {}
    if path.is_file():
        data.update(_read(path))
    elif path != DEFAULT_CONFIG_PATH:
        raise TuningToolConfigError(f"找不到數值工坊設定檔：{path}")
    local_path = LOCAL_CONFIG_PATH if local is None else local
    if local_path.is_file():
        data.update(_read(local_path))
    try:
        return TuningToolSettings.model_validate(data)
    except ValidationError as exc:
        raise TuningToolConfigError(f"數值工坊設定不合法（{path}）：{exc}") from exc


TUNING_TOOL: Final = load_tuning_tool_settings()
"""伺服器啟動時讀到的數值工坊設定（模組載入時讀一次）。"""
