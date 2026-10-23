"""效果（effect）的資料模型。

動作展開為效果，放入佇列逐一結算（``docs/專案計畫.md`` 5.9）。每個效果帶 ``depth``：
由動作直接產生的為 0，由事件觸發的為觸發來源的 ``depth + 1``。

新增效果類型（Phase 1B、Phase 2 的原語）：在這裡新增 model 並加入 :data:`Effect`，
再以 :func:`trpg.engine.effects.queue.register_effect` 註冊處理器。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.content.battle import Dice
from trpg.engine.events import DamageCause, MoveMode, ObjectDestroyCause
from trpg.shared.types import Attribute, Element, ObjectId, Pos, Surface, Team, UnitId

__all__ = [
    "EFFECT_LIST_ADAPTER",
    "ApplyStatusEffect",
    "BombBlastEffect",
    "CancelChargeEffect",
    "ChangeTileEffect",
    "CleanseEffect",
    "CreateObstacleEffect",
    "CreateSurfaceEffect",
    "DamageEffect",
    "DamageObjectEffect",
    "DestroyObjectEffect",
    "DetonateRuneEffect",
    "Effect",
    "EffectBase",
    "ElementTouchEffect",
    "ExplodeEffect",
    "HealEffect",
    "HurlObjectEffect",
    "IgniteObjectEffect",
    "InscribeEffect",
    "LowerTerrainEffect",
    "MoveUnitEffect",
    "PushEffect",
    "RaiseTerrainEffect",
    "RemoveStatusEffect",
    "ShieldEffect",
    "SpawnUnitEffect",
]

type XY = tuple[int, int]
type Direction = tuple[int, int]


class EffectBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    depth: int = Field(default=0, ge=0)
    source_id: UnitId | None = None

    # 佇列排序用（同一時刻產生的效果依「來源單位 ID → 目標 ID → 格子座標」排序）
    def sort_target(self) -> str:
        return ""

    def sort_pos(self) -> tuple[int, int]:
        return (-1, -1)


class DamageEffect(EffectBase):
    """傷害。

    ``mode``：

    - ``roll``：``(骰子 ＋ flat ＋ scaled_permille ÷ 1000) × 元素修正``，無條件捨去，
      最低 ``min_damage``；``crit`` 時骰子顆數加倍、固定值不加倍。
    - ``percent_max_hp``：最大 HP × ``permille`` ÷ 1000（無條件捨去，最低 ``min_damage``）。
    - ``lethal``：直接把 HP 降為 0（致命地形）。

    ``apply_element_mod=False`` 時不套用元素修正（墜落、致命地形等以最大 HP 比例計算的傷害）。
    ``multiplier_permille``：最後再乘上的倍率（格擋 500 = 傷害減半），無條件捨去，最低
    ``min_damage``。``mode == "roll"`` 時另套用天氣的元素傷害修正（``apply_weather=False`` 時
    不套用：例如雷電擴散的基準傷害已含天氣修正，避免重複計算）。
    """

    kind: Literal["damage"] = "damage"
    target_id: UnitId
    cause: DamageCause = "effect"
    element: Element = Element.PHYSICAL
    mode: Literal["roll", "percent_max_hp", "lethal"] = "roll"
    dice: Dice | None = None
    flat: int = 0
    scaled_permille: int = 0
    block_permille: int = Field(default=1000, ge=0)
    """格擋倍率（Phase 3-41b，僅供紀錄顯示）：已包含在 ``multiplier_permille`` 裡，不再乘。"""
    scale_attr: Attribute | None = None
    """屬性加成的來源屬性（僅供紀錄顯示；Phase 3-41b）。"""
    crit: bool = False
    permille: int = Field(default=0, ge=0)
    apply_element_mod: bool = True
    apply_weather: bool = True
    min_damage: int = Field(default=1, ge=0)
    multiplier_permille: int = Field(default=1000, ge=0)
    pierce_permille: int = Field(default=1000, ge=0)
    """穿透後方折扣（Phase 3C-6a，僅供紀錄顯示）：已包含在 ``multiplier_permille`` 裡，不再乘。"""
    explode_max: int = Field(default=0, ge=0)
    """爆骰（Phase 3D-7b）：傷害骰擲到最大值時再加擲一次，每顆骰最多再擲這麼多次（0 為不爆骰）。"""
    preset_rolls: tuple[int, ...] | None = None
    """已經擲好的骰值（Phase 3D-8a 聖光雙效：敵方的傷害與友方的治療共用同一次擲骰）。暴擊的額外骰子
    另外擲。"""

    def sort_target(self) -> str:
        return self.target_id


class HealEffect(EffectBase):
    """治療：``骰子 ＋ flat ＋ scaled_permille ÷ 1000``，不超過最大 HP；倒下的單位不能被治療
    （Phase 1 沒有復活）。``scaled_permille`` 為縮放屬性 × 法術倍率（Phase 2A 的治療技能）。"""

    kind: Literal["heal"] = "heal"
    target_id: UnitId
    dice: Dice | None = None
    flat: int = 0
    scaled_permille: int = 0
    preset_rolls: tuple[int, ...] | None = None
    """已經擲好的骰值（Phase 3D-8a 聖光雙效）；省略時依 ``dice`` 擲骰。"""
    cause: Literal["heal", "lifesteal"] = "heal"
    """``lifesteal``：吸血（Phase 3D-8a；``flat`` 為回復量）。"""
    multiplier_permille: int = 1000
    """施放者的治療量倍率（‰；修正規則 ``heal_permille``，Phase 3-24b1）；1000 為不變。"""

    def sort_target(self) -> str:
        return self.target_id


class MoveUnitEffect(EffectBase):
    """把單位移到 ``dest``。

    - ``walk``：主動移動的一步（合法性已由 ``Move`` 動作檢查；可暫時穿過友方）。
    - ``forced``：強制位移；目的地有其他單位或超出地圖時不移動（``move_blocked``）。
    - ``teleport``：傳送；不觸發墜落。
    - ``teleported``：被別人傳送（Phase 3D-2b ``teleport_target``）；不觸發墜落，但落點的陷阱、
      表面與致命地形照常結算。
    - ``dash``／``leap``：衝鋒的一步／跳躍的落點（Phase 3D-2）；同步行，會墜落、觸發陷阱與
      表面（``leap`` 的高度差限制在 1 層以內，不會墜落）。

    ``walk`` 與 ``forced`` 往下落差達門檻時觸發墜落；進入致命地形時觸發致命地形規則。
    """

    kind: Literal["move_unit"] = "move_unit"
    unit_id: UnitId
    dest: tuple[int, int]
    mode: MoveMode = "forced"
    cost: int = 0

    def sort_target(self) -> str:
        return self.unit_id

    def sort_pos(self) -> tuple[int, int]:
        return (self.dest[1], self.dest[0])

    @property
    def dest_pos(self) -> Pos:
        return Pos(x=self.dest[0], y=self.dest[1])


class SwapUnitsEffect(EffectBase):
    """兩個單位交換位置（``swap``，Phase 3D-2）：``unit_id`` 到 ``other_id`` 的格子、反過來亦然，
    各自結算抵達的後果（事件 ``unit_moved`` 的 ``mode`` 為 ``swap``）。任一方不在場或任一格不能站
    立時不交換（``effect_fizzled``）。"""

    kind: Literal["swap_units"] = "swap_units"
    unit_id: UnitId
    other_id: UnitId

    def sort_target(self) -> str:
        return self.unit_id


class ApplyStatusEffect(EffectBase):
    """施加狀態；``duration`` 為 ``None`` 時使用狀態定義的預設值。重複施加時刷新持續時間。"""

    kind: Literal["apply_status"] = "apply_status"
    target_id: UnitId
    status_id: str
    duration: int | None = Field(default=None, ge=1)
    amount: int | None = Field(default=None, ge=1)
    """狀態的數值（``StatusInstance.amount``）；``soul_link`` 的轉移千分比（Phase 3C-4b）。"""
    skill_id: str | None = None
    """施加狀態的技能（``StatusInstance.skill_id``；定時炸彈，Phase 3D-8b）。"""

    def sort_target(self) -> str:
        return self.target_id


class RemoveStatusEffect(EffectBase):
    """移除狀態（不存在時沒有效果）。"""

    kind: Literal["remove_status"] = "remove_status"
    target_id: UnitId
    status_id: str
    reason: Literal[
        "expired",
        "removed",
        "stood_up",
        "stance_ended",
        "consumed",
        "stolen",
        "dispelled",
        "revealed",
        "downed",
        "fired",
        "ambushed",
    ] = "removed"

    def sort_target(self) -> str:
        return self.target_id


class BombBlastEffect(EffectBase):
    """定時炸彈爆炸（Phase 3D-8b，:mod:`trpg.engine.bombs`）：在攜帶者 ``unit_id`` 目前的位置爆炸。
    ``source_id`` 是施放者、``skill_id`` 是帶有 ``delayed_damage`` 的技能；``cause`` 是倒數歸零或
    攜帶者倒下。處理器發出 ``bomb_exploded``，傷害由它的觸發函式結算。"""

    kind: Literal["bomb_blast"] = "bomb_blast"
    unit_id: UnitId
    skill_id: str
    cause: Literal["timer", "downed"]

    def sort_target(self) -> str:
        return self.unit_id


class CancelChargeEffect(EffectBase):
    """取消延遲段（Phase 3F-4b，:mod:`trpg.engine.delayed`）：移除 ``unit_id`` 身上的 ``charging``
    並發出 ``followup_cancelled``（``reason``：倒下、被控制）。已經沒有蓄力時不做事。"""

    kind: Literal["cancel_charge"] = "cancel_charge"
    unit_id: UnitId
    reason: Literal["downed", "controlled"]

    def sort_target(self) -> str:
        return self.unit_id


class ShieldEffect(EffectBase):
    """護盾（Phase 2D-1）：護盾量 ＝ ``骰子 ＋ flat ＋ scaled_permille ÷ 1000``（與治療同一公式，
    無條件捨去）。目標獲得 ``shielded`` 狀態；已有護盾時吸收量取較大值並刷新持續時間。"""

    kind: Literal["shield"] = "shield"
    target_id: UnitId
    dice: Dice | None = None
    flat: int = 0
    scaled_permille: int = 0
    multiplier_permille: int = 1000
    """技能等級的效果倍率（‰；Phase 3-26a）；1000 為不變，護盾量 ＝ 上式 × 倍率，無條件捨去。"""

    def sort_target(self) -> str:
        return self.target_id


class CleanseEffect(EffectBase):
    """淨化（Phase 2D-1）：移除目標身上所有減益（``polarity: debuff``）的狀態；增益與中性狀態保留（玩法決定 #60），依狀態 ID 排序
    逐一發出 ``status_removed``（原因 ``cleansed``）。"""

    kind: Literal["cleanse"] = "cleanse"
    target_id: UnitId

    def sort_target(self) -> str:
        return self.target_id


# ---------------------------------------------------------------------------
# Phase 1B：環境效果
# ---------------------------------------------------------------------------


class _AtPos(EffectBase):
    pos: XY

    def sort_pos(self) -> tuple[int, int]:
        return (self.pos[1], self.pos[0])


class PushEffect(EffectBase):
    """推擊：沿 ``direction``（單位向量）推動單位或物件 ``distance`` 格（逐格移動，遇阻擋停止）。

    - 單位：帶 ``steadfast`` 標籤者距離 × ``steadfast_push_permille``（無條件捨去）；
      目的地有其他單位、``blocks_move`` 物件、比目前高、或超出地圖時停止。每一步都可能墜落、
      落入致命地形、進入表面。
    - 物件（需 ``pushable``）：目的地有物件、有單位、比目前高、或超出地圖時停止；推入致命地形時
      物件掉落並摧毀。``topplable`` 物件不移動，往 ``direction`` 倒下（推倒，Phase 3C-5a；
      ``distance`` 不影響倒下的長度）。
    """

    kind: Literal["push"] = "push"
    target_id: UnitId | None = None
    object_id: ObjectId | None = None
    direction: Direction
    distance: int = Field(ge=0)
    how: Literal["push", "shove_aside"] = "push"
    """物件被移動的方式（只影響 ``ObjectMoved`` 事件的說明；撥開為 ``shove_aside``）。"""
    collision_dice: Dice | None = None
    """單位被推時的撞擊骰（技能的 ``collision_dice``）；``None`` 用核心規則的預設。"""
    extra_collisions: int = Field(default=0, ge=0)
    """推完之後額外結算的撞擊次數（修正規則把距離加到超過 ``max_displace_distance`` 的部分，
    就算沒有撞到東西也算；Phase 3C-3a）。"""

    def sort_target(self) -> str:
        return self.target_id or self.object_id or ""


class HurlObjectEffect(EffectBase):
    """投擲物件（Phase 3C-5a ``hurl_object``）：把 ``object_id`` 丟到 ``dest`` 並依標籤結算落地
    （爆炸、碎掉漏油、放下或沒有空格而摧毀）。落點單位的傷害由技能另外結算。

    爆炸物（油桶）摔破時預設漏油、不爆炸（Phase 3D-3）；只有 ``ignite``（技能帶火元素）或落點
    本來有火焰表面時才爆炸。"""

    kind: Literal["hurl_object"] = "hurl_object"
    object_id: ObjectId
    dest: XY
    ignite: bool = False
    """投擲技能帶火元素：爆炸物落地時引爆（落點本來有火也會引爆，由結算判斷）。"""

    def sort_target(self) -> str:
        return self.object_id

    def sort_pos(self) -> tuple[int, int]:
        return (self.dest[1], self.dest[0])


class CreateSurfaceEffect(_AtPos):
    """在 ``pos`` 產生表面。

    ``react=True``（技能、天氣、地圖事件）：先查互動表的 ``surface_created`` 規則（例如水熄滅火），
    產生後若表面帶元素，格上物件會被該元素觸及（例如在油桶上產生火焰會引爆）。
    ``react=False``：互動規則的直接結果，不再觸發其他互動。
    ``duration`` 為 ``None`` 時使用表面定義的預設值。
    """

    kind: Literal["create_surface"] = "create_surface"
    surface: Surface
    duration: int | None = Field(default=None, ge=1)
    team: Team | None = None
    react: bool = True
    cause: str = "effect"


class DamageObjectEffect(EffectBase):
    """對物件造成傷害（攻擊命中物件時一律命中，不擲命中骰，不暴擊，物件沒有抗性）。"""

    kind: Literal["damage_object"] = "damage_object"
    object_id: ObjectId
    element: Element = Element.PHYSICAL
    dice: Dice | None = None
    flat: int = 0
    scaled_permille: int = 0
    min_damage: int = Field(default=1, ge=0)
    cause: DamageCause = "effect"
    multiplier_permille: int = Field(default=1000, ge=0)
    """最後再乘上的倍率（武器技的技能倍率），無條件捨去，最低 ``min_damage``。"""

    def sort_target(self) -> str:
        return self.object_id


class DestroyObjectEffect(EffectBase):
    """摧毀物件。``set_terrain`` 不為空時該格地形改為此地形（大地填平深淵）。

    木橋（``over_chasm``）摧毀後，格上的單位落入原本的致命地形。
    """

    kind: Literal["destroy_object"] = "destroy_object"
    object_id: ObjectId
    cause: ObjectDestroyCause = "effect"
    set_terrain: str | None = None

    def sort_target(self) -> str:
        return self.object_id


class RaiseTerrainEffect(_AtPos):
    """地形隆起（高度 +``amount``，上限 3）；站在上面的單位跟著升高。"""

    kind: Literal["raise_terrain"] = "raise_terrain"
    amount: int = Field(default=1, ge=1)


class LowerTerrainEffect(_AtPos):
    """地形下陷（高度 −``amount``，下限 0）；站在上面的單位跟著下降（落差達門檻時墜落）。"""

    kind: Literal["lower_terrain"] = "lower_terrain"
    amount: int = Field(default=1, ge=1)


class CreateObstacleEffect(_AtPos):
    """產生障礙物（物件 ``object_kind``）；該格已有物件、單位或不可站立時沒有效果。"""

    kind: Literal["create_obstacle"] = "create_obstacle"
    object_kind: str = "earth_wall"
    duration: int | None = Field(default=None, ge=1)
    """暫時障礙（Phase 3-11）：存在的環境回合數；``None`` 為永久。"""


class InscribeEffect(_AtPos):
    """刻印（Phase 3-23）：在 ``pos`` 留下 ``source_id`` 的符文（恰好帶 ``element`` 或 ``tag``）；
    ``duration`` 省略時用核心規則的預設。不可站立或超出地圖的格子沒有效果。"""

    kind: Literal["inscribe"] = "inscribe"
    team: Team
    element: Element | None = None
    tag: str | None = None
    duration: int | None = Field(default=None, ge=1)


class DetonateRuneEffect(_AtPos):
    """引爆符文（Phase 3-23 ``detonate_runes``）：移除 ``rune_id`` 的符文（傷害另由同一技能的
    ``damage`` 效果結算）。符文已不存在時沒有效果。"""

    kind: Literal["detonate_rune"] = "detonate_rune"
    rune_id: int


class SpawnUnitEffect(_AtPos):
    """產生單位（``template_id`` 必須在 ``BattleState.spawn_templates`` 中）。

    目的地不可站立或已有單位時改到最近的安全格；新單位排在先攻順序的最後。
    """

    kind: Literal["spawn_unit"] = "spawn_unit"
    template_id: str
    team: Team


class ElementTouchEffect(_AtPos):
    """元素觸及一格（技能直接指定格子、環境火勢蔓延、風吹……）：依互動表產生後續效果。

    ``direction``／``push_distance`` 供風的推擊與火勢蔓延使用；``damage`` 為雷電擴散的基準傷害。
    ``objects_only``：只套用物件類規則（產生帶元素的表面後使用）；``tile_only``：只套用表面與物件
    類規則，不含單位（技能的範圍傷害觸及沒有單位的格子）。
    """

    kind: Literal["element_touch"] = "element_touch"
    element: Element
    direction: Direction | None = None
    push_distance: int = Field(default=0, ge=0)
    damage: int = Field(default=0, ge=0)
    objects_only: bool = False
    tile_only: bool = False


class ExplodeEffect(EffectBase):
    """物件爆炸（參數見物件定義的 ``explosion``）：摧毀物件、範圍內單位受傷、每一格被元素觸及。"""

    kind: Literal["explode"] = "explode"
    object_id: ObjectId

    def sort_target(self) -> str:
        return self.object_id


class IgniteObjectEffect(EffectBase):
    """物件著火：``burning_object_rounds`` 次環境回合後摧毀。"""

    kind: Literal["ignite_object"] = "ignite_object"
    object_id: ObjectId

    def sort_target(self) -> str:
        return self.object_id


class ChangeTileEffect(_AtPos):
    """地圖事件：改變一格的高度、地形或表面（省略的欄位不變）。"""

    kind: Literal["change_tile"] = "change_tile"
    height: int | None = Field(default=None, ge=0, le=3)
    terrain: str | None = None
    surface: Surface | None = None


type Effect = Annotated[
    DamageEffect
    | HealEffect
    | MoveUnitEffect
    | SwapUnitsEffect
    | ApplyStatusEffect
    | BombBlastEffect
    | CancelChargeEffect
    | RemoveStatusEffect
    | ShieldEffect
    | CleanseEffect
    | PushEffect
    | HurlObjectEffect
    | CreateSurfaceEffect
    | DamageObjectEffect
    | DestroyObjectEffect
    | RaiseTerrainEffect
    | LowerTerrainEffect
    | CreateObstacleEffect
    | InscribeEffect
    | DetonateRuneEffect
    | SpawnUnitEffect
    | ElementTouchEffect
    | ExplodeEffect
    | IgniteObjectEffect
    | ChangeTileEffect,
    Field(discriminator="kind"),
]

EFFECT_LIST_ADAPTER: TypeAdapter[list[Effect]] = TypeAdapter(list[Effect])
