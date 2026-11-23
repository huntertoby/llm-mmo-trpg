"""地圖檔 schema（``content/maps/<id>.yaml``）與跨檔案驗證。

格式見 ``docs/phases/Phase1計畫.md`` 5.2。座標 ``(x, y)``：x 向右、y 向下；``heights`` 與
``terrain`` 第 y 行第 x 個字元即該格。
"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable, Sequence
from typing import Annotated, Literal, Protocol

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, TerrainDef
from trpg.content.environment import ObjectDef
from trpg.content.rules import CoreRules
from trpg.content.schemas import ContentModel
from trpg.shared.types import Surface, Team

__all__ = [
    "MAX_HEIGHT",
    "AltObjective",
    "AltObjectives",
    "Encounter",
    "GiantFacing",
    "MapArchetypeDef",
    "MapArchetypeTable",
    "MapDef",
    "MapEvent",
    "MapObjectPlacement",
    "MapRole",
    "MapSurfacePlacement",
    "Objective",
    "SpawnPlacement",
    "SpawnUnitsEvent",
    "TerrainChangeEvent",
    "TileChange",
    "TileSource",
    "check_map",
    "grid_bfs",
    "grid_path",
    "grid_rows",
    "grid_shape_problems",
    "passable_grid",
    "placement_problems",
    "reachable_from",
    "standable",
    "step_allowed",
]

MAX_HEIGHT = 3
_MIN_SIZE = 1
_MAX_SIZE = 64

type XY = tuple[int, int]


type GiantFacing = Literal["north", "east", "south", "west"]
"""巨型頭目的朝向（同引擎的 ``Facing``；北＝y − 1）。"""


type MapRole = Literal["test", "training", "boss"]
"""有特殊用途的地圖類型（Phase WL-2）：``test`` 測試地圖、``training`` 技能工坊的靶場
（Phase 3F-1）、``boss`` Boss 戰專屬地圖（Phase 3-5b）。程式依用途找類型，不寫死類型 ID。"""


# QF-5（WL-2 裁定 4，照 WL-1 b 的骨架檢查）：程式依用途找類型、找不到會出錯或擋不下來的用途。
# 每種至少要有一個類型標這個 role，缺了載入時給中文錯誤。改到下面的程式時同步這份。
CODE_REQUIRED_ROLES: dict[MapRole, str] = {
    "test": "開發用量測工具 sim/leap_check.py 的 field_as_battle_map（取第一個 role: test 的類型）",
    "training": "技能工坊的靶場（content/workshop.py 檢查 workshop.yaml 的地圖、API 的對手選單）",
    "boss": "頭目地圖與賽季 Boss（content/world_map.py、content/world_season.py、api/sessions.py）",
}
"""程式需要的地圖用途：role → 用到它的地方（錯誤訊息用）；順序＝錯誤訊息的順序。"""


class MapArchetypeDef(ContentModel):
    """一種地圖類型（``content/map_archetypes.yaml`` 的一列，Phase WL-2）。"""

    id: str = Field(pattern=ID_PATTERN)
    in_random_pool: bool = True
    """會不會進一般抽選：``false`` 的類型不能進區域與 roguelite 的地圖池，也不進模擬的預設地圖與
    循環賽。"""
    role: MapRole | None = None
    """特殊用途（見 :data:`MapRole`）；``None``＝一般地圖，所有依用途的分支都走預設。"""


class MapArchetypeTable(ContentModel):
    """地圖類型清單（``content/map_archetypes.yaml``，Phase WL-2）：地圖檔的 ``archetype``、區域的
    ``map_pool`` 只能填這裡的 ID。列的順序就是清單順序（例如模擬矩陣的類型欄）。"""

    archetypes: tuple[MapArchetypeDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> MapArchetypeTable:
        ids = [a.id for a in self.archetypes]
        dup = sorted({a for a in ids if ids.count(a) > 1})
        if dup:
            raise ValueError(f"地圖類型重複：{'、'.join(dup)}")
        have = {a.role for a in self.archetypes}
        needed = [f"{r}（{why}）" for r, why in CODE_REQUIRED_ROLES.items() if r not in have]
        if needed:
            raise ValueError(f"缺少程式需要的地圖用途（role）：{'；'.join(needed)}")
        return self

    def ids(self) -> tuple[str, ...]:
        """全部類型 ID（照資料檔的順序）。"""
        return tuple(a.id for a in self.archetypes)

    def get(self, archetype: str) -> MapArchetypeDef | None:
        return next((a for a in self.archetypes if a.id == archetype), None)

    def in_random_pool(self, archetype: str) -> bool:
        """這種類型會不會進一般抽選（不認得的類型＝不會）。"""
        found = self.get(archetype)
        return found is not None and found.in_random_pool

    def has_role(self, archetype: str, role: MapRole) -> bool:
        found = self.get(archetype)
        return found is not None and found.role == role

    def role_ids(self, role: MapRole) -> tuple[str, ...]:
        """用途是 ``role`` 的類型（照資料檔的順序）。"""
        return tuple(a.id for a in self.archetypes if a.role == role)

    def role_label(self, role: MapRole) -> str:
        """錯誤訊息用：用途是 ``role`` 的類型 ID（以「、」連接）；沒有時寫 ``role: <role>``。"""
        return "、".join(self.role_ids(role)) or f"role: {role}"

    def unknown_problem(self, archetype: str) -> str | None:
        """``archetype`` 不在清單裡時的錯誤訊息（中文）；認得就回傳 ``None``。"""
        if self.get(archetype) is not None:
            return None
        return f"未知的地圖類型 {archetype!r}（可用：{'、'.join(self.ids())}）"


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

    ``leader_retreat``（BAL-16a，05 5.8，#86；只用在 ``eliminate``）：Boss 戰——敵方頭目（``boss``
    標籤）全部倒下時，其餘敵人撤退，我方直接勝利（``leader_defeated``）。
    """

    kind: Literal["eliminate", "escape", "defend"] = "eliminate"
    rounds: int | None = Field(default=None, ge=1)
    tiles: tuple[tuple[int, int], ...] = ()
    leader_retreat: bool = False

    @model_validator(mode="after")
    def _check(self) -> Objective:
        if self.leader_retreat and self.kind != "eliminate":
            raise ValueError("leader_retreat 只能用在 eliminate")
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


