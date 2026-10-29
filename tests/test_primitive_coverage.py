"""效果原語的對應檢查（Phase 3E-2b）：解譯器、預算、AI 估值、敘事、預覽。"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from trpg.content.battle import Dice
from trpg.content.form_text import form_effect_lines, form_entry_lines
from trpg.content.forms import EntryBurst, EntryHealAdjacent, FormEffects, FormEntry, TakenMod
from trpg.content.library import load_library
from trpg.content.modifier_changes import (
    ModifierChangeDef,
    ModifierChangeTable,
    modifier_change_problems,
)
from trpg.content.races import RACE_EFFECT_SPECS
from trpg.content.skills import ModifierChange, PrimitiveDef
from trpg.engine.ai.coverage import PRIMITIVE_VALUATION
from trpg.engine.forms import FORM_EFFECT_CONSUMERS, FORM_ENTRY_CONSUMERS
from trpg.engine.modifiers import CHANGE_HANDLERS
from trpg.engine.preview import PRIMITIVE_PREVIEW
from trpg.engine.race.skills import RACE_EFFECT_EXECUTORS
from trpg.engine.skills.primitives import PRIMITIVE_HANDLERS, primitive_handler
from trpg.narrative.skills import DESCRIBED_CHANGES, DESCRIBED_PRIMITIVES
from trpg.primitive_coverage import (
    change_coverage_problems,
    check_primitive_coverage,
    coverage_problems,
    form_coverage_problems,
    knob_problems,
    load_checked_library,
    race_coverage_problems,
    race_lead_problems,
)
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute, Element
from trpg.skillgen.budget import STRUCTURED_CHANGES

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_FROST_NOVA = """
  - id: frost_nova
    name_zh: 霜爆
    description_zh: 測試用的新原語（沒有任何對應項）。
    category: numeric
    harmful: true
    budget_basis: fixed
    base_points: 3
