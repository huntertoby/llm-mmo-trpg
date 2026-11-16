"""PK-4 許願池「願望驅動」的純函式（:mod:`trpg.skillgen.wish_pick`；07 7.6「許願池：願望驅動」）：
標籤的清理與檢查、命中判定、「做不到」那一行的字。候選池與挑選在
``tests/world/test_wish_pk4.py``。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.skillgen.wish_pick import (
    clean_wish_tags,
    skill_tag_ids,
    tag_hits,
    tag_labels,
    wish_miss_zh,
    wish_tags_problem,
)

MENU = ("ignite", "frozen", "summon", "collision", "high_ground")


def test_tag_list_matches_the_design() -> None:
    """07 7.6 第 1 點的清單：元素 9 個、效果類型 8 個、形狀 5 個、種類 3 個；上限 2／1／2／1／1。"""
    rules = library().skill_pick.wish_tags
    assert [i.name_zh for i in rules.elements] == [
        "物理",
        "火焰",
        "冰霜",
        "雷電",
        "毒素",
        "風",
        "大地",
        "神聖",
        "暗影",
    ]
    assert [i.name_zh for i in rules.effects] == [
        "傷害",
        "控制",
        "治療",
        "護盾",
        "增益",
        "位移",
        "召喚",
        "地形",
    ]
    assert [i.name_zh for i in rules.shapes] == ["單體", "範圍", "直線", "錐形", "自身周圍"]
    assert [i.name_zh for i in rules.kinds] == ["主動", "被動", "反應"]
    assert (rules.max_keywords, rules.max_elements, rules.max_effects) == (2, 1, 2)
    assert (rules.max_shapes, rules.max_kinds) == (1, 1)
    lib = library()
    assert len(lib.keywords.keywords) == 16
    prims = {p.id for p in lib.ruleset.primitives.primitives}
    statuses = {s.id for s in lib.ruleset.statuses.statuses}
    shapes = {s.id for s in lib.ruleset.shapes.shapes}
    for tag in rules.effects:
        assert set(tag.primitives) <= prims, tag.id
        assert set(tag.statuses) <= statuses, tag.id
    for shape in rules.shapes:
        assert set(shape.shapes) <= shapes, shape.id


def test_clean_drops_only_the_bad_items() -> None:
    """清單外、重複、超過上限的那一項丟掉，其餘照用（07 7.6「其餘照用」）。"""
    raw = {
        "keywords": ["ignite", "nope", "ignite", "frozen", "summon"],
        "elements": ["fire", "ice"],
        "effects": ["damage", "laser"],
        "shapes": [],
        "kinds": ["reaction"],
    }
    tags, codes = clean_wish_tags(library(), raw, MENU)
    assert tags == WishTags(
        keywords=("ignite", "frozen"),
        elements=("fire",),
        effects=("damage",),
        kinds=("reaction",),
    )
    assert codes.count("wish.dropped.keywords") == 3
    assert codes.count("wish.dropped.elements") == 1
    assert codes.count("wish.dropped.effects") == 1
    empty, _ = clean_wish_tags(library(), {}, MENU)
    assert empty.empty()


def test_problem_checks_lists_limits_and_at_least_one() -> None:
    lib = library()
    assert wish_tags_problem(lib, WishTags(keywords=("ignite",)), MENU) is None
    assert wish_tags_problem(lib, WishTags(), MENU) is None
    assert wish_tags_problem(lib, WishTags(), MENU, require_one=True) == "至少要選一個標籤"
    assert wish_tags_problem(lib, WishTags(keywords=("ki",)), MENU) is not None  # 不在選單
    assert wish_tags_problem(lib, WishTags(elements=("fire", "ice")), MENU) is not None
    assert wish_tags_problem(lib, WishTags(effects=("damage", "damage")), MENU) is not None
    assert wish_tags_problem(lib, WishTags(shapes=("star",)), MENU) is not None


def test_hits_and_the_honest_line() -> None:
    """命中由程式依技能資料判定；做不到的那一行照 07 7.6 第 5 點的字。"""
    lib = library()
    bolt = lib.skills["skill_fire_bolt"]
    mine = skill_tag_ids(lib, bolt)
    assert "fire" in mine.elements and "damage" in mine.effects
    assert mine.kinds == ("active",)
    all_hit = WishTags(elements=("fire",), effects=("damage",))
    assert tag_hits(lib, bolt, all_hit) == (("火焰", "傷害"), ())
    assert wish_miss_zh(lib, bolt, all_hit) is None
    some = WishTags(keywords=("summon",), elements=("fire",))
    assert wish_miss_zh(lib, bolt, some) == "最接近你願望的一招：有火焰；召喚物這次做不到。"
    none = WishTags(effects=("summon",))
    assert wish_miss_zh(lib, bolt, none) == "最接近你願望的一招：召喚這次做不到。"
    assert wish_miss_zh(lib, bolt, WishTags()) is None
    assert tag_labels(lib, some) == ("召喚物", "火焰")
