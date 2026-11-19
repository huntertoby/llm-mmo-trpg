"""WC-2 第 2 項：一招一個形狀、一個種類，照現狀（#167 第 2 題維持；07 7.6 第 2 點「一招一個形狀、
一個種類」）。角色階級再高，願望的形狀、種類也都最多 1 個；只有元素 2 階起放寬（第 1 項）。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.content.skill_pick import WishTags
from trpg.skillgen.wish_pick import clean_wish_tags, tag_limits, wish_tags_problem


def test_one_shape_and_one_kind_at_every_tier() -> None:
    lib = library()
    for tier in range(1, lib.budget.min_character_tier.highest() + 2):
        limits = tag_limits(lib, tier)
        assert (limits["shapes"], limits["kinds"]) == (1, 1), tier
        two_shapes = WishTags(shapes=("cone", "line"))
        assert wish_tags_problem(lib, two_shapes, (), tier=tier) == "形狀最多選 1 個"
        two_kinds = WishTags(kinds=("active", "passive"))
        assert wish_tags_problem(lib, two_kinds, (), tier=tier) == "種類最多選 1 個"
        raw = {"shapes": ["cone", "line"], "kinds": ["active", "reaction"]}
        tags, codes = clean_wish_tags(lib, raw, (), tier=tier)
        assert (tags.shapes, tags.kinds) == (("cone",), ("active",))
        assert codes == ("wish.dropped.shapes", "wish.dropped.kinds")
