"""實地地圖上的東西（Phase 6C-5；21.6、21.9 第 14 條）：營火、事件「！」、情境物件、潛行、朋友的
腳印與留言石碑。純顯示、不改狀態、不耗亂數。

- **朋友的腳印**：來源是其他角色的 ``visited_locations``（6C-6；:class:`FieldSocial` 由伺服器的
  :class:`~trpg.api.world.WorldStore` 從記憶體快取的角色組出來，不掃世界日誌）。每位朋友在室外圖上
  畫一串腳印：端點是入口與每個出口往內一格（依出口 ID），依 ``fnv1a64("<地圖>:<角色>")`` 挑兩個，
  沿四方向 BFS 的最短路每隔一格畫一個（最多 :data:`PRINTS_MAX` 個）。最多
  :data:`FOOTPRINT_FRIENDS_MAX` 位（依角色 ID）。同樣的地圖與名單一定畫在同樣的位置（確定性）。
- **留言石碑**：這個地點有留言時，畫在入口附近第一個空的可站格（依和入口的距離、y、x）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from trpg.api.world_field_schemas import (
    FieldEventMarkView,
    FieldFootprintView,
    FieldNoteStoneView,
    FieldSituationObjectView,
    FieldSpotView,
)
from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.shared.rng import fnv1a64
from trpg.world.actions import WorldEvent
from trpg.world.common import rules_of
from trpg.world.field import FieldCtx, FieldGrid, arrival
from trpg.world.field_actions import EventMarkedEvent, SneakStartedEvent
from trpg.world.field_things import object_status, sneak_problem
from trpg.world.state import CharacterState, Facing, WorldState

__all__ = [
    "FOOTPRINT_FRIENDS_MAX",
    "FOOTPRINT_NAMES",
    "PRINTS_MAX",
    "FieldSocial",
    "Visitor",
    "footprint_cells",
    "note_stone_cell",
    "things_line",
    "things_update",
]

FOOTPRINT_FRIENDS_MAX: Final = 3
"""一張圖最多畫幾位朋友的腳印。"""
PRINTS_MAX: Final = 8
"""一位朋友最多畫幾個腳印。"""
FOOTPRINT_NAMES: Final = 3
"""區域圖上一個地點最多列幾位朋友。"""

type XY = tuple[int, int]
type Place = tuple[str, str]


@dataclass(frozen=True)
class Visitor:
    character_id: str
    name_zh: str


@dataclass(frozen=True)
class FieldSocial:
    """其他角色留下的東西（伺服器組；測試可以直接給）。"""

    visitors: Mapping[Place, tuple[Visitor, ...]] = field(default_factory=dict)
    """(區域, 地點) → 去過的其他角色（依角色 ID）。"""
    notes: Mapping[Place, int] = field(default_factory=dict)
    """(區域, 地點) → 留言數。"""

    def visitors_at(self, region: str, location: str) -> tuple[Visitor, ...]:
        return self.visitors.get((region, location), ())


def things_line(_library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """地圖上的「！」與潛行的句子（感知判定、發現地點、開事件卡照原本的句子）。"""
    if isinstance(event, EventMarkedEvent):
        return "附近好像有什麼動靜（地圖上的「！」）。"
    if isinstance(event, SneakStartedEvent):
        spent = event.supplies_spent
        return f"壓低身子潛行，敵人的視野變小了（花 {spent} 補給，到下一張地圖為止）。"
    return None


_DIRS: Final[tuple[tuple[XY, Facing], ...]] = (
    ((0, -1), "n"),
    ((1, 0), "e"),
    ((0, 1), "s"),
    ((-1, 0), "w"),
)


def _ends(library: ContentLibrary, char: CharacterState, found: FieldMapDef) -> list[XY]:
    ends: list[XY] = [found.entry]
    for exit_ in sorted(found.exits, key=lambda e: e.id):
        pos = arrival(library, char, found, exit_.id, 0)
        if (pos.x, pos.y) not in ends:
            ends.append((pos.x, pos.y))
    return ends


def _facing(a: XY, b: XY) -> Facing:
    delta = (b[0] - a[0], b[1] - a[1])
    return next((f for d, f in _DIRS if d == delta), "s")


def footprint_cells(
    library: ContentLibrary,
    char: CharacterState,
    found: FieldMapDef,
    grid: FieldGrid,
    owner: str,
) -> list[tuple[XY, Facing]]:
    """``owner`` 在這張圖上的腳印（見模組說明）；端點不到兩個或走不通＝空。"""
    ends = _ends(library, char, found)
    if len(ends) < 2:  # noqa: PLR2004 - 一條路要兩個端點
        return []
    h = fnv1a64(f"{found.id}:{owner}".encode())
    a = h % len(ends)
    b = (h // len(ends)) % (len(ends) - 1)
    b = b + 1 if b >= a else b
    path = grid.shortest_path(ends[a], ends[b], library.ruleset.core.max_climb_height)
    out: list[tuple[XY, Facing]] = []
    for i in range(1, len(path) - 1, 2):
        out.append((path[i], _facing(path[i - 1], path[i])))
        if len(out) >= PRINTS_MAX:
            break
    return out


def note_stone_cell(found: FieldMapDef, grid: FieldGrid) -> XY | None:
    """留言石碑的格子：入口附近第一個空的可站格（不是入口、出入口、NPC、營火、事件點、物件）。"""
    taken: set[XY] = {found.entry}
    taken |= {c for e in found.exits for c in e.at}
    taken |= {d.at for d in found.doors} | {s.at for s in found.teleport_stones}
    taken |= {n.at for n in found.npcs} | {f.at for f in found.facilities}
    for spots in (found.campfires, found.event_spots, found.situation_objects):
        taken |= {s.at for s in spots}
    ex, ey = found.entry
    cells = sorted(
        ((x, y) for y in range(found.height) for x in range(found.width)),
        key=lambda c: (abs(c[0] - ex) + abs(c[1] - ey), c[1], c[0]),
    )
    return next((c for c in cells if grid.standable(c) and c not in taken), None)


def _footprints(
    library: ContentLibrary,
    char: CharacterState,
    found: FieldMapDef,
    grid: FieldGrid,
    visitors: Sequence[Visitor],
) -> tuple[FieldFootprintView, ...]:
    out: list[FieldFootprintView] = []
    for v in sorted(visitors, key=lambda v: v.character_id)[:FOOTPRINT_FRIENDS_MAX]:
        for (x, y), facing in footprint_cells(library, char, found, grid, v.character_id):
            out.append(
                FieldFootprintView(owner=v.character_id, name_zh=v.name_zh, x=x, y=y, facing=facing)
            )
    return tuple(out)


def _objects(
    library: ContentLibrary,
    world: WorldState | None,
    char: CharacterState,
    found: FieldMapDef,
    now: int,
) -> tuple[FieldSituationObjectView, ...]:
    if world is None:
        return ()
    ctx = FieldCtx(library=library, world=world, map=found, now=now)
    out: list[FieldSituationObjectView] = []
    for spot in found.situation_objects:
        status = object_status(ctx, char, spot)
        if not status.shown:
            continue
        out.append(
            FieldSituationObjectView(
                id=spot.id,
                name_zh=spot.name_zh or "物件",
                x=spot.at[0],
                y=spot.at[1],
                use=status.use,
                usable=status.usable,
                note_zh=status.note_zh,
                problem_zh=status.problem_zh,
                panel=spot.panel,
                stele_region=spot.stele_region,
            )
        )
    return tuple(out)


def things_update(
    library: ContentLibrary,
    world: WorldState | None,
    char: CharacterState,
    grid: FieldGrid,
    *,
    now: int,
    social: FieldSocial | None,
) -> dict[str, object]:
    """``FieldView`` 的 6C-5 欄位（``grid.map`` 那張圖）。"""
    found = grid.map
    mark = char.field_event
    update: dict[str, object] = {
        "campfires": tuple(FieldSpotView(id=c.id, x=c.at[0], y=c.at[1]) for c in found.campfires),
        "event_mark": (
            FieldEventMarkView(x=mark.x, y=mark.y)
            if mark is not None and mark.map == found.id
            else None
        ),
        "situation_objects": _objects(library, world, char, found, now),
        "sneaking": char.sneaking,
        "sneak_cost": rules_of(library).hasten.cost,
        "sneak_problem_zh": sneak_problem(library, char),
    }
    if social is not None and not found.is_interior:
        place = (found.region, found.place)
        update["footprints"] = _footprints(library, char, found, grid, social.visitors_at(*place))
        count = social.notes.get(place, 0)
        cell = note_stone_cell(found, grid) if count > 0 else None
        if cell is not None:
            update["note_stone"] = FieldNoteStoneView(x=cell[0], y=cell[1], count=count)
    return update