REQUIRED_ZONE_TEAMS: tuple[Team, ...] = (Team.ALLY, Team.ENEMY)
"""地圖必須有起始區的陣營（第三方可省略，Phase 5B-M3）。"""


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


def grid_rows(text: str) -> list[str]:
    """``heights``／``terrain`` 文字網格拆成每行一個字串（戰鬥地圖與實地地圖共用，6B-1）。"""
    return _grid_lines(text)


def grid_shape_problems(
    size: tuple[int, int], heights: str, terrain: str, legend: dict[str, str]
) -> list[str]:
    """網格的形狀檢查（戰鬥地圖與實地地圖共用，6B-1）：行數、每行字元數與 ``size`` 一致；
    ``legend`` 的鍵是單一字元且涵蓋 ``terrain`` 用到的字元；高度是 0～``MAX_HEIGHT``。"""
    w, h = size
    problems: list[str] = []
    for name, rows in (("heights", _grid_lines(heights)), ("terrain", _grid_lines(terrain))):
        if len(rows) != h:
            problems.append(f"{name} 應有 {h} 行，實際 {len(rows)} 行")
            continue
        problems += [
            f"{name} 第 {y} 行應有 {w} 個字元，實際 {len(row)} 個"
            for y, row in enumerate(rows)
            if len(row) != w
        ]
    problems += [f"legend 的鍵必須是單一字元，收到 {k!r}" for k in legend if len(k) != 1]
    if problems:
        return problems
    problems += [
        f"heights ({x}, {y}) 的高度必須是 0–{MAX_HEIGHT}，收到 {ch!r}"
        for y, row in enumerate(_grid_lines(heights))
        for x, ch in enumerate(row)
        if ch not in "0123456789" or int(ch) > MAX_HEIGHT
    ]
    used = sorted({ch for row in _grid_lines(terrain) for ch in row})
    missing = [ch for ch in used if ch not in legend]
    if missing:
        problems.append(f"legend 缺少字元：{', '.join(repr(c) for c in missing)}")
    return problems


