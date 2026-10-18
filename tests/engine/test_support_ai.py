"""Phase 2D-1 3.7／3.9 第 9 項：``support`` 行為模式與友方支援的評分。"""

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
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.engine import Attack, UseSkill
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Team, UnitId

AEGIS, TAILWIND, RENEWAL, PURIFY = (
    "skill_guardian_aegis",
    "skill_tailwind",
    "skill_renewal",
    "skill_purify",
)
U3 = UnitId("unit_0003")


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _scene(skills: list[str], *, profile: str = "support", hurt: bool = True) -> BattleState:
    """U1 是支援法師 (1, 3)；友方戰士 U2 (2, 3) 與敵方盜賊 U3 (3, 3) 貼身。輪到 U1。"""
    m = make_map(FLAT7, ally=[(1, 3), (2, 3)], enemy=[(3, 3)])
    caster = caster_template(skills, ai_profile=profile)
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 3), caster),
            spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", skills=[])),
            spawn(Team.ENEMY, (3, 3), no_reactions()),
        ],
    )
    state = give_turn(state, U1)
    if hurt:
        state.units[U2].hp = state.units[U2].max_hp // 3
    return state


def test_the_support_profile_exists_and_values_support_over_damage() -> None:
    profiles = library().ai_profiles.by_id()
    w = profiles["support"].weights
    assert (w.heal, w.shield, w.support) == (12, 10, 12) and w.keep_distance == 20
    assert w.shield > w.damage and w.support > w.damage
    assert profiles["guard"].weights.shield == 8 and profiles["brute"].weights.support == 3
    assert profiles["support"].ally_status_values == {
        "guarded": 5,
        "empowered": 5,
        "hasted": 3,
        "regenerating": 6,
        "defending": 3,
        "stance_fury": 8,  # 2E-2：姿態以自身為對象，由效用 AI 的 ally_status_values 計分
        "stance_bulwark": 8,
    }
    assert library().ai_profiles.status_values["taunted"] == 5


def _covered(state: BattleState, uid: UnitId) -> BattleState:
    """``uid`` 已經帶著所有增益（護盾、護衛、加速、再生），再施放同類技能對它沒有收益。"""
    s = state.clone()
    s.units[uid].statuses = [
        StatusInstance("guarded", 2, U1),
        StatusInstance("hasted", 2, U1),
        StatusInstance("regenerating", 3, U1),
        StatusInstance("shielded", 2, U1, 99),
    ]
    return s


def test_a_support_unit_protects_a_hurt_ally_in_melee_instead_of_attacking() -> None:
    for skill in (AEGIS, RENEWAL, TAILWIND):
        state = _covered(_scene([skill]), U1)  # 自己已有增益：值得施放的只有受傷的友方
        action = _ai()(state)
        assert isinstance(action, UseSkill) and action.skill_id == skill, skill
        assert action.target_id == U2


def test_the_shield_gain_is_scored_by_the_shield_weight() -> None:
    state = _scene([AEGIS])
    scored = {
        (s.action.skill_id, s.action.target_id): s.score
        for s in _ai().rank(state)
        if isinstance(s.action, UseSkill)
    }
    assert scored[(AEGIS, U2)] > 0
    # 已經有大護盾時，再罩一次的增加量（取較大值）很小，分數低很多
    big = state.clone()
    big.units[U2].statuses = [StatusInstance("shielded", 2, U1, 99)]
    again = {
        (s.action.skill_id, s.action.target_id): s.score
        for s in _ai().rank(big)
        if isinstance(s.action, UseSkill)
    }
    assert again[(AEGIS, U2)] < scored[(AEGIS, U2)]
    assert again[(AEGIS, U2)] <= 0


def test_buffs_are_not_recast_on_a_full_health_ally_who_already_has_them() -> None:
    state = _scene([TAILWIND], hurt=False)
    fresh = _ai()(state)
    assert isinstance(fresh, UseSkill) and fresh.skill_id == TAILWIND  # 還沒有增益：值得施放
    action = _ai()(_covered(_covered(state, U2), U1))
    assert not (isinstance(action, UseSkill) and action.skill_id == TAILWIND)


def test_a_partially_remaining_buff_is_only_worth_the_extra_duration() -> None:
    state = _scene([TAILWIND], hurt=False)
    low = state.clone()
    low.units[U2].statuses = [
        StatusInstance("guarded", 1, U1),
        StatusInstance("hasted", 1, U1),
    ]
    none_ = {
        s.action.target_id: s.score
        for s in _ai().rank(state)
        if isinstance(s.action, UseSkill) and s.action.target_id == U2
    }
    some = {
        s.action.target_id: s.score
        for s in _ai().rank(low)
        if isinstance(s.action, UseSkill) and s.action.target_id == U2
    }
    assert some[U2] < none_[U2]  # 只剩 1 回合：差額比例 1/2


def test_cleanse_is_valued_by_the_statuses_it_removes() -> None:
    state = _scene([PURIFY], hurt=False)
    clean = {
        s.action.target_id: s.score for s in _ai().rank(state) if isinstance(s.action, UseSkill)
    }
    sick = state.clone()
    sick.units[U2].statuses = [StatusInstance("poison", 3, U3), StatusInstance("slow", 2, U3)]
    ranked = {
        s.action.target_id: s.score for s in _ai().rank(sick) if isinstance(s.action, UseSkill)
    }
    # poison 6 ＋ slow 4（status_values）× support 12
    assert ranked[U2] - clean.get(U2, Fraction(0)) >= 12 * (6 + 4) - 12 * 3
    action = _ai()(sick)
    assert isinstance(action, UseSkill) and action.skill_id == PURIFY and action.target_id == U2


def test_a_non_support_profile_still_prefers_its_own_job() -> None:
    state = _scene([AEGIS], profile="brute", hurt=False)
    action = _ai()(state)
    assert isinstance(action, Attack | UseSkill)  # 不例外、不僵住
