"""預支原語 ``borrow_ap``（AP-2，#168，06 6.3「新原語『預支』」）：本回合 +N、下回合 −N、不超過
上限、預支的回合不保留 AP、和透支疊加時 AP 最少 0、只有帶預支的主動技可以 0 AP、AI 的使用條件。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, battle, cast, of
from tests.skillgen.helpers import lib
from trpg.content.skills import SkillDef
from trpg.engine import EndTurn, resolve
from trpg.engine.ai.self_costs import borrow_allowed
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import ApBorrowed, EffectFizzled, TurnEnded, TurnStarted
from trpg.engine.rules.statuses import next_turn_ap_penalty
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Team

BIG = "skill_t_big"


def borrow_skill(
    amount: int = 1,
    *,
    skill_id: str = SID,
    ap_cost: int = 0,
    cooldown: int | None = None,
    extra: Sequence[dict[str, Any]] = (),
    kind: str = "active",
) -> SkillDef:
    cost: dict[str, Any] = {"mana": 0}
    if cooldown is not None:
        cost["cooldown"] = cooldown
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": "測試預支",
            "tier": 1,
            "rarity": "rare",
            "skeleton": "aura",
            "kind": kind,
            "category": "spell",
            "weapon_req": "focus",
            "ap_cost": ap_cost if kind == "active" else None,
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [{"type": "borrow_ap", "amount": amount}, *extra],
            "cost": cost,
        }
    )


def _end_round(state: BattleState) -> tuple[BattleState, list[Any]]:
    """一直結束回合，直到 U1 的下一個回合開始；回傳那時的狀態與途中的事件。"""
    events: list[Any] = []
    for _ in range(12):
        active = state.active_unit
        assert active is not None
        step = resolve(state, EndTurn(unit_id=active))
        state = step.state
        events += step.events
        if any(isinstance(e, TurnStarted) and e.unit_id == U1 for e in step.events):
            return state, events
    raise AssertionError("U1 沒有再輪到")


def _baseline_next_ap() -> int:
    """不預支、用光 AP 時 U1 下一個回合開始的 AP（玩家方每回合 AP）。"""
    state = battle(borrow_skill())
    state.units[U1].ap = 0
    after, _ = _end_round(state)
    return after.units[U1].ap


# ---------------------------------------------------------------------------
# 結算
# ---------------------------------------------------------------------------


def test_borrow_gives_n_now_and_takes_n_on_the_next_turn() -> None:
    base = _baseline_next_ap()
    state = battle(borrow_skill(1))
    before = state.units[U1].ap
    result = cast(state)
    unit = result.state.units[U1]
    assert unit.ap == before + 1
    assert unit.ap_borrowed == 1
    [event] = of(result, ApBorrowed)
    assert (event.amount, event.ap_after, event.next_turn_loss) == (1, before + 1, 1)
    status = unit.get_status("borrowed_ap")
    assert status is not None and status.amount == 1 and status.remaining == 2
    assert next_turn_ap_penalty(result.state.ruleset, unit, own_turn=True) == 1
    unit.ap = 0  # 用光
    after, _ = _end_round(result.state)
    assert after.units[U1].ap == base - 1
    assert after.units[U1].ap_lost == after.units[U1].ap_lost_borrowed == 1
    after.units[U1].ap = 0
    again, _ = _end_round(after)
    assert again.units[U1].ap == base  # 只扣一個回合
    assert again.units[U1].get_status("borrowed_ap") is None


def test_borrow_two_takes_two() -> None:
    base = _baseline_next_ap()
    state = battle(borrow_skill(2))
    result = cast(state)
    assert result.state.units[U1].ap == state.units[U1].ap + 2
    result.state.units[U1].ap = 0
    after, _ = _end_round(result.state)
    assert after.units[U1].ap == base - 2


def test_borrow_does_not_exceed_the_turn_cap_and_owes_only_what_it_gave() -> None:
    state = battle(borrow_skill(2))
    unit = state.units[U1]
    cap = unit.ap_per_turn + state.ruleset.core.ap_carry_max
    unit.ap = cap - 1
    result = cast(state)
    [event] = of(result, ApBorrowed)
    assert result.state.units[U1].ap == cap
    assert event.amount == event.next_turn_loss == 1


def test_borrow_at_the_cap_fizzles_and_owes_nothing() -> None:
    state = battle(borrow_skill(1))
    unit = state.units[U1]
    unit.ap = unit.ap_per_turn + state.ruleset.core.ap_carry_max
    result = cast(state)
    assert not of(result, ApBorrowed)
    assert [e.reason for e in of(result, EffectFizzled)] == ["ap_cap"]
    assert result.state.units[U1].get_status("borrowed_ap") is None
    assert result.state.units[U1].ap_borrowed == 0


def test_the_borrowing_turn_keeps_no_ap() -> None:
    base = _baseline_next_ap()
    state = battle(borrow_skill(1))
    result = cast(state)
    assert result.state.units[U1].ap >= 2  # 還剩 AP，平常會保留 1
    after, events = _end_round(result.state)
    [ended] = [e for e in events if isinstance(e, TurnEnded) and e.unit_id == U1]
    assert ended.ap_carried == 0
    assert after.units[U1].ap == base - 1  # 沒有保留，只有扣回
    assert after.units[U1].ap_carried_in == 0


def test_two_borrows_in_one_turn_add_up() -> None:
    base = _baseline_next_ap()
    state = battle(borrow_skill(1))
    first = cast(state)
    second = cast(first.state)
    [event] = of(second, ApBorrowed)
    assert event.next_turn_loss == 2
    unit = second.state.units[U1]
    assert unit.ap_borrowed == 2
    unit.ap = 0
    after, _ = _end_round(second.state)
    assert after.units[U1].ap == base - 2


def test_borrow_stacks_with_overdraft_and_never_goes_below_zero() -> None:
    state = battle(borrow_skill(2))
    result = cast(state)
    unit = result.state.units[U1]
    unit.statuses = sorted([*unit.statuses, _overdrawn(result.state)], key=lambda s: s.status_id)
    assert next_turn_ap_penalty(result.state.ruleset, unit, own_turn=True) == 3
    assert next_turn_ap_penalty(result.state.ruleset, unit, own_turn=True, borrowed=True) == 2
    unit.ap = 0
    unit.ap_per_turn = 2  # 每回合 2 AP：2 − 透支 1 − 預支 2 → 0
    after, _ = _end_round(result.state)
    hero = after.units[U1]
    assert hero.ap == 0
    assert hero.ap_lost == 2
    assert hero.ap_lost_borrowed == 2


def _overdrawn(state: BattleState) -> Any:
    del state
    return StatusInstance(status_id="overdrawn", remaining=2, source_id=U1, cost_status=True)


def test_borrow_is_deterministic() -> None:
    a = cast(battle(borrow_skill(1)))
    b = cast(battle(borrow_skill(1)))
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]


# ---------------------------------------------------------------------------
# 0 AP 例外（06 6.3）
# ---------------------------------------------------------------------------


def test_only_skills_with_borrow_may_cost_zero_ap() -> None:
    assert borrow_skill().ap_cost == 0
    with pytest.raises(ValidationError, match="ap_cost 必須是 1 到 3"):
        SkillDef.model_validate(
            {
                **borrow_skill().model_dump(exclude_none=True),
                "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
            }
        )


def test_a_borrow_skill_must_cost_zero_ap() -> None:
    with pytest.raises(ValidationError, match="borrow_ap"):
        borrow_skill(ap_cost=1)


def test_borrow_must_be_the_only_effect_of_an_active_skill() -> None:
    with pytest.raises(ValidationError):
        borrow_skill(extra=[{"type": "shield", "dice": "1d4", "affects": "self"}])
    with pytest.raises(ValidationError):
        borrow_skill(kind="passive")


# ---------------------------------------------------------------------------
# AI 使用條件：本回合差 AP、湊不出大招時才用
# ---------------------------------------------------------------------------


def _big(ap_cost: int) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": BIG,
            "name_zh": "測試大招",
            "tier": 1,
            "rarity": "common",
            "skeleton": "area",
            "category": "spell",
            "weapon_req": "focus",
            "ap_cost": ap_cost,
            "scaling_attr": "int",
            "shape": {"type": "single", "range": 5},
            "effects": [{"type": "damage", "dice": "2d6", "element": "fire"}],
            "cost": {"mana": 0},
        }
    )


def _ai_state(big_cost: int, ap: int, *, cooldown: bool = False) -> tuple[BattleState, SkillDef]:
    borrow = borrow_skill(1, cooldown=2)
    big = _big(big_cost)
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(5, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([borrow, big])),
        spawn(Team.ENEMY, (5, 3), no_reactions()),
    ]
    state = give_turn(make_state(m, spawns, skills=[borrow, big]), U1)
    state.units[U1].ap = ap
    if cooldown:
        state.units[U1].cooldowns[BIG] = 1
    return state, borrow


@pytest.mark.parametrize(
    ("big_cost", "ap", "cooldown", "expected"),
    [
        (3, 2, False, True),  # 差 1 AP：預支後放得出
        (3, 3, False, False),  # 已經夠：不用預支
        (3, 1, False, False),  # 差 2 AP：預支 1 也不夠
        (2, 1, False, True),
        (3, 2, True, False),  # 大招冷卻中
    ],
)
def test_the_ai_borrows_only_to_reach_a_skill_it_cannot_afford(
    big_cost: int, ap: int, cooldown: bool, expected: bool
) -> None:
    state, borrow = _ai_state(big_cost, ap, cooldown=cooldown)
    assert borrow_allowed(state, state.units[U1], borrow) is expected


def test_the_ai_does_not_borrow_at_the_cap() -> None:
    state, borrow = _ai_state(3, 2)
    unit = state.units[U1]
    unit.ap_per_turn = 1  # 上限 2：已經到頂
    assert borrow_allowed(state, unit, borrow) is False


def _borrow_score(state: BattleState) -> Any:
    ranked = UtilityAI(lib().ai_profiles).rank_all(state)
    scores = [r.score for r in ranked if getattr(r.action, "skill_id", None) == SID]
    return max(scores) if scores else None


def test_the_utility_ai_scores_borrow_only_when_it_unlocks_a_skill() -> None:
    allowed, _ = _ai_state(3, 2)
    score = _borrow_score(allowed)
    assert score is not None and score > 0
    blocked, _ = _ai_state(3, 3)
    score = _borrow_score(blocked)
    assert score is None or score < 0
