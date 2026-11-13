"""BS-2「要拿匕首類」標灰（06 6.21.1 C2、08 8.11）：:func:`trpg.api.condition_off.skills_off`。

無聲類技能（無聲步、影纏）在手上不是匕首或雙匕首時標灰；雙牙「兩下都中」在不是雙匕首時標灰。
拿對武器時不標。
"""

from __future__ import annotations

from tests.engine.helpers import make_map, make_state, no_reactions, spawn
from tests.engine.skill_helpers import FLAT7, U1
from trpg.api.condition_off import OFF_REASON_ZH, skills_off
from trpg.api.schemas import SkillOffOut
from trpg.engine import BattleState
from trpg.shared.types import Team

STEP = "skill_silent_step"
BIND = "skill_shadow_bind"
FANG = "skill_twin_fang"
POUNCE = "skill_lone_wolf_pounce"
ALL = (STEP, BIND, FANG)


def _state(weapon: str, skills: tuple[str, ...] = ALL, *, allies: int = 0) -> BattleState:
    spots = [(1, 1), (1, 3)]
    m = make_map(FLAT7, ally=spots[: 1 + allies], enemy=[(5, 3)])
    units = [spawn(Team.ALLY, spots[0], "hero_fighter", weapon, skills=skills)]
    units += [spawn(Team.ALLY, spots[1], "bandit")] * allies
    units += [spawn(Team.ENEMY, (5, 3), no_reactions("bandit"))]
    return make_state(m, units)


def test_dual_dagger_greys_nothing() -> None:
    assert skills_off(_state("dual_dagger"), U1) is None


def test_dagger_greys_only_the_twin_fang_poison() -> None:
    assert skills_off(_state("dagger"), U1) == (
        SkillOffOut(
            skill_id=FANG,
            conditions=("all_strikes_hit",),
            whole=False,
            reason_zh=OFF_REASON_ZH["all_strikes_hit"],
            effects=(1,),
        ),
    )


def test_sword_greys_silent_skills_and_twin_fang() -> None:
    silent = OFF_REASON_ZH["silent_strike"]
    assert "要拿匕首類" in silent
    assert skills_off(_state("one_handed_sword"), U1) == (
        SkillOffOut(
            skill_id=BIND,
            conditions=("silent_strike",),
            whole=False,
            reason_zh=silent,
            effects=(1,),
        ),
        SkillOffOut(skill_id=STEP, conditions=("silent_strike",), whole=True, reason_zh=silent),
        SkillOffOut(
            skill_id=FANG,
            conditions=("all_strikes_hit",),
            whole=False,
            reason_zh=OFF_REASON_ZH["all_strikes_hit"],
            effects=(1,),
        ),
    )


def test_weapon_and_lone_wolf_are_listed_together_per_skill() -> None:
    """帶隊友＋拿劍：獨狼與武器條件各自列在自己的技能上；同一招不會重複。"""
    found = skills_off(_state("one_handed_sword", (STEP, POUNCE), allies=1), U1)
    assert found is not None
    assert [(s.skill_id, s.conditions) for s in found] == [
        (POUNCE, ("lone_wolf",)),
        (STEP, ("silent_strike",)),
    ]
