"""``tests/world`` 共用的小工具。"""

from __future__ import annotations

import dataclasses
from typing import Any

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_rules import WorldRules
from trpg.shared.types import Attribute
from trpg.world.state import EncounterResult, WorldState

NOON = 1_793_592_000

PARTY = ("merc_tiebi", "merc_huichun")
"""打得贏的測試隊伍（5C-2 起雇 0 名＝獨行；需要打贏的測試帶這兩名傭兵）。"""
"""2026-11-02 12:00 台北（UTC 04:00）；遊戲日的前半（白天）。"""


def with_rules(library: ContentLibrary, **updates: Any) -> ContentLibrary:
    """換掉 ``world_rules`` 的部分欄位（巢狀欄位傳 dict 時只蓋過給的鍵）。"""
    assert library.world_rules is not None
    data = library.world_rules.model_dump()
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    return dataclasses.replace(library, world_rules=WorldRules.model_validate(data))


def hero(library: ContentLibrary, *, wis: int | None = None) -> UnitTemplate:
    template = next(b.hero for b in library.builds.builds if b.id == "build_support")
    if wis is None:
        return template
    attributes = {**template.attributes, Attribute.WIS: wis}
    return template.model_copy(update={"attributes": attributes})


def make_world(**updates: Any) -> WorldState:
    data: dict[str, Any] = {"season_id": "s1", "season_seed": 20261102, "season_start": NOON}
    data.update(updates)
    return WorldState.model_validate(data)


SEASON_BOOKKEEPING: dict[str, Any] = {"rolled_day": None, "activity": (), "world_events": ()}
"""5F-1 每個動作都會寫的賽季紀錄（換日、上線紀錄、世界事件）；比較「其他世界欄位不變」時拿掉。"""


def without_season(world: WorldState) -> WorldState:
    """拿掉換日與上線紀錄（見 :data:`SEASON_BOOKKEEPING`）。"""
    return world.model_copy(update=SEASON_BOOKKEEPING)


def make_encounter(
    location: str,
    *,
    seed: int = 0,
    battle_map: str | None = None,
    level: int = 1,
    from_location: str | None = None,
    weather: str = "clear",
) -> EncounterResult:
    """雲嶺 ``location`` 的遭遇（5A-4 測試用）。"""
    return EncounterResult(
        region="cloud_ridge",
        location=location,
        level=level,
        battle_map=battle_map,
        battle_seed=seed,
        weather=weather,
        day_phase="day",
        at=NOON,
        from_location=from_location,
    )
