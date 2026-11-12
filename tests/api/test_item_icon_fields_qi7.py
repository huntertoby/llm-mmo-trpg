"""物品 view 的 ``color``／``rare``（QI-7 物品圖示；物品移植需求第 5 節第 1、2 點）。

染料帶 ``items.yaml`` 的 ``color``、材料帶 ``rare``（不是材料為 ``None``），
前端照它選染料色與框線色。
"""

from __future__ import annotations

from trpg.api.world_economy_view import _bag_item, item_rare
from trpg.api.world_mail_view import _items
from trpg.content.library import ContentLibrary


def test_bag_item_carries_dye_color_and_material_rare(library: ContentLibrary) -> None:
    items = library.world_economy.items
    for item_id, found in sorted(items.items()):
        view = _bag_item(library, item_id, 1)
        assert view.color == found.color
        assert view.rare == (found.rare if found.kind == "material" else None)
    assert _bag_item(library, "item_dye_indigo", 1).color == "#2E4A7D"
    assert _bag_item(library, "item_living_bone", 1).rare is True
    assert _bag_item(library, "item_wolf_fang", 1).rare is False
    assert _bag_item(library, "item_hp_potion_small", 1).rare is None


def test_rare_materials_match_art_table(library: ContentLibrary) -> None:
    """美術 PM 決定：稀有材料一律品質 3（紫框）。前端表的稀有四個要和 content 一致。"""
    rare = sorted(i for i, d in library.world_economy.items.items() if item_rare(d) is True)
    assert rare == [
        "item_frost_ember",
        "item_living_bone",
        "item_molten_heart",
        "item_summit_mist_crystal",
    ]


def test_letter_items_carry_color_and_rare(library: ContentLibrary) -> None:
    rows = _items(library, {"item_dye_jade": 2, "item_frost_ember": 1, "ghost": 1})
    by = {r.item: r for r in rows}
    assert by["item_dye_jade"].color == "#3E8E6A" and by["item_dye_jade"].rare is None
    assert by["item_frost_ember"].rare is True and by["item_frost_ember"].color is None
    assert by["ghost"].color is None and by["ghost"].rare is None
