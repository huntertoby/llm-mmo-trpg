"""傳說核心三擇一與常駐類傳說的 ``activation``（Phase 3D-6，``Phase3D計畫.md`` 0.1、6）。

- 核心：改寫規則型原語、修正規則、規則改變（``rule_change``）恰好一種。
- ``activation: timed | battle``：修正型與規則改變型傳說必填，其他技能不可填；整場型預算 × 600‰。
- ``content/rule_changes.yaml`` 的 schema、引用與每人最多裝 1 個規則改變。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.library import Ruleset
from trpg.content.rule_changes import RULE_CHANGE_KINDS, RuleChangeDef, RuleChangeTable
from trpg.content.skills import SkillDef, legendary_cores, skill_problems, skill_slot_problems
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.validate import validate_skill

RULE = {"type": "rule_change", "rule": "move_any_object", "affects": "self"}
GRANT = {"type": "grant_ap", "amount": 2, "affects": "self"}
MODIFIER = {"applies_to": {"all_attacks": True}, "change": {"damage_permille": 180}}
RULE_CHANGE_SKILLS = (
    "skill_kindred_flame",
    "skill_mountain_mover",
    "skill_bloodwake_stride",
    "skill_afterimage_vow",
)


def _rule_change(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "skill_t_rule_change",
        "name_zh": "測試規則改變",
        "tier": 1,
        "rarity": "legendary",
        "skeleton": "aura",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": 1,
        "scaling_attr": "str",
        "shape": {"type": "self"},
        "effects": [RULE],
        "activation": "timed",
        "cost": {"source": 1},
    }
    data.update(over)
    return data


def _modifier(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "skill_t_lasting_mod",
        "name_zh": "測試修正型傳說",
        "tier": 1,
        "rarity": "legendary",
        "kind": "modifier",
        "skeleton": "modifier",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": "str",
        "shape": {"type": "self"},
        "effects": [],
        "modifiers": [MODIFIER],
        "activation": "timed",
        "cost": {"source": 1},
    }
    data.update(over)
    return data


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
        rule_change_ids=set(rules.rule_changes.by_id()),
    )


# ---------------------------------------------------------------------------
# 核心三擇一
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("skill_id", "core"),
    [
        ("skill_time_surge", "rule_rewrite"),
        ("skill_war_avatar", "modifier"),
        ("skill_kindred_flame", "rule_change"),
    ],
)
def test_each_of_the_three_cores_makes_a_valid_legendary(skill_id: str, core: str) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    assert legendary_cores(skill, lib.ruleset.primitives.by_id()) == [core]
    assert validate_skill(skill, lib) == []


def test_a_legendary_with_two_cores_is_rejected() -> None:
    two = SkillDef.model_validate(
        _rule_change(
            effects=[GRANT, {"type": "cheat_death", "duration": 1, "affects": "self"}],
            activation=None,
            cost={"source": 1, "cooldown": 2},
        )
    )
    (problem,) = _problems(two)
    assert problem.endswith("收到 rule_rewrite、rule_rewrite")


def test_a_rule_change_must_be_the_only_effect_on_a_self_shaped_active_legendary() -> None:
    with pytest.raises(ValidationError, match="rule_change 必須是技能唯一的效果"):
        SkillDef.model_validate(_rule_change(effects=[RULE, GRANT]))
    with pytest.raises(ValidationError, match="rule_change 技能的形狀必須是 self"):
        SkillDef.model_validate(_rule_change(shape={"type": "single", "range": 3}))
    with pytest.raises(ValidationError, match="rule_change 只能用在傳說技能"):
        SkillDef.model_validate(_rule_change(rarity="epic", cost={}, activation=None))


def test_an_unknown_rule_change_is_a_reference_problem() -> None:
    skill = SkillDef.model_validate(_rule_change(effects=[{**RULE, "rule": "no_such_rule"}]))
    assert _problems(skill) == ["effects[0].rule：未知的規則改變 'no_such_rule'"]


# ---------------------------------------------------------------------------
# activation
# ---------------------------------------------------------------------------


def test_lasting_legendaries_must_declare_an_activation() -> None:
    with pytest.raises(ValidationError, match="必須寫 activation"):
        SkillDef.model_validate(_rule_change(activation=None))
    with pytest.raises(ValidationError, match="必須寫 activation"):
        SkillDef.model_validate(_modifier(activation=None))


def test_other_skills_cannot_declare_an_activation() -> None:
    rewrite = _rule_change(effects=[GRANT], cost={"source": 1, "cooldown": 2})
    with pytest.raises(ValidationError, match="只有修正型與規則改變型傳說可以寫 activation"):
        SkillDef.model_validate(rewrite)
    epic = _modifier(rarity="epic", cost={})
    with pytest.raises(ValidationError, match="只有修正型與規則改變型傳說可以寫 activation"):
        SkillDef.model_validate(epic)


def test_a_modifier_legendary_can_only_cost_source_and_cooldown() -> None:
    SkillDef.model_validate(_modifier(cost={"source": 2, "cooldown": 3}))
    with pytest.raises(ValidationError, match="修正型傳說的代價只能有源力與冷卻"):
        SkillDef.model_validate(_modifier(cost={"source": 1, "mana": 5}))
    with pytest.raises(ValidationError, match=r"傳說技能必須有 cost\.source"):
        SkillDef.model_validate(_modifier(cost={}))


def test_a_modifier_legendary_is_written_and_activated_from_the_skill_bar() -> None:
    skill = SkillDef.model_validate(_modifier())
    assert skill.is_modifier and skill.is_activatable and skill.is_actionable
    assert _problems(skill) == []
    assert validate_skill(skill, library()) == []
    epic = SkillDef.model_validate(_modifier(rarity="epic", cost={}, activation=None))
    assert not epic.is_actionable  # 一般修正技能仍然不能「施放」


def test_battle_activation_scales_the_usable_budget_by_600_permille() -> None:
    lib = library()
    assert lib.budget.legendary_battle_budget_permille == 600
    assert lib.ruleset.core.legendary_timed_rounds == 3
    timed = skill_budget(SkillDef.model_validate(_rule_change(activation="timed")), lib)
    battle = skill_budget(SkillDef.model_validate(_rule_change(activation="battle")), lib)
    assert timed.total == battle.total == 7  # 規則改變 push_any_object 的點數
    assert battle.usable * 1000 == timed.usable * 600
    assert timed.coefficient_label == "啟動 AP 1 係數（限時）"
    assert battle.coefficient_label == "啟動 AP 1 係數 × 整場 600‰"
    # 修正型傳說也一樣（係數改用啟動 AP 的 AP 係數）
    mod_timed = skill_budget(SkillDef.model_validate(_modifier()), lib)
    mod_battle = skill_budget(SkillDef.model_validate(_modifier(activation="battle")), lib)
    assert mod_battle.usable * 1000 == mod_timed.usable * 600


def test_the_demo_lasting_legendaries_cover_both_activations_and_every_rule_kind() -> None:
    lib = library()
    equipped = {s for b in lib.builds.builds for s in b.hero.skills}
    kinds = set()
    for skill_id in (*RULE_CHANGE_SKILLS, "skill_war_avatar"):
        skill = lib.skills[skill_id]
        assert validate_skill(skill, lib) == [], skill_id
        assert skill_budget(skill, lib).ok, skill_id
        assert skill_id in equipped, skill_id
        if skill.rule_change_id is not None:
            kinds.add(lib.ruleset.rule_change_def(skill.rule_change_id).kind)
    assert kinds == set(RULE_CHANGE_KINDS)
    activations = {lib.skills[s].activation for s in (*RULE_CHANGE_SKILLS, "skill_war_avatar")}
    assert activations == {"timed", "battle"}


# ---------------------------------------------------------------------------
# rule_changes.yaml 與裝備
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"kind": "element_heals_allies", "element": "fire"}, "缺少參數：permille"),
        ({"kind": "push_any_object", "status": "bleed"}, "不接受參數：status"),
        ({"kind": "pass_through_apply", "status": "bleed"}, "缺少參數：duration"),
        ({"kind": "on_downed_spawn", "unit": "summon_afterimage", "duration": 4}, "duration"),
        ({"kind": "element_heals_allies", "element": "physical", "permille": 500}, "物理"),
        ({"kind": "teleport_everyone"}, "kind"),
    ],
)
def test_rule_change_params_are_checked_per_kind(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        RuleChangeDef.model_validate({"id": "rule_t", "name_zh": "測試", **data})


def test_rule_change_references_and_kind_points_are_checked() -> None:
    rules = library().ruleset
    bad_status = RuleChangeDef(
        id="rule_t", name_zh="測試", kind="pass_through_apply", status="nope", duration=1
    )
    table = RuleChangeTable(kinds=rules.rule_changes.kinds, rule_changes=(bad_status,))
    with pytest.raises(ValidationError, match="未知的狀態：nope"):
        Ruleset.model_validate({**dict(rules), "rule_changes": table})
    bad_unit = RuleChangeDef(
        id="rule_t", name_zh="測試", kind="on_downed_spawn", unit="nobody", duration=1
    )
    table = RuleChangeTable(kinds=rules.rule_changes.kinds, rule_changes=(bad_unit,))
    with pytest.raises(ValidationError, match="未知的召喚物範本：nobody"):
        Ruleset.model_validate({**dict(rules), "rule_changes": table})
    with pytest.raises(ValidationError, match="kinds 缺少"):
        RuleChangeTable(kinds={}, rule_changes=(bad_unit,))


def test_each_unit_equips_at_most_one_rule_change_legendary() -> None:
    lib = library()
    slots = lib.ruleset.core.skill_slots
    one = [lib.skills["skill_kindred_flame"], lib.skills["skill_war_avatar"]]
    assert skill_slot_problems(one, slots) == []
    two = [lib.skills["skill_kindred_flame"], lib.skills["skill_mountain_mover"]]
    assert skill_slot_problems(two, slots) == [
        "規則改變型傳說每人最多裝 1 個，收到 2 個：慈焰誓約、移山之力"
    ]
