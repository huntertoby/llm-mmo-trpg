"""世界畫面的實地地圖（Phase 6B-2；3.5）：目前地圖的地形、物件、出口、門、傳送石、NPC、設施與自己的
位置。舊存檔沒有位置時照 :func:`trpg.world.field.placed` 放到 ``entry``（只算，不寫檔）。"""

from __future__ import annotations

from trpg.api.world_field_schemas import (
    FieldDoorView,
    FieldExitView,
    FieldFacilityView,
    FieldGearLookView,
    FieldHeroView,
    FieldNpcView,
    FieldObjectView,
    FieldPositionView,
    FieldStoneTargetView,
    FieldStoneView,
    FieldTileView,
    FieldView,
)
from trpg.content.appearance import derive_keywords
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.engine.view import AppearanceView
from trpg.world.actions import WorldEvent
from trpg.world.field import FieldGrid, field_grid, field_map, hidden_door, placed
from trpg.world.field_actions import (
    FieldEnteredEvent,
    TeleportStoneUnlockedEvent,
    TeleportStoneUsedEvent,
)
from trpg.world.gear import hero_loadout
from trpg.world.narration import region_npcs
from trpg.world.state import CharacterState

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
    hero = char.hero
    weapon = library.weapons.get(hero.weapon)
    race = None
    if hero.race is not None:
        try:
            race = library.ruleset.race_def(hero.race).look
        except KeyError:
            race = None
    gear = tuple(
        FieldGearLookView(
            slot=e.slot,
            appearance=AppearanceView(
                kind=e.item.kind,
                form=e.item.form,
                material=e.item.material,
                dye=e.item.dye,
                style=e.item.style,
                rarity=e.item.rarity or ("legendary" if e.item.legendary else "common"),
                keywords=derive_keywords(a.affix for a in e.affixes),
            ),
        )
        for e in hero_loadout(library, char).items
    )
    return FieldHeroView(
        template_id=hero.id,
        doll_look=hero.doll,
        weapon_id=hero.weapon,
        weapon_class="melee" if weapon is None else weapon.weapon_class,
        race_look=race,
        equipment=gear,
    )


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


def field_view(library: ContentLibrary, char: CharacterState) -> FieldView | None:
    """目前的實地地圖；所在地點沒有實地地圖＝``None``。"""
    char = placed(library, char)
    pos = char.field
    found = None if pos is None else field_map(library, pos.map)
    if pos is None or found is None:
        return None
    cards = region_npcs(library, found.region)
    return FieldView(
        map_id=found.id,
        name_zh=_map_name(library, found),
        region=found.region,
        location=found.place,
        interior=found.is_interior,
        width=found.width,
        height=found.height,
        tiles=_tiles(found, field_grid(library, char, found)),
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
        npcs=tuple(
            FieldNpcView(
                id=n.id,
                name_zh=cards[n.id].name_zh if n.id in cards else n.id,
                x=n.at[0],
                y=n.at[1],
            )
            for n in found.npcs
        ),
        facilities=tuple(
            FieldFacilityView(kind=f.id, x=f.at[0], y=f.at[1]) for f in found.facilities
        ),
        me=FieldPositionView(x=pos.x, y=pos.y, facing=pos.facing),
        max_climb=library.ruleset.core.max_climb_height,
        hero=_hero(library, char),
        stone_targets=_stone_targets(library, char, found, (pos.x, pos.y)),
    )
