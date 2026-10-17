"""戰鬥狀態模型與序列化。

- 以 ``dataclass(slots=True)`` 實作（複製比 pydantic model 快，Phase 2 模擬器要跑大量戰鬥），
  以 pydantic :class:`~pydantic.TypeAdapter` 序列化為 JSON 並完整往返。
- 單位以 ID 為鍵的字典存放；需要迭代時一律依 ID 排序（:meth:`BattleState.units_sorted`）。
- 地圖格子 :class:`Tile` 不可變，整張地圖是 ``tuple``，複製狀態時共用；改變格子時替換元素。
- :attr:`BattleState.ruleset` 是整份規則資料（不可變、複製時共用），讓重播不依賴當下的資料檔。
- 亂數狀態存放在 :attr:`BattleState.rng_state`，``resolve`` 內部以 ``Rng.from_state`` 還原。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from pydantic import TypeAdapter

from trpg.content.battle import WeaponDef
from trpg.content.library import Ruleset
from trpg.shared.types import Attribute, Element, ObjectId, Pos, ResistGroup, Surface, Team, UnitId

__all__ = [
    "BattleState",
    "StatusInstance",
    "Tile",
    "UnitState",
    "state_from_json",
    "state_to_json",
]


@dataclass(slots=True, frozen=True)
class StatusInstance:
    """單位身上的一個狀態。``remaining`` 為剩餘回合（``None`` 表示不倒數）。"""

    status_id: str
    remaining: int | None = None
    source_id: UnitId | None = None


@dataclass(slots=True, frozen=True)
class Tile:
    """一格地圖。``surface``、``object_id`` 於 Phase 1B 起使用。"""

    height: int
    terrain: str
    surface: Surface = Surface.NONE
    object_id: ObjectId | None = None


@dataclass(slots=True)
class UnitState:
    """戰鬥中的單位（可變；只在 ``resolve`` 內部的複本上修改）。"""

    id: UnitId
    template_id: str
    name_zh: str
    team: Team
    pos: Pos
    hp: int
    max_hp: int
    attributes: dict[Attribute, int]
    speed: int
    armor_bonus: int
    weapon: WeaponDef
    resist: dict[ResistGroup, int]
    element_mods: dict[Element, int]
    tags: tuple[str, ...]
    initiative: int = 0
    ap: int = 0
    ap_carry: int = 0
    move_points: int = 0
    statuses: list[StatusInstance] = field(default_factory=list)
    downed: bool = False

    @property
    def alive(self) -> bool:
        return not self.downed

    @property
    def xy(self) -> tuple[int, int]:
        return (self.pos.x, self.pos.y)

    def has_status(self, status_id: str) -> bool:
        return any(s.status_id == status_id for s in self.statuses)

    def get_status(self, status_id: str) -> StatusInstance | None:
        for s in self.statuses:
            if s.status_id == status_id:
                return s
        return None

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def clone(self) -> UnitState:
        # 屬性、抗性等字典在戰鬥中不會被修改，可以共用；只有狀態清單需要複製。
        return replace(self, statuses=list(self.statuses))


@dataclass(slots=True)
class BattleState:
    """一場戰鬥的完整狀態。``初始狀態 ＋ 動作列表`` 即可完整重播。"""

    map_id: str
    map_name_zh: str
    width: int
    height: int
    tiles: tuple[Tile, ...]
    ruleset: Ruleset
    units: dict[UnitId, UnitState]
    turn_order: list[UnitId]
    turn_pos: int
    active_unit: UnitId | None
    round: int
    max_rounds: int | None
    seed: int
    rng_state: tuple[int, int, int, int]
    next_event_seq: int = 0
    ended: bool = False
    winner: Team | None = None
    end_reason: str | None = None

    # ------------------------------------------------------------------
    # 複製
    # ------------------------------------------------------------------

    def clone(self) -> BattleState:
        """深度足夠的複本：之後修改複本不會影響原狀態。"""
        return replace(
            self,
            units={uid: unit.clone() for uid, unit in self.units.items()},
            turn_order=list(self.turn_order),
        )

    # ------------------------------------------------------------------
    # 地圖
    # ------------------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, x: int, y: int) -> Tile:
        return self.tiles[y * self.width + x]

    # ------------------------------------------------------------------
    # 單位
    # ------------------------------------------------------------------

    def unit(self, unit_id: UnitId) -> UnitState:
        return self.units[unit_id]

    def units_sorted(self) -> list[UnitState]:
        return [self.units[uid] for uid in sorted(self.units)]

    def living_units(self) -> list[UnitState]:
        return [u for u in self.units_sorted() if u.alive]

    def unit_at(self, x: int, y: int) -> UnitState | None:
        """站在 ``(x, y)`` 的存活單位（同一格最多一個）。"""
        for uid in sorted(self.units):
            u = self.units[uid]
            if u.alive and u.pos.x == x and u.pos.y == y:
                return u
        return None

    def occupancy(self) -> dict[tuple[int, int], UnitState]:
        """存活單位的位置表。"""
        return {u.xy: u for u in self.living_units()}

    @property
    def active(self) -> UnitState | None:
        return None if self.active_unit is None else self.units[self.active_unit]


_STATE_ADAPTER: TypeAdapter[BattleState] = TypeAdapter(BattleState)


def state_to_json(state: BattleState) -> str:
    """序列化為 JSON 字串（確定性：相同狀態必得相同字串）。"""
    return _STATE_ADAPTER.dump_json(state).decode("utf-8")


def state_from_json(text: str | bytes) -> BattleState:
    return _STATE_ADAPTER.validate_json(text)
