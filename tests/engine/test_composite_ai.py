"""Phase 3F-3b：AI 使用複合技能（落點 × 動作目標的評估與上限）。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.test_composite_skills import CONE, CROSS, SID, arena, combo
from trpg.engine import UseSkill, legal_actions
from trpg.engine.ai.utility import UtilityAI


def ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def test_the_ai_teleports_next_to_distant_foes_and_cuts_them() -> None:
    state = arena(combo("teleport", CONE), caster=(0, 3), foes=[(5, 3), (5, 2)])
    action = ai()(state)
    assert isinstance(action, UseSkill)
    assert action.skill_id == SID
    assert action.followup_target is not None
    assert action.followup_target.direction == "east"


def test_the_ai_uses_a_centered_followup_around_the_landing() -> None:
    state = arena(combo("leap", CROSS), caster=(0, 3), foes=[(4, 3), (3, 2)])
    action = ai()(state)
    assert isinstance(action, UseSkill)
    assert action.skill_id == SID


def test_the_number_of_previewed_composite_candidates_is_capped() -> None:
    state = arena(combo("teleport", CONE), caster=(0, 3), foes=[(3, 3), (5, 5)])
    listed = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]
    assert len(listed) > ai().skill_candidates  # 組合比上限多
    ranked = [s for s in ai().rank(state) if isinstance(s.action, UseSkill)]
    assert 0 < len(ranked) <= ai().skill_candidates


def test_the_ai_ignores_composites_when_no_foe_would_be_hit() -> None:
    state = arena(combo("teleport", CONE), caster=(0, 3), foes=[(6, 6)])
    ranked = [s for s in ai().rank(state) if isinstance(s.action, UseSkill)]
    assert ranked == []
