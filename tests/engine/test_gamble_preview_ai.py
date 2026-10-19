"""賭博型技能的預覽與 AI（Phase 3D-7a，``docs/phases/Phase3D計畫.md`` 7.0、7.3）：預覽列出兩個分支
的機率與結果、AI 以期望值評分、低血量不亂賭。"""

from __future__ import annotations

from fractions import Fraction

import pytest

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
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, battle
from tests.engine.test_gamble import DOUBLE, FIRE, SINGLE5, gamble_skill, miss_skill
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, UseSkill, preview, resolve, state_to_json
from trpg.engine.ai.gamble import can_hurt_caster
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.shared.types import Team

# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def test_the_preview_lists_both_branches_with_chance_and_results() -> None:
    state = battle(gamble_skill(), [(5, 3)])
    p = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert p.gamble is not None and p.gamble.chance_permille == 600
    win, lose = p.gamble.branches
    assert (win.kind, win.chance) == ("win", Fraction(3, 5))
    assert (lose.kind, lose.chance) == ("lose", Fraction(2, 5))
    assert win.multiplier_permille == 2000 and lose.multiplier_permille == 1000
    assert win.self_damage == (0, 0)
    assert lose.self_damage[0] > 0 and lose.self_damage[1] >= lose.self_damage[0]
    win_hit = win.preview.targets[0].damage
    lose_hit = lose.preview.targets[0].damage
    assert win_hit is not None and lose_hit is not None
    assert win_hit.maximum > lose_hit.maximum  # 成功的分支傷害較高
    assert Fraction(1) == win.chance + lose.chance


def test_the_preview_does_not_consume_randomness_or_change_the_state() -> None:
    state = battle(gamble_skill(), [(5, 3)])
    before = state_to_json(state)
    preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert state_to_json(state) == before


def test_a_skill_without_a_gamble_has_no_gamble_preview() -> None:
    state = battle(make_skill(SID, SINGLE5, [FIRE]), [(5, 3)])
    assert preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).gamble is None


def test_the_preview_describes_the_miss_backlash() -> None:
    state = battle(miss_skill(), [(5, 3)])
    p = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert p.miss_notes == ("失手時：你獲得「倒地」",)


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles, override="brute")


def test_the_ai_scores_a_gamble_with_the_expected_value_of_its_branches() -> None:
    state = battle(gamble_skill(), [(5, 3)])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    p = preview(state, action)
    assert p.gamble is not None
    profile = _ai().profile_for(state.units[U1])
    scores = [score_action(state, action, profile)]
    win, lose = p.gamble.branches
    # 兩個分支各自評分後依機率加權：期望分數介於成功與失敗分支的分數之間
    assert scores[0].score > 0
    assert win.preview.targets[0].damage is not None and lose.preview.targets[0].damage is not None


def test_a_low_hp_caster_does_not_pick_a_gamble_that_can_hurt_it() -> None:
    plain = make_skill(
        "skill_t_plain", SINGLE5, [{"type": "damage", "dice": "1d4", "element": "fire"}]
    )
    risky = gamble_skill()
    healthy = battle(risky, [(5, 3)])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    profile = _ai().profile_for(healthy.units[U1])
    normal = score_action(healthy, action, profile).score
    assert normal > 0
    hurt = healthy.clone()
    unit = hurt.units[U1]
    unit.hp = unit.max_hp * 25 // 100  # 低於 300‰
    low = score_action(hurt, action, profile).score
    assert 0 < low < normal * Fraction(1, 5)
    assert can_hurt_caster(risky) and not can_hurt_caster(plain)


def test_the_low_hp_penalty_only_applies_to_gambles_that_can_hurt() -> None:
    """賭注的失敗分支只有狀態或治療（沒有自傷）時，低血量不受影響。"""
    safe = gamble_skill(
        win=[DOUBLE], lose=[{"type": "apply_status", "status": "slow", "affects": "self"}]
    )
    assert not can_hurt_caster(safe)
    state = battle(safe, [(5, 3)])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    profile = _ai().profile_for(state.units[U1])
    normal = score_action(state, action, profile).score
    hurt = state.clone()
    hurt.units[U1].hp = 1
    assert score_action(hurt, action, profile).score == normal


def test_the_miss_backlash_lowers_the_ai_score() -> None:
    cheap = make_skill(SID, SINGLE5, [FIRE])
    costly = miss_skill()
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    state_a = battle(cheap, [(5, 3)])
    state_b = battle(costly, [(5, 3)])
    profile = _ai().profile_for(state_a.units[U1])
    assert (
        score_action(state_b, action, profile).score <= score_action(state_a, action, profile).score
    )


def test_resolving_an_ai_chosen_gamble_replays(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(gamble_skill(), [(5, 3)])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    first, second = resolve(state, action), resolve(state, action)
    assert state_to_json(first.state) == state_to_json(second.state)


def _two_skill_state(risky: SkillDef, safe: SkillDef) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(5, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([risky, safe])),
        spawn(Team.ENEMY, (5, 3), no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[risky, safe]), U1)


def test_the_ai_gambles_when_healthy_but_picks_the_safe_skill_when_nearly_dead() -> None:
    risky = gamble_skill()
    safe = make_skill(
        "skill_t_safe", SINGLE5, [{"type": "damage", "dice": "2d6", "element": "fire"}]
    )
    state = _two_skill_state(risky, safe)
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == SID  # 期望值較高的賭注
    state.units[U1].hp = state.units[U1].max_hp * 20 // 100  # 低於 300‰
    action = _ai()(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_t_safe"
