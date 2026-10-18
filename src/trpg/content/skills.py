"""技能系統的內容 schema（``docs/phases/Phase2A計畫.md`` 第 3 節、``docs/design/06-技能.md``）。

對應資料檔：

- ``content/skill_shapes.yaml``：目標形狀（``ShapeTable``）。
- ``content/skill_primitives.yaml``：效果原語（``PrimitiveTable``）。
- ``content/skills/<id>.yaml``：一個檔一個技能（``SkillDef``）。

載入時的驗證分兩層：

1. **schema 內** 的驗證（與其他資料表無關）：欄位範圍、``kind`` 與 ``ap_cost``、``category`` 與
   ``weapon_req``、效果數量、推擊距離等。違反時的訊息為繁體中文。
2. **跨檔案** 的驗證（:func:`skill_problems`）：形狀與原語存在、參數在資料檔定義的範圍內、
   引用的狀態／表面／物件存在。由 :func:`trpg.content.library.load_library` 呼叫。

技能是獨立實體（``docs/design/17-未來展望.md`` 17.5）：``provenance`` 記錄來源、擁有者、是否綁定
與可否交易。2A 只存不用。
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, Dice
from trpg.content.rules import SkillSlots
from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute, Element, Surface

if TYPE_CHECKING:
    from trpg.content.skill_triggers import SkillTriggerDef
    from trpg.content.stacks import StackDef

__all__ = [
    "ADD_STACK",
    "AFFECTS_VALUES",
    "CONSUME_STACK",
    "INTERCEPT",
    "PLACE_TRAP",
    "RARITY_ORDER",
    "REQUIRED_CONDITIONS",
    "REQUIRED_SHAPES",
    "SKELETON_IDS",
    "SKILL_ID_PATTERN",
    "SKILL_REACTION_EVENTS",
    "WEAPON_CLASSES",
    "Affects",
    "ConditionDef",
    "ConditionSpec",
    "ConditionTable",
    "EffectSpec",
    "NarrativeDef",
    "ParamDef",
    "PrimitiveDef",
    "PrimitiveParam",
    "PrimitiveTable",
    "Provenance",
    "ReactionSpec",
    "ShapeBudget",
    "ShapeDef",
    "ShapeSpec",
    "ShapeTable",
    "SkillCost",
    "SkillDef",
    "SkillTable",
    "TrapSpec",
    "TriggerSpec",
    "condition_text",
    "default_affects",
    "rarity_rank",
    "skill_problems",
    "skill_slot_problems",
    "weapon_problem",
]

SKILL_ID_PATTERN = r"^skill_[a-z0-9_]+$"

SKELETON_IDS: tuple[str, ...] = (
    "strike",
    "area",
    "control",
    "displace",
    "builder_finisher",
    "combo",
    "trap",
    "aura",
    "summon",
    "reaction",
    "stance",
    "passive",
)
"""``docs/design/06-技能.md`` 6.9 的 12 種骨架（結構驗證在 Phase 2B 才實作，這裡只檢查 ID）。"""

WEAPON_CLASSES: tuple[str, ...] = ("melee", "ranged", "focus")

REQUIRED_SHAPES: tuple[str, ...] = (
    "self",
    "single",
    "line",
    "cone",
    "cross",
    "square3",
    "ring",
    "ground_tile",
    "chain",
    "allies_in_radius",
)
"""引擎實作的 10 種形狀（``trpg.engine.skills.shapes``），資料檔必須全部定義。"""

REQUIRED_CONDITIONS: tuple[str, ...] = (
    "target_hp_below",
    "self_hp_below",
    "height_advantage",
    "target_on_surface",
    "target_has_status",
)
"""引擎實作的 5 種條件（``trpg.engine.skills.conditions``），資料檔必須全部定義。"""

type Targeting = Literal["self", "unit", "tile", "direction", "none"]
type Affects = Literal["enemies", "allies", "all", "self", "tiles"]
type SkillKind = Literal["active", "reaction", "passive", "stance"]
type ReactionEvent = Literal[
    "hit_by_melee", "hit_by_attack", "ally_hit_adjacent", "enemy_leaves_adjacent"
]
type SkillRarity = Literal["common", "rare", "epic", "legendary"]
type SkillCategory = Literal["weapon", "spell"]
type WeaponReq = Literal["melee", "ranged", "focus", "any"]
type Origin = Literal["builtin", "level_up", "drop", "crafted", "taught", "tome"]

AFFECTS_VALUES: tuple[str, ...] = ("enemies", "allies", "all", "self", "tiles")

RARITY_ORDER: tuple[str, ...] = ("common", "rare", "epic", "legendary")
"""稀有度由低到高。"""


def rarity_rank(rarity: str) -> int:
    """稀有度的高低（普通 0 … 傳說 3）。"""
    return RARITY_ORDER.index(rarity)


_MAX_EFFECTS = 4
_MAX_DISPLACE = 2
_MAX_COOLDOWN = 6
_MAX_AP_COST = 3
_PERMILLE = 1000
_MAX_MULTIPLIER_PERMILLE = 10_000


def _unique(ids: Iterable[str], what: str) -> None:
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    if dup:
        raise ValueError(f"重複的{what} ID：{', '.join(dup)}")


# ---------------------------------------------------------------------------
# 形狀
# ---------------------------------------------------------------------------


class ParamDef(ContentModel):
    """形狀參數的範圍。``allow_weapon``：可寫成字串 ``"weapon"``（武器射程）。"""

    min: int
    max: int
    required: bool = True
    allow_weapon: bool = False

    @model_validator(mode="after")
    def _range(self) -> ParamDef:
        if self.min > self.max:
            raise ValueError(f"參數範圍不合理：min {self.min} > max {self.max}")
        return self


class ShapeBudget(ContentModel):
    """形狀倍率（‰，``docs/phases/Phase2B計畫.md`` 4.2）。

    倍率 ＝ ``by_value_permille[參數值]``（有表格時），否則 ``base_permille ＋ per_unit_permille ×
    參數值``（``param`` 為 ``None`` 時只有 ``base_permille``）。
    """

    base_permille: int = Field(default=1000, ge=1)
    param: str | None = None
    per_unit_permille: int = Field(default=0, ge=0)
    by_value_permille: dict[int, int] | None = None

    @model_validator(mode="after")
    def _check(self) -> ShapeBudget:
        if self.param is None and (self.per_unit_permille or self.by_value_permille):
            raise ValueError("設定 per_unit_permille 或 by_value_permille 時必須指定 param")
        if self.by_value_permille is not None and not self.by_value_permille:
            raise ValueError("by_value_permille 不可為空")
        return self

    def permille_for(self, values: dict[str, int | str]) -> int:
        """``values`` 是技能形狀已填的參數；表格缺少該值時回傳 ``base_permille``。"""
        if self.param is None:
            return self.base_permille
        raw = values.get(self.param)
        value = raw if isinstance(raw, int) else 0
        if self.by_value_permille is not None:
            return self.by_value_permille.get(value, self.base_permille)
        return self.base_permille + self.per_unit_permille * value


class ShapeDef(ContentModel):
    """一種目標形狀。``targeting`` 決定 ``UseSkill`` 需要哪個欄位：

    ``unit``＝``target_id`` 或 ``target_object_id``、``tile``＝``target_pos``、
    ``direction``＝``direction``、``self``／``none``＝不需要。

    ``min_rarity``：使用此形狀的最低稀有度；``budget``：預算的形狀倍率（2B-2）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    targeting: Targeting
    params: dict[str, ParamDef] = Field(default_factory=dict)
    min_rarity: SkillRarity = "common"
    budget: ShapeBudget = Field(default_factory=ShapeBudget)

    @model_validator(mode="after")
    def _check_budget(self) -> ShapeDef:
        param = self.budget.param
        if param is None:
            return self
        spec = self.params.get(param)
        if spec is None:
            raise ValueError(f"形狀 {self.id}：budget.param {param!r} 不是這個形狀的參數")
        table = self.budget.by_value_permille
        if table is not None:
            missing = [v for v in range(spec.min, spec.max + 1) if v not in table]
            if missing:
                raise ValueError(f"形狀 {self.id}：by_value_permille 缺少參數值 {missing}")
        return self

    def summary(self) -> str:
        return self.name_zh


