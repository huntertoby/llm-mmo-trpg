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
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, Dice
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.rules import SkillSlots
from trpg.content.schemas import ContentModel
from trpg.content.skill_tags import UNKNOWN_TAG_TEXT
from trpg.content.yaml_sources import (
    mechanic_status,
    primitive_status,
    shape_role,
    split_heal_skeletons,
)
from trpg.shared.bonus_text import bonus_text
from trpg.shared.types import Attribute, Element, Surface, rune_name

if TYPE_CHECKING:
    from trpg.content.battle import WeaponDef
    from trpg.content.rules import CoreRules
    from trpg.content.skill_triggers import SkillTriggerDef
    from trpg.content.stacks import StackDef

__all__ = [
    "ADD_STACK",
    "AFFECTS_VALUES",
    "BACKLASH_TYPES",
    "BASIC_ACTIONS",
    "BLOW_SURFACE",
    "CASTER_CONDITIONS",
    "CHANGE_TARGETS",
    "CHARGE_THROUGH",
    "CHARGING",
    "CHEAT_DEATH",
    "CHEAT_DEATH_STATUS",
    "COMPOSITE_KIND_ZH",
    "COMPOSITE_MOVES",
    "CONSUME_STACK",
    "CONSUME_STATUS",
    "CONSUME_THEN_TYPES",
    "COPY_SKILL",
    "DAMAGE_MULTIPLIER",
    "DASH",
    "DELAYED_DAMAGE",
    "DELAYED_RELEASE_VALUES",
    "DELAYED_SHAPES",
    "DETONATE_RUNES",
    "DISPEL",
    "EFFECT_NON_PARAM_FIELDS",
    "EFFECT_PARAM_FIELDS",
    "EXTRA_REACTION",
    "FOLLOWUP_AUTO_WHENS",
    "FOLLOWUP_CHOICE_WHENS",
    "FOLLOWUP_FORBIDDEN",
    "FOLLOWUP_SHAPES",
    "FOLLOWUP_WHEN_VALUES",
    "GAMBLE",
    "GAMBLE_BRANCH_TYPES",
    "GAMBLE_TAG",
    "GATHER_SHAPES",
    "GRANT_AP",
    "GRANT_SKILL",
    "HURL_OBJECT",
    "INSCRIBE",
    "INTERCEPT",
    "LEAP",
    "LEGACY_REACTION_EVENTS",
    "MAX_GRANT_DURATION",
    "MAX_MODIFIERS",
    "MAX_SUMMON_COUNT",
    "MAX_VARIANTS",
    "MIN_SKILL_CRIT_RANGE",
    "MODIFIER_CHANGES",
    "ON_HIT_PRIMITIVES",
    "ON_KILL_TYPES",
    "ON_MISS_MIN_RARITY",
    "PAIR_MOVES",
    "PAIR_SHAPES",
    "PIERCE_SHAPES",
    "PLACE_TRAP",
    "RARITY_ORDER",
    "REDIRECT_DAMAGE",
    "REDIRECT_STATUS",
    "REFUND_AP",
    "REFUND_COOLDOWN",
    "REQUIRED_CONDITIONS",
    "REQUIRED_SHAPES",
    "RESET_COOLDOWN",
    "REVEAL",
    "REVIVE",
    "RULE_CHANGE",
    "SACRIFICE_SUMMON",
    "SCALE_BY_VALUES",
    "SELF_CONDITIONS",
    "SELF_DAMAGE_OF_HIT",
    "SELF_ONLY_CHANGES",
    "SHADOWSTEP",
    "SHAPE_REQUIRED_PRIMITIVES",
    "SKELETON_IDS",
    "SKILL_ID_PATTERN",
    "SKILL_REACTION_EVENTS",
    "SPLIT_SKELETONS",
    "SUMMON",
    "SWAP",
    "SWAP_ANY",
    "TELEPORT_TARGET",
    "TIME_BOMB",
    "TOPPLE",
    "VARIANT_CONDITIONS",
    "VARIANT_TARGET_CONDITIONS",
    "WEAPON_CLASSES",
    "WIELDING_EFFECT_ONLY",
    "WIELDING_WEAPON",
    "ZONE",
    "ZONE_CASTER_SHAPES",
    "ZONE_EFFECT_TYPES",
    "ZONE_MOVING_SHAPES",
    "Activation",
    "Affects",
    "BasicAction",
    "CompositionRule",
    "ConditionDef",
    "ConditionSpec",
    "ConditionTable",
    "EffectSpec",
    "FollowupSpec",
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
    "RequiredWhen",
    "ScaleSpec",
    "ShapeBudget",
    "ShapeCells",
    "ShapeDef",
    "ShapeSpec",
    "ShapeTable",
    "SkillCost",
    "SkillDef",
    "SkillRuleError",
    "SkillTable",
    "TrapSpec",
    "TriggerSpec",
    "VariantEffectSwap",
    "VariantSpec",
    "VariantWhen",
    "composition_rules",
    "composition_shapes",
    "condition_text",
    "default_affects",
    "granted_skill_problems",
    "held_gear",
    "is_wind_skill",
    "legendary_cores",
    "on_hit_carrier",
    "param_required_for",
    "rarity_rank",
    "skill_elements",
    "skill_problems",
    "skill_slot_problems",
    "true_only_params",
    "walk_effect",
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
    "rune",
    "sacrifice",
)
"""``docs/design/06-技能.md`` 6.9 的 12 種骨架，加上 Phase 3C-2 的 ``modifier``（修正規則：改造型與
修正型被動，6.14.1）、3C-3b 的 ``consume_status``（6.14.2 管道 1）與 3-23 的 ``rune``（6.25 刻印）。
結構驗證見 ``skillgen``。"""

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
    "flanked",
    "from_behind",
    "self_concealed",
    "on_own_rune",
    "target_collided",
    "wielding_weapon",
)
"""引擎實作的 16 種條件（``trpg.engine.skills.conditions``），資料檔必須全部定義。"""

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
type Origin = Literal["builtin", "level_up", "drop", "crafted", "taught", "tome", "workshop"]
"""技能的來源；``workshop``：技能工坊（Phase 3F-1，開發工具）做的技能。"""

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
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）：中性描述，不含世界觀名詞、階段編號與欄位名。"""

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


class ShapeCells(ContentModel):
    """形狀影響的格子數（純幾何，不看地圖上的牆壁；區域預算 ``zone`` 用，Phase 3E-1）。

    ``param`` 為 ``None`` 時固定 ``base`` 格；否則依參數值查 ``by_value``（涵蓋參數的整個範圍）。
    數字必須與 ``trpg.engine.skills.shapes`` 的幾何一致（``tests/engine/test_shape_cell_counts.py``
    在空地圖上逐一比對）。
    """

    base: int = Field(default=1, ge=1)
    param: str | None = None
    by_value: dict[int, int] | None = None

    @model_validator(mode="after")
    def _check(self) -> ShapeCells:
        if (self.param is None) != (self.by_value is None):
            raise ValueError("cell_count 的 param 與 by_value 必須一起指定")
        if self.by_value is not None and any(v < 1 for v in self.by_value.values()):
            raise ValueError("cell_count 的 by_value 格數必須 ≥ 1")
        return self

    def count_for(self, values: dict[str, int | str]) -> int:
        """``values`` 是技能形狀已填的參數；參數缺少或表格沒有該值時拋出 :class:`ValueError`。"""
        if self.param is None or self.by_value is None:
            return self.base
        raw = values.get(self.param)
        if not isinstance(raw, int) or raw not in self.by_value:
            raise ValueError(f"cell_count 沒有參數 {self.param} = {raw!r} 的格數")
        return self.by_value[raw]


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
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）。"""
    params: dict[str, ParamDef] = Field(default_factory=dict)
    min_rarity: SkillRarity = "common"
    budget: ShapeBudget = Field(default_factory=ShapeBudget)
    cell_count: ShapeCells | None = None
    """影響的格子數（沒有固定格數的形狀，例如連鎖，為 ``None``）。"""

    @model_validator(mode="after")
    def _check_cells(self) -> ShapeDef:
        cells = self.cell_count
        if cells is None or cells.param is None:
            return self
        spec = self.params.get(cells.param)
        if spec is None:
            raise ValueError(f"形狀 {self.id}：cell_count.param {cells.param!r} 不是這個形狀的參數")
        assert cells.by_value is not None
        missing = [v for v in range(spec.min, spec.max + 1) if v not in cells.by_value]
        if missing:
            raise ValueError(f"形狀 {self.id}：cell_count.by_value 缺少參數值 {missing}")
        return self

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


SHAPE_ROLES: tuple[str, ...] = (
    "followup",
    "on_kill_second",
    "pierce",
    "shape_to",
    "zone_caster",
    "zone_moving",
)
"""``skill_shapes.yaml`` 的 ``shape_roles`` 必須有的用途。"""
SHAPE_TO_VALUES: tuple[str, ...] = shape_role("shape_to")
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
    shape_roles: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """形狀的用途清單（Phase 3E-2f）：鍵必須是 :data:`SHAPE_ROLES`，值是存在的形狀 ID。"""

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
        self._check_roles(ids)
        return self

    def _check_roles(self, ids: set[str]) -> None:
        if not self.shape_roles:
            return
        unknown_roles = sorted(set(self.shape_roles) - set(SHAPE_ROLES))
        missing_roles = [r for r in SHAPE_ROLES if r not in self.shape_roles]
        if unknown_roles or missing_roles:
            raise ValueError(
                f"shape_roles 的用途必須是 {'、'.join(SHAPE_ROLES)}"
                f"（未知：{unknown_roles or '無'}；缺少：{missing_roles or '無'}）"
            )
        for role, role_ids in sorted(self.shape_roles.items()):
            bad = sorted(set(role_ids) - ids)
            if bad or not role_ids:
                raise ValueError(
                    f"shape_roles.{role}：形狀必須存在且至少一個（未知：{bad or '無'}）"
                )

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


