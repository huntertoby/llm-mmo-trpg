"""世界畫面的實地地圖（Phase 6B-2；3.5）：目前地圖的地形、物件、出口、門、傳送石、NPC、設施與自己的
位置。舊存檔沒有位置時照 :func:`trpg.world.field.placed` 放到 ``entry``（只算，不寫檔）。

**隱藏門（6D-R1）**：還沒發現的隱藏門格在地形裡畫成牆（:data:`HIDDEN_DOOR_TERRAIN`，不可站、沒有
表面），和真的牆分不出來；靜態地形（:func:`field_tiles`）一律這樣畫，發現之後那一格的真地形放在
``FieldView.open_cells``，前端蓋上去。靜態地形只給看得到這張圖的角色（:func:`visible_field_map`）。"""

from __future__ import annotations

import hashlib
import json
from typing import Final

from trpg.api.world_field_people import ALERT_ZH, friends_here, look_of, npc_marks
from trpg.api.world_field_schemas import (
    FieldDoorView,
    FieldEnemyUnitView,
    FieldEnemyView,
    FieldExitView,
    FieldFacilityView,
    FieldHeroView,
    FieldNpcView,
    FieldObjectView,
    FieldPositionView,
    FieldStoneTargetView,
    FieldStoneView,
    FieldTilesView,
    FieldTileView,
    FieldView,
)
from trpg.api.world_field_things import FieldSocial, things_update
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.actions import WorldEvent
from trpg.world.encounters import EncounterLineup, LineupMember, elite_kinds
from trpg.world.field import (
    FieldGrid,
    exit_open,
    field_grid,
    field_map,
    hidden_cells,
    hidden_door,
    placed,
)
from trpg.world.field_actions import (
    ExitBlockedEvent,
    FieldEnteredEvent,
    TeleportStoneUnlockedEvent,
    TeleportStoneUsedEvent,
)
from trpg.world.field_enemies import FieldEnemy, enemy_lineup, field_enemies
from trpg.world.gear import hero_loadout
from trpg.world.narration import region_npcs
from trpg.world.state import CharacterState, WorldState

__all__ = ["HIDDEN_DOOR_TERRAIN", "field_line", "field_tiles", "field_view", "visible_field_map"]

type XY = tuple[int, int]

HIDDEN_DOOR_TERRAIN: Final = "wall"
"""還沒發現的隱藏門格畫成的地形（6D-R1；戰鬥規則的牆，前端本來就會畫）。"""


def field_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """實地地圖事件的句子：走進室內、傳送石。走格子本身不出句子（21.7 文字減量）；踩出口換地點的
    句子是原本的「走到…」。"""
    if isinstance(event, FieldEnteredEvent):
        inner = None if event.map is None else field_map(library, event.map)
        if inner is not None and inner.is_interior:
            return f"走進{_map_name(library, inner)}。"
        return None
    if isinstance(event, ExitBlockedEvent):  # 6E-1（#122）：霧牆擋住
        return event.text_zh
    if isinstance(event, TeleportStoneUnlockedEvent):
        return "傳送石亮了起來，之後可以從別的傳送石傳過來。"
    if isinstance(event, TeleportStoneUsedEvent):
        return f"經傳送石到了{_place_name(library, event.region, event.location)}。"
    return None


def _place_name(library: ContentLibrary, region: str, location: str) -> str:
    world_map = library.location_map(region)
    found = None if world_map is None else world_map.location_by_id().get(location)
    return location if found is None else found.name_zh


def _map_name(library: ContentLibrary, found: FieldMapDef) -> str:
    return found.name_zh or _place_name(library, found.region, found.place)


def visible_field_map(
    library: ContentLibrary, char: CharacterState, map_id: str
) -> FieldMapDef | None:
    """``char`` 看得到的實地地圖（6D-R1；看不到和不存在一樣是 ``None``，不能拿來列舉地圖 ID）：
    目前地點的室外圖與它的室內圖，或去過（``visited_locations``）、已發現（``revealed``）的地點的
    室外圖與室內圖。隱藏地點沒發現、還沒走到的區域都看不到。"""
    found = field_map(library, map_id)
    if found is None:
        return None
    places = {(r.region, r.location) for r in (*char.visited_locations, *char.revealed)}
    places.add((char.region, char.location))
    return found if (found.region, found.place) in places else None


_TILES: dict[tuple[int, str], tuple[ContentLibrary, FieldTilesView]] = {}
"""（內容庫, 地圖 ID）→ 靜態地形（存著內容庫本身，``id`` 不會被重用）。"""
_TILES_MAX: Final = 256


