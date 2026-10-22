"""Phase 3-25a：AI 與戰場變奏——評估每個可行型態、移到觸發條件的格子再施放（PM 決定 #9）。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.engine import BattleState, EndTurn, Move, UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.ai.variant import variant_move_bonus
from trpg.engine.events import SkillUsed
from trpg.shared.types import Team, UnitId

U1 = UnitId("unit_0001")
TIDAL = "skill_tidal_spear"
FLAT9 = "\n".join(["0000000"] * 9)
BASES = {
    "skill_tidal_spear": "hero_mage",
    "skill_wall_brace_bash": "hero_fighter",
    "skill_oil_spark_throw": "hero_archer",
    "skill_frost_ledge_cleave": "hero_fighter",
}


def _scene(
    skill_id: str,
    *,
    caster: tuple[int, int],
    foes: Sequence[tuple[int, int]],
    heights: str = FLAT9,
    terrain: str | None = None,
    surfaces: Sequence[tuple[int, int, str]] = (),
    element_mods: dict[str, int] | None = None,
) -> BattleState:
    m = make_map(heights, terrain, ally=[caster], enemy=foes, surfaces=surfaces)
    spawns = [spawn(Team.ALLY, caster, caster_template([skill_id], base=BASES[skill_id]))]
    foe = no_reactions("bandit", max_hp=200, element_mods=element_mods or {})
    spawns += [spawn(Team.ENEMY, xy, foe) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def test_the_ai_steps_into_water_and_casts_the_tidal_spear_line() -> None:
    """敵人在 4 格外（基礎型態射程 3 打不到），而且免疫火焰法杖的普攻；腳邊的水格讓矛化成直線
    貫穿 3 格：這一回合 AI 先走進水裡（變奏位置加分），再施放水中貫穿。"""
    state = _scene(
        TIDAL,
        caster=(3, 8),
        foes=[(3, 4)],
        surfaces=[(3, 7, "water")],
        element_mods={"fire": -1000},
    )
    ai = _ai()
    moved_into_water = False
    used: list[SkillUsed] = []
    for _ in range(8):
        if state.active_unit != U1 or state.ended:
            break
        action = ai(state)
        if isinstance(action, EndTurn):
            break
        if isinstance(action, Move) and (action.path[-1].x, action.path[-1].y) == (3, 7):
            moved_into_water = True
        result = resolve(state, action)
        used += [e for e in result.events if isinstance(e, SkillUsed) and e.skill_id == TIDAL]
        state = result.state
        if used:
            break
    assert moved_into_water
    assert [e.variant for e in used] == ["tide_pierce"]


def test_the_move_bonus_only_counts_tiles_that_newly_satisfy_a_variant() -> None:
    state = _scene(TIDAL, caster=(3, 8), foes=[(3, 4)], surfaces=[(3, 7, "water")])
    unit = state.units[U1]
    points = library().ai_profiles.basic.variant_position_bonus
    assert points > 0
    assert variant_move_bonus(state, unit, (3, 7), points) == points
    assert variant_move_bonus(state, unit, (2, 7), points) == 0
    wet = _scene(TIDAL, caster=(3, 8), foes=[(3, 4)], surfaces=[(3, 8, "water"), (3, 7, "water")])
    assert variant_move_bonus(wet, wet.units[U1], (3, 7), points) == 0  # 現在就成立


def test_the_move_bonus_counts_high_ground_above_an_enemy() -> None:
    heights = "\n".join(["0000000"] * 7 + ["0001000", "0000000"])
    state = _scene(TIDAL, caster=(3, 8), foes=[(3, 2)], heights=heights)
    points = library().ai_profiles.basic.variant_position_bonus
    assert variant_move_bonus(state, state.units[U1], (3, 7), points) == points


_USE_CASES = [
    ("skill_tidal_spear", (3, 4), (3, 2), (), None, None),
    (
        "skill_wall_brace_bash",
        (3, 4),
        (3, 3),
        (),
        ".......\n" * 4 + "..#....\n" + ".......\n" * 4,
        None,
    ),
    ("skill_oil_spark_throw", (3, 6), (3, 2), ((3, 2, "oil"),), None, None),
    ("skill_frost_ledge_cleave", (3, 4), (3, 3), ((3, 4, "ice"),), None, None),
]


@pytest.mark.parametrize(
    ("skill_id", "caster", "foe", "surfaces", "terrain", "heights"), _USE_CASES
)
def test_the_ai_uses_every_demo_skill_in_its_variant_form(
    skill_id: str,
    *,
    caster: tuple[int, int],
    foe: tuple[int, int],
    surfaces: tuple[tuple[int, int, str], ...],
    terrain: str | None,
    heights: str | None,
) -> None:
    state = _scene(
        skill_id,
        caster=caster,
        foes=[foe],
        surfaces=surfaces,
        terrain=None if terrain is None else terrain.strip(),
        heights=heights or FLAT9,
    )
    ranked = _ai().rank(state)
    best = max(ranked, key=lambda s: s.score)
    skill_scores = [s for s in ranked if isinstance(s.action, UseSkill)]
    assert skill_scores and max(s.score for s in skill_scores) > 0
    if isinstance(best.action, UseSkill):
        events = resolve(state, best.action).events
        assert any(isinstance(e, SkillUsed) and e.skill_id == skill_id for e in events)
    if skill_id != "skill_tidal_spear":  # 其他三招在這些場景裡條件成立：施放的是變奏型態
        action = next(s.action for s in skill_scores)
        used = [e for e in resolve(state, action).events if isinstance(e, SkillUsed)]
        assert used[0].variant is not None
