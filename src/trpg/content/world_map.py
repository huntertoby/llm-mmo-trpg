"""大世界地點圖（``content/world/maps/<region>.yaml``，Phase 5A-1）。

每個區域一張地點圖（``docs/design/09-世界與敘事.md`` 9.6.2，#29）：15～25 個地點、點了就走、
隱藏地點要探索才出現、每個地點有建議等級與種類。本模組只定義資料與驗證；移動、遇敵、隱藏地點
的判定在之後的 ``trpg.world``（5A-2 起）。

驗證分兩層：

- 單檔（:class:`LocationMapDef` 的 validator）：地點數、ID、小鎮、等級、戰鬥地圖、隱藏、傳送點、
  連線、連通（從小鎮走得到全部地點，且隱藏地點不是任何非隱藏地點的唯一通路）。
- 跨檔案（:func:`world_map_problems`）：區域 ID、戰鬥地圖 ID、地圖類型在該區地圖池內
  （``docs/design/05-戰鬥.md`` 5.1「區域地圖池」，#43）。

確定性：鄰接表一律依 ID 排序，BFS 不依賴 ``set``／``dict`` 的順序（守則 2）。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.maps import BOSS_ARCHETYPE, MapDef
from trpg.content.regions import RegionTable
from trpg.content.schemas import ContentModel

__all__ = [
    "MAX_LOCATIONS",
    "MIN_LOCATIONS",
    "LocationDef",
    "LocationKind",
    "LocationMapDef",
    "MapPos",
    "RevealMethod",
    "world_map_problems",
]

MIN_LOCATIONS = 15
MAX_LOCATIONS = 25
"""每區地點數（9.6.2「每區 15～25 個地點」）。"""

type LocationKind = Literal[
    "town",  # 區域小鎮（9.6.1）
    "camp",  # 營地（9.6.2）
    "ruin",  # 遺跡
    "altar",  # 祭壇
    "anomaly",  # 異象
    "caravan",  # 商隊
    "village",  # 村落
    "secret",  # 秘境（隱藏）
    "elite_lair",  # 精英巢穴
    "boss",  # 區域 Boss 據點（18.3；Phase 5 計畫 Q16）
    "gate",  # 通往其他區域的傳送點（18.3；Phase 5 計畫 Q16）
]

type RevealMethod = Literal[
    "perception_nearby",  # 靠近時感知判定（9.6.7 #10）
    "situation",  # 情境判定成功
    "quest_clue",  # 任務線索
    "friend_footprint",  # 朋友的足跡
]

_NO_LEVEL_KINDS = frozenset({"town", "gate"})
"""沒有建議等級的地點種類。"""
_NO_BATTLE_KINDS = frozenset({"town", "gate", "village", "caravan"})
"""不能放戰鬥地圖的地點種類。"""
_BATTLE_REQUIRED_KINDS = frozenset({"camp", "elite_lair", "secret"})
"""至少要有 1 張戰鬥地圖的地點種類。"""
_NEVER_HIDDEN_KINDS = frozenset({"town", "gate"})


class MapPos(ContentModel):
    """前端畫地點圖用的相對座標（0～100；純顯示，不進規則）。"""

    x: int = Field(ge=0, le=100)
    y: int = Field(ge=0, le=100)


class LocationDef(ContentModel):
    """地點圖上的一個地點。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    kind: LocationKind
    level_min: int | None = Field(default=None, ge=1)
    """建議等級（9.6.2）；``town``、``gate`` 必須省略，其餘必填。"""
    level_max: int | None = Field(default=None, ge=1)
    """省略＝同 ``level_min``（載入時補上）。"""
    battle_maps: tuple[str, ...] = ()
    """``content/maps/`` 的地圖 ID（遇敵時展開格子戰場用，9.6.2）。"""
    hidden: bool = False
    """要探索才會出現（9.6.2）。"""
    reveal: tuple[RevealMethod, ...] = ()
    """隱藏地點的出現方式；``hidden`` 時必填。"""
    gate_to: str | None = Field(default=None, pattern=ID_PATTERN)
    """只有 ``gate`` 可填（且必填）：通往的區域 ID。"""
    unlock_flag: str | None = Field(default=None, pattern=ID_PATTERN)
    """世界旗標 ID；有值＝旗標成立前不能進入（只存資料，判定在 5A-2 之後）。"""
    description_zh: str = ""
    """地點說明（純顯示）。"""
    pos: MapPos

    @model_validator(mode="before")
    @classmethod
    def _default_level_max(cls, data: object) -> object:
        if isinstance(data, dict) and data.get("level_max") is None:
            level_min = data.get("level_min")
            if level_min is not None:
                return {**data, "level_max": level_min}
        return data

    @model_validator(mode="after")
    def _check(self) -> LocationDef:
        problems = [
            *self._level_problems(),
            *self._battle_map_problems(),
            *self._hidden_problems(),
            *self._gate_problems(),
        ]
        if problems:
            raise ValueError(f"地點 {self.id}：{'；'.join(problems)}")
        return self

    def _level_problems(self) -> list[str]:
        if self.kind in _NO_LEVEL_KINDS:
            if self.level_min is not None or self.level_max is not None:
                return [f"{self.kind} 不可填建議等級"]
            return []
        if self.level_min is None:
            return ["必須填建議等級 level_min"]
        if self.level_max is not None and self.level_max < self.level_min:
            return [f"level_max {self.level_max} 小於 level_min {self.level_min}"]
        return []

    def _battle_map_problems(self) -> list[str]:
        out: list[str] = []
        if len(set(self.battle_maps)) != len(self.battle_maps):
            out.append("battle_maps 有重複的地圖")
        if self.kind in _NO_BATTLE_KINDS and self.battle_maps:
            out.append(f"{self.kind} 不可有戰鬥地圖")
        if self.kind in _BATTLE_REQUIRED_KINDS and not self.battle_maps:
            out.append(f"{self.kind} 至少要有 1 張戰鬥地圖")
        return out

    def _hidden_problems(self) -> list[str]:
        out: list[str] = []
        if self.kind == "secret" and not self.hidden:
            out.append("秘境（secret）必須是隱藏地點")
        if self.kind in _NEVER_HIDDEN_KINDS and self.hidden:
            out.append(f"{self.kind} 不可隱藏")
        if self.hidden and not self.reveal:
            out.append("隱藏地點必須填 reveal（出現方式）")
        if len(set(self.reveal)) != len(self.reveal):
            out.append("reveal 有重複")
        return out

    def _gate_problems(self) -> list[str]:
        if self.kind == "gate" and self.gate_to is None:
            return ["傳送點（gate）必須填 gate_to"]
        if self.kind != "gate" and self.gate_to is not None:
            return ["只有傳送點（gate）可以填 gate_to"]
        return []


