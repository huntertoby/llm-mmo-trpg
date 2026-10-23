"""技能工坊的「裝上試玩」設定（``content/workshop.yaml``；Phase 3F-1）。

只定義 schema 與單檔檢查；地圖存在且是靶場類型（``training``）、單位範本存在、起始區放得下等跨檔案
檢查由 :func:`workshop_problems`（``trpg.content.library`` 載入時呼叫）負責。
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, UnitTemplate
from trpg.content.maps import TRAINING_ARCHETYPE, MapDef
from trpg.content.schemas import ContentModel
from trpg.shared.types import Team

__all__ = [
    "WorkshopOpponents",
    "WorkshopRules",
    "WorkshopTextEntry",
    "WorkshopTextTable",
    "workshop_problems",
]


class WorkshopOpponents(ContentModel):
    """一組可選的對手（例：木樁、會反擊）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    enemies: tuple[str, ...] = Field(min_length=1)


class WorkshopRules(ContentModel):
    """``content/workshop.yaml``。"""

    map: str = Field(pattern=ID_PATTERN)
    """預設地圖（靶場）。"""
    max_rounds: int = Field(ge=1, le=200)
    opponents: tuple[WorkshopOpponents, ...] = Field(min_length=1)
    """可選的對手；第一個是預設。"""

    @model_validator(mode="after")
    def _unique(self) -> WorkshopRules:
        ids = [o.id for o in self.opponents]
        if len(set(ids)) != len(ids):
            raise ValueError("opponents 的 id 不可重複")
        return self

    def opponent(self, opponent_id: str | None) -> WorkshopOpponents | None:
        """``None`` 為預設（第一個）；不存在時回傳 ``None``。"""
        if opponent_id is None:
            return self.opponents[0]
        return next((o for o in self.opponents if o.id == opponent_id), None)

    def summary(self) -> str:
        return f"地圖 {self.map}，{len(self.opponents)} 種對手"


def workshop_problems(
    rules: WorkshopRules, maps: Mapping[str, MapDef], units: Mapping[str, UnitTemplate]
) -> list[str]:
    """跨檔案檢查：地圖存在且是靶場類型、單位範本存在、敵方起始區放得下。"""
    map_def = maps.get(rules.map)
    if map_def is None:
        return [f"未知的地圖：{rules.map}"]
    problems: list[str] = []
    if map_def.archetype != TRAINING_ARCHETYPE:
        problems.append(
            f"地圖 {rules.map} 的類型必須是 {TRAINING_ARCHETYPE}，收到 {map_def.archetype}"
        )
    unknown = sorted({t for o in rules.opponents for t in o.enemies if t not in units})
    if unknown:
        problems.append(f"未知的單位範本：{', '.join(unknown)}")
    most = max(len(o.enemies) for o in rules.opponents)
    if len(map_def.start_zones[Team.ENEMY]) < most:
        problems.append(f"地圖 {rules.map} 的敵方起始區放不下 {most} 名敵人")
    return problems


class WorkshopTextEntry(ContentModel):
    """玩法 PM 改寫的一筆工坊說明（3-48f）：source＝程式裡的原文，player＝玩家語氣。"""

    id: str = Field(min_length=1)
    """來源檔的編號（例：``原語.zone``、``工坊.effects.effects=push``），只供對照。"""
    source: str = Field(min_length=1)
    player: str = Field(min_length=1)
    scope: str | None = None
    """同一段原文在不同欄位要用不同說法時填欄位範圍（例 add_stack.stack）。"""


class WorkshopTextTable(ContentModel):
    """``content/workshop_text.yaml``：工坊說明的玩家語氣對照表。玩家模式顯示 ``player``，
    ``?dev=1`` 顯示原文 ``source``。程式依原文（與選填的欄位範圍）查表；沒有對到的說明維持
    3-48c 的程式化處理。"""

    texts: tuple[WorkshopTextEntry, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> WorkshopTextTable:
        seen: dict[tuple[str, str | None], str] = {}
        by_text: dict[str, set[str]] = {}
        for entry in self.texts:
            key = (entry.source, entry.scope)
            if key in seen and seen[key] != entry.player:
                raise ValueError(f"同一段原文與範圍有兩種玩家語氣：{entry.id}")
            seen[key] = entry.player
            if entry.scope is None:
                by_text.setdefault(entry.source, set()).add(entry.player)
        clashing = sorted(t[:20] for t, p in by_text.items() if len(p) > 1)
        if clashing:
            raise ValueError(f"原文相同但玩家語氣不同，需要填 scope：{'、'.join(clashing)}")
        return self

    def lookup(self, source: str, scope: str | None = None) -> str | None:
        """原文對應的玩家語氣；先找指定範圍，再找不分範圍的。"""
        plain: str | None = None
        for entry in self.texts:
            if entry.source != source:
                continue
            if scope is not None and entry.scope == scope:
                return entry.player
            if entry.scope is None:
                plain = entry.player
        return plain
