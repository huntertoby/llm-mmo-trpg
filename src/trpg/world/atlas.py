"""大世界圖與主城的規則（Phase 6D-5；21.1、21.9 第 4、5 條、9.6.5）。

- **主城**：``region``／``location`` 都是 ``capital``（:func:`trpg.world.common.in_capital`）；
  地點圖是內容檔 ``content/world/maps/capital.yaml``（``hub: true``，6D-R2）的一個城鎮地點。
  主城的傳送石**一開始就解鎖**（:func:`unlocked_stones`），不寫進 ``teleport_stones``（存檔不變）。
- **區域亮起**（:func:`region_lit`）：到過那一區的小鎮，或走進過那一區的任何地點
  （``visited_locations``）。灰燼荒原只能從雲嶺的渡口走過去，所以「走進過荒原的地點」＝親自
  走過渡口、抵達灰渡口（21.1）。
- **三種狀態**（:func:`region_state`）：``open``（已開放：亮起或主城）、``locked``（有地點圖、
  還沒亮起：寫解鎖條件）、``later``（``regions.yaml`` 有、這一季沒有地點圖：「之後的賽季」）。
- **第一次傳送免費**（6F-2，#125、21 21.5）：角色在主城、還沒到過新手區
  （``world/newcomer.yaml`` 的 ``start_region``）的小鎮（``visited_towns`` 沒有它）時，主城可以直接
  傳到那一區的小鎮，不必先解鎖那邊的傳送石（:func:`free_first_teleport`、:func:`can_teleport_to`、
  :func:`unlocked_stones`）。不另加旗標：到過之後就照 #120 的一般規則；舊存檔的角色建角時就到過
  起始區的小鎮，不受影響。

確定性：只看內容、世界旗標與角色狀態；清單依 ``regions.yaml`` 的順序（守則 2）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.fields import CAPITAL_LOCATION, CAPITAL_NAME_ZH, CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "LATER_ZH",
    "RegionState",
    "RegionStatus",
    "atlas_regions",
    "can_teleport_to",
    "capital_stone",
    "cross_gate",
    "free_first_stone",
    "free_first_teleport",
    "region_lit",
    "region_name",
    "region_state",
    "unlocked_stones",
]

type RegionStatus = Literal["open", "locked", "later"]

LATER_ZH = "之後的賽季"


@dataclass(frozen=True)
class RegionState:
    region: str
    name_zh: str
    status: RegionStatus
    condition_zh: str | None = None
    """``locked`` 的解鎖條件、``later`` 的「之後的賽季」；``open`` 是 ``None``。"""
    town: str | None = None
    """這一區的城鎮地點（沒有地點圖＝``None``）。"""
    town_name_zh: str | None = None


def capital_stone(library: ContentLibrary) -> str | None:
    """主城的傳送石 ID（主城實地地圖上的第一顆；沒有主城＝``None``）。"""
    found = library.field_maps.get(CAPITAL_LOCATION)
    if found is None or not found.teleport_stones:
        return None
    return found.teleport_stones[0].id


def free_first_teleport(library: ContentLibrary, char: CharacterState, region: str) -> bool:
    """``region`` 是新手區、角色在主城、還沒到過那一區的小鎮：第一次傳送免費（6F-2，#125）。"""
    newcomer = library.world_newcomer
    return (
        newcomer is not None
        and region == newcomer.start_region
        and char.region == CAPITAL_REGION
        and region not in char.visited_towns
        and library.location_map(region) is not None
    )


def free_first_stone(library: ContentLibrary, char: CharacterState) -> str | None:
    """第一次免費傳送的目的地傳送石（新手區小鎮實地地圖上的第一顆；不適用＝``None``）。"""
    newcomer = library.world_newcomer
    if newcomer is None or not free_first_teleport(library, char, newcomer.start_region):
        return None
    world_map = library.location_map(newcomer.start_region)
    town = None if world_map is None else library.outdoor_map(world_map.region, world_map.town)
    if town is None or not town.teleport_stones:
        return None
    return town.teleport_stones[0].id


