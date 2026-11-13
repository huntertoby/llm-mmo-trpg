"""不動巨型頭目的內容檢查（GB-1a，``docs/design/05-戰鬥.md`` 5.12.4、``PhaseGB計畫.md`` T13）。

- 只有 ``archetype: boss`` 地圖的遭遇（地圖的預設陣容、一輪的頭目戰、大世界戰鬥地圖全是頭目地圖的
  地點）能有佔多格的單位；一般地圖、一輪的一般遭遇、同伴、其他大世界遭遇、地圖事件與頭目階段的
  召喚都不行。
- 放得下：照引擎開場的放法（``trpg.engine.battle._place_units``：巨型單位先放，陣營起始區裡第一個
  9 格都在地圖內、不是牆、沒被別的巨型單位佔的格子當中心），那 9 格都要可站、同高度、沒有物件與
  表面；剩下的起始格要夠其他單位站。
- 地圖的 ``giant_facing`` 只能寫存在的範本。

範本本身的欄位（``footprint`` 只收 1、3；只給帶 ``boss`` 標籤、不是召喚物的範本）在
:class:`~trpg.content.battle.UnitTemplate` 驗證。目前內容沒有巨型單位，這些檢查全部通過。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from trpg.content.battle import TerrainDef, UnitTemplate
from trpg.content.environment import ObjectDef
from trpg.content.maps import MapDef, SpawnUnitsEvent, passable_grid
from trpg.content.roguelite import RunRules
from trpg.content.world_encounters import EncounterTable
from trpg.content.world_map import LocationMapDef
from trpg.shared.types import Team

__all__ = ["giant_problems"]

type XY = tuple[int, int]

BOSS_ARCHETYPE = "boss"


def _giants(units: Mapping[str, UnitTemplate]) -> frozenset[str]:
    return frozenset(tid for tid, t in units.items() if t.footprint > 1)


def _square(center: XY, size: int) -> list[XY]:
    half = size // 2
    return [
        (x, y)
        for y in range(center[1] - half, center[1] + half + 1)
        for x in range(center[0] - half, center[0] + half + 1)
    ]


class _Board:
    """一張地圖的格子查詢（地形、物件、表面）。"""

    def __init__(
        self, map_def: MapDef, terrain: Mapping[str, TerrainDef], objects: Mapping[str, ObjectDef]
    ) -> None:
        self.map = map_def
        self.grid = map_def.grid()
        self.terrain = terrain
        self.passable = passable_grid(map_def, dict(terrain), dict(objects))
        self.objects = {o.at for o in map_def.objects}
        self.surfaces = {s.at for s in map_def.surfaces}

    def not_solid(self, xy: XY) -> bool:
        """引擎開場挑中心格時的條件：在地圖內、不是牆（可站或致命地形）。"""
        if not self.map.in_bounds(*xy):
            return False
        definition = self.terrain[self.grid[xy[1]][xy[0]][1]]
        return definition.walkable or definition.deadly

    def strict_problems(self, cells: Sequence[XY]) -> list[str]:
        """9 格都可站、同高度、沒有物件與表面。"""
        problems: list[str] = []
        if any(not self.passable[y][x] for x, y in cells):
            problems.append("有格子站不上去")
        if len({self.grid[y][x][0] for x, y in cells}) > 1:
            problems.append("高度不一致")
        if any(c in self.objects for c in cells):
            problems.append("有物件")
        if any(c in self.surfaces for c in cells):
            problems.append("有表面")
        return problems


def _lineup_problems(
    where: str,
    board: _Board,
    lineup: Mapping[Team, Sequence[str]],
    units: Mapping[str, UnitTemplate],
) -> list[str]:
    """照引擎的放法把 ``lineup`` 的巨型單位放進起始區，檢查放得下、9 格合格、其他單位還站得下。"""
    problems: list[str] = []
    used: set[XY] = set()
    for team, members in sorted(lineup.items()):
        zone = list(board.map.start_zones.get(team, ()))
        for tid in members:
            size = units[tid].footprint
            if size == 1:
                continue
            center = next(
                (
                    c
                    for c in zone
                    if board.not_solid(c)
                    and all(x not in used and board.not_solid(x) for x in _square(c, size))
                ),
                None,
            )
            if center is None:
                problems.append(f"{where}：{team.value} 起始區放不下巨型單位 {tid}")
                continue
            cells = _square(center, size)
            used.update(cells)
            problems += [
                f"{where}：巨型單位 {tid} 站在 {list(center)} 時佔的 9 格{p}"
                for p in board.strict_problems(cells)
            ]
    for team, members in sorted(lineup.items()):
        small = sum(1 for tid in members if units[tid].footprint == 1)
        free = [c for c in board.map.start_zones.get(team, ()) if c not in used]
        if used and small > len(free):
            problems.append(
                f"{where}：巨型單位佔掉起始格後，{team.value} 起始區放不下 {small} 名單位"
            )
    return problems


def _map_problems(
    map_def: MapDef, board: _Board, giants: frozenset[str], units: Mapping[str, UnitTemplate]
) -> list[str]:
    where = f"地圖 {map_def.id}"
    problems = [
        f"{where} 的 giant_facing 寫了不存在的範本：{tid}"
        for tid in sorted(map_def.giant_facing)
        if tid not in units
    ]
    for event in map_def.events:
        if isinstance(event, SpawnUnitsEvent):
            problems += [
                f"{where} 第 {event.round} 輪的地圖事件不能產生巨型單位 {u.template}"
                for u in event.units
                if u.template in giants
            ]
    encounter = map_def.encounter
    if encounter is None:
        return problems
    lineup = {Team.ALLY: encounter.allies, Team.ENEMY: encounter.enemies}
    found = sorted({t for members in lineup.values() for t in members if t in giants})
    if not found:
        return problems
    if map_def.archetype != BOSS_ARCHETYPE:
        return [*problems, f"{where} 不是頭目地圖，預設陣容不能有巨型單位：{', '.join(found)}"]
    return problems + _lineup_problems(f"{where} 的預設陣容", board, lineup, units)


def _run_problems(
    rules: RunRules,
    boards: Mapping[str, _Board],
    giants: frozenset[str],
    units: Mapping[str, UnitTemplate],
) -> list[str]:
    problems: list[str] = []
    random = sorted({t for step in rules.encounters for o in step.options for t in o} & giants)
    if random:
        problems.append(f"一輪的一般遭遇不能有巨型單位：{', '.join(random)}")
    companions = sorted(set(rules.companions) & giants)
    if companions:
        problems.append(f"一輪的同伴不能是巨型單位：{', '.join(companions)}")
    boss = sorted(set(rules.boss.enemies) & giants)
    board = boards.get(rules.boss.map)
    if boss and board is not None:
        if board.map.archetype != BOSS_ARCHETYPE:
            problems.append(f"一輪的頭目戰地圖 {rules.boss.map} 不是頭目地圖，不能有巨型單位")
        else:
            lineup = {Team.ENEMY: rules.boss.enemies}
            problems += _lineup_problems(f"一輪的頭目戰（{rules.boss.map}）", board, lineup, units)
    return problems


def _phase_spawn_problems(units: Mapping[str, UnitTemplate], giants: frozenset[str]) -> list[str]:
    return [
        f"單位 {tid} 階段 {phase.id} 不能召喚巨型單位 {spawn.template}"
        for tid, template in sorted(units.items())
        for phase in template.phases
        for spawn in phase.spawns
        if spawn.template in giants
    ]


def _world_problems(
    world_maps: Mapping[str, LocationMapDef],
    tables: Mapping[str, EncounterTable],
    boards: Mapping[str, _Board],
    giants: frozenset[str],
    units: Mapping[str, UnitTemplate],
) -> list[str]:
    """大世界遭遇表：有巨型單位的陣容只能用在戰鬥地圖全是頭目地圖的地點（同時檢查放得下）；
    固定精英、加人、等級替換都不能是巨型單位。"""
    problems: list[str] = []
    for region, table in sorted(tables.items()):
        where = f"大世界 {region} 的遭遇表"
        problems += [
            f"{where}：加人（{s.flag}）不能是巨型單位 {s.unit}"
            for s in table.surges
            if s.unit in giants
        ]
        groups = {g.id: g for g in table.groups if set(g.all_units) & giants}
        used: set[str] = set()
        nodes = {} if region not in world_maps else {n.id: n for n in world_maps[region].locations}
        for loc in table.locations:
            here = f"{where} 地點 {loc.location}"
            elites = [loc.elite, *(v.elite for v in loc.variants)]
            problems += [
                f"{here}：固定精英不能是巨型單位 {e.unit}" for e in elites if e and e.unit in giants
            ]
            problems += [
                f"{here}：等級替換不能用巨型單位 {m.otherwise}"
                for m in loc.unit_min_levels
                if m.otherwise in giants
            ]
            names = [g.group for g in loc.groups] + [v.group for v in loc.variants]
            for name in sorted({n for n in names if n in groups}):
                used.add(name)
                node = nodes.get(loc.location)
                maps = () if node is None else node.battle_maps
                bad = [
                    m for m in maps if m not in boards or boards[m].map.archetype != BOSS_ARCHETYPE
                ]
                if not maps or bad:
                    problems.append(f"{here}：陣容 {name} 有巨型單位，戰鬥地圖必須全是頭目地圖")
                    continue
                lineup = {Team.ENEMY: groups[name].units, Team.THIRD: groups[name].third}
                for map_id in maps:
                    problems += _lineup_problems(
                        f"{here} 陣容 {name}（{map_id}）",
                        boards[map_id],
                        {k: v for k, v in lineup.items() if v},
                        units,
                    )
        problems += [
            f"{where}：陣容 {name} 有巨型單位，只能用在頭目地點"
            for name in sorted(set(groups) - used)
        ]
    return problems


def giant_problems(
    units: Mapping[str, UnitTemplate],
    maps: Mapping[str, MapDef],
    *,
    terrain: Mapping[str, TerrainDef],
    objects: Mapping[str, ObjectDef],
    roguelite: RunRules,
    world_maps: Mapping[str, LocationMapDef],
    world_encounters: Mapping[str, EncounterTable],
) -> list[str]:
    """巨型單位的跨檔案問題（空清單＝通過）。沒有任何巨型單位時只檢查 ``giant_facing`` 的範本。"""
    giants = _giants(units)
    if not giants:
        return [
            f"地圖 {map_id} 的 giant_facing 寫了不存在的範本：{tid}"
            for map_id, map_def in sorted(maps.items())
            for tid in sorted(map_def.giant_facing)
            if tid not in units
        ]
    boards = {mid: _Board(m, terrain, objects) for mid, m in sorted(maps.items())}
    problems: list[str] = []
    for map_id, map_def in sorted(maps.items()):
        problems += _map_problems(map_def, boards[map_id], giants, units)
    problems += _run_problems(roguelite, boards, giants, units)
    problems += _phase_spawn_problems(units, giants)
    problems += _world_problems(world_maps, world_encounters, boards, giants, units)
    return problems