def field_tiles(library: ContentLibrary, map_id: str) -> FieldTilesView | None:
    """實地地圖的靜態地形與內容雜湊（6C-R3；沒有這張圖＝``None``）。同一個內容庫只算一次。"""
    cached = _TILES.get((id(library), map_id))
    if cached is not None and cached[0] is library:
        return cached[1]
    found = field_map(library, map_id)
    if found is None:
        return None
    tiles = _tiles(found, field_grid(library, None, found), hidden_cells(None, found))
    text = json.dumps(
        [found.width, found.height, [t.model_dump(mode="json") for t in tiles]],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    view = FieldTilesView(
        map_id=found.id, hash=digest, width=found.width, height=found.height, tiles=tiles
    )
    if len(_TILES) >= _TILES_MAX:
        _TILES.clear()
    _TILES[(id(library), map_id)] = (library, view)
    return view


def _open_cells(
    found: FieldMapDef, char: CharacterState, grid: FieldGrid
) -> tuple[FieldTileView, ...]:
    """靜態地形畫成牆、這個角色已經發現的隱藏門格：這一格真正的地形（6D-R1；前端蓋在靜態地形上）。"""
    revealed = hidden_cells(None, found) - hidden_cells(char, found)
    rows = found.grid()
    surfaces = _surfaces(found)
    return tuple(
        _tile((x, y), rows[y][x], surfaces, grid, hidden=frozenset())
        for x, y in sorted(revealed, key=lambda c: (c[1], c[0]))
    )


def _surfaces(found: FieldMapDef) -> dict[XY, str]:
    return {s.at: str(s.surface) for s in found.surfaces}


def _tile(
    cell: XY,
    height_terrain: tuple[int, str],
    surfaces: dict[XY, str],
    grid: FieldGrid,
    *,
    hidden: frozenset[XY],
) -> FieldTileView:
    x, y = cell
    height, terrain = height_terrain
    if cell in hidden:  # 還沒發現的隱藏門：畫成牆，和真的牆分不出來（6D-R1）
        return FieldTileView(x=x, y=y, height=height, terrain=HIDDEN_DOOR_TERRAIN, walkable=False)
    return FieldTileView(
        x=x,
        y=y,
        height=height,
        terrain=terrain,
        surface=surfaces.get(cell, "none"),
        walkable=grid.standable(cell),
    )


def _tiles(found: FieldMapDef, grid: FieldGrid, hidden: frozenset[XY]) -> tuple[FieldTileView, ...]:
    """整張圖的地形；``hidden`` 的格子（還沒發現的隱藏門）畫成牆。"""
    surfaces = _surfaces(found)
    return tuple(
        _tile((x, y), cell, surfaces, grid, hidden=hidden)
        for y, row in enumerate(found.grid())
        for x, cell in enumerate(row)
    )


def _doors(
    library: ContentLibrary, char: CharacterState, found: FieldMapDef
) -> tuple[FieldDoorView, ...]:
    out: list[FieldDoorView] = []
    for door in found.doors:
        if hidden_door(char, found, door):
            continue
        inner = field_map(library, door.to)
        name = (
            _map_name(library, inner)
            if inner is not None
            else _place_name(library, found.region, door.to)
        )
        out.append(
            FieldDoorView(id=door.id, x=door.at[0], y=door.at[1], to=door.to, to_name_zh=name)
        )
    return tuple(out)


def _hero(library: ContentLibrary, char: CharacterState) -> FieldHeroView:
    """主角外觀（同戰鬥 ``UnitView`` 的 ``doll_look``、武器、種族外觀與裝備外觀；純顯示）。"""
    return look_of(library, char.hero, hero_loadout(library, char))


def _npcs(
    library: ContentLibrary,
    world: WorldState | None,
    char: CharacterState,
    found: FieldMapDef,
    now: int,
) -> tuple[FieldNpcView, ...]:
    """地圖上的 NPC：名稱、好感級別與頭上的「！」（6B-4）。人設卡沒有外觀資料，``look`` 留空。"""
    cards = region_npcs(library, found.region)
    marks = npc_marks(library, world, char, [n.id for n in found.npcs], now)
    out: list[FieldNpcView] = []
    for n in found.npcs:
        mark = marks[n.id]
        out.append(
            FieldNpcView(
                id=n.id,
                name_zh=cards[n.id].name_zh if n.id in cards else n.id,
                x=n.at[0],
                y=n.at[1],
                rank=mark.rank,
                rank_zh=mark.rank_zh,
                alert=mark.alert,
                alert_zh=None if mark.alert is None else ALERT_ZH[mark.alert],
                portrait=cards[n.id].portrait if n.id in cards else None,
            )
        )
    return tuple(out)


def _stone_targets(
    library: ContentLibrary, char: CharacterState, found: FieldMapDef, at: tuple[int, int]
) -> tuple[FieldStoneTargetView, ...]:
    here = next((s.id for s in found.teleport_stones if s.at == at), None)
    if here is None:
        return ()
    out: list[FieldStoneTargetView] = []
    for map_id in sorted(library.field_maps):
        other = library.field_maps[map_id]
        for stone in other.teleport_stones:
            if stone.id != here and stone.id in char.teleport_stones:
                name = _place_name(library, other.region, other.place)
                out.append(FieldStoneTargetView(id=stone.id, name_zh=name))
    return tuple(sorted(out, key=lambda t: t.id))


def _leader_look(library: ContentLibrary, lineup: EncounterLineup) -> FieldHeroView | None:
    """帶頭單位的外觀（6C-R3）：陣容第一名，沒有敵方時第三方第一名；同戰鬥的 ``UnitView``。"""
    lead = next(iter((*lineup.members, *lineup.third)), None)
    if lead is None:
        return None
    template = library.enemy_catalog().template(lead.unit)
    return look_of(library, template, library.loadout_of(template))


def _units(library: ContentLibrary, lineup: EncounterLineup) -> tuple[FieldEnemyUnitView, ...]:
    catalog = library.enemy_catalog()

    def one(member: LineupMember, *, third: bool) -> FieldEnemyUnitView:
        template = catalog.template(member.unit)
        return FieldEnemyUnitView(
            unit=member.unit,
            name_zh=template.name_zh,
            affix=member.affix,
            elite=member.affix is not None or catalog.is_elite(template),
            third=third,
        )

    return (
        *(one(m, third=False) for m in lineup.members),
        *(one(m, third=True) for m in lineup.third),
    )


def _enemy(
    library: ContentLibrary, world: WorldState, char: CharacterState, enemy: FieldEnemy, now: int
) -> FieldEnemyView:
    lineup = enemy_lineup(library, world, char, enemy, now)
    table = library.world_encounters.get(char.region)
    group = enemy.spawn.group if lineup is None else lineup.group
    found = None if table is None else table.group_by_id().get(group)
    return FieldEnemyView(
        id=f"e{enemy.index}",
        x=enemy.x,
        y=enemy.y,
        facing=enemy.facing,
        patrol=enemy.patrols,
        group=group,
        name_zh=group if found is None else found.name_zh,
        elite=lineup is not None and bool(elite_kinds(library, lineup)),
        units=() if lineup is None else _units(library, lineup),
        sight=enemy.sight,
        look=None if lineup is None else _leader_look(library, lineup),
    )


def _enemies(
    library: ContentLibrary, world: WorldState | None, char: CharacterState, now: int
) -> tuple[FieldEnemyView, ...]:
    if world is None:
        return ()
    return tuple(
        _enemy(library, world, char, e, now) for e in field_enemies(library, world, char, now)
    )


def field_view(
    library: ContentLibrary,
    char: CharacterState,
    *,
    world: WorldState | None = None,
    now: int = 0,
    social: FieldSocial | None = None,
    inline_tiles: bool = True,
) -> FieldView | None:
    """目前的實地地圖；所在地點沒有實地地圖＝``None``。``world`` 給了才帶看得見的敵人（6C-1）與
    情境物件（6C-5）；``social`` 給了才帶朋友的腳印與留言石碑（6C-5）。``inline_tiles`` 為假時不帶
    ``tiles``（世界畫面，6C-R3：前端依 ``tiles_hash`` 另外取靜態地形，再套上 ``open_cells``）。"""
    char = placed(library, char)
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    static = None if found is None else field_tiles(library, found.id)
    if pos is None or found is None or static is None:
        return None
    grid = field_grid(library, char, found)
    view = FieldView(
        map_id=found.id,
        name_zh=_map_name(library, found),
        region=found.region,
        location=found.place,
        interior=found.is_interior,
        width=found.width,
        height=found.height,
        tiles=_tiles(found, grid, hidden_cells(char, found)) if inline_tiles else (),
        tiles_hash=static.hash,
        open_cells=_open_cells(found, char, grid),
        objects=tuple(
            FieldObjectView(id=f"o{o.at[0]}_{o.at[1]}", kind=o.kind, x=o.at[0], y=o.at[1])
            for o in found.objects
        ),
        exits=tuple(
            FieldExitView(
                id=e.id,
                cells=e.at,
                to=e.to,
                to_name_zh=_place_name(library, e.region or found.region, e.to),
                blocked_zh=(
                    None
                    if e.gate is None or exit_open(library, char, found, e)
                    else e.gate.notice_zh()
                ),
            )
            for e in found.exits
        ),
        doors=_doors(library, char, found),
        stones=tuple(
            FieldStoneView(id=s.id, x=s.at[0], y=s.at[1], unlocked=s.id in char.teleport_stones)
            for s in found.teleport_stones
        ),
        npcs=_npcs(library, world, char, found, now),
        facilities=tuple(
            FieldFacilityView(kind=f.id, x=f.at[0], y=f.at[1]) for f in found.facilities
        ),
        me=FieldPositionView(x=pos.x, y=pos.y, facing=pos.facing),
        max_climb=library.ruleset.core.max_climb_height,
        walk_max_steps=_walk_max_steps(library),
        hero=_hero(library, char),
        stone_targets=_stone_targets(library, char, found, (pos.x, pos.y)),
        enemies=_enemies(library, world, char, now),
        friends=friends_here(library, world, char, found, grid),
    )
    return view.model_copy(
        update=things_update(library, world, char, grid, now=now, social=social)  # 6C-5
    )


def _walk_max_steps(library: ContentLibrary) -> int:
    """一次 ``walk`` 最多幾格（規則 ``field.walk_max_steps``；沒有世界規則時用預設值）。"""
    rules = library.world_rules
    if rules is None:
        return int(FieldView.model_fields["walk_max_steps"].default)
    return rules.field.walk_max_steps
