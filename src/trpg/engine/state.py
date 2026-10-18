"""戰鬥狀態模型與序列化。

- 以 ``dataclass(slots=True)`` 實作（複製比 pydantic model 快，Phase 2 模擬器要跑大量戰鬥），
  以 pydantic :class:`~pydantic.TypeAdapter` 序列化為 JSON 並完整往返。
- 單位以 ID 為鍵的字典存放；需要迭代時一律依 ID 排序（:meth:`BattleState.units_sorted`）。
- 地圖格子 :class:`Tile` 不可變；整張地圖是 ``list``，複製狀態時複製串列（格子本身共用），
  改變格子時替換元素（:meth:`BattleState.set_tile`）。
- 格子物件 :class:`ObjectState` 以 ID 為鍵存放；摧毀後保留在字典中（``destroyed=True``）。
- :attr:`BattleState.ruleset` 是整份規則資料（不可變、複製時共用），讓重播不依賴當下的資料檔。
- 亂數狀態存放在 :attr:`BattleState.rng_state`，``resolve`` 內部以 ``Rng.from_state`` 還原。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, TypeAdapter

from trpg.content.battle import ReactionRule, UnitTemplate, WeaponDef
from trpg.content.environment import ObjectDef, WeatherDef
from trpg.content.library import Ruleset
from trpg.content.maps import MapEvent, Objective
from trpg.shared.types import Attribute, Element, ObjectId, Pos, ResistGroup, Surface, Team, UnitId

__all__ = [
    "BattleState",
    "ObjectState",
    "PendingResolution",
    "SpawnTemplate",
    "StatusInstance",
    "Tile",
    "UnitState",
    "state_from_json",
    "state_to_json",
]


@dataclass(slots=True, frozen=True)
class StatusInstance:
    """單位身上的一個狀態。``remaining`` 為剩餘回合（``None`` 表示不倒數）。

    ``amount``：護盾的剩餘吸收量（只有 ``absorbs_damage`` 的狀態使用，Phase 2D-1）。"""

    status_id: str
    remaining: int | None = None
    source_id: UnitId | None = None
    amount: int | None = None


@dataclass(slots=True, frozen=True)
class Tile:
    """一格地圖。

    - ``surface_remaining``：表面剩餘的環境回合數（``None`` 為永久）。
    - ``surface_team``：產生表面者的陣營（聖光表面只治療同陣營；地圖原有的表面為 ``None``）。
    - ``object_id``：格上的物件（最多一個；摧毀後清除）。
    """

    height: int
    terrain: str
    surface: Surface = Surface.NONE
    surface_remaining: int | None = None
    surface_team: Team | None = None
    object_id: ObjectId | None = None


@dataclass(slots=True)
class ObjectState:
    """戰場上的格子物件（可變；只在 ``resolve`` 內部的複本上修改）。

    ``burning``：著火後剩餘的環境回合數，歸零時摧毀（``None`` 表示沒有著火）。
    ``burn_source``：點燃它的單位（燒斷橋造成的墜落歸給點燃者；追溯不到為 ``None``）。
    """

    id: ObjectId
    kind: str
    pos: Pos
    hp: int | None
    max_hp: int | None
    burning: int | None = None
    destroyed: bool = False
    burn_source: UnitId | None = None

    @property
    def xy(self) -> tuple[int, int]:
        return (self.pos.x, self.pos.y)

    def clone(self) -> ObjectState:
        # 明確列出欄位（比 dataclasses.replace 快數倍；tests/engine/test_state_clone.py 檢查
        # 這裡涵蓋所有欄位）。
        return ObjectState(
            id=self.id,
            kind=self.kind,
            pos=self.pos,
            hp=self.hp,
            max_hp=self.max_hp,
            burning=self.burning,
            destroyed=self.destroyed,
            burn_source=self.burn_source,
        )


class SpawnTemplate(BaseModel):
    """可在戰鬥中產生的單位（地圖事件的援軍、Phase 2 的召喚）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    template: UnitTemplate
    weapon: WeaponDef