class LocationMapDef(ContentModel):
    """一個區域的地點圖（一區一檔，檔名＝``region``）。"""

    region: str = Field(pattern=ID_PATTERN)
    """``regions.yaml`` 的區域 ID。"""
    name_zh: str = Field(min_length=1)
    level_min: int = Field(ge=1)
    """區域等級範圍（7.8）。"""
    level_max: int = Field(ge=1)
    town: str = Field(pattern=ID_PATTERN)
    """本區小鎮的地點 ID（9.6.1，每區 1 座）。"""
    locations: tuple[LocationDef, ...]
    edges: tuple[tuple[str, str], ...]
    """無向連線。"""

    @model_validator(mode="after")
    def _check(self) -> LocationMapDef:
        problems = [
            *self._count_problems(),
            *self._town_problems(),
            *self._level_problems(),
            *self._gate_problems(),
            *self._edge_problems(),
        ]
        if not problems:
            problems = self._connectivity_problems()
        if problems:
            raise ValueError(f"地點圖 {self.region}：{'；'.join(problems)}")
        return self

    # ---- 單檔驗證 ----

    def _count_problems(self) -> list[str]:
        out: list[str] = []
        count = len(self.locations)
        if not MIN_LOCATIONS <= count <= MAX_LOCATIONS:
            out.append(f"地點數 {count} 不在 {MIN_LOCATIONS}～{MAX_LOCATIONS} 之內")
        seen: set[str] = set()
        for loc in self.locations:
            if loc.id in seen:
                out.append(f"地點 ID {loc.id} 重複")
            seen.add(loc.id)
        return out

    def _town_problems(self) -> list[str]:
        towns = sorted(loc.id for loc in self.locations if loc.kind == "town")
        if len(towns) != 1:
            return [f"小鎮（town）必須恰好 1 個，目前 {len(towns)} 個（{', '.join(towns)}）"]
        if towns[0] != self.town:
            return [f"town 欄位 {self.town} 不是本區的小鎮（小鎮是 {towns[0]}）"]
        return []

    def _level_problems(self) -> list[str]:
        out: list[str] = []
        if self.level_min > self.level_max:
            out.append(f"區域 level_min {self.level_min} 大於 level_max {self.level_max}")
            return out
        for loc in self.locations:
            for value in (loc.level_min, loc.level_max):
                if value is not None and not self.level_min <= value <= self.level_max:
                    out.append(
                        f"地點 {loc.id} 的建議等級 {value} 超出區域範圍"
                        f" {self.level_min}～{self.level_max}"
                    )
                    break
        return out

    def _gate_problems(self) -> list[str]:
        return [
            f"傳送點 {loc.id} 的 gate_to 不可是本區 {self.region}"
            for loc in self.locations
            if loc.gate_to == self.region
        ]

    def _edge_problems(self) -> list[str]:
        out: list[str] = []
        ids = {loc.id for loc in self.locations}
        seen: set[tuple[str, str]] = set()
        for a, b in self.edges:
            unknown = sorted({a, b} - ids)
            if unknown:
                out.append(f"連線 {a}–{b} 的端點不是本圖的地點：{', '.join(unknown)}")
            if a == b:
                out.append(f"連線 {a}–{b} 不可自己連自己")
            key = (a, b) if a <= b else (b, a)
            if key in seen:
                out.append(f"連線 {a}–{b} 重複（無向）")
            seen.add(key)
        return out

    def _connectivity_problems(self) -> list[str]:
        out: list[str] = []
        all_ids = sorted(loc.id for loc in self.locations)
        reached = _bfs(self.town, self._adjacency(all_ids))
        missing = [i for i in all_ids if i not in reached]
        if missing:
            out.append(f"從小鎮 {self.town} 走不到：{', '.join(missing)}")
        visible = sorted(loc.id for loc in self.locations if not loc.hidden)
        reached_visible = _bfs(self.town, self._adjacency(visible))
        cut = [i for i in visible if i not in reached_visible and i not in missing]
        if cut:
            out.append(f"不經過隱藏地點就走不到（隱藏地點不可是唯一通路）：{', '.join(cut)}")
        return out

    # ---- 查詢 ----

    def _adjacency(self, ids: Iterable[str]) -> dict[str, tuple[str, ...]]:
        """只含 ``ids`` 內地點的鄰接表；每個地點的鄰居依 ID 排序。"""
        allowed = sorted(set(ids))
        found: dict[str, list[str]] = {i: [] for i in allowed}
        for a, b in self.edges:
            if a in found and b in found and a != b:
                found[a].append(b)
                found[b].append(a)
        return {i: tuple(sorted(set(found[i]))) for i in allowed}

    def location_by_id(self) -> dict[str, LocationDef]:
        return {loc.id: loc for loc in self.locations}

    def neighbors(self, location_id: str) -> tuple[str, ...]:
        """相鄰地點的 ID（依 ID 排序）；未知的地點拋出 ``KeyError``。"""
        adjacency = self._adjacency(loc.id for loc in self.locations)
        try:
            return adjacency[location_id]
        except KeyError:
            raise KeyError(f"地點圖 {self.region} 沒有地點 {location_id}") from None

    def summary(self) -> str:
        hidden = sum(1 for loc in self.locations if loc.hidden)
        return (
            f"{self.name_zh}：{len(self.locations)} 個地點（隱藏 {hidden}）、"
            f"{len(self.edges)} 條連線、等級 {self.level_min}～{self.level_max}"
        )


