"""地圖卡路檢查（Phase 3C-1 3.3）：可推動物件會不會擋住從我方起始區到敵方起始區的通路。

對每張地圖（預設為正式地圖，不含 ``test_`` 開頭者）：

1. 列出可推動（``pushable``）物件的位置，以及其中會 **擋路**（帶 ``blocks_move``）者。
2. 以 BFS 檢查「物件視為不可通行」時，我方起始區能否走到敵方起始區（只看地形與高度，
   不看單位與移動點數）。
3. 若走不到：對每個擋路的可推動物件試著推（四個方向）或撥開，列出能單獨打通路的移動。

只讀不改地圖；有問題的地圖（原本就不通、需要先移動物件才通）列在摘要表的「狀態」欄。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from trpg.content.library import ContentLibrary
from trpg.content.maps import standable
from trpg.engine.battle import start_battle
from trpg.engine.effects.world import object_push_block
from trpg.engine.rules.geometry import XY
from trpg.engine.setup import build_setup
from trpg.engine.state import BattleState, ObjectState
from trpg.shared.types import ObjectId, Team

__all__ = ["MapPushReport", "check_map", "check_state", "render_report"]

_DIRECTIONS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))
_DIRECTION_NAMES = {(0, -1): "北", (1, 0): "東", (0, 1): "南", (-1, 0): "西"}


@dataclass(frozen=True)
class Unblock:
    """單一次移動（推或撥開的結果）能打通路。"""

    object_id: str
    from_xy: XY
    to_xy: XY

    def text(self) -> str:
        dx, dy = self.to_xy[0] - self.from_xy[0], self.to_xy[1] - self.from_xy[1]
        return f"{self.object_id} {self.from_xy}→{self.to_xy}（往{_DIRECTION_NAMES[(dx, dy)]}）"


@dataclass
class MapPushReport:
    map_id: str
    pushable: list[tuple[str, str, XY]] = field(default_factory=list)
    """``(物件 ID, 種類, 位置)``。"""
    blockers: list[tuple[str, XY]] = field(default_factory=list)
    """會擋路的可推動物件（帶 ``blocks_move``）。"""
    connected: bool = True
    """物件視為不可通行時，我方起始區能否走到敵方起始區。"""
    unblocks: list[Unblock] = field(default_factory=list)
    """不通時，單一次移動就能打通的方式。"""
    seals: list[Unblock] = field(default_factory=list)
    """原本通的地圖：單次推或撥開就把通路封死的移動（空表示沒有）。"""
    sole_blockers: list[str] = field(default_factory=list)
    """通路被它們擋住（把它從地圖拿掉就通）的可推動物件 ID。"""

    @property
    def status(self) -> str:
        if self.connected:
            return "通"
        if self.unblocks:
            return "需移動物件（可撥開／推開）"
        return "不通（移動一次也打不通）"


def _blocked_tiles(state: BattleState, removed: str | None = None) -> set[XY]:
    """存活物件所在的格子，一律視為不可通行（``removed`` 的物件除外）。木橋等架在深淵上的物件
    是通路，不算。"""
    blocked: set[XY] = set()
    for obj in state.objects_sorted():
        if obj.destroyed or obj.id == removed:
            continue
        tags = state.object_def(obj).tags
        if "over_chasm" in tags:
            continue
        blocked.add(obj.xy)
    return blocked


def _can_step(state: BattleState, a: XY, b: XY) -> bool:
    """只看地形與高度的一步（物件由 ``blocked`` 處理，所以這裡不看 ``blocks_move``）。木橋等
    ``over_chasm`` 物件架在致命地形上時可站。"""
    tile = state.tile(*b)
    bridged = tile.object_id is not None and state.object_has_tag(*b, "over_chasm")
    if not (bridged or standable(state.ruleset.terrain_def(tile.terrain))):
        return False
    rise = tile.height - state.tile(*a).height
    return rise <= state.ruleset.core.max_climb_height


def _reachable(state: BattleState, sources: list[XY], blocked: set[XY]) -> set[XY]:
    seen = {xy for xy in sources if xy not in blocked}
    queue = deque(seen)
    while queue:
        cur = queue.popleft()
        for dx, dy in _DIRECTIONS:
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in seen or nxt in blocked or not state.in_bounds(*nxt):
                continue
            if not _can_step(state, cur, nxt):
                continue
            seen.add(nxt)
            queue.append(nxt)
    return seen


def _linked(state: BattleState, allies: list[XY], enemies: list[XY], blocked: set[XY]) -> bool:
    reached = _reachable(state, allies, blocked)
    return any(xy in reached for xy in enemies)


def _moves(state: BattleState, obj: ObjectState) -> list[XY]:
    """物件能被推或撥到的相鄰格（四個方向，不論由誰、從哪一側）。"""
    return [
        nxt
        for dx, dy in _DIRECTIONS
        if object_push_block(state, obj.xy, nxt := (obj.xy[0] + dx, obj.xy[1] + dy)) is None
    ]


def check_map(library: ContentLibrary, map_id: str) -> MapPushReport:
    """檢查內容庫中的一張地圖（以預設單位開場，只用到地形、物件與起始區）。"""
    setup = build_setup(library, map_id, ["hero_fighter"], ["bandit"])
    return check_state(start_battle(setup, 0), map_id, setup.map.start_zones)


def check_state(
    state: BattleState, map_id: str, zones: Mapping[Team, Sequence[Sequence[int]]]
) -> MapPushReport:
    """檢查一個戰鬥狀態的地形與物件（``zones`` 為兩隊的起始區）。"""
    allies = [(c[0], c[1]) for c in zones[Team.ALLY]]
    enemies = [(c[0], c[1]) for c in zones[Team.ENEMY]]
    report = MapPushReport(map_id)
    for obj in state.objects_sorted():
        tags = state.object_def(obj).tags
        if obj.destroyed or "pushable" not in tags:
            continue
        report.pushable.append((obj.id, obj.kind, obj.xy))
        if "blocks_move" in tags:
            report.blockers.append((obj.id, obj.xy))
    base = _blocked_tiles(state)
    report.connected = _linked(state, allies, enemies, base)
    if report.connected:
        _find_seals(state, report, allies, enemies, base)
        return report
    for obj_id, xy in report.blockers:
        if _linked(state, allies, enemies, _blocked_tiles(state, removed=obj_id)):
            report.sole_blockers.append(obj_id)
        obj = state.objects[ObjectId(obj_id)]
        for nxt in _moves(state, obj):
            moved = (base - {xy}) | {nxt}
            if _linked(state, allies, enemies, moved):
                report.unblocks.append(Unblock(obj_id, xy, nxt))
    return report


def _find_seals(
    state: BattleState, report: MapPushReport, allies: list[XY], enemies: list[XY], base: set[XY]
) -> None:
    """原本通的地圖：哪些單次移動會把通路封死（推進窄道）。"""
    for obj_id, _kind, xy in report.pushable:
        for nxt in _moves(state, state.objects[ObjectId(obj_id)]):
            if not _linked(state, allies, enemies, (base - {xy}) | {nxt}):
                report.seals.append(Unblock(obj_id, xy, nxt))


def render_report(reports: list[MapPushReport]) -> str:
    lines = [
        "| 地圖 | 可推動物件 | 擋路的可推物件 | 狀態 | 單次移動可打通 | 單次移動會封路 |",
        "|---|---|---|---|---|---|",
    ]
    for r in reports:
        pushable = "、".join(f"{kind}{xy}" for _, kind, xy in r.pushable) or "—"
        blockers = "、".join(f"{oid}{xy}" for oid, xy in r.blockers) or "—"
        unblocks = "；".join(u.text() for u in r.unblocks) or "—"
        seals = "；".join(u.text() for u in r.seals) or "—"
        lines.append(
            f"| {r.map_id} | {pushable} | {blockers} | {r.status} | {unblocks} | {seals} |"
        )
    return "\n".join(lines)
