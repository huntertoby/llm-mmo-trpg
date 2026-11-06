"""獸躍捷徑檢查（Phase 6R-1 驗收 C，#138；``docs/design/07-角色成長.md`` 7.7 實作細節第 6 點）。

問題：獸躍（3 格內任一空格、往上最多 2 層、不能越過牆與石柱）會不會被拿來跳過牆、繞過地圖設計
的阻擋（例：跳進封閉區、Boss 戰跳過關鍵地形），或讓撤離區、守點、Boss 的路徑短超過 2 格。

做法（只用引擎的規則函式，不另寫一套）：每張地圖建一個只有一名獸耳族探針的戰鬥狀態，在格子圖上跑
三層最短路徑（成本＝移動點數）：

- **走路**：:func:`~trpg.engine.rules.movement.step_cost`（相鄰、往上最多 1 層、可站立）；
- **走路＋攀跳**：再加上 :func:`~trpg.engine.basics.vault_plan`（攀上 2 層、跳過 1 格缺口；所有
  種族都能用），成本 ``vault_move_cost``；
- **加一次獸躍**：再加上 :func:`~trpg.engine.race.skills.leap_problem` 合法的落點，成本＝曼哈頓距離
  （獸躍本身不花移動點數；用距離計，平地上不會變短，只有越過走不過去的地方才會短）。每條路徑最多
  一次（每場 1 次）。

量的東西：

1. **目標路徑**：起點（我方起始區；實地地圖是入口、出口與門）到目標（撤離格、守點、敵方起始區＝
   Boss 戰的 Boss；實地地圖是出口、門、駐守點、事件點、NPC、營火）的「走路＋攀跳」減「加一次
   獸躍」，超過 :data:`MAX_SHORTCUT` 格就標出（07 7.7：不能讓撤離區／守點／Boss 門的路徑短超過
   2 格）。
2. **只有獸躍到得了的格子**：從起點用「走路＋攀跳」到不了、加一次獸躍到得了的可站立格
   （跳進封閉區）。
3. **最長的單次捷徑**：每一個合法的獸躍（起點 → 落點）比「走路＋攀跳」省下的最多格數（給人讀；
   跟起點無關）。

確定性：只讀內容，不擲骰、不讀時間。
"""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Final

from trpg.content.fields import FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.maps import MapDef
from trpg.content.races import RaceEffect
from trpg.engine import BattleSetup, UnitSpawn, start_battle
from trpg.engine.basics import vault_plan
from trpg.engine.race.skills import leap_problem
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.rules.movement import is_standable, step_cost
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, Team

__all__ = [
    "MAX_SHORTCUT",
    "LeapReport",
    "RouteCheck",
    "battle_map_report",
    "field_map_report",
    "format_reports",
    "probe_state",
]

MAX_SHORTCUT: Final = 2
"""路徑最多可以短幾格（07 7.7 實作細節第 6 點）。"""
_PROBE_RACE: Final = "fox"
_INF: Final = 10**9


@dataclass(frozen=True, slots=True)
class RouteCheck:
    """一條「起點 → 目標」的比較：三種走法的最短移動點數（到不了＝``None``）。"""

    source: str
    target: str
    walk: int | None
    vault: int | None
    leap: int | None

    @property
    def shortcut(self) -> int:
        """加一次獸躍比「走路＋攀跳」短幾格（走路＋攀跳到不了而獸躍到得了＝很大）。"""
        if self.leap is None:
            return 0
        if self.vault is None:
            return _INF
        return self.vault - self.leap


@dataclass(slots=True)
class LeapReport:
    """一張地圖的檢查結果。"""

    map_id: str
    kind: str
    """``battle``（戰鬥地圖）或 ``field``（實地地圖）。"""
    routes: list[RouteCheck] = field(default_factory=list)
    leap_only: list[XY] = field(default_factory=list)
    """從起點用走路＋攀跳到不了、加一次獸躍到得了的可站立格。"""
    best_edge: tuple[XY, XY, int] | None = None
    """省最多的單次獸躍（起點、落點、省下的格數）；沒有省的時為 ``None``。"""

    @property
    def flagged(self) -> list[RouteCheck]:
        return [r for r in self.routes if r.shortcut > MAX_SHORTCUT]

    @property
    def ok(self) -> bool:
        return not self.flagged and not self.leap_only


# ---------------------------------------------------------------------------
# 狀態
# ---------------------------------------------------------------------------