def _bfs(start: str, adjacency: Mapping[str, tuple[str, ...]]) -> set[str]:
    """從 ``start`` 出發走得到的地點（含自己）；``start`` 不在圖內時回傳空集合。"""
    if start not in adjacency:
        return set()
    reached = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in adjacency[current]:
            if nxt not in reached:
                reached.add(nxt)
                queue.append(nxt)
    return reached


def world_map_problems(
    world_map: LocationMapDef,
    *,
    regions: RegionTable | None,
    maps: Mapping[str, MapDef],
) -> list[str]:
    """跨檔案檢查：區域、傳送目的地、戰鬥地圖 ID、地圖類型在該區地圖池內。

    回傳排序過的問題清單；空＝通過。沒有 ``regions.yaml``（``regions`` 為 ``None``）時
    無法驗證區域，回報為問題。
    """
    problems: list[str] = []
    pool: frozenset[str] = frozenset()
    if regions is None:
        problems.append(f"地點圖 {world_map.region}：缺少 regions.yaml，無法檢查區域")
    else:
        by_id = regions.region_by_id()
        region = by_id.get(world_map.region)
        if region is None:
            problems.append(f"地點圖 {world_map.region}：未知的區域 {world_map.region}")
        else:
            pool = frozenset(region.map_pool)
        for loc in world_map.locations:
            if loc.gate_to is not None and loc.gate_to not in by_id:
                problems.append(f"地點 {loc.id}：gate_to 是未知的區域 {loc.gate_to}")
    for loc in world_map.locations:
        problems += _battle_map_refs(loc, maps, pool)
    return sorted(problems)


def _battle_map_refs(
    loc: LocationDef, maps: Mapping[str, MapDef], pool: frozenset[str]
) -> list[str]:
    out: list[str] = []
    for map_id in loc.battle_maps:
        map_def = maps.get(map_id)
        if map_def is None:
            out.append(f"地點 {loc.id}：未知的戰鬥地圖 {map_id}")
        elif map_def.archetype == BOSS_ARCHETYPE:
            if loc.kind != "boss":
                out.append(f"地點 {loc.id}：Boss 地圖 {map_id} 只能放在 boss 地點")
        elif pool and loc.kind != "boss" and map_def.archetype not in pool:
            out.append(f"地點 {loc.id}：地圖 {map_id} 的類型 {map_def.archetype} 不在本區地圖池內")
    return out
