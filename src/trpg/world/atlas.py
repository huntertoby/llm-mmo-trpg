"""大世界圖與主城的規則（Phase 6D-5；21.1、21.9 第 4、5 條、9.6.5）。

- **主城**：``region``／``location`` 都是 ``capital``（:func:`trpg.world.common.in_capital`）；
  地點圖是 :func:`trpg.world.common.capital_map` 臨時組的一個城鎮地點。主城的傳送石
  **一開始就解鎖**（:func:`unlocked_stones`），不寫進 ``teleport_stones``（存檔不變）。
- **區域亮起**（:func:`region_lit`）：到過那一區的小鎮，或走進過那一區的任何地點
  （``visited_locations``）。灰燼荒原只能從雲嶺的渡口走過去，所以「走進過荒原的地點」＝親自
  走過渡口、抵達灰渡口（21.1）。
- **三種狀態**（:func:`region_state`）：``open``（已開放：亮起或主城）、``locked``（有地點圖、
  還沒亮起：寫解鎖條件）、``later``（``regions.yaml`` 有、這一季沒有地點圖：「之後的賽季」）。

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
    "capital_stone",
    "cross_gate",
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


def unlocked_stones(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """能傳過去的傳送石：走到過的，加上主城的（一開始就解鎖；排序、不重複）。"""
    stone = capital_stone(library)
    if stone is None or stone in char.teleport_stones:
        return char.teleport_stones
    return tuple(sorted({*char.teleport_stones, stone}))


def region_lit(char: CharacterState, region: str) -> bool:
    """這一區在自己的大世界圖上亮起（可以從城鎮傳送過去；21.1）。"""
    if region == CAPITAL_REGION or region in char.visited_towns:
        return True
    return any(r.region == region for r in char.visited_locations)


def region_name(library: ContentLibrary, region: str) -> str:
    if region == CAPITAL_REGION:
        return CAPITAL_NAME_ZH
    world_map = library.world_maps.get(region)
    if world_map is not None:
        return world_map.name_zh
    table = library.regions
    found = None if table is None else table.region_by_id().get(region)
    return region if found is None else found.name_zh


def _gates_into(library: ContentLibrary, region: str) -> list[tuple[str, LocationDef]]:
    """別區通往 ``region`` 的渡口（區域、地點；依區域與地點 ID 排序）。"""
    out: list[tuple[str, LocationDef]] = []
    for other in sorted(library.world_maps):
        if other == region:
            continue
        for loc in sorted(library.world_maps[other].locations, key=lambda loc: loc.id):
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
    world_map = library.world_maps.get(region)
    if region == CAPITAL_REGION:  # 城鎮名＝主城實地地圖的名字（暫名「樞島」）
        found = library.field_maps.get(CAPITAL_LOCATION)
        town_name = name if found is None else found.name_zh
        return RegionState(region, name, "open", town=CAPITAL_LOCATION, town_name_zh=town_name)
    if world_map is None:
        return RegionState(region, name, "later", LATER_ZH)
    town = world_map.location_by_id()[world_map.town]
    if region_lit(char, region):
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
    for map_id in sorted(library.field_maps):
        found = library.field_maps[map_id]
        if found.region == region and found.location == location and not found.is_interior:
            return any(e.region is not None and e.region != region for e in found.exits)
    return False