def probe_state(library: ContentLibrary, map_def: MapDef) -> BattleState:
    """``map_def`` 上只有一名獸耳族探針（我方起始區第一格）的戰鬥狀態：開戰需要的一名敵人放在
    敵方起始區第一格後標成撤離（不佔格子，不影響落點）。"""
    template = library.unit("hero_fighter").model_copy(update={"race": _PROBE_RACE})
    foe = library.unit("bandit")
    ally_at = map_def.start_zones[Team.ALLY][0]
    enemy_at = map_def.start_zones[Team.ENEMY][0]
    setup = BattleSetup(
        map=map_def,
        ruleset=library.ruleset,
        units=(
            UnitSpawn(
                template=template,
                weapon=library.weapon_of(template),
                team=Team.ALLY,
                position=ally_at,
            ),
            UnitSpawn(
                template=foe, weapon=library.weapon_of(foe), team=Team.ENEMY, position=enemy_at
            ),
        ),
    )
    state = start_battle(setup, 0)
    for unit in state.units_sorted():
        if unit.team is Team.ENEMY:
            unit.escaped = True
    return state


def _probe(state: BattleState) -> UnitState:
    return next(u for u in state.units_sorted() if u.team is Team.ALLY)


def _leap_effect(state: BattleState) -> RaceEffect:
    skill = state.ruleset.race_def(_PROBE_RACE).skill
    return next(e for e in skill.effects if e.type == "leap")


def _cells(state: BattleState) -> list[XY]:
    return [(x, y) for y in range(state.height) for x in range(state.width)]


_DIRS: Final = ((0, -1), (1, 0), (0, 1), (-1, 0))
type _Edges = dict[XY, list[tuple[XY, int]]]


def _walk_edges(state: BattleState, _probe_unit: UnitState, xy: XY) -> list[tuple[XY, int]]:
    out: list[tuple[XY, int]] = []
    for dx, dy in _DIRS:
        nxt = (xy[0] + dx, xy[1] + dy)
        cost = step_cost(state, xy, nxt) if state.in_bounds(*nxt) else None
        if cost is not None:
            out.append((nxt, cost))
    return out


def _vault_edges(state: BattleState, probe: UnitState, xy: XY) -> list[tuple[XY, int]]:
    core = state.ruleset.core
    out: list[tuple[XY, int]] = []
    for dx, dy in _DIRS:
        for dist in range(1, core.vault_jump_width + 2):
            nxt = (xy[0] + dx * dist, xy[1] + dy * dist)
            if state.in_bounds(*nxt) and not isinstance(vault_plan(state, probe, nxt), str):
                out.append((nxt, core.vault_move_cost))
    return out


def _leap_edges(state: BattleState, probe: UnitState, xy: XY) -> list[tuple[XY, int]]:
    effect = _leap_effect(state)
    reach = effect.range or 0
    return [
        (nxt, manhattan(xy, nxt))
        for nxt in _cells(state)
        if 0 < manhattan(xy, nxt) <= reach and leap_problem(state, probe, effect, nxt) is None
    ]


_LAYERS: Final = {"walk": _walk_edges, "vault": _vault_edges, "leap": _leap_edges}


def _edges(state: BattleState, layer: str) -> _Edges:
    """格子圖的邊：``walk``、``vault``（只有攀跳的邊）、``leap``（只有獸躍的邊）。"""
    probe = _probe(state)
    probe.ap, probe.move_points = state.ruleset.core.ap_per_turn, 99
    build = _LAYERS[layer]
    found: _Edges = {}
    for xy in _cells(state):
        if is_standable(state, xy):
            probe.pos = Pos(x=xy[0], y=xy[1])
            found[xy] = build(state, probe, xy)
    return found


@dataclass(frozen=True, slots=True)
class _Graph:
    walk: dict[XY, list[tuple[XY, int]]]
    vault: dict[XY, list[tuple[XY, int]]]
    leap: dict[XY, list[tuple[XY, int]]]


def _graph(state: BattleState) -> _Graph:
    walk = _edges(state, "walk")
    vault_only = _edges(state, "vault")
    vault = {xy: [*walk.get(xy, []), *vault_only.get(xy, [])] for xy in walk}
    return _Graph(walk=walk, vault=vault, leap=_edges(state, "leap"))


