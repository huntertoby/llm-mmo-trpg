"""Phase 2D-1 3.9 第 5、6 項：護盾（``shield``）與淨化（``cleanse``）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    spawn,
    template,
)
from tests.engine.skill_helpers import U1, U2, battle, cast, of, script_rolls
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import Attack, EndTurn, preview, resolve, state_from_json, state_to_json
from trpg.engine.effects import DamageEffect, ShieldEffect, run_effects
from trpg.engine.events import (
    EVENT_ADAPTER,
    DamageDealt,
    ShieldAbsorbed,
    ShieldGained,
    StatusRemoved,
)
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Element, Team
from trpg.skillgen.budget import BudgetError, skill_budget

SID = "skill_t_prim"
FLAT = "\n".join(["000000"] * 6)


def _shield_skill(**effect: object) -> SkillDef:
    spec = {"type": "shield", "dice": "2d6", "affects": "allies", **effect}
    return make_skill(SID, {"type": "single", "range": 4}, [spec])


def _duel() -> BattleState:
    m = make_map(FLAT, ally=[(1, 1)], enemy=[(2, 1)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 1), template("hero_fighter", reactions=[])),
            spawn(Team.ENEMY, (2, 1), template("bandit", reactions=[])),
        ],
    )
    return give_turn(state, U1)


def _shielded(state: BattleState, uid: str, amount: int, remaining: int = 2) -> BattleState:
    s = state.clone()
    s.units[uid].statuses = [  # type: ignore[index]
        StatusInstance("shielded", remaining, U1, amount),
    ]
    return s


def _hit(state: BattleState, flat: int = 10, *, percent: int | None = None) -> tuple[list, list]:  # type: ignore[type-arg]
    effect = DamageEffect(
        source_id=U1,
        target_id=U2,
        cause="attack" if percent is None else "fall",
        flat=flat,
        element=Element.PHYSICAL,
        mode="roll" if percent is None else "percent_max_hp",
        permille=percent or 0,
        apply_element_mod=percent is None,
    )
    result = run_effects(state, [effect])
    return list(result.events), [result.state]


# ---------------------------------------------------------------------------
# 護盾量與施加
# ---------------------------------------------------------------------------


def test_shield_amount_is_dice_plus_half_the_scaling_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(_shield_skill(), foes=[(6, 6)], allies=[(3, 4)])
    script_rolls(monkeypatch, [3, 4])
    result = cast(state, target_id=U2)
    (gained,) = of(result, ShieldGained)
    attr = state.units[U1].attributes["int"]  # type: ignore[index]
    scaled = attr * state.ruleset.core.spell_attr_multiplier_permille // 1000
    assert gained.unit_id == U2 and gained.rolls == (3, 4)
    assert gained.amount == 7 + scaled == gained.total
    status = result.state.units[U2].get_status("shielded")
    assert status is not None and status.amount == gained.total
    assert (status.remaining, status.source_id) == (2, U1)


def test_a_second_shield_keeps_the_larger_amount_and_refreshes_the_duration() -> None:
    def total(existing: int, new_flat: int) -> tuple[int, int | None]:
        state = _shielded(_duel(), U2, existing, remaining=1)
        res = run_effects(state, [ShieldEffect(target_id=U2, source_id=U1, flat=new_flat)])
        status = res.state.units[U2].get_status("shielded")
        assert status is not None
        return status.amount or 0, status.remaining

    assert total(20, 12) == (20, 2)  # 較大值：原有的 20
    assert total(5, 12) == (12, 2)  # 較大值：新的 12


# ---------------------------------------------------------------------------
# 吸收
# ---------------------------------------------------------------------------


def test_damage_hits_the_shield_before_hit_points() -> None:
    state = _shielded(_duel(), U2, 15)
    events, (after,) = _hit(state, flat=10)
    absorbed = [e for e in events if isinstance(e, ShieldAbsorbed)]
    (dealt,) = [e for e in events if isinstance(e, DamageDealt)]
    assert [(a.absorbed, a.remaining) for a in absorbed] == [(10, 5)]
    assert dealt.amount == 10 and dealt.absorbed == 10
    assert dealt.hp_before == dealt.hp_after == state.units[U2].hp
    status = after.units[U2].get_status("shielded")
    assert status is not None and status.amount == 5


def test_a_partial_absorb_damages_the_rest_and_removes_the_depleted_shield() -> None:
    state = _shielded(_duel(), U2, 6)
    events, (after,) = _hit(state, flat=10)
    kinds = [type(e) for e in events]
    # 先吸收、再移除（depleted）、最後才是傷害事件
    assert kinds[:3] == [ShieldAbsorbed, StatusRemoved, DamageDealt]
    removed = events[1]
    assert isinstance(removed, StatusRemoved) and removed.reason == "depleted"
    dealt = events[2]
    assert isinstance(dealt, DamageDealt)
    assert (dealt.amount, dealt.absorbed) == (10, 6)
    assert dealt.hp_before - dealt.hp_after == 4  # 只記實際扣血
    assert after.units[U2].get_status("shielded") is None


def test_percentage_damage_ignores_the_shield() -> None:
    state = _shielded(_duel(), U2, 50)
    events, (after,) = _hit(state, percent=100)
    assert not [e for e in events if isinstance(e, ShieldAbsorbed)]
    (dealt,) = [e for e in events if isinstance(e, DamageDealt)]
    assert dealt.absorbed == 0 and dealt.hp_after < dealt.hp_before
    status = after.units[U2].get_status("shielded")
    assert status is not None and status.amount == 50


def test_a_shield_expires_with_its_duration_and_keeps_its_amount_while_ticking() -> None:
    state = _shielded(_duel(), U2, 9, remaining=2)
    state = resolve(resolve(state, EndTurn(unit_id=U1)).state, EndTurn(unit_id=U2)).state
    status = state.units[U2].get_status("shielded")
    assert status is not None and (status.remaining, status.amount) == (1, 9)


# ---------------------------------------------------------------------------
# 預覽、序列化
# ---------------------------------------------------------------------------


def test_preview_matches_the_actual_damage_through_a_shield(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _shielded(_duel(), U2, 4)
    action = Attack(unit_id=U1, target_id=U2)
    plain = preview(_duel(), action)
    shielded = preview(state, action)
    assert plain.damage is not None and shielded.damage is not None
    assert shielded.damage.minimum == max(0, plain.damage.minimum - 4)
    assert shielded.damage.expected_if_hit < plain.damage.expected_if_hit
    script_rolls(monkeypatch, [19] + [1] * 10)
    low = resolve(state, action)
    (dealt,) = [e for e in of(low, DamageDealt) if e.cause == "attack"]
    assert dealt.hp_before - dealt.hp_after == shielded.damage.minimum
    assert dealt.absorbed == min(4, dealt.amount)


def test_a_shielded_state_round_trips_through_json() -> None:
    state = _shielded(_duel(), U2, 12)
    again = state_from_json(state_to_json(state))
    assert again.units[U2].get_status("shielded") == state.units[U2].get_status("shielded")
    (event,) = of(run_effects(state, [ShieldEffect(target_id=U2, flat=3)]), ShieldGained)
    assert EVENT_ADAPTER.validate_json(EVENT_ADAPTER.dump_json(event)) == event


# ---------------------------------------------------------------------------
# 淨化
# ---------------------------------------------------------------------------


def _cleanse_skill(affects: str = "allies") -> SkillDef:
    return make_skill(
        SID, {"type": "single", "range": 4}, [{"type": "cleanse", "affects": affects}]
    )


def test_cleanse_removes_only_harmful_statuses_in_id_order() -> None:
    state = battle(_cleanse_skill(), foes=[(6, 6)], allies=[(3, 4)])
    ally = state.units[U2]
    ally.statuses = [
        StatusInstance("burning", 2, None),
        StatusInstance("guarded", 2, None),
        StatusInstance("poison", 3, None),
        StatusInstance("slow", 2, None),
    ]
    result = cast(state, target_id=U2)
    removed = [(e.status_id, e.reason) for e in of(result, StatusRemoved)]
    assert removed == [("burning", "cleansed"), ("poison", "cleansed"), ("slow", "cleansed")]
    assert [s.status_id for s in result.state.units[U2].statuses] == ["guarded"]


def test_cleanse_without_harmful_statuses_emits_nothing() -> None:
    state = battle(_cleanse_skill(), foes=[(6, 6)], allies=[(3, 4)])
    result = cast(state, target_id=U2)
    assert not of(result, StatusRemoved)


def test_the_validator_rejects_cleanse_against_enemies() -> None:
    rules = library().ruleset
    for affects in ("enemies", "all"):
        skill = _cleanse_skill(affects)
        problems = skill_problems(
            skill,
            rules.shapes.by_id(),
            rules.primitives.by_id(),
            status_ids={s.id for s in rules.statuses.statuses},
            object_ids=set(),
            conditions=rules.conditions.by_id(),
        )
        assert any("cleanse" in p and "affects" in p for p in problems), problems


def test_shield_status_cannot_be_applied_by_a_skill_budget() -> None:
    skill = make_skill(
        SID,
        {"type": "single", "range": 4},
        [{"type": "apply_status", "status": "shielded", "affects": "allies"}],
    )
    with pytest.raises(BudgetError):
        skill_budget(skill, library())
