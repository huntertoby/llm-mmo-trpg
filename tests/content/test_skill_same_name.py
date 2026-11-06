"""同名技能檢查（6L-1，玩法 PM：顯示名相同、技能內容不同要報錯；白板武器版另取名）。"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.content.composer_rules import (
    WhiteboardRecipe,
    recipe_display_names,
    whiteboard_name_problems,
)
from trpg.content.library import ContentLibrary, skill_name_problems


def _recipe(**updates: Any) -> WhiteboardRecipe:
    data: dict[str, Any] = {
        "id": "bolt",
        "keyword": "ignite",
        "skeleton": "strike",
        "effect": {"type": "damage", "element": "fire"},
        "name_zh": "火球",
        "concept_zh": "一團火",
        "flavor_zh": "火焰飛出",
    }
    return WhiteboardRecipe.model_validate({**data, **updates})


def test_content_has_no_same_name_skills(library: ContentLibrary) -> None:
    assert skill_name_problems(library.skills, library.composer.whiteboard) == []
    wb = library.composer.whiteboard
    every = (*wb.active, *wb.passive, *wb.reaction)
    assert whiteboard_name_problems(wb.active, every) == []


@pytest.mark.parametrize(
    ("recipe_id", "weapon_name"),
    [
        ("fire_bolt", "火球擊"),
        ("lightning_bolt", "雷擊斬"),
        ("shadow_bolt", "暗影彈射"),
        ("frost_shard", "冰錐刺"),
    ],
)
def test_weapon_versions_named(recipe_id: str, weapon_name: str, library: ContentLibrary) -> None:
    wb = library.composer.whiteboard
    recipe = next(r for r in wb.active if r.id == recipe_id)
    assert recipe_display_names(recipe)["weapon"] == weapon_name
    assert recipe_display_names(recipe)["spell"] == recipe.name_zh != weapon_name


def test_dual_recipe_without_weapon_name_rejected() -> None:
    problems = whiteboard_name_problems([_recipe()], [_recipe()])
    assert any("武器版和法術版同名" in p for p in problems)
    # 已經是武器打法結尾、只開放一種、或另取武器版名稱：不報錯
    for ok in (
        _recipe(name_zh="火焰重擊"),
        _recipe(categories=["spell"]),
        _recipe(weapon_name_zh="火球擊"),
    ):
        assert whiteboard_name_problems([ok], [ok]) == []


def test_cross_recipe_same_name_rejected() -> None:
    a = _recipe(weapon_name_zh="火球擊")
    b = _recipe(id="other", name_zh="火球擊", categories=["spell"])
    assert any("同名：火球擊" in p for p in whiteboard_name_problems([a, b], [a, b]))
    same = _recipe(weapon_name_zh="火球")
    assert any("和 name_zh 相同" in p for p in whiteboard_name_problems([same], [same]))


def test_handwritten_same_name_different_content_rejected(library: ContentLibrary) -> None:
    skill = library.skills["skill_palm_strike"]
    twin = skill.model_copy(update={"id": "skill_twin", "ap_cost": (skill.ap_cost or 0) + 1})
    problems = skill_name_problems({skill.id: skill, twin.id: twin}, library.composer.whiteboard)
    assert problems == [f"技能同名但內容不同：{skill.name_zh}（skill_palm_strike、skill_twin）"]
    clone = skill.model_copy(update={"id": "skill_clone"})  # 內容完全相同（只差 ID）不算
    assert (
        skill_name_problems({skill.id: skill, clone.id: clone}, library.composer.whiteboard) == []
    )
    taken = skill.model_copy(update={"name_zh": "火球擊"})  # 白板武器版名稱撞到手寫技能
    assert any(
        "fire_bolt" in p
        for p in skill_name_problems({taken.id: taken}, library.composer.whiteboard)
    )
