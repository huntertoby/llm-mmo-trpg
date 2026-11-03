"""區域圖（只能看）的迷霧、任務標記與傳送石（Phase 6C-6；21.1、21.2、21.9 第 3、13 條）。

- **迷霧三段**：去過的地點（``visited_locations``，加上目前位置與到過小鎮的那一區的城鎮——舊存檔
  沒有紀錄時也看得到）是 ``visited``；和去過的相連（照畫出來的連線）但沒去過的是 ``silhouette``；
  其他是 ``fog``。隱藏地點在發現前本來就不在回應裡（:func:`trpg.api.world_presenter._visible`）。
- **任務標記**：進行中任務的目前這一步，條件是「在某地點」或「在某地點打贏」時標在那個地點。
- **傳送石**：只列去過或剪影地點的室外圖上的傳送石；``can_teleport`` 照
  :func:`trpg.world.field.teleport_origin`（站在傳送石上或在城鎮裡），規則仍由引擎的
  ``use_teleport_stone`` 檢查。
"""

from __future__ import annotations

from collections.abc import Iterable

from trpg.api.world_field_things import FOOTPRINT_NAMES, FieldSocial
from trpg.api.world_schemas import RegionStoneView, WorldLocationView, WorldMapView
from trpg.content.library import ContentLibrary
from trpg.content.world_narration import mask_text
from trpg.content.world_quests import AnyOf, AtLocation, QuestCondition, WinBattle
from trpg.world.field import placed, teleport_origin
from trpg.world.narration import story_masks
from trpg.world.quests import quest_table
from trpg.world.state import CharacterState

__all__ = ["fog_levels", "region_marks"]


def _visited(char: CharacterState, region: str, town: str) -> set[str]:
    seen = {r.location for r in char.visited_locations if r.region == region}
    if char.region == region:
        seen.add(char.location)
    if region in char.visited_towns:
        seen.add(town)
    return seen


def fog_levels(
    locations: Iterable[str], edges: Iterable[tuple[str, str]], visited: set[str]
) -> dict[str, str]:
    """每個地點的迷霧：去過＝``visited``、和去過的相連＝``silhouette``、其他＝``fog``。"""
    near: set[str] = set()
    for a, b in edges:
        if a in visited:
            near.add(b)
        if b in visited:
            near.add(a)
    out: dict[str, str] = {}
    for loc in locations:
        if loc in visited:
            out[loc] = "visited"
        elif loc in near:
            out[loc] = "silhouette"
        else:
            out[loc] = "fog"
    return out


def _targets(condition: QuestCondition) -> list[str]:
    leaves = condition.conditions if isinstance(condition, AnyOf) else (condition,)
    out: list[str] = []
    for leaf in leaves:
        place = leaf.location if isinstance(leaf, AtLocation | WinBattle) else None
        if place is not None:
            out.append(place)
    return out


def _quest_marks(library: ContentLibrary, char: CharacterState) -> dict[str, list[str]]:
    table = quest_table(library, char.region)
    if table is None:
        return {}
    defs = table.quest_by_id()
    masks = story_masks(library, char)
    marks: dict[str, list[str]] = {}
    for state in sorted(char.quests, key=lambda q: q.quest):
        defn = defs.get(state.quest)
        if defn is None or state.done or state.steps_done >= len(defn.steps):
            continue
        step = defn.steps[state.steps_done]
        places = sorted({loc for cond in step.when for loc in _targets(cond)})
        for loc in places:
            marks.setdefault(loc, []).append(mask_text(defn.name_zh, masks))
    return marks


def _teleport_problem(char: CharacterState, origin: str | None, in_battle: bool) -> str | None:
    if in_battle:
        return "戰鬥進行中"
    if char.pending_encounter is not None:
        return "先處理眼前的遭遇"
    if char.pending_flash is not None:
        return "先選完閃現的變化"
    if char.pending_offers:
        return "先選完任務給的技能"
    if origin is None:
        return "站在傳送石上或在城鎮裡打開地圖，才能點傳送石傳送"
    return None


def _stones(
    library: ContentLibrary, char: CharacterState, region: str, shown: dict[str, str]
) -> tuple[list[RegionStoneView], str | None]:
    """這一區看得到的傳送石（依 ID）與現在出發的那一顆。"""
    here = placed(library, char)
    origin = teleport_origin(library, here) if here.region == region else None
    stones: list[RegionStoneView] = []
    for map_id in sorted(library.field_maps):
        found = library.field_maps[map_id]
        loc = found.location
        if found.region != region or loc is None or shown.get(loc, "fog") == "fog":
            continue
        stones.extend(
            RegionStoneView(
                id=s.id,
                location=loc,
                unlocked=s.id in char.teleport_stones,
                here=s.id == origin,
            )
            for s in found.teleport_stones
        )
    stones.sort(key=lambda s: s.id)
    return stones, origin


def region_marks(
    library: ContentLibrary,
    char: CharacterState,
    view: WorldMapView,
    *,
    town: str,
    in_battle: bool,
    social: FieldSocial | None = None,
) -> WorldMapView:
    """在地點圖的回應上加上迷霧、任務標記、傳送石與能不能從圖上傳送（6C-6）；朋友的足跡（6C-5：
    去過的其他角色，依角色 ID 最多 :data:`FOOTPRINT_NAMES` 位，霧裡的不給）。"""
    visited = _visited(char, view.region, town)
    fog = fog_levels((loc.id for loc in view.locations), view.edges, visited)
    marks = _quest_marks(library, char) if char.region == view.region else {}

    def one(loc: WorldLocationView) -> WorldLocationView:
        level = fog[loc.id]
        update: dict[str, object] = {"fog": level}
        if level != "fog" and loc.id in marks:
            update["quest_marks"] = tuple(marks[loc.id])
        if level != "fog" and social is not None:
            visitors = social.visitors_at(view.region, loc.id)[:FOOTPRINT_NAMES]
            if visitors:
                update["footprints"] = tuple(v.name_zh for v in visitors)
        return loc.model_copy(update=update)

    stones, origin = _stones(library, char, view.region, fog)
    problem = _teleport_problem(char, origin, in_battle)
    return view.model_copy(
        update={
            "locations": tuple(one(loc) for loc in view.locations),
            "stones": tuple(stones),
            "can_teleport": problem is None,
            "teleport_problem_zh": problem,
        }
    )
