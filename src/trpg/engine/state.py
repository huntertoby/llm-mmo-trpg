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
from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

from trpg.content.battle import ReactionRule, UnitTemplate, WeaponDef
from trpg.content.environment import ObjectDef, WeatherDef
from trpg.content.library import Ruleset
from trpg.content.maps import MapEvent, Objective
from trpg.content.rules import CoreRules
from trpg.shared.types import Attribute, Element, ObjectId, Pos, ResistGroup, Surface, Team, UnitId

__all__ = [
    "Activation",
    "BattleState",
    "Facing",
    "GrantedSkill",
    "LastCast",
    "ObjectState",
    "PendingResolution",
    "SpawnTemplate",
    "StatusInstance",
    "Tile",
    "TrapState",
    "UnitState",
    "ZoneState",
    "reaction_limit",
    "state_from_json",
    "state_to_json",
]


type Facing = Literal["north", "east", "south", "west"]
"""單位的朝向（Phase 3D-8d，四方向；北 ＝ y − 1）。背後格 ＝ 位置 ＋ 朝向的反方向。"""


@dataclass(slots=True, frozen=True)
class StatusInstance:
    """單位身上的一個狀態。``remaining`` 為剩餘回合（``None`` 表示不倒數）。

    ``amount``：護盾的剩餘吸收量（只有 ``absorbs_damage`` 的狀態使用，Phase 2D-1）。
    ``skill_id``：施加這個狀態的技能（只有定時炸彈 ``time_bomb`` 使用，Phase 3D-8b：``remaining`` 是
    環境回合的倒數，爆炸的骰子、元素與半徑取自這個技能的 ``delayed_damage`` 效果）。"""

    status_id: str
    remaining: int | None = None
    source_id: UnitId | None = None
    amount: int | None = None
    skill_id: str | None = None


@dataclass(slots=True, frozen=True)
class Tile:
    """一格地圖。

    - ``surface_remaining``：表面剩餘的環境回合數（``None`` 為永久）。
    - ``surface_team``：產生表面者的陣營（聖光表面只治療同陣營；地圖原有的表面為 ``None``）。
    - ``surface_creator``：產生表面的單位 ID（Phase 3C-3b；``on_enter_surface`` 用）。蔓延、天氣、
      地圖原有的表面為 ``None``；環境互動產生的表面沿用觸及它的來源。
    - ``object_id``：格上的物件（最多一個；摧毀後清除）。
    """

    height: int
    terrain: str
    surface: Surface = Surface.NONE
    surface_remaining: int | None = None
    surface_team: Team | None = None
    object_id: ObjectId | None = None
    surface_creator: UnitId | None = None


@dataclass(slots=True, frozen=True)
class TrapState:
    """戰場上的陷阱（Phase 2E-3；不可變，更新時替換）。

    - ``owner_id``／``team``：放置者與其陣營（只有這個陣營看得到，見 ``trpg.engine.traps``）。
    - ``skill_id``：陷阱技能（觸發時的效果、觸發方式與範圍都來自它的 ``trap`` 欄位）。
    - ``remaining``：剩餘輪數，放置者每次回合開始 −1，歸零時 ``delay`` 觸發、``enter`` 消失。
    - ``attributes``：放置時施放者的有效屬性快照（觸發時的傷害與抵抗判定用）；不可變的
      ``(Attribute, value)`` 配對（Phase 2F-1 3.5），確保狀態複製（``clone``）不會共用同一個
      可變 dict 的參照（舊版是 ``dict[Attribute, int]``，複製 ``traps`` 列表時是淺層複製，
      同一個 dict 物件在原狀態與複本之間共用）。``dict(trap.attributes)`` 仍能還原成一般 dict。
    """

    owner_id: UnitId
    team: Team
    pos: Pos
    skill_id: str
    remaining: int
    attributes: tuple[tuple[Attribute, int], ...]
    revealed_to: tuple[Team, ...] = ()
    """被 ``reveal`` 揭露而看得到這個陷阱的其他陣營（Phase 3D-8a；放置者陣營本來就看得到）。"""

    @property
    def xy(self) -> tuple[int, int]:
        return (self.pos.x, self.pos.y)


type ZoneAnchor = Literal["tile", "caster", "moving"]