class RequiredWhen(ContentModel):
    """參數「依情況才必填」的條件（Phase 4-L3，取代原本寫死在驗證器裡的 ``_filled_by_category``）。

    只能和 ``required: true`` 並用，且恰好填一種：``category`` ＝ 只有技能類別是這個才必填
    （例如武器技的傷害骰來自武器，法術技才要填）；``unless_filled`` ＝ 同一技能內同類型的效果
    只要有任何一個填了指定的另一個參數，這個參數就不必填（例如符文填了標籤就可以省略元素）。
    """

    category: SkillCategory | None = None
    unless_filled: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _one(self) -> RequiredWhen:
        if (self.category is None) == (self.unless_filled is None):
            raise ValueError("required_when 必須恰好填 category 或 unless_filled 其中一種")
        return self

    def applies(self, *, category: str, sibling_filled: Callable[[str], bool]) -> bool:
        """條件成立（＝這個參數必填）。"""
        if self.category is not None:
            return category == self.category
        assert self.unless_filled is not None
        return not sibling_filled(self.unless_filled)


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
        "skill",
        "on_hit",
        "summon",
        "summon_trait",
        "infusion",
        "anchor",
        "zone_when",
        "rule_change",
        "scaling",
        "count",
        "landing",
        "scope",
        "weapon",
    ]
    required: bool = False
    show_when: dict[str, str] | None = None
    """工坊的條件顯示（3-48c）：同一個原語的另一個參數（鍵）填了指定的值（值）才顯示這個參數
    （例：持續區域的 ``speed`` 只在 ``anchor: moving`` 時有意義）。只影響畫面，不影響驗證。"""
    required_when: RequiredWhen | None = None
    """``required: true`` 時，只在條件成立才必填（``None`` ＝ 一律必填）。"""
    min: int | None = None
    max: int | None = None
    allowed_skeletons: tuple[str, ...] | None = None
    """只能用在這些骨架（``None`` ＝ 不限；``split_heal``，Phase 3E-2f）。"""
    true_only: bool = False
    """``type: bool`` 的參數只能填 ``true``（不啟用就省略；``explode``、``split_heal``，4-L5c）。
    驗證器與 LLM 提議模型讀同一份資料。"""
    description_zh: str = ""
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）：中性描述，不含世界觀名詞、階段編號與欄位名；
    ``description_zh`` 是給開發者的。出貨的資料一律要寫（``tests/content/test_llm_hint.py``）。"""

    @model_validator(mode="after")
    def _check_required_when(self) -> PrimitiveParam:
        if self.required_when is not None and not self.required:
            raise ValueError("required_when 必須搭配 required: true")
        return self


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
      ``obstacle`` ``base_points`` × ``obstacle_duration_permille``（依 ``duration``；省略＝永久，
      Phase 3-11）、
      ``consume_status`` ``then`` 的點數 × 期望倍率 × 濺射 × 「需要先有狀態」折扣（3C-3b）、
      ``consume_stack`` 同技能傷害點數 × 期望消耗層數 × ``per_stack_permille``（2E-3）、
      ``hurl_object`` 骰子平均 × 「需要附近有物件」折扣（＋擊倒點數，3C-5a）、
      ``charge_through`` （骰子平均 ＋ on_hit 點數）× 預期被撞到的敵人數（3D-2c）、
      ``summon`` 召喚物每輪預估傷害 × 持續輪數 × ``summon_round_value_permille``（3D-4a）、
      ``zone`` 區域效果點數 × 預估觸發次數（格數 × 輪數 × 係數，3D-5）、
      ``gamble`` 成功率 × win 的點數 ＋ 失敗率 × lose 的點數（期望值，3D-7a）、
      ``revive`` 基礎點數 ＋ 回復比例 × 係數（3D-8b）、
      ``delayed_damage`` 骰子平均 × 預期波及人數（3D-8b）、
      ``grant_skill`` 被給技能的總點數 × 預期使用次數（3D-8c）、
      ``inscribe`` ``base_points`` × ``inscribe_duration_permille``（依 ``duration``，3-23）、
      ``detonate_runes`` 骰子平均 × ``detonate_runes_permille``（需要先刻印的折扣，3-23）、
      ``dice_average`` 骰子平均值、``damage`` 法術為骰子平均值而武器為倍率 × 基準武器傷害、
      ``status``／``surface`` 為該狀態或表面的 ``budget_points`` × 持續 ÷ 預設持續。
      ``None`` 表示無法計算預算（驗證器會拒絕）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3；與 ``description_zh``、``player_description`` 分開）。"""
    player_description: str | None = Field(default=None, min_length=1)
    """給玩家看的一句話說明（Phase 3E-2e）：不含階段編號與程式識別字；glossary API 與部件說明框
    用它，省略時退回 ``description_zh``。出貨的原語一律要寫
    （``tests/content/test_player_description.py``）。"""
    category: Literal["numeric", "structural", "rule_rewrite", "rule_change"]
    min_rarity: SkillRarity = "common"
    harmful: bool
    acts_on: Literal["unit", "tile", "caster"] = "unit"
    allowed_shapes: tuple[str, ...] | None = None
    forbid_affects: tuple[Affects, ...] = ()
    position: Literal["first", "last"] | None = None
    """組合規則（Phase 4-L5b）：必須是技能的第一個（``first``）或最後一個（``last``）效果。"""
    sole_effect: bool = False
    """組合規則：必須是技能唯一的效果。"""
    others_affect: Literal["self"] | None = None
    """組合規則：同一技能的其他效果必須明寫這個 ``affects``（``self``：只作用在施放者）。"""
    nested_core: bool = False
    """這個原語的內容就是一組巢狀效果（消耗狀態後的效果、賭注的贏／輸分支、持續區域的效果）：
    工坊在 3-48d 起開放（子效果的選項見 ``trpg.skillgen.option_nested``）。"""
    max_per_skill: int | None = Field(default=None, ge=1)
    """組合規則：一個技能最多幾個這個效果。"""
    active_only: bool = False
    """組合規則：只能用在主動技能（``kind: active``）。

    以上五個欄位與 ``allowed_shapes`` 是「原語對整招技能的組合規則」的唯一來源：
    ``SkillDef`` 的驗證器（:func:`composition_rules`）與 LLM 提議模型（``trpg.skillgen.proposal``）
    都讀它們。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    """這個原語固定施加的狀態 ID（``statuses.yaml``；Phase 3E-2f）。引擎常數
    :data:`CHEAT_DEATH_STATUS`、:data:`REDIRECT_STATUS`、:data:`TIME_BOMB` 從這裡讀取。"""
    lookup_by_skill_id: bool = False
    """事後以技能 ID 查表（``skill_def(id)``）取回本原語的設定（Phase 3E-2a）：查到的是基礎型態，
    所以帶變奏的技能（基礎或任一變奏型態）不能含它——變奏的替換不會生效，甚至找不到效果而崩潰。"""
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
            "obstacle",
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
            "revive",
            "delayed_damage",
            "grant_skill",
            "inscribe",
            "detonate_runes",
            "sacrifice_summon",
        ]
        | None
    ) = None
    base_points: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_budget(self) -> PrimitiveDef:
        needs_points = ("fixed", "per_distance", "per_amount", "obstacle", "inscribe")
        if self.budget_basis in needs_points and self.base_points is None:
            raise ValueError(f"原語 {self.id}：budget_basis {self.budget_basis} 必須填 base_points")
        for name, spec in self.params.items():
            unknown = sorted(set(spec.allowed_skeletons or ()) - set(SKELETON_IDS))
            if unknown:
                raise ValueError(
                    f"原語 {self.id}.{name}：allowed_skeletons 有未知的骨架：{', '.join(unknown)}"
                )
        return self

    def summary(self) -> str:
        return self.name_zh


class PrimitiveTable(ContentModel):
    """``content/skill_primitives.yaml``。"""

    primitives: tuple[PrimitiveDef, ...] = Field(min_length=1)
    mechanic_statuses: dict[str, str] = Field(default_factory=dict)
    """不是由原語施加、由技能機制使用的狀態 ID（``charging``；Phase 3E-2f）。"""

    @model_validator(mode="after")
    def _check(self) -> PrimitiveTable:
        _unique((p.id for p in self.primitives), "原語")
        return self

    def status_refs(self) -> set[str]:
        """原語與技能機制固定使用的狀態 ID（必須存在於 ``statuses.yaml``）。"""
        return {p.status for p in self.primitives if p.status is not None} | set(
            self.mechanic_statuses.values()
        )

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
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）。"""
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
    """``cast_tag_this_turn`` 專用（Phase 3D-1）：本回合施放過的技能標籤；``on_own_rune`` 的符文標籤
    篩選（Phase 3-23）。"""
    element: Element | None = None
    """``on_own_rune`` 專用（Phase 3-23）：符文元素篩選（省略＝任何符文）。"""
    weapon: str | None = Field(default=None, pattern=ID_PATTERN)
    """``wielding_weapon`` 專用（Phase 3I-5，6.10 #50）：要手持的武器或副手 ID
    （``weapons.yaml``、``offhands.yaml``）。"""

    def param_values(self) -> dict[str, Any]:
        """已填寫的參數（依名稱排序）。"""
        names = ("element", "permille", "status", "surface", "tag", "weapon")
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}


_PLAIN_CONDITION_TEXT = {
    "moved_this_turn": "本回合移動過",
    "adjacent_ally": "身旁有友方",
    "target_isolated": "目標身邊沒有友方",
    "flanked": "夾擊（目標的對面有友方）",
    "from_behind": "背刺（站在目標背後）",
    "self_concealed": "潛行偷襲（自身隱蔽中）",
    "first_round": "第一輪",
    "target_collided": "目標本回合受過撞擊",
}
"""沒有參數的條件的一句話（Phase 3D-1）。"""


def _rune_condition_text(
    condition: ConditionSpec, tag_runes: Mapping[str, str] | None = None
) -> str:
    """``on_own_rune`` 的一句話（Phase 3-23）：可帶元素或標籤篩選。"""
    if condition.element is None and condition.tag is None:
        return "目標站在自己的符文上"
    return f"目標站在自己的{rune_name(condition.element, condition.tag, tag_runes)}上"


def _unknown_tag(_tag: str) -> str:
    return UNKNOWN_TAG_TEXT