@dataclass(slots=True, frozen=True)
class PendingResolution:
    """暫停中的結算（``prompt`` 反應等待決定）。

    恢復時從 ``base_state_json``（動作之前的狀態）以 ``decisions`` 重新結算 ``action_json``；
    結算是確定的，因此會重現暫停前的所有結果，再接著套用新的決定。
    ``events_emitted`` 是已回傳給呼叫端的事件數（恢復時只回傳之後的事件）。
    """

    action_json: str
    decisions: tuple[bool, ...]
    base_state_json: str
    events_emitted: int
    kind: str
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None


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
    stamina: int = 0
    max_stamina: int = 0
    reactions: tuple[ReactionRule, ...] = ()
    reactions_used: int = 0
    escaped: bool = False
    ai_profile: str | None = None
    mana: int = 0
    max_mana: int = 0
    skills: tuple[str, ...] = ()
    cooldowns: dict[str, int] = field(default_factory=dict)
    """技能剩餘冷卻回合（只列出 > 0 的）；自己回合開始時 −1。"""
    skill_uses: dict[str, int] = field(default_factory=dict)
    """本場已使用次數（``uses_per_battle`` 檢查用）。"""
    control_dr: dict[str, int] = field(default_factory=dict)
    """控制遞減：控制類別 → 遞減持續到的輪數（含；``state.round`` 不超過它時，同類別的抵抗判定中
    守方屬性 ×``control_dr_resist_permille``）。"""

    @property
    def alive(self) -> bool:
        """仍在戰場上（未倒下、未撤離）。"""
        return not self.downed and not self.escaped

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
        # 屬性、抗性等字典在戰鬥中不會被修改，可以共用；狀態清單、冷卻與使用次數需要複製。
        # 明確列出欄位（比 dataclasses.replace 快數倍；tests/engine/test_state_clone.py 檢查
        # 這裡涵蓋所有欄位）。
        return UnitState(
            id=self.id,
            template_id=self.template_id,
            name_zh=self.name_zh,
            team=self.team,
            pos=self.pos,
            hp=self.hp,
            max_hp=self.max_hp,
            attributes=self.attributes,
            speed=self.speed,
            armor_bonus=self.armor_bonus,
            weapon=self.weapon,
            resist=self.resist,
            element_mods=self.element_mods,
            tags=self.tags,
            initiative=self.initiative,
            ap=self.ap,
            ap_carry=self.ap_carry,
            move_points=self.move_points,
            statuses=list(self.statuses),
            downed=self.downed,
            stamina=self.stamina,
            max_stamina=self.max_stamina,
            reactions=self.reactions,
            reactions_used=self.reactions_used,
            escaped=self.escaped,
            ai_profile=self.ai_profile,
            mana=self.mana,
            max_mana=self.max_mana,
            skills=self.skills,
            cooldowns=dict(self.cooldowns),
            skill_uses=dict(self.skill_uses),
            control_dr=dict(self.control_dr),
        )


@dataclass(slots=True)
class BattleState:
    """一場戰鬥的完整狀態。``初始狀態 ＋ 動作列表`` 即可完整重播。"""

    map_id: str
    map_name_zh: str
    width: int
    height: int
    tiles: list[Tile]
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
    objects: dict[ObjectId, ObjectState] = field(default_factory=dict)
    weather: WeatherDef | None = None
    objective: Objective = field(default_factory=Objective)
    map_events: tuple[MapEvent, ...] = ()
    spawn_templates: dict[str, SpawnTemplate] = field(default_factory=dict)
    pending: PendingResolution | None = None

    # ------------------------------------------------------------------
    # 複製
    # ------------------------------------------------------------------

    def clone(self) -> BattleState:
        """深度足夠的複本：之後修改複本不會影響原狀態。

        明確列出欄位（比 dataclasses.replace 快；tests/engine/test_state_clone.py 檢查涵蓋
        所有欄位）。
        """
        return BattleState(
            map_id=self.map_id,
            map_name_zh=self.map_name_zh,
            width=self.width,
            height=self.height,
            tiles=list(self.tiles),
            ruleset=self.ruleset,
            units={uid: unit.clone() for uid, unit in self.units.items()},
            turn_order=list(self.turn_order),
            turn_pos=self.turn_pos,
            active_unit=self.active_unit,
            round=self.round,
            max_rounds=self.max_rounds,
            seed=self.seed,
            rng_state=self.rng_state,
            next_event_seq=self.next_event_seq,
            ended=self.ended,
            winner=self.winner,
            end_reason=self.end_reason,
            objects={oid: obj.clone() for oid, obj in self.objects.items()},
            weather=self.weather,
            objective=self.objective,
            map_events=self.map_events,
            spawn_templates=self.spawn_templates,
            pending=self.pending,
        )

    # ------------------------------------------------------------------
    # 地圖
    # ------------------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, x: int, y: int) -> Tile:
        return self.tiles[y * self.width + x]

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        self.tiles[y * self.width + x] = tile

    # ------------------------------------------------------------------
    # 物件
    # ------------------------------------------------------------------

    def object_at(self, x: int, y: int) -> ObjectState | None:
        """``(x, y)`` 上未摧毀的物件。"""
        oid = self.tiles[y * self.width + x].object_id
        return None if oid is None else self.objects[oid]

    def object_def(self, obj: ObjectState) -> ObjectDef:
        return self.ruleset.object_def(obj.kind)

    def object_has_tag(self, x: int, y: int, tag: str) -> bool:
        obj = self.object_at(x, y)
        return obj is not None and tag in self.ruleset.object_def(obj.kind).tags

    def objects_sorted(self) -> list[ObjectState]:
        """未摧毀的物件，依 ID 排序。"""
        return [self.objects[o] for o in sorted(self.objects) if not self.objects[o].destroyed]

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