class MapDef(ContentModel):
    """一張地圖。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    archetype: str = Field(pattern=ID_PATTERN)
    """地圖類型（``content/map_archetypes.yaml`` 的 ID；載入器檢查，Phase WL-2）。"""
    size: tuple[int, int]
    heights: str
    terrain: str
    legend: dict[str, str]
    objects: tuple[MapObjectPlacement, ...] = ()
    surfaces: tuple[MapSurfacePlacement, ...] = ()
    start_zones: dict[Team, tuple[tuple[int, int], ...]]
    """各陣營的起始區。``ally``、``enemy`` 必填；``third``（Phase 5B-M3 三方混戰）可省略，
    省略時第三方自動排在敵方起始區附近（:mod:`trpg.engine.battle`）。"""
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
    tags: tuple[str, ...] = ()
    """地圖標籤（Phase 3R-2，內容資料）：目前只有 ``forest``（森林地圖；精靈的環境被動「林間視野」
    看這個標籤）。新增地圖不改程式；不重複。"""
    source_wells: tuple[tuple[int, int], ...] = ()
    """源泉格（Phase 3C-4a）：我方單位進入時 +1 源力（不超過上限），源泉消失。不可與物件、
    起始區重疊，不可重複。"""
    giant_facing: dict[str, GiantFacing] = Field(default_factory=dict, exclude_if=lambda v: not v)
    """不動巨型頭目的朝向（GB-1a，05 5.12.4 第 7 點、T8）：範本 ID → 正面朝哪個方向（整場不轉）。
    沒列的巨型單位照陣營的開場朝向。範本 ID 必須存在（載入內容庫時檢查）；空＝不輸出。"""

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
        if kind == "eliminate":  # 地圖本身的全滅條件（Boss 地圖帶 leader_retreat，BAL-16a）
            return self.objective if self.objective.kind == "eliminate" else Objective()
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
        bad_tags = [t for t in self.tags if not re.fullmatch(ID_PATTERN, t)]
        if bad_tags or len(set(self.tags)) != len(self.tags):
            problems.append(f"tags 必須是不重複的 ID：{list(self.tags)}")
        if problems:
            raise ValueError("；".join(problems))
        return self

    def _grid_problems(self) -> list[str]:
        return grid_shape_problems(self.size, self.heights, self.terrain, self.legend)

    def _zone_problems(self) -> list[str]:
        problems = [
            f"start_zones 缺少 {team.value}"
            for team in REQUIRED_ZONE_TEAMS
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


class TileSource(Protocol):
    """有網格與物件的地圖（:class:`MapDef`、實地地圖 ``FieldMapDef``；6B-1 共用驗證工具）。"""

    @property
    def objects(self) -> Sequence[MapObjectPlacement]: ...

    def grid(self) -> list[list[tuple[int, str]]]: ...


def passable_grid(
    map_def: TileSource, terrain: dict[str, TerrainDef], objects: dict[str, ObjectDef]
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


_passable_grid = passable_grid


type StepFn = Callable[[XY, XY], bool]
"""``(這一格, 下一格) → 走不走得過去``（地圖範圍也由它檢查）。"""

_BFS_DIRS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))
"""四方向 BFS 的展開順序（北、東、南、西；同一組輸入一定得到同一條最短路）。"""


def grid_bfs(start: XY, can_step: StepFn, goal: XY | None = None) -> dict[XY, XY | None]:
    """四方向 BFS（戰鬥地圖、實地地圖共用，6C-R2）：走得到的格子 → 前一格（``start`` → ``None``）。
    給了 ``goal`` 時走到就停。"""
    prev: dict[XY, XY | None] = {start: None}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here == goal:
            break
        for dx, dy in _BFS_DIRS:
            nxt = (here[0] + dx, here[1] + dy)
            if nxt not in prev and can_step(here, nxt):
                prev[nxt] = here
                queue.append(nxt)
    return prev


def grid_path(start: XY, goal: XY, can_step: StepFn) -> list[XY]:
    """``start`` 到 ``goal`` 的四方向最短路（含兩端；走不到＝空）。"""
    prev = grid_bfs(start, can_step, goal)
    if goal not in prev:
        return []
    out: list[XY] = []
    cur: XY | None = goal
    while cur is not None:
        out.append(cur)
        cur = prev[cur]
    return out[::-1]


def reachable_from(
    start: XY, grid: list[list[tuple[int, str]]], passable: Passable, core: CoreRules
) -> set[XY]:
    """從 ``start`` 依移動規則走得到的格子（含自己）：只走可站立的格子，往上一步最多
    ``max_climb_height`` 層。"""
    height, width = len(grid), len(grid[0])

    def can_step(here: XY, nxt: XY) -> bool:
        nx, ny = nxt
        return (
            0 <= nx < width
            and 0 <= ny < height
            and passable[ny][nx]
            and grid[ny][nx][0] - grid[here[1]][here[0]][0] <= core.max_climb_height
        )

    return set(grid_bfs(start, can_step))


_reachable_from = reachable_from


def placement_problems(
    grid: list[list[tuple[int, str]]],
    objects: Sequence[MapObjectPlacement],
    surfaces: Sequence[MapSurfacePlacement],
    terrain: dict[str, TerrainDef],
) -> list[str]:
    """物件與表面的位置（戰鬥地圖與實地地圖共用，6B-1）：表面不放在致命地形或牆壁上、
    不可為 ``none``；物件不放在牆壁（不可進入且非致命的地形）上。座標須已在地圖內。"""
    problems = [
        f"surfaces 的 {list(s.at)} 位於致命地形"
        for s in surfaces
        if terrain[grid[s.at[1]][s.at[0]][1]].deadly
    ]
    problems += [
        f"surfaces 的 {list(s.at)} 位於牆壁等不可站立的地形"
        for s in surfaces
        if _is_solid(terrain[grid[s.at[1]][s.at[0]][1]])
    ]
    problems += [
        f"objects 的 {list(o.at)} 位於牆壁等不可站立的地形"
        for o in objects
        if _is_solid(terrain[grid[o.at[1]][o.at[0]][1]])
    ]
    problems += [
        f"surfaces 的 {list(s.at)} 不可為 none" for s in surfaces if s.surface is Surface.NONE
    ]
    return problems


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
    problems += placement_problems(grid, map_def.objects, map_def.surfaces, terrain)
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