def condition_text(
    condition: ConditionSpec,
    *,
    status_name: Callable[[str], str] = str,
    surface_name: Callable[[Surface], str] = lambda surface: surface.value,
    tag_name: Callable[[str], str] = _unknown_tag,
    tag_runes: Mapping[str, str] | None = None,
    weapon_name: Callable[[str], str] = str,
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
        return f"本回合已施放過帶「{tag_name(condition.tag)}」標籤的技能"
    plain = _PLAIN_CONDITION_TEXT.get(kind)
    if plain is None and kind == "on_own_rune":
        plain = _rune_condition_text(condition, tag_runes)
    if plain is None and kind == "wielding_weapon" and condition.weapon is not None:
        plain = f"手持{weapon_name(condition.weapon)}時"  # 3I-5
    if plain is None and kind == "wielding_weapon":
        plain = "手持指定的武器時"  # 3-55：沒帶武器 ID 時也不露出英文代號
    return plain or kind


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
    multiplier_permille: int | None = None
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
    splash: int | None = None
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
    landing: Literal["choose", "behind"] | None = None
    """``shadowstep`` 專用（Phase 3D-8d）：``choose`` 一般瞬步（形狀 ``unit_then_tile``，玩家自選
    目標相鄰的空格）；``behind`` 瞬步背刺類（形狀 ``single``，固定落在目標的背後格）。"""
    unit: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3D-4a）：召喚物範本 ID（``content/units/summons/``）。"""
    count: int | Literal["all"] | None = Field(default=None)
    """``summon`` 專用（Phase 3D-4a）：一次召喚的數量（1；數量型分歧進化 3-33f2 可為 2，此時必須
    填 ``power_permille``）。``dispel`` 專用（Phase 3D-8a）：驅散的增益個數（1）或
    ``all``（全部）。"""
    power_permille: int | None = None
    """``summon`` 專用（Phase 3-33f2，數量型分歧進化）：每隻召喚物的最大 HP 與傷害只有一般的這麼多
    ‰（例如 600 ＝ 60%）；一次召喚 2 隻（``count: 2``）時必填，只有一隻時不可填。"""
    max_hp_permille: int | None = None
    """``summon`` 專用（Phase 3-33f2，加深分歧進化）：召喚物的最大 HP 多 ‰（召喚時結算，在成長與
    修正規則之後相乘）。"""
    trait: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3-33f2，加深分歧進化）：召喚物的小特性（``core.yaml`` 的
    ``summon_traits``）。"""
    infusion: str | None = Field(default=None, pattern=ID_PATTERN)
    """``summon`` 專用（Phase 3-33f2，橋接分歧進化）：召喚物固有的第二個灌注關鍵字
    （``core.yaml`` 的 ``summon_infusions``）；與施放時選的灌注、範本固有的灌注並存。"""
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
    lifesteal_permille: int | None = None
    """``damage`` 專用（Phase 3D-8a，6.18 A）：吸血——施放者回復「這個效果實際造成的傷害（扣掉護盾
    吸收）」的 n‰（無條件捨去，不超過最大 HP）。只有技能自己的傷害效果可以用。"""
    spread: int | None = Field(default=None, ge=1, le=2)
    """``damage`` 專用（Phase 3-54b，06 6.33）：風元素傷害的元素擴散格數（1 或 2；省略＝
    ``core.wind.spread_distance``，預設 1）。只有 ``element: wind`` 的技能自己的傷害效果可以填；
    2 格的預算較貴（``wind_spread_permille``）。"""
    split_heal: bool | None = None
    """``damage`` 專用（Phase 3D-8a，6.18 B）：聖光雙效——必須搭配 ``affects: all``；敵方依一般命中
    判定受到傷害、友方（含施放者）不擲命中而改為治療同樣的骰值（骰一次）。只能用在 ``aura``、
    ``area`` 骨架的法術技。"""
    skill: str | None = Field(default=None, pattern=SKILL_ID_PATTERN)
    """``grant_skill`` 專用（Phase 3D-8c，6.20）：暫時給目標的技能 ID（``content/skills/``）；必須是
    一般的主動技能（不是傳說、不含改寫規則型原語、不是 ``grant_skill`` 技能；跨檔案檢查）。"""
    hp_permille: int | None = Field(default=None, ge=1, le=_PERMILLE)
    """``revive`` 專用（Phase 3D-8b，6.18 C）：被復活的單位站起來時的 HP（最大 HP 的 n‰，至少
    1）。"""
    rounds: int | None = None
    """``delayed_damage`` 專用（Phase 3D-8b，6.18 H）：定時炸彈的倒數輪數（每次環境回合 −1，歸零時
    爆炸）。"""
    radius: int | None = None
    """``delayed_damage`` 專用：爆炸半徑（曼哈頓距離；0 只波及目標自己）。"""
    scope: Literal["target_cell"] | None = None
    """``detonate_runes`` 專用（Phase 3-31，修正規則 ``on_hit_effects`` 與普攻詞條）：
    ``target_cell`` 只引爆被命中目標所在的那 1 格上自己的符文。"""
    on_kill: tuple[EffectSpec, ...] | None = None
    """``damage`` 專用（Phase 3D-8b，6.18 F）：這個傷害效果讓敵人倒下時才結算的效果（1–2 個，類型見
    :data:`ON_KILL_TYPES`，對象一律是施放者）；同一個效果讓一個以上的敵人倒下只結算一次。只有技能
    自己的傷害效果可以用（不能放進賭注分支、失手反噬、``then``）。"""
    effects: tuple[EffectSpec, ...] | None = None
    """``zone`` 專用（Phase 3D-5）：區域結算的效果（1–2 個，只能用 :data:`ZONE_EFFECT_TYPES`，
    不可自帶 ``affects``／``condition``；對象由區域的 ``affects`` 決定）。"""
    condition: ConditionSpec | None = None

    @model_validator(mode="after")
    def _check_yaml_ranges(self) -> EffectSpec:
        """:data:`YAML_RANGED_FIELDS` 的範圍取自 ``skill_primitives.yaml`` 的 ``min``／``max``
        （Phase 3E-2f，唯一來源）；其他整數欄位的細緻範圍由跨檔案驗證（:func:`skill_problems`）
        檢查。不在該檔的效果類型（``refund_ap`` 等）沒有範圍。"""
        for name, spec in _yaml_ranged_params().get(self.type, {}).items():
            value = getattr(self, name, None)
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if (spec.min is not None and value < spec.min) or (
                spec.max is not None and value > spec.max
            ):
                raise ValueError(
                    f"效果 {self.type} 的 {name} 必須在 {spec.min}–{spec.max}，收到 {value}"
                )
        return self

    def param_values(self) -> dict[str, Any]:
        """已填寫的原語參數（不含 ``type``、``affects``、``condition``；欄位清單由
        :data:`EFFECT_PARAM_FIELDS` 從 model 推導，依名稱排序）。"""
        return {n: getattr(self, n) for n in EFFECT_PARAM_FIELDS if getattr(self, n) is not None}


YAML_RANGED_FIELDS = frozenset(
    {
        "lifesteal_permille",
        "max_hp_permille",
        "multiplier_permille",
        "power_permille",
        "radius",
        "rounds",
        "splash",
    }
)
"""``EffectSpec`` 中只宣告型別、範圍完全取自 ``skill_primitives.yaml`` 的整數欄位（建構時就檢查）。
其餘整數欄位仍有較寬的 schema 範圍（健全性檢查）或只在跨檔案驗證時檢查細緻範圍。"""


@cache
def _ranged_params_of(path: Path) -> dict[str, dict[str, PrimitiveParam]]:
    if not path.is_file():  # 沒有這個檔的內容資料夾由載入器自己報錯
        return {}
    table = load_content_file(path, PrimitiveTable)
    return {
        p.id: {
            n: s
            for n, s in p.params.items()
            if n in YAML_RANGED_FIELDS
            and s.type == "int"
            and (s.min is not None or s.max is not None)
        }
        for p in table.primitives
    }


def _yaml_ranged_params() -> dict[str, dict[str, PrimitiveParam]]:
    """各原語「範圍只在 YAML」的整數參數（內容資料夾見
    :func:`~trpg.content.loader.default_content_dir`，每個路徑只讀一次）。"""
    return _ranged_params_of(default_content_dir() / "skill_primitives.yaml")


@dataclass(frozen=True, slots=True)
class CompositionRule:
    """一個原語對整招技能的組合規則（Phase 4-L5b；欄位意義見 :class:`PrimitiveDef`）。"""

    primitive: str
    allowed_shapes: tuple[str, ...] | None = None
    position: Literal["first", "last"] | None = None
    sole_effect: bool = False
    others_affect: Literal["self"] | None = None
    max_per_skill: int | None = None
    active_only: bool = False

    @classmethod
    def of(cls, primitive: PrimitiveDef) -> CompositionRule:
        return cls(
            primitive=primitive.id,
            allowed_shapes=primitive.allowed_shapes,
            position=primitive.position,
            sole_effect=primitive.sole_effect,
            others_affect=primitive.others_affect,
            max_per_skill=primitive.max_per_skill,
            active_only=primitive.active_only,
        )

    @property
    def cross_effect(self) -> bool:
        """有牽涉其他效果的規則（位置、唯一效果、其他效果的對象）。"""
        return self.position is not None or self.sole_effect or self.others_affect is not None


@cache
def _composition_of(path: Path) -> dict[str, CompositionRule]:
    if not path.is_file():  # 沒有這個檔的內容資料夾由載入器自己報錯
        return {}
    table = load_content_file(path, PrimitiveTable)
    return {p.id: CompositionRule.of(p) for p in table.primitives}


def composition_rules() -> dict[str, CompositionRule]:
    """各原語的組合規則（``skill_primitives.yaml``，唯一來源；每個路徑只讀一次）。"""
    return _composition_of(default_content_dir() / "skill_primitives.yaml")


@cache
def _true_only_of(path: Path) -> dict[str, frozenset[str]]:
    if not path.is_file():
        return {}
    table = load_content_file(path, PrimitiveTable)
    out = {p.id: frozenset(n for n, s in p.params.items() if s.true_only) for p in table.primitives}
    return {k: v for k, v in out.items() if v}


def true_only_params() -> dict[str, frozenset[str]]:
    """原語 ID → 只能填 ``true`` 的參數名稱（``skill_primitives.yaml`` 的 ``true_only``）。"""
    return _true_only_of(default_content_dir() / "skill_primitives.yaml")


def composition_shapes(primitive: str) -> tuple[str, ...]:
    """原語 YAML 的 ``allowed_shapes``（``SkillDef`` 結構檢查用；沒有限制時為空 tuple）。"""
    rule = composition_rules().get(primitive)
    return () if rule is None or rule.allowed_shapes is None else rule.allowed_shapes


class SkillRuleError(ValueError):
    """``SkillDef`` 結構檢查的錯誤，帶出錯的 JSON 路徑（Phase 4-L5b：給 LLM 的回饋可定位）。

    pydantic 會把它包進 ``value_error``，原本的例外留在錯誤的 ``ctx["error"]``。"""

    def __init__(self, message: str, *, path: str = "", code: str = "") -> None:
        super().__init__(message)
        self.path = path
        self.code = (
            code  # 穩定的錯誤代碼（Phase 4-L5c，例 combo.position）；空字串＝沿用 value_error
        )


def _check_composition(kind: str, effects: tuple[EffectSpec, ...]) -> None:
    """技能頂層效果的組合規則（Phase 4-L5b；資料見 :func:`composition_rules`）：只能用在主動技能、
    每技能數量上限、唯一的效果、第一個／最後一個、其他效果的對象。形狀限制（``allowed_shapes``）
    由各原語自己的檢查與跨檔案驗證處理（:func:`skill_problems`）。"""
    rules = composition_rules()
    types = [e.type for e in effects]
    used = [rules[t] for t in dict.fromkeys(types) if t in rules]
    for rule in used:
        if rule.active_only and kind != "active":
            raise SkillRuleError(
                f"{rule.primitive} 只能用在主動技能，收到 kind: {kind}",
                path="kind",
                code="combo.active_only",
            )
    moves = [t for t in types if t in SELF_MOVES]
    if len(moves) > 1 and any(t != "teleport" for t in moves):  # 跨原語的群組規則（留在程式）
        raise SkillRuleError(
            f"一個技能最多一個改變自身位置的原語，收到 {'、'.join(moves)}",
            path="effects",
            code="combo.max_per_skill",
        )
    for rule in used:
        _check_rule(rule, effects, types)


def _check_rule(rule: CompositionRule, effects: tuple[EffectSpec, ...], types: list[str]) -> None:
    name = rule.primitive
    where = [i for i, t in enumerate(types) if t == name]
    if rule.max_per_skill is not None and len(where) > rule.max_per_skill:
        count = "一個" if rule.max_per_skill == 1 else f" {rule.max_per_skill} 個"
        raise SkillRuleError(
            f"一個技能最多{count} {name} 效果",
            path=f"effects[{where[rule.max_per_skill]}]",
            code="combo.max_per_skill",
        )
    if rule.sole_effect and len(types) != 1:
        raise SkillRuleError(
            f"{name} 必須是技能唯一的效果", path="effects", code="combo.sole_effect"
        )
    if rule.position == "first" and types[0] != name:
        raise SkillRuleError(
            f"{name} 必須是技能的第一個效果（一律最先結算）",
            path=f"effects[{where[0]}]",
            code="combo.position",
        )
    if rule.position == "last" and types[-1] != name:
        raise SkillRuleError(
            f"{name} 必須是技能的最後一個效果（一律最後結算）",
            path=f"effects[{where[-1]}]",
            code="combo.position",
        )
    if rule.others_affect is not None:
        for index, effect in enumerate(effects):
            if effect.type != name and effect.affects != rule.others_affect:
                raise SkillRuleError(
                    f"{name} 以外的效果必須明寫 affects: {rule.others_affect}（只作用在施放者）",
                    path=f"effects[{index}].affects",
                    code="combo.others_affect",
                )


EFFECT_NON_PARAM_FIELDS = frozenset({"type", "affects", "condition"})
"""``EffectSpec`` 中不是原語參數的欄位（其餘欄位一律視為參數，新增欄位不必另外登記）。"""

EFFECT_PARAM_FIELDS = tuple(sorted(set(EffectSpec.model_fields) - EFFECT_NON_PARAM_FIELDS))
"""``EffectSpec`` 的原語參數欄位名稱（從 ``model_fields`` 推導）。"""


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
    stamina: int = Field(default=0, ge=0)
    """耐力代價（Phase 3H-2，06 6.10）：武器技花耐力、法術技花法力（依類別，``skill_budget.yaml`` 的
    ``cost_resource``；內容庫與產生器檢查）。"""
    cooldown: int | None = Field(default=None, ge=1, le=_MAX_COOLDOWN)
    uses_per_battle: int | None = Field(default=None, ge=1)
    hp_percent: int | None = Field(default=None, ge=1, le=_PERMILLE - 1)
    stacks: int | None = Field(default=None, ge=1)
    """施放前至少要有幾層（Phase 2E-3）：對應技能裡 ``owner: self`` 的 ``consume_stack`` 的層數；
    不足時不可施放。需求本身不消耗層數（消耗由 ``consume_stack`` 負責）。"""
    self_status: SelfStatusCost | None = None
    """施放後施放者自己獲得的狀態（Phase 2H-1）；只有主動技能可以使用。"""
    overdraft: int | None = Field(default=None, ge=1, le=1)
    """透支（Phase 3-50，06 6.5）：施放後自己下一個回合少這麼多 AP（目前一招最多 1 AP，固定折抵見
    ``skill_budget.yaml`` 的 ``allowance.overdraft_permille``）；只有主動技能可以使用。"""
    source: int | None = Field(default=None, ge=1, le=2)
    """花費的源力（Phase 3C-4a，1 或 2）：只有傳說技能可以、而且必須有；源力不足時不能施放。"""
    on_miss: tuple[EffectSpec, ...] = ()
    """失手反噬（Phase 3D-7a，6.17 C）：攻擊沒命中（含自然 1）時對施放者結算的效果（至多 2 個，
    類型見 :data:`BACKLASH_TYPES`，對象只能是施放者自己）；命中則不結算。"""


class FollowupSpec(ContentModel):
    """複合技能的第二段（Phase 3F-3a，``docs/design/06-技能.md`` 6.23）：自己的骨架、形狀、效果與
    條件，照該骨架的規則檢查。``when`` 決定第二段何時、以哪裡為原點結算（:data:`FollowupWhen`）：

    - ``after_move``：施放者真的移動到位移段的落點時，以落點為原點結算；
    - ``after_action``（3F-4a）：第一段結算完、施放者還站著就結算（自身位移，從目前位置選落點）；
    - ``after_gather``（3F-4a）：第一段把敵人拉向聚集點，第二段以聚集點為中心結算；
    - ``on_kill``（3F-4a）：第一段讓敵人倒下才結算（從施放者的位置選目標）；
    - ``on_hit``（3F-4a）：第一段命中敵人才結算（自動對命中的同一個目標）；
    - ``delayed``（3F-4b）：延遲段——施放後施放者身上帶著「蓄力」狀態，``release`` 成立時以施放者
      當下的位置為中心結算（``next_turn``：施放者下回合開始時；``attacked``：到施放者下回合開始
      之前被敵人攻擊時）。"""

    when: FollowupWhen = "after_move"
    skeleton: str
    shape: ShapeSpec
    effects: tuple[EffectSpec, ...] = Field(min_length=1)
    condition: ConditionSpec | None = None
    release: DelayedRelease | None = None
    """延遲段（``when: delayed``，Phase 3F-4b）何時釋放；其他種類必須省略。"""

    @field_validator("skeleton")
    @classmethod
    def _skeleton(cls, value: str) -> str:
        if value not in SKELETON_IDS:
            raise ValueError(f"未知的骨架 {value!r}（可用：{', '.join(SKELETON_IDS)}）")
        return value


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
ON_SUMMON_DOWNED = "on_summon_downed"
"""召喚物倒下時（Phase 3-33f2）：只給裝備詞條用的觸發時機，效果是以倒下的召喚物為中心的爆炸或治療
（``sacrifice_summon`` 效果）。"""
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
CHEAT_DEATH_STATUS = primitive_status("cheat_death")
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
GRANT_SKILL = "grant_skill"
MAX_GRANT_DURATION = 4
"""Phase 3D-8c 的暫時獲得技能原語 ID（6.20）：目標的技能列暫時多出 ``skill``，``duration`` 輪後
（在目標自己的回合結束時倒數）消失。持續輪數上限。"""
REVIVE = "revive"
DELAYED_DAMAGE = "delayed_damage"
TIME_BOMB = primitive_status("delayed_damage")
"""Phase 3D-8b 的原語 ID（6.18 C、H）：復活倒下的友方、在目標身上附加定時炸彈（狀態 ``time_bomb``，
``statuses.yaml``；倒數與爆炸見 ``trpg.engine.bombs``）。"""
REFUND_AP = "refund_ap"
REFUND_COOLDOWN = "refund_cooldown"
ON_KILL_TYPES: tuple[str, ...] = (REFUND_AP, REFUND_COOLDOWN, "heal", "shield", "apply_status")
"""技能內的擊殺時效果（``on_kill``，Phase 3D-8b，6.18 F）可用的效果類型：``refund_ap``（返還 AP）與
``refund_cooldown``（本技能冷卻歸零）是只能放在 ``on_kill`` 裡的專用效果（不是
``skill_primitives.yaml`` 的原語，也不屬於改寫規則型）；其餘依一般原語結算，對象一律是施放者。"""
MAX_ON_KILL_EFFECTS = 2
MAX_REFUND_AP = 2
"""``on_kill`` 的效果個數上限，與 ``refund_ap`` 一次最多返還的 AP。"""
SPLIT_SKELETONS: tuple[str, ...] = split_heal_skeletons()
"""``split_heal``（聖光雙效）可以使用的骨架。"""
DASH = "dash"
LEAP = "leap"
SWAP = "swap"
"""Phase 3D-2 的自身位移原語 ID（6.16 A）。"""
SHADOWSTEP = "shadowstep"
"""Phase 3D-8d 的瞬步原語 ID（6.21）：以敵方單位為目標，瞬間出現在他相鄰的格子；``landing:
choose`` 搭配形狀 ``unit_then_tile``、``landing: behind`` 搭配形狀 ``single``。"""
SHADOWSTEP_SHAPES: dict[str, str] = {"choose": "unit_then_tile", "behind": "single"}
TELEPORT_TARGET = "teleport_target"
SWAP_ANY = "swap_any"
"""Phase 3D-2b 的位移他人原語 ID（6.19）：傳送他人（形狀 ``unit_then_tile``）、任意兩者互換
（形狀 ``unit_pair``）。"""
PAIR_MOVES: tuple[str, ...] = (TELEPORT_TARGET, SWAP_ANY)
PAIR_SHAPES: dict[str, str] = {TELEPORT_TARGET: "unit_then_tile", SWAP_ANY: "unit_pair"}
SHAPE_REQUIRED_PRIMITIVES: dict[str, tuple[str, ...]] = {
    "unit_then_tile": (TELEPORT_TARGET, SHADOWSTEP),
    "unit_pair": (SWAP_ANY,),
    "object_then_tile": ("hurl_object",),
}
"""形狀這一側的組合規則（Phase 4-L5b 整理；驗證見 ``SkillDef._check_pair_moves``、
``_check_hurl_object``）：這些形狀必須搭配其中一個原語（``shadowstep`` 要 ``landing: choose``）。
LLM 提議模型的一般型態不開放這些形狀。"""
CHARGE_THROUGH = "charge_through"
"""Phase 3D-2c 的直線衝撞原語 ID（6.22）：形狀 ``ground_tile`` 選終點格，沿直線衝過去。"""
SUMMON = "summon"
MAX_SUMMON_COUNT = 2
"""一次召喚的數量上限（Phase 3-33f2，數量型分歧進化：2 隻各 ``power_permille``）。"""
"""Phase 3D-4a 的召喚原語 ID（6.16 B）：在 ``ground_tile`` 選的空格召喚 ``unit`` 範本。"""
RULE_CHANGE = "rule_change"
"""規則改變（Phase 3D-6）：引用 ``content/rule_changes.yaml`` 的一條規則，以 ``activation``
啟動。"""
INSCRIBE = "inscribe"
"""Phase 3-23 的刻印原語 ID（6.25）：在影響格留下施放者專屬的符文（``element`` 或 ``tag``）。"""
DETONATE_RUNES = "detonate_runes"
"""Phase 3-23 的消耗型原語 ID（6.25）：引爆影響格內施放者自己的符文，每格對該格單位一次小傷害。"""
RUNE_BOTH_MESSAGE = "不能同時刻下符文又引爆符文（要靠兩件東西搭配，不是單一被動或單一裝備自己完成）"
BLOW_SURFACE = "blow_surface"
"""Phase 3-54a 的吹送原語 ID（06 6.33，#56）：把影響格上的表面整片往風向平移 ``distance`` 格。"""
SACRIFICE_SUMMON = "sacrifice_summon"
"""Phase 3-24c 的獻祭召喚物原語 ID（6.27.2）：移除自己的一個召喚物，在它的位置爆炸或治療。"""
ZONE = "zone"
"""Phase 3D-5 的持續區域原語 ID（6.16 G）：在格子上建立持續 ``duration`` 輪的區域。"""
ZONE_EFFECT_TYPES: tuple[str, ...] = ("damage", "heal", "shield", "apply_status")
"""``zone`` 的 ``effects`` 可用的原語（Phase 3D-5；與 ``consume_status`` 的 ``then`` 相同）。"""
ZONE_MOVING_SHAPES: tuple[str, ...] = shape_role("zone_moving")
"""``anchor: moving`` 可用的形狀（選方向的形狀；區域沿施放方向前進）。"""
ZONE_CASTER_SHAPES: tuple[str, ...] = shape_role("zone_caster")
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
SELF_MOVES: tuple[str, ...] = (DASH, LEAP, SWAP, CHARGE_THROUGH, SHADOWSTEP, "teleport")
"""改變施放者位置的原語；一個技能最多一個。"""
COMPOSITE_MOVES: tuple[str, ...] = ("teleport", LEAP, DASH, CHARGE_THROUGH, SHADOWSTEP)
"""複合技能（Phase 3F-3a，6.23 基本型「位移 → 動作」）的位移段可用的施放者自身位移原語。"""
FOLLOWUP_SHAPES: tuple[str, ...] = shape_role("followup")
"""複合技能動作段可用的形狀（Phase 3F-3a）：以落點為原點；``cross``、``square3`` 必須 ``range: 0``
（以落點為中心）。"""
FOLLOWUP_CENTERED: tuple[str, ...] = ("cross", "square3")
FOLLOWUP_FORBIDDEN: tuple[str, ...] = (
    *SELF_MOVES,
    TELEPORT_TARGET,
    SWAP_ANY,
    SUMMON,
    ZONE,
    PLACE_TRAP,
    COPY_SKILL,
    RULE_CHANGE,
    GAMBLE,
    "hurl_object",
)
"""動作段不能用的原語（Phase 3F-3a）：位移（不套娃）、召喚、持續區域、陷阱，以及需要另外選取或改變
整個施放流程的原語（複製技能、規則改變、賭注、投擲物件；保守做法）。"""
type FollowupWhen = Literal[
    "after_move", "after_action", "after_gather", "on_kill", "on_hit", "delayed"
]
"""第二段的時機（6.23）：``after_move`` 位移 → 動作（3F-3a）；``after_action`` 動作 → 位移
（打帶跑）、``after_gather`` 聚集 → 範圍打擊、``on_kill`` 擊殺 → 接下一段、``on_hit`` 命中 →
加碼段（3F-4a）；``delayed`` 延遲段（3F-4b）。"""
type DelayedRelease = Literal["next_turn", "attacked"]
"""延遲段的釋放時機（Phase 3F-4b）：``next_turn`` 施放者下回合開始時；``attacked`` 到施放者下回合
開始之前被敵人攻擊（擲命中，不論是否命中）時——沒被攻擊就在下回合開始時失效。"""
FOLLOWUP_WHEN_VALUES: tuple[str, ...] = (
    "after_move",
    "after_action",
    "after_gather",
    "on_kill",
    "on_hit",
    "delayed",
)
DELAYED_RELEASE_VALUES: tuple[str, ...] = ("next_turn", "attacked")
DELAYED_SHAPES: tuple[str, ...] = ("cross", "square3", "ring")
"""延遲段的形狀（Phase 3F-4b）：以施放者釋放當下的位置為中心（十字、方陣 ``range: 0``）。"""
CHARGING = mechanic_status("charging")
"""延遲段等待期間施放者身上的狀態（Phase 3F-4b；``StatusInstance.skill_id`` 是技能、
``remaining`` 是還要幾回合釋放）。"""
FOLLOWUP_CHOICE_WHENS: tuple[str, ...] = ("after_action", "on_kill")
"""第二段要施放者自己選目標的種類（3F-4a）：結算到第二段時以 ``pending``（``kind: followup``）
詢問；AI 與重播直接在 ``UseSkill.followup_target`` 帶選取。"""
FOLLOWUP_AUTO_WHENS: tuple[str, ...] = ("after_gather", "on_hit")
"""第二段的選取由引擎決定的種類（3F-4a）：聚集點、命中的同一個目標；不能帶 ``followup_target``。"""
COMPOSITE_KIND_ZH: dict[str, str] = {
    "after_move": "位移 → 動作",
    "after_action": "動作 → 位移",
    "after_gather": "聚集 → 範圍打擊",
    "on_kill": "擊殺 → 接下一段",
    "on_hit": "命中 → 加碼段",
    "delayed": "延遲段",
}
"""複合技能種類的中文名稱（6.23）。"""
GATHER_SHAPES: tuple[str, ...] = ("cross", "square3", "ring")
"""聚集段（``after_gather`` 的第一段）的形狀：十字、方陣以選的中心格為聚集點，環形以施放者
為聚集點。"""
ON_KILL_SECOND_SHAPES: tuple[str, ...] = shape_role("on_kill_second")
"""``on_kill`` 第二段的形狀：動作段的形狀，加上跳躍、傳送用的指定格。"""
_FOLLOWUP_CACHE: dict[int, tuple[Any, Any]] = {}
_FOLLOWUP_CACHE_LIMIT = 4096
_VARIANT_CACHE: dict[tuple[int, str], tuple[Any, Any]] = {}
"""變奏型態（:meth:`SkillDef.variant_form`）的快取：以技能物件的 ``id`` 與變奏 ID 為鍵
（值保留原物件，避免 ``id`` 重用時取錯）。"""


def _types(effects: tuple[EffectSpec, ...]) -> str:
    return "、".join(e.type for e in effects)


def _lone_move(effects: tuple[EffectSpec, ...], where: str) -> None:
    """``where`` 只能是一個施放者自身位移原語（:data:`COMPOSITE_MOVES`）。"""
    if len(effects) != 1 or effects[0].type not in COMPOSITE_MOVES:
        raise ValueError(
            f"複合技能的{where}只能有一個施放者自身位移原語（{'、'.join(COMPOSITE_MOVES)}），"
            f"收到 {_types(effects)}"
        )


def _no_forbidden(
    effects: tuple[EffectSpec, ...], where: str, allowed: tuple[str, ...] = ()
) -> None:
    bad = [e.type for e in effects if e.type in FOLLOWUP_FORBIDDEN and e.type not in allowed]
    if bad:
        raise ValueError(
            f"複合技能的{where}不能有位移、召喚、區域、陷阱等原語（不能套娃），"
            f"收到 {'、'.join(bad)}"
        )


def _second_shape(follow: FollowupSpec, shapes: tuple[str, ...]) -> None:
    """第二段的形狀在 ``shapes`` 內；以原點為中心的 ``cross``、``square3`` 必須 ``range: 0``。"""
    if follow.shape.type not in shapes:
        raise ValueError(f"followup 的形狀只能是 {'、'.join(shapes)}，收到 {follow.shape.type}")
    if follow.shape.type in FOLLOWUP_CENTERED and follow.shape.range != 0:
        raise ValueError(
            f"followup 的形狀 {follow.shape.type} 以第二段的原點為中心，range 必須是 0，"
            f"收到 {follow.shape.range}"
        )


def _needs_damage(effects: tuple[EffectSpec, ...], what: str) -> None:
    if not any(e.type == "damage" for e in effects):
        raise ValueError(f"「{what}」的第一段必須有傷害效果（damage），收到 {_types(effects)}")


def _check_after_move(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """位移 → 動作（3F-3a）：第一段是一個自身位移；第二段是以落點為原點的動作。"""
    _lone_move(effects, "位移段")
    _second_shape(f, FOLLOWUP_SHAPES)
    _no_forbidden(f.effects, "動作段")


def _check_after_action(
    effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec
) -> None:
    """動作 → 位移（打帶跑，3F-4a）：第一段是動作；第二段是一個自身位移（形狀照該原語）。"""
    _no_forbidden(effects, "第一段")
    _lone_move(f.effects, "第二段（位移）")


def _check_after_gather(effects: tuple[EffectSpec, ...], shape: ShapeSpec, f: FollowupSpec) -> None:
    """聚集 → 範圍打擊（3F-4a）：第一段只有一個 ``pull``（朝聚集點拉），形狀在
    :data:`GATHER_SHAPES`；第二段以聚集點為中心（``cross``／``square3``，射程與第一段相同，環形為
    0）。"""
    if len(effects) != 1 or effects[0].type != "pull":
        raise ValueError(f"聚集段只能有一個拉扯原語（pull），收到 {_types(effects)}")
    if shape.type not in GATHER_SHAPES:
        raise ValueError(f"聚集段的形狀只能是 {'、'.join(GATHER_SHAPES)}，收到 {shape.type}")
    if f.shape.type not in FOLLOWUP_CENTERED:
        raise ValueError(
            f"聚集後的打擊以聚集點為中心，形狀只能是 {'、'.join(FOLLOWUP_CENTERED)}，"
            f"收到 {f.shape.type}"
        )
    reach = shape.range if shape.type in FOLLOWUP_CENTERED else 0
    if f.shape.range != reach:
        raise ValueError(
            f"聚集後的打擊以聚集點為中心，range 必須與聚集段相同（{reach}），收到 {f.shape.range}"
        )
    _no_forbidden(f.effects, "第二段")


def _check_on_kill(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """擊殺 → 接下一段（3F-4a）：第一段是有傷害的動作；第二段是動作或位移（可以先位移再動作，
    例如衝鋒接傷害），從施放者的位置選目標。"""
    _no_forbidden(effects, "第一段")
    _needs_damage(effects, COMPOSITE_KIND_ZH["on_kill"])
    _second_shape(f, ON_KILL_SECOND_SHAPES)
    _no_forbidden(f.effects, "第二段", allowed=COMPOSITE_MOVES)


def _check_on_hit(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """命中 → 加碼段（3F-4a）：第一段是有傷害的動作；第二段是動作，自動對命中的同一個目標。"""
    _no_forbidden(effects, "第一段")
    _needs_damage(effects, COMPOSITE_KIND_ZH["on_hit"])
    _second_shape(f, FOLLOWUP_SHAPES)
    _no_forbidden(f.effects, "第二段")


def _check_delayed(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """延遲段（3F-4b）：第一段任何動作（可以有一個自身位移）；第二段是以施放者為中心的動作
    （:data:`DELAYED_SHAPES`），必須指定 ``release``。"""
    if f.release is None:
        raise ValueError(
            f"延遲段必須指定 release（{'、'.join(DELAYED_RELEASE_VALUES)}）：何時釋放第二段"
        )
    _no_forbidden(effects, "第一段", allowed=COMPOSITE_MOVES)
    _second_shape(f, DELAYED_SHAPES)
    _no_forbidden(f.effects, "延遲段")


_FOLLOWUP_CHECKS: dict[str, Callable[[tuple[EffectSpec, ...], ShapeSpec, FollowupSpec], None]] = {
    "after_move": _check_after_move,
    "after_action": _check_after_action,
    "after_gather": _check_after_gather,
    "on_kill": _check_on_kill,
    "on_hit": _check_on_hit,
    "delayed": _check_delayed,
}
"""``followup.when`` → 兩段的結構檢查（schema 層級；骨架規則由驗證器檢查）。"""
_MAX_COOLDOWN_RESTORE = 2
"""``restore_resource`` 的 ``resource: cooldown`` 一次最多縮短的回合（Phase 3D-1）。"""
HURL_OBJECT = "hurl_object"
TOPPLE = "topple"
"""Phase 3C-5a 的物件原語 ID（6.15）：投擲物件、推倒。"""
PIERCE_SHAPES: tuple[str, ...] = shape_role("pierce")
"""可以穿透（``pierce``，Phase 3C-5b）的形狀：遠程單體與直線。"""
REDIRECT_STATUS = primitive_status("redirect_damage")
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
    "heal_permille",
    "summon_hp_permille",
    "summon_attack_dice",
    "summon_limit_delta",
    "summon_duration_delta",
    "summon_damage_permille",
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
    "heal_permille": _SKILL_TARGETS,
    "summon_hp_permille": _SKILL_TARGETS,
    "summon_attack_dice": _SKILL_TARGETS,
    "summon_limit_delta": _SKILL_TARGETS,
    "summon_duration_delta": _SKILL_TARGETS,
    "summon_damage_permille": _SKILL_TARGETS,
}
"""每種 ``change`` 可以套用的對象（``applies_to`` 的每一項都必須在內）：推擊、絆倒、互動沒有傷害與
命中骰，基本動作沒有冷卻與標籤。"""

SELF_ONLY_CHANGES: frozenset[str] = frozenset(
    {
        "ap_delta",
        "range_delta",
        "add_element",
        "add_tags",
        "grant_pierce",
        "heal_permille",
        "summon_hp_permille",
        "summon_attack_dice",
        "summon_limit_delta",
        "summon_duration_delta",
        "summon_damage_permille",
        *SHAPE_CHANGES,
    }
)
"""在選目標之前就要決定的修正：條件只能看持有者自己（``self_hp_below``）或省略。"""

WIELDING_WEAPON = "wielding_weapon"
"""武器親和條件（Phase 3I-5）。"""
WIELDING_EFFECT_ONLY = (
    "「手持某種武器時」只能寫在效果上（沒拿那種武器時技能照常可用，只是少那個加成）；"
    "想限定武器才能用，請改用限定武器"
)
"""``wielding_weapon`` 寫在技能條件上時的訊息（schema 與工坊事前停用共用）。"""

SELF_CONDITIONS: frozenset[str] = frozenset({"self_hp_below"})
CASTER_CONDITIONS: frozenset[str] = frozenset(
    {
        "self_hp_below",
        "moved_this_turn",
        "adjacent_ally",
        "first_round",
        "cast_tag_this_turn",
        "self_concealed",
        "wielding_weapon",
    }
)
"""只看施放者的條件（Phase 3D-1；``wielding_weapon`` 為 3I-5）：技能層級的判斷不需要影響範圍內
有對象。選目標之前就要決定的修正規則改變（:data:`SELF_ONLY_CHANGES`）仍只允許
:data:`SELF_CONDITIONS`（``self_hp_below``）。"""

ON_HIT_PRIMITIVES: tuple[str, ...] = (
    "damage",
    "apply_status",
    "push",
    "pull",
    "knock_prone",
    "create_surface",
    "detonate_runes",
    "inscribe",
)
"""``on_hit_effects`` 可用的原語（作用在被命中的目標或其所在格，自動命中）。``detonate_runes``、
``inscribe``（Phase 3-31 普攻與符文）只作用在目標所在的那 1 格。"""

PER_TURN_LIMIT_CHANGES: frozenset[str] = frozenset({"damage_permille", "on_hit_effects"})
"""可以帶 ``per_turn_limit`` 的 ``change`` 種類（Phase 3-31）。"""

_MAX_MODIFIERS = 2
_MAX_MASTERY_MODIFIERS = 4
"""專精（帶 ``exclusive_group`` 的修正型被動，3-33f1）可以有的規則數：效果與代價各幾條。"""
MAX_MODIFIERS = _MAX_MODIFIERS
"""修正技能的修正規則條數上限（Phase 3F-1 公開給技能工坊的選項推導）。"""
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
    - ``heal_permille``（3-24b1，8.21.4.2）：你的治療量 ±‰（技能的治療與聖光雙效的治療；
      −500～＋1000，不可為 0；多條規則加總後套用一次，結果下限 0）。
    - ``summon_hp_permille``（3-24b1）：你召喚出來的召喚物最大 HP +n‰（1～1000；召喚時結算）。
    - ``summon_attack_dice``（3-24b1）：你召喚出來的召喚物攻擊傷害骰多 +n 顆（只能是 1；召喚時
      結算）。
    - ``summon_limit_delta``（3-33f1，6.29.4）：你同時存在的召喚物上限 ±1（只能是 +1 或 −1；
      結果不低於 1、不超過 ``core.summon_hard_cap``）。
    - ``summon_duration_delta``（3-33f1）：你召喚出來的召喚物持續輪數 +n（1～2；加在
      ``summon_max_duration`` 之後）。
    - ``summon_damage_permille``（3-33f1）：你召喚出來的召喚物傷害加成 +n‰（1～1000；召喚時快照，
      與成長加成一樣計入全身 +50% 上限）。
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
    heal_permille: int | None = Field(default=None, ge=-500, le=1000)
    summon_hp_permille: int | None = Field(default=None, ge=1, le=1000)
    summon_attack_dice: int | None = Field(default=None, ge=1, le=1)
    summon_limit_delta: int | None = Field(default=None, ge=-1, le=1)
    summon_duration_delta: int | None = Field(default=None, ge=1, le=2)
    summon_damage_permille: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def _check(self) -> ModifierChange:
        given = [name for name in MODIFIER_CHANGES if getattr(self, name) is not None]
        if len(given) != 1:
            got = "、".join(given) if given else "沒有"
            raise ValueError(f"change 必須恰好一種（{'、'.join(MODIFIER_CHANGES)}），收到 {got}")
        kind = given[0]
        value = getattr(self, kind)
        if (
            kind
            in (
                "damage_permille",
                "hit_bonus",
                "ap_delta",
                "range_delta",
                "heal_permille",
                "summon_limit_delta",
            )
            and value == 0
        ):
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
            ModifierChange._check_on_hit_rune(index, effect)
        types = {e.type for e in effects}
        if INSCRIBE in types and DETONATE_RUNES in types:
            raise ValueError(RUNE_BOTH_MESSAGE)

    @staticmethod
    def _check_on_hit_rune(index: int, effect: EffectSpec) -> None:
        where = f"change.on_hit_effects[{index}]（{effect.type}）"
        if effect.type == DETONATE_RUNES and effect.scope != "target_cell":
            raise ValueError(f"{where}：命中後引爆必須填 scope: target_cell（只引爆目標那 1 格）")
        if effect.type != DETONATE_RUNES and effect.scope is not None:
            raise ValueError(f"{where}：只有 detonate_runes 使用 scope")
        if effect.type == INSCRIBE and (effect.element is None) == (effect.tag is None):
            raise ValueError(f"{where}：必須恰好填 element 或 tag 其中一個")
        if effect.type == INSCRIBE and effect.dice is not None:
            raise ValueError(f"{where}：符文本身沒有效果，不可填 dice")

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
    per_turn_limit: Literal[1] | None = None
    """每回合最多生效幾次（Phase 3-31；只能是 1）。次數存在持有者的戰鬥狀態內（自己回合開始時
    清除）；只有 ``damage_permille``（且只套用在普攻）與 ``on_hit_effects`` 可以填。"""
    empty_slots_cap: int | None = Field(default=None, ge=1, le=6)
    """傷害加成依空欄位數計算（Phase 3-32a，普攻精通）：``damage_permille`` 變成「主動技能欄每空
    1 格加這麼多‰」，最多算這麼多格；空格數在每次普攻結算當下由引擎從單位裝備的主動技能數量算出
    （``core.skill_slots.active`` 減去裝備的主動技能數）。只能搭配 ``damage_permille`` 且只套用在
    普攻（``applies_to.actions``），不可與 ``per_turn_limit`` 並用。"""

    @model_validator(mode="after")
    def _check(self) -> ModifierSpec:
        kind = self.change.kind
        self._check_per_turn(kind)
        self._check_empty_slots(kind)
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

    def _check_per_turn(self, kind: str) -> None:
        if self.per_turn_limit is None:
            return
        if kind not in PER_TURN_LIMIT_CHANGES:
            names = "、".join(sorted(PER_TURN_LIMIT_CHANGES))
            raise ValueError(f"per_turn_limit 只能用在 {names}，收到 change.{kind}")
        target = self.applies_to
        if kind == "damage_permille" and (
            target.skill_tags or target.all_attacks or target.all_skills
        ):
            raise ValueError("傷害加成的 per_turn_limit 只能套用在普攻（applies_to.actions）")

    def _check_empty_slots(self, kind: str) -> None:
        if self.empty_slots_cap is None:
            return
        target = self.applies_to
        if kind != "damage_permille" or (self.change.damage_permille or 0) <= 0:
            raise ValueError("empty_slots_cap 只能搭配正的 change.damage_permille")
        if target.skill_tags or target.all_attacks or target.all_skills:
            raise ValueError("empty_slots_cap 只能套用在普攻（applies_to.actions）")
        if self.per_turn_limit is not None:
            raise ValueError("empty_slots_cap 不可與 per_turn_limit 並用")


# ---------------------------------------------------------------------------
# 戰場變奏（Phase 3-25a，06 6.24）
# ---------------------------------------------------------------------------

MAX_VARIANTS = 2
"""一招技能最多的變奏數（實際上限再依稀有度，見 ``core.yaml`` 的 ``variant_max_by_rarity``）。"""
VARIANT_CONDITIONS: tuple[str, ...] = (
    "caster_surface",
    "caster_high_ground",
    "caster_adjacent_blocker",
    "target_surface",
)
"""變奏條件的四種（PM 決定 #2）。"""
VARIANT_TARGET_CONDITIONS: tuple[str, ...] = ("caster_high_ground", "target_surface")
"""依賴目標點的條件：同一招對不同的目標點可能選出不同的型態（PM 決定 #4）。"""
_MAX_VARIANT_REPLACEMENTS = 2
_VARIANT_REPLACEMENTS = ("shape", "range_delta", "element", "add_effect", "replace_effect")


class VariantWhen(ContentModel):
    """變奏的條件：四種恰好填一種（PM 決定 #2）。

    - ``caster_surface``：施放者所在格的表面是其中之一（表面 id，必須在 ``surfaces.yaml``）；
    - ``caster_high_ground: true``：施放者所在格比目標點高至少 1 層；
    - ``caster_adjacent_blocker: true``：施放者八方向相鄰的格子有牆壁或 ``blocks_move`` 物件；
    - ``target_surface``：目標點的表面是其中之一。
    """

    caster_surface: tuple[str, ...] | None = None
    caster_high_ground: Literal[True] | None = None
    caster_adjacent_blocker: Literal[True] | None = None
    target_surface: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def _check(self) -> VariantWhen:
        given = [name for name in VARIANT_CONDITIONS if getattr(self, name) is not None]
        if len(given) != 1:
            raise ValueError(
                f"變奏條件 when 必須恰好填一種（{'、'.join(VARIANT_CONDITIONS)}），"
                f"收到 {len(given)} 種"
            )
        for name in ("caster_surface", "target_surface"):
            ids = getattr(self, name)
            if ids is None:
                continue
            if not ids:
                raise ValueError(f"when.{name} 至少要列一種表面")
            bad = [i for i in ids if re.match(ID_PATTERN, i) is None]
            if bad or len(set(ids)) != len(ids):
                raise ValueError(f"when.{name} 必須是不重複的表面 id，收到 {', '.join(ids)}")
        return self

    @property
    def kind(self) -> str:
        """填了哪一種條件。"""
        return next(name for name in VARIANT_CONDITIONS if getattr(self, name) is not None)

    @property
    def target_dependent(self) -> bool:
        """條件依賴目標點（居高、目標格表面）。"""
        return self.kind in VARIANT_TARGET_CONDITIONS

    @property
    def surfaces(self) -> tuple[str, ...]:
        """條件引用的表面 id（沒有時為空）。"""
        return self.caster_surface or self.target_surface or ()


class VariantEffectSwap(ContentModel):
    """``replace_effect``：把第 ``index`` 個效果（從 0 起算）換成 ``effect``。"""

    index: int = Field(ge=0)
    effect: EffectSpec


def walk_effect(effect: EffectSpec) -> Iterator[EffectSpec]:
    """效果本身與巢狀的效果（``then``、``win``／``lose``、``on_kill``、zone 的 ``effects``）。"""
    yield effect
    for group in (effect.then, effect.win, effect.lose, effect.on_kill, effect.effects):
        for sub in group or ():
            yield from walk_effect(sub)


class VariantSpec(ContentModel):
    """技能的一個戰場變奏（Phase 3-25a，06 6.24；PM 決定 #1）：條件 ``when`` 成立時，施放的是把
    替換內容套上去的型態（:meth:`SkillDef.variant_form`）。

    替換內容填 1～2 項：``shape``（整個換掉）、``range_delta``（射程 ±，結果至少 1；形狀要有數字
    射程）、``element``（換掉所有傷害效果的元素）、``add_effect``（加一個附帶效果）、
    ``replace_effect``（換掉一個附帶效果；不可換掉主傷害或唯一的效果）。AP、冷卻、代價、kind 與
    骨架不能改（沒有這些欄位）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    """型態名，例如「水中貫穿」。"""
    when: VariantWhen
    shape: ShapeSpec | None = None
    range_delta: int | None = None
    element: Element | None = None
    add_effect: EffectSpec | None = None
    replace_effect: VariantEffectSwap | None = None

    @model_validator(mode="after")
    def _check(self) -> VariantSpec:
        count = len(self.replacements)
        if not 1 <= count <= _MAX_VARIANT_REPLACEMENTS:
            raise ValueError(
                f"變奏 {self.id} 的替換內容必須填 1～2 項"
                f"（{'、'.join(_VARIANT_REPLACEMENTS)}），收到 {count} 項"
            )
        if self.range_delta == 0:
            raise ValueError(f"變奏 {self.id} 的 range_delta 不可為 0")
        return self

    @property
    def replacements(self) -> tuple[str, ...]:
        """填了的替換欄位（依 :data:`_VARIANT_REPLACEMENTS` 的順序）。"""
        return tuple(name for name in _VARIANT_REPLACEMENTS if getattr(self, name) is not None)


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
    weapon_only: tuple[str, ...] = ()
    """限定武器（Phase 3I-5，6.10 #50 專屬招牌技）：非空時，只有主手武器或副手的 ID 在這份清單裡
    （``weapons.yaml``、``offhands.yaml``）才能裝備、施放這個技能；空 ＝ 不限（照 ``weapon_req``）。
    與 ``weapon_req`` 並存：兩者都要符合。只有火器、盾、成對武器、鞭的招牌技使用。"""
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
    exclusive_group: str | None = Field(default=None, pattern=ID_PATTERN)
    """互斥群組（Phase 3-33f1，6.29.4）：同一群組的技能不能同時裝備（例如普攻精通、群召、精英召喚
    都是 ``mastery``）；只有修正型被動可以填。檢查在 :func:`skill_slot_problems`。"""
    tags: tuple[str, ...] = ()
    element: Element | None = None
    """技能元素（主題元素，Phase 3-54d，06 6.33「大地元素的判定與限制」）：填了就以它為準，不論有沒
    有
    傷害效果（可以做出沒有傷害、只有隆起或下陷的大地技能）；省略時沿用 ``tags`` 裡的元素名稱
    （手寫技能的主題標籤、組合器的主題元素）。見 :func:`skill_elements`。"""
    narrative: NarrativeDef = Field(default_factory=NarrativeDef)
    provenance: Provenance = Field(default_factory=Provenance)
    followup: FollowupSpec | None = None
    """複合技能的第二段（Phase 3F-3a，6.23）：有它的技能本身是第一段，``followup.when`` 決定第二段
    何時、以哪裡為原點結算（見 :class:`FollowupSpec`、:meth:`followup_skill`）。"""
    variants: tuple[VariantSpec, ...] = ()
    """戰場變奏（Phase 3-25a，6.24）：0～2 個，條件成立時施放的是變奏型態（:meth:`variant_form`）；
    多個成立時取排在前面的。只有主動技能可以帶；稀有度上限是跨檔案檢查（``core.yaml``）。"""

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
    def _check_element(self) -> SkillDef:
        clash = [t for t in self.tags if t in _ELEMENT_VALUES and t != self.element]
        if self.element is not None and any(t != Element.PHYSICAL.value for t in clash):
            raise ValueError(
                f"技能元素 {self.element.value} 與標籤的元素不一致：{', '.join(clash)}"
            )
        return self

    @model_validator(mode="after")
    def _check_exclusive_group(self) -> SkillDef:
        if self.exclusive_group is not None and self.kind != "modifier":
            raise ValueError("只有修正型被動（kind: modifier）可以填 exclusive_group")
        return self

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
        self._check_self_costs()
        _check_composition(self.kind, self.effects)
        self._check_legendary()
        self._check_copy_skill()
        self._check_hurl_object()
        self._check_pierce()
        self._check_self_moves()
        self._check_pair_moves()
        self._check_summon()
        self._check_zone()
        self._check_runes()
        self._check_sacrifice()
        self._check_gamble()
        self._check_revive()
        self._check_delayed_damage()
        self._check_grant_skill()
        if self.kind == "passive" and self.trigger is None:
            raise ValueError("被動技能（kind: passive）必須有 trigger")
        if self.kind != "passive" and self.trigger is not None:
            raise ValueError(f"只有被動技能可以有 trigger，收到 kind: {self.kind}")
        self._check_reaction_and_stance()
        self._check_trap_and_stacks()
        self._check_scaling_and_mastery()
        self._check_gear_limits()
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
        self._check_followup()
        self._check_variants()
        return self

    def _check_variants(self) -> None:
        """戰場變奏（Phase 3-25a，PM 決定 #1、#7）：最多 2 個、ID 不重複；只有主動技能（不是陷阱、
        不是複合技能、不是常駐類傳說）可以帶；每個型態本身也要是合法的技能（:meth:`variant_form`
        以同一套 schema 檢查）。"""
        if not self.variants:
            return
        if len(self.variants) > MAX_VARIANTS:
            raise ValueError(f"一招技能最多 {MAX_VARIANTS} 個變奏，收到 {len(self.variants)} 個")
        ids = [v.id for v in self.variants]
        if len(set(ids)) != len(ids):
            raise ValueError(f"變奏的 id 不可重複：{', '.join(ids)}")
        if self.kind != "active" or self.trap is not None:
            raise ValueError("只有主動技能可以帶變奏（被動、反應、姿態、陷阱之後再開放）")
        if self.followup is not None:
            raise ValueError("複合技能（有 followup）不能帶變奏")
        if self.is_activatable:
            raise ValueError("常駐類傳說（有 activation）不能帶變奏")
        for variant in self.variants:
            self._check_variant(variant)
            try:
                self.variant_form(variant.id)
            except ValueError as exc:
                raise ValueError(f"變奏「{variant.name_zh}」：{exc}") from None

    def iter_effects(
        self,
        *,
        include_followup: bool = False,
        include_variants: bool = False,
        include_backlash: bool = False,
        include_modifiers: bool = False,
    ) -> Iterator[EffectSpec]:
        """技能所有層級的效果（Phase 3E-2a 統一走訪）：``effects`` 與其巢狀的 ``then``、賭注
        ``win``／``lose``、擊殺時效果 ``on_kill``、區域子效果 ``effects``（zone）。陷阱技能的觸發
        效果就是 ``effects``，自然包含在內。

        - ``include_followup``：複合技能第二段的效果；
        - ``include_variants``：每個變奏的 ``add_effect``、``replace_effect.effect``（尚未套用到
          基礎效果上的原始內容；要看變奏型態的完整效果請走 :meth:`variant_form`）；
        - ``include_backlash``：失手反噬 ``cost.on_miss``；
        - ``include_modifiers``：修正規則的命中後效果 ``change.on_hit_effects``。
        """
        roots: list[EffectSpec] = list(self.effects)
        if include_followup and self.followup is not None:
            roots += self.followup.effects
        if include_backlash:
            roots += self.cost.on_miss
        if include_modifiers:
            for rule in self.modifiers:
                roots += rule.change.on_hit_effects or ()
        if include_variants:
            for variant in self.variants:
                if variant.add_effect is not None:
                    roots.append(variant.add_effect)
                if variant.replace_effect is not None:
                    roots.append(variant.replace_effect.effect)
        for root in roots:
            yield from walk_effect(root)

    def _check_variant(self, variant: VariantSpec) -> None:
        main = self.main_damage_index
        swap = variant.replace_effect
        if swap is not None:
            if len(self.effects) == 1:
                raise ValueError(f"變奏「{variant.name_zh}」：唯一的效果不能被 replace_effect 換掉")
            if swap.index >= len(self.effects):
                raise ValueError(
                    f"變奏「{variant.name_zh}」：replace_effect.index {swap.index} 超出效果數"
                    f" {len(self.effects)}"
                )
            if swap.index == main:
                raise ValueError(f"變奏「{variant.name_zh}」：主傷害（第 {main} 個效果）不能被換掉")
        if variant.element is not None and main is None:
            raise ValueError(f"變奏「{variant.name_zh}」：沒有傷害效果，不能換元素（element）")
        if variant.range_delta is not None:
            shape = variant.shape or self.shape
            if not isinstance(shape.range, int):
                raise ValueError(
                    f"變奏「{variant.name_zh}」：range_delta 只能用在射程是數字的形狀，"
                    f"收到 {shape.type} 的射程 {shape.range!r}"
                )

    @property
    def main_damage_index(self) -> int | None:
        """主傷害：第一個 ``damage`` 效果的索引（沒有時為 ``None``）。"""
        return next((i for i, e in enumerate(self.effects) if e.type == "damage"), None)

    def variant(self, variant_id: str) -> VariantSpec:
        """ID 為 ``variant_id`` 的變奏；沒有時拋出 ``KeyError``。"""
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        raise KeyError(f"{self.id} 沒有變奏 {variant_id}")

    def variant_form(self, variant_id: str) -> SkillDef:
        """變奏型態（Phase 3-25a）：本技能套上變奏的替換內容，展開成一個獨立的技能（沒有
        ``variants``；ID、名稱、代價、骨架都不變）。依序套用：換形狀 → 射程 ± → 換掉附帶效果 →
        加附帶效果 → 換所有傷害效果的元素。引擎施放、驗證器與預算都用它。"""
        key = (id(self), variant_id)
        cached = _VARIANT_CACHE.get(key)
        if cached is not None and cached[0] is self:
            found: SkillDef = cached[1]
            return found
        variant = self.variant(variant_id)
        shape = variant.shape or self.shape
        if variant.range_delta is not None and isinstance(shape.range, int):
            shape = shape.model_copy(update={"range": max(1, shape.range + variant.range_delta)})
        effects = list(self.effects)
        if variant.replace_effect is not None and variant.replace_effect.index < len(effects):
            effects[variant.replace_effect.index] = variant.replace_effect.effect
        if variant.add_effect is not None:
            effects.append(variant.add_effect)
        if variant.element is not None:
            effects = [
                e.model_copy(update={"element": variant.element}) if e.type == "damage" else e
                for e in effects
            ]
        data = {name: getattr(self, name) for name in type(self).model_fields}
        data.update(shape=shape, effects=tuple(effects), variants=())
        try:
            form = SkillDef.model_validate(data)
        except ValidationError as exc:
            messages = "；".join(str(e["msg"]).removeprefix("Value error, ") for e in exc.errors())
            raise ValueError(messages) from None
        if len(_VARIANT_CACHE) >= _FOLLOWUP_CACHE_LIMIT:
            _VARIANT_CACHE.clear()
        _VARIANT_CACHE[key] = (self, form)
        return form

    def _check_followup(self) -> None:
        """複合技能（Phase 3F-3a／3F-4a，6.23）：主動技能、不是陷阱、沒有失手反噬；兩段的結構依
        ``followup.when`` 檢查（:data:`_FOLLOWUP_CHECKS`）；兩段合計最多 4 個效果；第二段本身也要
        是合法的技能（:meth:`followup_skill` 以同一套 schema 檢查）。"""
        follow = self.followup
        if follow is None:
            return
        if self.kind != "active":
            raise ValueError(f"只有主動技能可以有 followup（複合技能），收到 kind: {self.kind}")
        if self.trap is not None or self.cost.on_miss:
            raise ValueError("複合技能不能是陷阱，也不能有失手反噬 cost.on_miss")
        if follow.release is not None and follow.when != "delayed":
            raise ValueError(
                f"只有延遲段（when: delayed）可以指定 release，收到 when: {follow.when}"
            )
        _FOLLOWUP_CHECKS[follow.when](self.effects, self.shape, follow)
        total = len(self.effects) + len(follow.effects)
        if total > _MAX_EFFECTS:
            raise ValueError(f"複合技能兩段合計最多 {_MAX_EFFECTS} 個效果，收到 {total} 個")
        try:
            self.followup_skill()
        except ValueError as exc:
            raise ValueError(f"followup：{exc}") from None

    def followup_skill(self) -> SkillDef | None:
        """複合技能的動作段，展開成一個獨立的技能（Phase 3F-3a）：沿用本技能的 ID、名稱、類別、
        武器需求、縮放屬性、階級、稀有度與代價，骨架、形狀、效果與條件換成 ``followup`` 的。引擎以
        它結算動作段（命中、傷害照常），驗證器與預算以它檢查動作段；沒有 ``followup`` 時為
        ``None``。"""
        if self.followup is None:
            return None
        cached = _FOLLOWUP_CACHE.get(id(self))
        if cached is not None and cached[0] is self:
            derived: SkillDef = cached[1]
            return derived
        follow = self.followup
        data = {name: getattr(self, name) for name in type(self).model_fields if name != "followup"}
        data.update(
            skeleton=follow.skeleton,
            shape=follow.shape,
            effects=follow.effects,
            condition=follow.condition,
        )
        try:
            derived = SkillDef.model_validate(data)
        except ValidationError as exc:
            messages = "；".join(str(e["msg"]).removeprefix("Value error, ") for e in exc.errors())
            raise ValueError(messages) from None
        if len(_FOLLOWUP_CACHE) >= _FOLLOWUP_CACHE_LIMIT:
            _FOLLOWUP_CACHE.clear()
        _FOLLOWUP_CACHE[id(self)] = (self, derived)
        return derived

    def move_segment(self) -> SkillDef:
        """複合技能的第一段（去掉 ``followup`` 的本技能；「位移 → 動作」為位移段）；不是複合技能時
        回傳自己。"""
        if self.followup is None:
            return self
        return self.model_copy(update={"followup": None})

    def _add_gamble_tag(self) -> None:
        """帶賭博機制的技能自動加標籤 ``gamble``（傾向向量與「用法決定進化」用；Phase 3D-7a）。"""
        if self.is_gamble and GAMBLE_TAG not in self.tags:
            object.__setattr__(self, "tags", (*self.tags, GAMBLE_TAG))

    def _check_self_costs(self) -> None:
        """自己付的代價（``cost.self_status``、``cost.overdraft``，2H-1、3-50）只有主動技能可以用。"""
        for name in ("self_status", "overdraft"):
            if getattr(self.cost, name) is not None and self.kind != "active":
                raise ValueError(f"只有主動技能可以有 cost.{name}，收到 kind: {self.kind}")

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

    def _require_shape(self, primitive: str, label: str | None = None) -> None:
        """形狀必須在原語 YAML 的 ``allowed_shapes`` 內（Phase 4-L5b：資料的唯一來源）。"""
        shapes = composition_shapes(primitive)
        if shapes and self.shape.type not in shapes:
            subject = label or f"{primitive} 的"
            allowed = "、".join(shapes)
            raise SkillRuleError(
                f"{subject}形狀必須是 {allowed}，收到 {self.shape.type}", path="shape.type"
            )

    def _check_rule_change(self) -> None:
        """``rule_change``（Phase 3D-6）：主動技能、形狀 ``self``、技能唯一的效果、對象 ``self``，
        而且是傳說（``activation`` 由 :meth:`_check_legendary` 檢查）。主動、唯一效果與形狀的資料在
        ``skill_primitives.yaml``（:func:`_check_composition`）。"""
        changes = [e for e in self.effects if e.type == RULE_CHANGE]
        if not changes:
            return
        if self.rarity != "legendary":
            raise ValueError(f"rule_change 只能用在傳說技能，收到稀有度 {self.rarity}")
        self._require_shape(RULE_CHANGE, "rule_change 技能的")

    def _check_copy_skill(self) -> None:
        """``copy_skill``（Phase 3C-4b）：主動技能、形狀 ``self``，而且是唯一的效果（複製的技能自己
        有目標，由玩家或 AI 在施放時另選）。資料在 ``skill_primitives.yaml``。"""
        if any(e.type == COPY_SKILL for e in self.effects):
            self._require_shape(COPY_SKILL, "copy_skill 技能的")

    def _check_hurl_object(self) -> None:
        """``hurl_object``（Phase 3C-5a）與形狀 ``object_then_tile`` 必須一起出現：主動技能、
        恰好一個投擲效果（物件只有一個）。原語這一側（主動、最多一個、形狀）的資料在
        ``skill_primitives.yaml``；形狀這一側（形狀要求這個原語）留在程式。"""
        hurls = sum(1 for e in self.effects if e.type == HURL_OBJECT)
        if self.shape.type == "object_then_tile" and hurls != 1:
            raise ValueError("形狀 object_then_tile 的技能必須恰好有一個 hurl_object 效果")
        if hurls:
            self._require_shape(HURL_OBJECT)

    def _check_self_moves(self) -> None:
        """自身位移（Phase 3D-2）：``charge_through`` 的形狀、``shadowstep`` 的落點。
        只能用在主動技能、``dash``／``charge_through``／``shadowstep`` 必須是第一個效果的資料在
        ``skill_primitives.yaml``；位移原語最多一個是跨原語的群組規則（都在
        :func:`_check_composition`）。"""
        types = [e.type for e in self.effects]
        if CHARGE_THROUGH in types:
            self._require_shape(CHARGE_THROUGH)
        if SHADOWSTEP in types:
            self._check_shadowstep()

    def _check_shadowstep(self) -> None:
        """``shadowstep``（Phase 3D-8d）：``landing`` 必填，``choose`` 搭配形狀 ``unit_then_tile``、
        ``behind`` 搭配形狀 ``single``（依參數決定形狀，留在程式）。"""
        landing = self.effects[0].landing
        if landing is None:
            raise SkillRuleError(
                "shadowstep 必須填 landing（choose 或 behind）", path="effects[0].landing"
            )
        shape = SHADOWSTEP_SHAPES[landing]
        if self.shape.type != shape:
            raise SkillRuleError(
                f"shadowstep 的 landing: {landing} 必須搭配形狀 {shape}，收到 {self.shape.type}",
                path="shape.type",
            )

    def _check_summon(self) -> None:
        """召喚（Phase 3D-4a）：``count`` 目前只能是 1（或數量型分歧進化的 2）。只能用在主動技能、
        最多一個、形狀 ``ground_tile``、其餘效果必須明寫 ``affects: self``（選的格子是召喚位置，
        必須是空格）的資料在 ``skill_primitives.yaml``。"""
        summons = [e for e in self.effects if e.type == SUMMON]
        if not summons:
            return
        count = summons[0].count or 1
        if count not in (1, MAX_SUMMON_COUNT):
            raise ValueError(f"summon 的 count 只能是 1 或 {MAX_SUMMON_COUNT}，收到 {count}")
        if (count > 1) != (summons[0].power_permille is not None):
            raise ValueError("summon 的 power_permille 與 count: 2 必須一起填（數量型分歧進化）")

    def _check_revive(self) -> None:
        """復活（Phase 3D-8b）：必須填 ``hp_permille``。只能用在主動技能、最多一個、形狀
        ``single``（選一個倒下的友方）、其餘效果必須明寫 ``affects: self`` 的資料在
        ``skill_primitives.yaml``。
        「每場限一次或冷卻至少幾回合」是跨檔案檢查（``skillgen.validate``）。"""
        revives = [e for e in self.effects if e.type == REVIVE]
        if not revives:
            return
        self._require_shape(REVIVE)
        if revives[0].hp_permille is None:
            raise ValueError("revive 必須填 hp_permille")

    def _check_grant_skill(self) -> None:
        """暫時獲得技能（Phase 3D-8c）：``skill`` 與 ``duration`` 必填（只能用在主動技能、
        最多一個的資料在 ``skill_primitives.yaml``）。被給技能本身的限制（一般主動技能、不是傳說、
        不含改寫規則型原語、不是 ``grant_skill``）是跨檔案檢查
        （:func:`granted_skill_problems`）。"""
        grants = [e for e in self.effects if e.type == GRANT_SKILL]
        if not grants:
            return
        grant = grants[0]
        if grant.skill is None or grant.duration is None:
            raise ValueError("grant_skill 必須填 skill 與 duration")
        if grant.skill == self.id:
            raise ValueError("grant_skill 不能給出自己")
        if grant.duration > MAX_GRANT_DURATION:
            raise ValueError(
                f"grant_skill 的 duration 最多 {MAX_GRANT_DURATION}，收到 {grant.duration}"
            )

    def _check_delayed_damage(self) -> None:
        """定時炸彈（Phase 3D-8b）：只能用在法術技；``dice``、``element``、``rounds``、
        ``radius`` 都必填（只能用在主動技能、最多一個的資料在 ``skill_primitives.yaml``）。"""
        bombs = [e for e in self.effects if e.type == DELAYED_DAMAGE]
        if not bombs:
            return
        if self.category != "spell":
            raise SkillRuleError("delayed_damage 只能用在主動的法術技", path="category")
        bomb = bombs[0]
        if bomb.dice is None or bomb.element is None or bomb.rounds is None or bomb.radius is None:
            raise ValueError("delayed_damage 必須填 dice、element、rounds、radius")

    def _check_on_kill(self, where: str, effect: EffectSpec, *, top: bool) -> None:
        """``on_kill``（Phase 3D-8b）：只有主動技能自己的 ``damage`` 效果可以有；內容 1–2 個、類型在
        :data:`ON_KILL_TYPES`、對象只能是施放者；``refund_ap`` 與 ``refund_cooldown`` 只能出現在
        ``on_kill`` 裡。"""
        if effect.type in (REFUND_AP, REFUND_COOLDOWN):
            raise ValueError(f"{where}：{effect.type} 只能出現在 on_kill 裡")
        if effect.on_kill is None:
            return
        if effect.type != "damage":
            raise ValueError(f"{where}：只有 damage 使用 on_kill")
        if not top or self.kind != "active":
            raise ValueError(f"{where}：on_kill 只能用在主動技能自己的傷害效果")
        subs = effect.on_kill
        if not 1 <= len(subs) <= MAX_ON_KILL_EFFECTS:
            raise ValueError(f"{where}：on_kill 必須有 1 到 {MAX_ON_KILL_EFFECTS} 個效果")
        for i, sub in enumerate(subs):
            self._check_on_kill_sub(f"{where}.on_kill[{i}]（{sub.type}）", sub)

    def _check_on_kill_sub(self, at: str, sub: EffectSpec) -> None:
        """``on_kill`` 的一個效果：類型、對象與各類型自己的欄位。"""
        if sub.type not in ON_KILL_TYPES:
            raise ValueError(f"{at}：只能使用 {'、'.join(ON_KILL_TYPES)}")
        if sub.condition is not None or sub.affects not in (None, "self"):
            raise ValueError(
                f"{at}：對象只能是施放者（省略 affects 或寫 self），不可自帶 condition"
            )
        if sub.type == REFUND_AP:
            if sub.amount is None or not 1 <= sub.amount <= MAX_REFUND_AP:
                raise ValueError(f"{at}：必須填 amount（1–{MAX_REFUND_AP}）")
        elif sub.type == REFUND_COOLDOWN:
            if not self.cost.cooldown:
                raise ValueError(f"{at}：技能沒有冷卻（cost.cooldown），沒有東西可以歸零")
        else:
            self._check_effect(0, sub)

    def _check_runes(self) -> None:
        """刻印（Phase 3-23）：``inscribe`` 恰好填 ``element`` 或 ``tag`` 其中一個（標籤符文不可同時
        帶元素）。兩者只能用在主動技能的資料在 ``skill_primitives.yaml``。"""
        for index, effect in enumerate(self.effects):
            if effect.type not in (INSCRIBE, DETONATE_RUNES):
                continue
            where = f"effects[{index}]（{effect.type}）"
            if effect.type == INSCRIBE and (effect.element is None) == (effect.tag is None):
                raise ValueError(f"{where}：必須恰好填 element 或 tag 其中一個")
            if effect.type == INSCRIBE and effect.dice is not None:
                raise ValueError(f"{where}：符文本身沒有效果，不可填 dice")
            if effect.scope is not None:
                raise ValueError(f"{where}：scope 只能用在修正規則的命中後效果")

    def _check_sacrifice(self) -> None:
        """獻祭召喚物（Phase 3-24c）：形狀是 ``single``（選自己的一個召喚物），必須填 ``dice`` 與
        ``radius``；填了 ``element`` 是爆炸（傷害範圍內的敵人），省略是治療範圍內的友方。只能用在
        主動技能與形狀的資料在 ``skill_primitives.yaml``。"""
        for index, effect in enumerate(self.effects):
            if effect.type != SACRIFICE_SUMMON:
                continue
            where = f"effects[{index}]（{SACRIFICE_SUMMON}）"
            shapes = composition_shapes(SACRIFICE_SUMMON)
            if shapes and self.shape.type not in shapes:
                raise SkillRuleError(
                    f"{where}：形狀必須是 {'、'.join(shapes)}（選自己的召喚物）", path="shape.type"
                )
            if effect.dice is None or effect.radius is None:
                raise ValueError(f"{where}：必須填 dice 與 radius")

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
        if zones:  # 只能用在主動技能、唯一的效果：skill_primitives.yaml（_check_composition）
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
        """賭博型（Phase 3D-7a）：``gamble`` 只能用在主動技能、每個技能一個而且是最後一個效果
        （資料在 ``skill_primitives.yaml``）；``cost.on_miss`` 只有主動技能可以有。分支與反噬的
        內容見 :meth:`_check_branch`。"""
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
        # 只能用在主動技能、最多一個、最後一個效果：skill_primitives.yaml（_check_composition）
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
        if (
            self.shape.type in needed
            and not any(
                e.type in PAIR_MOVES and PAIR_SHAPES[e.type] == self.shape.type
                for e in self.effects
            )
            and not self._chooses_shadowstep_landing()
        ):
            raise ValueError(f"形狀 {self.shape.type} 的技能必須有對應的位移他人效果")
        # 原語這一側（主動、唯一的效果、形狀）的資料在 skill_primitives.yaml；
        # 形狀這一側（形狀要求對應的原語，上面）留在程式。
        for effect in self.effects:
            if effect.type in PAIR_MOVES:
                self._require_shape(effect.type)

    def _chooses_shadowstep_landing(self) -> bool:
        """一般瞬步（``shadowstep`` 的 ``landing: choose``，Phase 3D-8d）也用形狀
        ``unit_then_tile``：第 1 段選敵人、第 2 段選他相鄰的落點。"""
        return any(e.type == SHADOWSTEP and e.landing == "choose" for e in self.effects)

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
        limit = _MAX_MODIFIERS if self.exclusive_group is None else _MAX_MASTERY_MODIFIERS
        if not 1 <= len(self.modifiers) <= limit:
            count = len(self.modifiers)
            raise ValueError(f"修正技能的 modifiers 必須有 1 到 {limit} 條，收到 {count} 條")
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
        rune_types = {
            e.type
            for rule in self.modifiers
            for e in rule.change.on_hit_effects or ()
            if e.type in (INSCRIBE, DETONATE_RUNES)
        }
        if len(rune_types) > 1:
            raise ValueError(f"modifiers：{RUNE_BOTH_MESSAGE}")
        for rule_index, rule in enumerate(self.modifiers):
            for index, effect in enumerate(rule.change.on_hit_effects or ()):
                try:
                    self._check_effect(index, effect)
                except ValueError as exc:
                    raise ValueError(f"modifiers[{rule_index}].change.on_hit_{exc}") from None

    def _check_gear_limits(self) -> None:
        """武器親和與限定武器的結構（3I-5，6.10 #50）：``wielding_weapon`` 只能寫在效果上（沒拿
        那種武器時技能照常可用，只是少一個加成；寫在技能條件上就變成不能施放）；限定武器不重複。"""
        gated = [self.condition]
        if self.followup is not None:
            gated.append(self.followup.condition)
        if any(c is not None and c.type == WIELDING_WEAPON for c in gated):
            raise ValueError(f"condition：{WIELDING_EFFECT_ONLY}")
        if len(set(self.weapon_only)) != len(self.weapon_only):
            raise ValueError("weapon_only 不可重複")

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
            and effect.spread is None
        ):
            return
        if effect.type != "damage":
            raise ValueError(
                f"{where}：只有 damage 使用 explode、scaling、lifesteal、split_heal、spread"
            )
        if not top:
            raise ValueError(
                f"{where}：explode、scaling、lifesteal、split_heal、spread "
                "只能用在技能自己的傷害效果"
            )
        if effect.spread is not None and effect.element is not Element.WIND:
            raise ValueError(f"{where}：spread（擴散格數）只有風元素（element: wind）的傷害能填")
        if effect.split_heal is not None:
            self._check_split_heal(where, effect)

    def _check_split_heal(self, where: str, effect: EffectSpec) -> None:
        """``split_heal``（聖光雙效）：只能填 true、``affects: all``、法術技、``aura``／``area``
        骨架、主動技能，不可與吸血、爆骰、縮放並用（治療與傷害要用同一個骰值）。"""
        if effect.affects != "all":
            raise ValueError(f"{where}：split_heal 必須搭配 affects: all")
        if self.category != "spell" or self.kind != "active":
            raise ValueError(f"{where}：split_heal 只能用在主動的法術技")
        if self.skeleton not in SPLIT_SKELETONS:
            allowed = "、".join(SPLIT_SKELETONS)
            raise ValueError(f"{where}：split_heal 只能用在 {allowed} 骨架，收到 {self.skeleton}")
        if effect.lifesteal_permille is not None or effect.explode or effect.scaling is not None:
            raise ValueError(f"{where}：split_heal 不能與 lifesteal、explode、scaling 並用")

    @staticmethod
    def _check_true_only(index: int, where: str, effect: EffectSpec) -> None:
        """只能填 ``true`` 的開關（資料見 :func:`true_only_params`）：填 ``false`` 一律擋下。"""
        for name in sorted(true_only_params().get(effect.type, ())):
            if getattr(effect, name, None) is False:
                raise SkillRuleError(
                    f"{where}：{name} 只能填 true（不啟用就省略）",
                    path=f"effects[{index}].{name}",
                    code="flag.true_only",
                )

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
        self._check_true_only(index, where, effect)
        self._check_variable_damage(where, effect, top=top)
        self._check_on_kill(where, effect, top=top)
        self._check_consume_status(index, effect)
        if effect.type == RESET_COOLDOWN:
            if effect.which is None:
                raise ValueError(f"{where}：reset_cooldown 必須填 which（all 或 tag）")
            if (effect.which == "tag") != (effect.tag is not None):
                raise ValueError(f"{where}：which: tag 必須填 tag，which: all 不可填 tag")
        elif effect.which is not None or (effect.tag is not None and effect.type != INSCRIBE):
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

    def scaling_value(
        self, get: Callable[[Attribute], int], weapon: WeaponDef | None = None
    ) -> int:
        """技能縮放屬性的值（Phase 2H-2）：雙屬性為兩個屬性的平均（無條件捨去），否則為主屬性。
        ``get`` 讀屬性值（引擎傳有效屬性，卡片傳面板屬性）；引擎的 ``skill_scaling_value`` 與卡片的
        「目前加成」都經過這裡。

        **武器技看手上武器的屬性**（Phase 3H-6，玩法決定 #45）：``category: weapon`` 且給了
        ``weapon`` 時改用 :meth:`WeaponDef.scaling_value`（雙屬性照取較高／取平均），技能自己的
        ``scaling_attr`` 只當顯示提示。沒有武器時（工坊、三選一的泛稱）退回技能自己的。"""
        if self.category == "weapon" and weapon is not None:
            # 魔劍士方案 A（3I-3，#46）：武器技可帶一個心智第二屬性，和武器的縮放值取平均
            base = weapon.scaling_value(get)
            if self.secondary_scaling_attr is None:
                return base
            return (base + get(self.secondary_scaling_attr)) // 2
        primary = get(self.scaling_attr)
        if self.secondary_scaling_attr is None:
            return primary
        return (primary + get(self.secondary_scaling_attr)) // 2

    def mastery_value(
        self, get: Callable[[Attribute], int], weapon: WeaponDef | None = None
    ) -> int:
        """專精比較用的屬性值（和自己最高的屬性比）：一般技能為 ``scaling_attr`` 本身；武器技為
        手上武器的縮放值（3H-6，雙屬性取較高／取平均）。"""
        if self.category == "weapon" and weapon is not None:
            return weapon.scaling_value(get)
        return get(self.scaling_attr)

    def contest_attr(self, weapon: WeaponDef | None = None) -> Attribute:
        """對抗判定（擊倒、位移、狀態抵抗）守方被比的單一屬性；武器技為手上武器的主屬性。攻方的值是
        :meth:`scaling_value`（雙屬性為平均，3I-3b）。"""
        if self.category == "weapon" and weapon is not None:
            return weapon.scaling_attr
        return self.scaling_attr

    def _formula_names_zh(self, weapon: WeaponDef | None) -> str:
        """算法句裡的屬性名（3-55）。武器技看手上武器（3H-6）：有武器寫實際的屬性名（雙屬性寫取較高
        ／取平均；3I-3 的心智第二屬性再取平均），沒有武器寫「武器屬性」（卡片另列由武器資料產生的
        例子）；其他技能寫自己的縮放屬性。"""
        second = self.secondary_scaling_attr
        if self.category != "weapon":
            names = self.scaling_attr.display_name
            return names if second is None else f"{names}／{second.display_name}（取平均）"
        if weapon is not None:
            return weapon.skill_scaling_names_zh(second)
        return "武器屬性" if second is None else f"武器屬性與{second.display_name}（取平均）"

    def formula_lines_zh(
        self,
        core: CoreRules,
        weapon: WeaponDef | None = None,
        get: Callable[[Attribute], int] | None = None,
        weapon_examples: str = "",
    ) -> tuple[str, ...]:
        """傷害、治療、護盾的算法（3-41c，08 8.11）：「傷害算法：骰值＋智力 × 0.5（目前 +6.5）」。

        法術技的傷害骰值來自效果自己、治療與護盾一律用法術倍率；武器技的傷害用武器的骰與固定傷害，
        屬性乘普攻倍率（效果的倍率、等級與修正規則另算，見效果句）。倍率取自 ``rules/core.yaml``，
        ``weapon`` 與 ``get`` 都省略時不附武器骰與目前加成。"""
        types = {e.type for e in self.effects}
        names = self._formula_names_zh(weapon)
        now = None if get is None else self.scaling_value(get, weapon)

        def line(label: str, base: str, permille: int) -> str:
            text = f"{label}算法：{base}＋{names} × {permille / 1000:g}"
            return text if now is None else f"{text}（{bonus_text(now, permille)}）"

        out: list[str] = []
        if "damage" in types:
            if self.category == "spell":
                out.append(line("傷害", "骰值", core.spell_attr_multiplier_permille))
            else:
                base = "武器骰"
                if weapon is not None:
                    base += f" {weapon.dice}" + (f"＋{weapon.flat}" if weapon.flat else "")
                out.append(line("傷害", base, core.basic_attack_attr_multiplier_permille))
                if weapon is None and weapon_examples:  # 3-55：沒有主角時列例子
                    out.append(f"武器屬性看手上的武器：{weapon_examples}")
        for kind, label in (("heal", "治療"), ("shield", "護盾")):
            if kind in types:
                out.append(line(label, "骰值", core.spell_attr_multiplier_permille))
        return tuple(out)

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
        "summon_trait": (refs.summon_trait_ids, "召喚物小特性"),
        "infusion": (refs.infusion_ids, "灌注關鍵字"),
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
    summon_trait_ids: set[str] | None = None
    """``summon`` 的 ``trait`` 可用的小特性 ID（Phase 3-33f2）；``None`` 不檢查。"""
    infusion_ids: set[str] | None = None
    """``summon`` 的 ``infusion`` 可用的灌注關鍵字 ID（Phase 3-33f2）；``None`` 不檢查。"""


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


def _forbidden_affects_message(where: str, primitive_id: str, affects: str) -> str:
    if primitive_id == INSCRIBE:  # 刻印的對象只有影響的格子（玩法 PM 2026-10-24）
        return f"{where}.affects：刻印只能刻在影響的格子上，對象要選「格子」（tiles）"
    return f"{where}.affects：{primitive_id} 不能搭配 affects: {affects}"


def _effect_problems(
    skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs, *, on_hit: bool = False
) -> list[str]:
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
        required = param_required_for(
            spec,
            category=skill.category,
            sibling_filled=lambda n: any(
                e.type == primitive.id and getattr(e, n, None) is not None for e in skill.effects
            ),
        )
        if required and name not in values:
            problems.append(f"{where}.{name}：效果 {primitive.id} 缺少必要參數 {name}")
    affects = effect.affects or default_affects(primitive)
    if primitive.acts_on == "caster" and affects != "self":
        problems.append(f"{where}.affects：{primitive.id} 只能對施放者（self），收到 {affects}")
    if primitive.acts_on != "tile" and affects == "tiles":
        problems.append(f"{where}.affects：{primitive.id} 是對單位的效果，不能用 tiles")
    if affects in primitive.forbid_affects:
        problems.append(_forbidden_affects_message(where, primitive.id, affects))
    if (
        primitive.allowed_shapes is not None
        and skill.shape.type not in primitive.allowed_shapes
        and not on_hit  # 命中後效果只作用在目標那 1 格，不看載體技能的形狀
    ):
        allowed = "、".join(primitive.allowed_shapes)
        problems.append(f"{where}：{primitive.id} 只能搭配形狀 {allowed}，收到 {skill.shape.type}")
    problems += _stack_effect_problems(skill, where, effect, affects, refs)
    problems += _consume_status_problems(skill, index, effect, refs)
    problems += _zone_problems(skill, index, effect, refs)
    problems += _gamble_problems(skill, index, effect, refs)
    problems += _on_kill_problems(skill, index, effect, refs)
    problems += _scaling_problems(where, effect, refs)
    return problems


def _on_kill_problems(skill: SkillDef, index: int, effect: EffectSpec, refs: _Refs) -> list[str]:
    """``on_kill`` 的跨檔案檢查（Phase 3D-8b）：一般原語（治療、護盾、施加狀態）當成同一技能的
    效果檢查（參數、引用）；``refund_ap``、``refund_cooldown`` 不是原語，已由 schema 檢查。"""
    problems: list[str] = []
    for i, sub in enumerate(effect.on_kill or ()):
        if sub.type in (REFUND_AP, REFUND_COOLDOWN):
            continue
        prefix = "effects[0]"
        carrier = skill.model_copy(update={"effects": (sub,)})
        problems += [
            f"effects[{index}].on_kill[{i}]{p.removeprefix(prefix)}"
            for p in _effect_problems(carrier, 0, sub, refs)
        ]
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


def _consumer_problems(skill: SkillDef, where: str, stack: StackDef) -> list[str]:
    """``consume_stack`` 的消耗規則（Phase 3-52，``stacks.yaml`` 的 ``consumer``）：技能要有被加成
    的效果（傷害、治療、護盾），並滿足 ``requires_any`` 的其中一項。"""
    consumer = stack.consumer
    if consumer is None:
        return []
    problems: list[str] = []
    no_boost, unmet = consumer.gaps(skill)
    if no_boost:
        problems.append(
            f"{where}.stack：消耗層數 {stack.id} 的技能至少要有{consumer.boost_names()}其中一種效果"
        )
    if unmet:
        problems.append(f"{where}.stack：層數 {stack.id} 只有符合條件的技能可以消耗（見層數說明）")
    return problems


def _stack_effect_problems(
    skill: SkillDef, where: str, effect: EffectSpec, affects: str, refs: _Refs
) -> list[str]:
    """層數原語的跨檔案檢查：層數的 ``owner`` 決定對象（``self`` 型只能對施放者自己、``target`` 型
    只能對敵方），累積量不超過上限；消耗還要符合層數的消耗規則。"""
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
    if effect.type == CONSUME_STACK:
        problems += _consumer_problems(skill, where, stack)
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


def param_required_for(
    spec: PrimitiveParam, *, category: str, sibling_filled: Callable[[str], bool]
) -> bool:
    """這個參數在這個技能裡是否必填：``required``，且 ``required_when`` 成立（沒有則一律必填）。
    ``sibling_filled(name)``：技能內同類型的效果是否有任何一個填了參數 ``name``。"""
    if not spec.required:
        return False
    if spec.required_when is None:
        return True
    return spec.required_when.applies(category=category, sibling_filled=sibling_filled)


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


def granted_skill_problems(
    skill: SkillDef, skills: Mapping[str, SkillDef], primitives: Mapping[str, PrimitiveDef]
) -> list[str]:
    """``grant_skill`` 的跨技能檢查（Phase 3D-8c，6.20）：被給的技能必須存在，而且是一般的主動技能
    ——不是傳說、不含改寫規則型與規則改變型原語、不是 ``grant_skill`` 技能（不連鎖）、也不是技能
    自己（空串列為通過）。"""
    problems: list[str] = []
    for index, effect in enumerate(skill.effects):
        if effect.type != GRANT_SKILL or effect.skill is None:
            continue
        where = f"effects[{index}].skill"
        granted = skills.get(effect.skill)
        if granted is None:
            problems.append(f"{where}：未知的技能 {effect.skill!r}")
            continue
        reasons: list[str] = []
        if granted.id == skill.id:
            reasons.append("不能給出自己")
        if granted.kind != "active":
            reasons.append(f"必須是主動技能（kind: {granted.kind}）")
        if granted.rarity == "legendary":
            reasons.append("不能是傳說技能")
        rewrite = sorted(
            {
                e.type
                for e in granted.effects
                if (p := primitives.get(e.type)) is not None
                and p.category in ("rule_rewrite", "rule_change")
            }
        )
        if rewrite:
            reasons.append(f"不能含改寫規則型原語（{'、'.join(rewrite)}）")
        if any(e.type == GRANT_SKILL for e in granted.effects):
            reasons.append("不能是 grant_skill 技能")
        if reasons:
            problems.append(f"{where}：被給的技能 {granted.id} " + "；".join(reasons))
    return problems


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
    summon_trait_ids: set[str] | None = None,
    infusion_ids: set[str] | None = None,
) -> list[str]:
    """技能引用的形狀、原語、條件、狀態、物件是否存在、參數是否在範圍內（繁體中文，空串列為通過）。

    ``summon_trait_ids``／``infusion_ids``（Phase 3-33f2）：``summon`` 的 ``trait``、``infusion``
    可用的 ID（省略時不檢查）。

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
        summon_trait_ids,
        infusion_ids,
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
                f"{where}.change.on_hit_{p}"
                for p in _effect_problems(carrier, index, effect, refs, on_hit=True)
            ]
    return problems


def on_hit_carrier(skill: SkillDef, effects: tuple[EffectSpec, ...]) -> SkillDef:
    """把修正規則的命中後效果包成一個「技能」（同一個修正技能的複本，``effects`` 換成命中後
    效果），讓驗證、預算與引擎的自動命中施放沿用一般技能的程式。不經過 schema 驗證。"""
    return skill.model_copy(update={"effects": effects})


def skill_elements(skill: SkillDef) -> frozenset[Element]:
    """技能的元素（Phase 3-54d，06 6.33「大地元素的判定與限制」）：技能元素欄（``element``）有填就是
    它；
    沒填時沿用 ``tags`` 裡的元素名稱（組合器的主題元素、手寫技能的主題標籤），有多個元素標籤時取
    **第一個非物理的**（保守：只算一個元素）。物理不算（物理是沒有元素）。**效果自己寫的元素不算**：
    一段大地傷害不會讓技能變成大地技能。"""
    if skill.element is not None:
        found = {skill.element}
    else:
        tagged = (Element(t) for t in skill.tags if t in _ELEMENT_VALUES)
        found = {next((e for e in tagged if e is not Element.PHYSICAL), Element.PHYSICAL)}
    found.discard(Element.PHYSICAL)
    return frozenset(found)


_ELEMENT_VALUES = frozenset(e.value for e in Element)


def is_wind_skill(skill: SkillDef) -> bool:
    """風元素的技能（Phase 3-54a，06 6.33）：頂層有 ``element: wind`` 的傷害效果。

    風壓撞擊（推擊的撞擊傷害加成）用這個判斷；只看技能資料（卡片、預算與實戰同源），武器詞條或
    修正規則在戰鬥中加上的風元素不算。"""
    return any(e.type == "damage" and e.element is Element.WIND for e in skill.effects)


# ---------------------------------------------------------------------------
# 單位與技能
# ---------------------------------------------------------------------------


def weapon_problem(
    skill: SkillDef,
    weapon_class: str,
    held: Mapping[str, str] | None = None,
    *,
    names: Mapping[str, str] | None = None,
) -> str | None:
    """技能的 ``weapon_req`` 與武器分類不相容、或不是限定武器（``weapon_only``，3I-5）時的原因。

    ``held``：單位手上的主手武器與副手（ID → 中文名，見 :func:`held_gear`）；技能有 ``weapon_only``
    而沒給 ``held`` 一律視為不符。``names``：ID → 中文名，只用來把限定武器寫成中文。"""
    if skill.weapon_req not in ("any", weapon_class):
        need, have = _REQ_NAMES[skill.weapon_req], _REQ_NAMES[weapon_class]
        return f"技能「{skill.name_zh}」需要{need}，但單位的武器是{have}"
    if skill.weapon_only and not (held and set(skill.weapon_only) & set(held)):
        lookup = names or {}
        need_text = "、".join(lookup.get(w, w) for w in skill.weapon_only)
        have_text = "、".join(sorted(held.values())) if held else "空手"
        return f"技能「{skill.name_zh}」限定手持{need_text}，但單位手上是{have_text}"
    return None


def held_gear(weapon: Any, offhand: Any = None) -> dict[str, str]:
    """單位手上的主手武器與副手（ID → 中文名），給 :func:`weapon_problem` 與 ``wielding_weapon``
    條件用；``weapon``／``offhand`` 是有 ``id``、``name_zh`` 的定義（副手可為 ``None``）。"""
    held = {weapon.id: weapon.name_zh}
    if offhand is not None:
        held[offhand.id] = offhand.name_zh
    return held


_REQ_NAMES = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器", "any": "任何武器"}


_GROUP_NAMES = {"mastery": "專精（普攻精通、群召、精英召喚）"}


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
    groups: dict[str, list[str]] = {}
    for s in skills:
        if s.exclusive_group is not None:
            groups.setdefault(s.exclusive_group, []).append(s.name_zh)
    for group in sorted(groups):  # 專精互斥（3-33f1）：同一群組最多裝 1 個
        if len(groups[group]) > 1:
            problems.append(
                f"{_GROUP_NAMES.get(group, group)}只能擇一裝備，收到 {len(groups[group])} 個："
                f"{'、'.join(sorted(groups[group]))}"
            )
    changes = sorted(s.name_zh for s in skills if s.rule_change_id is not None)
    if len(changes) > 1:  # 改變規則型傳說每人最多裝 1 個（Phase 3D-6，使用者決定）
        problems.append(
            f"規則改變型傳說每人最多裝 1 個，收到 {len(changes)} 個：{'、'.join(changes)}"
        )
    return problems
