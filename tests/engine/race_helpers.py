"""種族技與環境被動測試（Phase 3R-2）共用的小工具：U1 是指定種族的戰士，其餘是沒有反應的盜賊。

``legacy_fox=True``：把種族 ``fox`` 換回 #138 之前的「舊狐族」（狐火誘餌＋靈覺）。那兩項已經退役、
不在 ``content/races.yaml``，但效果 ``decoy`` 與被動規則 ``detect_hidden_nearby`` 的引擎程式保留
（舊紀錄照樣能重播），所以用這份測試專用的定義繼續測。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4
from trpg.content.library import Ruleset
from trpg.content.races import RaceDef
from trpg.engine import BattleState, EndTurn, ResolveResult, UseRaceSkill, resolve
from trpg.engine.events import EventBase
from trpg.shared.types import Pos, Team

__all__ = [
    "FLAT7",
    "LEGACY_FOX_PASSIVE",
    "LEGACY_FOX_SKILL",
    "U1",
    "U2",
    "U3",
    "U4",
    "act",
    "all_races",
    "end_turn",
    "legacy_fox_rules",
    "of",
    "race_state",
    "use",
]


LEGACY_FOX_SKILL: Final[dict[str, Any]] = {
    "id": "race_foxfire_decoy",
    "name_zh": "狐火誘餌",
    "description_zh": "在 2 格內放一個誘餌，敵人的下一次單體攻擊會打向它。每場限用 1 次。",
    "uses_per_battle": 1,
    "shape": {"type": "ground_tile", "range": 2},
    "effects": [
        {
            "type": "decoy",
            "range": 2,
            "summon": "summon_foxfire_decoy",
            "lifetime": 3,
            "ai_trigger_range": 7,
        }
    ],
}
"""#138 之前的狐族種族技（退役，照 3R-2 的資料）。"""
LEGACY_FOX_PASSIVE: Final[dict[str, Any]] = {
    "id": "fox_keen_senses",
    "name_zh": "靈覺",
    "description_zh": "看得見 2 格內的敵方陷阱與隱蔽單位。",
    "rule": "detect_hidden_nearby",
    "radius": 2,
}
"""#138 之前的狐族環境被動（退役）。"""


def legacy_fox_rules(rules: Ruleset) -> Ruleset:
    """``rules`` 的複本，種族 ``fox`` 換回舊狐族（狐火誘餌＋靈覺）。"""
    table = rules.races
    assert table is not None
    races = tuple(
        RaceDef.model_validate(
            {
                **r.model_dump(mode="json", exclude_none=True),
                "name_zh": "狐族",
                "skill": LEGACY_FOX_SKILL,
                "passive": LEGACY_FOX_PASSIVE,
            }
        )
        if r.id == "fox"
        else r
        for r in table.races
    )
    ruleset = rules.model_copy(update={"races": table.model_copy(update={"races": races})})
    ruleset.model_post_init(None)
    return ruleset


def race_state(
    race: str | None,
    *,
    me: tuple[int, int] = (3, 3),
    foes: Sequence[tuple[int, int]] = ((6, 3),),
    allies: Sequence[tuple[int, int]] = (),
    heights: str = FLAT7,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    surfaces: Sequence[tuple[int, int, str]] = (),
    weather: str | None = None,
    map_tags: Sequence[str] = (),
    foe_base: str = "bandit",
    foe_race: str | None = None,
    foe_hp: int = 999,
    foe_attrs: dict[str, int] | None = None,
    my_hp: int = 999,
    legacy_fox: bool = False,
) -> BattleState:
    """U1 ＝ 指定種族的戰士（沒有反應、HP ``my_hp``）；敵人依 ``foes`` 排在 U1 與友方之後。
    ``legacy_fox``：種族 ``fox`` 用舊狐族的定義（見模組說明）。"""
    m = make_map(
        heights, terrain, ally=[me, *allies], enemy=list(foes), objects=objects, surfaces=surfaces
    )
    if map_tags:
        m = m.model_copy(update={"tags": tuple(map_tags)})
    spawns = [
        spawn(Team.ALLY, me, no_reactions("hero_fighter", max_hp=my_hp, race=race)),
        *[spawn(Team.ALLY, xy, no_reactions("hero_archer", max_hp=999)) for xy in allies],
    ]
    overrides: dict[str, object] = {"max_hp": foe_hp, "race": foe_race}
    if foe_attrs:
        overrides["attributes"] = foe_attrs
    spawns += [spawn(Team.ENEMY, xy, no_reactions(foe_base, **overrides)) for xy in foes]
    state = make_state(m, spawns, weather=weather)
    if legacy_fox:
        state.ruleset = legacy_fox_rules(state.ruleset)
    return give_turn(state, U1)


def use(
    *,
    target_id: str | None = None,
    target_object_id: str | None = None,
    pos: tuple[int, int] | None = None,
    direction: str | None = None,
    choice: str | None = None,
    unit: str = U1,
) -> UseRaceSkill:
    return UseRaceSkill.model_validate(
        {
            "unit_id": unit,
            "target_id": target_id,
            "target_object_id": target_object_id,
            "target_pos": None if pos is None else Pos(x=pos[0], y=pos[1]),
            "direction": direction,
            "choice": choice,
        }
    )


def act(state: BattleState, **fields: object) -> ResolveResult:
    return resolve(state, use(**fields))  # type: ignore[arg-type]


def of[E: EventBase](result: ResolveResult, kind: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, kind)]


def all_races() -> tuple[RaceDef, ...]:
    races = library().ruleset.races
    assert races is not None
    return races.races


def end_turn(state: BattleState) -> ResolveResult:
    """目前行動者結束回合。"""
    assert state.active_unit is not None
    return resolve(state, EndTurn(unit_id=state.active_unit))
