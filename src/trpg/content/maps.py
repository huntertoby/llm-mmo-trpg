"""地圖檔 schema（``content/maps/<id>.yaml``）與跨檔案驗證。

格式見 ``docs/phases/Phase1計畫.md`` 5.2。座標 ``(x, y)``：x 向右、y 向下；``heights`` 與
``terrain`` 第 y 行第 x 個字元即該格。
"""

from __future__ import annotations

from collections import deque
from typing import Annotated, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, TerrainDef
from trpg.content.environment import ObjectDef
from trpg.content.rules import CoreRules
from trpg.content.schemas import ContentModel
from trpg.shared.types import Surface, Team

__all__ = [
    "ARCHETYPES",
    "BOSS_ARCHETYPE",
    "MAX_HEIGHT",
    "TEST_ARCHETYPE",
    "TRAINING_ARCHETYPE",
    "AltObjective",
    "AltObjectives",
    "Archetype",
    "Encounter",
    "MapDef",
    "MapEvent",
    "MapObjectPlacement",
    "MapSurfacePlacement",
    "Objective",
    "SpawnPlacement",
    "SpawnUnitsEvent",
    "TerrainChangeEvent",
    "TileChange",
    "check_map",
    "standable",
    "step_allowed",
]

MAX_HEIGHT = 3
_MIN_SIZE = 1
_MAX_SIZE = 64

type XY = tuple[int, int]


type Archetype = Literal[
    "bridge_chasm",
    "oil_depot",
    "swamp",
    "ruined_heights",
    "forest",
    "corridor",
    "open_plain",
    "frozen_lake",
    "test",
    "training",
    "boss",
]
"""地圖類型（``docs/design/05-戰鬥.md`` 5.1 的 8 種類型，另加測試地圖用的 ``test`` 與技能工坊
靶場用的 ``training``，Phase 3F-1）。"""

ARCHETYPES: tuple[str, ...] = (
    "bridge_chasm",
    "oil_depot",
    "swamp",
    "ruined_heights",
    "forest",
    "corridor",
    "open_plain",
    "frozen_lake",
    "test",
    "training",
    "boss",
)
TEST_ARCHETYPE = "test"
TRAINING_ARCHETYPE = "training"
"""技能工坊靶場的地圖類型（Phase 3F-1）：不進 roguelite 抽選、模擬的預設地圖與一般地圖列表。"""
BOSS_ARCHETYPE = "boss"
"""Boss 戰專屬地圖的類型（Phase 3-5b）：同樣不進一般抽選、模擬的預設地圖與一般地圖列表。"""


class MapObjectPlacement(ContentModel):
    """地圖上的物件。``kind`` 為 ``objects.yaml`` 的 ID。"""

    at: tuple[int, int]
    kind: str = Field(pattern=ID_PATTERN)


class MapSurfacePlacement(ContentModel):
    """地圖上的初始表面。``duration`` 省略時為永久。"""

    at: tuple[int, int]
    surface: Surface
    duration: int | None = Field(default=None, ge=1)


class Objective(ContentModel):
    """勝利條件（``docs/專案計畫.md`` 5.8）。

    - ``eliminate``：擊倒所有敵人。
    - ``escape``：我方存活單位在 ``rounds`` 輪內全部抵達 ``tiles``（出口格）即勝；抵達者離開戰場。
      第 ``rounds`` 輪結束時仍未全部撤離即敗。
    - ``defend``：守住 ``tiles``（守點格）``rounds`` 輪；某輪結束時有敵方單位站在守點格上即敗。

    任何模式下，我方全滅即敗；敵方全滅即勝。
    """

    kind: Literal["eliminate", "escape", "defend"] = "eliminate"
    rounds: int | None = Field(default=None, ge=1)
    tiles: tuple[tuple[int, int], ...] = ()

    @model_validator(mode="after")
    def _check(self) -> Objective:
        if self.kind == "eliminate":
            if self.rounds is not None or self.tiles:
                raise ValueError("eliminate 不需要 rounds 與 tiles")
        elif self.rounds is None or not self.tiles:
            raise ValueError(f"{self.kind} 必須設定 rounds 與 tiles")
        if len(set(self.tiles)) != len(self.tiles):
            raise ValueError("objective.tiles 不可重複")
        return self


