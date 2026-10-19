"""高變異、超載與依情況縮放（Phase 3D-7b，``docs/phases/Phase3D計畫.md`` 7.2、7.3）：爆骰（含次數
上限）、暴擊範圍、基礎傷害折扣、超載（每層加成、門檻反噬並清空、反噬上限）、``scaling`` 四種依據
（捨去與上限）、重播。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    OverloadTriggered,
    StacksChanged,
)
from trpg.engine.skills.variance import overload_bonus, scale_bonus, scale_steps
from trpg.shared.rng import Rng

SINGLE5: dict[str, Any] = {"type": "single", "range": 5}


def spell(*effects: dict[str, Any], **fields: Any) -> SkillDef:
    data = make_skill(SID, SINGLE5, list(effects)).model_dump(mode="json")
    data.update(fields)
    return SkillDef.model_validate(data)


def damage(dice: str = "1d6", **fields: Any) -> dict[str, Any]:
    return {"type": "damage", "dice": dice, "element": "fire", **fields}


def script_randint(monkeypatch: pytest.MonkeyPatch, values: Sequence[int]) -> list[int]:
    """讓接下來的 ``Rng.randint``（所有骰子都經過它）依序回傳 ``values``；用完再擲會讓測試失敗。"""
    queue = list(values)

    def randint(self: Rng, lo: int, hi: int) -> int:
        assert queue, "骰值用完了"
        value = queue.pop(0)
        assert lo <= value <= hi, f"{value} 不在 {lo}–{hi}"
        return value

    monkeypatch.setattr(Rng, "randint", randint)
    return queue


# ---------------------------------------------------------------------------
# 爆骰
# ---------------------------------------------------------------------------


def test_an_exploding_die_rerolls_on_its_maximum(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(damage(explode=True)), [(5, 3)])
    script_randint(monkeypatch, [19, 6, 6, 3])  # 命中；6 爆、6 再爆、3 停
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.rolls == (6, 6, 3) and hit.exploded == 2


def test_the_explosion_stops_at_the_reroll_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(damage(explode=True)), [(5, 3)])
    queue = script_randint(monkeypatch, [19, 6, 6, 6])  # 第三顆也是 6，但每顆最多再擲 2 次
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.rolls == (6, 6, 6) and hit.exploded == 2 and queue == []


def test_a_die_that_does_not_reach_its_maximum_does_not_explode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(damage(explode=True)), [(5, 3)])
    queue = script_randint(monkeypatch, [19, 5])
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.rolls == (5,) and hit.exploded == 0 and queue == []


def test_without_explode_the_maximum_roll_is_final(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(damage()), [(5, 3)])
    queue = script_randint(monkeypatch, [19, 6])
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.rolls == (6,) and hit.exploded == 0 and queue == []


def test_every_die_of_a_critical_hit_can_explode(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(spell(damage(explode=True)), [(5, 3)])
    script_randint(monkeypatch, [20, 6, 2, 4])  # 自然 20 暴擊：2 顆骰，第一顆爆骰
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.crit and hit.rolls == (6, 2, 4) and hit.exploded == 1


# ---------------------------------------------------------------------------
# 暴擊範圍與基礎傷害折扣
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("natural", "crit"), [(17, True), (16, False)])
def test_the_skill_crit_range_widens_the_critical_hit(
    monkeypatch: pytest.MonkeyPatch, natural: int, crit: bool
) -> None:
    state = battle(spell(damage(), crit_range=17), [(5, 3)])
    script_randint(monkeypatch, [natural, 3, 3])
    (rolled,) = of(cast(state, target_id=U2), AttackRolled)
    assert rolled.hit and rolled.crit is crit


def test_without_a_skill_crit_range_a_spell_only_crits_on_twenty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(damage()), [(5, 3)])
    script_randint(monkeypatch, [19, 3])
    (rolled,) = of(cast(state, target_id=U2), AttackRolled)
    assert rolled.hit and not rolled.crit


def test_a_weapon_skill_takes_the_wider_of_the_weapon_and_skill_crit_range() -> None:
    from trpg.engine.skills.targeting import skill_profile  # noqa: PLC0415

    plain = make_skill(
        SID, SINGLE5, [{"type": "damage", "multiplier_permille": 1000}], category="weapon"
    )
    wide = SkillDef.model_validate(plain.model_dump(mode="json") | {"crit_range": 17})
    state = battle(wide, [(5, 3)], base="hero_fighter")
    assert skill_profile(state, state.units[U1], wide).crit_range == 17
    weapon_range = state.units[U1].weapon.crit_range
    assert skill_profile(state, state.units[U1], plain).crit_range == weapon_range >= 19


def test_the_base_damage_discount_multiplies_every_damage_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(damage(), damage("1d4"), damage_permille=750), [(5, 3)])
    script_randint(monkeypatch, [19, 3, 2])
    hits = of(cast(state, target_id=U2), DamageDealt)
    assert [h.multiplier_permille for h in hits] == [750, 750]


def test_the_discount_explode_and_crit_range_can_be_combined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(spell(damage(explode=True), damage_permille=750, crit_range=17), [(5, 3)])
    script_randint(monkeypatch, [18, 6, 4, 6, 1])  # 18 暴擊：2 顆骰，兩顆都是 6 而各自爆骰
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.crit and hit.rolls == (6, 4, 6, 1) and hit.exploded == 2
    assert hit.multiplier_permille == 750


# ---------------------------------------------------------------------------
# 超載
# ---------------------------------------------------------------------------

CHARGE: dict[str, Any] = {
    "type": "add_stack",
    "stack": "overload_surge",
    "amount": 1,
    "affects": "self",
}


def surge_skill(*, tagged: bool = True) -> SkillDef:
    tags = ["overcurrent"] if tagged else ["lightning"]
    return spell(damage("1d8"), CHARGE, tags=tags, rarity="rare")


def test_each_overload_stack_raises_the_damage_of_tagged_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(surge_skill(), [(5, 3)])
    state.units[U1].stacks["overload_surge"] = 2
    script_randint(monkeypatch, [19, 4])
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.multiplier_permille == 1400  # 1000 + 2 層 × 200‰


def test_overload_does_not_boost_skills_without_the_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(surge_skill(tagged=False), [(5, 3)])
    state.units[U1].stacks["overload_surge"] = 3
    script_randint(monkeypatch, [19, 4])
    (hit,) = of(cast(state, target_id=U2), DamageDealt)
    assert hit.multiplier_permille == 1000


def test_below_the_threshold_a_hit_only_accumulates_a_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(surge_skill(), [(5, 3)])
    state.units[U1].stacks["overload_surge"] = 3
    script_randint(monkeypatch, [19, 4])
    result = cast(state, target_id=U2)
    assert result.state.units[U1].stacks["overload_surge"] == 4
    assert not of(result, OverloadTriggered)


def test_reaching_the_threshold_strikes_the_caster_and_clears_the_stacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(surge_skill(), [(5, 3)])
    state.units[U1].stacks["overload_surge"] = 4
    hp = state.units[U1].hp
    script_randint(monkeypatch, [19, 4, 3, 5])  # 命中、1d8、反噬 2d6（3 與 5）
    result = cast(state, target_id=U2)
    (triggered,) = of(result, OverloadTriggered)
    assert (triggered.unit_id, triggered.stacks, triggered.threshold) == (U1, 5, 5)
    changes = [(e.before, e.after, e.reason) for e in of(result, StacksChanged)]
    assert changes == [(4, 5, "gained"), (5, 0, "overload")]
    assert "overload_surge" not in result.state.units[U1].stacks
    hit, back = of(result, DamageDealt)
    assert hit.multiplier_permille == 1800  # 以施放前的 4 層計算
    assert (back.target_id, back.cause, back.rolls) == (U1, "backlash", (3, 5))
    assert result.state.units[U1].hp == hp - back.amount


def test_the_overload_backlash_never_kills_the_caster(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(surge_skill(), [(5, 3)])
    state.units[U1].stacks["overload_surge"] = 4
    state.units[U1].hp = 2
    script_randint(monkeypatch, [19, 4, 6, 6])
    result = cast(state, target_id=U2)
    assert result.state.units[U1].hp == 1 and result.state.units[U1].alive


def test_overload_bonus_is_a_pure_function_of_stacks_and_tags() -> None:
    state = battle(surge_skill(), [(5, 3)])
    caster = state.units[U1]
    assert overload_bonus(state, caster, surge_skill()) == 0
    caster.stacks["overload_surge"] = 3
    assert overload_bonus(state, caster, surge_skill()) == 600
    assert overload_bonus(state, caster, surge_skill(tagged=False)) == 0


# ---------------------------------------------------------------------------
# scaling 四種依據
# ---------------------------------------------------------------------------


def scaled(by: str, per_step: int = 80, cap: int = 800) -> SkillDef:
    scaling = {"by": by, "per_step_permille": per_step, "cap_permille": cap}
    return spell(damage("1d6", scaling=scaling), rarity="rare")


def hit_on_u2(state: BattleState) -> DamageDealt:
    result = cast(state, target_id=U2)
    (hit,) = [e for e in of(result, DamageDealt) if e.target_id == U2]
    return hit


def test_missing_hp_adds_a_step_for_every_ten_percent_of_max_hp_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(scaled("missing_hp_10pct"), [(5, 3)])
    caster = state.units[U1]
    caster.max_hp, caster.hp = 40, 25  # 少 37.5%（零頭不算）→ 3 步
    assert scale_steps(state, caster, state.units[U2], "missing_hp_10pct") == 3
    script_randint(monkeypatch, [19, 3])
    assert hit_on_u2(state).multiplier_permille == 1000 + 3 * 80


def test_missing_hp_is_zero_at_full_health_and_below_ten_percent() -> None:
    state = battle(scaled("missing_hp_10pct"), [(5, 3)])
    caster, target = state.units[U1], state.units[U2]
    assert scale_steps(state, caster, target, "missing_hp_10pct") == 0
    caster.max_hp, caster.hp = 40, 37  # 少 7.5%
    assert scale_steps(state, caster, target, "missing_hp_10pct") == 0
    caster.hp = 36  # 少 10%
    assert scale_steps(state, caster, target, "missing_hp_10pct") == 1


def test_distance_adds_a_step_per_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(scaled("distance", 60), [(6, 3)])  # 施放者 (3, 3)、目標 (6, 3)：距離 3
    script_randint(monkeypatch, [19, 3])
    assert hit_on_u2(state).multiplier_permille == 1000 + 3 * 60


def test_enemies_adjacent_to_the_target_count_for_the_caster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 目標 U2 在 (6, 3)；對施放者而言的另外兩名敵人在 (6, 4)、(5, 3)，第四名在 (6, 6) 不相鄰
    state = battle(scaled("enemies_adjacent_target", 100), [(6, 3), (6, 4), (5, 3), (6, 6)])
    script_randint(monkeypatch, [19, 3])
    assert hit_on_u2(state).multiplier_permille == 1000 + 2 * 100


def test_enemies_adjacent_to_the_caster_count_for_every_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 施放者 (3, 3)：相鄰的敵人在 (4, 3)（目標 U2）與 (3, 4)；(6, 3) 太遠
    state = battle(scaled("enemies_adjacent_self", 100), [(4, 3), (3, 4), (6, 3)])
    script_randint(monkeypatch, [19, 3])
    assert hit_on_u2(state).multiplier_permille == 1000 + 2 * 100


def test_allies_next_to_the_caster_are_not_counted() -> None:
    state = battle(scaled("enemies_adjacent_self"), [(6, 3)], allies=[(3, 4)])
    steps = scale_steps(state, state.units[U1], state.units[U2], "enemies_adjacent_self")
    assert steps == 0


def test_the_scaling_bonus_is_limited_by_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(scaled("distance", 150, 300), [(6, 3)])  # 3 步 × 150 = 450 → 上限 300
    script_randint(monkeypatch, [19, 3])
    assert hit_on_u2(state).multiplier_permille == 1300


def test_scale_bonus_is_zero_without_scaling_and_capped_with_it() -> None:
    state = battle(scaled("distance", 100, 250), [(6, 3)])
    caster, target = state.units[U1], state.units[U2]
    assert scale_bonus(state, caster, target, None) == 0
    scaling = state.ruleset.skill_def(SID).effects[0].scaling
    assert scale_bonus(state, caster, target, scaling) == 250


def test_the_scaling_bonus_is_floored_in_the_final_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    state = battle(scaled("distance", 85), [(5, 3)])  # 距離 2 → ×1.17
    unscaled = battle(spell(damage("1d6"), rarity="rare"), [(5, 3)])
    script_randint(monkeypatch, [19, 5, 19, 5])
    hit = hit_on_u2(state)
    assert hit.multiplier_permille == 1170
    base = hit_on_u2(unscaled).amount
    assert base < hit.amount <= base * 1170 // 1000 + 1  # 無條件捨去（元素修正的零頭最多差 1）


def test_scaling_adds_to_the_overload_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    scaling = {"by": "distance", "per_step_permille": 100, "cap_permille": 800}
    skill = spell(damage("1d6", scaling=scaling), tags=["overcurrent"], rarity="rare")
    state = battle(skill, [(5, 3)])
    state.units[U1].stacks["overload_surge"] = 1
    script_randint(monkeypatch, [19, 3])
    assert hit_on_u2(state).multiplier_permille == 1000 + 200 + 2 * 100


# ---------------------------------------------------------------------------
# 示範技能與重播
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("build", ["build_gambler", "build_striker", "build_ranged"])
def test_a_battle_with_the_variance_builds_replays_exactly(build: str) -> None:
    from tests.engine.test_zone_ai import _run  # noqa: PLC0415
    from trpg.engine import state_to_json  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _run(build, "open_plain", 3)
    again = replay(setup, 3, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
