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
from collections.abc import Callable, Collection, Iterable
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
    "BACKLASH_TYPES",
    "BASIC_ACTIONS",
    "CASTER_CONDITIONS",
    "CHANGE_TARGETS",
    "CHARGE_THROUGH",
    "CHEAT_DEATH",
    "CHEAT_DEATH_STATUS",
    "CONSUME_STACK",
    "CONSUME_STATUS",
    "CONSUME_THEN_TYPES",
    "COPY_SKILL",
    "DAMAGE_MULTIPLIER",
    "DASH",
    "DISPEL",
    "EXTRA_REACTION",
    "GAMBLE",
    "GAMBLE_BRANCH_TYPES",
    "GAMBLE_TAG",
    "GRANT_AP",
    "HURL_OBJECT",
    "INTERCEPT",
    "LEAP",
    "LEGACY_REACTION_EVENTS",
    "MAX_LIFESTEAL_PERMILLE",
    "MIN_SKILL_CRIT_RANGE",
    "MODIFIER_CHANGES",
    "ON_HIT_PRIMITIVES",
    "ON_MISS_MIN_RARITY",
    "PAIR_MOVES",
    "PAIR_SHAPES",
    "PIERCE_SHAPES",
    "PLACE_TRAP",
    "RARITY_ORDER",
    "REDIRECT_DAMAGE",
    "REDIRECT_STATUS",
    "REQUIRED_CONDITIONS",
    "REQUIRED_SHAPES",
    "RESET_COOLDOWN",
    "REVEAL",
    "RULE_CHANGE",
    "SCALE_BY_VALUES",
    "SELF_CONDITIONS",
    "SELF_DAMAGE_OF_HIT",
    "SELF_ONLY_CHANGES",
    "SKELETON_IDS",
    "SKILL_ID_PATTERN",
    "SKILL_REACTION_EVENTS",
    "SPLIT_SKELETONS",
    "SUMMON",
    "SWAP",
    "SWAP_ANY",
    "TELEPORT_TARGET",
    "TOPPLE",
    "WEAPON_CLASSES",
    "ZONE",
    "ZONE_CASTER_SHAPES",
    "ZONE_EFFECT_TYPES",
    "ZONE_MOVING_SHAPES",
    "Activation",
    "Affects",
    "BasicAction",
    "ConditionDef",
    "ConditionSpec",
    "ConditionTable",
    "EffectSpec",
    "Mastery",
    "ModifierChange",
    "ModifierSpec",
    "ModifierTarget",
    "NarrativeDef",
    "ParamDef",
    "PrimitiveDef",
    "PrimitiveParam",
    "PrimitiveTable",
    "Provenance",
    "ReactionSpec",
    "ScaleSpec",
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
    "legendary_cores",
    "on_hit_carrier",
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
    "modifier",
    "consume_status",
)
"""``docs/design/06-技能.md`` 6.9 的 12 種骨架，加上 Phase 3C-2 的 ``modifier``（修正規則：改造型與
修正型被動，6.14.1）與 3C-3b 的 ``consume_status``（6.14.2 管道 1）。結構驗證見 ``skillgen``。"""

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
    "object_then_tile",
    "unit_then_tile",
    "unit_pair",
)
"""引擎實作的 13 種形狀（``trpg.engine.skills.shapes``），資料檔必須全部定義。

``object_then_tile``（Phase 3C-5a）：投擲物件，先選射程內的物件、再選落點格。
``unit_then_tile``（Phase 3D-2b）：傳送他人，先選射程內的單位、再選落點格。
``unit_pair``（Phase 3D-2b）：任意兩者互換，選射程內的兩個單位。"""

REQUIRED_CONDITIONS: tuple[str, ...] = (
    "target_hp_below",
    "self_hp_below",
    "height_advantage",
    "target_on_surface",
    "target_has_status",
    "moved_this_turn",
    "adjacent_ally",
    "target_isolated",
    "first_round",
    "cast_tag_this_turn",
)
"""引擎實作的 10 種條件（``trpg.engine.skills.conditions``），資料檔必須全部定義。"""

