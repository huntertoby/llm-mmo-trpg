"""E6-b2 第 5 項（WM-1 待決 9）：大世界的主角面板照角色身上穿的裝備算，不是照主角範本的裝備。"""

from __future__ import annotations

from tests.roguelite.signature_helpers import GRAPPLE, gear_item, sig_library
from tests.world.helpers import hero, make_world, without_fields
from trpg.api.world_growth_view import clear_hero_panel_cache, hero_panel
from trpg.content.equipment import AffixRoll, ItemDef
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.world.step import new_character

STR_ITEM = ItemDef(
    id="item_e6b2_str_gloves",
    name_zh="力量手套",
    slot_type="hands",
    rarity="rare",
    affixes=(AffixRoll(affix="affix_attr_str", value=30),),
)


def test_panel_counts_the_worn_equipment(content_library: ContentLibrary) -> None:
    lib = without_fields(content_library)
    world = make_world()
    char = new_character(lib, "alice", hero(lib), region="cloud_ridge")
    clear_hero_panel_cache()
    bare = hero_panel(lib, world, char)[0]
    worn = hero_panel(lib, world, char.model_copy(update={"equipment": {"hands": STR_ITEM}}))[0]
    strength = Attribute.STR
    assert worn.effective_attributes[strength] == bare.effective_attributes[strength] + 30
    hands = next(s for s in worn.equipment if s.slot == "hands")
    assert hands.item is not None and hands.item.id == STR_ITEM.id


def test_panel_shows_signatures_with_the_picks(content_library: ContentLibrary) -> None:
    lib = sig_library(without_fields(content_library))
    char = new_character(lib, "alice", hero(lib), region="cloud_ridge")
    char = char.model_copy(
        update={
            "equipment": {"hands": gear_item("g", "hands", GRAPPLE)},
            "gear_chosen": (f"hands:{GRAPPLE}",),
        }
    )
    clear_hero_panel_cache()
    panel = hero_panel(lib, make_world(), char)[0].signatures
    assert panel is not None and panel.chosen == (f"hands:{GRAPPLE}",)
    assert panel.count_zh == "生效 1／3"
