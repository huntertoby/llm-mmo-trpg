"""失手返還（AP-1，#168，05 5.2「⚠ AP 改版」）：2 AP 以上的技能所有目標都沒命中時返還 1 AP。

每條規則一列：單體失手、範圍技中 1 個、範圍技全空、被豁免擋下、不擲命中的技能（位移對抗）、
每回合最多 1 次、1 AP 技能不返還、命中不返還、敵人也適用、工坊值 0 時關閉、文字與重播。
"""

from __future__ import annotations

from typing import Any

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
    with_rolls,
)
from tests.engine.skill_helpers import (
    FLAT7,
    SID,
    U1,
    U2,
    U3,
    battle,
    cast,
    hit_with,
    of,
    script_rolls,
)
from trpg.content.skills import SkillDef
from trpg.engine import BattleState, EndTurn, UseSkill, resolve
from trpg.engine.events import (
    ApRefunded,
    AttackRolled,
    ManeuverRolled,
    StatusSaveRolled,
)
from trpg.engine.refunds import all_targets_missed
from trpg.narrative.events import describe_event
from trpg.shared.types import Team

DAMAGE: dict[str, Any] = {"type": "damage", "dice": "1d4", "element": "fire"}
SINGLE: dict[str, Any] = {"type": "single", "range": 4}


def bolt(ap_cost: int = 2, shape: dict[str, Any] | None = None, *effects: Any) -> SkillDef:
    return make_skill(SID, shape or SINGLE, list(effects) or [DAMAGE], ap_cost=ap_cost)


def tough(xy: tuple[int, int]) -> tuple[int, int, Any]:
    return (*xy, no_reactions("bandit", max_hp=500))


def refunds(result: Any) -> list[ApRefunded]:
    return [e for e in of(result, ApRefunded) if e.on_miss]


def missed(state: BattleState) -> BattleState:
    return with_rolls(state, [(20, 1)])  # 自然 1：失手


# ---------------------------------------------------------------------------
# 規則
# ---------------------------------------------------------------------------


def test_a_single_target_miss_refunds_one_ap() -> None:
    state = missed(battle(bolt(), [tough((4, 3))]))
    before = state.units[U1].ap
    result = cast(state, target_id=U2)
    assert [e.hit for e in of(result, AttackRolled)] == [False]
    (refund,) = refunds(result)
    assert (refund.unit_id, refund.skill_id, refund.amount) == (U1, SID, 1)
    assert result.state.units[U1].ap == before - 2 + 1 == refund.ap_after
    assert result.state.units[U1].miss_refunded


def test_a_hit_is_not_refunded() -> None:
    state = hit_with(battle(bolt(), [tough((4, 3))]))
    result = cast(state, target_id=U2)
    assert refunds(result) == []
    assert result.state.units[U1].ap == state.units[U1].ap - 2


def test_an_area_skill_that_hits_one_target_is_not_refunded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = bolt(2, {"type": "cross", "range": 4})
    state = battle(skill, [tough((4, 3)), tough((4, 4))])
    script_rolls(monkeypatch, [1, 19, 1, 1, 1, 1, 1, 1])  # U2 失手、U3 命中，其餘是傷害骰
    result = cast(state, target_pos={"x": 4, "y": 3})
    assert sorted((e.target_id, e.hit) for e in of(result, AttackRolled)) == [
        (U2, False),
        (U3, True),
    ]
    assert refunds(result) == []


def test_an_area_skill_that_misses_every_target_is_refunded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = bolt(2, {"type": "cross", "range": 4})
    state = battle(skill, [tough((4, 3)), tough((4, 4))])
    script_rolls(monkeypatch, [1, 1])
    result = cast(state, target_pos={"x": 4, "y": 3})
    assert [e.hit for e in of(result, AttackRolled)] == [False, False]
    assert [e.amount for e in refunds(result)] == [1]


def test_a_hit_blocked_by_the_save_counts_as_a_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """只施加狀態的技能：命中了，但狀態被抵抗（豁免擋下）→ 算沒命中。"""
    stun = {"type": "apply_status", "status": "stun", "duration": 1}
    state = battle(bolt(2, None, stun), [tough((4, 3))])
    script_rolls(monkeypatch, [19, 1])  # 命中 19；抵抗判定自然 1（攻方失敗）
    result = cast(state, target_id=U2)
    assert [e.hit for e in of(result, AttackRolled)] == [True]
    assert [e.applied for e in of(result, StatusSaveRolled)] == [False]
    assert [e.amount for e in refunds(result)] == [1]


