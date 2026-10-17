"""效用 AI 的最低限度技能支援（docs/phases/Phase2A計畫.md 5.3）。"""

from __future__ import annotations

from collections.abc import Sequence

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill
from trpg.engine.ai.utility import SKILL_CANDIDATES, UtilityAI, score_action
from trpg.shared.types import Pos, Team


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles, override="brute")


def _state(
    skills: list[str],
    foes: list[tuple[int, int]],
    *,
    base: str = "hero_mage",
    allies: list[tuple[int, int]] | None = None,
    caster: tuple[int, int] = (1, 3),
    extra: Sequence[SkillDef] = (),
) -> BattleState:
    allies = allies or []
    m = make_map(FLAT7, ally=[caster, *allies], enemy=foes)
    spawns = [spawn(Team.ALLY, caster, caster_template(skills, base=base))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns, skills=list(extra)), U1)


def test_the_ai_casts_a_damaging_skill_at_an_enemy_in_range() -> None:
    state = _state(["skill_fire_bolt"], [(4, 3)])
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_fire_bolt"
    assert action.target_id == U2


def test_selections_without_any_enemy_object_or_hurt_ally_are_not_candidates() -> None:
    state = _state(["skill_ashen_oath", "skill_sanctuary"], [(6, 6)], base="hero_stormcaller")
    state.units[U1].skills = ("skill_ashen_oath", "skill_sanctuary")
    ranked = _ai().rank(state)
    assert not [s for s in ranked if isinstance(s.action, UseSkill)]  # 範圍內沒有人，也沒有傷者


def test_a_healing_skill_is_only_considered_when_an_ally_is_hurt() -> None:
    state = _state(["skill_sanctuary"], [(6, 6)], base="hero_stormcaller", allies=[(2, 3)])
    assert not [s for s in _ai().rank(state) if isinstance(s.action, UseSkill)]
    state.units[U2].hp = 5
    ranked = [s for s in _ai().rank(state) if isinstance(s.action, UseSkill)]
    assert len(ranked) == 1 and ranked[0].score > 0
    assert isinstance(_ai()(state), UseSkill)


def test_friendly_fire_lowers_the_score_of_an_all_affecting_skill() -> None:
    skill = make_skill(
        SID,
        {"type": "square3", "range": 5},
        [{"type": "damage", "dice": "2d6", "element": "fire", "affects": "all"}],
    )
    alone = _state([SID], [(4, 3)], extra=[skill])
    crowded = _state([SID], [(4, 3)], allies=[(4, 4)], extra=[skill])
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=4, y=3))
    profile = _ai().profile_for(alone.units[U1])
    score_alone = score_action(alone, action, profile).score
    score_crowded = score_action(crowded, action, profile).score
    assert score_crowded < score_alone


def test_each_skill_keeps_only_its_best_few_selections() -> None:
    skill = make_skill(
        SID, {"type": "ground_tile", "range": 4}, [{"type": "create_surface", "surface": "oil"}]
    )
    state = _state([SID], [(4, 3)], extra=[skill])
    listed = [a for a in _ai().rank(state) if isinstance(a.action, UseSkill)]
    assert len(listed) <= SKILL_CANDIDATES