class AltObjective(ContentModel):
    """地圖可替換的一個勝利條件資料（Phase 3-22）：出口格或守點格，加上輪數。"""

    rounds: int = Field(ge=1)
    tiles: tuple[tuple[int, int], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> AltObjective:
        if len(set(self.tiles)) != len(self.tiles):
            raise ValueError("alt_objectives 的 tiles 不可重複")
        return self


class AltObjectives(ContentModel):
    """地圖支援的替代勝利條件（Phase 3-22）：``escape``（撤離：出口格＋輪數）、``defend``
    （守點：守點格＋輪數）。至少要有一個。roguelite 抽一輪時依此決定哪些地圖可以撤離或守點。"""

    escape: AltObjective | None = None
    defend: AltObjective | None = None

    @model_validator(mode="after")
    def _check(self) -> AltObjectives:
        if self.escape is None and self.defend is None:
            raise ValueError("alt_objectives 至少要設定 escape 或 defend 其中之一")
        return self


class Encounter(ContentModel):
    """地圖的預設陣容（單位範本 ID）。"""

    allies: tuple[str, ...] = Field(min_length=1)
    enemies: tuple[str, ...] = Field(min_length=1)


class SpawnPlacement(ContentModel):
    template: str = Field(pattern=ID_PATTERN)
    at: tuple[int, int]
    team: Team = Team.ENEMY


class SpawnUnitsEvent(ContentModel):
    """第 ``round`` 輪結束（環境回合）時在指定格產生單位。"""

    kind: Literal["spawn_units"]
    round: int = Field(ge=1)
    units: tuple[SpawnPlacement, ...] = Field(min_length=1)

    def positions(self) -> list[tuple[int, int]]:
        return [u.at for u in self.units]


class TileChange(ContentModel):
    """一格的變化：高度、地形、表面（省略的欄位不變）。"""

    at: tuple[int, int]
    height: int | None = Field(default=None, ge=0, le=3)
    terrain: str | None = Field(default=None, pattern=ID_PATTERN)
    surface: Surface | None = None

    @model_validator(mode="after")
    def _check(self) -> TileChange:
        if self.height is None and self.terrain is None and self.surface is None:
            raise ValueError(
                "terrain_change 的每一格至少要改變 height、terrain 或 surface 其中之一"
            )
        return self


class TerrainChangeEvent(ContentModel):
    """第 ``round`` 輪結束（環境回合）時改變指定格。"""

    kind: Literal["terrain_change"]
    round: int = Field(ge=1)
    tiles: tuple[TileChange, ...] = Field(min_length=1)

    def positions(self) -> list[tuple[int, int]]:
        return [t.at for t in self.tiles]


type MapEvent = Annotated[SpawnUnitsEvent | TerrainChangeEvent, Field(discriminator="kind")]


def _grid_lines(text: str) -> list[str]:
    # YAML 的 ``|`` 區塊結尾帶換行；容許 Windows 行尾。
    return [line.rstrip("\r") for line in text.strip("\n").split("\n")]


class MapDef(ContentModel):
    """一張地圖。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    archetype: Archetype
    size: tuple[int, int]
    heights: str
    terrain: str
    legend: dict[str, str]
    objects: tuple[MapObjectPlacement, ...] = ()
    surfaces: tuple[MapSurfacePlacement, ...] = ()
    start_zones: dict[Team, tuple[tuple[int, int], ...]]
    objective: Objective = Field(default_factory=Objective)
    alt_objectives: AltObjectives | None = None
    """可替換的勝利條件（Phase 3-22）：roguelite 抽到撤離或守點時，用這裡的格子與輪數取代
    ``objective``。格子必須在地圖內、不與任何起始區重疊。"""
    weather: str = Field(default="clear", pattern=ID_PATTERN)
    encounter: Encounter | None = None
    events: tuple[MapEvent, ...] = ()
    region: str | None = Field(default=None, pattern=ID_PATTERN)
    """區域主題（Phase 3-37a，``content/regions.yaml``）：只影響外觀；省略 ＝ 預設畫法。未知值由
    :func:`trpg.content.regions.sanitize_map_theme` 在載入時丟棄並警告。"""
    look: dict[str, str] = Field(default_factory=dict)
    """單張地圖的外觀覆寫（鍵與值見 ``regions.yaml`` 的 ``look_keys``；載入後已併入區域預設）。"""
    source_wells: tuple[tuple[int, int], ...] = ()
    """源泉格（Phase 3C-4a）：我方單位進入時 +1 源力（不超過上限），源泉消失。不可與物件、
    起始區重疊，不可重複。"""

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    def supports_objective(self, kind: str) -> bool:
        """地圖是否有 ``kind``（``escape``／``defend``）的資料；``eliminate`` 一律可以。"""
        if kind == "eliminate":
            return True
        alt = self.alt_objectives
        return alt is not None and getattr(alt, kind, None) is not None

    def objective_for(self, kind: str) -> Objective:
        """本地圖在 ``kind`` 勝利條件下的 :class:`Objective`（沒有資料時拋出 ``ValueError``）。"""
        if kind == "eliminate":
            return Objective()
        if kind not in ("escape", "defend") or not self.supports_objective(kind):
            raise ValueError(f"地圖 {self.id} 沒有 {kind} 的勝利條件資料")
        assert self.alt_objectives is not None
        alt: AltObjective = getattr(self.alt_objectives, kind)
        return Objective(kind=kind, rounds=alt.rounds, tiles=alt.tiles)  # type: ignore[arg-type]

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
        placed: list[tuple[str, tuple[int, int]]] = [("objects", o.at) for o in self.objects]
        placed += [("surfaces", s.at) for s in self.surfaces]
        placed += [("objective.tiles", t) for t in self.objective.tiles]
        placed += [(f"alt_objectives.{k}", t) for k, alt in self.alt_pairs() for t in alt.tiles]
        for event in self.events:
            placed += [(f"events（第 {event.round} 輪）", at) for at in event.positions()]
        problems += [
            f"{what} 的 {list(at)} 超出地圖範圍" for what, at in placed if not self.in_bounds(*at)
        ]
        groups: tuple[tuple[str, list[tuple[int, int]]], ...] = (
            ("objects", [o.at for o in self.objects]),
            ("surfaces", [s.at for s in self.surfaces]),
        )
        for what, spots in groups:
            dup = sorted({c for c in spots if spots.count(c) > 1})
            problems += [f"{what} 的 {list(c)} 重複（每格最多一個）" for c in dup]
        for kind, alt in self.alt_pairs():
            problems += [
                f"alt_objectives.{kind} 的 {list(t)} 在起始區內" for t in alt.tiles if t in seen
            ]
        return problems + self._well_problems(seen)

    def alt_pairs(self) -> list[tuple[str, AltObjective]]:
        if self.alt_objectives is None:
            return []
        pairs = (("escape", self.alt_objectives.escape), ("defend", self.alt_objectives.defend))
        return [(k, alt) for k, alt in pairs if alt is not None]

    def _well_problems(self, zones: set[XY]) -> list[str]:
        problems: list[str] = []
        objects = {o.at for o in self.objects}
        wells = list(self.source_wells)
        for cell in wells:
            if not self.in_bounds(*cell):
                problems.append(f"source_wells 的 {list(cell)} 超出地圖範圍")
            elif cell in objects:
                problems.append(f"source_wells 的 {list(cell)} 與物件重疊")
            elif cell in zones:
                problems.append(f"source_wells 的 {list(cell)} 在起始區內")
        dup = sorted({c for c in wells if wells.count(c) > 1})
        problems += [f"source_wells 的 {list(c)} 重複" for c in dup]
        return problems

    def summary(self) -> str:
        return f"{self.name_zh}（{self.width}×{self.height}）"


def standable(terrain: TerrainDef) -> bool:
    """單位能否主動站上（並停在）這種地形。"""
    return terrain.walkable and not terrain.deadly


def _is_solid(terrain: TerrainDef) -> bool:
    """牆壁這類地形：不可進入、也不是致命地形（不能放物件或表面）。"""
    return not terrain.walkable and not terrain.deadly


def step_allowed(from_height: int, to_height: int, to_terrain: TerrainDef, core: CoreRules) -> bool:
    """主動移動一步是否可行（不考慮單位與物件）：目標可站立，且往上不超過 ``max_climb_height``。"""
    return standable(to_terrain) and to_height - from_height <= core.max_climb_height


type Passable = list[list[bool]]


def _passable_grid(
    map_def: MapDef, terrain: dict[str, TerrainDef], objects: dict[str, ObjectDef]
) -> Passable:
    """每格是否可站立：地形可站立或有 ``over_chasm`` 物件，且沒有 ``blocks_move`` 物件。"""
    grid = map_def.grid()
    placed = {o.at: objects[o.kind] for o in map_def.objects if o.kind in objects}
    result: Passable = []
    for y, row in enumerate(grid):
        cells = []
        for x, (_, tid) in enumerate(row):
            obj = placed.get((x, y))
            ok = standable(terrain[tid]) or (obj is not None and obj.has_tag("over_chasm"))
            if obj is not None and obj.has_tag("blocks_move"):
                ok = False
            cells.append(ok)
        result.append(cells)
    return result


def _reachable_from(
    start: XY, grid: list[list[tuple[int, str]]], passable: Passable, core: CoreRules
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
            if passable[ny][nx] and grid[ny][nx][0] - h <= core.max_climb_height:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def check_map(
    map_def: MapDef,
    terrain: dict[str, TerrainDef],
    core: CoreRules,
    objects: dict[str, ObjectDef] | None = None,
) -> list[str]:
    """需要其他資料檔才能做的檢查；回傳問題清單（空清單表示通過）。

    - 圖例的地形 ID、物件種類存在。
    - 起始區與勝利條件的格子可站立（考慮物件：``blocks_move`` 不可站、``over_chasm`` 可站）。
    - 表面不放在致命地形上；表面與物件不放在牆壁（不可進入且非致命的地形）上；
      地圖事件的地形 ID 存在。
    - 連通性：每一個起始格都能走到對方起始區的至少一格（依移動規則，往上一步最多
      ``max_climb_height`` 層，不經過不可站立的格子）。
    """
    objects = objects or {}
    problems: list[str] = []
    unknown = sorted({tid for tid in map_def.legend.values() if tid not in terrain})
    if unknown:
        return [f"legend 使用了未知的地形：{', '.join(unknown)}"]
    unknown_objects = sorted({o.kind for o in map_def.objects if o.kind not in objects})
    if unknown_objects:
        return [f"objects 使用了未知的物件：{', '.join(unknown_objects)}"]
    grid = map_def.grid()
    passable = _passable_grid(map_def, terrain, objects)
    for team, cells in sorted(map_def.start_zones.items()):
        for x, y in cells:
            if not passable[y][x]:
                problems.append(f"start_zones.{team.value} 的 [{x}, {y}] 位於不可站立的格子")
    problems += [
        f"objective.tiles 的 [{x}, {y}] 位於不可站立的格子"
        for x, y in map_def.objective.tiles
        if not passable[y][x]
    ]
    for kind, alt in map_def.alt_pairs():
        problems += [
            f"alt_objectives.{kind} 的 [{x}, {y}] 位於不可站立的格子"
            for x, y in alt.tiles
            if not passable[y][x]
        ]
    problems += [
        f"surfaces 的 {list(s.at)} 位於致命地形"
        for s in map_def.surfaces
        if terrain[grid[s.at[1]][s.at[0]][1]].deadly
    ]
    problems += [
        f"surfaces 的 {list(s.at)} 位於牆壁等不可站立的地形"
        for s in map_def.surfaces
        if _is_solid(terrain[grid[s.at[1]][s.at[0]][1]])
    ]
    problems += [
        f"objects 的 {list(o.at)} 位於牆壁等不可站立的地形"
        for o in map_def.objects
        if _is_solid(terrain[grid[o.at[1]][o.at[0]][1]])
    ]
    problems += [
        f"surfaces 的 {list(s.at)} 不可為 none"
        for s in map_def.surfaces
        if s.surface is Surface.NONE
    ]
    for event in map_def.events:
        if isinstance(event, TerrainChangeEvent):
            problems += [
                f"events（第 {event.round} 輪）使用了未知的地形：{t.terrain}"
                for t in event.tiles
                if t.terrain is not None and t.terrain not in terrain
            ]
    if problems:
        return problems
    for team, cells in sorted(map_def.start_zones.items()):
        targets = set(map_def.start_zones[team.opponent])
        for cell in cells:
            if not _reachable_from(cell, grid, passable, core) & targets:
                problems.append(
                    f"start_zones.{team.value} 的 {list(cell)} 無法走到 "
                    f"{team.opponent.value} 的起始區（連通性檢查失敗）"
                )
    problems += _alt_reach_problems(map_def, grid, passable, core)
    return problems


def _alt_reach_problems(
    map_def: MapDef, grid: list[list[tuple[int, str]]], passable: Passable, core: CoreRules
) -> list[str]:
    """替代勝利條件的格子要走得到：我方每個起始格都能走到至少一格出口（或守點）。"""
    problems: list[str] = []
    for kind, alt in map_def.alt_pairs():
        targets = set(alt.tiles)
        problems += [
            f"alt_objectives.{kind} 的目標格無法從我方起始格 {list(cell)} 走到"
            for cell in map_def.start_zones[Team.ALLY]
            if not _reachable_from(cell, grid, passable, core) & targets
        ]
    return problems
