"""玩家看到的工坊檢查文字不露英文欄位名、ID、列舉值（3-48，玩法決定 #44）。"""

from __future__ import annotations

import copy
import re
from typing import Any

from tests.engine.helpers import library
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.options import draft_options
from trpg.skillgen.player_text import plainify
from trpg.skillgen.random_composer import compose_random_skill

# 玩家文字裡允許的英文縮寫（遊戲用語）
_ALLOWED = {"AP", "HP", "MP", "YAML"}
_ENGLISH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]{2,}")


def _leaks(text: str) -> list[str]:
    return [w for w in _ENGLISH.findall(text) if w not in _ALLOWED]


def _field_texts(field: Any) -> list[str]:
    """欄位與選項的顯示文字（名稱、說明；遞迴）。"""
    out = [
        field.name_zh,
        field.description_zh,
    ]  # 3-48c：說明也是玩家文字（原文在 dev_description_zh）
    for sub in field.fields:
        out += _field_texts(sub)
    for choice in field.choices:
        out += [choice.name_zh, choice.description_zh]
        for param in choice.params:
            out += _field_texts(param)
    return out


def _player_texts(draft: dict[str, Any]) -> list[str]:
    lib = library()
    options = draft_options(draft, lib)
    check = check_draft(draft, lib)
    texts = list(options.problems)
    for step in options.steps:
        texts += [step.name_zh, step.description_zh, *step.notes_zh]
        for field in step.fields:
            texts += _field_texts(field)
    texts += [p.message_zh for p in check.problems]
    texts += list(check.rarity_reasons)
    if check.budget is not None:
        b = check.budget
        for line in b.lines:
            texts += [line.type, line.note]
        for seg in b.segments:
            texts += [seg.skeleton, seg.shape, *seg.synergies]
            for line in seg.lines:
                texts += [line.type, line.note]
        texts += [*b.synergies, *b.self_combo_reasons]
    return texts


def _mutations(base: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [base]
    for key, value in (
        ("category", "weapon"),
        ("category", "spell"),
        ("weapon_req", "melee"),
        ("weapon_req", "focus"),
        ("scaling_attr", "wil"),
        ("scaling_attr", "str"),
        ("secondary_scaling_attr", "dex"),
        ("tier", 1),
        ("tier", 9),
        ("rarity", "common"),
        ("kind", "passive"),
        ("kind", "stance"),
        ("ap_cost", 9),
        ("skeleton", "strike"),
        ("skeleton", "bogus_skeleton"),
    ):
        mutated = copy.deepcopy(base)
        mutated[key] = value
        out.append(mutated)
    for index in range(len(base.get("effects", ()))):
        mutated = copy.deepcopy(base)
        del mutated["effects"][index]
        out.append(mutated)
    return out


def test_player_check_texts_have_no_english_identifiers() -> None:
    found: dict[str, str] = {}
    for seed in range(60):
        base = compose_random_skill(seed, library=library()).model_dump(
            mode="json", exclude_none=True
        )
        for draft in _mutations(base):
            for text in _player_texts(draft):
                for word in _leaks(text):
                    found.setdefault(word, text)
    assert found == {}, found


def test_plainify_translates_fields_and_ids() -> None:
    lib = library()
    text = plainify("骨架 strike：effects[1]（damage）的 weapon_req 只能是 melee、ranged", lib)
    assert "strike" not in text and "damage" not in text and "weapon_req" not in text
    assert "第 2 個效果" in text and "近戰武器" in text and "遠程武器" in text


def _nested_drafts() -> list[dict[str, Any]]:
    """3-48d：四種巢狀原語各一份草稿（內建示範技能的欄位），含正常的與故意寫錯的子效果。"""
    keys = (
        "skeleton",
        "kind",
        "category",
        "weapon_req",
        "scaling_attr",
        "tier",
        "ap_cost",
        "name_zh",
        "shape",
        "effects",
        "condition",
        "cost",
        "rarity",
    )
    lib = library()
    out: list[dict[str, Any]] = []
    for skill_id in (
        "skill_detonate_burning",
        "skill_fire_wall",
        "skill_blood_sacrifice",
        "skill_ash_harvest",
    ):
        dumped = lib.skills[skill_id].model_dump(mode="json", exclude_none=True)
        draft = {k: dumped[k] for k in keys if k in dumped}
        out.append(draft)
        for group in ("then", "effects", "win", "lose", "on_kill"):
            for bad in ({"type": "taunt"}, {"type": "zone"}, {"type": "damage"}, {}):
                mutated = copy.deepcopy(draft)
                for effect in mutated["effects"]:
                    if group in effect:
                        effect[group] = [bad]
                out.append(mutated)
    return out


def test_nested_level_texts_have_no_english_identifiers() -> None:
    found: dict[str, str] = {}
    for draft in _nested_drafts():
        for text in _player_texts(draft):
            for word in _leaks(text):
                found.setdefault(word, text)
    assert found == {}, found