class ShapeTable(ContentModel):
    """``content/skill_shapes.yaml``。"""

    shapes: tuple[ShapeDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> ShapeTable:
        _unique((s.id for s in self.shapes), "形狀")
        ids = {s.id for s in self.shapes}
        missing = [s for s in REQUIRED_SHAPES if s not in ids]
        if missing:
            raise ValueError(f"缺少引擎實作的形狀：{', '.join(missing)}")
        unknown = sorted(ids - set(REQUIRED_SHAPES))
        if unknown:
            raise ValueError(f"引擎尚未實作的形狀：{', '.join(unknown)}")
        return self

    def by_id(self) -> dict[str, ShapeDef]:
        return {s.id: s for s in self.shapes}

    def summary(self) -> str:
        return f"{len(self.shapes)} 種目標形狀"


# ---------------------------------------------------------------------------
# 效果原語
# ---------------------------------------------------------------------------


class PrimitiveParam(ContentModel):
    """原語的一個參數。

    ``type``：``dice``（``NdM``）、``int``（``min``～``max``）、``status``／``surface``／
    ``object``／``stack``（引用其他資料檔的 ID）、``element``。
    """

    type: Literal["dice", "int", "status", "surface", "object", "element", "stack"]
    required: bool = False
    min: int | None = None
    max: int | None = None
    description_zh: str = ""


class PrimitiveDef(ContentModel):
    """一種效果原語。

    - ``category``：``numeric`` 數值型、``structural`` 結構型、``rule_rewrite`` 改寫規則型。
    - ``min_rarity``：使用此原語的最低稀有度（2A 只存不用，限制在 2B 實作）。
    - ``harmful``：有害（決定 ``affects`` 的預設值：有害 ``enemies``、有益 ``allies``）。
    - ``acts_on``：``unit``（對單位）、``tile``（對格子；預設 ``affects: tiles``）、
      ``caster``（只對施放者；``affects`` 一律為 ``self``）。
    - ``allowed_shapes``：只能搭配這些形狀（``None`` 為不限）。
    - ``forbid_affects``：不可搭配的 ``affects``（淨化不能對敵方使用）。
    - ``budget_basis``／``base_points``：預算點數的算法（``docs/phases/Phase2B計畫.md`` 4.2）：
      ``fixed`` 固定 ``base_points``、``per_distance`` ``base_points × distance``、
      ``per_amount`` ``base_points × amount``（2E-3 的 ``add_stack``）、
      ``consume_stack`` 同技能傷害點數 × 期望消耗層數 × ``per_stack_permille``（2E-3）、
      ``dice_average`` 骰子平均值、``damage`` 法術為骰子平均值而武器為倍率 × 基準武器傷害、
      ``status``／``surface`` 為該狀態或表面的 ``budget_points`` × 持續 ÷ 預設持續。
      ``None`` 表示無法計算預算（驗證器會拒絕）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    category: Literal["numeric", "structural", "rule_rewrite"]
    min_rarity: SkillRarity = "common"
    harmful: bool
    acts_on: Literal["unit", "tile", "caster"] = "unit"
    allowed_shapes: tuple[str, ...] | None = None
    forbid_affects: tuple[Affects, ...] = ()
    params: dict[str, PrimitiveParam] = Field(default_factory=dict)
    budget_basis: (
        Literal[
            "fixed",
            "per_distance",
            "per_amount",
            "dice_average",
            "damage",
            "status",
            "surface",
            "consume_stack",
        ]
        | None
    ) = None
    base_points: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_budget(self) -> PrimitiveDef:
        needs_points = ("fixed", "per_distance", "per_amount")
        if self.budget_basis in needs_points and self.base_points is None:
            raise ValueError(f"原語 {self.id}：budget_basis {self.budget_basis} 必須填 base_points")
        return self

    def summary(self) -> str:
        return self.name_zh


class PrimitiveTable(ContentModel):
    """``content/skill_primitives.yaml``。"""

    primitives: tuple[PrimitiveDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> PrimitiveTable:
        _unique((p.id for p in self.primitives), "原語")
        return self

    def by_id(self) -> dict[str, PrimitiveDef]:
        return {p.id: p for p in self.primitives}

    def summary(self) -> str:
        return f"{len(self.primitives)} 種效果原語"


def default_affects(primitive: PrimitiveDef) -> Affects:
    """省略 ``affects`` 時的預設值：地形類 ``tiles``、施放者專屬 ``self``、有害 ``enemies``、
    有益 ``allies``。"""
    if primitive.acts_on == "tile":
        return "tiles"
    if primitive.acts_on == "caster":
        return "self"
    return "enemies" if primitive.harmful else "allies"


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


class ConditionDef(ContentModel):
    """一種條件（``content/skill_conditions.yaml``）。

    ``harshness``：``common`` 常見／``harsh`` 嚴苛，決定預算的條件倍率（2B-2）。
    ``min_rarity``：使用此條件的最低稀有度。
    ``params`` 沿用原語參數的格式（``int``／``status``／``surface``）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    harshness: Literal["common", "harsh"]
    min_rarity: SkillRarity = "common"
    params: dict[str, PrimitiveParam] = Field(default_factory=dict)

    def summary(self) -> str:
        return self.name_zh


class ConditionTable(ContentModel):
    """``content/skill_conditions.yaml``。"""

    conditions: tuple[ConditionDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> ConditionTable:
        _unique((c.id for c in self.conditions), "條件")
        ids = {c.id for c in self.conditions}
        missing = [c for c in REQUIRED_CONDITIONS if c not in ids]
        if missing:
            raise ValueError(f"缺少引擎實作的條件：{', '.join(missing)}")
        unknown = sorted(ids - set(REQUIRED_CONDITIONS))
        if unknown:
            raise ValueError(f"引擎尚未實作的條件：{', '.join(unknown)}")
        return self

    def by_id(self) -> dict[str, ConditionDef]:
        return {c.id: c for c in self.conditions}

    def summary(self) -> str:
        return f"{len(self.conditions)} 種條件"


class ConditionSpec(ContentModel):
    """技能或效果上的條件：``type`` 加上該條件的參數（範圍見 ``skill_conditions.yaml``）。"""

    type: str = Field(pattern=ID_PATTERN)
    permille: int | None = None
    surface: Surface | None = None
    status: str | None = Field(default=None, pattern=ID_PATTERN)

    def param_values(self) -> dict[str, Any]:
        """已填寫的參數（依名稱排序）。"""
        names = ("permille", "status", "surface")
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}


def condition_text(
    condition: ConditionSpec,
    *,
    status_name: Callable[[str], str] = str,
    surface_name: Callable[[Surface], str] = lambda surface: surface.value,
) -> str:
    """條件的一句話（繁體中文），例如「目標血量低於 40%」。"""
    kind = condition.type
    if kind in ("target_hp_below", "self_hp_below") and condition.permille is not None:
        who = "目標" if kind == "target_hp_below" else "自身"
        return f"{who}血量低於 {condition.permille / 10:g}%"
    if kind == "height_advantage":
        return "居高臨下"
    if kind == "target_on_surface" and condition.surface is not None:
        return f"目標站在「{surface_name(condition.surface)}」表面上"
    if kind == "target_has_status" and condition.status is not None:
        return f"目標帶有狀態「{status_name(condition.status)}」"
    return kind


# ---------------------------------------------------------------------------
# 技能
# ---------------------------------------------------------------------------


class ShapeSpec(ContentModel):
    """技能的目標形狀：``type`` 加上該形狀的參數（範圍見 ``skill_shapes.yaml``）。"""

    type: str = Field(pattern=ID_PATTERN)
    size: int | None = None
    range: int | Literal["weapon"] | None = None
    radius: int | None = None
    jumps: int | None = None
    jump_range: int | None = None

    def param_values(self) -> dict[str, int | str]:
        """已填寫的參數（依名稱排序）。"""
        values: dict[str, int | str] = {}
        for name in ("jump_range", "jumps", "radius", "range", "size"):
            value = getattr(self, name)
            if value is not None:
                values[name] = value
        return dict(sorted(values.items()))


class EffectSpec(ContentModel):
    """技能的一個效果原語（flat 結構；哪些參數合法由原語定義決定）。

    ``condition`` 為效果層級的條件：對每個對象（單位或格子）分別判斷，不成立的對象不受此效果影響。
    """

    type: str = Field(pattern=ID_PATTERN)
    affects: Affects | None = None
    dice: Dice | None = None
    multiplier_permille: int | None = Field(default=None, ge=1, le=_MAX_MULTIPLIER_PERMILLE)
    element: Element | None = None
    distance: int | None = None
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    duration: int | None = Field(default=None, ge=1)
    surface: Surface | None = None
    object: str | None = Field(default=None, pattern=ID_PATTERN)
    amount: int | None = None
    stack: str | None = Field(default=None, pattern=ID_PATTERN)
    per_stack_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    condition: ConditionSpec | None = None

    def param_values(self) -> dict[str, Any]:
        """已填寫的原語參數（不含 ``type``、``affects``、``condition``）。"""
        names = (
            "amount",
            "dice",
            "distance",
            "duration",
            "element",
            "multiplier_permille",
            "object",
            "per_stack_permille",
            "stack",
            "status",
            "surface",
        )
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}


