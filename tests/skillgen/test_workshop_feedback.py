"""主題合併（R2）。

原 ``test_workshop_48c.py``：

Phase 3-48c：工坊試玩回饋第二批（稀有度步驟錯誤、法術技選項、最低花費、刻印）。

原 ``test_workshop_48f.py``：

Phase 3-48f：賭注專用效果的玩家文字、擊殺時效果的有益狀態限制。

原 ``test_workshop_rune_hint_48f.py``：

Phase 3-48f：工坊提示——刻印 + 給友方增益 + 沒有讀取符文的條件（玩法決定 #51）。

原 ``test_workshop_text_48f.py``：

Phase 3-48f：玩法 PM 改寫的工坊說明（content/workshop_text.yaml）套用到玩家模式。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from tests.skillgen.test_workshop_nested import _nested, _options_of, _weapon_draft
from tests.skillgen.workshop_walks import STRIKE, walk_draft
from trpg.content.skills import ModifierChange, SkillDef
from trpg.content.workshop import WorkshopTextEntry, WorkshopTextTable
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_models import Choice, FieldSpec, StepOptions
from trpg.skillgen.option_params import ParamContext, primitive_param_fields
from trpg.skillgen.option_player import content_dev_texts, has_dev_text, option_dev_texts, playerize
from trpg.skillgen.options import _change_field, draft_options
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill

# --- 原 test_workshop_48c.py ---

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


# --- 原 test_workshop_48f.py ---

LIB_48F = library()


def _harmful() -> str:
    return next(
        s.id for s in LIB_48F.ruleset.statuses.statuses if not s.beneficial and s.budget_points
    )


def _on_kill_effects(status: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "damage",
            "multiplier_permille": 1500,
            "on_kill": [{"type": "apply_status", "status": status, "duration": 2}],
        }
    ]


def test_gamble_special_effects_use_player_units() -> None:
    win = _nested(_options_of("gamble")["gamble"], "win")
    by_value = {str(c.value): c for c in win.choices}
    mult = by_value["damage_multiplier"].params[0]
    assert (mult.name_zh, mult.display) == ("倍率", "multiplier")
    assert "×2＝加倍" in by_value["damage_multiplier"].description_zh
    back = by_value["self_damage_of_hit"].params[0]
    assert (back.name_zh, back.display) == ("反噬比例（%）", "percent")
    assert "HP 至少留 1" in by_value["self_damage_of_hit"].description_zh
    for choice in (by_value["damage_multiplier"], by_value["self_damage_of_hit"]):
        assert "‰" not in choice.description_zh
        assert all("‰" not in p.name_zh for p in choice.params)


def test_refund_ap_is_called_ap_everywhere() -> None:
    kill = _nested(_options_of("damage")["damage"], "on_kill")
    refund = next(c for c in kill.choices if c.value == "refund_ap")
    assert refund.name_zh == "返還 AP" and "行動點" not in refund.description_zh


def test_on_kill_rejects_harmful_status_with_reason() -> None:
    draft = _weapon_draft(_on_kill_effects(_harmful()))
    result = check_draft(draft, LIB_48F)
    assert not result.legal
    assert any("擊殺時效果" in p.message_zh and "有益" in p.message_zh for p in result.problems)


def test_on_kill_beneficial_status_is_not_flagged() -> None:
    good = next(
        s.id
        for s in LIB_48F.ruleset.statuses.statuses
        if s.beneficial and s.budget_points and not s.stance
    )
    result = check_draft(_weapon_draft(_on_kill_effects(good)), LIB_48F)
    assert not any("擊殺時效果" in p.message_zh for p in result.problems)


def test_validator_rule_catches_yaml_and_proposals() -> None:
    base = LIB_48F.skills["skill_ash_harvest"].model_dump(mode="json", exclude_none=True)
    effects = _on_kill_effects(_harmful())
    effects[0].pop("multiplier_permille")
    effects[0].update(dice="2d6", element="fire")
    skill = SkillDef.model_validate({**base, "effects": effects})
    assert "on_kill.beneficial" in {v.rule for v in validate_skill(skill, LIB_48F)}


def test_no_builtin_skill_breaks_the_on_kill_rule() -> None:
    bad = [
        sid
        for sid, skill in LIB_48F.skills.items()
        if any(v.rule == "on_kill.beneficial" for v in validate_skill(skill, LIB_48F))
    ]
    assert bad == []


# --- 原 test_workshop_rune_hint_48f.py ---

LIB_WORKSHOP_RUNE_HINT_48F = library()
_INSCRIBE = {"type": "inscribe", "element": "lightning", "duration": 2}
_SHIELD_ALLIES = {"type": "shield", "dice": "1d6", "affects": "allies"}
_HINT = "符文本身沒有效果"


def _effects_notes(effects: list[dict[str, Any]], **over: Any) -> tuple[str, ...]:
    base = LIB_WORKSHOP_RUNE_HINT_48F.skills["skill_thunder_sigil"].model_dump(
        mode="json", exclude_none=True
    )
    keys = ("skeleton", "kind", "category", "weapon_req", "scaling_attr", "tier", "ap_cost")
    draft: dict[str, Any] = {k: base[k] for k in (*keys, "name_zh", "shape", "cost", "rarity")}
    draft.update(effects=effects, **over)
    step = next(
        s for s in draft_options(draft, LIB_WORKSHOP_RUNE_HINT_48F).steps if s.id == "effects"
    )
    return step.notes_zh


def test_rune_hint_shows_for_inscribe_plus_ally_buff_without_a_reader() -> None:
    notes = _effects_notes([_INSCRIBE, _SHIELD_ALLIES])
    assert any(_HINT in n and "持續區域" in n for n in notes)


def test_rune_hint_hidden_without_ally_buff() -> None:
    assert not any(_HINT in n for n in _effects_notes([_INSCRIBE]))


def test_rune_hint_hidden_when_a_rune_reader_exists() -> None:
    reader = {**_SHIELD_ALLIES, "condition": {"type": "on_own_rune"}}
    assert not any(_HINT in n for n in _effects_notes([_INSCRIBE, reader]))
    top = _effects_notes([_INSCRIBE, _SHIELD_ALLIES], condition={"type": "on_own_rune"})
    assert not any(_HINT in n for n in top)


# --- 原 test_workshop_text_48f.py ---

LIB_WORKSHOP_TEXT_48F = library()
TABLE = LIB_WORKSHOP_TEXT_48F.workshop_text


def _walk(fields: tuple[FieldSpec, ...]) -> list[FieldSpec]:
    out: list[FieldSpec] = []
    for f in fields:
        out.append(f)
        out += _walk(f.fields)
        for c in f.choices:
            out += _walk(c.params)
    return out


def _all_dev_texts() -> dict[str, str]:
    rows = dict(content_dev_texts(LIB_WORKSHOP_TEXT_48F))
    drafts: list[dict[str, object]] = [{}]
    for seed, skeleton in enumerate(sorted(LIB_WORKSHOP_TEXT_48F.skeletons), start=1):
        try:
            skill = compose_random_skill(seed, skeleton=skeleton, library=LIB_WORKSHOP_TEXT_48F)
        except ComposeError:
            continue
        full = skill.model_dump(mode="json", exclude_none=True)
        for drop in ((), ("effects", "cost", "rarity", "condition", "followup")):
            drafts.append({k: v for k, v in full.items() if k not in drop})
    for draft in drafts:
        for step in draft_options(draft, LIB_WORKSHOP_TEXT_48F).steps:
            rows.update(option_dev_texts({step.id: step.fields}))
    # 修正技能的「可套用」說明由程式依樣板產生玩家語氣（`options._change_field`；玩法 PM），
    # 不放在對照表裡，另由 test_modifier_change_texts_are_generated 檢查。
    return {k: v for k, v in rows.items() if not k.startswith(_MODIFIER_GENERATED)}


_MODIFIER_GENERATED = "工坊.effects.modifiers.change."


def test_modifier_change_texts_are_generated() -> None:
    for name in ModifierChange.model_fields:
        try:
            spec = _change_field(name, LIB_WORKSHOP_TEXT_48F, None)
        except KeyError:
            continue
        assert spec.description_zh.startswith("可以套用在："), name
        assert spec.dev_description_zh.startswith("可套用："), name
        assert not any("a" <= c <= "z" for c in spec.description_zh.replace("HP", "").lower())


def test_table_has_the_164_rewritten_entries() -> None:
    # 149 ＋ 3-54c 的清除表面 ＋ 3I-5 的手持武器條件（工坊、條件各一）
    # ＋ 3-54a 的吹送（說明 3-54b 改成玩法 PM 的句子）
    # ＋ 3-54b 的震波與元素擴散格數（實作者初稿，待玩法 PM 改寫）
    # ＋ 3J-1a 的進入形態與它的形態參數（實作者初稿，待玩法 PM 改寫）
    # ＋ 3J-3 的在形態中條件（工坊、條件各一）
    # ＋ 3J-4b 的在形態中加成（傷害、治療的原語與工坊各一）
    # ＋ 3J-4c 的解除形態（原語一筆）
    # ＋ 3W-5b 的完整姿態幅度（原語參數一筆，實作者初稿，待玩法 PM 改寫）
    # ＋ BAL-2c 的形態幅度（原語參數一筆，實作者初稿，待玩法 PM 改寫）
    # ＋ BAL-12c 的固定值加成（傷害、治療、護盾原語參數各一，實作者初稿，待玩法 PM 改寫）
    # ＋ BAL-12e 的表面強度（原語參數一筆，實作者初稿，待玩法 PM 改寫）
    # ＋ TF-1 的召喚到身邊（原語與反咬參數各一，實作者初稿，待玩法 PM 改寫）
    # ＋ KW-1b 的自身層數達到的層數參數（條件參數一筆，實作者初稿，待玩法 PM 改寫）
    assert len(TABLE.texts) == 173
    assert len({e.id for e in TABLE.texts}) == 173


def test_every_dev_text_has_a_player_rewrite_and_every_rewrite_is_used() -> None:
    rows = _all_dev_texts()
    sources = {e.source for e in TABLE.texts}
    assert sorted({t for t in rows.values() if t not in sources}) == []
    assert sorted(sources - set(rows.values())) == []


def test_player_mode_shows_the_rewrite_and_dev_mode_keeps_the_original() -> None:
    skill = compose_random_skill(1, skeleton="strike", library=LIB_WORKSHOP_TEXT_48F)
    draft = skill.model_dump(mode="json", exclude_none=True)
    found = 0
    for step in draft_options(draft, LIB_WORKSHOP_TEXT_48F).steps:
        for f in _walk(step.fields):
            for text, dev in [(f.description_zh, f.dev_description_zh)] + [
                (c.description_zh, c.dev_description_zh) for c in f.choices
            ]:
                if dev:
                    found += 1
                    assert text == TABLE.lookup(dev, None) or TABLE.lookup(dev, None) is None
                    assert text != dev
    assert found > 0


def test_same_source_different_scope_texts() -> None:
    assert TABLE.lookup("層數 ID（stacks.yaml）", "add_stack.stack") == "要累積哪一種層數。"
    assert TABLE.lookup("層數 ID（stacks.yaml）", "consume_stack.stack") == "要消耗哪一種層數。"
    assert TABLE.lookup("層數 ID（stacks.yaml）", "other.stack") is None


def test_clashing_texts_need_a_scope() -> None:
    a = WorkshopTextEntry(id="a", source="x", player="1")
    b = WorkshopTextEntry(id="b", source="x", player="2")
    with pytest.raises(ValidationError):
        WorkshopTextTable(texts=(a, b))
    scoped = WorkshopTextEntry(id="b", source="x", player="2", scope="f.g")
    assert WorkshopTextTable(texts=(a, scoped)).lookup("x", "f.g") == "2"


def test_rewritten_texts_do_not_leak_internal_ids() -> None:
    for entry in TABLE.texts:
        assert "‰" not in entry.player or entry.id.startswith("工坊") or entry.id.startswith("原語")
        assert ".yaml" not in entry.player
