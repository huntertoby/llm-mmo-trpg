"""``trpg.world`` 各模組共用的小工具：取內容、角色的 HP 與法力上限。

5A-2 寫在 ``step``，5A-4 抽出來給 ``battle``、``town`` 共用。
"""

from __future__ import annotations

from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.content.world_rules import WorldRules
from trpg.shared.types import Attribute
from trpg.world.errors import WorldError
from trpg.world.state import CharacterState

__all__ = [
    "capital_map",
    "here",
    "in_capital",
    "location_level",
    "max_hp",
    "max_mana",
    "rules_of",
    "world_map_of",
]


def rules_of(library: ContentLibrary) -> WorldRules:
    if library.world_rules is None:
        raise WorldError("內容庫沒有 world/rules.yaml")
    return library.world_rules


def capital_map(library: ContentLibrary) -> LocationMapDef:
    """主城的地點圖（6D-5；6D-R2 起是內容檔 ``content/world/maps/capital.yaml``，``hub: true``）：
    只有一個城鎮地點 ``capital``、沒有連線，讓「所在地點是城鎮」的既有規則直接套用。"""
    return world_map_of(library, CAPITAL_REGION)


def in_capital(char: CharacterState) -> bool:
    """角色在主城（含室內；6D-5：``region``、``location`` 都是 ``capital``）。"""
    return char.region == CAPITAL_REGION


def world_map_of(library: ContentLibrary, region: str) -> LocationMapDef:
    """``region`` 的地點圖（含主城，:meth:`ContentLibrary.location_map`）；沒有就拋 ``WorldError``
    （不會 ``KeyError``；6D-R2：存取一律經這裡）。"""
    found = library.location_map(region)
    if found is None:
        raise WorldError(f"沒有區域 {region} 的地點圖")
    return found


def here(library: ContentLibrary, char: CharacterState) -> LocationDef:
    """角色目前所在的地點。"""
    return world_map_of(library, char.region).location_by_id()[char.location]


def location_level(library: ContentLibrary, region: str, location: str, default: int = 1) -> int:
    """地點的建議等級下限（``level_min``）；沒有地點或沒標等級時用 ``default``。"""
    found = world_map_of(library, region).location_by_id().get(location)
    if found is None or found.level_min is None:
        return default
    return found.level_min


def max_hp(library: ContentLibrary, char: CharacterState) -> int:
    """最大 HP（同 ``RunState.max_hp_in``）。"""
    core = library.ruleset.core
    return core.run_max_hp(char.hero.max_hp, char.hero.attributes[Attribute.CON], char.level)


def max_mana(library: ContentLibrary, char: CharacterState) -> int:
    """法力上限（同 ``RunState.max_mana_in``）。"""
    core = library.ruleset.core
    return core.resources.max_for("mana", core.template_mana(char.hero), char.hero.attributes)