@dataclass(slots=True, frozen=True)
class ZoneState:
    """戰場上的持續區域（Phase 3D-5，``docs/design/06-技能.md`` 6.16 G；不可變，更新時替換）。

    - ``id``：區域編號（依建立順序，從 1 起；:attr:`BattleState.next_zone_id`）。
    - ``owner_id``／``team``：施放者與其陣營（``affects`` 依這個陣營判斷敵我）。
    - ``skill_id``：區域技能（``effects``、``when``、``affects``、``surface`` 都來自它唯一的
      ``zone`` 效果）。
    - ``anchor``：``tile`` 固定、``caster`` 跟隨施放者、``moving`` 每次環境回合沿 ``direction``
      前進 ``speed`` 格。
    - ``cells``：``tile``／``moving`` 的格子（依 ``(y, x)`` 排序）；``caster`` 為空，格子由施放者
      目前的位置與 ``shape``／``radius`` 展開（:func:`trpg.engine.zones.zone_cells`）。
    - ``expires_round``：施放輪 ＋ ``duration``；施放者在那一輪（或之後）的回合結束時消失，施放者
      不在場時在那一輪的環境回合消失。
    - ``attributes``：建立時施放者的有效屬性快照（結算效果用，同陷阱）。
    """

    id: int
    owner_id: UnitId
    team: Team
    skill_id: str
    anchor: ZoneAnchor
    cells: tuple[Pos, ...]
    expires_round: int
    attributes: tuple[tuple[Attribute, int], ...]
    direction: str | None = None
    speed: int = 0
    shape: str = "self"
    radius: int | None = None


@dataclass(slots=True)
class ObjectState:
    """戰場上的格子物件（可變；只在 ``resolve`` 內部的複本上修改）。

    ``burning``：著火後剩餘的環境回合數，歸零時摧毀（``None`` 表示沒有著火）。
    ``burn_source``：點燃它的單位（燒斷橋造成的墜落歸給點燃者；追溯不到為 ``None``）。
    ``expires_in``（Phase 3-11）：暫時障礙還剩幾次環境回合，歸零時自動移除（``None`` 為永久）。
    """

    id: ObjectId
    kind: str
    pos: Pos
    hp: int | None
    max_hp: int | None
    burning: int | None = None
    destroyed: bool = False
    burn_source: UnitId | None = None
    expires_in: int | None = None

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
            expires_in=self.expires_in,
        )


