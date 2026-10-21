"""技能工坊 API 的請求與回應（Phase 3F-1）。

技能一律以 **技能定義的 JSON**（``content/skills/*.yaml`` 的同一份欄位，可以缺欄位）傳遞；選項與檢查
結果的模型直接沿用 :mod:`trpg.skillgen.option_models` 與 :mod:`trpg.skillgen.draft_check`。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.schemas import MapSummary
from trpg.content.skills import SkillRarity
from trpg.narrative.skill_icon import SkillIcon
from trpg.narrative.skills import SkillCard
from trpg.shared.rng import MASK64
from trpg.skillgen.draft_check import DraftCheck

__all__ = [
    "ArenaOpponents",
    "WorkshopArena",
    "WorkshopCheck",
    "WorkshopExport",
    "WorkshopRandom",
    "WorkshopRandomRequest",
    "WorkshopSkillRequest",
]


class _ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkshopSkillRequest(_ApiModel):
    """組到一半（或完整）的技能。"""

    skill: dict[str, Any] = Field(default_factory=dict)


class WorkshopCheck(DraftCheck):
    """:class:`~trpg.skillgen.draft_check.DraftCheck` ＋ 技能卡片（完整且通過 schema 時才有）。"""

    card: SkillCard | None = None
    icon: SkillIcon
    """組裝式圖示（Phase 3-17）：草稿組到哪一步就有哪些部件（沒完成也有，``partial`` 為真）。"""


class WorkshopRandomRequest(_ApiModel):
    """隨機組合器（``trpg skills random`` 同一個函式）：同種子同參數結果一致。"""

    seed: int = Field(ge=0, le=MASK64)
    tier: int | None = Field(default=None, ge=1, le=5)
    rarity: SkillRarity | None = None
    skeleton: str | None = None


class WorkshopRandom(_ApiModel):
    skill: dict[str, Any]
    """完整的技能定義（JSON），可以直接再送進 ``options``／``check`` 修改。"""
    check: WorkshopCheck


class WorkshopExport(_ApiModel):
    yaml: str
    """與 ``content/skills/*.yaml`` 同格式的 YAML（``provenance.origin: workshop``）。"""
    filename: str
    legal: bool
    problems: tuple[str, ...]


class ArenaOpponents(_ApiModel):
    id: str
    name_zh: str
    description_zh: str
    enemies: tuple[str, ...]
    """敵人的中文名（依擺放順序）。"""


class WorkshopArena(_ApiModel):
    """裝上試玩的選單：預設地圖（靶場）與可選的地圖、對手。"""

    default_map: str
    max_rounds: int
    maps: tuple[MapSummary, ...]
    """靶場在最前面，其後是一般地圖。"""
    opponents: tuple[ArenaOpponents, ...]
    """靶場的對手（第一個是預設）。"""
