"""Phase 3-48c：工坊試玩回饋第二批（稀有度步驟錯誤、法術技選項、最低花費、刻印）。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import STRIKE, walk_draft
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_models import Choice, FieldSpec, StepOptions
from trpg.skillgen.option_params import ParamContext, primitive_param_fields
from trpg.skillgen.option_player import content_dev_texts, has_dev_text, playerize
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill

LIB = library()


def _strike_draft() -> dict[str, Any]:
    draft: dict[str, Any] = {}
    for _step, picks in STRIKE[:-1]:
        draft.update(picks)
    return draft


def _step(draft: dict[str, Any], step_id: str) -> StepOptions:
    return next(s for s in draft_options(draft, LIB).steps if s.id == step_id)


def _field(step: StepOptions, name: str) -> FieldSpec:
    return next(f for f in step.fields if f.field == name)


def test_rarity_step_lists_the_plain_error_and_the_step_to_go_back_to() -> None:
    # 第二縮放屬性和主屬性相同：稀有度推導不出來，步驟要列出白話原因與「回到第 N 步修改」
    draft = {**_strike_draft(), "secondary_scaling_attr": "str"}
    notes = _step(draft, "rarity").notes_zh
    assert any("無法推導稀有度" in n for n in notes)
    assert not any("problems" in n or "見檢查結果" in n for n in notes)
    assert any(n.startswith("．") and "回到第" in n for n in notes)
    assert not any("secondary_scaling_attr" in n for n in notes)


def test_stale_weapon_requirement_is_reported_and_the_step_is_not_ticked() -> None:
    draft = {**_strike_draft(), "category": "spell"}  # 武器技換成法術技，武器需求還是近戰
    options = draft_options(draft, LIB)
    basics = next(s for s in options.steps if s.id == "basics")
    assert not basics.complete
    assert options.problems


def test_spell_shape_range_has_no_weapon_range_option() -> None:
    spell = {**_strike_draft(), "category": "spell", "weapon_req": "focus", "scaling_attr": "int"}
    weapon = _strike_draft()
    for draft, expected in ((spell, False), (weapon, True)):
        shape = _field(_step(draft, "shape"), "shape")
        single = next(c for c in shape.choices if c.value == "single")
        assert any(p.allow_weapon for p in single.params) is expected


# ---------------------------------------------------------------------------
# 最低花費（06 6.10，2026-10-24）
# ---------------------------------------------------------------------------


def test_workshop_check_rejects_an_active_skill_without_the_minimum_cost() -> None:
    draft = walk_draft(STRIKE)
    assert check_draft(draft, LIB).legal
    result = check_draft({**draft, "cost": {}}, LIB)
    assert not result.legal
    assert any(p.rule == "cap.min_cost" and "1 點耐力" in p.message_zh for p in result.problems)
    spell = {**draft, "category": "spell", "weapon_req": "focus", "scaling_attr": "int"}
    spell["effects"] = [{"type": "damage", "dice": "2d6", "element": "fire"}]
    spell["cost"] = {}
    assert any("1 點法力" in p.message_zh for p in check_draft(spell, LIB).problems)


def _walk_fields(fields: Any) -> Any:
    for f in fields:
        yield f
        yield from _walk_fields(f.fields)
        for c in f.choices:
            yield from _walk_fields(c.params)


def _rune_draft() -> dict[str, Any]:
    return {
        "skeleton": "rune",
        "kind": "active",
        "ap_cost": 2,
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "tier": 1,
        "shape": {"type": "ground_tile", "range": 3},
        "effects": [{"type": "inscribe", "tag": "hunt", "duration": 3}],
        "cost": {"mana": 4, "cooldown": 2},
    }


def _wide_draft() -> dict[str, Any]:
    """控場骨架（效果選項最多：持續區域、消耗狀態、賭注都在）。"""
    draft = {k: v for k, v in _rune_draft().items() if k not in ("effects", "cost")}
    core = {"type": "apply_status", "status": "burning", "duration": 2}
    return {
        **draft,
        "skeleton": "control",
        "shape": {"type": "single", "range": 3},
        "effects": [core],
    }


def _effect_choice(step: StepOptions, primitive: str) -> Any:
    effects = _field(step, "effects")
    return next(c for c in effects.choices if c.value == primitive)


def test_rune_tag_is_a_menu_of_defined_rune_tags_and_only_tiles_can_be_targeted() -> None:
    draft = {k: v for k, v in _rune_draft().items() if k not in ("effects", "cost")}
    inscribe = _effect_choice(_step(draft, "effects"), "inscribe")
    params = {p.field: p for p in inscribe.params}
    assert params["tag"].type == "choice"
    assert [(c.value, c.name_zh) for c in params["tag"].choices] == [("hunt", "獵紋")]
    assert [c.value for c in params["affects"].choices] == ["tiles"]
    assert (
        "（" not in params["duration"].description_zh
        or "yaml" not in params["duration"].description_zh
    )


def test_validator_rejects_a_custom_rune_tag_and_a_non_tile_target() -> None:
    ok = check_draft({**_rune_draft(), "rarity": "rare"}, LIB)
    assert not any(p.rule in ("rune.tag", "reference") for p in ok.problems), ok.problems
    custom = _rune_draft()
    custom["effects"] = [{"type": "inscribe", "tag": "mytag", "duration": 3}]
    result = check_draft({**custom, "rarity": "rare"}, LIB)
    assert any(p.rule == "rune.tag" and "獵紋" in p.message_zh for p in result.problems)
    own = _rune_draft()
    own["effects"] = [{"type": "inscribe", "element": "fire", "affects": "self"}]
    result = check_draft({**own, "rarity": "rare"}, LIB)
    assert not result.legal


def test_conditional_fields_carry_show_when_and_nested_primitives_are_no_longer_hidden() -> None:

    ctx = ParamContext(LIB, category="spell")
    choices = tuple(
        Choice(
            value=p.id,
            name_zh=p.name_zh,
            description_zh=p.description_zh,
            params=primitive_param_fields(p, ctx),
        )
        for p in LIB.ruleset.primitives.primitives
    )
    effects = playerize(
        (FieldSpec(field="effects", name_zh="效果", type="effects", choices=choices),), LIB
    )
    by_id = {c.value: c for c in effects[0].choices}
    assert not any(c.later for c in effects[0].choices)
    damage = by_id["damage"]
    assert not damage.later and not any(p.later for p in damage.params)
    assert {p.field: p.show_when for p in by_id["zone"].params}["speed"] == {"anchor": "moving"}
    assert {p.field: p.show_when for p in by_id["consume_status"].params}["stack"] == {
        "scale": "stacks"
    }
    assert {p.field: p.show_when for p in by_id["reset_cooldown"].params}["tag"] == {"which": "tag"}


def test_every_option_description_is_player_safe_and_keeps_the_original_for_dev() -> None:

    effects = _step(_wide_draft(), "effects")
    changed = 0
    for f in _walk_fields(effects.fields):
        assert not has_dev_text(f.description_zh), f.field
        changed += bool(f.dev_description_zh)
        for c in f.choices:
            assert not has_dev_text(c.description_zh), c.value
            changed += bool(c.dev_description_zh)
    assert changed > 10


def test_description_export_lists_the_dev_flavoured_texts() -> None:

    rows = dict(content_dev_texts(LIB))
    assert "原語.zone" in rows and "原語.consume_status" in rows and "形狀.line" in rows


def test_random_composer_always_pays_the_minimum_cost() -> None:
    for seed in range(300):
        skill = compose_random_skill(seed, library=LIB, tier=1 + seed % 3)
        assert LIB.budget.min_cost_problem(skill.kind, skill.category, skill.cost) is None, seed
