"""基本動作（Phase 3-21a，玩法 #24）：守護、換位、瞄準，以及速度 0 不能跑步。"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from trpg.api.presenter import run_option_out
from trpg.engine import (
    Aim,
    Attack,
    BattleState,
    Defend,
    EndTurn,
    Run,
    Swap,
    UseSkill,
    legal_actions,
    resolve,
)
from trpg.engine.ai.basics import aim_bonus
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.effects import ApplyStatusEffect, run_effects
from trpg.engine.events import (
    AttackIntercepted,
    AttackRolled,
    DamageDealt,
    GuardSet,
    UnitAimed,
    UnitMoved,
)
from trpg.engine.preview import preview
from trpg.engine.rules.statuses import move_points_for_turn
from trpg.engine.runner import replay, run_battle
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId


def _scene(*, foe_skills: tuple[str, ...] = (), foe_xy: tuple[int, int] = (5, 3)) -> BattleState:
    """U1（我方戰士，守護者）(3,3)、U2（我方戰士，被守護）(4,3)、U3（敵人）``foe_xy``；輪到 U1。"""
    m = make_map(FLAT7, ally=[(3, 3), (4, 3)], enemy=[foe_xy])
    foe = no_reactions("bandit", max_hp=999, skills=list(foe_skills))
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter", max_hp=999)),
            spawn(Team.ALLY, (4, 3), no_reactions("hero_fighter", max_hp=999)),
            spawn(Team.ENEMY, foe_xy, foe),
        ],
    )
    return give_turn(state, U1)


def _guarding(*, foe_skills: tuple[str, ...] = ()) -> BattleState:
    state = resolve(_scene(foe_skills=foe_skills), Defend(unit_id=U1, target_id=U2)).state
    return give_turn(state, U3)


def _move_unit(state: BattleState, unit_id: UnitId, xy: tuple[int, int]) -> BattleState:
    out = state.clone()
    out.units[unit_id].pos = Pos(x=xy[0], y=xy[1])
    return out


# ---- 守護 -------------------------------------------------------------------


def test_guard_sets_the_ally_and_costs_one_ap() -> None:
    state = _scene()
    result = resolve(state, Defend(unit_id=U1, target_id=U2))
    unit = result.state.units[U1]
    assert unit.guarding_id == U2 and unit.ap == state.units[U1].ap - 1
    assert unit.has_status("defending")
    (event,) = of(result, GuardSet)
    assert (event.unit_id, event.ally_id) == (U1, U2)


def test_guard_self_has_no_ally() -> None:
    result = resolve(_scene(), Defend(unit_id=U1))
    assert result.state.units[U1].guarding_id is None and not of(result, GuardSet)
    assert result.state.units[U1].has_status("defending")


def test_a_single_target_attack_on_the_guarded_ally_is_taken_by_the_guardian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = _guarding()
    result = resolve(state, Attack(unit_id=U3, target_id=U2))
    (hit,) = of(result, AttackIntercepted)
    assert (hit.guardian_id, hit.attacker_id, hit.target_id, hit.guard) == (U1, U3, U2, True)
    (dmg,) = of(result, DamageDealt)
    assert dmg.target_id == U1
    assert result.state.units[U2].hp == state.units[U2].hp
    assert len(of(result, AttackRolled)) == 1  # 不重擲命中
    assert result.state.units[U1].guard_transfers == 1
    assert result.state.units[U1].reactions_used == 0  # 守護不花反應


def test_a_single_target_skill_is_also_taken_by_the_guardian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = _guarding(foe_skills=("skill_shield_bash",))
    state.units[U3].mana = 99
    result = resolve(state, UseSkill(unit_id=U3, skill_id="skill_shield_bash", target_id=U2))
    (hit,) = of(result, AttackIntercepted)
    assert hit.guard and hit.guardian_id == U1 and hit.skill_id == "skill_shield_bash"
    assert result.state.units[U2].hp == state.units[U2].hp


def test_area_skills_are_not_transferred(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _guarding(foe_skills=("skill_cleave",))
    state.units[U3].mana = 99
    result = resolve(state, UseSkill(unit_id=U3, skill_id="skill_cleave", direction="west"))
    assert of(result, DamageDealt) and not of(result, AttackIntercepted)
    assert result.state.units[U2].hp < state.units[U2].hp


def test_only_one_transfer_per_round(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _guarding()
    first = resolve(state, Attack(unit_id=U3, target_id=U2)).state
    assert first.units[U1].guard_transfers == 1
    again = resolve(give_turn(first, U3), Attack(unit_id=U3, target_id=U2))  # 同一輪第二次
    assert not of(again, AttackIntercepted)
    assert again.state.units[U2].hp < first.units[U2].hp


def test_transfer_count_comes_from_core_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _scene().clone()
    state.ruleset = state.ruleset.model_copy(
        update={"core": state.ruleset.core.model_copy(update={"guard_transfers_per_round": 2})}
    )
    state = give_turn(resolve(state, Defend(unit_id=U1, target_id=U2)).state, U3)
    for _ in range(2):
        state = give_turn(resolve(state, Attack(unit_id=U3, target_id=U2)).state, U3)
    assert state.units[U1].guard_transfers == 2


def test_the_transfer_count_resets_every_round(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = resolve(_guarding(), Attack(unit_id=U3, target_id=U2)).state
    assert state.units[U1].guard_transfers == 1
    start_round = state.round
    for _ in range(6):
        if state.round > start_round:
            break
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    assert state.round == start_round + 1
    assert state.units[U1].guard_transfers == 0


def test_no_transfer_when_the_guardian_is_no_longer_adjacent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = _move_unit(_guarding(), U1, (1, 3))  # 被推開了
    result = resolve(state, Attack(unit_id=U3, target_id=U2))
    assert not of(result, AttackIntercepted)
    assert result.state.units[U2].hp < state.units[U2].hp


def test_guarding_yourself_never_transfers(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = give_turn(resolve(_scene(), Defend(unit_id=U1)).state, U3)
    assert not of(resolve(state, Attack(unit_id=U3, target_id=U2)), AttackIntercepted)


def test_the_guard_ends_when_the_guardians_next_turn_starts() -> None:
    state = _guarding()
    assert state.units[U1].guarding_id == U2
    for _ in range(6):
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
        if state.active_unit == U1:
            break
    assert state.active_unit == U1
    assert state.units[U1].guarding_id is None
    assert not state.units[U1].has_status("defending")


def test_guard_legal_actions_list_every_adjacent_ally() -> None:
    guards = [a for a in legal_actions(_scene()) if isinstance(a, Defend)]
    assert {a.target_id for a in guards} == {None, U2}


def test_illegal_guards_have_chinese_reasons() -> None:
    state = _scene()
    with pytest.raises(IllegalActionError, match="不在相鄰格"):
        resolve(_move_unit(state, U2, (6, 3)), Defend(unit_id=U1, target_id=U2))
    with pytest.raises(IllegalActionError, match="不是隊友"):
        resolve(state, Defend(unit_id=U1, target_id=U3))
    with pytest.raises(IllegalActionError, match="不能指定自己"):
        resolve(state, Defend(unit_id=U1, target_id=U1))
    guarded = resolve(state, Defend(unit_id=U1, target_id=U2)).state
    with pytest.raises(IllegalActionError, match="已處於守護姿態"):
        resolve(guarded, Defend(unit_id=U1, target_id=U2))
    state.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(state, Defend(unit_id=U1))


# ---- 換位 -------------------------------------------------------------------


def test_swap_exchanges_positions_keeps_facing_and_costs_one_ap() -> None:
    state = _scene()
    a, b = state.units[U1], state.units[U2]
    result = resolve(state, Swap(unit_id=U1, target_id=U2))
    out_a, out_b = result.state.units[U1], result.state.units[U2]
    assert (out_a.pos, out_b.pos) == (b.pos, a.pos)
    assert (out_a.facing, out_b.facing) == (a.facing, b.facing)
    assert out_a.ap == a.ap - 1
    moves = of(result, UnitMoved)
    assert {m.mode for m in moves} == {"swap"} and len(moves) == 2


def test_swap_does_not_provoke_opportunity_attacks(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    m = make_map(FLAT7, ally=[(3, 3), (4, 3)], enemy=[(3, 4)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter")),
                spawn(Team.ALLY, (4, 3), no_reactions("hero_fighter")),
                spawn(Team.ENEMY, (3, 4), "bandit"),  # 與 U1 相鄰：走開會吃藉機攻擊
            ],
        ),
        U1,
    )
    result = resolve(state, Swap(unit_id=U1, target_id=U2))
    assert not of(result, AttackRolled) and not of(result, DamageDealt)


def test_swap_works_with_summons() -> None:
    state = _scene()
    state.units[U2].owner_id = U1  # 召喚物
    assert any(isinstance(a, Swap) and a.target_id == U2 for a in legal_actions(state))


def test_swap_is_listed_only_for_adjacent_allies() -> None:
    state = _scene()
    assert [a for a in legal_actions(state) if isinstance(a, Swap)] == [
        Swap(unit_id=U1, target_id=U2)
    ]
    far = _move_unit(state, U2, (6, 6))
    assert not any(isinstance(a, Swap) for a in legal_actions(far))


def _rooted(state: BattleState, unit_id: UnitId) -> BattleState:
    out = run_effects(
        state, [ApplyStatusEffect(target_id=unit_id, status_id="root", duration=3)]
    ).state
    unit = out.units[unit_id]
    unit.move_points = move_points_for_turn(out.ruleset, unit)
    return out


@pytest.mark.parametrize("rooted", [U1, U2])
def test_swap_is_illegal_when_either_side_is_rooted(rooted: UnitId) -> None:
    state = _rooted(_scene(), rooted)
    assert not any(isinstance(a, Swap) for a in legal_actions(state))
    with pytest.raises(IllegalActionError, match="被定身，不能換位"):
        resolve(state, Swap(unit_id=U1, target_id=U2))


def test_swap_other_illegal_cases() -> None:
    state = _scene()
    immobile = state.clone()
    immobile.units[U2].speed = 0
    with pytest.raises(IllegalActionError, match="不能移動"):
        resolve(immobile, Swap(unit_id=U1, target_id=U2))
    with pytest.raises(IllegalActionError, match="不是隊友"):
        resolve(state, Swap(unit_id=U1, target_id=U3))
    with pytest.raises(IllegalActionError, match="不在相鄰格"):
        resolve(_move_unit(state, U2, (6, 6)), Swap(unit_id=U1, target_id=U2))
    state.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(state, Swap(unit_id=U1, target_id=U2))


# ---- 瞄準 -------------------------------------------------------------------


def _aim_ready() -> BattleState:
    """U1 在 (3,4)，敵人 U3 在 (4,4)（相鄰）。"""
    state = _scene(foe_xy=(4, 4))
    return give_turn(_move_unit(state, U1, (3, 4)), U1)


def _rolled(result: object) -> AttackRolled:
    (rolled,) = of(result, AttackRolled)  # type: ignore[arg-type]
    return rolled


def test_aim_adds_hit_bonus_to_the_next_attack_only(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = _aim_ready()
    base = _rolled(resolve(state, Attack(unit_id=U1, target_id=U3))).total
    aimed = resolve(state, Aim(unit_id=U1))
    unit = aimed.state.units[U1]
    assert unit.aimed and unit.ap == state.units[U1].ap - 1
    (event,) = of(aimed, UnitAimed)
    assert (event.unit_id, event.bonus) == (U1, 2)
    first = resolve(aimed.state, Attack(unit_id=U1, target_id=U3))
    assert _rolled(first).total == base + 2 and _rolled(first).modifier_bonus == 2
    assert not first.state.units[U1].aimed  # 用掉
    second = resolve(first.state, Attack(unit_id=U1, target_id=U3))
    assert _rolled(second).total == base  # 不再有加值


def test_aim_does_not_stack() -> None:
    aimed = resolve(_aim_ready(), Aim(unit_id=U1)).state
    assert not any(isinstance(a, Aim) for a in legal_actions(aimed))
    with pytest.raises(IllegalActionError, match="已經瞄準了"):
        resolve(aimed, Aim(unit_id=U1))


def test_aim_is_only_offered_with_ap_left_and_a_target() -> None:
    state = _aim_ready()
    assert any(isinstance(a, Aim) for a in legal_actions(state))
    state.units[U1].ap = 1  # 瞄準後就沒有 AP 可以攻擊了
    assert not any(isinstance(a, Aim) for a in legal_actions(state))
    state.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(state, Aim(unit_id=U1))


def test_aim_expires_at_the_end_of_the_turn() -> None:
    state = resolve(_aim_ready(), Aim(unit_id=U1)).state
    state = resolve(state, EndTurn(unit_id=U1)).state
    assert not state.units[U1].aimed


def test_aim_applies_to_a_skill_cast_and_is_used_up(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    hero = caster_template(["skill_shield_bash"], base="hero_fighter")
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (3, 3), hero), spawn(Team.ENEMY, (4, 3), no_reactions())]),
        U1,
    )
    state.units[U1].mana = 99
    cast = UseSkill(unit_id=U1, skill_id="skill_shield_bash", target_id=U2)
    base = _rolled(resolve(state, cast)).total
    aimed = resolve(state, Aim(unit_id=U1)).state
    result = resolve(aimed, cast)
    assert _rolled(result).total == base + 2
    assert not result.state.units[U1].aimed


def test_aim_bonus_comes_from_core_rules() -> None:
    state = _aim_ready().clone()
    state.ruleset = state.ruleset.model_copy(
        update={"core": state.ruleset.core.model_copy(update={"aim_hit_bonus": 5})}
    )
    (event,) = of(resolve(state, Aim(unit_id=U1)), UnitAimed)
    assert event.bonus == 5


# ---- 跑步遺留：速度 0 -------------------------------------------------------


def test_speed_zero_unit_cannot_run() -> None:
    state = _scene()
    state.units[U1].speed = 0
    assert not any(isinstance(a, Run) for a in legal_actions(state))
    with pytest.raises(IllegalActionError, match="速度為 0，不能跑"):
        resolve(state, Run(unit_id=U1))
    option = run_option_out(state, U1)
    assert not option.legal and option.reason == "速度為 0，不能跑"


# ---- AI ---------------------------------------------------------------------


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def _ai_scene(
    *, ally_hp: int, ally_xy: tuple[int, int] = (4, 3), foe_xy: tuple[int, int] = (6, 3)
) -> BattleState:
    state = _move_unit(_scene(foe_xy=foe_xy), U2, ally_xy)
    state.units[U2].hp = ally_hp
    state.units[U1].move_points = 0  # 不靠走位決定
    state.units[U1].ran_this_turn = True  # 也不跑步
    return state


def test_ai_guards_a_weak_adjacent_ally_under_threat() -> None:
    assert _ai()(_ai_scene(ally_hp=100, ally_xy=(2, 3), foe_xy=(5, 3))) == Defend(
        unit_id=U1, target_id=U2
    )


def test_ai_guards_itself_when_the_ally_is_healthy_or_out_of_threat() -> None:
    for state in (_ai_scene(ally_hp=999), _ai_scene(ally_hp=100, foe_xy=(0, 6))):
        action = _ai()(state)
        assert not (isinstance(action, Defend) and action.target_id is not None)


def test_ai_swaps_a_weak_front_ally_to_the_back() -> None:
    # U2 在前（離敵人 U3 較近）且血量低、敵人逼近：換位把他換離前線
    state = _ai_scene(ally_hp=100, ally_xy=(4, 3), foe_xy=(6, 3))
    state.units[U1].ap = 1  # 只剩 1 AP 時守護與換位都夠，換位分數較高
    assert _ai()(state) == Swap(unit_id=U1, target_id=U2)


def test_ai_swaps_a_tank_to_the_front() -> None:
    state = _ai_scene(ally_hp=999, ally_xy=(4, 3), foe_xy=(6, 3))
    state.units[U1].max_hp = state.units[U1].hp = 999
    state.units[U2].max_hp = state.units[U2].hp = 100  # 自己的最大 HP 遠高於隊友
    state.units[U1].ap = 1
    assert _ai()(state) == Swap(unit_id=U1, target_id=U2)


def test_ai_does_not_swap_without_a_reason() -> None:
    same = _ai_scene(ally_hp=999)  # 同樣肉、都健康
    assert not isinstance(_ai()(same), Swap)
    behind = _ai_scene(ally_hp=100, ally_xy=(2, 3), foe_xy=(6, 3))  # 隊友在後面
    assert not isinstance(_ai()(behind), Swap)


def test_ai_aims_before_a_costly_low_chance_attack() -> None:
    state = _aim_ready()
    state.units[U1].ap = 3
    attack = Attack(unit_id=U1, target_id=U3)
    p = preview(state, attack)
    assert p.ap_cost == 1
    # 普攻只花 1 AP（低於 aim_min_attack_ap）：不瞄準
    rules = library().ai_profiles.basic
    assert aim_bonus(state, state.units[U1], [(Fraction(5), p)], rules) == 0


def test_ai_basic_actions_replay_in_battle() -> None:
    m = make_map(FLAT7, ally=[(1, 3), (1, 4)], enemy=[(5, 3), (5, 4)])
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, (1, 3), "hero_fighter"),
            spawn(Team.ALLY, (1, 4), "hero_mage"),
            spawn(Team.ENEMY, (5, 3), no_reactions()),
            spawn(Team.ENEMY, (5, 4), no_reactions()),
        ],
    )
    result = run_battle(setup, 3, policy=_ai())
    assert replay(setup, 3, result.actions).events == result.events


def test_aim_bonus_scoring_conditions() -> None:
    state = _aim_ready()
    unit = state.units[U1]
    rules = library().ai_profiles.basic
    base = preview(state, Attack(unit_id=U1, target_id=U3))
    costly_low = replace(base, ap_cost=2, hit_chance=Fraction(2, 5))
    unit.ap = 3  # 剛好 = 瞄準 1 + 攻擊 2
    assert aim_bonus(state, unit, [(Fraction(7), costly_low)], rules) == 7 + rules.aim_points
    unit.ap = 4  # AP 有剩：不瞄準
    assert aim_bonus(state, unit, [(Fraction(7), costly_low)], rules) == 0
    unit.ap = 3
    high = replace(costly_low, hit_chance=Fraction(9, 10))  # 命中率高：不瞄準
    assert aim_bonus(state, unit, [(Fraction(7), high)], rules) == 0
    assert aim_bonus(state, unit, [(Fraction(0), costly_low)], rules) == 0  # 沒有收益