type Targeting = Literal[
    "self", "unit", "tile", "direction", "none", "object_tile", "unit_tile", "unit_pair"
]
type Affects = Literal["enemies", "allies", "all", "self", "tiles"]
type SkillKind = Literal["active", "reaction", "passive", "stance", "modifier"]
type ReactionEvent = Literal[
    "hit_by_melee",
    "hit_by_attack",
    "ally_hit_adjacent",
    "enemy_leaves_adjacent",
    "hit_by_spell",
    "ally_downed",
    "enemy_enters_adjacent",
    "ally_targeted",
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


SHAPE_TO_VALUES: tuple[str, ...] = ("line", "chain", "cone")
"""修正規則 ``shape_to`` 可以轉成的形狀（Phase 3D-3；組合見 ``skill_shapes.yaml``）。"""


class ShapeConversion(ContentModel):
    """一種允許的形狀轉換（修正規則的 ``shape_to``，Phase 3D-3）：``from_shape`` 的技能轉成 ``to``。

    ``params``：轉換後固定的參數（例：直線 ``size: 3``）；``keep``：從原形狀帶過來的參數名稱
    （例：單體 → 連鎖保留 ``range``，直線 → 錐形保留 ``size``），超出新形狀的參數範圍時截斷到範圍內
    （原形狀的 ``range`` 為 ``"weapon"`` 時取施放者的武器射程）。只有表列的組合能轉換，其餘不轉。
    """

    from_shape: str = Field(pattern=ID_PATTERN)
    to: str = Field(pattern=ID_PATTERN)
    params: dict[str, int] = Field(default_factory=dict)
    keep: tuple[str, ...] = ()


class ShapeTable(ContentModel):
    """``content/skill_shapes.yaml``。"""

    shapes: tuple[ShapeDef, ...] = Field(min_length=1)
    conversions: tuple[ShapeConversion, ...] = ()
    """允許的形狀轉換（Phase 3D-3）。"""

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
        self._check_conversions()
        return self

    def _check_conversions(self) -> None:
        by_id = self.by_id()
        seen: set[tuple[str, str]] = set()
        for conv in self.conversions:
            where = f"conversions {conv.from_shape}→{conv.to}"
            source, target = by_id.get(conv.from_shape), by_id.get(conv.to)
            if source is None or target is None:
                raise ValueError(f"{where}：形狀不存在")
            if conv.to not in SHAPE_TO_VALUES:
                raise ValueError(f"{where}：目標形狀必須是 {'、'.join(SHAPE_TO_VALUES)}")
            if (conv.from_shape, conv.to) in seen:
                raise ValueError(f"{where}：重複的轉換")
            seen.add((conv.from_shape, conv.to))
            if set(conv.params) & set(conv.keep):
                raise ValueError(f"{where}：params 與 keep 不可有相同的參數")
            for name in conv.keep:
                if name not in source.params:
                    raise ValueError(f"{where}：keep {name} 不是 {conv.from_shape} 的參數")
            for name, value in conv.params.items():
                spec = target.params.get(name)
                if spec is None or not spec.min <= value <= spec.max:
                    raise ValueError(f"{where}：params {name}={value} 超出 {conv.to} 的範圍")
            given = {*conv.params, *conv.keep}
            required = {n for n, spec in target.params.items() if spec.required}
            if not required <= given:
                missing_params = "、".join(sorted(required - given))
                raise ValueError(f"{where}：缺少 {conv.to} 的必要參數 {missing_params}")
            if not given <= set(target.params):
                raise ValueError(f"{where}：{conv.to} 沒有這些參數")
        missing_targets = [
            v for v in SHAPE_TO_VALUES if not any(c.to == v for c in self.conversions)
        ]
        if self.conversions and missing_targets:
            raise ValueError(f"conversions 缺少目標形狀：{'、'.join(missing_targets)}")

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
    ``object``／``stack``（引用其他資料檔的 ID）、``element``、``summon``（召喚物範本 ID，
    ``content/units/summons/``，Phase 3D-4a）。
    """

    type: Literal[
        "dice",
        "int",
        "status",
        "surface",
        "object",
        "element",
        "stack",
        "scale",
        "effects",
        "which",
        "tag",
        "bool",
        "resource",
        "on_hit",
        "summon",
        "anchor",
        "zone_when",
        "rule_change",
        "scaling",
        "count",
    ]
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
      ``consume_status`` ``then`` 的點數 × 期望倍率 × 濺射 × 「需要先有狀態」折扣（3C-3b）、
      ``consume_stack`` 同技能傷害點數 × 期望消耗層數 × ``per_stack_permille``（2E-3）、
      ``hurl_object`` 骰子平均 × 「需要附近有物件」折扣（＋擊倒點數，3C-5a）、
      ``charge_through`` （骰子平均 ＋ on_hit 點數）× 預期被撞到的敵人數（3D-2c）、
      ``summon`` 召喚物每輪預估傷害 × 持續輪數 × ``summon_round_value_permille``（3D-4a）、
      ``zone`` 區域效果點數 × 預估觸發次數（格數 × 輪數 × 係數，3D-5）、
      ``gamble`` 成功率 × win 的點數 ＋ 失敗率 × lose 的點數（期望值，3D-7a）、
      ``dice_average`` 骰子平均值、``damage`` 法術為骰子平均值而武器為倍率 × 基準武器傷害、
      ``status``／``surface`` 為該狀態或表面的 ``budget_points`` × 持續 ÷ 預設持續。
      ``None`` 表示無法計算預算（驗證器會拒絕）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    category: Literal["numeric", "structural", "rule_rewrite", "rule_change"]
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
            "consume_status",
            "hurl_object",
            "restore_resource",
            "charge_through",
            "summon",
            "zone",
            "rule_change",
            "gamble",
            "dispel",
            "reveal",
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
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """``cast_tag_this_turn`` 專用（Phase 3D-1）：本回合施放過的技能標籤。"""

    def param_values(self) -> dict[str, Any]:
        """已填寫的參數（依名稱排序）。"""
        names = ("permille", "status", "surface", "tag")
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}


_PLAIN_CONDITION_TEXT = {
    "moved_this_turn": "本回合移動過",
    "adjacent_ally": "身旁有友方",
    "target_isolated": "目標身邊沒有友方",
    "first_round": "第一輪",
}
"""沒有參數的條件的一句話（Phase 3D-1）。"""


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
    if kind == "cast_tag_this_turn" and condition.tag is not None:
        return f"本回合已施放過「{condition.tag}」類技能"
    return _PLAIN_CONDITION_TEXT.get(kind, kind)


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


type ScaleBy = Literal[
    "missing_hp_10pct", "distance", "enemies_adjacent_target", "enemies_adjacent_self"
]
SCALE_BY_VALUES: tuple[str, ...] = (
    "missing_hp_10pct",
    "distance",
    "enemies_adjacent_target",
    "enemies_adjacent_self",
)
"""依情況縮放（Phase 3D-7b，6.17 E、6.18 G）的依據：施放者每少 10% 最大 HP、與目標的距離（格）、
目標相鄰的敵方數、施放者相鄰的敵方數。"""
MAX_LIFESTEAL_PERMILLE = 500
"""吸血（``lifesteal_permille``，Phase 3D-8a）的上限（‰）。"""
MIN_SKILL_CRIT_RANGE = 15
"""技能 ``crit_range`` 的下限（Phase 3D-7b，6.17 B）。"""
ON_MISS_MIN_RARITY = "rare"
"""``cost.on_miss`` 失手反噬的最低稀有度（Phase 3D-7b，3D-7a 驗收決定）。"""


class ScaleSpec(ContentModel):
    """傷害效果的 ``scaling``（Phase 3D-7b）：每一步傷害 ``+per_step_permille`` ‰（無條件捨去），
    總加成不超過 ``cap_permille``（必填；上限見 ``core.yaml`` 的 ``scale_cap_max_permille``）。
    （欄位名不叫 ``scale``：那是 ``consume_status`` 的欄位。）"""

    by: ScaleBy
    per_step_permille: int = Field(ge=1, le=_PERMILLE)
    cap_permille: int = Field(ge=1, le=_MAX_MULTIPLIER_PERMILLE)


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
    collision_dice: Dice | None = None
    """``push``/``pull`` 可省略：撞擊傷害骰，取代核心規則的預設（Phase 3C-3a）。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    duration: int | None = Field(default=None, ge=1)
    surface: Surface | None = None
    object: str | None = Field(default=None, pattern=ID_PATTERN)
    amount: int | None = None
    permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``redirect_damage`` 專用（Phase 3C-4b）：轉移給施放者的傷害千分比。"""
    stack: str | None = Field(default=None, pattern=ID_PATTERN)
    per_stack_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    then: tuple[EffectSpec, ...] | None = None
    """``consume_status`` 專用：移除狀態之後結算的效果（1–2 個；Phase 3C-3b）。"""
    scale: Literal["remaining_rounds", "stacks"] | None = None
    """``consume_status`` 專用：``then`` 的骰數倍率（Phase 3C-3b）。``remaining_rounds``＝被消耗
    狀態的剩餘回合（永久狀態為 1）；``stacks``＝同時消耗目標身上 ``stack`` 的層數
    （``stack`` 必填）。"""
    splash: int | None = Field(default=None, ge=1, le=1)
    """``consume_status`` 專用：``then`` 也作用在被消耗者周圍這麼遠（曼哈頓距離）的敵方單位。"""
    which: Literal["all", "tag"] | None = None
    """``reset_cooldown`` 專用（Phase 3C-4a）：``all`` 全部技能、``tag`` 只有帶 ``tag`` 標籤的
    技能。"""
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """``reset_cooldown`` 的 ``which: tag`` 必填：要重置的技能標籤。"""
    range: int | None = Field(default=None, ge=1)
    """``hurl_object`` 專用（Phase 3C-5a）：可以舉起的物件與施放者的最遠距離（曼哈頓）。"""
    knock_prone: bool | None = None
    """``hurl_object`` 專用（Phase 3C-5a）：命中落點的單位時另外擊倒（對抗判定同
    ``knock_prone`` 原語）。"""
    resource: Literal["mana", "cooldown"] | None = None
    """``restore_resource`` 專用（Phase 3D-1）：``mana`` 回復法力 ``amount``；``cooldown`` 讓目標
    所有技能（不含花源力的技能與施放中的這個技能）冷卻 −``amount``。"""
    on_hit: Literal["knock_prone", "push_aside"] | None = None
    """``charge_through`` 專用（Phase 3D-2c）：被撞到的敵人除了傷害之外的效果——``knock_prone``
    擊倒（對抗判定）或 ``push_aside`` 推到路徑旁一格。"""
    unit: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3D-4a）：召喚物範本 ID（``content/units/summons/``）。"""
    count: int | Literal["all"] | None = Field(default=None)
    """``summon`` 專用（Phase 3D-4a）：一次召喚的數量（目前只能是 1）。``dispel`` 專用
    （Phase 3D-8a）：驅散的增益個數（1）或 ``all``（全部）。"""
    anchor: Literal["tile", "caster", "moving"] | None = None
    """``zone`` 專用（Phase 3D-5）：``tile`` 固定在施放時的格子、``caster`` 跟隨施放者、``moving``
    每次環境回合沿施放方向前進 ``speed`` 格。"""
    when: Literal["enter", "turn_start", "both"] | None = None
    """``zone`` 專用（Phase 3D-5）：區域效果結算的時機——單位 **進入** 區域時、**回合開始時** 站在
    區域內時，或兩者。（設計文件寫作 ``on``；YAML 1.1 會把 ``on`` 讀成布林值，所以欄位名用
    ``when``。）"""
    speed: int | None = Field(default=None, ge=1)
    """``zone`` 的 ``anchor: moving`` 專用（Phase 3D-5）：每次環境回合前進的格數。"""
    rule: str | None = Field(default=None, pattern=ID_PATTERN)
    """``rule_change`` 專用（Phase 3D-6）：``content/rule_changes.yaml`` 的規則改變 ID。"""
    chance_permille: int | None = Field(default=None, ge=1, le=_PERMILLE - 1)
    """``gamble`` 專用（Phase 3D-7a）：成功（結算 ``win``）的機率（‰）；d1000 不超過它就成功。"""
    win: tuple[EffectSpec, ...] | None = None
    lose: tuple[EffectSpec, ...] | None = None
    """``gamble`` 專用：成功／失敗時結算的效果（各 0–2 個，至少一邊有效果；類型見
    :data:`GAMBLE_BRANCH_TYPES`）；對象 ``self`` 即對施放者（失敗的反噬）。"""
    damage_multiplier_permille: int | None = Field(
        default=None, ge=100, le=_MAX_MULTIPLIER_PERMILLE
    )
    """``damage_multiplier`` 專用：本次施放的傷害效果 × 這個倍率（‰；2000 ＝ 加倍）。"""
    self_damage_permille_of_hit: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``self_damage_of_hit`` 專用：施放者受到「本次施放對敵人造成的傷害」的 n‰（反噬，不致命）。"""
    explode: bool | None = None
    """``damage`` 專用（Phase 3D-7b，6.17 B）：爆骰——擲到最大值再加擲一次，每顆骰最多再擲
    ``core.explode_max`` 次。只有主技能效果（不含賭注分支與 ``then``）可以用。"""
    scaling: ScaleSpec | None = None
    """``damage`` 專用（Phase 3D-7b，6.17 E、6.18 G）：依情況縮放傷害。"""
    lifesteal_permille: int | None = Field(default=None, ge=1, le=MAX_LIFESTEAL_PERMILLE)
    """``damage`` 專用（Phase 3D-8a，6.18 A）：吸血——施放者回復「這個效果實際造成的傷害（扣掉護盾
    吸收）」的 n‰（無條件捨去，不超過最大 HP）。只有技能自己的傷害效果可以用。"""
    split_heal: bool | None = None
    """``damage`` 專用（Phase 3D-8a，6.18 B）：聖光雙效——必須搭配 ``affects: all``；敵方依一般命中
    判定受到傷害、友方（含施放者）不擲命中而改為治療同樣的骰值（骰一次）。只能用在 ``aura``、
    ``area`` 骨架的法術技。"""
    effects: tuple[EffectSpec, ...] | None = None
    """``zone`` 專用（Phase 3D-5）：區域結算的效果（1–2 個，只能用 :data:`ZONE_EFFECT_TYPES`，
    不可自帶 ``affects``／``condition``；對象由區域的 ``affects`` 決定）。"""
    condition: ConditionSpec | None = None

    def param_values(self) -> dict[str, Any]:
        """已填寫的原語參數（不含 ``type``、``affects``、``condition``）。"""
        names = (
            "amount",
            "anchor",
            "chance_permille",
            "collision_dice",
            "count",
            "damage_multiplier_permille",
            "dice",
            "distance",
            "duration",
            "effects",
            "element",
            "explode",
            "knock_prone",
            "lifesteal_permille",
            "lose",
            "multiplier_permille",
            "object",
            "on_hit",
            "per_stack_permille",
            "permille",
            "range",
            "resource",
            "rule",
            "scale",
            "scaling",
            "self_damage_permille_of_hit",
            "speed",
            "split_heal",
            "splash",
            "stack",
            "status",
            "surface",
            "tag",
            "then",
            "unit",
            "when",
            "which",
            "win",
        )
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}


class SelfStatusCost(ContentModel):
    """自身狀態代價（Phase 2H-1）：施放結算完之後，施放者自己獲得 ``status``（不擲抵抗）。

    狀態在帶有者回合結束時倒數，所以施放當回合結束就會 −1：``duration`` 限制為 2–3
    （1 等於沒有效果），預算折抵用的「有效回合」＝ ``duration − 1``。允許的狀態與折抵見
    ``content/skill_budget.yaml`` 的 ``allowance.self_status``。
    """

    status: str = Field(pattern=ID_PATTERN)
    duration: int = Field(ge=2, le=3)


class SkillCost(ContentModel):
    """技能代價（``docs/phases/Phase2A計畫.md`` 3.5）。``hp_percent`` 是最大 HP 的千分比（‰）。"""

    mana: int = Field(default=0, ge=0)
    cooldown: int | None = Field(default=None, ge=1, le=_MAX_COOLDOWN)
    uses_per_battle: int | None = Field(default=None, ge=1)
    hp_percent: int | None = Field(default=None, ge=1, le=_PERMILLE - 1)
    stacks: int | None = Field(default=None, ge=1)
    """施放前至少要有幾層（Phase 2E-3）：對應技能裡 ``owner: self`` 的 ``consume_stack`` 的層數；
    不足時不可施放。需求本身不消耗層數（消耗由 ``consume_stack`` 負責）。"""
    self_status: SelfStatusCost | None = None
    """施放後施放者自己獲得的狀態（Phase 2H-1）；只有主動技能可以使用。"""
    source: int | None = Field(default=None, ge=1, le=2)
    """花費的源力（Phase 3C-4a，1 或 2）：只有傳說技能可以、而且必須有；源力不足時不能施放。"""
    on_miss: tuple[EffectSpec, ...] = ()
    """失手反噬（Phase 3D-7a，6.17 C）：攻擊沒命中（含自然 1）時對施放者結算的效果（至多 2 個，
    類型見 :data:`BACKLASH_TYPES`，對象只能是施放者自己）；命中則不結算。"""


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


ON_CAST_TAG = "on_cast_tag"
ON_STATUS_APPLIED = "on_status_applied"
ON_COLLISION = "on_collision"
ON_ENTER_SURFACE = "on_enter_surface"
"""帶參數或需要特別處理的觸發時機 ID（Phase 3C-3a；其餘見 ``content/skill_triggers.yaml``）。"""


class TriggerSpec(ContentModel):
    """被動技能的觸發設定（``docs/phases/Phase2E計畫.md`` 3.2）。

    - ``event``：``content/skill_triggers.yaml`` 的 ID。
    - ``n``：只有 ``every_n_hits`` 使用（2 或 3）。
    - ``target``：效果作用的單位——``self``（持有者）或 ``other``（該時機的另一方）。
    - ``max_per_round``：每輪最多觸發幾次（每輪開始時重設）。
    - ``max_distance``：``target: other`` 時，另一方與持有者的曼哈頓距離上限。
    - ``tag``：只有 ``on_cast_tag`` 使用且必填（施放帶這個標籤的技能；Phase 3C-3a）。
    - ``status``：只有 ``on_status_applied`` 使用，可省略（省略＝任何狀態）。
    - ``surface``：只有 ``on_enter_surface`` 使用，可省略（省略＝任何表面；Phase 3C-3b）。
    """

    event: str = Field(pattern=ID_PATTERN)
    n: int | None = None
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    surface: Surface | None = None
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
        if self.event == ON_CAST_TAG:
            if self.tag is None:
                raise ValueError("on_cast_tag 必須填 tag")
        elif self.tag is not None:
            raise ValueError(f"只有 on_cast_tag 使用 tag，{self.event} 不可填 tag")
        if self.status is not None and self.event != ON_STATUS_APPLIED:
            raise ValueError(f"只有 on_status_applied 使用 status，{self.event} 不可填 status")
        if self.surface is not None and self.event != ON_ENTER_SURFACE:
            raise ValueError(f"只有 on_enter_surface 使用 surface，{self.event} 不可填 surface")
        if self.surface is Surface.NONE:
            raise ValueError("trigger.surface 不可為 none")
        return self


SKILL_REACTION_EVENTS: tuple[str, ...] = (
    "hit_by_melee",
    "hit_by_attack",
    "ally_hit_adjacent",
    "enemy_leaves_adjacent",
    "hit_by_spell",
    "ally_downed",
    "enemy_enters_adjacent",
    "ally_targeted",
)
"""反應技（``kind: reaction``）的觸發事件（Phase 2E-2 4.1；後四個是 Phase 3D-3 新增）。"""

LEGACY_REACTION_EVENTS: tuple[str, ...] = SKILL_REACTION_EVENTS[:4]
"""Phase 2E-2 的四個觸發事件。隨機組合器只從這些抽（3D-3 的新事件只給手寫技能，組合器的亂數
串流與既有種子的結果因此不變）。"""

INTERCEPT = "intercept"
"""替隊友擋攻擊的原語 ID（只能出現在 ``event: ally_hit_adjacent`` 的反應技）。"""

ADD_STACK = "add_stack"
CONSUME_STACK = "consume_stack"
CONSUME_STATUS = "consume_status"
CONSUME_THEN_TYPES = ("damage", "heal", "shield", "apply_status")
"""``consume_status`` 的 ``then`` 可用的原語（Phase 3C-3b）。"""
PLACE_TRAP = "place_trap"
"""Phase 2E-3 的原語 ID：累積層數、消耗層數、放置陷阱。"""
GRANT_AP = "grant_ap"
RESET_COOLDOWN = "reset_cooldown"
CHEAT_DEATH = "cheat_death"
"""Phase 3C-4a 的改寫規則型原語 ID（6.3；規則見 ``content/skill_primitives.yaml``）。"""
CHEAT_DEATH_STATUS = "undying"
"""``cheat_death`` 施加的狀態（``statuses.yaml``，``prevents_death``）。"""
REDIRECT_DAMAGE = "redirect_damage"
COPY_SKILL = "copy_skill"
EXTRA_REACTION = "extra_reaction"
"""Phase 3C-4b 的改寫規則型原語 ID。"""
RESTORE_RESOURCE = "restore_resource"
STEAL_BUFF = "steal_buff"
"""Phase 3D-1 的資源互動原語 ID（6.16 H）。"""
DISPEL = "dispel"
REVEAL = "reveal"
"""Phase 3D-8a 的原語 ID（6.18 J、I）：驅散敵方增益、揭露隱蔽與陷阱。"""
SPLIT_SKELETONS: tuple[str, ...] = ("aura", "area")
"""``split_heal``（聖光雙效）可以使用的骨架。"""
DASH = "dash"
LEAP = "leap"
SWAP = "swap"
"""Phase 3D-2 的自身位移原語 ID（6.16 A）。"""
TELEPORT_TARGET = "teleport_target"
SWAP_ANY = "swap_any"
"""Phase 3D-2b 的位移他人原語 ID（6.19）：傳送他人（形狀 ``unit_then_tile``）、任意兩者互換
（形狀 ``unit_pair``）。"""
PAIR_MOVES: tuple[str, ...] = (TELEPORT_TARGET, SWAP_ANY)
PAIR_SHAPES: dict[str, str] = {TELEPORT_TARGET: "unit_then_tile", SWAP_ANY: "unit_pair"}
CHARGE_THROUGH = "charge_through"
"""Phase 3D-2c 的直線衝撞原語 ID（6.22）：形狀 ``ground_tile`` 選終點格，沿直線衝過去。"""
SUMMON = "summon"
"""Phase 3D-4a 的召喚原語 ID（6.16 B）：在 ``ground_tile`` 選的空格召喚 ``unit`` 範本。"""
RULE_CHANGE = "rule_change"
"""規則改變（Phase 3D-6）：引用 ``content/rule_changes.yaml`` 的一條規則，以 ``activation``
啟動。"""
ZONE = "zone"
"""Phase 3D-5 的持續區域原語 ID（6.16 G）：在格子上建立持續 ``duration`` 輪的區域。"""
ZONE_EFFECT_TYPES: tuple[str, ...] = ("damage", "heal", "shield", "apply_status")
"""``zone`` 的 ``effects`` 可用的原語（Phase 3D-5；與 ``consume_status`` 的 ``then`` 相同）。"""
ZONE_MOVING_SHAPES: tuple[str, ...] = ("line", "cone")
"""``anchor: moving`` 可用的形狀（選方向的形狀；區域沿施放方向前進）。"""
ZONE_CASTER_SHAPES: tuple[str, ...] = ("self", "ring", "allies_in_radius")
"""``anchor: caster`` 可用的形狀（以施放者為中心、不需要選取的形狀；跟著施放者重新展開）。"""
_ZONE_ONLY_FIELDS = ("anchor", "when", "speed", "effects")
GAMBLE = "gamble"
GAMBLE_TAG = "gamble"
"""帶賭博機制的技能自動加上的標籤。"""
DAMAGE_MULTIPLIER = "damage_multiplier"
SELF_DAMAGE_OF_HIT = "self_damage_of_hit"
"""Phase 3D-7a 的賭博型原語（6.17 A）：``gamble``（賭注：成敗兩個分支）；``damage_multiplier``
（本次傷害 × 倍率）與 ``self_damage_of_hit``（施放者受本次傷害的 n‰）只能出現在賭注的分支裡，
不是 ``skill_primitives.yaml`` 的原語。"""
GAMBLE_BRANCH_TYPES: tuple[str, ...] = (
    "damage",
    "heal",
    "shield",
    "apply_status",
    DAMAGE_MULTIPLIER,
    SELF_DAMAGE_OF_HIT,
)
"""賭注分支（``win``／``lose``）可用的效果類型。"""
BACKLASH_TYPES: tuple[str, ...] = ("damage", "apply_status")
"""失手反噬（``cost.on_miss``）可用的效果類型。"""
_MAX_BRANCH_EFFECTS = 2
_GAMBLE_ONLY_FIELDS = ("chance_permille", "win", "lose")
_MAX_ZONE_EFFECTS = 2
SELF_MOVES: tuple[str, ...] = (DASH, LEAP, SWAP, CHARGE_THROUGH, "teleport")
"""改變施放者位置的原語；一個技能最多一個。"""
_MAX_COOLDOWN_RESTORE = 2
"""``restore_resource`` 的 ``resource: cooldown`` 一次最多縮短的回合（Phase 3D-1）。"""
HURL_OBJECT = "hurl_object"
TOPPLE = "topple"
"""Phase 3C-5a 的物件原語 ID（6.15）：投擲物件、推倒。"""
PIERCE_SHAPES: tuple[str, ...] = ("single", "line")
"""可以穿透（``pierce``，Phase 3C-5b）的形狀：遠程單體與直線。"""
REDIRECT_STATUS = "soul_link"
"""``redirect_damage`` 施加的狀態（``statuses.yaml``，``redirects_damage``）：
``StatusInstance.amount`` 存轉移的千分比、``source_id`` 是承受轉移的施放者。"""


class ReactionSpec(ContentModel):
    """反應技的觸發設定（``docs/phases/Phase2E計畫.md`` 4.1）。

    - ``hit_by_melee``：持有者被近戰攻擊命中、傷害結算之後（仍存活）。
    - ``hit_by_attack``：被任何攻擊命中、傷害結算之後（仍存活）。
    - ``ally_hit_adjacent``：與持有者相鄰（曼哈頓距離 1）的友方被攻擊命中、**傷害結算之前**
      （只給 ``intercept`` 使用）。
    - ``enemy_leaves_adjacent``：敵人離開相鄰格時（同藉機攻擊）。
    - ``hit_by_spell``（3D-3）：被法術技（``category: spell``）命中、**傷害之前**；另一方是施放者。
    - ``ally_downed``（3D-3）：持有者視野內的友方倒下之後；另一方是倒下的友方（已倒下，所以形狀
      必須是 ``self``）。
    - ``enemy_enters_adjacent``（3D-3）：敵方單位 **主動移動**（步行、衝鋒、直線衝撞）進入持有者
      相鄰格之後（強制位移、傳送、跳躍、互換不算；本來就相鄰的移動不算「進入」）。
    - ``ally_targeted``（3D-3）：與持有者相鄰的友方被敵方單體技能或普攻選為目標、**命中判定之前**；
      另一方是攻擊者。
    """

    event: ReactionEvent


class TrapSpec(ContentModel):
    """陷阱技能的設定（``docs/phases/Phase2E計畫.md`` 5.2；技能必須有 ``place_trap`` 原語）。

    - ``trigger``：``enter`` 為敵人進入陷阱格時觸發、``rounds`` 輪（放置者的回合開始時倒數）後
      未觸發就消失；``delay`` 為 ``rounds`` 輪後（放置者回合開始時）觸發。
    - ``shape``：觸發時以陷阱格為中心的影響範圍；形狀 ID（``single``、``cross``、``square3``）須
      存在於 ``content/skill_shapes.yaml``（跨檔案檢查，見 :func:`skill_problems`；Phase 2F-1
      3.2——取代原本的 ``Literal``，讓引擎的形狀展開能涵蓋資料檔新增的形狀而不必改程式）。
    - 技能其餘的效果就是陷阱觸發時的效果（自動命中；狀態照常擲抵抗）。
    """

    trigger: Literal["enter", "delay"]
    rounds: int = Field(default=2, ge=1, le=6)
    shape: str = Field(default="single", pattern=ID_PATTERN)


# ---------------------------------------------------------------------------
# 修正規則（Phase 3C-2：修正型被動與改造型技能，``docs/design/06-技能.md`` 6.14.1、6.14.3）
# ---------------------------------------------------------------------------

type BasicAction = Literal["attack", "shove", "trip", "interact"]
"""可以被修正的基本動作：普攻（含藉機攻擊）、推擊、絆倒、互動（推或撥開物件）。"""

BASIC_ACTIONS: tuple[str, ...] = ("attack", "shove", "trip", "interact")

MODIFIER_CHANGES: tuple[str, ...] = (
    "damage_permille",
    "hit_bonus",
    "cooldown_delta",
    "push_distance_delta",
    "ap_delta",
    "range_delta",
    "add_element",
    "add_tags",
    "on_hit_effects",
    "grant_pierce",
    "area_delta",
    "shape_to",
    "allow_self_target",
)
"""``change`` 的種類（每條規則恰好一種）。"""

SHAPE_CHANGES: frozenset[str] = frozenset({"area_delta", "shape_to", "allow_self_target"})
"""讓技能變形的修正（Phase 3D-3）：選目標之前就決定，只套用在主動技能；引擎以
:func:`trpg.engine.modifiers.shaped_skill` 產生變形後的技能。"""

_ATTACK_TARGETS = frozenset({"attack", "all_attacks", "all_skills", "skill_tags"})
_SKILL_TARGETS = frozenset({"all_skills", "skill_tags"})
CHANGE_TARGETS: dict[str, frozenset[str]] = {
    "damage_permille": _ATTACK_TARGETS,
    "hit_bonus": _ATTACK_TARGETS,
    "cooldown_delta": _SKILL_TARGETS,
    "push_distance_delta": frozenset({"shove", "all_skills", "skill_tags"}),
    "ap_delta": frozenset({*BASIC_ACTIONS, "all_attacks", "all_skills", "skill_tags"}),
    "range_delta": _ATTACK_TARGETS,
    "add_element": _ATTACK_TARGETS,
    "add_tags": _SKILL_TARGETS,
    "on_hit_effects": _ATTACK_TARGETS,
    "grant_pierce": _SKILL_TARGETS,
    "area_delta": frozenset({"all_attacks", "all_skills", "skill_tags"}),
    "shape_to": frozenset({"all_attacks", "all_skills", "skill_tags"}),
    "allow_self_target": _SKILL_TARGETS,
}
"""每種 ``change`` 可以套用的對象（``applies_to`` 的每一項都必須在內）：推擊、絆倒、互動沒有傷害與
命中骰，基本動作沒有冷卻與標籤。"""

SELF_ONLY_CHANGES: frozenset[str] = frozenset(
    {"ap_delta", "range_delta", "add_element", "add_tags", "grant_pierce", *SHAPE_CHANGES}
)
"""在選目標之前就要決定的修正：條件只能看持有者自己（``self_hp_below``）或省略。"""

SELF_CONDITIONS: frozenset[str] = frozenset({"self_hp_below"})
CASTER_CONDITIONS: frozenset[str] = frozenset(
    {"self_hp_below", "moved_this_turn", "adjacent_ally", "first_round", "cast_tag_this_turn"}
)
"""只看施放者的條件（Phase 3D-1）：技能層級的判斷不需要影響範圍內有對象。選目標之前就要決定的
修正規則改變（:data:`SELF_ONLY_CHANGES`）仍只允許 :data:`SELF_CONDITIONS`（``self_hp_below``）。"""

ON_HIT_PRIMITIVES: tuple[str, ...] = (
    "damage",
    "apply_status",
    "push",
    "pull",
    "knock_prone",
    "create_surface",
)
"""``on_hit_effects`` 可用的原語（作用在被命中的目標或其所在格，自動命中）。"""

_MAX_MODIFIERS = 2
_MAX_CONSUME_THEN = 2
_MAX_ON_HIT_EFFECTS = 2


class ModifierTarget(ContentModel):
    """修正規則的套用對象（``applies_to``；至少一項，多項為「或」）。

    - ``actions``：基本動作（``attack`` 普攻、``shove`` 推擊、``trip`` 絆倒、``interact`` 互動）。
    - ``skill_tags``：帶這些標籤（含其他修正規則用 ``add_tags`` 加上的）的技能。
    - ``all_attacks``：你的所有攻擊——普攻與「有對敵方傷害效果」的技能（修正型被動）。
    - ``all_skills``：你施放的所有技能（主動、姿態與反應技）。

    被動觸發與陷阱觸發的效果不是「你的動作」，不受修正規則影響。
    """

    actions: tuple[BasicAction, ...] = ()
    skill_tags: tuple[str, ...] = ()
    all_attacks: bool = False
    all_skills: bool = False

    @model_validator(mode="after")
    def _check(self) -> ModifierTarget:
        if not (self.actions or self.skill_tags or self.all_attacks or self.all_skills):
            raise ValueError(
                "applies_to 至少要有一項（actions、skill_tags、all_attacks、all_skills）"
            )
        if len(set(self.actions)) != len(self.actions):
            raise ValueError("applies_to.actions 不可重複")
        bad = [t for t in self.skill_tags if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"applies_to.skill_tags 必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(self.skill_tags)) != len(self.skill_tags):
            raise ValueError("applies_to.skill_tags 不可重複")
        return self

    def keys(self) -> frozenset[str]:
        """對象的代碼集合：基本動作、``all_attacks``、``all_skills``、``skill_tags``。"""
        keys: set[str] = set(self.actions)
        if self.all_attacks:
            keys.add("all_attacks")
        if self.all_skills:
            keys.add("all_skills")
        if self.skill_tags:
            keys.add("skill_tags")
        return frozenset(keys)


class ModifierChange(ContentModel):
    """修正規則的改變（恰好一種，正交；``docs/phases/Phase3C計畫.md`` 4.1）。

    - ``damage_permille``：傷害 ±‰（−500～＋1000，不可為 0；多條規則加總後套用一次）。
    - ``hit_bonus``：命中 ±（−3～＋3）。
    - ``cooldown_delta``：命中後該技能剩餘冷卻 −1 或 −2（下限 0）。
    - ``push_distance_delta``：推擊與拉扯距離 +1 或 +2（結果截斷在 ``max_displace_distance``）。
    - ``ap_delta``：AP 成本 ±1（結果至少 1）。
    - ``range_delta``：射程 −1～＋2（不可為 0；結果至少 1；只改有射程的形狀與普攻）。
    - ``add_element``：傷害獲得元素（只改物理傷害，已有元素的不覆寫）。
    - ``add_tags``：技能獲得標籤（1～3 個）。
    - ``on_hit_effects``：命中後附加效果（1～2 個，原語見 :data:`ON_HIT_PRIMITIVES`）。
    - ``grant_pierce``：技能獲得穿透（只能是 ``true``；只對遠程單體與直線的技能有效，
      Phase 3C-5b）。
    - ``area_delta``（3D-3）：範圍型形狀大小 +1（直線與錐形的 ``size``、環形與範圍光環的
      ``radius``；不超過 ``skill_shapes.yaml`` 的最大值，``cross``、``square3`` 的大小固定）。
    - ``shape_to``（3D-3）：形狀轉換，只有 ``skill_shapes.yaml`` 的 ``conversions`` 表列的組合：
      ``single → line``、``single → chain``、``line → cone``；技能的效果原語必須允許新形狀，
      否則不轉。
    - ``allow_self_target``（3D-3，只能是 ``true``）：治療、護盾、增益類技能（有對友方生效的效果）
      的影響範圍也包含施放者自己（單體形狀本來就能選自己；直線、錐形等形狀的範圍不含施放者，
      這條規則把他算進去）。
    """

    damage_permille: int | None = Field(default=None, ge=-500, le=1000)
    hit_bonus: int | None = Field(default=None, ge=-3, le=3)
    cooldown_delta: int | None = Field(default=None, ge=-2, le=-1)
    push_distance_delta: int | None = Field(default=None, ge=1, le=2)
    ap_delta: int | None = Field(default=None, ge=-1, le=1)
    range_delta: int | None = Field(default=None, ge=-1, le=2)
    add_element: Element | None = None
    add_tags: tuple[str, ...] | None = None
    on_hit_effects: tuple[EffectSpec, ...] | None = None
    grant_pierce: bool | None = None
    area_delta: int | None = Field(default=None, ge=1, le=1)
    shape_to: Literal["line", "chain", "cone"] | None = None
    allow_self_target: bool | None = None

    @model_validator(mode="after")
    def _check(self) -> ModifierChange:
        given = [name for name in MODIFIER_CHANGES if getattr(self, name) is not None]
        if len(given) != 1:
            got = "、".join(given) if given else "沒有"
            raise ValueError(f"change 必須恰好一種（{'、'.join(MODIFIER_CHANGES)}），收到 {got}")
        kind = given[0]
        value = getattr(self, kind)
        if kind in ("damage_permille", "hit_bonus", "ap_delta", "range_delta") and value == 0:
            raise ValueError(f"change.{kind} 不可為 0")
        if kind == "add_element" and value is Element.PHYSICAL:
            raise ValueError("change.add_element 不可是物理（physical）")
        if kind in ("grant_pierce", "allow_self_target") and value is not True:
            raise ValueError(f"change.{kind} 只能是 true")
        if kind == "add_tags":
            self._check_tags(value)
        if kind == "on_hit_effects":
            self._check_on_hit(value)
        return self

    @staticmethod
    def _check_tags(tags: tuple[str, ...]) -> None:
        if not 1 <= len(tags) <= 3:  # noqa: PLR2004 - 規格的 1～3 個
            raise ValueError(f"change.add_tags 必須有 1 到 3 個標籤，收到 {len(tags)} 個")
        bad = [t for t in tags if re.match(ID_PATTERN, t) is None]
        if bad:
            raise ValueError(f"change.add_tags 必須是小寫 snake_case：{', '.join(bad)}")
        if len(set(tags)) != len(tags):
            raise ValueError("change.add_tags 不可重複")

    @staticmethod
    def _check_on_hit(effects: tuple[EffectSpec, ...]) -> None:
        if not 1 <= len(effects) <= _MAX_ON_HIT_EFFECTS:
            raise ValueError(
                f"change.on_hit_effects 必須有 1 到 {_MAX_ON_HIT_EFFECTS} 個效果，"
                f"收到 {len(effects)} 個"
            )
        for index, effect in enumerate(effects):
            if effect.type not in ON_HIT_PRIMITIVES:
                raise ValueError(
                    f"change.on_hit_effects[{index}]：{effect.type} 不能當命中後效果"
                    f"（可用：{'、'.join(ON_HIT_PRIMITIVES)}）"
                )
            if effect.type in ("push", "pull") and (
                effect.distance is None or not 1 <= effect.distance <= _MAX_DISPLACE
            ):
                raise ValueError(
                    f"change.on_hit_effects[{index}]：推擊與拉扯的距離必須是 1 到 "
                    f"{_MAX_DISPLACE} 格，收到 {effect.distance}"
                )

    @property
    def kind(self) -> str:
        """這條改變的種類（:data:`MODIFIER_CHANGES` 之一）。"""
        return next(name for name in MODIFIER_CHANGES if getattr(self, name) is not None)


class ModifierSpec(ContentModel):
    """一條修正規則：套用對象、條件（可省略，沿用 ``skill_conditions.yaml``）與改變。

    條件的判斷對象：``self_hp_below`` 看持有者；其他條件看這次動作的目標（傷害、命中、推擊距離
    看該目標；冷卻看「被命中的敵人中至少一個」；命中後效果看被命中的目標）。:data:`SELF_ONLY_CHANGES`
    在選目標之前就要決定，所以條件只能是 ``self_hp_below``。
    """

    applies_to: ModifierTarget
    condition: ConditionSpec | None = None
    change: ModifierChange

    @model_validator(mode="after")
    def _check(self) -> ModifierSpec:
        kind = self.change.kind
        allowed = CHANGE_TARGETS[kind]
        extra = sorted(self.applies_to.keys() - allowed)
        if extra:
            raise ValueError(
                f"change.{kind} 不能套用在 {'、'.join(extra)}（可用：{'、'.join(sorted(allowed))}）"
            )
        condition = self.condition
        if (
            kind in SELF_ONLY_CHANGES
            and condition is not None
            and condition.type not in SELF_CONDITIONS
        ):
            raise ValueError(
                f"change.{kind} 在選目標之前就決定，條件只能是 self_hp_below，收到 {condition.type}"
            )
        return self


type Activation = Literal["timed", "battle"]
"""常駐類傳說的啟動方式（Phase 3D-6，6.14.4）：``timed`` 持續 ``legendary_timed_rounds`` 輪、
``battle`` 本場剩餘時間有效（預算較低）。"""

type Mastery = Literal["range", "duration"]
"""專精加成的種類（Phase 2H-2）。"""


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
    secondary_scaling_attr: Attribute | None = None
    """第二縮放屬性（Phase 2H-2）：與 ``scaling_attr`` 各占 50%（取平均，無條件捨去）。
    最低稀有度由 ``core.yaml`` 的 ``dual_scaling_min_rarity`` 決定（跨檔案檢查）。"""
    mastery: Mastery | None = None
    """專精加成（Phase 2H-2）：施放者的 ``scaling_attr`` 基礎屬性是自己所有屬性中最高（含並列）
    時生效——``range`` 施放距離 +1、``duration`` 此技能施加的狀態持續 +1。雙屬性技能不可設定。"""
    shape: ShapeSpec
    effects: tuple[EffectSpec, ...]
    condition: ConditionSpec | None = None
    trigger: TriggerSpec | None = None
    reaction: ReactionSpec | None = None
    trap: TrapSpec | None = None
    cost: SkillCost = Field(default_factory=SkillCost)
    crit_range: int | None = Field(default=None, ge=MIN_SKILL_CRIT_RANGE, le=19)
    """擴大暴擊範圍（Phase 3D-7b，6.17 B）：自然骰不小於它就暴擊（17 ＝ 17–20）；取技能與武器
    （法術技為 20）中較寬的。需要有傷害效果。"""
    damage_permille: int | None = Field(default=None, ge=100, le=_PERMILLE - 1)
    """基礎傷害折扣（Phase 3D-7b，6.17 B）：技能的每個傷害效果再 × 它（‰；750 ＝ −25%），
    例如高變異技能用較低的基礎傷害換取暴擊與爆骰。需要有傷害效果。"""
    pierce: bool = False
    """穿透（Phase 3C-5b，6.15）：無視半掩護，並穿過 ``penetrable`` 物件（物件受全額傷害，後方目標
    受 ``core.pierce_behind_permille``）。只能用在遠程的單體或直線形狀。"""
    include_caster: bool = False
    """影響範圍也包含施放者自己（Phase 3D-3）：修正規則 ``allow_self_target`` 套用後的技能才會是
    ``true``（引擎在施放前複製出變形後的技能，見 :func:`trpg.engine.modifiers.shaped_skill`），
    資料檔不必寫。只對有友方效果、形狀不含施放者的技能有意義。"""
    modifiers: tuple[ModifierSpec, ...] = ()
    """修正規則（Phase 3C-2；只有 ``kind: modifier`` 可以有，1～2 條）。"""
    activation: Activation | None = None
    """常駐類傳說的啟動方式（Phase 3D-6）：修正型傳說（``kind: modifier``）與規則改變型傳說
    （``rule_change`` 原語）必填，其他技能不可填。以 ``UseSkill`` 花 ``legendary_activation_ap``
    AP ＋ 源力啟動；啟動前修正規則與規則改變都不生效。"""
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

    @model_validator(mode="after")
    def _check(self) -> SkillDef:
        if self.kind == "modifier":
            self._check_modifier()
        else:
            if not 1 <= len(self.effects) <= _MAX_EFFECTS:
                raise ValueError(
                    f"效果原語必須有 1 到 {_MAX_EFFECTS} 個，收到 {len(self.effects)} 個"
                )
            if self.modifiers:
                raise ValueError(
                    f"只有修正技能（kind: modifier）可以有 modifiers，收到 {self.kind}"
                )
        if self.kind == "active":
            if self.ap_cost is None or not 1 <= self.ap_cost <= _MAX_AP_COST:
                raise ValueError(
                    f"主動技能的 ap_cost 必須是 1 到 {_MAX_AP_COST}，收到 {self.ap_cost}"
                )
        elif self.ap_cost is not None:
            raise ValueError(f"{self.kind} 技能的 ap_cost 必須為 null（不花 AP）")
        if self.cost.self_status is not None and self.kind != "active":
            raise ValueError(f"只有主動技能可以有 cost.self_status，收到 kind: {self.kind}")
        self._check_legendary()
        self._check_copy_skill()
        self._check_hurl_object()
        self._check_pierce()
        self._check_self_moves()
        self._check_pair_moves()
        self._check_summon()
        self._check_zone()
        self._check_gamble()
        if self.kind == "passive" and self.trigger is None:
            raise ValueError("被動技能（kind: passive）必須有 trigger")
        if self.kind != "passive" and self.trigger is not None:
            raise ValueError(f"只有被動技能可以有 trigger，收到 kind: {self.kind}")
        self._check_reaction_and_stance()
        self._check_trap_and_stacks()
        self._check_scaling_and_mastery()
        allowed = ("melee", "ranged") if self.category == "weapon" else ("focus", "any")
        if self.weapon_req not in allowed:
            name = "武器技" if self.category == "weapon" else "法術技"
            raise ValueError(
                f"{name}（category: {self.category}）的 weapon_req 只能是 "
                f"{'、'.join(allowed)}，收到 {self.weapon_req}"
            )
        for index, effect in enumerate(self.effects):
            self._check_effect(index, effect, top=True)
        self._check_variance()
        self._add_gamble_tag()
        return self

    def _add_gamble_tag(self) -> None:
        """帶賭博機制的技能自動加標籤 ``gamble``（傾向向量與「用法決定進化」用；Phase 3D-7a）。"""
        if self.is_gamble and GAMBLE_TAG not in self.tags:
            object.__setattr__(self, "tags", (*self.tags, GAMBLE_TAG))

    def _check_legendary(self) -> None:
        """傳說技能（Phase 3C-4a、3D-6，6.14.4）必須花源力（``cost.source``），非傳說不能花。核心
        三擇一（改寫規則型原語、修正規則、規則改變）是跨檔案檢查（:func:`skill_problems`）。

        常駐類傳說（修正型 ``kind: modifier``、規則改變型 ``rule_change``）必須寫 ``activation``，
        其他技能不可寫；修正型傳說是唯一可以花源力的非主動技能。
        """
        if self.rarity == "legendary" and self.cost.source is None:
            raise ValueError("傳說技能必須有 cost.source（花 1 或 2 點源力）")
        if self.rarity != "legendary" and self.cost.source is not None:
            raise ValueError(f"只有傳說技能可以有 cost.source，收到稀有度 {self.rarity}")
        if self.cost.source is not None and self.kind not in ("active", "modifier"):
            raise ValueError(
                f"只有主動技能與修正型傳說可以花源力（cost.source），收到 kind: {self.kind}"
            )
        lasting = self.rarity == "legendary" and (
            self.kind == "modifier" or any(e.type == RULE_CHANGE for e in self.effects)
        )
        if lasting and self.activation is None:
            raise ValueError("修正型與規則改變型傳說必須寫 activation（timed 限時或 battle 整場）")
        if not lasting and self.activation is not None:
            raise ValueError("只有修正型與規則改變型傳說可以寫 activation")
        self._check_rule_change()

    def _check_rule_change(self) -> None:
        """``rule_change``（Phase 3D-6）：主動技能、形狀 ``self``、技能唯一的效果、對象 ``self``，
        而且是傳說（``activation`` 由 :meth:`_check_legendary` 檢查）。"""
        changes = [e for e in self.effects if e.type == RULE_CHANGE]
        if not changes:
            return
        if self.kind != "active":
            raise ValueError(f"rule_change 只能用在主動技能，收到 kind: {self.kind}")
        if self.rarity != "legendary":
            raise ValueError(f"rule_change 只能用在傳說技能，收到稀有度 {self.rarity}")
        if self.shape.type != "self":
            raise ValueError(f"rule_change 技能的形狀必須是 self，收到 {self.shape.type}")
        if len(self.effects) != 1:
            raise ValueError("rule_change 必須是技能唯一的效果")

    def _check_copy_skill(self) -> None:
        """``copy_skill``（Phase 3C-4b）：主動技能、形狀 ``self``，而且是唯一的效果（複製的技能自己
        有目標，由玩家或 AI 在施放時另選）。"""
        if not any(e.type == COPY_SKILL for e in self.effects):
            return
        if self.kind != "active":
            raise ValueError(f"copy_skill 只能用在主動技能，收到 kind: {self.kind}")
        if self.shape.type != "self":
            raise ValueError(f"copy_skill 技能的形狀必須是 self，收到 {self.shape.type}")
        if len(self.effects) != 1:
            raise ValueError("copy_skill 必須是技能唯一的效果")

    def _check_hurl_object(self) -> None:
        """``hurl_object``（Phase 3C-5a）與形狀 ``object_then_tile`` 必須一起出現：主動技能、
        恰好一個投擲效果（物件只有一個）。"""
        hurls = sum(1 for e in self.effects if e.type == HURL_OBJECT)
        if self.shape.type == "object_then_tile" and hurls != 1:
            raise ValueError("形狀 object_then_tile 的技能必須恰好有一個 hurl_object 效果")
        if hurls == 0:
            return
        if self.kind != "active":
            raise ValueError(f"hurl_object 只能用在主動技能，收到 kind: {self.kind}")
        if self.shape.type != "object_then_tile":
            raise ValueError(f"hurl_object 的形狀必須是 object_then_tile，收到 {self.shape.type}")

    def _check_self_moves(self) -> None:
        """自身位移（Phase 3D-2）：``dash``、``leap``、``swap`` 只能用在主動技能（反應技、姿態、
        被動與陷阱沒有可選的目標或落點）；位移原語最多一個；``dash`` 一律最先結算，必須是第一個
        效果。"""
        types = [e.type for e in self.effects]
        moves = [t for t in types if t in SELF_MOVES]
        if not any(t in (DASH, LEAP, SWAP, CHARGE_THROUGH) for t in moves):
            return
        if self.kind != "active":
            raise ValueError(f"{'、'.join(moves)} 只能用在主動技能，收到 kind: {self.kind}")
        if len(moves) > 1:
            raise ValueError(f"一個技能最多一個改變自身位置的原語，收到 {'、'.join(moves)}")
        if DASH in types and types[0] != DASH:
            raise ValueError("dash 必須是技能的第一個效果（衝鋒一律最先結算）")
        if CHARGE_THROUGH in types:
            self._check_charge_through(types)

    def _check_charge_through(self, types: list[str]) -> None:
        """``charge_through``（Phase 3D-2c）：形狀 ``ground_tile``、第一個效果；其餘效果只能作用在
        施放者自己（沿途的敵人由衝撞自己結算，隊友不受影響）。"""
        if types[0] != CHARGE_THROUGH:
            raise ValueError("charge_through 必須是技能的第一個效果（衝撞一律最先結算）")
        if self.shape.type != "ground_tile":
            raise ValueError(f"charge_through 的形狀必須是 ground_tile，收到 {self.shape.type}")
        for effect in self.effects[1:]:
            if effect.affects != "self":
                raise ValueError(
                    "charge_through 以外的效果必須明寫 affects: self（只作用在施放者）"
                )

    def _check_summon(self) -> None:
        """召喚（Phase 3D-4a）：只能用在主動技能（形狀 ``ground_tile`` 由原語表限制）；每個技能最多
        一個召喚效果，``count`` 目前只能是 1；其餘效果必須明寫 ``affects: self``（選的格子是召喚
        位置，必須是空格，不另外對它結算效果）。"""
        summons = [e for e in self.effects if e.type == SUMMON]
        if not summons:
            return
        if self.kind != "active":
            raise ValueError(f"summon 只能用在主動技能，收到 kind: {self.kind}")
        if len(summons) > 1:
            raise ValueError("一個技能最多一個 summon 效果")
        if (summons[0].count or 1) != 1:
            raise ValueError(f"summon 的 count 目前只能是 1，收到 {summons[0].count}")
        for effect in self.effects:
            if effect.type != SUMMON and effect.affects != "self":
                raise ValueError("summon 以外的效果必須明寫 affects: self（只作用在施放者）")

    def _check_zone(self) -> None:
        """持續區域（Phase 3D-5）：只能用在主動技能，而且是技能唯一的效果；``anchor``、``when``、
        ``duration``、``effects`` 必填，``affects`` 必須是 ``enemies``／``allies``／``all``；
        ``moving`` 要搭配選方向的形狀並填 ``speed``，``caster`` 要搭配以施放者為中心的形狀。"""
        zones = [e for e in self.effects if e.type == ZONE]
        for index, effect in enumerate(self.effects):
            if effect.type != ZONE and any(
                getattr(effect, f) is not None for f in _ZONE_ONLY_FIELDS
            ):
                raise ValueError(f"effects[{index}]：只有 zone 使用 anchor、when、speed、effects")
        if not zones:
            return
        if self.kind != "active":
            raise ValueError(f"zone 只能用在主動技能，收到 kind: {self.kind}")
        if len(self.effects) != 1:
            raise ValueError("zone 必須是技能唯一的效果")
        self._check_zone_effect(zones[0])

    def _check_zone_effect(self, zone: EffectSpec) -> None:
        where = "effects[0]（zone）"
        if zone.anchor is None or zone.when is None or zone.duration is None:
            raise ValueError(f"{where}：必須填 anchor、when、duration")
        if zone.affects not in ("enemies", "allies", "all"):
            raise ValueError(f"{where}：affects 必須明寫 enemies、allies 或 all")
        if zone.anchor == "moving":
            if self.shape.type not in ZONE_MOVING_SHAPES:
                allowed = "、".join(ZONE_MOVING_SHAPES)
                raise ValueError(f"{where}：anchor: moving 的形狀必須是 {allowed}")
            if zone.speed is None:
                raise ValueError(f"{where}：anchor: moving 必須填 speed")
        elif zone.speed is not None:
            raise ValueError(f"{where}：只有 anchor: moving 使用 speed")
        if zone.anchor == "caster" and self.shape.type not in ZONE_CASTER_SHAPES:
            allowed = "、".join(ZONE_CASTER_SHAPES)
            raise ValueError(f"{where}：anchor: caster 的形狀必須是 {allowed}")
        subs = zone.effects or ()
        if not 1 <= len(subs) <= _MAX_ZONE_EFFECTS:
            raise ValueError(f"{where}：effects 必須有 1 到 {_MAX_ZONE_EFFECTS} 個效果")
        for sub_index, sub in enumerate(subs):
            if sub.type not in ZONE_EFFECT_TYPES:
                allowed = "、".join(ZONE_EFFECT_TYPES)
                raise ValueError(
                    f"{where}.effects[{sub_index}]：只能使用 {allowed}，收到 {sub.type}"
                )
            if sub.affects is not None or sub.condition is not None:
                raise ValueError(
                    f"{where}.effects[{sub_index}]：區域的效果不可自帶 affects 或 condition"
                )
            self._check_effect(0, sub)

    def _check_gamble(self) -> None:
        """賭博型（Phase 3D-7a）：``gamble`` 只能用在主動技能、每個技能一個而且是最後一個效果；
        ``cost.on_miss`` 只有主動技能可以有。分支與反噬的內容見 :meth:`_check_branch`。"""
        gambles = [e for e in self.effects if e.type == GAMBLE]
        for index, effect in enumerate(self.effects):
            if effect.type != GAMBLE and any(
                getattr(effect, f) is not None for f in _GAMBLE_ONLY_FIELDS
            ):
                raise ValueError(f"effects[{index}]：只有 gamble 使用 chance_permille、win、lose")
            if effect.type in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
                raise ValueError(f"effects[{index}]：{effect.type} 只能出現在 gamble 的分支裡")
        self._check_on_miss()
        if not gambles:
            return
        if self.kind != "active":
            raise ValueError(f"gamble 只能用在主動技能，收到 kind: {self.kind}")
        if len(gambles) > 1:
            raise ValueError("一個技能最多一個 gamble 效果")
        if self.effects[-1].type != GAMBLE:
            raise ValueError("gamble 必須是技能的最後一個效果（成敗分支最後結算）")
        self._check_gamble_effect(gambles[0], f"effects[{len(self.effects) - 1}]（gamble）")

    def _check_on_miss(self) -> None:
        """``cost.on_miss``（失手反噬）：只有主動技能可以有。"""
        if not self.cost.on_miss:
            return
        if self.kind != "active":
            raise ValueError(f"只有主動技能可以有 cost.on_miss，收到 kind: {self.kind}")
        self._check_branch("cost.on_miss", self.cost.on_miss, BACKLASH_TYPES, backlash=True)

    def _check_gamble_effect(self, gamble: EffectSpec, where: str) -> None:
        """``gamble`` 效果本身：必填 ``chance_permille``、``win`` 與 ``lose`` 至少一邊有效果。"""
        if gamble.chance_permille is None:
            raise ValueError(f"{where}：必須填 chance_permille")
        if not (gamble.win or gamble.lose):
            raise ValueError(f"{where}：win 與 lose 至少要有一邊有效果")
        for name in ("win", "lose"):
            branch = getattr(gamble, name) or ()
            if branch:
                self._check_branch(f"{where}.{name}", branch, GAMBLE_BRANCH_TYPES, backlash=False)

    def _check_branch(
        self,
        where: str,
        branch: tuple[EffectSpec, ...],
        allowed: tuple[str, ...],
        *,
        backlash: bool,
    ) -> None:
        """賭注分支或失手反噬的效果列表：1–2 個、類型在 ``allowed`` 內、不自帶 ``condition``；
        反噬的對象只能是施放者自己；倍率與自傷各至多一個，而且技能要有傷害效果可以乘。"""
        if not 1 <= len(branch) <= _MAX_BRANCH_EFFECTS:
            raise ValueError(
                f"{where}：必須有 1 到 {_MAX_BRANCH_EFFECTS} 個效果，收到 {len(branch)}"
            )
        has_damage = any(e.type == "damage" for e in self.effects)
        for i, sub in enumerate(branch):
            at = f"{where}[{i}]（{sub.type}）"
            if sub.type not in allowed:
                raise ValueError(f"{at}：只能使用 {'、'.join(allowed)}")
            if sub.condition is not None:
                raise ValueError(f"{at}：不可自帶 condition")
            if backlash and sub.affects not in (None, "self"):
                raise ValueError(f"{at}：失手反噬的對象只能是施放者（省略 affects 或寫 self）")
            if sub.affects == "tiles":
                raise ValueError(f"{at}：不能用 affects: tiles")
            self._check_branch_fields(at, sub, has_damage=has_damage)
            if sub.type not in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
                self._check_effect(0, sub)
        for special in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
            if sum(1 for e in branch if e.type == special) > 1:
                raise ValueError(f"{where}：每個分支最多一個 {special}")

    @staticmethod
    def _check_branch_fields(where: str, sub: EffectSpec, *, has_damage: bool) -> None:
        """分支效果的專用欄位：``damage_multiplier`` 與 ``self_damage_of_hit`` 必填自己的數值、
        不可自帶 ``affects``，而且技能要有傷害效果；其他類型不可填這兩個欄位。"""
        if sub.type == DAMAGE_MULTIPLIER:
            if (
                sub.damage_multiplier_permille is None
                or sub.damage_multiplier_permille == _PERMILLE
            ):
                raise ValueError(f"{where}：必須填 damage_multiplier_permille（不等於 1000）")
        elif sub.damage_multiplier_permille is not None:
            raise ValueError(f"{where}：只有 damage_multiplier 使用 damage_multiplier_permille")
        if sub.type == SELF_DAMAGE_OF_HIT:
            if sub.self_damage_permille_of_hit is None:
                raise ValueError(f"{where}：必須填 self_damage_permille_of_hit")
        elif sub.self_damage_permille_of_hit is not None:
            raise ValueError(f"{where}：只有 self_damage_of_hit 使用 self_damage_permille_of_hit")
        if sub.type in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
            if sub.affects is not None:
                raise ValueError(f"{where}：不可自帶 affects")
            if not has_damage:
                raise ValueError(f"{where}：技能必須有傷害效果")

    def _check_pair_moves(self) -> None:
        """位移他人（Phase 3D-2b）：``teleport_target`` 與形狀 ``unit_then_tile``、``swap_any`` 與
        形狀 ``unit_pair`` 必須一起出現；主動技能、是技能唯一的效果（選取的單位與落點就是它的
        參數，不另外結算命中與其他效果）。"""
        needed = {t for t in PAIR_SHAPES.values()}
        if self.shape.type in needed and not any(
            e.type in PAIR_MOVES and PAIR_SHAPES[e.type] == self.shape.type for e in self.effects
        ):
            raise ValueError(f"形狀 {self.shape.type} 的技能必須有對應的位移他人效果")
        for effect in self.effects:
            if effect.type not in PAIR_MOVES:
                continue
            if self.kind != "active":
                raise ValueError(f"{effect.type} 只能用在主動技能，收到 kind: {self.kind}")
            if self.shape.type != PAIR_SHAPES[effect.type]:
                raise ValueError(
                    f"{effect.type} 的形狀必須是 {PAIR_SHAPES[effect.type]}，收到 {self.shape.type}"
                )
            if len(self.effects) != 1:
                raise ValueError(f"{effect.type} 必須是技能唯一的效果")

    def _check_pierce(self) -> None:
        """``pierce``（Phase 3C-5b）：主動技能或反應技、遠程武器或法術、形狀是單體（射程大於 1）或
        直線，而且要有對敵方的傷害效果。射程是否算「遠程」另由引擎依武器判斷。"""
        if not self.pierce:
            return
        if self.kind not in ("active", "reaction"):
            raise ValueError(f"pierce 只能用在主動技能與反應技，收到 kind: {self.kind}")
        if self.shape.type not in PIERCE_SHAPES:
            raise ValueError(
                f"pierce 的形狀必須是 {'、'.join(PIERCE_SHAPES)}，收到 {self.shape.type}"
            )
        if self.weapon_req == "melee":
            raise ValueError("pierce 不能用在近戰武器技")
        if self.shape.type == "single" and self.shape.range == 1:
            raise ValueError("pierce 的單體形狀射程必須大於 1")
        if not any(e.type == "damage" for e in self.effects):
            raise ValueError("pierce 的技能必須有傷害效果")

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
            if self.reaction.event == "ally_downed" and self.shape.type != "self":
                raise ValueError("ally_downed 的反應技形狀必須是 self（另一方已經倒下）")
        elif INTERCEPT in types:
            raise ValueError("intercept 只能用在反應技")

    def _check_modifier(self) -> None:
        """修正技能（3C-2）：裝在被動欄位、不花 AP、沒有觸發；效果都寫在 ``modifiers`` 裡。"""
        if not 1 <= len(self.modifiers) <= _MAX_MODIFIERS:
            count = len(self.modifiers)
            raise ValueError(
                f"修正技能的 modifiers 必須有 1 到 {_MAX_MODIFIERS} 條，收到 {count} 條"
            )
        if self.effects:
            raise ValueError("修正技能（kind: modifier）的 effects 必須為空（效果寫在 modifiers）")
        if self.shape.type != "self":
            raise ValueError(f"修正技能的形狀只能是 self，收到 {self.shape.type}")
        if self.condition is not None:
            raise ValueError("修正技能不能有技能層級的 condition（條件寫在每條修正規則）")
        allowed = (
            SkillCost(source=self.cost.source, cooldown=self.cost.cooldown)
            if self.rarity == "legendary"
            else SkillCost()
        )
        if self.cost != allowed:
            raise ValueError(
                "修正型傳說的代價只能有源力與冷卻（cost.source、cost.cooldown）"
                if self.rarity == "legendary"
                else "修正技能不能有代價（cost 必須為空）"
            )
        if self.mastery is not None:
            raise ValueError("修正技能不能有 mastery")
        for rule_index, rule in enumerate(self.modifiers):
            for index, effect in enumerate(rule.change.on_hit_effects or ()):
                try:
                    self._check_effect(index, effect)
                except ValueError as exc:
                    raise ValueError(f"modifiers[{rule_index}].change.on_hit_{exc}") from None

    def _check_scaling_and_mastery(self) -> None:
        """雙屬性縮放與專精加成的結構（2H-2；稀有度門檻是跨檔案檢查）。"""
        if self.secondary_scaling_attr == self.scaling_attr:
            raise ValueError("secondary_scaling_attr 不可和 scaling_attr 相同")
        if self.mastery is None:
            return
        if self.secondary_scaling_attr is not None:
            raise ValueError("雙屬性技能不享專精加成（mastery 與 secondary_scaling_attr 不可並用）")
        if self.mastery == "range" and self.shape.range is None:
            raise ValueError("mastery: range 只能用在有施放距離（shape.range）的技能")
        if self.mastery == "duration" and not any(e.type == "apply_status" for e in self.effects):
            raise ValueError("mastery: duration 只能用在有 apply_status 效果的技能")

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
        banned = [t for t in types if t in (*SELF_MOVES, *PAIR_MOVES, ADD_STACK, CONSUME_STACK)]
        if banned:
            raise ValueError(f"陷阱技能不能有 {'、'.join(banned)}（陷阱觸發時才結算其餘效果）")

    def _check_consume_status(self, index: int, effect: EffectSpec) -> None:
        """``consume_status`` 的結構（3C-3b）：``then`` 1–2 個、只能用 :data:`CONSUME_THEN_TYPES`、
        不自帶對象；``scale``、``splash``、``then`` 只屬於 ``consume_status``。"""
        where = f"effects[{index}]（{effect.type}）"
        if effect.type != CONSUME_STATUS:
            if effect.then is not None or effect.scale is not None or effect.splash is not None:
                raise ValueError(f"{where}：只有 consume_status 使用 then、scale、splash")
            return
        then = effect.then or ()
        if not 1 <= len(then) <= _MAX_CONSUME_THEN:
            raise ValueError(
                f"{where}：then 必須有 1 到 {_MAX_CONSUME_THEN} 個效果，收到 {len(then)}"
            )
        if effect.scale == "stacks" and effect.stack is None:
            raise ValueError(f"{where}：scale: stacks 必須填 stack（目標型層數）")
        if effect.scale != "stacks" and effect.stack is not None:
            raise ValueError(f"{where}：只有 scale: stacks 使用 stack")
        for sub_index, sub in enumerate(then):
            if sub.type not in CONSUME_THEN_TYPES:
                allowed = "、".join(CONSUME_THEN_TYPES)
                raise ValueError(f"{where}.then[{sub_index}]：只能使用 {allowed}，收到 {sub.type}")
            if sub.affects is not None or sub.condition is not None:
                raise ValueError(
                    f"{where}.then[{sub_index}]：then 的效果不可自帶 affects 或 condition"
                )
            self._check_effect(index, sub)

    def _check_restore_resource(self, where: str, effect: EffectSpec) -> None:
        """``restore_resource`` 的結構（3D-1）：必須填 ``resource``；冷卻最多 −2。"""
        if effect.resource is None:
            raise ValueError(f"{where}：restore_resource 必須填 resource（mana 或 cooldown）")
        if effect.resource == "cooldown" and (effect.amount or 1) > _MAX_COOLDOWN_RESTORE:
            raise ValueError(f"{where}：冷卻最多縮短 {_MAX_COOLDOWN_RESTORE} 回合")

    def _check_variable_damage(self, where: str, effect: EffectSpec, *, top: bool) -> None:
        """``explode``、``scaling``（Phase 3D-7b）與 ``lifesteal_permille``、``split_heal``
        （Phase 3D-8a）：只有技能自己的 ``damage`` 效果可以用（不能在賭注分支、失手反噬、``then``
        裡）；``scaling.cap_permille`` 的上限是跨檔案檢查。"""
        if (
            effect.explode is None
            and effect.scaling is None
            and effect.lifesteal_permille is None
            and effect.split_heal is None
        ):
            return
        if effect.type != "damage":
            raise ValueError(f"{where}：只有 damage 使用 explode、scaling、lifesteal、split_heal")
        if not top:
            raise ValueError(
                f"{where}：explode、scaling、lifesteal、split_heal 只能用在技能自己的傷害效果"
            )
        if effect.explode is False:
            raise ValueError(f"{where}：explode 只能填 true（不爆骰就省略）")
        if effect.split_heal is not None:
            self._check_split_heal(where, effect)

    def _check_split_heal(self, where: str, effect: EffectSpec) -> None:
        """``split_heal``（聖光雙效）：只能填 true、``affects: all``、法術技、``aura``／``area``
        骨架、主動技能，不可與吸血、爆骰、縮放並用（治療與傷害要用同一個骰值）。"""
        if effect.split_heal is False:
            raise ValueError(f"{where}：split_heal 只能填 true（不分流就省略）")
        if effect.affects != "all":
            raise ValueError(f"{where}：split_heal 必須搭配 affects: all")
        if self.category != "spell" or self.kind != "active":
            raise ValueError(f"{where}：split_heal 只能用在主動的法術技")
        if self.skeleton not in SPLIT_SKELETONS:
            allowed = "、".join(SPLIT_SKELETONS)
            raise ValueError(f"{where}：split_heal 只能用在 {allowed} 骨架，收到 {self.skeleton}")
        if effect.lifesteal_permille is not None or effect.explode or effect.scaling is not None:
            raise ValueError(f"{where}：split_heal 不能與 lifesteal、explode、scaling 並用")

    def _check_variance(self) -> None:
        """``crit_range``、``damage_permille`` 需要有傷害效果、只能用在主動技能。"""
        if self.crit_range is None and self.damage_permille is None:
            return
        if self.kind != "active":
            raise ValueError(f"只有主動技能可以有 crit_range、damage_permille，收到 {self.kind}")
        if not any(e.type == "damage" for e in self.effects):
            raise ValueError("crit_range、damage_permille 需要技能有傷害效果")

    def _check_effect(self, index: int, effect: EffectSpec, *, top: bool = False) -> None:
        where = f"effects[{index}]（{effect.type}）"
        self._check_variable_damage(where, effect, top=top)
        self._check_consume_status(index, effect)
        if effect.type == RESET_COOLDOWN:
            if effect.which is None:
                raise ValueError(f"{where}：reset_cooldown 必須填 which（all 或 tag）")
            if (effect.which == "tag") != (effect.tag is not None):
                raise ValueError(f"{where}：which: tag 必須填 tag，which: all 不可填 tag")
        elif effect.which is not None or effect.tag is not None:
            raise ValueError(f"{where}：只有 reset_cooldown 使用 which、tag")
        if effect.type == RESTORE_RESOURCE:
            self._check_restore_resource(where, effect)
        elif effect.resource is not None:
            raise ValueError(f"{where}：只有 restore_resource 使用 resource")
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
    def is_gamble(self) -> bool:
        """帶賭博機制（Phase 3D-7a、7b）：有 ``gamble`` 效果、失手反噬 ``cost.on_miss``、高變異
        （``explode``、``crit_range``）或以血換力（``scaling`` 依 ``missing_hp_10pct``）。
        超載是層數的規則（見 ``StackDef``），由帶標籤的技能在預算上反映。"""
        return (
            bool(self.cost.on_miss)
            or self.crit_range is not None
            or any(
                e.type == GAMBLE
                or e.explode
                or (e.scaling is not None and e.scaling.by == "missing_hp_10pct")
                for e in self.effects
            )
        )

    @property
    def is_active(self) -> bool:
        return self.kind == "active"

    @property
    def is_modifier(self) -> bool:
        """修正技能（改造型與修正型被動，3C-2）：不能施放，持續改變持有者自己的動作。"""
        return self.kind == "modifier"

    @property
    def is_activatable(self) -> bool:
        """常駐類傳說（Phase 3D-6）：以 ``UseSkill`` 啟動，啟動前不生效。"""
        return self.activation is not None

    @property
    def rule_change_id(self) -> str | None:
        """規則改變型傳說引用的規則改變 ID（Phase 3D-6）；其他技能為 ``None``。"""
        return next((e.rule for e in self.effects if e.type == RULE_CHANGE), None)

    @property
    def is_actionable(self) -> bool:
        """玩家可以在自己的回合用 ``UseSkill`` 施放：主動技能與姿態（花 AP），以及修正型傳說的
        啟動（Phase 3D-6，裝在被動欄位、從技能列啟動）。"""
        return self.kind in ("active", "stance") or (self.is_modifier and self.is_activatable)


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


def _count_problem(where: str, primitive: PrimitiveDef, name: str, value: object) -> str | None:
    """``count`` 型參數（Phase 3D-8a）：``all`` 或 ``min``–``max`` 的整數。"""
    spec = primitive.params[name]
    if value == "all":
        return None
    low, high = spec.min or 1, spec.max
    if isinstance(value, int) and low <= value and (high is None or value <= high):
        return None
    return f"{where}.{name}：{primitive.id} 的 {name} 必須在 {low}–{high} 或 all，收到 {value!r}"


def _value_problem(
    where: str, primitive: PrimitiveDef, name: str, value: object, refs: _Refs
) -> str | None:
    """單一原語參數值的問題（範圍或引用不存在）。"""
    spec = primitive.params[name]
    if spec.type == "count":
        return _count_problem(where, primitive, name, value)
    if spec.type == "int":
        assert isinstance(value, int)
        below = spec.min is not None and value < spec.min
        above = spec.max is not None and value > spec.max
        if below or above:
            return (
                f"{where}.{name}：{primitive.id} 的 {name} "
                f"必須在 {spec.min}–{spec.max}，收到 {value}"
            )
    elif spec.type == "surface" and value is Surface.NONE:
        return f"{where}.{name}：不能產生 none 表面"
    else:
        return _reference_problem(where, name, spec.type, value, refs)
    return None


def _reference_problem(where: str, name: str, kind: str, value: object, refs: _Refs) -> str | None:
    """引用其他資料檔 ID 的參數（狀態、物件、層數、召喚物範本）是否存在。"""
    known: dict[str, tuple[Collection[object] | None, str]] = {
        "status": (refs.status_ids, "狀態"),
        "object": (refs.object_ids, "物件"),
        "stack": (refs.stacks, "層數"),
        "summon": (refs.summon_ids, "召喚物範本"),
        "rule_change": (refs.rule_change_ids, "規則改變"),
    }
    entry = known.get(kind)
    if entry is None or entry[0] is None or value in entry[0]:
        return None
    return f"{where}.{name}：未知的{entry[1]} {value!r}"


@dataclass(frozen=True, slots=True)
class _Refs:
    """跨檔案驗證用的引用表。"""

    primitives: dict[str, PrimitiveDef]
    status_ids: set[str]
    object_ids: set[str]
    conditions: dict[str, ConditionDef]
    stacks: dict[str, StackDef] | None = None
    summon_ids: set[str] | None = None
    rule_change_ids: set[str] | None = None
    unsafe_statuses: frozenset[str] | None = None
    """不能當反噬的狀態（硬控、跳過回合、持續傷害；Phase 3D-7a）；``None`` 不檢查。"""
    scale_cap_max: int | None = None
    """``scaling.cap_permille`` 的上限（``core.yaml`` 的 ``scale_cap_max_permille``；Phase 3D-7b）；
    ``None`` 不檢查。"""


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
    problems += _consume_status_problems(skill, index, effect, refs)
    problems += _zone_problems(skill, index, effect, refs)
    problems += _gamble_problems(skill, index, effect, refs)
    problems += _scaling_problems(where, effect, refs)
    return problems


def _scaling_problems(where: str, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``scaling.cap_permille`` 不超過 ``core.scale_cap_max_permille``（Phase 3D-7b）。"""
    scaling = effect.scaling
    if scaling is None or refs.scale_cap_max is None or scaling.cap_permille <= refs.scale_cap_max:
        return []
    return [
        f"{where}.scaling.cap_permille：{scaling.cap_permille} 超過上限 {refs.scale_cap_max}"
        "（core.yaml 的 scale_cap_max_permille）"
    ]


def _branch_problems(
    where: str, skill: SkillDef, branch: tuple[EffectSpec, ...], refs: _Refs, *, backlash: bool
) -> list[str]:
    """賭注分支或失手反噬的跨檔案檢查（Phase 3D-7a）：真正的原語（傷害、治療、護盾、施加狀態）
    當成同一技能的效果檢查；對施放者自己的狀態不能是硬控、跳過回合或持續傷害（反噬不致命、不讓
    施放者跳過回合）；對敵方的效果需要技能本身有對敵方的效果（才有命中判定）。"""
    problems: list[str] = []
    carrier = skill.model_copy(update={"effects": branch})
    hostile = any(
        (e.affects or _default_affects_of(refs, e)) in ("enemies", "all")
        for e in skill.effects
        if e.type != GAMBLE
    )
    for i, sub in enumerate(branch):
        if sub.type in (DAMAGE_MULTIPLIER, SELF_DAMAGE_OF_HIT):
            continue
        prefix = f"effects[{i}]"
        problems += [
            f"{where}[{i}]{p.removeprefix(prefix)}" for p in _effect_problems(carrier, i, sub, refs)
        ]
        affects = "self" if backlash else sub.affects or _default_affects_of(refs, sub)
        unsafe = refs.unsafe_statuses or frozenset()
        if affects == "self" and sub.type == "apply_status" and sub.status in unsafe:
            problems.append(
                f"{where}[{i}].status：反噬不能使用硬控、跳過回合或持續傷害的狀態（{sub.status}）"
            )
        if affects in ("enemies", "all") and not hostile and not backlash:
            problems.append(f"{where}[{i}].affects：技能沒有對敵方的效果，沒有命中判定可以依據")
    return problems


def _default_affects_of(refs: _Refs, effect: EffectSpec) -> str:
    primitive = refs.primitives.get(effect.type)
    return "enemies" if primitive is None else default_affects(primitive)


def _gamble_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``gamble`` 的跨檔案檢查（Phase 3D-7a）：``win``／``lose`` 的效果。"""
    if effect.type != GAMBLE:
        return []
    problems: list[str] = []
    for name in ("win", "lose"):
        branch = getattr(effect, name) or ()
        problems += _branch_problems(
            f"effects[{index}].{name}", skill, branch, refs, backlash=False
        )
    return problems


def _zone_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``zone`` 的跨檔案檢查（Phase 3D-5）：``effects`` 當成同一技能的效果檢查（原語、參數、
    引用）。"""
    if effect.type != ZONE:
        return []
    problems: list[str] = []
    subs = effect.effects or ()
    carrier = skill.model_copy(update={"effects": subs})
    for sub_index, sub in enumerate(subs):
        problems += [
            f"effects[{index}].effects{p.removeprefix('effects')}"
            for p in _effect_problems(carrier, sub_index, sub, refs)
        ]
    return problems


def _consume_status_problems(
    skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs
) -> list[str]:
    """``consume_status`` 的跨檔案檢查：``then`` 的效果當成同一技能的效果檢查（原語、參數、引用），
    ``scale: stacks`` 的層數必須存在且是目標型。"""
    if effect.type != CONSUME_STATUS:
        return []
    problems: list[str] = []
    carrier = skill.model_copy(update={"effects": effect.then or ()})
    for sub_index, sub in enumerate(effect.then or ()):
        problems += [
            f"effects[{index}].then{p.removeprefix('effects')}"
            for p in _effect_problems(carrier, sub_index, sub, refs)
        ]
    if effect.scale == "stacks" and refs.stacks is not None and effect.stack is not None:
        stack = refs.stacks.get(effect.stack)
        if stack is None:
            problems.append(f"effects[{index}].stack：未知的層數 {effect.stack!r}")
        elif stack.owner != "target":
            problems.append(
                f"effects[{index}].stack：scale: stacks 需要目標型層數（owner: target）"
            )
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


def _trigger_problems(
    skill: SkillDef, triggers: dict[str, SkillTriggerDef], status_ids: set[str]
) -> list[str]:
    """被動技能的觸發設定：時機存在、``target: other`` 只用在有另一方的時機、``status`` 存在。"""
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
    if spec.status is not None and spec.status not in status_ids:
        return [f"trigger.status：未知的狀態 {spec.status!r}"]
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
    dual_min_rarity: str | None = None,
    summon_ids: set[str] | None = None,
    rule_change_ids: set[str] | None = None,
    unsafe_statuses: frozenset[str] | None = None,
    scale_cap_max: int | None = None,
) -> list[str]:
    """技能引用的形狀、原語、條件、狀態、物件是否存在、參數是否在範圍內（繁體中文，空串列為通過）。

    ``triggers``：觸發時機表（省略時不檢查被動的 ``trigger``）；``stacks``：層數表（省略時不檢查
    層數原語引用的層數）；``dual_min_rarity``：雙屬性縮放的最低稀有度（省略時不檢查）；
    ``summon_ids``：召喚物範本 ID（省略時不檢查 ``summon`` 的 ``unit``）；``rule_change_ids``：
    規則改變 ID（Phase 3D-6，省略時不檢查 ``rule_change`` 的 ``rule``）；``unsafe_statuses``：
    不能當反噬的狀態 ID（Phase 3D-7a，省略時不檢查）；``scale_cap_max``：``scaling`` 的
    ``cap_permille`` 上限（Phase 3D-7b，省略時不檢查）。
    """
    problems: list[str] = []
    if (
        dual_min_rarity is not None
        and skill.secondary_scaling_attr is not None
        and rarity_rank(skill.rarity) < rarity_rank(dual_min_rarity)
    ):
        problems.append(
            f"secondary_scaling_attr：雙屬性縮放最低稀有度為 {dual_min_rarity}，收到 {skill.rarity}"
        )
    shape = shapes.get(skill.shape.type)
    if shape is None:
        known = ", ".join(sorted(shapes))
        problems.append(f"shape.type：未知的形狀 {skill.shape.type!r}（可用：{known}）")
    else:
        problems += _int_param_problems("shape", skill.shape.param_values(), shape)
    if skill.trap is not None and skill.trap.shape not in shapes:
        known = ", ".join(sorted(shapes))
        problems.append(f"trap.shape：未知的形狀 {skill.trap.shape!r}（可用：{known}）")
    refs = _Refs(
        primitives,
        status_ids,
        object_ids,
        conditions,
        stacks,
        summon_ids,
        rule_change_ids,
        unsafe_statuses,
        scale_cap_max,
    )
    if stacks is not None:
        problems += _cost_stack_problems(skill, stacks)
    self_status = skill.cost.self_status
    if self_status is not None and self_status.status not in status_ids:
        problems.append(f"cost.self_status：未知的狀態 {self_status.status!r}")
    if triggers is not None:
        problems += _trigger_problems(skill, triggers, status_ids)
    if skill.condition is not None:
        problems += _condition_problems("condition", skill.condition, refs)
    for index, effect in enumerate(skill.effects):
        problems += _effect_problems(skill, index, effect, refs)
    problems += _branch_problems("cost.on_miss", skill, skill.cost.on_miss, refs, backlash=True)
    problems += _modifier_problems(skill, refs)
    problems += _legendary_problems(skill, primitives)
    return problems


