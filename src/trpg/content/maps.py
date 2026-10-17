"""地圖檔 schema（``content/maps/<id>.yaml``）與跨檔案驗證。

格式見 ``docs/phases/Phase1計畫.md`` 5.2。座標 ``(x, y)``：x 向右、y 向下；``heights`` 與
``terrain`` 第 y 行第 x 個字元即該格。
"""

from __future__ import annotations

from collections import deque

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, TerrainDef
from trpg.content.rules import CoreRules
from trpg.content.schemas import ContentModel
from trpg.shared.types import Surface, Team

__all__ = [
    "MAX_HEIGHT",
    "MapDef",
    "MapObjectPlacement",
    "MapSurfacePlacement",
    "check_map",
    "standable",
    "step_allowed",
]

MAX_HEIGHT = 3
_MIN_SIZE = 1
_MAX_SIZE = 64

type XY = tuple[int, int]


class MapObjectPlacement(ContentModel):
    """地圖上的物件（Phase 1B 起支援）。"""

    at: tuple[int, int]
    kind: str = Field(pattern=ID_PATTERN)


class MapSurfacePlacement(ContentModel):
    """地圖上的初始表面（Phase 1B 起支援）。"""

    at: tuple[int, int]
    surface: Surface


def _grid_lines(text: str) -> list[str]:
    # YAML 的 ``|`` 區塊結尾帶換行；容許 Windows 行尾。
    return [line.rstrip("\r") for line in text.strip("\n").split("\n")]