def _dijkstra(
    graph: _Graph, sources: Iterable[XY], *, use_vault: bool, leaps: int
) -> dict[XY, int]:
    """多起點最短路徑；狀態＝（格子, 用過幾次獸躍）。回傳每格的最小成本。"""
    base = graph.vault if use_vault else graph.walk
    best: dict[tuple[XY, int], int] = {}
    queue: list[tuple[int, int, XY]] = []
    for s in sorted(set(sources)):
        if s in base:
            best[(s, 0)] = 0
            heapq.heappush(queue, (0, 0, s))
    while queue:
        cost, used, xy = heapq.heappop(queue)
        if best.get((xy, used), _INF) < cost:
            continue
        moves = [(n, c, used) for n, c in base.get(xy, [])]
        if used < leaps:
            moves += [(n, c, used + 1) for n, c in graph.leap.get(xy, [])]
        for nxt, step, u in moves:
            total = cost + step
            if total < best.get((nxt, u), _INF):
                best[(nxt, u)] = total
                heapq.heappush(queue, (total, u, nxt))
    out: dict[XY, int] = {}
    for (xy, _u), cost in best.items():
        out[xy] = min(cost, out.get(xy, _INF))
    return out


def _check(
    report: LeapReport,
    state: BattleState,
    sources: dict[str, list[XY]],
    targets: dict[str, list[XY]],
) -> LeapReport:
    graph = _graph(state)
    all_sources = [xy for cells in sources.values() for xy in cells]
    reach_vault = _dijkstra(graph, all_sources, use_vault=True, leaps=0)
    reach_leap = _dijkstra(graph, all_sources, use_vault=True, leaps=1)
    report.leap_only = sorted(
        (xy for xy in reach_leap if xy not in reach_vault), key=lambda p: (p[1], p[0])
    )
    for source, cells in sources.items():
        walk = _dijkstra(graph, cells, use_vault=False, leaps=0)
        vault = _dijkstra(graph, cells, use_vault=True, leaps=0)
        leap = _dijkstra(graph, cells, use_vault=True, leaps=1)
        for target, goals in targets.items():
            if target == source:
                continue
            report.routes.append(
                RouteCheck(
                    source=source,
                    target=target,
                    walk=_min_at(walk, goals),
                    vault=_min_at(vault, goals),
                    leap=_min_at(leap, goals),
                )
            )
    report.best_edge = _best_edge(graph)
    return report


def _min_at(dist: dict[XY, int], goals: list[XY]) -> int | None:
    found = [dist[g] for g in goals if g in dist]
    return min(found) if found else None


def _best_edge(graph: _Graph) -> tuple[XY, XY, int] | None:
    """省最多的單次獸躍：落點的「走路＋攀跳」距離 − 獸躍距離（同分取格子順序在前的）。"""
    best: tuple[XY, XY, int] | None = None
    for start in sorted(graph.leap, key=lambda p: (p[1], p[0])):
        edges = graph.leap[start]
        if not edges:
            continue
        dist = _dijkstra(graph, [start], use_vault=True, leaps=0)
        for dest, cost in sorted(edges, key=lambda e: (e[0][1], e[0][0])):
            saved = dist.get(dest, _INF) - cost
            if best is None or saved > best[2]:
                best = (start, dest, saved)
    return best if best is not None and best[2] > 0 else None


# ---------------------------------------------------------------------------
# 地圖
# ---------------------------------------------------------------------------


def battle_map_report(library: ContentLibrary, map_def: MapDef) -> LeapReport:
    """戰鬥地圖：我方起始區 → 撤離格、守點、敵方起始區（Boss 戰的 Boss）。"""
    state = probe_state(library, map_def)
    ally = list(map_def.start_zones[Team.ALLY])
    targets: dict[str, list[XY]] = {"敵方起始區": list(map_def.start_zones[Team.ENEMY])}
    objective = map_def.objective
    if objective is not None and objective.tiles:
        targets[f"勝利條件 {objective.kind}"] = list(objective.tiles)
    alt = map_def.alt_objectives
    if alt is not None:
        for name in ("escape", "defend"):
            spec = getattr(alt, name)
            if spec is not None:
                targets[f"輪替 {name}"] = [_xy(t) for t in spec.tiles]
    report = LeapReport(map_def.id, "battle")
    return _check(report, state, {"我方起始區": ally}, targets)


