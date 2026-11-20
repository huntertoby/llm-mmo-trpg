"""X10-3a：``content/`` 手寫說明文字裡的量類數字是新單位（和資料的值對得上）。

每一條都從資料讀出實際的值，再看說明文字寫的是不是同一個數字。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from trpg.content.library import ContentLibrary


def _yaml(library: ContentLibrary, relative: str) -> Any:
    return yaml.safe_load((library.root / relative).read_text(encoding="utf-8"))


def _by_id(rows: list[dict[str, Any]], row_id: str) -> dict[str, Any]:
    return next(r for r in rows if r.get("id") == row_id)


@pytest.fixture(scope="module")
def scale(library: ContentLibrary) -> int:
    value = library.ruleset.core.quantity_scale
    assert value == 10
    return value


def test_mana_potion_text(library: ContentLibrary) -> None:
    potion = _by_id(_yaml(library, "world/items.yaml")["items"], "item_mana_potion")
    (effect,) = potion["skill"]["effects"]
    assert effect["resource"] == "mana"
    assert f"戰鬥中回 {effect['amount']} 法力" in potion["description_zh"]
    assert effect["amount"] == 100


def test_block_reaction_text(library: ContentLibrary) -> None:
    block = _by_id(_yaml(library, "reactions.yaml")["reactions"], "block")
    assert f"消耗 {block['stamina_cost']} 耐力" in block["description_zh"]


def test_undying_text(library: ContentLibrary, scale: int) -> None:
    undying = _by_id(_yaml(library, "statuses.yaml")["statuses"], "undying")
    assert f"HP 留在 {scale}，" in undying["description_zh"]


def test_backlash_floor_texts(library: ContentLibrary, scale: int) -> None:
    primitives = (library.root / "skill_primitives.yaml").read_text(encoding="utf-8")
    workshop = (library.root / "workshop_text.yaml").read_text(encoding="utf-8")
    assert f"（反噬，不致命，不會讓 HP 低於 {scale}）" in primitives
    assert f"反噬傷害不會讓他的 HP 低於 {scale}，" in primitives
    assert workshop.count(f"反噬傷害不會讓他的 HP 低於 {scale}，") == 2  # source 與原文同步
    assert workshop.count(f"反噬不會讓你的 HP 低於 {scale}，") == 2
    for text in (primitives, workshop):
        assert "HP 低於 1，" not in text and "HP 低於 1）" not in text


def test_workshop_dummy_text(library: ContentLibrary) -> None:
    dummy = _yaml(library, "units/training_dummy.yaml")
    opponent = _by_id(_yaml(library, "workshop.yaml")["opponents"], "dummy")
    assert f"（HP {dummy['max_hp']}）" in opponent["description_zh"]


def test_flash_cost_texts(library: ContentLibrary, scale: int) -> None:
    minor = _yaml(library, "flash_templates.yaml")["minor"]
    light = _by_id(minor, "cost_light")["summary_zh"]
    assert f"法力、耐力 −{scale}" in light and f"法力、耐力最少留 {scale}" in light
    assert "冷卻最少留 1" in light and "AP −1（最少 1）" in light  # 冷卻、AP 不變
    blood = _by_id(minor, "cost_blood")["summary_zh"]
    assert f"只花 {scale} 點" in blood
    # X10-3c：姿態進入代價的法力、耐力一格也是 1 × scale（flash_ops._entry_cost）
    enter_light = _by_id(minor, "stance_enter_light")["summary_zh"]
    assert f"法力、耐力 −{scale}" in enter_light and f"法力、耐力最少留 {scale}" in enter_light
    assert "冷卻 −1" in enter_light and "冷卻最少留 1" in enter_light  # 冷卻不變
    enter_heavy = _by_id(minor, "stance_enter_heavy")["summary_zh"]
    assert f"法力或耐力 +{scale}" in enter_heavy


def test_newcomer_attribute_notes(library: ContentLibrary) -> None:
    perks = _yaml(library, "rules/core.yaml")["attribute_perks"]
    first_tier = perks["base"] + perks["step"]
    per_tier = {p["kind"]: p["per_tier"] for p in perks["perks"]}
    notes = _yaml(library, "world/newcomer.yaml")["attribute_notes"]
    for attr in ("str", "int", "wis", "wil"):
        assert f"；{first_tier} 起" in notes[attr]
    dealt, taken = per_tier["collision_dealt"], per_tier["collision_taken"]
    assert f"撞擊傷害多 {dealt}、受到的少 {taken}" in notes["str"]
    assert f"控制抵抗 +{per_tier['control_resist']}" in notes["wil"]
    assert f"表面多 {per_tier['surface_duration']} 回合" in notes["int"]  # 回合不放大


def test_ashen_heart_armor_thread_text(library: ContentLibrary) -> None:
    encounters = _yaml(library, "world/encounters/ashen_waste.yaml")
    text = (library.root / "world/events/cloud_ridge.yaml").read_text(encoding="utf-8")
    amounts = [
        mod["amount"]
        for row in _rows_with_armor_mods(encounters)
        for mod in row["armor_mods"]["mods"]
        if mod.get("world_flag") == "ashen_heart_hardened"
    ]
    assert amounts == [10]
    assert f"灰燼之心第 1 階段護甲 +{amounts[0]}（" in text


def _rows_with_armor_mods(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if "armor_mods" in node:
            found.append(node)
        for value in node.values():
            found.extend(_rows_with_armor_mods(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_rows_with_armor_mods(value))
    return found