class SkillCost(ContentModel):
    """技能代價（``docs/phases/Phase2A計畫.md`` 3.5）。``hp_percent`` 是最大 HP 的千分比（‰）。"""

    mana: int = Field(default=0, ge=0)
    cooldown: int | None = Field(default=None, ge=1, le=_MAX_COOLDOWN)
    uses_per_battle: int | None = Field(default=None, ge=1)
    hp_percent: int | None = Field(default=None, ge=1, le=_PERMILLE - 1)
    stacks: int | None = Field(default=None, ge=1)
    """施放前至少要有幾層（Phase 2E-3）：對應技能裡 ``owner: self`` 的 ``consume_stack`` 的層數；
    不足時不可施放。需求本身不消耗層數（消耗由 ``consume_stack`` 負責）。"""


class NarrativeDef(ContentModel):
    concept: str = ""
    cast_flavor: str = ""


class Provenance(ContentModel):
    """技能的來源與歸屬（``docs/design/17-未來展望.md`` 17.5）；2A 只存不用。"""

    origin: Origin = "builtin"
    owner_id: str | None = None
    created_by: str | None = None
    parents: tuple[str, ...] = ()
    bound: bool = True
    tradeable: bool = False


class TriggerSpec(ContentModel):
    """被動技能的觸發設定（``docs/phases/Phase2E計畫.md`` 3.2）。

    - ``event``：``content/skill_triggers.yaml`` 的 ID。
    - ``n``：只有 ``every_n_hits`` 使用（2 或 3）。
    - ``target``：效果作用的單位——``self``（持有者）或 ``other``（該時機的另一方）。
    - ``max_per_round``：每輪最多觸發幾次（每輪開始時重設）。
    - ``max_distance``：``target: other`` 時，另一方與持有者的曼哈頓距離上限。
    """

    event: str = Field(pattern=ID_PATTERN)
    n: int | None = None
    target: Literal["self", "other"] = "self"
    max_per_round: int = Field(default=1, ge=1, le=3)
    max_distance: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _check(self) -> TriggerSpec:
        if self.event == "every_n_hits":
            if self.n not in (2, 3):
                raise ValueError(f"every_n_hits 的 n 必須是 2 或 3，收到 {self.n}")
        elif self.n is not None:
            raise ValueError(f"只有 every_n_hits 使用 n，{self.event} 不可填 n")
        if self.max_distance is not None and self.target != "other":
            raise ValueError("max_distance 只能搭配 target: other")
        return self


