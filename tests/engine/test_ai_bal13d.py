"""BAL-13d：弱 build 的 AI 修正（seer 的行為模式、狂怒姿態的進入與取消、孤注一擲的低血量、
捨身突刺的自身易傷估值）。"""

from __future__ import annotations

from fractions import Fraction

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import U1, U2
from trpg.engine import BattleState, EndStance, UseSkill, resolve
from trpg.engine.ai.gamble import cautious
from trpg.engine.ai.stance import stance_cancel, stance_entry_blocked
from trpg.engine.ai.utility import UtilityAI, skill_cost
from trpg.shared.types import Pos, Team

FURY, BULWARK = "skill_fury_stance", "skill_bulwark_stance"
ROW = "\n".join(["0" * 20] * 3)


def scene(enemy_x: int, *, hp: int = 100, skills: tuple[str, ...] = (FURY,)) -> BattleState:
    """U1（戰士）在 (0, 1) 手上有回合；U2（敵人）在 (enemy_x, 1)。"""
    m = make_map(ROW, ally=[(0, 1)], enemy=[(enemy_x, 1)])
    owner = caster_template(list(skills), base="hero_fighter", max_hp=100)
    state = make_state(
        m,
        [spawn(Team.ALLY, (0, 1), owner), spawn(Team.ENEMY, (enemy_x, 1), no_reactions())],
    )
    state = give_turn(state, U1)
    state.units[U1].hp = hp
    return state


def test_the_seer_profile_only_overrides_the_two_rewrite_fields() -> None:
    profiles = library().ai_profiles.by_id()
    seer, cunning = profiles["seer"], profiles["cunning"]
    assert (seer.rewrite.mana_points, seer.rewrite.cooldown_points) == (0, 1)
    others = {"mana_points", "cooldown_points"}
    assert seer.rewrite.model_dump(exclude=others) == cunning.rewrite.model_dump(exclude=others)
    assert seer.weights == cunning.weights
    assert library().builds.by_id()["build_seer"].hero.ai_profile == "seer"


def test_fury_is_only_entered_when_an_enemy_is_within_two_turns_reach() -> None:
    near = scene(5)
    unit = near.units[U1]
    reach = 2 * unit.speed + unit.weapon.range
    fury = near.ruleset.skill_def(FURY)
    stance = library().ai_profiles.by_id()["brute"].stance
    assert not stance_entry_blocked(scene(reach), scene(reach).units[U1], fury, stance)
    far = scene(reach + 1)
    assert stance_entry_blocked(far, far.units[U1], fury, stance)
    picks = {s.action for s in UtilityAI(library().ai_profiles).rank(far)}
    assert UseSkill(unit_id=U1, skill_id=FURY) not in picks


def test_a_stance_without_a_cost_is_not_gated() -> None:
    far = scene(19, skills=(BULWARK,))
    bulwark = far.ruleset.skill_def(BULWARK)
    stance = library().ai_profiles.by_id()["brute"].stance
    assert not stance_entry_blocked(far, far.units[U1], bulwark, stance)


def test_fury_is_cancelled_at_low_hp_with_an_enemy_nearby() -> None:
    stance = library().ai_profiles.by_id()["brute"].stance
    entered = resolve(scene(3), UseSkill(unit_id=U1, skill_id=FURY)).state
    assert stance_cancel(entered, entered.units[U1], stance) is None  # 滿血不取消
    low = entered.clone()
    low.units[U1].hp = 39
    assert stance_cancel(low, low.units[U1], stance) == EndStance(unit_id=U1)
    assert UtilityAI(library().ai_profiles)(low) == EndStance(unit_id=U1)
    assert stance_entry_blocked(low, low.units[U1], low.ruleset.skill_def(FURY), stance)
    alone = low.clone()
    alone.units[U2].pos = Pos(x=19, y=1)  # 附近沒有敵人：不取消
    assert stance_cancel(alone, alone.units[U1], stance) is None


def test_all_in_is_cautious_below_thirty_percent_hp() -> None:
    state = scene(1, hp=29)
    profile = library().ai_profiles.by_id()["brute"]
    all_in = state.ruleset.skill_def("skill_all_in")
    score = Fraction(50)
    low = profile.gamble.low_hp_permille
    assert cautious(state, state.units[U1], all_in, score, profile) == score * low / 1000
    state.units[U1].hp = 30
    assert cautious(state, state.units[U1], all_in, score, profile) == score


def test_the_reckless_lunge_self_vulnerable_cost_uses_the_self_value() -> None:
    state = scene(1, skills=("skill_reckless_lunge",))
    profile = library().ai_profiles.by_id()["brute"]
    values = {**profile.status_values, **profile.self_status_values}
    action = UseSkill(unit_id=U1, skill_id="skill_reckless_lunge", target_id=U2)
    skill = state.ruleset.skill_def("skill_reckless_lunge")
    w = profile.weights
    paid = skill_cost(state, state.units[U1], action, w, values)
    without = skill_cost(state, state.units[U1], action, w, {})
    assert skill.cost.self_status is not None
    turns = skill.cost.self_status.duration - 1
    vulnerable = profile.self_status_values["vulnerable"]
    assert paid == without - w.status * turns + w.damage * vulnerable * turns
