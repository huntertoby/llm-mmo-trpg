"""Phase 3-50：自己付的代價（暈眩／沉默／流血的自身狀態、透支）的引擎行為（06 6.5）。

涵蓋共通規則 3（自付狀態不觸發控制遞減、不受 Boss 轉換）、規則 6（AI 使用條件）與
「自暈的配套」（仍可被推、拉、傳送；護盾照常存在）。預算與驗證器的規則見
``tests/skillgen/test_self_costs.py``。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from tests.skillgen.helpers import lib
from trpg.engine import EndTurn, UseSkill, resolve
from trpg.engine.ai.self_costs import self_cost_gate
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, MoveUnitEffect
from trpg.engine.events import (
    DamageDealt,
    SkillUsed,
    StatusApplied,
    StatusConverted,
    StatusSaveRolled,
    TurnSkipped,
    TurnStarted,
)
from trpg.engine.preview import preview
from trpg.engine.runner import LOG_FORMAT, replay, run_battle
from trpg.engine.state import BattleState, state_to_json
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team

SINGLE = {"type": "single", "range": 5}
SPELL_DAMAGE = {"type": "damage", "dice": "1d6", "element": "fire"}
SELF = {"type": "self"}
DAMAGE = {"type": "damage", "multiplier_permille": 1000}
SHIELD = {"type": "shield", "dice": "2d6", "affects": "self"}


def _stun_shield(**cost: Any) -> Any:
    return make_skill(
        SID,
        SELF,
        [SHIELD],
        ap_cost=1,
        cost={"mana": 0, "self_status": {"status": "stun", "duration": 2}, **cost},
    )


def _strike(cost: dict[str, Any]) -> Any:
    return make_skill(SID, SINGLE, [DAMAGE], category="weapon", ap_cost=1, cost=cost)


def _pass_turns_until_skipped(state: BattleState) -> list[Any]:
    """所有人輪流結束回合，直到有人的回合被跳過；回傳這段期間的所有事件。"""
    events: list[Any] = []
    for _ in range(8):
        active = state.active_unit
        assert active is not None
        result = resolve(state, EndTurn(unit_id=active))
        state = result.state
        events += result.events
        if any(isinstance(e, TurnSkipped) for e in result.events):
            return events
    raise AssertionError("沒有任何回合被跳過")


# ---------------------------------------------------------------------------
# 自暈：結算
# ---------------------------------------------------------------------------


def test_self_stun_applies_without_a_save_and_empties_the_rest_of_the_turn() -> None:
    state = battle(_stun_shield(), [(6, 6)])
    result = cast(state)
    caster = result.state.units[U1]
    stun = caster.get_status("stun")
    assert stun is not None and stun.remaining == 2 and stun.source_id == U1
    assert not of(result, StatusSaveRolled)  # 不擲抵抗
    assert caster.ap == 0 and caster.move_points == 0  # 暈眩規則：沒有 AP、移動


def test_the_stunned_caster_loses_its_next_turn_only() -> None:
    result = cast(battle(_stun_shield(), [(6, 6)]))
    events = _pass_turns_until_skipped(result.state)
    skipped = [e for e in events if isinstance(e, TurnSkipped)]
    assert [(e.unit_id, e.status_id) for e in skipped] == [(U1, "stun")]
    after = resolve(result.state, EndTurn(unit_id=U1))  # 結束回合：暈眩 2 → 1
    assert after.state.units[U1].get_status("stun") is not None


def test_self_paid_stun_does_not_trigger_control_diminishing() -> None:
    result = cast(battle(_stun_shield(), [(6, 6)]))
    assert result.state.units[U1].control_dr == {}  # 敵人施加的硬控會登記遞減，自付的不會


def test_enemy_applied_stun_still_triggers_control_diminishing() -> None:
    """對照組：同一個狀態由別人施加時照常登記控制遞減（上一個測試不是因為狀態本身沒有遞減）。"""
    state = battle(_stun_shield(), [(6, 6)])
    ctx = Ctx(state)
    execute(ctx, [ApplyStatusEffect(source_id=U2, target_id=U1, status_id="stun", duration=1)])
    assert "hard" in state.units[U1].control_dr


def test_self_paid_stun_is_not_converted_on_a_boss() -> None:
    state = battle(_stun_shield(), [(6, 6)])
    caster = state.units[U1]
    caster.tags = (*caster.tags, "boss")
    result = cast(state)
    assert result.state.units[U1].get_status("stun") is not None
    assert not of(result, StatusConverted)
    assert result.state.units[U1].control_dr == {}


def test_a_boss_hit_by_an_enemy_stun_is_still_converted() -> None:
    """對照組：Boss 被別人施加硬控仍然轉換（規則 3 只豁免自己付的代價）。"""
    state = battle(_stun_shield(), [(6, 6)])
    caster = state.units[U1]
    caster.tags = (*caster.tags, "boss")
    ctx = Ctx(state)
    execute(ctx, [ApplyStatusEffect(source_id=U2, target_id=U1, status_id="stun", duration=1)])
    assert state.units[U1].get_status("stun") is None


# ---------------------------------------------------------------------------
# 自暈的配套：仍可被推、拉、傳送；護盾照常存在
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["forced", "teleported"])
def test_a_self_stunned_unit_can_still_be_pushed_pulled_or_teleported(mode: str) -> None:
    state = cast(battle(_stun_shield(), [(6, 6)])).state
    assert state.units[U1].get_status("stun") is not None
    ctx = Ctx(state)
    execute(ctx, [MoveUnitEffect(unit_id=U1, dest=(4, 3), mode=mode)])  # type: ignore[arg-type]
    assert state.units[U1].pos == Pos(x=4, y=3)  # 推、拉（forced）與傳送（teleported）都有效


def test_the_shield_from_the_skill_exists_while_stunned_and_absorbs_damage() -> None:
    result = cast(battle(_stun_shield(), [(6, 6)]))
    shield = result.state.units[U1].get_status("shielded")
    assert shield is not None and shield.amount is not None and shield.amount >= 2
    assert result.state.units[U1].get_status("stun") is not None  # 兩者同時存在
    state = result.state
    state.active_unit = U2  # 敵人的回合：對暈眩中的施放者出手
    ctx = Ctx(state)
    from trpg.engine.effects.models import DamageEffect  # noqa: PLC0415

    hp_before = state.units[U1].hp
    execute(ctx, [DamageEffect(source_id=U2, target_id=U1, flat=1, mode="roll", min_damage=1)])
    assert state.units[U1].hp == hp_before  # 護盾先吸收
    after = state.units[U1].get_status("shielded")
    assert after is not None and after.amount is not None and after.amount < shield.amount


def test_the_shield_is_not_removed_when_the_stun_is_applied_or_ends() -> None:
    """護盾的存續只看它自己的持續回合（2）：暈眩的施加與結束都不會移除它。暈眩在被跳過的那個回合
    結束時才結束，護盾恰好在同一刻到期（見報告「待 PM 決定」）。"""
    state = cast(battle(_stun_shield(), [(6, 6)])).state
    assert state.units[U1].get_status("shielded") is not None
    done = resolve(state, EndTurn(unit_id=U1)).state
    shield = done.units[U1].get_status("shielded")
    stun = done.units[U1].get_status("stun")
    assert shield is not None and shield.remaining == 1
    assert stun is not None and stun.remaining == 1  # 兩者倒數同步


# ---------------------------------------------------------------------------
# 沉默、流血
# ---------------------------------------------------------------------------


def test_self_silence_blocks_the_casters_next_spell_but_not_weapon_skills() -> None:
    spell = make_skill(
        SID,
        SINGLE,
        [SPELL_DAMAGE],
        ap_cost=1,
        cost={"mana": 0, "self_status": {"status": "silenced", "duration": 2}},
    )
    state = hit_with(battle(spell, [(4, 3)]))
    result = cast(state, target_id=U2)
    assert result.state.units[U1].get_status("silenced") is not None
    assert result.state.units[U1].ap > 0  # 沉默不會讓本回合沒有 AP
    with pytest.raises(IllegalActionError):
        resolve(result.state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))


def test_self_bleed_hurts_at_the_start_of_the_casters_next_turn() -> None:
    skill = _strike({"stamina": 0, "self_status": {"status": "bleed", "duration": 2}})
    state = hit_with(battle(skill, [(4, 3)], base="hero_fighter"))
    result = cast(state, target_id=U2)
    assert result.state.units[U1].get_status("bleed") is not None
    state = result.state
    ticks: list[DamageDealt] = []
    for _ in range(4):
        active = state.active_unit
        assert active is not None
        step = resolve(state, EndTurn(unit_id=active))
        state = step.state
        ticks += [e for e in of(step, DamageDealt) if e.target_id == U1]
        if ticks:
            break
    assert ticks and ticks[0].element == "physical"


# ---------------------------------------------------------------------------
# 透支：下回合少 1 AP
# ---------------------------------------------------------------------------


def _own_turn_aps(state: BattleState, count: int) -> list[int]:
    """一直結束回合，記下 U1 接下來 ``count`` 個回合開始時的 AP。"""
    aps: list[int] = []
    for _ in range(12):
        active = state.active_unit
        assert active is not None
        step = resolve(state, EndTurn(unit_id=active))
        state = step.state
        aps += [e.ap for e in of(step, TurnStarted) if e.unit_id == U1]
        if len(aps) >= count:
            break
    return aps[:count]


def test_overdraft_costs_one_ap_on_the_next_turn_only() -> None:
    plain = _strike({"stamina": 0})
    drawn = _strike({"stamina": 0, "overdraft": 1})
    normal = cast(hit_with(battle(plain, [(4, 3)], base="hero_fighter")), target_id=U2)
    result = cast(hit_with(battle(drawn, [(4, 3)], base="hero_fighter")), target_id=U2)
    status = result.state.units[U1].get_status("overdrawn")
    assert status is not None and status.remaining == 2 and status.source_id == U1
    base_aps = _own_turn_aps(normal.state, 2)
    aps = _own_turn_aps(result.state, 2)
    assert aps[0] == base_aps[0] - 1  # 下一個回合少 1 AP
    assert aps[1] == base_aps[1]  # 只有一個回合
    assert result.state.units[U1].get_status("overdrawn") is not None


def test_overdraft_does_not_trigger_a_save_or_control_diminishing() -> None:
    skill = _strike({"stamina": 0, "overdraft": 1})
    result = cast(hit_with(battle(skill, [(4, 3)], base="hero_fighter")), target_id=U2)
    applied = [e for e in of(result, StatusApplied) if e.target_id == U1]
    assert [e.status_id for e in applied] == ["overdrawn"]
    assert result.state.units[U1].control_dr == {}


# ---------------------------------------------------------------------------
# AI 使用條件（共通規則 6）
# ---------------------------------------------------------------------------


def _gate(state: BattleState, skill: Any, **target: Any) -> Fraction:
    profile = lib().ai_profiles.by_id()["brute"]
    action = UseSkill(unit_id=U1, skill_id=skill.id, **target)
    p = preview(state, action)
    return self_cost_gate(state, state.units[U1], skill, p, profile, score=Fraction(10))


def test_the_ai_self_stuns_only_when_low_on_hp_with_an_enemy_nearby() -> None:
    skill = _stun_shield()
    healthy = battle(skill, [(5, 3)])
    assert _gate(healthy, skill) < 0  # HP 全滿：不自廢一個回合
    hurt = battle(skill, [(5, 3)])
    unit = hurt.units[U1]
    unit.hp = unit.max_hp // 4
    assert _gate(hurt, skill) == 10
    far = battle(skill, [(5, 3)])
    far.units[U1].hp = far.units[U1].max_hp // 4
    far.units[U1].pos = Pos(x=0, y=0)
    far_enemy = far.units[U2]
    far_enemy.pos = Pos(x=6, y=6)
    assert _gate(far, skill) < 0  # 附近沒有敵人


def test_the_ai_uses_overdraft_only_for_a_kill_or_two_or_more_enemies() -> None:
    skill = make_skill(
        SID,
        {"type": "square3", "range": 5},
        [DAMAGE],
        category="weapon",
        ap_cost=1,
        cost={"stamina": 0, "overdraft": 1},
    )
    lone = battle(skill, [(5, 3)], base="hero_fighter")
    assert _gate(lone, skill, target_pos=Pos(x=5, y=3)) < 0  # 單一敵人且打不死
    pair = battle(skill, [(5, 3), (5, 4)], base="hero_fighter")
    assert _gate(pair, skill, target_pos=Pos(x=5, y=3)) == 10  # 範圍內敵人 ≥ 2
    kill = battle(skill, [(5, 3)], base="hero_fighter")
    kill.units[U2].hp = 1
    assert _gate(kill, skill, target_pos=Pos(x=5, y=3)) == 10  # 這一擊能擊殺


def test_skills_without_a_self_penalty_are_never_gated() -> None:
    plain = _strike({"stamina": 0})
    state = battle(plain, [(5, 3)], base="hero_fighter")
    assert _gate(state, plain, target_id=U2) == 10


# ---------------------------------------------------------------------------
# 重播：含四招示範技能的整場戰鬥
# ---------------------------------------------------------------------------


def test_a_battle_with_the_four_demo_skills_replays_identically() -> None:
    ids = (
        "skill_frost_armor_seal",
        "skill_all_in_chant",
        "skill_blood_rage_slash",
        "skill_overdraft_strike",
    )
    demo = [lib().skills[i] for i in ids]
    flat = "\n".join(["000000000"] * 9)
    m = make_map(flat, None, ally=[(1, 2), (1, 5)], enemy=[(6, 2), (6, 4), (7, 3)])
    spawns = [
        spawn(Team.ALLY, (1, 2), caster_template([demo[0], demo[1]], max_hp=60)),
        spawn(Team.ALLY, (1, 5), caster_template(demo[2:], base="hero_fighter", max_hp=80)),
        spawn(Team.ENEMY, (6, 2), no_reactions(max_hp=90)),
        spawn(Team.ENEMY, (6, 4), no_reactions(max_hp=90)),
        spawn(Team.ENEMY, (7, 3), no_reactions(max_hp=90)),
    ]
    setup = make_setup(m, spawns, max_rounds=14)
    policy = UtilityAI(lib().ai_profiles)
    run = run_battle(setup, 11, policy)
    again = replay(setup, 11, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert LOG_FORMAT.endswith("/68")
    used = {e.skill_id for e in run.events if isinstance(e, SkillUsed)}
    assert used & set(ids)  # AI 真的用到了示範技能