def unlocked_stones(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """能傳過去的傳送石：走到過的，加上主城的（一開始就解鎖），第一次免費傳送時再加上新手區小鎮的
    （6F-2；排序、不重複）。"""
    extra = {s for s in (capital_stone(library), free_first_stone(library, char)) if s is not None}
    if extra <= set(char.teleport_stones):
        return char.teleport_stones
    return tuple(sorted({*char.teleport_stones, *extra}))


def region_lit(char: CharacterState, region: str) -> bool:
    """這一區在自己的大世界圖上亮起（可以從城鎮傳送過去；21.1）。"""
    if region == CAPITAL_REGION or region in char.visited_towns:
        return True
    return any(r.region == region for r in char.visited_locations)


def can_teleport_to(library: ContentLibrary, char: CharacterState, region: str) -> bool:
    """從城鎮或傳送石能不能傳到 ``region``：亮起了，或第一次免費傳送（6F-2）。"""
    return region_lit(char, region) or free_first_teleport(library, char, region)


def region_name(library: ContentLibrary, region: str) -> str:
    if region == CAPITAL_REGION:
        return CAPITAL_NAME_ZH
    world_map = library.location_map(region)
    if world_map is not None:
        return world_map.name_zh
    table = library.regions
    found = None if table is None else table.region_by_id().get(region)
    return region if found is None else found.name_zh


def _gates_into(library: ContentLibrary, region: str) -> list[tuple[str, LocationDef]]:
    """別區通往 ``region`` 的渡口（區域、地點；依區域與地點 ID 排序）。"""
    out: list[tuple[str, LocationDef]] = []
    for other, world_map in sorted(library.world_maps.items()):
        if other == region:
            continue
        for loc in sorted(world_map.locations, key=lambda loc: loc.id):
            if loc.kind == "gate" and loc.gate_to == region:
                out.append((other, loc))
    return out


def _flag_event_name(library: ContentLibrary, flag: str) -> str | None:
    season = library.world_season
    if season is None:
        return None
    for event in season.world_events:
        if flag in event.on_success.flags or flag in event.on_failure.flags:
            return event.name_zh
    return None


def _condition(library: ContentLibrary, world: WorldState, region: str) -> str:
    gates = _gates_into(library, region)
    for _other, gate in gates:
        flag = gate.unlock_flag
        if flag is not None and not world.has_flag(flag):
            event = _flag_event_name(library, flag)
            return f"世界事件：{event}" if event is not None else "還沒開放"
    if gates:
        other, gate = gates[0]
        return f"先走過{region_name(library, other)}的「{gate.name_zh}」"
    return "還沒開放"


def region_state(
    library: ContentLibrary, world: WorldState, char: CharacterState, region: str
) -> RegionState:
    name = region_name(library, region)
    world_map = library.location_map(region)
    if region == CAPITAL_REGION:  # 城鎮名＝主城實地地圖的名字（暫名「樞島」）
        found = library.field_maps.get(CAPITAL_LOCATION)
        town_name = name if found is None else found.name_zh
        return RegionState(region, name, "open", town=CAPITAL_LOCATION, town_name_zh=town_name)
    if world_map is None:
        return RegionState(region, name, "later", LATER_ZH)
    town = world_map.location_by_id()[world_map.town]
    if can_teleport_to(library, char, region):  # 6F-2：第一次免費傳送的新手區也算開放
        return RegionState(region, name, "open", town=town.id, town_name_zh=town.name_zh)
    condition = _condition(library, world, region)
    return RegionState(region, name, "locked", condition, town=town.id, town_name_zh=town.name_zh)


def atlas_regions(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> tuple[RegionState, ...]:
    """大世界圖的五區（``regions.yaml`` 的順序；沒有區域表時用有地點圖的區，依 ID）。"""
    table = library.regions
    ids = [r.id for r in table.regions] if table is not None else sorted(library.world_maps)
    return tuple(region_state(library, world, char, r) for r in ids)


def cross_gate(library: ContentLibrary, region: str, location: str) -> bool:
    """``location`` 是有實地地圖、而且畫了跨區出口的渡口：要走出口過去，不能直接傳送（21.1：
    第一次要親自走過渡口）。"""
    found = library.outdoor_map(region, location)
    return found is not None and any(
        e.region is not None and e.region != region for e in found.exits
    )
