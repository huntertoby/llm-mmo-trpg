"""隱藏地點的感知判定（#112；Phase 5A-2 起在 :mod:`trpg.world.step`，6C-5 抽出來共用）。

- 抵達沒有實地地圖的地點：對相鄰的隱藏地點判定（:func:`trpg.world.step._perceive`）。
- 實地地圖：走到隱藏入口 3 格內判定（21.6、21.9 第 10 條；:mod:`trpg.world.field_things`）。

DC＝``perception.dc_for(隱藏地點建議等級)``；同一個角色對同一個隱藏地點每天（6 點刷新）只判定一次；
失敗沒有懲罰；只用角色自己的感知（朋友的影子不能代判，9.6.4）。亂數用 ``reveal`` 串流。
"""

from __future__ import annotations

from typing import Final

from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef
from trpg.shared.types import Attribute
from trpg.world.actions import LocationRevealedEvent, PerceptionCheckEvent, WorldEvent
from trpg.world.common import rules_of
from trpg.world.rng import STREAM_REVEAL, draw
from trpg.world.state import CharacterState, LocationRef, PerceptionMark, WorldState

__all__ = [
    "PERCEPTION_REVEAL",
    "can_perceive",
    "mark_perception",
    "perceive",
    "perception_modifier",
    "reveal_location",
]

PERCEPTION_REVEAL: Final = "perception_nearby"
"""地點的 ``reveal`` 寫了這個才會被感知判定發現。"""


def perception_modifier(library: ContentLibrary, char: CharacterState) -> int:
    """感知修正：``(感知 − ability_mod_base) // ability_mod_divisor``（同引擎的檢定修正）。"""
    core = library.ruleset.core
    wis = char.hero.attributes[Attribute.WIS]
    return (wis - core.ability_mod_base) // core.ability_mod_divisor


def mark_perception(char: CharacterState, region: str, location: str, day: int) -> CharacterState:
    marks = [m for m in char.perception_marks if (m.region, m.location) != (region, location)]
    marks.append(PerceptionMark(region=region, location=location, day=day))
    marks.sort(key=lambda m: (m.region, m.location))
    return char.model_copy(update={"perception_marks": tuple(marks)})


def reveal_location(char: CharacterState, region: str, location: str) -> CharacterState:
    """把隱藏地點加進角色的 ``revealed``（已發現則不變）。"""
    if char.has_revealed(region, location):
        return char
    refs = [*char.revealed, LocationRef(region=region, location=location)]
    refs.sort(key=LocationRef.key)
    return char.model_copy(update={"revealed": tuple(refs)})


def can_perceive(char: CharacterState, region: str, hidden: LocationDef, today: int) -> bool:
    """``hidden`` 現在能不能判定：是隱藏地點、可被感知發現、還沒發現、今天還沒判定過。"""
    return (
        hidden.hidden
        and PERCEPTION_REVEAL in hidden.reveal
        and not char.has_revealed(region, hidden.id)
        and char.perception_day(region, hidden.id) != today
    )


def perceive(  # noqa: PLR0917 - 判定要角色、世界、地點與日子
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    region: str,
    hidden: LocationDef,
    today: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    """擲一次感知（呼叫者先確認 :func:`can_perceive`）：記下今天判定過；成功就發現。"""
    assert hidden.level_min is not None
    dc = rules_of(library).perception.dc_for(hidden.level_min)
    modifier = perception_modifier(library, char)
    rng, char = draw(world.season_seed, char, STREAM_REVEAL)
    roll = rng.d20()
    success = roll + modifier >= dc
    char = mark_perception(char, region, hidden.id, today)
    events: list[WorldEvent] = [
        PerceptionCheckEvent(
            location=hidden.id, roll=roll, modifier=modifier, dc=dc, success=success
        )
    ]
    if success:
        char = reveal_location(char, region, hidden.id)
        events.append(LocationRevealedEvent(location=hidden.id, method=PERCEPTION_REVEAL))
    return char, events