def legendary_cores(skill: SkillDef, primitives: dict[str, PrimitiveDef]) -> list[str]:
    """傳說的核心（Phase 3D-6，6.14.4 三擇一）：每個改寫規則型原語、修正規則（整組算一個）、
    每個規則改變各算一個，依出現順序回傳種類（``rule_rewrite``／``modifier``／``rule_change``）。"""
    cores = [
        "rule_rewrite"
        for e in skill.effects
        if e.type in primitives and primitives[e.type].category == "rule_rewrite"
    ]
    if skill.modifiers:
        cores.append("modifier")
    cores += ["rule_change" for e in skill.effects if e.type == RULE_CHANGE]
    return cores


def _legendary_problems(skill: SkillDef, primitives: dict[str, PrimitiveDef]) -> list[str]:
    """傳說技能（Phase 3C-4a、3D-6，6.14.4）＝ 恰好 1 個核心（改寫規則型原語、修正規則、規則改變
    三擇一）＋ 源力代價。"""
    if skill.rarity != "legendary":
        return []
    cores = legendary_cores(skill, primitives)
    if len(cores) == 1:
        return []
    found = "、".join(cores) if cores else "沒有"
    return [
        "rarity：傳說技能必須恰好有 1 個核心（改寫規則型原語、修正規則 modifiers、規則改變 "
        f"rule_change 三擇一），收到 {found}"
    ]


