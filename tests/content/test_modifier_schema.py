"""Phase 3C-2：修正規則（``kind: modifier``）的 schema、跨檔案檢查、驗證、預算與描述。"""

from __future__ import annotations

import io
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.cli.budget import print_skill_budget
from trpg.content.skills import MODIFIER_CHANGES, SkillDef, skill_problems
from trpg.narrative.skills import modifier_summary, skill_card
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

DEMOS = ("skill_searing_scar", "skill_thunder_hand", "skill_heavy_stomp", "skill_ember_cycle")


def data(*rules: dict[str, Any], **fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "skill_t_mod",
        "name_zh": "測試修正",
        "tier": 1,
        "rarity": "epic",
        "kind": "modifier",
        "skeleton": "modifier",
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": "int",
        "shape": {"type": "self"},
        "effects": [],
        "modifiers": list(rules),
    }
    return {**base, **fields}


def rule(applies_to: dict[str, Any], change: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"applies_to": applies_to, "change": change, **extra}


ATTACKS = {"all_attacks": True}
SKILLS = {"all_skills": True}

VALID_CHANGES: dict[str, dict[str, Any]] = {
    "damage_permille": rule(ATTACKS, {"damage_permille": 100}),
    "hit_bonus": rule({"actions": ["attack"]}, {"hit_bonus": 1}),
    "cooldown_delta": rule(SKILLS, {"cooldown_delta": -1}),
    "push_distance_delta": rule(
        {"actions": ["shove"], "skill_tags": ["push"]}, {"push_distance_delta": 1}
    ),
    "ap_delta": rule({"actions": ["shove", "trip", "interact"]}, {"ap_delta": 1}),
    "range_delta": rule(ATTACKS, {"range_delta": 1}),
    "add_element": rule({"actions": ["attack"]}, {"add_element": "lightning"}),
    "add_tags": rule({"skill_tags": ["push"]}, {"add_tags": ["fire"]}),
    "on_hit_effects": rule(
        ATTACKS, {"on_hit_effects": [{"type": "apply_status", "status": "burning", "duration": 2}]}
    ),
    "grant_pierce": rule({"skill_tags": ["ranged"]}, {"grant_pierce": True}),
    "area_delta": rule({"skill_tags": ["fire"]}, {"area_delta": 1}),
    "shape_to": rule({"skill_tags": ["fire"]}, {"shape_to": "line"}),
    "allow_self_target": rule({"skill_tags": ["heal"]}, {"allow_self_target": True}),
}


def test_every_change_kind_has_a_valid_example() -> None:
    assert set(VALID_CHANGES) == set(MODIFIER_CHANGES)
    for kind, spec in VALID_CHANGES.items():
        skill = SkillDef.model_validate(data(spec))
        assert skill.modifiers[0].change.kind == kind
        assert skill.is_modifier and not skill.is_actionable