class MapDef(ContentModel):
    """一張地圖。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    size: tuple[int, int]
    heights: str
    terrain: str
    legend: dict[str, str]
    objects: tuple[MapObjectPlacement, ...] = ()
    surfaces: tuple[MapSurfacePlacement, ...] = ()
    start_zones: dict[Team, tuple[tuple[int, int], ...]]

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    def height_rows(self) -> list[str]:
        return _grid_lines(self.heights)

    def terrain_rows(self) -> list[str]:
        return _grid_lines(self.terrain)

    def tile_height(self, x: int, y: int) -> int:
        return int(self.height_rows()[y][x])

    def tile_terrain(self, x: int, y: int) -> str:
        return self.legend[self.terrain_rows()[y][x]]

    def grid(self) -> list[list[tuple[int, str]]]:
        """``grid()[y][x] == (高度, 地形 ID)``。"""
        hs, ts = self.height_rows(), self.terrain_rows()
        return [
            [(int(hs[y][x]), self.legend[ts[y][x]]) for x in range(self.width)]
            for y in range(self.height)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    @model_validator(mode="after")
    def _check_shape(self) -> MapDef:
        w, h = self.size
        if not (_MIN_SIZE <= w <= _MAX_SIZE and _MIN_SIZE <= h <= _MAX_SIZE):
            raise ValueError(f"size 必須在 {_MIN_SIZE}–{_MAX_SIZE} 之間，收到 {list(self.size)}")
        problems = self._grid_problems()
        problems += self._zone_problems()
        if problems:
            raise ValueError("；".join(problems))
        return self

    def _grid_problems(self) -> list[str]:
        w, h = self.size
        problems: list[str] = []
        for name, rows in (("heights", self.height_rows()), ("terrain", self.terrain_rows())):
            if len(rows) != h:
                problems.append(f"{name} 應有 {h} 行，實際 {len(rows)} 行")
                continue
            problems += [
                f"{name} 第 {y} 行應有 {w} 個字元，實際 {len(row)} 個"
                for y, row in enumerate(rows)
                if len(row) != w
            ]
        problems += [f"legend 的鍵必須是單一字元，收到 {k!r}" for k in self.legend if len(k) != 1]
        if problems:
            return problems
        problems += [
            f"heights ({x}, {y}) 的高度必須是 0–{MAX_HEIGHT}，收到 {ch!r}"
            for y, row in enumerate(self.height_rows())
            for x, ch in enumerate(row)
            if ch not in "0123456789" or int(ch) > MAX_HEIGHT
        ]
        used = sorted({ch for row in self.terrain_rows() for ch in row})
        missing = [ch for ch in used if ch not in self.legend]
        if missing:
            problems.append(f"legend 缺少字元：{', '.join(repr(c) for c in missing)}")
        return problems

    def _zone_problems(self) -> list[str]:
        problems = [
            f"start_zones 缺少 {team.value}"
            for team in Team
            if team not in self.start_zones or not self.start_zones[team]
        ]
        seen: set[XY] = set()
        for team, cells in sorted(self.start_zones.items()):
            for cell in cells:
                if not self.in_bounds(*cell):
                    problems.append(f"start_zones.{team.value} 的 {list(cell)} 超出地圖範圍")
                if cell in seen:
                    problems.append(f"start_zones 的 {list(cell)} 重複出現")
                seen.add(cell)
        placed = [("objects", o.at) for o in self.objects]
        placed += [("surfaces", s.at) for s in self.surfaces]
        problems += [
            f"{what} 的 {list(at)} 超出地圖範圍" for what, at in placed if not self.in_bounds(*at)
        ]
        return problems

    def summary(self) -> str:
        return f"{self.name_zh}（{self.width}×{self.height}）"


def standable(terrain: TerrainDef) -> bool:
    """單位能否主動站上（並停在）這種地形。"""
    return terrain.walkable and not terrain.deadly


def step_allowed(from_height: int, to_height: int, to_terrain: TerrainDef, core: CoreRules) -> bool:
    """主動移動一步是否可行（不考慮單位與物件）：目標可站立，且往上不超過 ``max_climb_height``。"""
    return standable(to_terrain) and to_height - from_height <= core.max_climb_height


def _reachable_from(
    start: XY, grid: list[list[tuple[int, str]]], terrain: dict[str, TerrainDef], core: CoreRules
) -> set[XY]:
    height, width = len(grid), len(grid[0])
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        h = grid[y][x][0]
        for nx, ny in ((x, y - 1), (x + 1, y), (x, y + 1), (x - 1, y)):
            if not (0 <= nx < width and 0 <= ny < height) or (nx, ny) in seen:
                continue
            nh, nt = grid[ny][nx]
            if step_allowed(h, nh, terrain[nt], core):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def check_map(map_def: MapDef, terrain: dict[str, TerrainDef], core: CoreRules) -> list[str]:
    """需要其他資料檔才能做的檢查；回傳問題清單（空清單表示通過）。

    - 圖例的地形 ID 存在於地形表。
    - 起始區不在不可站立的格子上。
    - 連通性：每一個起始格都能走到對方起始區的至少一格（依移動規則，往上一步最多
      ``max_climb_height`` 層，不經過不可站立的地形）。
    - Phase 1A 尚不支援 ``objects``／``surfaces``，必須為空。
    """
    problems: list[str] = []
    unknown = sorted({tid for tid in map_def.legend.values() if tid not in terrain})
    if unknown:
        return [f"legend 使用了未知的地形：{', '.join(unknown)}"]
    if map_def.objects:
        problems.append("objects 目前（Phase 1A）尚未支援，必須為空")
    if map_def.surfaces:
        problems.append("surfaces 目前（Phase 1A）尚未支援，必須為空")
    grid = map_def.grid()
    for team, cells in sorted(map_def.start_zones.items()):
        for x, y in cells:
            tdef = terrain[grid[y][x][1]]
            if not standable(tdef):
                problems.append(
                    f"start_zones.{team.value} 的 [{x}, {y}] 位於不可站立的地形 {tdef.id}"
                )
    if problems:
        return problems
    for team, cells in sorted(map_def.start_zones.items()):
        targets = set(map_def.start_zones[team.opponent])
        for cell in cells:
            if not _reachable_from(cell, grid, terrain, core) & targets:
                problems.append(
                    f"start_zones.{team.value} 的 {list(cell)} 無法走到 "
                    f"{team.opponent.value} 的起始區（連通性檢查失敗）"
                )
    return problems