def _modifier_problems(skill: SkillDef, refs: _Refs) -> list[str]:
    """修正規則的跨檔案檢查：條件存在且參數合法、命中後效果的原語與引用（當成以 ``self`` 形狀
    施放的效果檢查）。"""
    problems: list[str] = []
    for rule_index, rule in enumerate(skill.modifiers):
        where = f"modifiers[{rule_index}]"
        if rule.condition is not None:
            problems += _condition_problems(f"{where}.condition", rule.condition, refs)
        effects = rule.change.on_hit_effects
        if not effects:
            continue
        carrier = on_hit_carrier(skill, effects)
        for index, effect in enumerate(effects):
            problems += [
                f"{where}.change.on_hit_{p}" for p in _effect_problems(carrier, index, effect, refs)
            ]
    return problems


def on_hit_carrier(skill: SkillDef, effects: tuple[EffectSpec, ...]) -> SkillDef:
    """把修正規則的命中後效果包成一個「技能」（同一個修正技能的複本，``effects`` 換成命中後
    效果），讓驗證、預算與引擎的自動命中施放沿用一般技能的程式。不經過 schema 驗證。"""
    return skill.model_copy(update={"effects": effects})


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
    """裝備的技能數量超過 ``core.yaml`` 的欄位上限時的原因（依 ``kind``），以及規則改變型傳說
    超過 1 個（Phase 3D-6）。"""
    skills = tuple(skills)
    # 修正技能（kind: modifier，3C-2）裝在被動欄位，與觸發型被動共用上限
    counts: Counter[str] = Counter("passive" if s.is_modifier else s.kind for s in skills)
    limits = {
        "active": slots.active,
        "passive": slots.passive,
        "reaction": slots.reaction,
        "stance": slots.stance,
    }
    names = {"active": "主動", "passive": "被動（含修正）", "reaction": "反應", "stance": "姿態"}
    problems = [
        f"{names[kind]}技能超過欄位上限：{counts[kind]} 個（上限 {limits[kind]}）"
        for kind in limits
        if counts[kind] > limits[kind]
    ]
    changes = sorted(s.name_zh for s in skills if s.rule_change_id is not None)
    if len(changes) > 1:  # 改變規則型傳說每人最多裝 1 個（Phase 3D-6，使用者決定）
        problems.append(
            f"規則改變型傳說每人最多裝 1 個，收到 {len(changes)} 個：{'、'.join(changes)}"
        )
    return problems
