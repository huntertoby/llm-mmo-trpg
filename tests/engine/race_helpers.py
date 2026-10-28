"""種族技與環境被動測試（Phase 3R-2）共用的小工具：U1 是指定種族的戰士，其餘是沒有反應的盜賊。"""

from __future__ import annotations

from collections.abc import Sequence

from tests.engine.helpers import give_turn, library, make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4
from trpg.content.races import RaceDef
from trpg.engine import BattleState, EndTurn, ResolveResult, UseRaceSkill, resolve
from trpg.engine.events import EventBase
from trpg.shared.types import Pos, Team

__all__ = [
    "FLAT7",
    "U1",
    "U2",
    "U3",
    "U4",
    "act",
    "all_races",
    "end_turn",
    "of",
    "race_state",
    "use",
]


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
) -> BattleState:
    """U1 ＝ 指定種族的戰士（沒有反應、HP ``my_hp``）；敵人依 ``foes`` 排在 U1 與友方之後。"""
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
    return give_turn(make_state(m, spawns, weather=weather), U1)


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