class SpawnTemplate(BaseModel):
    """可在戰鬥中產生的單位（地圖事件的援軍、Phase 2 的召喚）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    template: UnitTemplate
    weapon: WeaponDef


@dataclass(slots=True, frozen=True)
class Activation:
    """一個生效中的常駐類傳說（Phase 3D-6，``activation``）：技能與結束的輪數。

    ``expires_round``：``timed`` 為啟動輪 ＋ ``legendary_timed_rounds``，持有者在這一輪（或之後）的
    回合開始時結束；``battle`` 為 ``None``（本場剩餘時間有效）。
    """

    skill_id: str
    expires_round: int | None = None


@dataclass(slots=True, frozen=True)
class GrantedSkill:
    """一個暫時獲得的技能（Phase 3D-8c，``grant_skill``）：技能 ID 與剩餘輪數（持有者每個回合
    結束時 −1，歸零時消失）。不佔技能欄位。"""

    skill_id: str
    remaining: int


@dataclass(slots=True, frozen=True)
class LastCast:
    """一次以 ``UseSkill`` 施放的主動技能（Phase 3C-4b）：施放者、技能與施放當輪。
    ``copy_skill`` 只複製本輪內的。"""

    unit_id: UnitId
    skill_id: str
    round: int


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
    kind: Literal["reaction", "copy_skill", "followup"]
    unit_id: UnitId
    reaction: str
    trigger_unit_id: UnitId | None
    skill_id: str | None = None
    copy_skill_id: str | None = None
    trigger_event_seq: int | None = None
    stamina_cost: int = 0
    mana_cost: int = 0
    hp_cost_permille: int = 0


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
    trigger_counts: dict[str, int] = field(default_factory=dict)
    """被動技能本輪已觸發的次數（技能 ID → 次數，只列出 > 0 的）；每輪開始時重設（Phase 2E-1）。"""
    hits_landed: int = 0
    """整場戰鬥累計的命中次數（``every_n_hits`` 的計數；只有裝備了該類被動的單位會累計）。"""
    stacks: dict[str, int] = field(default_factory=dict)
    """身上的層數（層數 ID → 層數，只列出 > 0 的；Phase 2E-3，定義在 ``stacks.yaml``）。"""
    stack_expiry: dict[str, int] = field(default_factory=dict)
    """有 ``expires_after_rounds`` 的層數：層數 ID → 在這一輪開始時清空。"""
    source: int = 0
    """源力（Phase 3C-4a）：傳說技能的代價，上限 ``core.yaml`` 的 ``source_max``。"""
    ap_pending: int = 0
    """``grant_ap`` 給不在自己回合的單位的 AP：下次自己回合開始時加上（不超過本回合上限）。"""
    ap_granted_round: int = 0
    """最近一次被 ``grant_ap`` 給 AP 的輪數（0 為從未；同一單位每輪最多被給一次）。"""
    extra_reactions: int = 0
    """``extra_reaction`` 給的額外反應次數（Phase 3C-4b）：本輪反應上限 ＝ ``reactions_per_round``
    ＋ 此值；每輪開始時歸零。"""
    moved_this_turn: bool = False
    """本回合做過主動移動（步行；傳送與強制位移不算；``moved_this_turn`` 條件，Phase 3D-1）；
    自己回合開始時清除。"""
    turn_cast_tags: tuple[str, ...] = ()
    """本回合已施放的主動技能的標籤（依施放順序、含重複；``cast_tag_this_turn`` 條件，Phase 3D-1）；
    自己回合開始時清除。"""
    owner_id: UnitId | None = None
    """召喚物的召喚者（Phase 3D-4a）；一般單位為 ``None``。"""
    summon_expires_round: int | None = None
    """召喚物在召喚者這一輪（含）的回合結束時消失（施放輪 ＋ ``duration``；Phase 3D-4a）。"""
    dismissed: bool = False
    """召喚物已消失（到期、召喚者離場或超過上限；Phase 3D-4a）。保留在 ``units`` 中（事件仍引用
    它），但不在戰場上。"""
    activations: tuple[Activation, ...] = ()
    """生效中的常駐類傳說（Phase 3D-6），依啟動順序。修正型傳說與規則改變只在這裡列出時生效。"""
    revived: bool = False
    """這個單位在本場戰鬥已經被復活過一次（``revive``，Phase 3D-8b）：每單位每場最多被復活 1 次。"""
    granted_skills: tuple[GrantedSkill, ...] = ()
    """暫時獲得的技能（``grant_skill``，Phase 3D-8c），依獲得順序；不佔技能欄位，不會與 ``skills``
    重複。"""
    facing: Facing = "east"
    """朝向（Phase 3D-8d）：主動移動（步行、衝鋒、跳躍、直線衝撞、瞬步）後面向移動方向，攻擊或對
    單位施放技能後面向目標；強制位移、傳送、交換不改。只影響背刺（``from_behind``）的判斷。"""

    @property
    def alive(self) -> bool:
        """仍在戰場上（未倒下、未撤離、召喚物未消失）。"""
        return not self.downed and not self.escaped and not self.dismissed

    @property
    def is_summon(self) -> bool:
        """召喚物（Phase 3D-4a）：不計入勝負條件、沒有源力、不能撤離。"""
        return self.owner_id is not None

    @property
    def xy(self) -> tuple[int, int]:
        return (self.pos.x, self.pos.y)

    @property
    def all_skills(self) -> tuple[str, ...]:
        """可以使用的技能 ID：裝備的技能，加上暫時獲得的技能（Phase 3D-8c；依獲得順序接在後面）。"""
        if not self.granted_skills:
            return self.skills
        return (*self.skills, *(g.skill_id for g in self.granted_skills))

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
            trigger_counts=dict(self.trigger_counts),
            hits_landed=self.hits_landed,
            stacks=dict(self.stacks),
            stack_expiry=dict(self.stack_expiry),
            source=self.source,
            ap_pending=self.ap_pending,
            ap_granted_round=self.ap_granted_round,
            extra_reactions=self.extra_reactions,
            moved_this_turn=self.moved_this_turn,
            turn_cast_tags=self.turn_cast_tags,
            owner_id=self.owner_id,
            summon_expires_round=self.summon_expires_round,
            dismissed=self.dismissed,
            activations=self.activations,
            revived=self.revived,
            granted_skills=self.granted_skills,
            facing=self.facing,
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
    traps: list[TrapState] = field(default_factory=list)
    """戰場上的陷阱（Phase 2E-3），依 ``(y, x)`` 排序；同一格最多一個。"""
    source_wells: tuple[tuple[int, int], ...] = ()
    """尚未被取用的源泉格（Phase 3C-4a），依 ``(y, x)`` 排序；我方單位進入時 +1 源力並消失。"""
    casts: tuple[LastCast, ...] = ()
    """本輪以 ``UseSkill`` 施放過的主動技能，依施放順序（Phase 3C-4b；``copy_skill`` 複製其中
    最後一個別人施放的）。每次記錄時順便丟掉舊輪的。"""
    zones: list[ZoneState] = field(default_factory=list)
    """戰場上的持續區域（Phase 3D-5），依 ``id`` 排序。"""
    next_zone_id: int = 1
    """下一個區域的編號（Phase 3D-5）。"""

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
            traps=list(self.traps),
            source_wells=self.source_wells,
            casts=self.casts,
            zones=list(self.zones),
            next_zone_id=self.next_zone_id,
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
    # 陷阱
    # ------------------------------------------------------------------

    def trap_at(self, x: int, y: int) -> TrapState | None:
        """``(x, y)`` 上的陷阱（不論陣營；AI 與預覽請改用 ``trpg.engine.traps.visible_traps``）。"""
        for trap in self.traps:
            if trap.pos.x == x and trap.pos.y == y:
                return trap
        return None

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


def reaction_limit(core: CoreRules, unit: UnitState) -> int:
    """單位本輪的反應次數上限：``reactions_per_round`` ＋ ``extra_reaction`` 給的額外次數。"""
    return core.reactions_per_round + unit.extra_reactions


def state_to_json(state: BattleState) -> str:
    """序列化為 JSON 字串（確定性：相同狀態必得相同字串）。"""
    return _STATE_ADAPTER.dump_json(state).decode("utf-8")


def state_from_json(text: str | bytes) -> BattleState:
    return _STATE_ADAPTER.validate_json(text)