"""


def _fake(primitive_id: str, basis: str | None = "fixed") -> PrimitiveDef:
    return PrimitiveDef.model_validate(
        {
            "id": primitive_id,
            "name_zh": "測試",
            "description_zh": "測試",
            "category": "numeric",
            "harmful": True,
            "budget_basis": basis,
            "base_points": 1,
        }
    )


def test_real_content_is_fully_covered() -> None:
    library = load_library()
    check_primitive_coverage(library)  # 不拋出
    ids = set(library.ruleset.primitives.by_id())
    # 對應表與 YAML 完全一致（沒有漏掉，也沒有過時的多餘項）
    assert set(PRIMITIVE_HANDLERS) == ids
    assert set(PRIMITIVE_VALUATION) == ids
    assert set(PRIMITIVE_PREVIEW) == ids
    assert ids == DESCRIBED_PRIMITIVES


def test_new_primitive_without_entries_lists_every_missing_place() -> None:
    library = load_library()
    primitives = (*library.ruleset.primitives.primitives, _fake("frost_nova"))
    problems = coverage_problems(primitives)
    assert problems == [
        "原語 frost_nova 沒有解譯器的對應項（請補 trpg.engine.skills.primitives 的 HANDLERS）",
        "原語 frost_nova 沒有AI 估值的對應項（請補 trpg.engine.ai.coverage.PRIMITIVE_VALUATION）",
        "原語 frost_nova 沒有敘事的對應項（請補 trpg.narrative.skills 的 _EFFECT_TEXT）",
        "原語 frost_nova 沒有預覽的對應項（請補 trpg.engine.preview.PRIMITIVE_PREVIEW）",
    ]


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        (None, "原語 frost_nova 沒有預算算法（budget_basis）"),
        ("fixed", None),
    ],
)
def test_budget_basis_must_be_implemented(basis: str | None, expected: str | None) -> None:
    problems = coverage_problems([_fake("frost_nova", basis)], tables=())
    assert problems == ([] if expected is None else [expected])


def test_unimplemented_budget_basis_is_reported() -> None:
    problems = coverage_problems([_fake("frost_nova")], tables=(), budget_bases=frozenset())
    assert problems == ["原語 frost_nova 的預算算法 fixed 沒有實作（請補 trpg.skillgen.budget）"]


def test_extra_table_entries_are_not_problems() -> None:
    """測試或模組用的內容資料夾刪掉某個原語時，對應表多出的項不算錯。"""
    assert coverage_problems([_fake("heal")], tables=(("解譯器", "x", {"heal", "damage"}),)) == []


def test_load_checked_library_raises_content_error(tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", content)
    yaml_path = content / "skill_primitives.yaml"
    yaml_path.write_text(yaml_path.read_text(encoding="utf-8") + _FROST_NOVA, encoding="utf-8")
    load_library(content)  # 內容本身合法
    with pytest.raises(ContentError) as caught:
        load_checked_library(content)
    assert caught.value.path == yaml_path
    assert "原語 frost_nova 沒有解譯器的對應項" in caught.value.reason


def test_interpreter_has_no_default_branch() -> None:
    """登錄表沒有的原語不會靜默略過（舊的 ``tile_effect`` 沒有 else）。"""
    with pytest.raises(KeyError, match="frost_nova"):
        primitive_handler("frost_nova")


# ---------------------------------------------------------------------------
# 修正規則的改變種類（Phase 3T-1）
# ---------------------------------------------------------------------------


def _fake_change(change_id: str, unit: str = "flag") -> ModifierChangeDef:
    budget: dict[str, object] = {"unit": unit}
    if unit != "structured":
        budget["points"] = "add_element"
    return ModifierChangeDef.model_validate(
        {"id": change_id, "name_zh": "測試", "applies_to": ["all_skills"], "budget": budget}
    )


def test_real_modifier_changes_are_fully_covered() -> None:
    library = load_library()
    ids = set(library.modifier_changes.ids)
    assert ids == set(ModifierChange.model_fields)
    assert ids == set(CHANGE_HANDLERS) == DESCRIBED_CHANGES
    structured = {c.id for c in library.modifier_changes.changes if c.budget.unit == "structured"}
    assert structured == set(STRUCTURED_CHANGES)
    assert change_coverage_problems(library.modifier_changes.changes) == []


def test_new_change_without_entries_lists_every_missing_place() -> None:
    problems = change_coverage_problems([_fake_change("frost_bonus", "structured")])
    assert problems == [
        "修正規則改變 frost_bonus 沒有引擎的對應項（請補 trpg.engine.modifiers.CHANGE_HANDLERS）",
        "修正規則改變 frost_bonus 沒有卡片文字的對應項"
        "（請補 trpg.narrative.skills.DESCRIBED_CHANGES）",
        "修正規則改變 frost_bonus 的預算算法 structured 沒有實作"
        "（請補 trpg.skillgen.budget.STRUCTURED_CHANGES）",
    ]


def test_points_change_needs_no_structured_entry() -> None:
    assert change_coverage_problems([_fake_change("frost_bonus")], tables=()) == []


def test_change_yaml_must_match_model_fields_and_budget_keys() -> None:
    table = ModifierChangeTable(changes=(_fake_change("frost_bonus"),))
    problems = modifier_change_problems(table, {"hit_bonus"}, {"hit_bonus"})
    assert problems == [
        "frost_bonus 沒有 ModifierChange 的欄位（請補 trpg.content.skills）",
        "ModifierChange 的欄位 hit_bonus 沒有宣告（請補 modifier_changes.yaml）",
        "frost_bonus 的預算點數鍵 add_element 不在 skill_budget.yaml 的 modifier.points_milli",
    ]


def test_load_library_rejects_undeclared_change(tmp_path: Path) -> None:
    """``modifier_changes.yaml`` 少寫一種改變：載入時就報中文錯誤（不是執行時 ``KeyError``）。"""
    content = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", content)
    yaml_path = content / "modifier_changes.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    yaml_path.write_text(text[: text.index("  - id: form_entry_permille")], encoding="utf-8")
    with pytest.raises(ContentError) as caught:
        load_library(content)
    assert caught.value.path == yaml_path
    assert "ModifierChange 的欄位 form_entry_permille 沒有宣告" in caught.value.reason


def test_check_coverage_rejects_change_without_engine() -> None:
    library = load_library()
    extra = (*library.modifier_changes.changes, _fake_change("frost_bonus"))
    broken = replace(library, modifier_changes=ModifierChangeTable(changes=extra))
    with pytest.raises(ContentError) as caught:
        check_primitive_coverage(broken)
    assert caught.value.path == library.root / "modifier_changes.yaml"
    assert "修正規則改變 frost_bonus 沒有引擎的對應項" in caught.value.reason


# ---------------------------------------------------------------------------
# 強度旋鈕（Phase 3T-1）
# ---------------------------------------------------------------------------


def _knobbed(knob: object = None, basis: str = "per_amount") -> PrimitiveDef:
    param: dict[str, object] = {"type": "int", "min": 1, "max": 3}
    if knob is not None:
        param["knob"] = knob
    return PrimitiveDef.model_validate(
        {
            "id": "frost_nova",
            "name_zh": "測試",
            "description_zh": "測試",
            "category": "numeric",
            "harmful": True,
            "budget_basis": basis,
            "base_points": 1,
            "params": {"amount": param},
        }
    )


def test_real_content_declares_every_knob() -> None:
    assert knob_problems(load_library().ruleset.primitives.primitives) == []


def test_numeric_param_without_knob_is_reported() -> None:
    assert knob_problems([_knobbed()]) == [
        "原語 frost_nova 的參數 amount 沒有宣告強度旋鈕"
        "（請在 skill_primitives.yaml 補 knob；沒有旋鈕請寫 knob: none）"
    ]
    assert knob_problems([_knobbed(basis="fixed")]) == []  # 固定點數的原語不需要
    assert knob_problems([_knobbed("none")]) == []


def test_unimplemented_knob_ladder_is_reported() -> None:
    primitive = _knobbed({"ladder": "param_range", "weight": "other"})
    assert knob_problems([primitive], ladders=()) == [
        "原語 frost_nova 的參數 amount 的旋鈕階梯 param_range 沒有實作"
        "（請補 trpg.skillgen.composer_parts.KNOB_LADDERS）"
    ]


def test_param_range_knob_needs_int_min_and_max() -> None:
    with pytest.raises(ValueError, match="param_range"):
        _knobbed({"ladder": "param_range", "weight": 1, "start": 5})  # start > max


def test_load_checked_library_rejects_missing_knob(tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", content)
    yaml_path = content / "skill_primitives.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    knob = ", knob: {ladder: param_range, weight: other}}"
    start = text.index("  - id: grant_ap")
    end = text.index(knob, start)
    yaml_path.write_text(text[:end] + "}" + text[end + len(knob) :], encoding="utf-8")
    load_library(content)  # 內容本身合法
    with pytest.raises(ContentError) as caught:
        load_checked_library(content)
    assert caught.value.path == yaml_path
    assert "原語 grant_ap 的參數 amount 沒有宣告強度旋鈕" in caught.value.reason


# ---------------------------------------------------------------------------
# 種族技與形態（Phase 3T-2）
# ---------------------------------------------------------------------------


def test_real_race_effects_are_fully_covered() -> None:
    """每種種族效果都有結算、合法性檢查（或宣告無條件）、AI 計分函式（或宣告附帶效果）。"""
    assert race_coverage_problems() == []
    assert set(RACE_EFFECT_EXECUTORS) == set(RACE_EFFECT_SPECS)


def test_no_bundled_race_leads_with_a_rider_effect() -> None:
    races = load_library().ruleset.races
    assert races is not None
    leads = [(r.skill.id, r.skill.effects[0].type) for r in races.races]
    assert race_lead_problems(leads) == []
    assert race_lead_problems([("race_x", "ignore_opportunity_attack")])


def test_new_race_effect_without_entries_lists_every_missing_place() -> None:
    problems = race_coverage_problems(effect_types=[*RACE_EFFECT_SPECS, "teleport"])
    assert len(problems) == 3
    assert all("teleport" in p for p in problems)
    assert any("結算" in p for p in problems)
    assert any("合法性檢查" in p for p in problems)
    assert any("AI 計分函式" in p for p in problems)


def test_riders_and_unconditional_effects_need_no_entry() -> None:
    assert (
        race_coverage_problems(
            effect_types=["x"],
            executors=["x"],
            problems_table=[],
            unconditional=["x"],
            scorers=[],
            riders=["x"],
        )
        == []
    )


def test_real_form_effects_are_fully_covered() -> None:
    assert form_coverage_problems() == []
    assert set(FORM_EFFECT_CONSUMERS) == set(FormEffects.model_fields)
    assert set(FORM_ENTRY_CONSUMERS) == set(FormEntry.model_fields)


def test_new_form_field_is_reported() -> None:
    problems = form_coverage_problems(
        effect_fields=[*FormEffects.model_fields, "lifesteal"],
        entry_fields=[*FormEntry.model_fields, "teleport"],
    )
    assert len(problems) == 2
    assert "lifesteal" in problems[0] and "teleport" in problems[1]


def test_every_form_field_has_card_text() -> None:
    """每個形態效果與進入獎勵欄位設了值就有卡片文字（欄位不是只在引擎生效而玩家看不到）。"""
    form = next(f for f in load_library().ruleset.forms.forms)
    effects = {
        "defense_permille": 100,
        "move": 1,
        "max_hp_permille": 100,
        "damage_taken": (TakenMod(element=Element.FIRE, permille=500),),
        "heal_permille": 100,
        "flat_height": 1,
    }
    assert set(effects) == set(FormEffects.model_fields)
    for name, value in effects.items():
        probe = form.model_copy(update={"effects": FormEffects.model_validate({name: value})})
        assert form_effect_lines(probe), name
    entry = {
        "shield_max_hp_permille": 100,
        "heal_max_hp_permille": 100,
        "next_attack_hit": 1,
        "next_attack_crit": 1,
        "move": 1,
        "conceal": 1,
        "burst": EntryBurst(radius=1, dice=Dice(count=1, sides=4), element=Element.FIRE),
        "heal_adjacent": EntryHealAdjacent(dice=Dice(count=1, sides=4), attr=Attribute.WIL),
        "collision_permille": 100,
    }
    # shield_duration 只是護盾的持續回合，文字與護盾同一行
    assert set(entry) | {"shield_duration"} == set(FormEntry.model_fields)
    for name, value in entry.items():
        assert form_entry_lines(FormEntry.model_validate({name: value})), name
