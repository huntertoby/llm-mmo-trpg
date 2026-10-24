"""Phase 2H-1 3.3：自身狀態代價 ``cost.self_status`` 的結算、預算折抵與驗證。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, hit_with, of
from tests.skillgen.helpers import lib, skill, violations
from trpg.content.skills import SkillDef
from trpg.engine import EndTurn, resolve
from trpg.engine.ai.utility import skill_cost
from trpg.engine.events import DamageDealt, SkillUsed, StatusApplied, StatusSaveRolled
from trpg.skillgen.budget import skill_budget

SINGLE = {"type": "single", "range": 5}
DAMAGE = {"type": "damage", "multiplier_permille": 1000}


def _rules(s: SkillDef) -> list[str]:
    return [v.rule for v in violations(s)]


def _lunge(self_status: dict[str, Any] | None) -> SkillDef:
    cost: dict[str, Any] = {} if self_status is None else {"self_status": self_status}
    return make_skill(SID, SINGLE, [DAMAGE], category="weapon", ap_cost=1, cost=cost)


def test_casting_gives_the_caster_the_status_without_a_save() -> None:
    state = battle(_lunge({"status": "vulnerable", "duration": 2}), [(4, 3)], base="hero_fighter")
    result = cast(hit_with(state), target_id=U2)
    caster = result.state.units[U1]
    status = caster.get_status("vulnerable")
    assert status is not None and status.remaining == 2 and status.source_id == U1
    applied = [e for e in of(result, StatusApplied) if e.target_id == U1]
    assert [(e.status_id, e.duration, e.source_id) for e in applied] == [("vulnerable", 2, U1)]
    assert not of(result, StatusSaveRolled)  # 不擲抵抗
    assert of(result, SkillUsed)


def test_the_status_counts_down_at_the_end_of_the_casting_turn() -> None:
    state = battle(_lunge({"status": "slow", "duration": 3}), [(4, 3)], base="hero_fighter")
    result = cast(hit_with(state), target_id=U2)
    after = resolve(result.state, EndTurn(unit_id=U1))
    status = after.state.units[U1].get_status("slow")
    assert status is not None and status.remaining == 2  # 施放當回合結束就 −1


def test_the_status_is_applied_after_the_cast_so_weaken_does_not_hit_its_own_damage() -> None:
    plain = battle(_lunge(None), [(4, 3)], base="hero_fighter")
    weakened = battle(_lunge({"status": "weaken", "duration": 2}), [(4, 3)], base="hero_fighter")
    dealt = []
    for state in (plain, weakened):
        result = cast(hit_with(state), target_id=U2)
        dealt.append(next(e.amount for e in of(result, DamageDealt) if e.cause == "attack"))
    assert dealt[0] == dealt[1]


def test_a_skill_without_self_status_leaves_the_caster_clean() -> None:
    state = battle(_lunge(None), [(4, 3)], base="hero_fighter")
    result = cast(hit_with(state), target_id=U2)
    assert not result.state.units[U1].statuses


def test_the_ai_charges_the_self_status_as_a_cost() -> None:
    plain = battle(_lunge(None), [(4, 3)], base="hero_fighter")
    costly = battle(_lunge({"status": "vulnerable", "duration": 3}), [(4, 3)], base="hero_fighter")
    profile = lib().ai_profiles.by_id()["brute"]
    from trpg.engine import UseSkill  # noqa: PLC0415

    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    base = skill_cost(plain, plain.units[U1], action, profile.weights, profile.status_values)
    extra = skill_cost(costly, costly.units[U1], action, profile.weights, profile.status_values)
    assert extra - base == profile.weights.damage * profile.status_values["vulnerable"] * 2


# ---------------------------------------------------------------------------
# 驗證與預算
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("duration", [0, 1, 4])
def test_duration_must_be_two_or_three(duration: int) -> None:
    with pytest.raises(ValidationError, match="duration"):
        skill(cost={"mana": 4, "self_status": {"status": "slow", "duration": duration}})


@pytest.mark.parametrize("kind", ["passive", "reaction", "stance"])
def test_only_active_skills_may_use_self_status(kind: str) -> None:
    data = {
        "kind": kind,
        "ap_cost": None,
        "cost": {"self_status": {"status": "slow", "duration": 2}},
    }
    with pytest.raises(ValidationError, match=r"只有主動技能可以有 cost.self_status"):
        skill(**data)


def test_a_status_outside_the_allowed_list_is_rejected_by_the_validator() -> None:
    bad = skill(cost={"mana": 4, "cooldown": 2, "self_status": {"status": "frozen", "duration": 2}})
    assert "cap.self_status" in _rules(bad)
    good = skill(cost={"mana": 4, "cooldown": 2, "self_status": {"status": "root", "duration": 2}})
    assert "cap.self_status" not in _rules(good)


def test_an_unknown_status_is_a_reference_error() -> None:
    bad = skill(cost={"self_status": {"status": "petrified", "duration": 2}})
    assert "reference" in _rules(bad)


@pytest.mark.parametrize(
    ("status", "duration", "expected"),
    [
        ("vulnerable", 2, 160),  # 4 點 × 1 有效回合 × 40
        ("slow", 2, 120),  # 3 × 1 × 40
        ("slow", 3, 240),  # 3 × 2 × 40
        ("root", 2, 160),  # 4 × 1 × 40
        ("weaken", 3, 250),  # 4 × 2 × 40 = 320 → 自己的上限 250
    ],
)
def test_the_allowance_is_points_times_effective_turns_with_its_own_cap(
    status: str, duration: int, expected: int
) -> None:
    report = skill_budget(
        skill(cost={"self_status": {"status": status, "duration": duration}}), lib()
    )
    (part,) = report.allowance_parts
    assert part[1] == expected
    assert report.allowance_permille == expected


def test_the_self_status_allowance_is_truncated_by_the_total_cap() -> None:
    """冷卻 6（300）＋ 法力 99（150）＋ 自身虛弱 3 回合（250）＝ 700 → 總上限 500。"""
    report = skill_budget(
        skill(
            cost={
                "mana": 99,
                "cooldown": 6,
                "self_status": {"status": "weaken", "duration": 3},
            }
        ),
        lib(),
    )
    assert (report.allowance_raw_permille, report.allowance_permille) == (700, 500)
    assert report.allowance_capped


def test_budget_rules_come_from_skill_budget_yaml() -> None:
    rule = lib().budget.allowance.self_status
    assert set(rule.allowed) == {  # 3-50：加入暈眩、沉默、流血
        "vulnerable",
        "weaken",
        "slow",
        "root",
        "stun",
        "silenced",
        "bleed",
    }
    assert (rule.per_point_permille, rule.cap) == (40, 250)