SKILL_REACTION_EVENTS: tuple[str, ...] = (
    "hit_by_melee",
    "hit_by_attack",
    "ally_hit_adjacent",
    "enemy_leaves_adjacent",
)
"""反應技（``kind: reaction``）的觸發事件（Phase 2E-2 4.1）。"""

INTERCEPT = "intercept"
"""替隊友擋攻擊的原語 ID（只能出現在 ``event: ally_hit_adjacent`` 的反應技）。"""

ADD_STACK = "add_stack"
CONSUME_STACK = "consume_stack"
PLACE_TRAP = "place_trap"
"""Phase 2E-3 的原語 ID：累積層數、消耗層數、放置陷阱。"""


class ReactionSpec(ContentModel):
    """反應技的觸發設定（``docs/phases/Phase2E計畫.md`` 4.1）。

    - ``hit_by_melee``：持有者被近戰攻擊命中、傷害結算之後（仍存活）。
    - ``hit_by_attack``：被任何攻擊命中、傷害結算之後（仍存活）。
    - ``ally_hit_adjacent``：與持有者相鄰（曼哈頓距離 1）的友方被攻擊命中、**傷害結算之前**
      （只給 ``intercept`` 使用）。
    - ``enemy_leaves_adjacent``：敵人離開相鄰格時（同藉機攻擊）。
    """

    event: ReactionEvent