def field_as_battle_map(library: ContentLibrary, field_map: FieldMapDef) -> MapDef:
    """整張實地地圖當成一張戰鬥地圖（只拿地形、高度、物件與表面；起始區是入口與另一個可站立
    格）。"""
    used = sorted({ch for line in field_map.terrain_rows() for ch in line})
    data: dict[str, object] = {
        "id": f"field_{field_map.id}",
        "name_zh": field_map.name_zh,
        "archetype": "test",
        "size": [field_map.width, field_map.height],
        "heights": "\n".join(field_map.height_rows()),
        "terrain": "\n".join(field_map.terrain_rows()),
        "legend": {ch: field_map.legend[ch] for ch in used},
        "objects": [{"at": list(o.at), "kind": o.kind} for o in field_map.objects],
        "surfaces": [
            {"at": list(s.at), "surface": s.surface.value, "duration": s.duration}
            for s in field_map.surfaces
        ],
    }
    other = next(
        (
            (x, y)
            for y in range(field_map.height)
            for x in range(field_map.width)
            if (x, y) != tuple(field_map.entry) and _standable_raw(library, field_map, (x, y))
        ),
        (0, 0),
    )
    return MapDef.model_validate(
        {**data, "start_zones": {"ally": [list(field_map.entry)], "enemy": [list(other)]}}
    )


def _standable_raw(library: ContentLibrary, field_map: FieldMapDef, xy: XY) -> bool:
    glyph = field_map.terrain_rows()[xy[1]][xy[0]]
    terrain = library.ruleset.terrain_def(field_map.legend[glyph])
    if not terrain.walkable or terrain.deadly:
        return False
    objects = library.ruleset.objects.by_id()
    return not any(
        tuple(o.at) == xy and "blocks_move" in objects[o.kind].tags for o in field_map.objects
    )


def field_map_report(library: ContentLibrary, field_map: FieldMapDef) -> LeapReport:
    """實地地圖（整張）：入口、出口、門 → 出口、門、駐守點、事件點、NPC、營火。"""
    state = probe_state(library, field_as_battle_map(library, field_map))
    sources: dict[str, list[XY]] = {"入口": [_xy(field_map.entry)]}
    targets: dict[str, list[XY]] = {}
    for exit_ in field_map.exits:
        cells = [_xy(c) for c in exit_.at]
        sources[f"出口 {exit_.id}"] = cells
        targets[f"出口 {exit_.id}"] = cells
    for door in field_map.doors:
        sources[f"門 {door.id}"] = [_xy(door.at)]
        targets[f"門 {door.id}"] = [_xy(door.at)]
    points = (
        *(("駐守 " + p.group, p.at) for p in field_map.spawns),
        *(("事件 " + p.id, p.at) for p in field_map.event_spots),
        *(("NPC " + p.id, p.at) for p in field_map.npcs),
        *(("營火 " + p.id, p.at) for p in field_map.campfires),
    )
    for name, at in points:
        targets[name] = [_xy(at)]
    report = LeapReport(field_map.id, "field")
    return _check(report, state, sources, targets)


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _xy(at: Sequence[int]) -> XY:
    return (at[0], at[1])


def _num(value: int | None) -> str:
    return "—" if value is None else str(value)


def format_reports(reports: list[LeapReport]) -> str:
    """摘要表（Markdown）：每張地圖一列＋被標出的路徑。"""
    lines = [
        "| 地圖 | 種類 | 路徑數 | 最大縮短（格） | 超過 2 格 | 只有獸躍到得了的格 "
        "| 省最多的單次獸躍 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    flagged: list[str] = []
    for r in reports:
        worst = max((c.shortcut for c in r.routes), default=0)
        worst_text = "∞" if worst >= _INF else str(worst)
        edge = "—"
        if r.best_edge is not None:
            edge = f"{r.best_edge[0]}→{r.best_edge[1]} 省 {r.best_edge[2]}"
        lines.append(
            f"| `{r.map_id}` | {r.kind} | {len(r.routes)} | {worst_text} | {len(r.flagged)} | "
            f"{len(r.leap_only)} | {edge} |"
        )
        for c in r.flagged:
            flagged.append(
                f"- `{r.map_id}`：{c.source} → {c.target}：走路 {_num(c.walk)}、走路＋攀跳 "
                f"{_num(c.vault)}、加獸躍 {_num(c.leap)}"
            )
        if r.leap_only:
            flagged.append(f"- `{r.map_id}`：只有獸躍到得了 {r.leap_only}")
    out = "\n".join(lines) + "\n"
    if flagged:
        out += "\n被標出的：\n\n" + "\n".join(flagged) + "\n"
    else:
        out += "\n沒有被標出的路徑或格子。\n"
    return out
