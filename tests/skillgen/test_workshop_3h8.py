"""工坊選項整修（Phase 3H-8）：第二屬性與專精選單、資源說明、組合規則標章、狀態選單。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import STRIKE, walk_draft
from trpg.skillgen.draft import build_skill
from trpg.skillgen.option_models import DraftOptions, FieldSpec, StepOptions
from trpg.skillgen.option_rules import composition_block
from trpg.skillgen.options import draft_options

SPELL: dict[str, Any] = {
    "skeleton": "strike",
    "kind": "active",
    "ap_cost": 2,
    "category": "spell",
    "weapon_req": "focus",
    "scaling_attr": "int",
    "tier": 2,
    "shape": {"type": "single", "range": 4},
    "effects": [{"type": "damage", "dice": "2d6", "element": "fire"}],
}


def _step(options: DraftOptions, step_id: str) -> StepOptions:
    return next(s for s in options.steps if s.id == step_id)


def _fields(step: StepOptions) -> dict[str, FieldSpec]:
    return {f.field: f for f in step.fields}


def _rarity_fields(draft: dict[str, Any]) -> dict[str, FieldSpec]:
    return _fields(_step(draft_options(draft, library()), "rarity"))


def test_spell_epic_shows_second_attribute_menu_within_allowed_range() -> None:
    lib = library()
    fields = _rarity_fields({**SPELL, "rarity": "epic"})
    secondary = fields.get("secondary_scaling_attr")
    values = set() if secondary is None else {c.value for c in secondary.choices}
    assert "int" not in values  # 不含主屬性

    # 選單＝允許範圍減主屬性（3H-7 後純火焰法術只允許智力，所以第二屬性沒有選項；
    # 組合主題的法術才有，例：元素＋意志主題）
    skill = build_skill({**SPELL, "rarity": "epic"})
    allowed = {a.value for a in lib.skill_scaling.allowed_attrs(skill, lib.weapons)}
    assert values == allowed - {skill.scaling_attr.value}


def test_second_attribute_hidden_below_epic_and_for_weapon_skills() -> None:
    assert "secondary_scaling_attr" not in _rarity_fields({**SPELL, "rarity": "rare"})
    weapon = walk_draft(STRIKE)
    fields = _rarity_fields({**weapon, "rarity": "epic"})
    assert "secondary_scaling_attr" not in fields


def test_mastery_menu_only_when_no_second_attribute() -> None:
    fields = _rarity_fields({**SPELL, "rarity": "epic"})
    assert {c.value for c in fields["mastery"].choices} == {"range"}
    chosen = _rarity_fields({**SPELL, "rarity": "epic", "secondary_scaling_attr": "wis"})
    assert "mastery" not in chosen
    assert "secondary_scaling_attr" in chosen


def test_mastery_duration_needs_a_status_effect() -> None:
    weapon = walk_draft(STRIKE)
    # 打擊 + 倒地沒有 apply_status：沒有持續專精；近戰單體沒有射程以外的專精也算有 range
    options = {
        c.value
        for c in _rarity_fields({**weapon, "rarity": "rare"})
        .get("mastery", FieldSpec(field="x", name_zh="x", type="choice"))
        .choices
    }
    assert "duration" not in options


def test_resource_text_comes_from_rules() -> None:
    lib = library()
    regen = lib.ruleset.core.resources.stamina_regen
    options = draft_options({**walk_draft(STRIKE)}, lib)
    cost = _step(options, "cost")
    stamina = _fields(cost)["cost.stamina"]
    assert f"每回合開始回復 {regen} 點" in stamina.description_zh
    assert "不回復" not in stamina.description_zh.split("；")[1]
    assert "耐力" in cost.description_zh
    assert "法力" not in cost.description_zh.split("、")[0]
    spell_cost = _step(draft_options({**SPELL, "rarity": "rare"}, lib), "cost")
    assert spell_cost.description_zh.startswith("法力")
    assert "cost.mana" in _fields(spell_cost)


def test_composition_rules_in_effect_choices() -> None:
    lib = library()
    draft = {k: v for k, v in SPELL.items() if k != "effects"}
    effects = _fields(_step(draft_options(draft, lib), "effects"))["effects"]
    infos = {str(c.value): c.info for c in effects.choices}
    ruled = {p.id: p for p in lib.ruleset.primitives.primitives if p.sole_effect or p.max_per_skill}
    shown = [pid for pid in ruled if pid in infos]
    assert shown
    for pid in shown:
        assert infos[pid]["badges_zh"]
        assert infos[pid]["rules_zh"]
        assert infos[pid]["composition"]["sole_effect"] == ruled[pid].sole_effect
        assert "unavailable_zh" not in infos[pid]  # 沒有已填效果時都能加


def test_composition_block_uses_the_primitive_rules() -> None:
    lib = library()
    by_id = lib.ruleset.primitives.by_id()
    hit = [{"type": "damage", "multiplier_permille": 1000}]
    reason, _ = composition_block(
        by_id["zone"], hit, lib, kind="active", allowed_affects=("tiles",)
    )
    assert reason is not None and "唯一" in reason
    reason, _ = composition_block(by_id["dash"], hit, lib, kind="passive", allowed_affects=())
    assert reason is not None and "主動技" in reason
    gamble = [{"type": "gamble"}]
    reason, _ = composition_block(by_id["gamble"], gamble, lib, kind="active", allowed_affects=())
    assert reason is not None and "上限" in reason
    # 其他效果限自己：已有的效果沒寫 affects: self 時要先改
    reason, _ = composition_block(
        by_id["charge_through"], hit, lib, kind="active", allowed_affects=("enemies",)
    )
    assert reason is not None and "自己" in reason
    ok, forced = composition_block(
        by_id["damage"],
        [{"type": "charge_through"}],
        lib,
        kind="active",
        allowed_affects=("enemies", "self"),
    )
    assert ok is None and forced == "self"
    blocked, _ = composition_block(
        by_id["damage"],
        [{"type": "charge_through"}],
        lib,
        kind="active",
        allowed_affects=("enemies",),
    )
    assert blocked is not None


def test_effects_step_marks_a_primitive_already_at_its_limit() -> None:
    lib = library()
    draft = {k: v for k, v in walk_draft(STRIKE).items() if k not in ("effects", "rarity")}
    draft["effects"] = [{"type": "damage", "multiplier_permille": 1000}, {"type": "gamble"}]
    effects = _fields(_step(draft_options(draft, lib), "effects"))["effects"]
    infos = {str(c.value): c.info for c in effects.choices}
    if "gamble" in infos:
        assert "上限" in infos["gamble"]["unavailable_zh"]
    assert "unavailable_zh" not in infos["damage"]


def test_apply_status_menu_excludes_statuses_without_budget_points() -> None:
    lib = library()
    draft = {k: v for k, v in SPELL.items() if k != "effects"}
    effects = _fields(_step(draft_options(draft, lib), "effects"))["effects"]
    apply = next(c for c in effects.choices if c.value == "apply_status")
    status = next(p for p in apply.params if p.field == "status")
    by_id = lib.ruleset.statuses.by_id()
    assert status.choices
    assert all(by_id[str(c.value)].budget_points is not None for c in status.choices)
