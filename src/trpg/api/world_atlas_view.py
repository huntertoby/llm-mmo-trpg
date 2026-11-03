"""大世界圖的回應（Phase 6D-5；21.1、9.6.5）。

規則在 :mod:`trpg.world.atlas`（區域三種狀態、亮起條件）與
:func:`trpg.world.town.teleport`（傳送）；這裡只把狀態排成畫面要的格式。``can_teleport`` 照
:func:`trpg.world.field.teleport_origin`（站在傳送石上或在城鎮裡），而且沒有遭遇、閃現、
三選一、戰鬥。
"""

from __future__ import annotations

from trpg.api.world_schemas import AtlasRegionView, AtlasView
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.world.atlas import RegionState, atlas_regions, region_state
from trpg.world.field import placed, teleport_origin
from trpg.world.state import CharacterState, WorldState

__all__ = ["atlas_view"]


def _problem(library: ContentLibrary, char: CharacterState, in_battle: bool) -> str | None:
    if in_battle:
        return "戰鬥進行中"
    if char.pending_encounter is not None:
        return "先處理眼前的遭遇"
    if char.pending_flash is not None:
        return "先選完閃現的變化"
    if char.pending_offers:
        return "先選完任務給的技能"
    if teleport_origin(library, placed(library, char)) is None:
        return "站在傳送石上或在城鎮裡打開地圖，才能點城鎮傳送"
    return None


def _one(state: RegionState, char: CharacterState, *, can: bool) -> AtlasRegionView:
    current = state.region == char.region
    return AtlasRegionView(
        region=state.region,
        name_zh=state.name_zh,
        status=state.status,
        condition_zh=state.condition_zh,
        town=state.town,
        town_name_zh=state.town_name_zh,
        current=current,
        can_teleport=can and state.status == "open" and not current,
    )


def atlas_view(
    library: ContentLibrary, world: WorldState, char: CharacterState, *, in_battle: bool = False
) -> AtlasView:
    problem = _problem(library, char, in_battle)
    can = problem is None
    regions = tuple(_one(s, char, can=can) for s in atlas_regions(library, world, char))
    capital = _one(region_state(library, world, char, CAPITAL_REGION), char, can=can)
    return AtlasView(
        regions=regions, capital=capital, can_teleport=can, teleport_problem_zh=problem
    )