@pytest.mark.parametrize(
    ("rules", "fields", "message"),
    [
        ([rule({}, {"hit_bonus": 1})], {}, "applies_to 至少要有一項"),
        ([rule({"actions": ["attack", "attack"]}, {"hit_bonus": 1})], {}, "不可重複"),
        ([rule({"skill_tags": ["Fire"]}, {"hit_bonus": 1})], {}, "snake_case"),
        ([rule(ATTACKS, {"hit_bonus": 1, "damage_permille": 100})], {}, "恰好一種"),
        ([rule(ATTACKS, {})], {}, "恰好一種"),
        ([rule(ATTACKS, {"damage_permille": 0})], {}, "不可為 0"),
        ([rule(ATTACKS, {"damage_permille": 1500})], {}, "less than or equal"),
        ([rule(ATTACKS, {"add_element": "physical"})], {}, "不可是物理"),
        ([rule(SKILLS, {"cooldown_delta": 1})], {}, "less than or equal"),
        ([rule(SKILLS, {"add_tags": []})], {}, "1 到 3 個"),
        ([rule({"actions": ["attack"]}, {"cooldown_delta": -1})], {}, "不能套用在 attack"),
        ([rule({"actions": ["shove"]}, {"damage_permille": 100})], {}, "不能套用在 shove"),
        ([rule({"actions": ["attack"]}, {"push_distance_delta": 1})], {}, "不能套用在 attack"),
        ([rule({"actions": ["trip"]}, {"add_tags": ["fire"]})], {}, "不能套用在 trip"),
        (
            [
                rule(
                    ATTACKS,
                    {"range_delta": 1},
                    condition={"type": "target_has_status", "status": "burning"},
                )
            ],
            {},
            "條件只能是 self_hp_below",
        ),
        (
            [rule(ATTACKS, {"on_hit_effects": [{"type": "teleport"}]})],
            {},
            "不能當命中後效果",
        ),
        (
            [rule(ATTACKS, {"on_hit_effects": [{"type": "apply_status", "status": "slow"}] * 3})],
            {},
            "1 到 2 個效果",
        ),
        (
            [rule(ATTACKS, {"on_hit_effects": [{"type": "damage", "dice": "1d4"}]})],
            {},
            "法術技的傷害必須指定 dice 與 element",
        ),
        # 3D-3：技能變形（area_delta、shape_to、allow_self_target）
        ([rule(SKILLS, {"area_delta": 2})], {}, "less than or equal"),
        ([rule(SKILLS, {"area_delta": 0})], {}, "greater than or equal"),
        ([rule({"actions": ["attack"]}, {"area_delta": 1})], {}, "不能套用在 attack"),
        ([rule({"actions": ["shove"]}, {"shape_to": "line"})], {}, "不能套用在 shove"),
        ([rule(ATTACKS, {"allow_self_target": True})], {}, "不能套用在 all_attacks"),
        ([rule(SKILLS, {"allow_self_target": False})], {}, "只能是 true"),
        ([rule(SKILLS, {"shape_to": "ring"})], {}, "shape_to"),  # 不允許的形狀轉換
        ([rule(SKILLS, {"shape_to": "single"})], {}, "shape_to"),
        ([rule(SKILLS, {"area_delta": 1, "shape_to": "line"})], {}, "恰好一種"),
        (
            [
                rule(
                    SKILLS,
                    {"area_delta": 1},
                    condition={"type": "target_has_status", "status": "burning"},
                )
            ],
            {},
            "條件只能是 self_hp_below",
        ),
        ([], {}, "1 到 2 條"),
        ([VALID_CHANGES["hit_bonus"]] * 3, {}, "1 到 2 條"),
        (
            [VALID_CHANGES["hit_bonus"]],
            {"effects": [{"type": "heal", "dice": "1d4"}]},
            "effects 必須為空",
        ),
        ([VALID_CHANGES["hit_bonus"]], {"shape": {"type": "single", "range": 1}}, "只能是 self"),
        ([VALID_CHANGES["hit_bonus"]], {"cost": {"mana": 2}}, "不能有代價"),
        (
            [VALID_CHANGES["hit_bonus"]],
            {"condition": {"type": "self_hp_below", "permille": 500}},
            "技能層級的 condition",
        ),
        ([VALID_CHANGES["hit_bonus"]], {"ap_cost": 1}, "ap_cost 必須為 null"),
        (
            [VALID_CHANGES["hit_bonus"]],
            {"trigger": {"event": "on_hit"}},
            "只有被動技能可以有 trigger",
        ),
    ],
)
def test_invalid_modifier_skills_are_rejected(
    rules: list[dict[str, Any]], fields: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(data(*rules, **fields))


def test_only_modifier_skills_may_have_modifiers() -> None:
    active = library().skills["skill_fire_bolt"].model_dump(mode="json")
    active["modifiers"] = [VALID_CHANGES["hit_bonus"]]
    with pytest.raises(ValidationError, match="只有修正技能"):
        SkillDef.model_validate(active)


def test_self_hp_condition_is_allowed_on_pre_target_changes() -> None:
    spec = rule(ATTACKS, {"range_delta": 1}, condition={"type": "self_hp_below", "permille": 500})
    assert SkillDef.model_validate(data(spec)).modifiers[0].condition is not None


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


def test_cross_file_checks_cover_rule_conditions_and_on_hit_effects() -> None:
    bad_condition = rule(
        ATTACKS, {"hit_bonus": 1}, condition={"type": "target_has_status", "status": "nope"}
    )
    bad_status = rule(ATTACKS, {"on_hit_effects": [{"type": "apply_status", "status": "nope"}]})
    problems = _problems(SkillDef.model_validate(data(bad_condition, bad_status)))
    assert any(p.startswith("modifiers[0].condition") and "nope" in p for p in problems)
    assert any(p.startswith("modifiers[1].change.on_hit_effects[0]") for p in problems)
    for spec in VALID_CHANGES.values():
        assert _problems(SkillDef.model_validate(data(spec))) == []


def test_modifier_skills_need_epic_rarity_and_pass_validation() -> None:
    lib = library()
    rare = SkillDef.model_validate(data(VALID_CHANGES["damage_permille"], rarity="rare"))
    assert "rarity.skeleton" in {v.rule for v in validate_skill(rare, lib)}
    for skill_id in DEMOS:
        skill = lib.skills[skill_id]
        assert skill.kind == "modifier" and skill.rarity == "epic"
        assert validate_skill(skill, lib) == []


def test_demo_modifier_budgets_use_uses_times_value() -> None:
    lib = library()
    expected = {  # 使用次數 ×（命中率 0.6）× 每次價值 × 條件倍率
        "skill_searing_scar": 10 * 0.6 * 0.7 * 0.85,
        "skill_thunder_hand": 6 * 0.6 * 1.0,
        "skill_heavy_stomp": 5 * 0.6 * 2 + 5 * -0.5,
        "skill_ember_cycle": 6 * 0.6 * 1.2 * 0.85,
    }
    for skill_id, total in expected.items():
        report = skill_budget(lib.skills[skill_id], lib)
        assert float(report.total) == pytest.approx(total)
        assert float(report.usable) == pytest.approx(14 * 0.3)
        assert report.ok and report.coefficient_label == "修正係數"


def test_budget_cli_shows_modifier_rule_points() -> None:
    lib = library()
    out = io.StringIO()
    assert print_skill_budget(lib, lib.skills["skill_heavy_stomp"], out) == 0
    text = out.getvalue()
    assert "修正（被動欄位，不花 AP）" in text
    assert "規則點數" in text and "modifier.push_distance_delta" in text
    assert "修正係數" in text and "驗證：通過" in text


def test_modifier_descriptions_are_in_chinese_and_on_the_skill_card() -> None:
    lib = library()
    scar = lib.skills["skill_searing_scar"]
    text = modifier_summary(lib, scar, scar.modifiers[0])
    assert text == "你的所有攻擊（普攻與攻擊技能）：傷害 +10%，若目標帶有狀態「燃燒」"
    stomp = lib.skills["skill_heavy_stomp"]
    card = skill_card(lib, stomp)
    assert card.kind == "修正" and card.effects == ()
    assert card.modifiers == (
        "推擊、帶標籤 push 的技能：推擊與拉扯距離 +1 格（最多 2 格，超過的每格改為一次撞擊傷害）",
        "推擊、帶標籤 push 的技能：AP +1（最少 1）",
    )
    assert skill_card(lib, lib.skills["skill_fire_bolt"]).modifiers == ()