def test_a_hit_that_deals_damage_is_not_refunded_even_when_the_status_is_saved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stun = {"type": "apply_status", "status": "stun", "duration": 1}
    state = battle(bolt(2, None, DAMAGE, stun), [tough((4, 3))])
    script_rolls(monkeypatch, [19, 1, 1, 1, 1, 1])
    result = cast(state, target_id=U2)
    assert [e.applied for e in of(result, StatusSaveRolled)] == [False]
    assert refunds(result) == []


def test_a_skill_without_a_hit_roll_is_refunded_when_every_target_resists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """不擲命中的技能（互換：位移對抗）：所有目標都抵抗成功 → 返還。"""
    swap = {"type": "swap", "affects": "enemies"}
    state = battle(bolt(2, None, swap), [tough((4, 3))])
    script_rolls(monkeypatch, [1, 20])  # 攻方自然 1、守方 20
    result = cast(state, target_id=U2)
    assert of(result, AttackRolled) == []
    assert [e.success for e in of(result, ManeuverRolled)] == [False]
    assert [e.amount for e in refunds(result)] == [1]


def test_a_skill_without_a_hit_roll_that_lands_is_not_refunded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    swap = {"type": "swap", "affects": "enemies"}
    state = battle(bolt(2, None, swap), [tough((4, 3))])
    script_rolls(monkeypatch, [20, 1])
    result = cast(state, target_id=U2)
    assert [e.success for e in of(result, ManeuverRolled)] == [True]
    assert refunds(result) == []


def test_at_most_once_per_turn_and_again_next_turn() -> None:
    state = battle(bolt(), [tough((4, 3))])
    state.units[U1].ap = 5
    first = cast(missed(state), target_id=U2)
    assert len(refunds(first)) == 1
    second = cast(missed(first.state), target_id=U2)
    assert refunds(second) == [] and not of(second, AttackRolled)[0].hit
    assert second.state.units[U1].ap == 5 - 2 + 1 - 2
    # 下一個回合重新可以拿
    s = second.state
    while True:
        assert s.active_unit is not None
        s = resolve(s, EndTurn(unit_id=s.active_unit)).state
        if s.active_unit == U1:
            break
    assert not s.units[U1].miss_refunded
    assert len(refunds(cast(missed(s), target_id=U2))) == 1


def test_a_one_ap_skill_is_not_refunded() -> None:
    state = missed(battle(bolt(1), [tough((4, 3))]))
    result = cast(state, target_id=U2)
    assert not of(result, AttackRolled)[0].hit
    assert refunds(result) == []


def test_enemies_get_the_refund_too() -> None:
    skill = bolt()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter", max_hp=500)),
        spawn(Team.ENEMY, (4, 3), caster_template([skill])),  # 敵方的法師
    ]
    state = missed(give_turn(make_state(m, spawns, skills=[skill]), U2))
    result = resolve(state, UseSkill(unit_id=U2, skill_id=SID, target_id=U1))
    assert [(e.unit_id, e.amount) for e in refunds(result)] == [(U2, 1)]


def test_a_zero_refund_turns_the_rule_off() -> None:
    skill = bolt()
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([skill])),
        spawn(Team.ENEMY, (4, 3), no_reactions("bandit", max_hp=500)),
    ]
    state = missed(give_turn(make_state(m, spawns, skills=[skill], miss_refund_ap=0), U1))
    assert refunds(cast(state, target_id=U2)) == []


def test_no_targets_means_nothing_to_miss() -> None:
    assert not all_targets_missed([], "unit_0001", {})


def test_the_log_line_says_it_was_a_miss_refund() -> None:
    state = missed(battle(bolt(), [tough((4, 3))]))
    result = cast(state, target_id=U2)
    (refund,) = refunds(result)
    line = describe_event(refund, result.state)
    assert line is not None
    assert "失手返還" in line and "返還了 1 AP" in line


def test_the_refund_is_deterministic() -> None:
    from trpg.engine import state_to_json  # noqa: PLC0415

    state = missed(battle(bolt(), [tough((4, 3))]))
    a, b = cast(state, target_id=U2), cast(state, target_id=U2)
    assert state_to_json(a.state) == state_to_json(b.state)
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]
    assert library().ruleset.core.miss_refund_ap == 1  # 初值