class TrapSpec(ContentModel):
    """陷阱技能的設定（``docs/phases/Phase2E計畫.md`` 5.2；技能必須有 ``place_trap`` 原語）。

    - ``trigger``：``enter`` 為敵人進入陷阱格時觸發、``rounds`` 輪（放置者的回合開始時倒數）後
      未觸發就消失；``delay`` 為 ``rounds`` 輪後（放置者回合開始時）觸發。
    - ``shape``：觸發時以陷阱格為中心的影響範圍（``single``、``cross``、``square3``）。
    - 技能其餘的效果就是陷阱觸發時的效果（自動命中；狀態照常擲抵抗）。
    """

    trigger: Literal["enter", "delay"]
    rounds: int = Field(default=2, ge=1, le=6)
    shape: Literal["single", "cross", "square3"] = "single"


class SkillDef(ContentModel):
    """一個技能（``content/skills/<id>.yaml``）。"""

    id: str = Field(pattern=SKILL_ID_PATTERN)
    schema_version: Literal[1] = 1
    name_zh: str = Field(min_length=1)
    description_zh: str | None = None
    tier: int = Field(ge=1, le=5)
    rank: int = Field(default=1, ge=1, le=5)
    rarity: SkillRarity
    kind: SkillKind = "active"
    skeleton: str
    category: SkillCategory
    weapon_req: WeaponReq
    ap_cost: int | None = None
    scaling_attr: Attribute
    shape: ShapeSpec
    effects: tuple[EffectSpec, ...]
    condition: ConditionSpec | None = None
    trigger: TriggerSpec | None = None
    reaction: ReactionSpec | None = None
    trap: TrapSpec | None = None
    cost: SkillCost = Field(default_factory=SkillCost)
    tags: tuple[str, ...] = ()
    narrative: NarrativeDef = Field(default_factory=NarrativeDef)
    provenance: Provenance = Field(default_factory=Provenance)

    @field_validator("skeleton")
    @classmethod
    def _skeleton(cls, value: str) -> str:
        if value not in SKELETON_IDS:
            raise ValueError(f"未知的骨架 {value!r}（可用：{', '.join(SKELETON_IDS)}）")
        return value

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        bad = [t for t in value if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"標籤必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(value)) != len(value):
            raise ValueError("標籤不可重複")
        return value

    @field_validator("effects")
    @classmethod
    def _effect_count(cls, value: tuple[EffectSpec, ...]) -> tuple[EffectSpec, ...]:
        if not 1 <= len(value) <= _MAX_EFFECTS:
            raise ValueError(f"效果原語必須有 1 到 {_MAX_EFFECTS} 個，收到 {len(value)} 個")
        return value

    @model_validator(mode="after")
    def _check(self) -> SkillDef:
        if self.kind == "active":
            if self.ap_cost is None or not 1 <= self.ap_cost <= _MAX_AP_COST:
                raise ValueError(
                    f"主動技能的 ap_cost 必須是 1 到 {_MAX_AP_COST}，收到 {self.ap_cost}"
                )
        elif self.ap_cost is not None:
            raise ValueError(f"{self.kind} 技能的 ap_cost 必須為 null（不花 AP）")
        if self.kind == "passive" and self.trigger is None:
            raise ValueError("被動技能（kind: passive）必須有 trigger")
        if self.kind != "passive" and self.trigger is not None:
            raise ValueError(f"只有被動技能可以有 trigger，收到 kind: {self.kind}")
        self._check_reaction_and_stance()
        self._check_trap_and_stacks()
        allowed = ("melee", "ranged") if self.category == "weapon" else ("focus", "any")
        if self.weapon_req not in allowed:
            name = "武器技" if self.category == "weapon" else "法術技"
            raise ValueError(
                f"{name}（category: {self.category}）的 weapon_req 只能是 "
                f"{'、'.join(allowed)}，收到 {self.weapon_req}"
            )
        for index, effect in enumerate(self.effects):
            self._check_effect(index, effect)
        return self

    def _check_reaction_and_stance(self) -> None:
        """反應技與姿態的結構（2E-2）：``reaction`` 欄位、形狀、``intercept`` 與 ``teleport``。"""
        if self.kind == "reaction" and self.reaction is None:
            raise ValueError("反應技（kind: reaction）必須有 reaction")
        if self.kind != "reaction" and self.reaction is not None:
            raise ValueError(f"只有反應技可以有 reaction，收到 kind: {self.kind}")
        types = [e.type for e in self.effects]
        if self.kind in ("reaction", "stance") and "teleport" in types:
            raise ValueError("反應技與姿態不能有 teleport（沒有可選的目標格）")
        if self.kind == "stance" and self.shape.type != "self":
            raise ValueError(f"姿態的形狀只能是 self，收到 {self.shape.type}")
        if self.kind == "reaction":
            assert self.reaction is not None
            if self.shape.type not in ("self", "single"):
                raise ValueError(f"反應技的形狀只能是 self 或 single，收到 {self.shape.type}")
            intercepts = INTERCEPT in types
            guarding = self.reaction.event == "ally_hit_adjacent"
            if guarding and not intercepts:
                raise ValueError("ally_hit_adjacent 的反應技必須有 intercept 效果")
            if intercepts and not guarding:
                raise ValueError("intercept 只能用在 event: ally_hit_adjacent 的反應技")
            if guarding and self.shape.type != "self":
                raise ValueError("ally_hit_adjacent 的反應技形狀必須是 self")
        elif INTERCEPT in types:
            raise ValueError("intercept 只能用在反應技")

    def _check_trap_and_stacks(self) -> None:
        """陷阱與層數的結構（2E-3）：``trap`` 與 ``place_trap`` 成對；陷阱技能是形狀
        ``ground_tile`` 的主動技能，其餘效果在觸發時結算，所以不能有 ``teleport``，也不能累積
        或消耗層數（觸發時的施放者是放置時的快照）。"""
        types = [e.type for e in self.effects]
        if (PLACE_TRAP in types) != (self.trap is not None):
            raise ValueError("place_trap 原語與 trap 欄位必須成對出現")
        if self.cost.stacks is not None and CONSUME_STACK not in types:
            raise ValueError("cost.stacks 需要一個 consume_stack 效果")
        if self.trap is None:
            return
        if types.count(PLACE_TRAP) != 1:
            raise ValueError("陷阱技能只能有一個 place_trap")
        if self.kind != "active" or self.shape.type != "ground_tile":
            raise ValueError("陷阱技能必須是形狀 ground_tile 的主動技能")
        banned = [t for t in types if t in ("teleport", ADD_STACK, CONSUME_STACK)]
        if banned:
            raise ValueError(f"陷阱技能不能有 {'、'.join(banned)}（陷阱觸發時才結算其餘效果）")

    def _check_effect(self, index: int, effect: EffectSpec) -> None:
        where = f"effects[{index}]（{effect.type}）"
        if effect.type in ("push", "pull") and (
            effect.distance is None or not 1 <= effect.distance <= _MAX_DISPLACE
        ):
            raise ValueError(
                f"{where}：推擊與拉扯的距離必須是 1 到 {_MAX_DISPLACE} 格，收到 {effect.distance}"
            )
        if effect.type != "damage":
            return
        if self.category == "spell":
            if effect.dice is None or effect.element is None:
                raise ValueError(f"{where}：法術技的傷害必須指定 dice 與 element")
            if effect.multiplier_permille not in (None, _PERMILLE):
                raise ValueError(f"{where}：法術技的傷害不使用 multiplier_permille")
        elif effect.dice is not None:
            raise ValueError(
                f"{where}：武器技的傷害骰來自武器，不可指定 dice（用 multiplier_permille）"
            )

    def summary(self) -> str:
        return f"{self.name_zh}（階級 {self.tier}，{self.skeleton}，AP {self.ap_cost}）"

    @property
    def is_active(self) -> bool:
        return self.kind == "active"

    @property
    def is_actionable(self) -> bool:
        """玩家可以在自己的回合用 ``UseSkill`` 施放：主動技能與姿態（花 AP）。"""
        return self.kind in ("active", "stance")


class SkillTable(ContentModel):
    """全部技能（``content/skills/`` 載入後嵌入 ``Ruleset``），依 ID 排序。"""

    skills: tuple[SkillDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> SkillTable:
        _unique((s.id for s in self.skills), "技能")
        return self

    def by_id(self) -> dict[str, SkillDef]:
        return {s.id: s for s in self.skills}

    def summary(self) -> str:
        return f"{len(self.skills)} 個技能"


# ---------------------------------------------------------------------------
# 跨檔案驗證
# ---------------------------------------------------------------------------


def _int_param_problems(where: str, values: dict[str, int | str], shape: ShapeDef) -> list[str]:
    problems: list[str] = []
    for name, spec in shape.params.items():
        value = values.get(name)
        if value is None:
            if spec.required:
                problems.append(f"{where}：{shape.name_zh}（{shape.id}）缺少參數 {name}")
            continue
        if value == "weapon":
            if not spec.allow_weapon:
                problems.append(f'{where}.{name}：{shape.id} 的 {name} 不接受 "weapon"')
            continue
        assert isinstance(value, int)
        if not spec.min <= value <= spec.max:
            problems.append(
                f"{where}.{name}：{shape.id} 的 {name} 必須在 {spec.min}–{spec.max}，收到 {value}"
            )
    for name in values:
        if name not in shape.params:
            problems.append(f"{where}.{name}：{shape.id} 不接受參數 {name}")
    return problems


def _value_problem(
    where: str, primitive: PrimitiveDef, name: str, value: object, refs: _Refs
) -> str | None:
    """單一原語參數值的問題（範圍或引用不存在）。"""
    spec = primitive.params[name]
    if spec.type == "int":
        assert isinstance(value, int)
        below = spec.min is not None and value < spec.min
        above = spec.max is not None and value > spec.max
        if below or above:
            return (
                f"{where}.{name}：{primitive.id} 的 {name} "
                f"必須在 {spec.min}–{spec.max}，收到 {value}"
            )
    elif spec.type == "status" and value not in refs.status_ids:
        return f"{where}.{name}：未知的狀態 {value!r}"
    elif spec.type == "object" and value not in refs.object_ids:
        return f"{where}.{name}：未知的物件 {value!r}"
    elif spec.type == "stack" and refs.stacks is not None and value not in refs.stacks:
        return f"{where}.{name}：未知的層數 {value!r}"
    elif spec.type == "surface" and value is Surface.NONE:
        return f"{where}.{name}：不能產生 none 表面"
    return None


@dataclass(frozen=True, slots=True)
class _Refs:
    """跨檔案驗證用的引用表。"""

    primitives: dict[str, PrimitiveDef]
    status_ids: set[str]
    object_ids: set[str]
    conditions: dict[str, ConditionDef]
    stacks: dict[str, StackDef] | None = None


def _condition_problems(where: str, condition: ConditionSpec, refs: _Refs) -> list[str]:
    """條件的類型存在、必要參數齊全、參數在範圍內、引用的狀態與表面存在。"""
    definition = refs.conditions.get(condition.type)
    if definition is None:
        known = ", ".join(sorted(refs.conditions))
        return [f"{where}.type：未知的條件 {condition.type!r}（可用：{known}）"]
    problems: list[str] = []
    values = condition.param_values()
    for name, value in values.items():
        spec = definition.params.get(name)
        if spec is None:
            problems.append(f"{where}.{name}：條件 {definition.id} 不接受參數 {name}")
        elif spec.type == "int":
            assert isinstance(value, int)
            if (spec.min is not None and value < spec.min) or (
                spec.max is not None and value > spec.max
            ):
                problems.append(
                    f"{where}.{name}：條件 {definition.id} 的 {name} "
                    f"必須在 {spec.min}–{spec.max}，收到 {value}"
                )
        elif spec.type == "status" and value not in refs.status_ids:
            problems.append(f"{where}.{name}：未知的狀態 {value!r}")
        elif spec.type == "surface" and value is Surface.NONE:
            problems.append(f"{where}.{name}：條件的表面不能是 none")
    for name, spec in definition.params.items():
        if spec.required and name not in values:
            problems.append(f"{where}.{name}：條件 {definition.id} 缺少必要參數 {name}")
    return problems


def _effect_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    where = f"effects[{index}]"
    primitive = refs.primitives.get(effect.type)
    if primitive is None:
        known = ", ".join(sorted(refs.primitives))
        return [f"{where}.type：未知的效果原語 {effect.type!r}（可用：{known}）"]
    problems: list[str] = []
    if effect.condition is not None:
        problems += _condition_problems(f"{where}.condition", effect.condition, refs)
    values = effect.param_values()
    for name, value in values.items():
        if name not in primitive.params:
            problems.append(f"{where}.{name}：效果 {primitive.id} 不接受參數 {name}")
        elif (problem := _value_problem(where, primitive, name, value, refs)) is not None:
            problems.append(problem)
    for name, spec in primitive.params.items():
        if spec.required and name not in values and not _filled_by_category(skill, primitive, name):
            problems.append(f"{where}.{name}：效果 {primitive.id} 缺少必要參數 {name}")
    affects = effect.affects or default_affects(primitive)
    if primitive.acts_on == "caster" and affects != "self":
        problems.append(f"{where}.affects：{primitive.id} 只能對施放者（self），收到 {affects}")
    if primitive.acts_on != "tile" and affects == "tiles":
        problems.append(f"{where}.affects：{primitive.id} 是對單位的效果，不能用 tiles")
    if affects in primitive.forbid_affects:
        problems.append(f"{where}.affects：{primitive.id} 不能搭配 affects: {affects}")
    if primitive.allowed_shapes is not None and skill.shape.type not in primitive.allowed_shapes:
        allowed = "、".join(primitive.allowed_shapes)
        problems.append(f"{where}：{primitive.id} 只能搭配形狀 {allowed}，收到 {skill.shape.type}")
    problems += _stack_effect_problems(where, effect, affects, refs)
    return problems


def _stack_effect_problems(where: str, effect: EffectSpec, affects: str, refs: _Refs) -> list[str]:
    """層數原語的跨檔案檢查：層數的 ``owner`` 決定對象（``self`` 型只能對施放者自己、``target`` 型
    只能對敵方），累積量不超過上限。"""
    if effect.type not in (ADD_STACK, CONSUME_STACK) or refs.stacks is None:
        return []
    stack = refs.stacks.get(effect.stack or "")
    if stack is None:
        return []
    want = "self" if stack.owner == "self" else "enemies"
    problems: list[str] = []
    if affects != want:
        problems.append(
            f"{where}.affects：層數 {stack.id}（owner: {stack.owner}）的{effect.type}"
            f"只能是 affects: {want}，收到 {affects}"
        )
    if effect.type == ADD_STACK and effect.amount is not None and effect.amount > stack.max:
        problems.append(f"{where}.amount：超過層數 {stack.id} 的上限 {stack.max}")
    return problems


def _cost_stack_problems(skill: SkillDef, stacks: dict[str, StackDef]) -> list[str]:
    """``cost.stacks``（施放前至少要有幾層）：對應 ``owner: self`` 的 ``consume_stack``。"""
    need = skill.cost.stacks
    if need is None:
        return []
    owned = [
        stacks[e.stack]
        for e in skill.effects
        if e.type == CONSUME_STACK and e.stack in stacks and stacks[e.stack].owner == "self"
    ]
    if not owned:
        return ["cost.stacks：需要一個 owner: self 的層數的 consume_stack 效果"]
    if need > owned[0].max:
        return [f"cost.stacks：{need} 超過層數 {owned[0].id} 的上限 {owned[0].max}"]
    return []


def _filled_by_category(skill: SkillDef, primitive: PrimitiveDef, name: str) -> bool:
    """法術技的傷害骰必填，武器技的傷害骰來自武器：``dice`` 對武器技的 damage 不是必要參數。"""
    return primitive.id == "damage" and name == "dice" and skill.category == "weapon"


def _trigger_problems(skill: SkillDef, triggers: dict[str, SkillTriggerDef]) -> list[str]:
    """被動技能的觸發設定：時機存在、``target: other`` 只用在有另一方的時機。"""
    spec = skill.trigger
    if spec is None:
        return []
    definition = triggers.get(spec.event)
    if definition is None:
        known = ", ".join(sorted(triggers))
        return [f"trigger.event：未知的觸發時機 {spec.event!r}（可用：{known}）"]
    if spec.target == "other" and not definition.has_other:
        return [
            f"trigger.target：觸發時機 {definition.id}（{definition.name_zh}）沒有另一方，"
            "target 只能是 self"
        ]
    return []


def skill_problems(
    skill: SkillDef,
    shapes: dict[str, ShapeDef],
    primitives: dict[str, PrimitiveDef],
    *,
    status_ids: set[str],
    object_ids: set[str],
    conditions: dict[str, ConditionDef],
    triggers: dict[str, SkillTriggerDef] | None = None,
    stacks: dict[str, StackDef] | None = None,
) -> list[str]:
    """技能引用的形狀、原語、條件、狀態、物件是否存在、參數是否在範圍內（繁體中文，空串列為通過）。

    ``triggers``：觸發時機表（省略時不檢查被動的 ``trigger``）；``stacks``：層數表（省略時不檢查
    層數原語引用的層數）。
    """
    problems: list[str] = []
    shape = shapes.get(skill.shape.type)
    if shape is None:
        known = ", ".join(sorted(shapes))
        problems.append(f"shape.type：未知的形狀 {skill.shape.type!r}（可用：{known}）")
    else:
        problems += _int_param_problems("shape", skill.shape.param_values(), shape)
    refs = _Refs(primitives, status_ids, object_ids, conditions, stacks)
    if stacks is not None:
        problems += _cost_stack_problems(skill, stacks)
    if triggers is not None:
        problems += _trigger_problems(skill, triggers)
    if skill.condition is not None:
        problems += _condition_problems("condition", skill.condition, refs)
    for index, effect in enumerate(skill.effects):
        problems += _effect_problems(skill, index, effect, refs)
    return problems


# ---------------------------------------------------------------------------
# 單位與技能
# ---------------------------------------------------------------------------


def weapon_problem(skill: SkillDef, weapon_class: str) -> str | None:
    """技能的 ``weapon_req`` 與武器分類不相容時的原因。"""
    if skill.weapon_req in ("any", weapon_class):
        return None
    need, have = _REQ_NAMES[skill.weapon_req], _REQ_NAMES[weapon_class]
    return f"技能「{skill.name_zh}」需要{need}，但單位的武器是{have}"


_REQ_NAMES = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器", "any": "任何武器"}


def skill_slot_problems(skills: Iterable[SkillDef], slots: SkillSlots) -> list[str]:
    """裝備的技能數量超過 ``core.yaml`` 的欄位上限時的原因（依 ``kind``）。"""
    counts: Counter[str] = Counter(s.kind for s in skills)
    limits = {
        "active": slots.active,
        "passive": slots.passive,
        "reaction": slots.reaction,
        "stance": slots.stance,
    }
    names = {"active": "主動", "passive": "被動", "reaction": "反應", "stance": "姿態"}
    return [
        f"{names[kind]}技能超過欄位上限：{counts[kind]} 個（上限 {limits[kind]}）"
        for kind in limits
        if counts[kind] > limits[kind]
    ]
