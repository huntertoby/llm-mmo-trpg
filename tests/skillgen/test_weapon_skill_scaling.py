"""Phase 3H-6：武器技看手上武器——工坊鎖定、產生器與驗證器的 scaling_attr 是武器大類主屬性。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from tests.skillgen.helpers import skill
from trpg.content.skill_scaling import weapon_class_mismatches
from trpg.shared.types import Attribute
from trpg.skillgen.option_conform import field_problems
from trpg.skillgen.option_models import FieldSpec
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

LIB = library()
RULES = LIB.skill_scaling


def _scaling_field(draft: dict[str, Any]) -> FieldSpec:
    options = draft_options(draft, LIB)
    basics = next(s for s in options.steps if s.id == "basics")
    return next(f for f in basics.fields if f.field == "scaling_attr")


@pytest.mark.parametrize(("req", "attr"), [("melee", "str"), ("ranged", "dex")])
def test_workshop_locks_the_scaling_of_a_weapon_skill(req: str, attr: str) -> None:
    field = _scaling_field({"skeleton": "strike", "category": "weapon", "weapon_req": req})
    assert field.locked
    assert [c.value for c in field.choices] == [attr]
    assert field.default == attr
    assert "手上武器" in field.choices[0].name_zh


def test_the_lock_waits_for_the_weapon_requirement() -> None:
    field = _scaling_field({"skeleton": "strike", "category": "weapon"})
    assert field.locked
    assert field.choices == ()


def test_empty_drafts_keep_the_free_choice() -> None:
    field = _scaling_field({"skeleton": "strike"})
    assert not field.locked
    assert {c.value for c in field.choices} == {a.value for a in Attribute}


def test_a_spell_before_its_effects_does_not_offer_body_attributes() -> None:
    """3-48c：法術技在選效果前不列力量、敏捷、體質，也沒有預設值。"""
    field = _scaling_field({"skeleton": "strike", "category": "spell", "weapon_req": "focus"})
    assert not field.locked
    assert {c.value for c in field.choices} == {"int", "wis", "wil"}
    assert field.default is None


def test_a_stale_value_in_a_locked_field_is_not_reported_as_a_player_mistake() -> None:
    draft = {
        "skeleton": "strike",
        "category": "weapon",
        "weapon_req": "melee",
        "scaling_attr": "int",
    }
    options = draft_options(draft, LIB)
    basics = next(s for s in options.steps if s.id == "basics")
    assert field_problems(basics.fields, draft) == []


def test_the_validator_rejects_a_generated_weapon_skill_with_the_wrong_attribute() -> None:
    good = skill(category="weapon", weapon_req="melee", scaling_attr="str")
    bad = good.model_copy(update={"scaling_attr": Attribute.INT})
    dual = good.model_copy(update={"secondary_scaling_attr": Attribute.DEX, "rarity": "epic"})
    mind = good.model_copy(update={"secondary_scaling_attr": Attribute.INT, "rarity": "epic"})
    generated = {"provenance": good.provenance.model_copy(update={"origin": "level_up"})}
    for skill_def, ok in ((good, True), (bad, False), (dual, True), (mind, True)):
        found = validate_skill(skill_def.model_copy(update=generated), LIB)
        assert ("scaling.weapon" in {v.rule for v in found}) is not ok
    # 第二屬性只能是心智屬性（3I-3）：物理屬性違反 scaling.range，心智屬性沒有任何縮放違規
    rules = {v.rule for v in validate_skill(dual.model_copy(update=generated), LIB)}
    assert "scaling.range" in rules
    rules = {v.rule for v in validate_skill(mind.model_copy(update=generated), LIB)}
    assert not rules & {"scaling.range", "scaling.weapon"}
    # 內建技能（欄位只當顯示提示）與進化而來的技能不檢查
    assert "scaling.weapon" not in {v.rule for v in validate_skill(bad, LIB)}
    evolved = bad.model_copy(
        update={
            "provenance": good.provenance.model_copy(
                update={"origin": "level_up", "parents": ("skill_cleave",)}
            )
        }
    )
    assert "scaling.weapon" not in {v.rule for v in validate_skill(evolved, LIB)}


@pytest.mark.parametrize("seed", range(60))
def test_composed_weapon_skills_use_the_weapon_class_attribute(seed: int) -> None:
    found = compose_random_skill(
        seed, tier=2, rarity="epic", skeleton="strike", category="weapon", library=LIB
    )
    assert found.category == "weapon"
    assert found.scaling_attr is RULES.weapon_class_attr(found.weapon_req)
    assert found.secondary_scaling_attr in (None, *RULES.weapon_second_attrs)  # 3I-3：心智第二屬性
    assert "scaling.weapon" not in {v.rule for v in validate_skill(found, LIB)}


def test_the_class_attributes_are_attributes_of_real_weapons() -> None:
    assert RULES.weapon_class_attr("melee") is Attribute.STR
    assert RULES.weapon_class_attr("ranged") is Attribute.DEX


def test_builtin_weapon_skills_that_disagree_with_their_class_are_only_hints() -> None:
    """內建武器技的 scaling_attr 引擎不再使用；不一致的招只列清單（報告用），不擋載入。"""
    listed = weapon_class_mismatches(RULES, LIB.skills)
    assert listed == sorted(listed)
    assert all(LIB.skills[s].category == "weapon" for s in listed)


def _basics_notes(draft: dict[str, Any]) -> tuple[str, ...]:
    options = draft_options(draft, LIB)
    return next(s for s in options.steps if s.id == "basics").notes_zh


def test_spell_scaling_warns_until_an_effect_is_chosen() -> None:
    """3-47：縮放屬性的範圍看主要效果，效果沒選時基本設定步驟提示（武器技不需要）。"""
    spell = {"skeleton": "strike", "category": "spell"}
    assert any("縮放屬性" in n for n in _basics_notes(spell))
    with_effect = {**spell, "effects": [{"type": "damage"}]}
    assert not any("縮放屬性" in n for n in _basics_notes(with_effect))
    weapon = {"skeleton": "strike", "category": "weapon", "weapon_req": "melee"}
    assert not any("縮放屬性" in n for n in _basics_notes(weapon))
