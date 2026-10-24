"""Phase 3-52：層數擴充的卡片、規則說明、驗證器與工坊（對象自動決定、依自己／敵人分組）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.api.glossary import build_glossary
from trpg.content.library import skill_reference_problems
from trpg.content.skills import SkillDef
from trpg.narrative.skills import skill_card
from trpg.skillgen.option_effect_rules import effect_fixes
from trpg.skillgen.option_params import STACK_GROUP_ZH, stack_choices

NEW_STACKS = ("combo_point", "focus", "holy_power", "soul_shard", "hoarfrost", "ki", "fury")
_ENGLISH = "abcdefghijklmnopqrstuvwxyz_"


def _card_text(skill_id: str) -> str:
    lib = library()
    card = skill_card(lib, lib.skills[skill_id])
    return "\n".join(card.effects)


def test_consume_text_names_what_the_stack_boosts() -> None:
    assert "傷害 +20%" in _card_text("skill_combo_finisher")
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
        assert "消耗：技能每層提高" in lines, stack_id
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
