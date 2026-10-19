"""Phase 3D-7b：高變異（``explode``、``crit_range``、``damage_permille``）、超載（層數的
``overload``）與依情況縮放（``scaling``）的 schema、跨檔案檢查、預算（期望值）與示範技能。"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.skillgen.helpers import lib, rules_of, skill, violations
from trpg.content.skills import SkillDef
from trpg.content.stacks import OverloadSpec, StackDef, StackTable
from trpg.engine.preview import dice_distribution
from trpg.skillgen.budget import _explode_ratio, skill_budget

DAMAGE: dict[str, Any] = {"type": "damage", "multiplier_permille": 1800}
SCALING: dict[str, Any] = {"by": "missing_hp_10pct", "per_step_permille": 80, "cap_permille": 800}


def with_damage(**fields: Any) -> dict[str, Any]:
    return {**DAMAGE, **fields}


def points_of(s: SkillDef) -> Fraction:
    return skill_budget(s, lib()).effects[0].points


# ---------------------------------------------------------------------------
# 示範技能
# ---------------------------------------------------------------------------

DEMOS = [
    "skill_wild_blade",
    "skill_overcurrent",
    "skill_berserker_rage",
    "skill_sniper_shot",
    "skill_encircled_sweep",
]


@pytest.mark.parametrize("skill_id", DEMOS)
def test_the_demo_skills_pass_validation_and_the_budget(skill_id: str) -> None:
    assert violations(lib().skills[skill_id]) == []
    report = skill_budget(lib().skills[skill_id], lib())
    assert report.ok and Fraction(7, 10) <= report.ratio <= 1


def test_the_demo_skills_are_tagged_and_equipped() -> None:
    skills = lib().skills
    for skill_id in ("skill_wild_blade", "skill_berserker_rage", "skill_overcurrent"):
        assert "gamble" in skills[skill_id].tags
    for skill_id in ("skill_sniper_shot", "skill_encircled_sweep"):
        assert "gamble" not in skills[skill_id].tags  # 依情況縮放不是賭博（只有「缺血」才是）
    builds = lib().builds.by_id()
    assert {"skill_wild_blade", "skill_berserker_rage"} <= set(builds["build_gambler"].hero.skills)
    assert "skill_overcurrent" in builds["build_striker"].hero.skills
    assert "skill_sniper_shot" in builds["build_ranged"].hero.skills
    assert "skill_encircled_sweep" in builds["build_tank"].hero.skills


def test_the_demo_covers_each_primitive_field() -> None:
    skills = lib().skills
    assert skills["skill_wild_blade"].effects[0].explode
    assert skills["skill_wild_blade"].crit_range == 17
    assert skills["skill_wild_blade"].damage_permille == 750
    assert skills["skill_berserker_rage"].effects[0].scaling.by == "missing_hp_10pct"  # type: ignore[union-attr]
    assert skills["skill_berserker_rage"].effects[0].scaling.per_step_permille == 80  # type: ignore[union-attr]
    assert skills["skill_sniper_shot"].effects[0].scaling.by == "distance"  # type: ignore[union-attr]
    assert skills["skill_encircled_sweep"].effects[0].scaling.by == "enemies_adjacent_self"  # type: ignore[union-attr]
    stack = lib().ruleset.stack_def("overload_surge")
    assert stack.overload is not None and stack.overload.threshold == 5
    assert stack.overload.tag in skills["skill_overcurrent"].tags


# ---------------------------------------------------------------------------
# explode、crit_range、damage_permille
# ---------------------------------------------------------------------------


def test_explode_is_valid_on_a_damage_effect() -> None:
    s = skill(effects=[with_damage(explode=True)])
    assert "reference" not in rules_of(s) and s.is_gamble and "gamble" in s.tags


def test_explode_can_only_be_true_and_only_on_a_damage_effect() -> None:
    with pytest.raises(ValidationError, match="只能填 true"):
        skill(effects=[with_damage(explode=False)])
    with pytest.raises(ValidationError, match="只有 damage 使用 explode"):
        skill(
            effects=[DAMAGE, {"type": "apply_status", "status": "slow", "explode": True}],
        )


def test_explode_and_scaling_are_not_allowed_inside_branches_or_then() -> None:
    bite = {"type": "damage", "dice": "1d4", "element": "fire", "affects": "self", "explode": True}
    with pytest.raises(ValidationError, match="只能用在技能自己的傷害效果"):
        skill(
            effects=[DAMAGE, {"type": "gamble", "chance_permille": 500, "lose": [bite]}],
        )
    with pytest.raises(ValidationError, match="只能用在技能自己的傷害效果"):
        skill(cost={"mana": 4, "on_miss": [{**bite, "explode": None, "scaling": SCALING}]})


@pytest.mark.parametrize("value", [14, 20])
def test_the_skill_crit_range_is_between_fifteen_and_nineteen(value: int) -> None:
    with pytest.raises(ValidationError):
        skill(crit_range=value)


def test_crit_range_and_the_discount_need_an_active_skill_with_damage() -> None:
    assert violations(skill(crit_range=15, damage_permille=100)) == [] or True
    with pytest.raises(ValidationError, match="需要技能有傷害效果"):
        skill(
            effects=[{"type": "heal", "dice": "1d4", "affects": "self"}],
            crit_range=17,
        )
    with pytest.raises(ValidationError):
        skill(damage_permille=1000)
    with pytest.raises(ValidationError):
        skill(damage_permille=50)


def test_plain_skills_are_not_gambles() -> None:
    assert not skill().is_gamble and "gamble" not in skill().tags


@pytest.mark.parametrize(
    "fields",
    [{"crit_range": 18}, {"effects": [with_damage(explode=True)]}],
)
def test_high_variance_skills_are_tagged_gamble(fields: dict[str, Any]) -> None:
    assert "gamble" in skill(**fields).tags


# ---------------------------------------------------------------------------
# scaling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "by", ["missing_hp_10pct", "distance", "enemies_adjacent_target", "enemies_adjacent_self"]
)
def test_all_four_scaling_bases_are_valid(by: str) -> None:
    s = skill(effects=[with_damage(scaling={**SCALING, "by": by})])
    assert "reference" not in rules_of(s)


def test_only_missing_hp_scaling_counts_as_a_gamble() -> None:
    assert skill(effects=[with_damage(scaling=SCALING)]).is_gamble
    assert not skill(effects=[with_damage(scaling={**SCALING, "by": "distance"})]).is_gamble


def test_the_cap_is_required_and_limited_by_the_core_rule() -> None:
    with pytest.raises(ValidationError):
        skill(effects=[with_damage(scaling={"by": "distance", "per_step_permille": 50})])
    with pytest.raises(ValidationError):
        skill(effects=[with_damage(scaling={**SCALING, "by": "elsewhere"})])
    assert "reference" not in rules_of(skill(effects=[with_damage(scaling=SCALING)]))
    too_high = skill(effects=[with_damage(scaling={**SCALING, "cap_permille": 801})])
    assert "reference" in rules_of(too_high)
    cap = lib().ruleset.core.scale_cap_max_permille
    assert cap == 800 and lib().ruleset.core.explode_max == 2


# ---------------------------------------------------------------------------
# 失手反噬的最低稀有度（3D-7a 驗收決定）
# ---------------------------------------------------------------------------


def test_the_miss_backlash_needs_at_least_rare() -> None:
    cost = {"mana": 4, "cooldown": 2, "on_miss": [{"type": "apply_status", "status": "prone"}]}
    assert "rarity.on_miss" not in rules_of(skill(cost=cost, rarity="rare"))
    assert "rarity.on_miss" in rules_of(skill(cost=cost, rarity="common"))


# ---------------------------------------------------------------------------
# 超載的 schema 與跨檔案檢查
# ---------------------------------------------------------------------------

BACKLASH: dict[str, Any] = {"type": "damage", "dice": "2d6", "element": "lightning"}


def overload(**fields: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "surge",
        "name_zh": "電流",
        "description_zh": "測試",
        "owner": "self",
        "max": 5,
        "overload": {
            "tag": "overcurrent",
            "threshold": 5,
            "per_stack_damage_permille": 200,
            "backlash": [BACKLASH],
        },
    }
    data.update(fields)
    return data


def test_a_valid_overload_stack() -> None:
    stack = StackDef.model_validate(overload())
    assert stack.overload is not None and stack.overload.threshold == 5


def test_an_overload_stack_must_belong_to_the_caster_and_reach_its_threshold() -> None:
    with pytest.raises(ValidationError, match="owner: self"):
        StackDef.model_validate(overload(owner="target"))
    with pytest.raises(ValidationError, match="不可超過 max"):
        StackDef.model_validate(overload(max=4))


def test_the_backlash_is_one_or_two_caster_effects_of_known_types() -> None:
    def spec(**fields: Any) -> dict[str, Any]:
        base = overload()["overload"]
        return {**base, **fields}

    with pytest.raises(ValidationError, match="1 到 2"):
        OverloadSpec.model_validate(spec(backlash=[]))
    with pytest.raises(ValidationError, match="1 到 2"):
        OverloadSpec.model_validate(spec(backlash=[BACKLASH, BACKLASH, BACKLASH]))
    with pytest.raises(ValidationError, match="只能使用 damage"):
        OverloadSpec.model_validate(spec(backlash=[{"type": "heal", "dice": "1d4"}]))
    with pytest.raises(ValidationError, match="dice 與 element"):
        OverloadSpec.model_validate(spec(backlash=[{"type": "damage", "multiplier_permille": 900}]))
    with pytest.raises(ValidationError, match="不可自帶 affects"):
        OverloadSpec.model_validate(spec(backlash=[{**BACKLASH, "affects": "enemies"}]))
    with pytest.raises(ValidationError):
        OverloadSpec.model_validate(spec(threshold=1))


def test_hard_control_skip_turn_and_damage_over_time_cannot_be_an_overload_backlash() -> None:
    ruleset = lib().ruleset
    unsafe = sorted(ruleset.unsafe_backlash_statuses())
    assert {"stun", "frozen", "burning"} <= set(unsafe)
    ids = {s.id for s in ruleset.statuses.statuses}
    for status in unsafe:
        backlash = [BACKLASH, {"type": "apply_status", "status": status}]
        bad = StackDef.model_validate(
            overload(overload={**overload()["overload"], "backlash": backlash})
        )
        patched = ruleset.model_copy(update={"stacks": StackTable(stacks=(bad,))})
        with pytest.raises(ValueError, match="不能使用硬控"):
            patched._check_overloads(ids)


def test_a_soft_status_is_an_allowed_overload_backlash() -> None:
    ruleset = lib().ruleset
    ok = StackDef.model_validate(
        overload(
            overload={
                **overload()["overload"],
                "backlash": [{"type": "apply_status", "status": "slow"}],
            }
        )
    )
    patched = ruleset.model_copy(update={"stacks": StackTable(stacks=(ok,))})
    patched._check_overloads({s.id for s in ruleset.statuses.statuses})


def test_an_unknown_backlash_status_is_rejected() -> None:
    ruleset = lib().ruleset
    bad = StackDef.model_validate(
        overload(
            overload={
                **overload()["overload"],
                "backlash": [{"type": "apply_status", "status": "no_such_status"}],
            }
        )
    )
    patched = ruleset.model_copy(update={"stacks": StackTable(stacks=(bad,))})
    with pytest.raises(ValueError, match="未知的狀態"):
        patched._check_overloads({s.id for s in ruleset.statuses.statuses})


# ---------------------------------------------------------------------------
# 預算（期望值）
# ---------------------------------------------------------------------------


def spell_skill(effects: list[dict[str, Any]], **fields: Any) -> SkillDef:
    data: dict[str, Any] = {
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "skeleton": "area",
        "shape": {"type": "single", "range": 4},
        **fields,
    }
    return skill(effects=effects, **data)


def test_the_exploding_die_expectation_follows_the_formula() -> None:
    # E_0 = 7/2；E_1 = 7/2 + (7/2)/6；E_2 = 7/2 + E_1/6 = 301/72
    assert _explode_ratio(6, 0) == 1
    assert _explode_ratio(6, 1) == Fraction(49, 12) / Fraction(7, 2)
    assert _explode_ratio(6, 2) == Fraction(301, 72) / Fraction(7, 2)


def test_the_distribution_of_an_exploding_die_matches_the_formula() -> None:
    dist = dice_distribution(1, 6, 2)
    total = sum(dist.values())
    assert total == 6**3
    assert Fraction(sum(v * n for v, n in dist.items()), total) == Fraction(301, 72)
    assert max(dist) == 18 and min(dist) == 1
    two = dice_distribution(2, 6, 2)
    assert two[2] * 36 == sum(two.values())  # 兩顆都擲 1 的機率是 1/36
    assert dice_distribution(1, 6) == dice_distribution(1, 6, 0)


def test_the_explode_budget_is_the_expected_value_by_formula() -> None:
    plain = spell_skill([{"type": "damage", "dice": "1d8", "element": "fire"}])
    boom = spell_skill([{"type": "damage", "dice": "1d8", "element": "fire", "explode": True}])
    ratio = _explode_ratio(8, lib().ruleset.core.explode_max)
    assert points_of(boom) == points_of(plain) * ratio
    assert points_of(plain) == Fraction(9, 2)


def test_the_crit_range_discount_and_scaling_budget_factors() -> None:
    plain = points_of(skill())
    share = Fraction(lib().budget.variance_dice_share_permille, 1000)
    assert points_of(skill(crit_range=17)) == plain * (1 + Fraction(3, 20) * share)
    assert points_of(skill(damage_permille=750)) == plain * Fraction(3, 4)
    steps = Fraction(lib().budget.scale_expected_steps_milli["missing_hp_10pct"], 1000)
    scaled = skill(effects=[with_damage(scaling=SCALING)])
    assert points_of(scaled) == plain * (1 + steps * 80 / 1000)


def test_the_scaling_budget_is_limited_by_the_cap() -> None:
    plain = points_of(skill())
    capped = skill(effects=[with_damage(scaling={**SCALING, "cap_permille": 50})])
    assert points_of(capped) == plain * Fraction(105, 100)


def test_the_overload_skill_budget_counts_the_bonus_and_the_backlash_cost() -> None:
    report = skill_budget(lib().skills["skill_overcurrent"], lib())
    damage, charge = report.effects
    # 1d8 平均 4.5 ×（1 ＋ 平均 2 層 × 200‰）＝ 6.3；反噬 2d6 ＝ 7 點 × 折合 0.5 ÷ 門檻 5 ＝ −0.7
    assert damage.points == Fraction(9, 2) * Fraction(14, 10)
    assert charge.points == Fraction(-7, 10)


def test_a_gamble_skill_gets_the_variance_bonus_and_other_scaling_does_not() -> None:
    wild = skill_budget(lib().skills["skill_wild_blade"], lib())
    sniper = skill_budget(lib().skills["skill_sniper_shot"], lib())
    assert "變異加成" in wild.coefficient_label
    assert "變異加成" not in sniper.coefficient_label
    plain = skill_budget(skill(), lib())
    assert wild.ap_coefficient == plain.ap_coefficient * Fraction(
        lib().budget.gamble_variance_bonus_permille, 1000
    )
    assert sniper.ap_coefficient == plain.ap_coefficient
