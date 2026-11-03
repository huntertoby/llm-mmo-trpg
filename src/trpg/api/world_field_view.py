"""世界畫面的實地地圖（Phase 6B-2；3.5）：目前地圖的地形、物件、出口、門、傳送石、NPC、設施與自己的
位置。舊存檔沒有位置時照 :func:`trpg.world.field.placed` 放到 ``entry``（只算，不寫檔）。"""

from __future__ import annotations

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
    FieldTileView,
    FieldView,
)
from trpg.api.world_field_things import FieldSocial, things_update
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.world.actions import WorldEvent
from trpg.world.encounters import EncounterLineup, LineupMember, elite_kinds
from trpg.world.field import FieldGrid, field_grid, field_map, hidden_door, placed
from trpg.world.field_actions import (
    FieldEnteredEvent,
    TeleportStoneUnlockedEvent,
    TeleportStoneUsedEvent,
)
from trpg.world.field_enemies import FieldEnemy, enemy_lineup, field_enemies
from trpg.world.gear import hero_loadout
from trpg.world.narration import region_npcs
from trpg.world.state import CharacterState, WorldState

__all__ = ["field_line", "field_view"]


def field_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """實地地圖事件的句子：走進室內、傳送石。走格子本身不出句子（21.7 文字減量）；踩出口換地點的
    句子是原本的「走到…」。"""
    if isinstance(event, FieldEnteredEvent):
        inner = None if event.map is None else field_map(library, event.map)
        if inner is not None and inner.is_interior:
            return f"走進{_map_name(library, inner)}。"
        return None
    if isinstance(event, TeleportStoneUnlockedEvent):
        return "傳送石亮了起來，之後可以從別的傳送石傳過來。"
    if isinstance(event, TeleportStoneUsedEvent):
        return f"經傳送石到了{_place_name(library, event.region, event.location)}。"
    return None


def _place_name(library: ContentLibrary, region: str, location: str) -> str:
    world_map = library.world_maps.get(region)
    found = None if world_map is None else world_map.location_by_id().get(location)
    return location if found is None else found.name_zh


def _map_name(library: ContentLibrary, found: FieldMapDef) -> str:
    return found.name_zh or _place_name(library, found.region, found.place)


def _tiles(found: FieldMapDef, grid: FieldGrid) -> tuple[FieldTileView, ...]:
    surfaces = {s.at: str(s.surface) for s in found.surfaces}
    return tuple(
        FieldTileView(
            x=x,
            y=y,
            height=height,
            terrain=terrain,
            surface=surfaces.get((x, y), "none"),
            walkable=grid.standable((x, y)),
        )
        for y, row in enumerate(found.grid())
        for x, (height, terrain) in enumerate(row)
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
) -> FieldView | None:
    """目前的實地地圖；所在地點沒有實地地圖＝``None``。``world`` 給了才帶看得見的敵人（6C-1）與
    情境物件（6C-5）；``social`` 給了才帶朋友的腳印與留言石碑（6C-5）。"""
    char = placed(library, char)
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    if pos is None or found is None:
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
        tiles=_tiles(found, grid),
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
        hero=_hero(library, char),
        stone_targets=_stone_targets(library, char, found, (pos.x, pos.y)),
        enemies=_enemies(library, world, char, now),
        friends=friends_here(library, world, char, found, grid),
    )
    return view.model_copy(
        update=things_update(library, world, char, found, grid, now, social)  # 6C-5
    )
