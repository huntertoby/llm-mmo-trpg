"""Phase 3D-7a：賭注 ``gamble`` 與失手反噬 ``cost.on_miss`` 的 schema、反噬上限、預算與示範技能。"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.skillgen.helpers import lib, rules_of, skill, violations
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import compose_random_skill

DAMAGE: dict[str, Any] = {"type": "damage", "multiplier_permille": 1200}
DOUBLE: dict[str, Any] = {"type": "damage_multiplier", "damage_multiplier_permille": 2000}
HALF_BACK: dict[str, Any] = {"type": "self_damage_of_hit", "self_damage_permille_of_hit": 500}


def gamble(**fields: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": "gamble",
        "chance_permille": 600,
        "win": [DOUBLE],
        "lose": [HALF_BACK],
    }
    data.update(fields)
    return data


def gambler(*effects: dict[str, Any], **overrides: Any) -> SkillDef:
    return skill(effects=list(effects or (DAMAGE, gamble())), **overrides)


# ---------------------------------------------------------------------------
# 示範技能
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", ["skill_blood_sacrifice", "skill_all_in"])
def test_the_demo_gamble_skills_are_valid_and_tagged(skill_id: str) -> None:
    demo = lib().skills[skill_id]
    assert violations(demo) == []
    assert "gamble" in demo.tags and demo.is_gamble  # 自動加標籤（YAML 沒有寫）


def test_the_gamble_tag_is_added_automatically_and_only_to_gamble_skills() -> None:
    assert "gamble" in gambler().tags
    assert (
        "gamble"
        in skill(cost={"mana": 0, "on_miss": [{"type": "apply_status", "status": "prone"}]}).tags
    )
    assert "gamble" not in skill().tags
    tagged = gambler(tags=["gamble", "physical"])
    assert tagged.tags.count("gamble") == 1


# ---------------------------------------------------------------------------
# gamble 的結構
# ---------------------------------------------------------------------------


def test_a_well_formed_gamble_is_valid() -> None:
    assert not [v for v in violations(gambler()) if v.rule == "reference"]


def test_the_gamble_must_be_the_last_effect_and_unique() -> None:
    with pytest.raises(ValidationError, match="最後一個效果"):
        gambler(gamble(), DAMAGE)
    with pytest.raises(ValidationError, match="最多一個 gamble"):
        gambler(DAMAGE, gamble(), gamble())


@pytest.mark.parametrize("chance", [0, 1000, 1500])
def test_chance_permille_must_be_between_zero_and_one_thousand(chance: int) -> None:
    with pytest.raises(ValidationError):
        gambler(DAMAGE, gamble(chance_permille=chance))


def test_chance_permille_is_limited_to_the_primitive_range() -> None:
    assert "reference" in rules_of(gambler(DAMAGE, gamble(chance_permille=20)))
    assert "reference" in rules_of(gambler(DAMAGE, gamble(chance_permille=980)))
    assert "reference" not in rules_of(gambler(DAMAGE, gamble(chance_permille=950)))


def test_the_gamble_needs_a_chance_and_at_least_one_branch() -> None:
    with pytest.raises(ValidationError, match="必須填 chance_permille"):
        gambler(DAMAGE, {"type": "gamble", "win": [DOUBLE]})
    with pytest.raises(ValidationError, match="至少要有一邊有效果"):
        gambler(DAMAGE, {"type": "gamble", "chance_permille": 500})


def test_each_branch_has_at_most_two_effects_of_the_allowed_types() -> None:
    heal = {"type": "heal", "dice": "1d4", "affects": "self"}
    with pytest.raises(ValidationError, match="1 到 2 個"):
        gambler(DAMAGE, gamble(win=[DOUBLE, HALF_BACK, heal]))
    with pytest.raises(ValidationError, match="只能使用"):
        gambler(DAMAGE, gamble(win=[{"type": "push", "distance": 1}]))
    with pytest.raises(ValidationError, match="不可自帶 condition"):
        gambler(
            DAMAGE,
            gamble(win=[{**heal, "condition": {"type": "first_round"}}]),
        )
    with pytest.raises(ValidationError, match="只能出現在 gamble 的分支裡"):
        gambler(DAMAGE, DOUBLE)
    with pytest.raises(ValidationError, match="只有 gamble 使用"):
        gambler({**DAMAGE, "chance_permille": 500}, gamble())


def test_multiplier_and_self_damage_need_a_damage_effect_and_their_value() -> None:
    heal = {"type": "heal", "dice": "1d4", "affects": "self"}
    with pytest.raises(ValidationError, match="技能必須有傷害效果"):
        gambler(heal, gamble(win=[DOUBLE]))
    with pytest.raises(ValidationError, match="damage_multiplier_permille"):
        gambler(DAMAGE, gamble(win=[{"type": "damage_multiplier"}]))
    with pytest.raises(ValidationError, match="不等於 1000"):
        gambler(
            DAMAGE,
            gamble(win=[{"type": "damage_multiplier", "damage_multiplier_permille": 1000}]),
        )
    with pytest.raises(ValidationError, match="self_damage_permille_of_hit"):
        gambler(DAMAGE, gamble(lose=[{"type": "self_damage_of_hit"}]))
    with pytest.raises(ValidationError, match="每個分支最多一個"):
        gambler(DAMAGE, gamble(win=[DOUBLE, DOUBLE]))


def test_a_branch_may_not_target_enemies_without_a_hit_roll() -> None:
    bite = {"type": "apply_status", "status": "slow", "affects": "enemies"}
    heal = {"type": "heal", "dice": "1d4", "affects": "self"}
    assert "reference" not in rules_of(gambler(DAMAGE, gamble(win=[bite])))
    assert "reference" in rules_of(gambler(heal, gamble(win=[bite], lose=[heal])))


def test_gamble_and_miss_backlash_are_active_skill_only() -> None:
    with pytest.raises(ValidationError, match=r"只有主動技能可以有 cost\.on_miss"):
        skill(
            kind="stance",
            ap_cost=None,
            shape={"type": "self"},
            effects=[{"type": "apply_status", "status": "stance_fury", "affects": "self"}],
            cost={"mana": 0, "on_miss": [{"type": "apply_status", "status": "prone"}]},
        )


# ---------------------------------------------------------------------------
# 反噬上限（schema 檢查）
# ---------------------------------------------------------------------------

HARD_CONTROL = ["stun", "frozen"]


@pytest.mark.parametrize("status", [*HARD_CONTROL, "burning", "poison", "bleed"])
def test_hard_control_and_damage_over_time_cannot_be_a_backlash(status: str) -> None:
    on_miss = skill(cost={"mana": 0, "on_miss": [{"type": "apply_status", "status": status}]})
    messages = [v.message for v in violations(on_miss) if v.rule == "reference"]
    assert any("反噬不能使用硬控、跳過回合或持續傷害的狀態" in m for m in messages)
    lose = gambler(
        DAMAGE,
        gamble(lose=[{"type": "apply_status", "status": status, "affects": "self"}]),
    )
    messages = [v.message for v in violations(lose) if v.rule == "reference"]
    assert any("反噬不能使用硬控" in m for m in messages)


@pytest.mark.parametrize("status", ["prone", "slow", "vulnerable", "weaken", "root"])
def test_soft_statuses_are_allowed_as_a_backlash(status: str) -> None:
    on_miss = skill(cost={"mana": 0, "on_miss": [{"type": "apply_status", "status": status}]})
    assert not [v for v in violations(on_miss) if v.rule == "reference"]


def test_a_hard_control_on_the_enemy_in_a_branch_is_fine() -> None:
    stun = {"type": "apply_status", "status": "stun", "affects": "enemies"}
    assert not [v for v in violations(gambler(DAMAGE, gamble(win=[stun]))) if v.rule == "reference"]


def test_the_unsafe_status_set_is_derived_from_the_status_table() -> None:
    unsafe = lib().ruleset.unsafe_backlash_statuses()
    assert {"stun", "frozen", "burning", "poison", "bleed"} <= unsafe
    assert not unsafe & {"prone", "slow", "vulnerable", "defending"}


def test_miss_backlash_is_limited_to_two_effects_on_the_caster() -> None:
    prone = {"type": "apply_status", "status": "prone"}
    with pytest.raises(ValidationError, match="1 到 2 個"):
        skill(cost={"mana": 0, "on_miss": [prone, prone, prone]})
    with pytest.raises(ValidationError, match="只能是施放者"):
        skill(cost={"mana": 0, "on_miss": [{**prone, "affects": "enemies"}]})
    with pytest.raises(ValidationError, match="只能使用"):
        skill(cost={"mana": 0, "on_miss": [{"type": "heal", "dice": "1d4"}]})


# ---------------------------------------------------------------------------
# 預算：期望值計、變異加成
# ---------------------------------------------------------------------------


def test_the_gamble_budget_is_the_expected_value_of_its_branches() -> None:
    report = skill_budget(lib().skills["skill_blood_sacrifice"], lib())
    damage, gamble_row = report.effects
    multiplier = lib().skills["skill_blood_sacrifice"].effects[0].multiplier_permille
    assert multiplier is not None
    assert damage.points == Fraction(multiplier, 1000) * 7  # 武器倍率（讀 content）× 基準 7
    # 60% × win（傷害 ×2 → +100% 傷害）＋ 40% × lose（自傷 50% × 折合 500‰ 的代價）
    expected = Fraction(6, 10) * damage.points - Fraction(4, 10) * damage.points / 2 / 2
    assert gamble_row.points == expected


def test_a_gamble_skill_gets_the_variance_bonus_on_its_usable_budget() -> None:
    plain = skill(effects=[DAMAGE])
    risky = gambler()
    bonus = Fraction(lib().budget.gamble_variance_bonus_permille, 1000)
    assert lib().budget.gamble_variance_bonus_permille == 1100
    assert (
        skill_budget(risky, lib()).ap_coefficient
        == skill_budget(plain, lib()).ap_coefficient * bonus
    )
    assert "變異加成" in skill_budget(risky, lib()).coefficient_label
    assert "變異加成" not in skill_budget(plain, lib()).coefficient_label


def test_self_harm_in_the_lose_branch_is_a_discounted_cost() -> None:
    with_harm = skill(effects=[DAMAGE, gamble(win=[DOUBLE], lose=[HALF_BACK])])
    only_win = skill(effects=[DAMAGE, gamble(win=[DOUBLE], lose=[])])
    lose_row = skill_budget(with_harm, lib()).effects[1].points
    win_row = skill_budget(only_win, lib()).effects[1].points
    assert lose_row < win_row  # 失敗分支的自傷以負點數計入（折合 500‰）
    assert win_row - lose_row == Fraction(4, 10) * Fraction(42, 5) / 2 / 2


def test_miss_backlash_is_a_discounted_negative_cost_row() -> None:
    risky = skill(
        cost={"mana": 4, "cooldown": 2, "on_miss": [{"type": "apply_status", "status": "prone"}]}
    )
    report = skill_budget(risky, lib())
    row = report.effects[-1]
    assert row.type == "cost.on_miss" and row.points < 0
    # 倒地 3 點 × 自傷折合 500‰ × 觸發率 300‰
    assert row.points == -Fraction(3) * Fraction(500, 1000) * Fraction(300, 1000)
    assert report.raw == skill_budget(skill(), lib()).raw + row.points


def test_the_gamble_primitive_is_composed_randomly_with_a_valid_structure() -> None:
    # 3C-6b：組合器能產生賭博型（成功率是強度旋鈕；gamble 一定是最後一個效果）
    composed = [
        compose_random_skill(seed, tier=2, rarity="epic", skeleton="strike") for seed in range(120)
    ]
    gambles = [s for s in composed if s.is_gamble]
    assert gambles
    for gamble in gambles:
        assert gamble.effects[-1].type == "gamble"
        assert any(e.type == "damage" for e in gamble.effects)
