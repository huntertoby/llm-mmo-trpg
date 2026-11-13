"""主題合併（R2）。

原 ``test_stack_expansion_52.py``：

Phase 3-52：層數擴充的卡片、規則說明、驗證器與工坊（對象自動決定、依自己／敵人分組）。

原 ``test_stack_workshop_52b.py``：

Phase 3-52b：工坊選層數時，事前停用「這招不能消耗的層數」，並與驗證器同源；氣的治療加成預算。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.api.glossary import build_glossary
from trpg.content.library import skill_reference_problems
from trpg.content.skills import SkillDef
from trpg.narrative.skills import skill_card
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.option_effect_rules import effect_fixes, stack_unavailable_reason
from trpg.skillgen.option_models import Choice
from trpg.skillgen.option_params import STACK_GROUP_ZH, stack_choices
from trpg.skillgen.options import draft_options

# --- 原 test_stack_expansion_52.py ---

NEW_STACKS = ("combo_point", "focus", "holy_power", "soul_shard", "hoarfrost", "ki", "fury")
_ENGLISH = "abcdefghijklmnopqrstuvwxyz_"


def _card_text(skill_id: str) -> str:
    lib = library()
    card = skill_card(lib, lib.skills[skill_id])
    return "\n".join(card.effects)


def test_consume_text_names_what_the_stack_boosts() -> None:
    assert "傷害 +20%" in _card_text("skill_combo_finisher")
    # RG-5b（玩法PM交接 4.1.7 第 3 條）：連擊點一律用「點」，其他照舊「層」
    assert "每點使本技能傷害 +20%" in _card_text("skill_combo_finisher")
    assert "每層" not in _card_text("skill_throat_cut")
    shield = _card_text("skill_sanctified_ward")
    assert "每層使本技能治療、護盾 +20%" in shield
    assert "傷害、治療" in _card_text("skill_qi_breath") or "治療 +15%" in _card_text(
        "skill_qi_breath"
    )


def test_glossary_explains_how_each_new_stack_is_gained_and_spent() -> None:
    glossary = build_glossary(library())
    by_id = {e.id: e for e in glossary.stacks}
    for stack_id in NEW_STACKS:
        lines = "\n".join(by_id[stack_id].rules_zh)
        assert "只有帶著消耗它的技能才會自動累積" in lines, stack_id
        unit = library().ruleset.stack_def(stack_id).unit_zh  # RG-5b：連擊點用「點」
        assert f"消耗：技能每{unit}提高" in lines, stack_id
        assert ("層" in lines) is (unit == "層"), f"{stack_id} 單位不一致：{lines}"
        assert not any(c in lines for c in _ENGLISH), f"{stack_id} 說明露出英文：{lines}"
    assert "疊在被命中的敵人身上" in "\n".join(by_id["hoarfrost"].rules_zh)
    assert "3 輪沒有再累積就清空" in "\n".join(by_id["hoarfrost"].rules_zh)
    assert "限帶「召喚」標籤" in "\n".join(by_id["soul_shard"].rules_zh)


def test_every_demo_pair_makes_and_uses_its_stack() -> None:
    lib = library()
    pairs = {
        "combo_point": ("skill_flurry_jab", "skill_combo_finisher"),
        "focus": ("skill_steady_aim", "skill_focused_shot"),
        "holy_power": ("skill_radiant_mend", "skill_sanctified_ward"),
        "soul_shard": ("skill_soul_reap", "skill_soul_torrent"),
        "hoarfrost": ("skill_rime_touch", "skill_shatter_frost"),
        "ki": ("skill_palm_strike", "skill_qi_breath"),
        "fury": ("skill_seething_rage", "skill_rage_unleashed"),
    }
    for stack_id, (makes, uses) in pairs.items():
        assert any(
            e.type == "add_stack" and e.stack == stack_id for e in lib.skills[makes].effects
        ), makes
        assert any(
            e.type == "consume_stack" and e.stack == stack_id for e in lib.skills[uses].effects
        ), uses


# ---------------------------------------------------------------------------
# 驗證器：消耗規則
# ---------------------------------------------------------------------------


def _with(skill_id: str, **changes: Any) -> SkillDef:
    return library().skills[skill_id].model_copy(update=changes)


def _problems(skill: SkillDef) -> list[str]:
    lib = library()
    return skill_reference_problems(skill, lib.ruleset, lib.skills)


def test_the_demo_skills_pass_the_consumer_rules() -> None:
    for skill_id in ("skill_combo_finisher", "skill_sanctified_ward", "skill_shatter_frost"):
        assert _problems(library().skills[skill_id]) == [], skill_id


def test_a_combo_point_consumer_must_be_a_finisher() -> None:
    skill = _with("skill_combo_finisher", tags=("physical", "melee"))
    assert any("只有符合條件的技能可以消耗" in p for p in _problems(skill))


def test_a_holy_power_consumer_needs_a_heal_or_shield() -> None:
    lib = library()
    damage_only = next(e for e in lib.skills["skill_combo_finisher"].effects if e.type == "damage")
    ward = lib.skills["skill_sanctified_ward"]
    consume = next(e for e in ward.effects if e.type == "consume_stack")
    skill = ward.model_copy(update={"effects": (damage_only, consume)})
    assert any("至少要有治療、護盾其中一種效果" in p for p in _problems(skill))


def test_a_frost_consumer_needs_ice_damage() -> None:
    lib = library()
    shatter = lib.skills["skill_shatter_frost"]
    fire = [
        e.model_copy(update={"element": "fire"}) if e.type == "damage" else e
        for e in shatter.effects
    ]
    assert any(
        "只有符合條件的技能可以消耗" in p
        for p in _problems(shatter.model_copy(update={"effects": tuple(fire)}))
    )


def test_a_stack_effect_must_target_its_owner() -> None:
    lib = library()
    jab = lib.skills["skill_flurry_jab"]
    wrong = [
        e.model_copy(update={"affects": "enemies"}) if e.type == "add_stack" else e
        for e in jab.effects
    ]
    assert any(
        "只能是 affects: self" in p
        for p in _problems(jab.model_copy(update={"effects": tuple(wrong)}))
    )


# ---------------------------------------------------------------------------
# 工坊：分組與對象自動決定
# ---------------------------------------------------------------------------


def test_workshop_groups_stacks_by_who_carries_them() -> None:
    choices = stack_choices(library())
    groups = [c.info["group_zh"] for c in choices]
    assert set(groups) == set(STACK_GROUP_ZH.values())
    assert groups == sorted(groups, key=lambda g: g != STACK_GROUP_ZH["self"])  # 自己的在前
    frost = next(c for c in choices if c.value == "hoarfrost")
    assert frost.info["owner"] == "target" and frost.info["group_zh"] == "疊在敵人身上"
    combo = next(c for c in choices if c.value == "combo_point")
    assert combo.info["owner"] == "self" and combo.info["group_zh"] == "累積在你身上"


@pytest.mark.parametrize(
    ("stack", "chosen", "expect"),
    [
        ("combo_point", None, "self"),
        ("combo_point", "enemies", "self"),
        ("hoarfrost", None, "enemies"),
        ("hoarfrost", "self", "enemies"),
    ],
)
def test_the_target_follows_the_chosen_stack(stack: str, chosen: str | None, expect: str) -> None:
    effect: dict[str, Any] = {"type": "add_stack", "stack": stack, "amount": 1}
    if chosen is not None:
        effect["affects"] = chosen
    fixes = effect_fixes({"effects": [effect]}, library(), ())
    assert [(f.index, f.value) for f in fixes] == [(0, expect)]
    assert "對象自動決定" in fixes[0].reason_zh


def test_no_fix_when_the_target_already_matches() -> None:
    effect = {"type": "consume_stack", "stack": "hoarfrost", "per_stack_permille": 250}
    assert effect_fixes({"effects": [{**effect, "affects": "enemies"}]}, library(), ()) == ()
    effect = {"type": "add_stack", "stack": "ki", "amount": 1, "affects": "self"}
    assert effect_fixes({"effects": [effect]}, library(), ()) == ()


# --- 原 test_stack_workshop_52b.py ---

LIB = library()


def _stack_choices(draft: dict[str, Any]) -> dict[str, Choice]:
    """效果步驟裡 ``consume_stack`` 選項的層數子選項（值 → 選項）。"""
    options = draft_options(draft, LIB)
    step = next(s for s in options.steps if s.id == "effects")
    field = next(f for f in step.fields if f.field == "effects")
    consume = next(c for c in field.choices if c.value == "consume_stack")
    stack = next(p for p in consume.params if p.field == "stack")
    return {str(c.value): c for c in stack.choices}


def _draft_of(skill_id: str, drop: str | None = None) -> dict[str, Any]:
    data = LIB.skills[skill_id].model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    data["effects"] = [e for e in data["effects"] if e["type"] != drop]
    for key in ("id", "provenance", "narrative", "tags"):
        data.pop(key, None)
    data["kind"] = "active"
    return data


def _reason(choices: dict[str, Choice], stack: str) -> object:
    return choices[stack].info.get("unavailable_zh")


def test_a_damage_only_draft_cannot_pick_heal_or_shield_stacks() -> None:
    choices = _stack_choices(_draft_of("skill_combo_finisher", drop="consume_stack"))
    reason = _reason(choices, "holy_power")
    assert isinstance(reason, str) and "治療" in reason and "護盾" in reason
    assert "先加入" in reason  # 白話：怎麼改
    assert _reason(choices, "combo_point") is None  # 傷害技可以（標籤不明時先視為符合）
    assert _reason(choices, "focus") is None
    assert _reason(choices, "static_charge") is None  # 舊層數沒有消耗規則


def test_a_heal_only_draft_cannot_pick_damage_only_stacks() -> None:
    choices = _stack_choices(_draft_of("skill_sanctified_ward", drop="consume_stack"))
    assert _reason(choices, "holy_power") is None
    reason = _reason(choices, "focus")
    assert isinstance(reason, str) and "傷害" in reason
    # 氣只加成「治療自己」：這招的護盾／別人的治療不算
    ki = _reason(choices, "ki")
    assert isinstance(ki, str) and "治療自己" in ki


def test_a_self_heal_makes_ki_available() -> None:
    choices = _stack_choices(_draft_of("skill_qi_breath", drop="consume_stack"))
    assert _reason(choices, "ki") is None


def test_an_ally_heal_does_not_make_ki_available() -> None:
    draft = _draft_of("skill_qi_breath", drop="consume_stack")
    draft["effects"][0]["affects"] = "allies"
    assert isinstance(_reason(_stack_choices(draft), "ki"), str)


def test_element_requirements_are_checked_against_the_draft_effects() -> None:
    fire = _draft_of("skill_shatter_frost", drop="consume_stack")
    for effect in fire["effects"]:
        if effect["type"] == "damage":
            effect["element"] = "fire"
    reason = _reason(_stack_choices(fire), "hoarfrost")
    assert isinstance(reason, str) and "冰霜傷害" in reason
    ice = _stack_choices(_draft_of("skill_shatter_frost", drop="consume_stack"))
    assert _reason(ice, "hoarfrost") is None


def test_the_options_agree_with_the_validator_for_every_stack() -> None:
    """同源：選項說可以的組合，驗證器的消耗規則不報錯；說不行的，驗證器一定報錯。"""
    stacks = LIB.ruleset.stacks.by_id()
    for skill_id in ("skill_combo_finisher", "skill_sanctified_ward", "skill_shatter_frost"):
        base = LIB.skills[skill_id]
        for stack_id, stack in sorted(stacks.items()):
            owner = "self" if stack.owner == "self" else "enemies"
            consume = next(e for e in base.effects if e.type == "consume_stack").model_copy(
                update={"stack": stack_id, "affects": owner}
            )
            effects = (*(e for e in base.effects if e.type != "consume_stack"), consume)
            skill: SkillDef = base.model_copy(update={"effects": effects})
            reason = stack_unavailable_reason(skill, stack_id, LIB)
            problems = [
                p
                for p in skill_reference_problems(skill, LIB.ruleset, LIB.skills)
                if "消耗層數" in p or "只有符合條件的技能可以消耗" in p
            ]
            assert (reason is None) == (problems == []), (skill_id, stack_id, reason, problems)


def test_the_chosen_stack_stays_selectable() -> None:
    """已經選了的層數不被停用（前端的規則；違規由檢查面板說明）：後端照實標，前端放行。"""
    choices = _stack_choices(_draft_of("skill_combo_finisher", drop="consume_stack"))
    assert set(choices) >= {"combo_point", "focus", "ki", "holy_power"}


def test_the_ki_budget_counts_only_the_self_heal() -> None:
    breath = LIB.skills["skill_qi_breath"]
    self_points = _consume_points(breath)
    ally = breath.model_copy(
        update={
            "effects": tuple(
                e.model_copy(update={"affects": "allies"}) if e.type == "heal" else e
                for e in breath.effects
            )
        }
    )
    assert _consume_points(ally) == Fraction(0) < self_points  # 治療別人沒有氣的加成點數


def _consume_points(skill: SkillDef) -> Fraction:
    report = skill_budget(skill, LIB)
    return sum((e.points for e in report.effects if e.type == "consume_stack"), Fraction(0))
