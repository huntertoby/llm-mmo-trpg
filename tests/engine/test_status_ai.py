"""Phase 2B-1 3.5／3.7 第 7 條：效用 AI 面對新狀態的情境。"""

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
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.engine import Attack, Defend, EndTurn, Move, UseSkill, legal_actions
from trpg.engine.ai.utility import ActionScore, UtilityAI
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Team


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _melee_vs_hero(*, rooted: bool, distance: int = 3, foe: str = "bandit") -> BattleState:
    """U1 是我方戰士 (1, 3)，U2 是敵方近戰單位；輪到 U2。"""
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(1 + distance, 3)])
    hero = no_reactions("hero_fighter")
    spawns = [
        spawn(Team.ALLY, (1, 3), hero),
        spawn(Team.ENEMY, (1 + distance, 3), template(foe, reactions=[])),
    ]
    state = give_turn(make_state(m, spawns), U2)
    if rooted:
        unit = state.units[U2]
        unit.statuses = [StatusInstance(status_id="root", remaining=1)]
    return state


# ---------------------------------------------------------------------------
# 被定身、緩速的單位能正常選動作
# ---------------------------------------------------------------------------


def test_a_free_melee_unit_closes_the_distance() -> None:
    """對照組：沒有定身時，遠處的近戰單位會走過去。"""
    assert isinstance(_ai()(_melee_vs_hero(rooted=False)), Move)


def test_a_rooted_melee_unit_never_tries_to_move() -> None:
    state = _melee_vs_hero(rooted=True)
    assert not [a for a in legal_actions(state) if isinstance(a, Move)]
    ranked = _ai().rank(state)
    assert not [s for s in ranked if isinstance(s.action, Move)]
    action = _ai()(state)
    assert isinstance(action, Defend | EndTurn)  # 打不到人、也走不了：防禦或結束回合


def test_a_rooted_melee_unit_uses_a_skill_when_something_is_in_reach() -> None:
    """定身的盜賊頭目（橫掃劈砍）旁邊有英雄時，改用攻擊或技能而不是移動。"""
    state = _melee_vs_hero(rooted=True, distance=1, foe="bandit_boss")
    action = _ai()(state)
    assert isinstance(action, Attack | UseSkill)
    assert action.unit_id == U2


def test_a_rooted_ranged_unit_still_shoots() -> None:
    state = _melee_vs_hero(rooted=True, distance=4, foe="bandit_archer")
    assert isinstance(_ai()(state), Attack | UseSkill)


def test_a_slowed_unit_still_picks_an_action() -> None:
    state = _melee_vs_hero(rooted=False)
    state.units[U2].statuses = [StatusInstance(status_id="slow", remaining=2)]
    state.units[U2].move_points = 2
    action = _ai()(state)
    assert isinstance(action, Move)
    assert len(action.path) - 1 <= 2  # 只用得到 2 點移動


# ---------------------------------------------------------------------------
# 法師在敵方近戰逼近時使用寒鎖
# ---------------------------------------------------------------------------


def _mage_scene(
    *, status: str | None = None, skills: tuple[str, ...] = ("skill_frost_shackle",)
) -> BattleState:
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(5, 3)])
    mage = caster_template(list(skills), base="hero_mage")
    spawns = [spawn(Team.ALLY, (1, 3), mage), spawn(Team.ENEMY, (5, 3), no_reactions("bandit"))]
    state = give_turn(make_state(m, spawns), U1)
    if status is not None:
        state.units[U2].statuses = [StatusInstance(status_id=status, remaining=1)]
    return state


def test_the_mage_roots_an_approaching_melee_enemy() -> None:
    action = _ai()(_mage_scene())
    assert isinstance(action, UseSkill) and action.skill_id == "skill_frost_shackle"
    assert action.target_id == U2


def test_the_mage_with_a_damage_skill_too_still_chooses_by_score() -> None:
    """有火焰箭可用時，寒鎖仍是被評分的候選（分數比普攻高）。"""
    state = _mage_scene(skills=("skill_fire_bolt", "skill_frost_shackle"))
    ranked = _ai().rank(state)
    skills = {s.action.skill_id for s in ranked if isinstance(s.action, UseSkill)}
    assert skills == {"skill_fire_bolt", "skill_frost_shackle"}
    best = {
        sid: max(
            s.score for s in ranked if isinstance(s.action, UseSkill) and s.action.skill_id == sid
        )
        for sid in skills
    }
    basic = max(s.score for s in ranked if isinstance(s.action, Attack))
    assert best["skill_frost_shackle"] > basic


def test_the_mage_does_not_reroot_an_already_rooted_enemy() -> None:
    fresh = _ai().rank(_mage_scene())
    rooted = _ai().rank(_mage_scene(status="root"))

    def shackle(ranked: list[ActionScore]) -> Fraction:
        return max(
            s.score
            for s in ranked
            if isinstance(s.action, UseSkill) and s.action.skill_id == "skill_frost_shackle"
        )

    assert shackle(rooted) < shackle(fresh)  # 重複施加只是刷新，狀態本身沒有價值


def test_status_values_are_defined_for_every_new_status() -> None:
    values = library().ai_profiles.status_values
    assert set(values) == {
        "stun",
        "root",
        "slow",
        "weaken",
        "vulnerable",
        "bleed",
        "poison",
        "taunted",  # 2D-1
    }
    assert all(v > 0 for v in values.values())
    for profile in library().ai_profiles.profiles:
        assert profile.status_values == values  # 表格層級的價值填入每個行為模式
