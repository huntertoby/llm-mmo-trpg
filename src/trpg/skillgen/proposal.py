"""LLM 技能提議模型（Phase 3E-2g 原型；設計見 ``docs/phases/Phase4-LLM技能提議設計.md``）。

LLM 不直接寫 :class:`~trpg.content.skills.SkillDef`（扁平的 ``EffectSpec`` 有約 40 個選填欄位，
LLM 容易填錯又難以定位），而是填「提議」：效果、形狀、條件、觸發都是以 ``type``（觸發為 ``event``）
區分的 discriminated union，每一支只有該原語自己的參數，範圍與可用值取自內容資料
（``skill_primitives.yaml`` 的 ``params``、``skill_shapes.yaml``、``skill_conditions.yaml``、
``skill_triggers.yaml`` 與各 ID 表）。

流程：:func:`build_proposal_models` 由內容庫產生模型與 JSON Schema → :func:`evaluate_proposal`
依序做「提議驗證（``proposal``）→ 轉成 ``SkillDef``（``skill``）→ 跨檔案驗證與預算（``rules``）」，
任一階段失敗就回傳結構化的 :class:`ProposalError`（路徑、代碼、中文原因、可用值），給 LLM 重試。

**提議不含數值**（Phase 4-L3，使用者決定 #3）：骰子、倍率、持續回合、距離、AP、法力、冷卻、條件門檻
等一律不在模型裡，只留結構與列舉選擇（見 :mod:`trpg.skillgen.proposal_numbers`）。轉成 ``SkillDef``
時由 :data:`~trpg.skillgen.proposal_numbers.NumberFiller` 補數值（預設是保守的最小補值，正式流程由
4-L5 的預算器補）。模型的說明文字取自內容資料的 ``llm_hint``。

ID、稀有度、階級、來源由呼叫端（:class:`ProposalContext`）決定，LLM 不能填。原型不涵蓋的部分
（複合技能第二段、反應、陷阱、修正規則、非原語的巢狀效果等）見設計文件。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from typing import Annotated, Any, Literal, TypeAliasType, Union, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    TypeAdapter,
    ValidationError,
    create_model,
)

from trpg.content.battle import ID_PATTERN
from trpg.content.keyword_derive import derive_keywords, skill_condition_specs
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    AFFECTS_VALUES,
    BACKLASH_TYPES,
    COMPOSITE_MOVES,
    CONSUME_THEN_TYPES,
    DELAYED_RELEASE_VALUES,
    FOLLOWUP_WHEN_VALUES,
    GAMBLE_BRANCH_TYPES,
    MAX_EFFECTS,
    ON_KILL_TYPES,
    SKILL_ID_PATTERN,
    SKILL_REACTION_EVENTS,
    WIELDING_WEAPON,
    ZONE_EFFECT_TYPES,
    CompositionRule,
    ConditionSpec,
    EffectSpec,
    NestedOnlyDef,
    Origin,
    PrimitiveDef,
    PrimitiveParam,
    ScaleBy,
    SkillDef,
    SkillRarity,
    SkillRuleError,
    TriggerSpec,
    VariantWhen,
    rarity_rank,
    skill_elements,
    weapon_problem,
)
from trpg.shared.types import Attribute, Element, Surface
from trpg.skillgen.option_gear import gear_pool
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal_costs import (
    COST_DOCS,
    apply_cost_choices,
    cost_choices_of,
    on_miss_allowed,
)
from trpg.skillgen.proposal_followup import (
    FOLLOWUP_DOC,
    followup_effect_ids,
    followup_shape_ids,
)
from trpg.skillgen.proposal_layouts import (
    STANDARD_LAYOUT,
    LayoutPlan,
    is_special,
    layout_hint,
    plan_layouts,
    skill_layout,
)
from trpg.skillgen.proposal_numbers import (
    NumberFiller,
    minimal_filler,
    numeric_param_names,
    split_numbers,
)
from trpg.skillgen.scaling import fit_scaling, grant_dual, retarget_scaling
from trpg.skillgen.self_penalty import penalty_choices, penalty_cost, penalty_of_cost
from trpg.skillgen.validate import COMPOSITE_MIN_RARITY, RARITY_STATUS_PRIMITIVES, validate_skill

__all__ = [
    "LLM_ID_PREFIX",
    "NumberFiller",
    "ProposalContext",
    "ProposalError",
    "ProposalModels",
    "ProposalResult",
    "budget_statuses",
    "build_proposal_models",
    "combined_skill_name",
    "composite_allowed",
    "evaluate_proposal",
    "feedback_payload",
    "kind_choices",
    "proposal_from_skill",
    "rarity_statuses",
    "reaction_events",
    "to_skill_def",
]

LLM_ID_PREFIX = "skill_llm_"

PROPOSAL_KINDS: tuple[str, ...] = ("active", "passive", "stance", "reaction")
"""開放提議的技能種類（反應技 Phase 4-L8 開放，帶 ``reaction``；修正型需要 ``modifiers``，
不開放）。"""
CLOSED_SKELETONS: frozenset[str] = frozenset({"modifier", "trap"})
"""不開放的骨架（需要提議模型沒有的欄位：修正規則、陷阱設定）。"""

NESTED_EFFECT_TYPES: dict[str, tuple[str, ...]] = {
    "then": CONSUME_THEN_TYPES,
    "win": GAMBLE_BRANCH_TYPES,
    "lose": GAMBLE_BRANCH_TYPES,
    "on_kill": ON_KILL_TYPES,
    "effects": ZONE_EFFECT_TYPES,
}
"""巢狀效果參數（``type: effects``）可用的效果類型；其中不是原語的類型（``refund_ap``、
``damage_multiplier`` 等）是只能巢狀的效果（Phase 4-L8b，``skill_primitives.yaml`` 的
``nested_only_effects``，父結構以 YAML 的 ``parents`` 為準）。"""
_MAX_NESTED = 2
_MAX_VARIANTS = 2
_MAX_TAGS = 8

# 提議中「由呼叫端或引擎決定、LLM 不能填」的 SkillDef 欄位（文件化用；模型本來就沒有這些欄位）。
CALLER_FIELDS: tuple[str, ...] = ("id", "tier", "rank", "rarity", "provenance", "schema_version")

type Stage = Literal["proposal", "skill", "rules"]


class _Proposal(BaseModel):
    """提議模型的基底：拼錯或多填的欄位一律報錯（錯誤可定位）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True, slots=True)
class ProposalError:
    """給 LLM 的一條結構化錯誤。

    - ``stage``：``proposal``（提議格式）、``skill``（轉成技能時的 schema 檢查）、``rules``（跨檔案
      驗證、預算與骨架規則）。
    - ``path``：出錯的 JSON 路徑（例如 ``effects[1].dice``；技能層級為空字串）。
    - ``code``：穩定的英文代碼（pydantic 錯誤型別或驗證器的規則代碼，例如 ``budget.over``）。
    - ``message``：繁體中文原因。
    - ``allowed``：可用值（列舉型錯誤才有）。
    """

    stage: Stage
    path: str
    code: str
    message: str
    allowed: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "stage": self.stage,
            "path": self.path,
            "code": self.code,
            "message": self.message,
        }
        if self.allowed:
            data["allowed"] = list(self.allowed)
        return data


@dataclass(frozen=True, slots=True)
class ProposalContext:
    """呼叫端決定的欄位（LLM 不能填）：階級、稀有度、等級、來源。

    ``hero_attributes``（Phase 3H-3，07 7.2）：給主角的屬性時，技能的縮放屬性由引擎改成其中最高的、
    且在 ``skill_scaling.yaml`` 允許範圍內的屬性（LLM 填的 ``scaling_attr`` 只是提議，會被取代；
    ID 以取代後的內容雜湊）。沒有給時（3H-7）LLM 填的屬性在允許範圍內就保留，否則取範圍裡第一個；
    第二屬性同樣限在範圍內。"""

    tier: int
    rarity: SkillRarity
    rank: int = 1
    origin: Origin = "level_up"
    hero_attributes: Mapping[Attribute, int] | None = None
    held: Mapping[str, str] | None = None
    """主角手上的主手武器與副手（ID → 中文名；Phase 3I-5）。有值時，提議的「手持某種武器時」
    條件只能指定這些裝備（否則加成永遠不會成立）；``None`` ＝ 不檢查。"""
    keywords: tuple[str, ...] = ()
    """題目的關鍵字（Phase 4-L6）：技能（依專屬規則推導）必須全部帶到，否則
    ``keyword.required``。"""
    core_primitive: str | None = None
    """題目指定的核心原語（Phase 4-L6）：技能的效果必須用到它，否則 ``core.required``。"""
    weapon_class: str | None = None
    """主角的武器大類（``melee``／``ranged``／``focus``；Phase 4-L6）：技能的武器需求必須與它相容
    （含 ``held``），否則 ``weapon.incompatible``，讓模型重提而不是白白浪費這個候選。"""


@dataclass(frozen=True, slots=True)
class ProposalResult:
    """:func:`evaluate_proposal` 的結果：``skill`` 為 ``None`` 時 ``errors`` 不為空。"""

    skill: SkillDef | None
    errors: tuple[ProposalError, ...]

    @property
    def ok(self) -> bool:
        return self.skill is not None and not self.errors


@dataclass(frozen=True, slots=True)
class ProposalModels:
    """由內容庫產生的提議模型。``skill`` 是頂層型別（只有一個版型時是模型本身，否則是以 ``layout``
    區分的 union）；``excluded_primitives`` 是沒有開放或限制用途的原語（與原因）；``layouts`` 是版型
    （ID、中文說明）。"""

    skill: Any
    primitive_ids: tuple[str, ...]
    variant_primitive_ids: tuple[str, ...]
    excluded_primitives: tuple[tuple[str, str], ...]
    layouts: tuple[tuple[str, str], ...] = ()

    def json_schema(self) -> dict[str, Any]:
        """給 LLM（structured output／tool input schema）的 JSON Schema。

        只影響說明、不影響「哪些 JSON 合法」的註記關鍵字（pydantic 自動產生的 ``title``、與
        ``oneOf`` 重複的 OpenAPI ``discriminator`` 對照表、``default``）去掉以縮小 schema
        （Phase 4-L5b；約束解碼不使用它們）。驗證一律用 pydantic 模型本身，不看這份 schema。"""
        schema: dict[str, Any] = _compact(TypeAdapter(self.skill).json_schema())
        return schema


_ANNOTATION_KEYS = frozenset({"title", "discriminator", "default"})
""":func:`_compact` 去掉的註記關鍵字。"""


def _compact(node: Any) -> Any:
    """遞迴去掉 schema 節點上的 :data:`_ANNOTATION_KEYS`；``properties``／``$defs`` 的鍵是欄位名或
    定義名，不去。"""
    if isinstance(node, list):
        return [_compact(v) for v in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key in _ANNOTATION_KEYS:
            continue
        if key in ("properties", "$defs") and isinstance(value, dict):
            out[key] = {name: _compact(sub) for name, sub in value.items()}
        else:
            out[key] = _compact(value)
    return out


# ---------------------------------------------------------------------------
# 模型產生
# ---------------------------------------------------------------------------


def _penalty_type(choices: Sequence[str]) -> Any:
    """``cost_penalty`` 的型別：允許的代價之一，或 ``None``。"""
    return Union[_literal(choices), None]  # noqa: UP007


def _literal(values: Iterable[object]) -> Any:
    lit: Any = Literal
    return lit[tuple(values)]


def _list_of(item: Any) -> Any:
    return list[item]


def _union(models: Sequence[Any], discriminator: str) -> Any:
    if not models:
        raise ValueError("提議模型沒有任何可用的類型（篩選後的原語清單是空的）")
    if len(models) == 1:
        return models[0]
    return Annotated[Union[tuple(models)], Field(discriminator=discriminator)]  # noqa: UP007


def _strip_none(annotation: Any) -> Any:
    args = [a for a in get_args(annotation) if a is not type(None)]
    if not args:
        return annotation
    return args[0] if len(args) == 1 else Union[tuple(args)]  # noqa: UP007


def _id_choice(ids: Iterable[str], pattern: str = ID_PATTERN) -> tuple[Any, dict[str, Any]]:
    values = sorted(ids)
    if not values:
        return str, {"pattern": pattern}
    return _literal(values), {}


@dataclass(frozen=True, slots=True)
class _Refs:
    """參數型別對應的可用 ID（來自內容庫）。"""

    statuses: tuple[str, ...]
    objects: tuple[str, ...]
    stacks: tuple[str, ...]
    summons: tuple[str, ...]
    rule_changes: tuple[str, ...]
    summon_traits: tuple[str, ...]
    infusions: tuple[str, ...]
    weapons: tuple[str, ...]
    """玩家手上會出現的武器與副手 ID（``wielding_weapon`` 條件的 ``weapon``；3I-5）。"""

    @classmethod
    def of(cls, library: ContentLibrary) -> _Refs:
        rules = library.ruleset
        return cls(
            statuses=tuple(sorted(s.id for s in rules.statuses.statuses)),
            objects=tuple(sorted(o.id for o in rules.objects.objects)),
            stacks=tuple(sorted(rules.stacks.by_id())),
            summons=tuple(sorted(rules.summons.by_id())),
            rule_changes=tuple(sorted(rules.rule_changes.by_id())),
            summon_traits=tuple(sorted(rules.core.summon_traits)),
            infusions=tuple(sorted(rules.core.summon_infusions)),
            weapons=tuple(sorted(gear_id for gear_id, _, _ in gear_pool(library))),
        )

    def ids_for(self, param_type: str) -> tuple[str, ...] | None:
        table = {
            "status": self.statuses,
            "object": self.objects,
            "stack": self.stacks,
            "summon": self.summons,
            "rule_change": self.rule_changes,
            "summon_trait": self.summon_traits,
            "infusion": self.infusions,
            "weapon": self.weapons,
        }
        return table.get(param_type)


_FIXED_PARAM_TYPES: dict[str, tuple[Any, dict[str, Any]]] = {
    "bool": (bool, {}),
    "element": (Element, {}),
    "surface": (Surface, {}),
    "tag": (str, {"pattern": ID_PATTERN}),
    "skill": (str, {"pattern": SKILL_ID_PATTERN}),
}
"""與內容庫無關的參數型別（數值型別 ``int``、``dice`` 不開放，見 :func:`_is_numeric`）。"""

_CONDITION_FIELDS = {**EffectSpec.model_fields, **ConditionSpec.model_fields}
"""條件參數退回欄位型別時查的欄位（條件自己的欄位優先，如 ``form_category``）。"""

COUNT_CHOICES: tuple[int | str, ...] = (1, "all")
"""``count`` 型參數（驅散的增益個數）：1 個或全部。"""


def _param_type(
    name: str, spec: PrimitiveParam, refs: _Refs, fallback: Mapping[str, Any]
) -> tuple[Any, dict[str, Any]]:
    """一個參數的型別與 ``Field`` 限制（格式、可用值）；呼叫端已排除數值型別（``_is_numeric``）。"""
    if spec.type == "scaling":
        return _scaling_model(), {}
    if spec.type == "count":
        return _literal(COUNT_CHOICES), {}
    if spec.type == "bool" and spec.true_only:
        return _literal((True,)), {}  # 只能填 true 的開關（Phase 4-L5c）
    fixed = _FIXED_PARAM_TYPES.get(spec.type)
    if fixed is not None:
        return fixed[0], dict(fixed[1])
    ids = refs.ids_for(spec.type)
    if ids is not None:
        return _id_choice(ids)
    # 其餘型別（which、scale、resource、on_hit、landing、anchor、zone_when、scope、scaling、count）
    # 沿用 EffectSpec 欄位的型別：可用值寫在 schema 的 Literal 或子模型裡。
    return _strip_none(fallback[name].annotation), {}


def _is_numeric(spec: PrimitiveParam) -> bool:
    """數值參數（``int``、``dice``）：提議模型不開放，由預算器補。"""
    return bool(numeric_param_names({"x": spec}))


@cache
def _scaling_model() -> Any:
    """``scaling`` 只留「依什麼縮放」，步進與上限是數值。"""
    return create_model("Scaling", __base__=_Proposal, by=(ScaleBy, ...))


def _field(annotation: Any, limits: Mapping[str, Any], *, required: bool, doc: str) -> Any:
    clean = {k: v for k, v in limits.items() if v is not None}
    if required:
        return (annotation, Field(description=doc or None, **clean))
    return (annotation | None, Field(default=None, description=doc or None, **clean))


def _affects_type(primitive: PrimitiveDef) -> Any:
    if primitive.acts_on == "caster":
        return _literal(("self",))
    forbid = set(primitive.forbid_affects or ())
    return _literal(v for v in AFFECTS_VALUES if v not in forbid)


def _required(spec: PrimitiveParam) -> bool:
    """提議中必填：YAML 的 ``required``，但有 ``required_when`` 的依情況才必填，提議中可省略、
    缺了由 ``rules`` 階段的跨檔案驗證報錯。"""
    return spec.required and spec.required_when is None


def _has_nested(primitive: PrimitiveDef) -> bool:
    return any(p.type == "effects" for p in primitive.params.values())


_SELF_AFFECTS_DOC = "這個版型的其他效果只作用在施放者。"


class _Builder:
    def __init__(
        self,
        library: ContentLibrary,
        only: frozenset[str] | None,
        shapes: frozenset[str] | None = None,
        conditions: frozenset[str] | None = None,
        triggers: frozenset[str] | None = None,
        *,
        statuses: tuple[str, ...] | None = None,
        extra_shapes: frozenset[str] = frozenset(),
    ) -> None:
        self.library = library
        self.nested_only = library.ruleset.primitives.nested_only_by_id()
        self.refs = _Refs.of(library)
        self.statuses = statuses
        self.budget_statuses = budget_statuses(library)
        self.trigger_ids = triggers
        self.condition = _alias("Condition", self._condition_union(conditions))
        # 複合技能第二段可以用子集以外的形狀（extra_shapes，Phase 4-L8）；版型只用 shapes
        self.all_shapes = self._shape_models(None if shapes is None else shapes | extra_shapes)
        self.shapes = {k: v for k, v in self.all_shapes.items() if shapes is None or k in shapes}
        primitives = [
            p for p in library.ruleset.primitives.primitives if only is None or p.id in only
        ]
        self.defs = {p.id: p for p in primitives}
        # 巢狀位置（then、win／lose、on_kill、zone 的 effects）不能再巢狀：用去掉巢狀參數的模型。
        leaves = {p.id: self._effect_model(p, None) for p in primitives}
        self.effects: dict[str, Any] = {}
        self.nested: dict[str, dict[str, Any]] = {}
        self.excluded: list[tuple[str, str]] = []
        self._self_models: dict[str, Any] = {}
        self._backlash: Any = None
        for p in primitives:
            nested = {
                name: self._nested_type(name, leaves)
                for name, spec in p.params.items()
                if spec.type == "effects"
            }
            # 選填的巢狀參數沒有可用原語就不開放該參數；必填的沒有可用原語就不開放整個原語。
            empty = sorted(
                name for name, item in nested.items() if item is None and p.params[name].required
            )
            if empty:
                self.excluded.append((p.id, f"巢狀參數 {', '.join(empty)} 沒有可用的原語"))
            elif nested:
                self.nested[p.id] = nested
                self.effects[p.id] = self._effect_model(p, nested)
            else:
                self.effects[p.id] = leaves[p.id]
        self.lookup_ids = {
            p.id for p in primitives if p.lookup_by_skill_id and p.id in self.effects
        }
        self.trigger = _alias("Trigger", self._trigger_union())

    def outside_models(self, ids: Iterable[str]) -> dict[str, Any]:
        """子集外原語的模型（複合技能第二段的自身位移，Phase 4-L8；沒有巢狀參數的版本）。"""
        table = self.library.ruleset.primitives.by_id()
        return {i: self._effect_model(table[i], None) for i in ids if i not in self.effects}

    def self_effect(self, primitive_id: str) -> Any:
        """只作用在施放者的版本（``affects`` 只能是 ``self``，預設 ``self``）。"""
        model = self._self_models.get(primitive_id)
        if model is None:
            primitive = self.defs[primitive_id]
            model = self._effect_model(primitive, self.nested.get(primitive_id), self_only=True)
            self._self_models[primitive_id] = model
        return model

    def shape_union(self, ids: Iterable[str]) -> Any:
        return _union([self.all_shapes[i] for i in ids], "type")

    def _nested_type(self, name: str, leaves: Mapping[str, Any]) -> Any:
        """巢狀參數 ``name`` 的效果清單型別：:data:`NESTED_EFFECT_TYPES` 中是原語的類型，加上
        只能巢狀的效果（Phase 4-L8b；``skill_primitives.yaml`` 的 ``nested_only_effects``，
        ``parents`` 含 ``name`` 才收）。"""
        models = []
        for t in NESTED_EFFECT_TYPES.get(name, ()):
            if t in leaves:
                models.append(leaves[t])
            elif t in self.nested_only and name in self.nested_only[t].parents:
                models.append(self._nested_only_model(self.nested_only[t]))
        if not models:
            return None
        return _list_of(_union(models, "type"))

    def _nested_only_model(self, definition: NestedOnlyDef) -> Any:
        """只能巢狀的效果的提議模型：``type`` 與非數值參數（目前都沒有；數值由補值器補）。"""
        fields: dict[str, Any] = {
            "type": (_literal((definition.id,)), Field(description=definition.name_zh)),
        }
        for name, spec in sorted(definition.params.items()):
            if _is_numeric(spec):
                continue
            annotation, limits = _param_type(name, spec, self.refs, EffectSpec.model_fields)
            fields[name] = _field(annotation, limits, required=_required(spec), doc=spec.llm_hint)
        return create_model(
            f"NestedOnly_{definition.id}",
            __base__=_Proposal,
            __doc__=definition.llm_hint,
            **fields,
        )

    def backlash_union(self) -> Any:
        """失手反噬（``cost_on_miss``，Phase 4-L8）的效果 union：:data:`BACKLASH_TYPES` 中內容庫有的
        原語，沒有 ``affects``（對象固定是施放者）與 ``condition``、沒有巢狀參數；不受原語子集
        篩選（反噬不是技能的效果）。"""
        if self._backlash is None:
            table = self.library.ruleset.primitives.by_id()
            models = [
                self._effect_model(table[t], None, mode="backlash")
                for t in BACKLASH_TYPES
                if t in table
            ]
            self._backlash = _alias("BacklashEffect", _union_or_none(models))
        return self._backlash

    def _effect_model(
        self,
        primitive: PrimitiveDef,
        nested: Mapping[str, Any] | None,
        *,
        self_only: bool = False,
        mode: Literal["effect", "backlash"] = "effect",
    ) -> Any:
        """一個原語的提議模型；``nested`` 為 ``None`` 時是巢狀位置用的版本（沒有巢狀參數）；
        ``self_only`` 是「其他效果只作用在施放者」的版型用的版本；``mode="backlash"`` 是失手
        反噬用的版本（沒有 ``affects``、``condition``）。"""
        fields: dict[str, Any] = {
            "type": (_literal((primitive.id,)), Field(description=primitive.name_zh)),
        }
        if mode == "effect":
            fields["affects"] = (
                (Literal["self"], Field(default="self", description=_SELF_AFFECTS_DOC))
                if self_only
                else (_affects_type(primitive) | None, None)
            )
            if self.condition is not None:
                fields["condition"] = (Union[self.condition, None], None)  # noqa: UP007
        for name, spec in sorted(primitive.params.items()):
            doc = spec.llm_hint
            if _is_numeric(spec):
                continue
            if spec.type == "effects":
                if nested is None or nested[name] is None:
                    continue
                limits = {"min_length": 1, "max_length": _MAX_NESTED}
                fields[name] = _field(nested[name], limits, required=spec.required, doc=doc)
                continue
            annotation, limits = self._param(primitive, name, spec)
            required = _required(spec)
            fields[name] = _field(annotation, limits, required=required, doc=doc)
        if mode == "backlash":
            prefix = "BacklashEffect"
        elif self_only:
            prefix = "SelfEffect"
        else:
            prefix = "NestedEffect" if nested is None and _has_nested(primitive) else "Effect"
        return create_model(
            f"{prefix}_{primitive.id}",
            __base__=_Proposal,
            __doc__=primitive.llm_hint,
            **fields,
        )

    def _param(
        self, primitive: PrimitiveDef, name: str, spec: PrimitiveParam
    ) -> tuple[Any, dict[str, Any]]:
        """參數型別；稀有度檢查狀態的原語（``apply_status``）只列稀有度夠的狀態（Phase 4-L5b）；
        以狀態點數計預算的原語（``budget_basis: status``）只列有 ``budget_points`` 的狀態
        （4-L5c）。"""
        if spec.type == "status":
            ids = self._status_choices(primitive)
            if ids is not None:
                return _id_choice(ids)
        return _param_type(name, spec, self.refs, EffectSpec.model_fields)

    def _status_choices(self, primitive: PrimitiveDef) -> tuple[str, ...] | None:
        """這個原語的狀態參數可用的 ID（``None`` ＝ 不限）。"""
        ids: set[str] | None = None
        if primitive.budget_basis == "status":
            ids = set(self.budget_statuses)
        if self.statuses is not None and primitive.id in RARITY_STATUS_PRIMITIVES:
            ids = set(self.statuses) if ids is None else ids & set(self.statuses)
        return None if ids is None else tuple(sorted(ids))

    def _condition_union(self, only: frozenset[str] | None) -> Any:
        """條件的 union；``only`` 篩選後沒有任何條件時回傳 ``None``（提議不開放條件欄位）。"""
        models = []
        for cond in self.library.ruleset.conditions.conditions:
            if only is not None and cond.id not in only:
                continue
            fields: dict[str, Any] = {"type": (_literal((cond.id,)), ...)}
            for name, spec in sorted(cond.params.items()):
                if _is_numeric(spec):
                    continue
                annotation, limits = _param_type(name, spec, self.refs, _CONDITION_FIELDS)
                fields[name] = _field(annotation, limits, required=spec.required, doc=spec.llm_hint)
            models.append(
                create_model(
                    f"Condition_{cond.id}",
                    __base__=_Proposal,
                    __doc__=cond.llm_hint,
                    **fields,
                )
            )
        return _union(models, "type") if models else None

    def _shape_models(self, only: frozenset[str] | None) -> dict[str, Any]:
        """形狀 ID → 模型（YAML 順序）。"""
        models: dict[str, Any] = {}
        for shape in self.library.ruleset.shapes.shapes:
            if only is not None and shape.id not in only:
                continue
            fields: dict[str, Any] = {"type": (_literal((shape.id,)), ...)}
            for name, spec in sorted(shape.params.items()):
                annotation: Any = int
                if spec.allow_weapon:
                    annotation = Union[int, Literal["weapon"]]  # noqa: UP007
                limits = {} if spec.allow_weapon else {"ge": spec.min, "le": spec.max}
                fields[name] = _field(
                    annotation, limits, required=spec.required, doc=shape.params[name].llm_hint
                )
            models[shape.id] = create_model(
                f"Shape_{shape.id}",
                __base__=_Proposal,
                __doc__=shape.llm_hint,
                **fields,
            )
        if not models:
            raise ValueError("提議模型沒有任何可用的類型（篩選後的形狀清單是空的）")
        return models

    def _trigger_union(self) -> Any:
        """觸發時機（``skill_triggers.yaml``）：只有「有另一方」的時機能填 ``target: other``；
        時機自己的參數（``n``、``tag``、``status``、``surface``）取自該時機的 ``params``。
        每輪觸發次數、距離上限是數值，不開放（預設每輪 1 次、不限距離）。"""
        models = []
        for trig in self.library.ruleset.skill_triggers.triggers:
            if self.trigger_ids is not None and trig.id not in self.trigger_ids:
                continue
            fields: dict[str, Any] = {"event": (_literal((trig.id,)), ...)}
            if trig.has_other:
                fields["target"] = (Literal["self", "other"], "self")
            for name, spec in sorted(trig.params.items()):
                annotation, limits = self._trigger_param(name, spec)
                fields[name] = _field(annotation, limits, required=spec.required, doc=spec.llm_hint)
            models.append(
                create_model(
                    f"Trigger_{trig.id}",
                    __base__=_Proposal,
                    __doc__=trig.llm_hint,
                    **fields,
                )
            )
        return _union(models, "event") if models else None

    def _trigger_param(self, name: str, spec: PrimitiveParam) -> tuple[Any, dict[str, Any]]:
        if spec.type == "int":
            # 觸發的整數參數（每幾次命中）是少數幾個列舉值，當成選擇而不是數值。
            assert spec.min is not None and spec.max is not None
            return _literal(range(spec.min, spec.max + 1)), {}
        return _param_type(name, spec, self.refs, TriggerSpec.model_fields)


def _variant_model(effect: Any | None, shape: Any) -> Any:
    """戰場變奏；``effect`` 是變奏能加入或替換的效果（不含 ``lookup_by_skill_id`` 原語），
    ``None`` 時不開放 ``add_effect``／``replace_effect``。"""
    fields: dict[str, Any] = {
        "id": (str, Field(pattern=ID_PATTERN)),
        "name_zh": (str, Field(min_length=1, max_length=12)),
        "when": (VariantWhen, ...),
        "shape": (shape | None, None),
        "element": (Element | None, None),
    }
    if effect is not None:
        swap = create_model(
            "VariantEffectSwap",
            __base__=_Proposal,
            index=(int, Field(ge=0)),
            effect=(effect, ...),
        )
        fields["add_effect"] = (Union[effect, None], None)  # noqa: UP007
        fields["replace_effect"] = (swap | None, None)
    return create_model(
        "Variant",
        __base__=_Proposal,
        __doc__="戰場變奏：when 條件成立時套用 1～2 項替換（shape、element、add_effect、"
        "replace_effect）。",
        **fields,
    )


def reaction_events(library: ContentLibrary) -> tuple[tuple[str, str], ...]:
    """反應技能用的觸發事件（ID、說明；Phase 4-L8）：:data:`SKILL_REACTION_EVENTS` 的順序，說明取
    ``reactions.yaml`` 的 ``events``（給玩家看的短句；沒有就用 ID）。"""
    texts = {e.id: e.description_zh for e in library.ruleset.reactions.events}
    return tuple((e, texts.get(e, e)) for e in SKILL_REACTION_EVENTS)


def _reaction_model(library: ContentLibrary) -> Any:
    """``reaction``：反應技能的觸發事件（``kind: reaction`` 必填，其他種類不可填）。"""
    lines = "；".join(f"{e}＝{text}" for e, text in reaction_events(library))
    return create_model(
        "Reaction",
        __base__=_Proposal,
        __doc__=f"反應技能（kind: reaction）必填：不花 AP、在事件發生時自動施放。{lines}",
        event=(_literal(SKILL_REACTION_EVENTS), ...),
    )


def _skeleton_choices(library: ContentLibrary, skeletons: Iterable[str] | None) -> list[str]:
    available = set(library.skeletons) - CLOSED_SKELETONS
    if skeletons is None:
        return sorted(available)
    chosen = sorted(set(skeletons) & available)
    if not chosen:
        raise ValueError("提議模型沒有任何可用的骨架（篩選後的骨架清單是空的）")
    return chosen


def kind_choices(library: ContentLibrary, skeletons: Sequence[str]) -> tuple[str, ...]:
    kinds = {k for s in skeletons for k in library.skeletons[s].kinds}
    return tuple(k for k in PROPOSAL_KINDS if k in kinds)


def _only(values: Iterable[str] | None) -> frozenset[str] | None:
    return None if values is None else frozenset(values)


def rarity_statuses(library: ContentLibrary, rarity: SkillRarity) -> tuple[str, ...]:
    """這個稀有度能施加的狀態 ID（排序；規則與驗證器的 ``rarity.status`` 相同）。"""
    rank = rarity_rank(rarity)
    return tuple(
        sorted(s.id for s in library.ruleset.statuses.statuses if rarity_rank(s.min_rarity) <= rank)
    )


def budget_statuses(library: ContentLibrary) -> tuple[str, ...]:
    """技能能施加的狀態 ID（有 ``budget_points``；規則與預算的 ``budget.unavailable`` 相同，
    Phase 4-L5c；排序）。"""
    return tuple(
        sorted(s.id for s in library.ruleset.statuses.statuses if s.budget_points is not None)
    )


_SKILL_DOC = "LLM 提議的技能（ID、稀有度、階級與來源由遊戲決定，不要填）。"
_GENERAL_TAG = "~general"
"""版型的效果 union 中「一般原語」那一支的標籤（不是原語 ID；錯誤路徑會略過它）。"""


def _alias(name: str, annotation: Any) -> Any:
    """具名的型別（JSON Schema 中只出現一次、各處以 ``$ref`` 引用）；``None`` 原樣回傳。"""
    if annotation is None:
        return None
    return TypeAliasType(name, annotation)


@dataclass(frozen=True, slots=True)
class _Shared:
    """各版型共用的具名型別：一般原語的 union、只作用在施放者的版本、一般版型的形狀與變奏。"""

    general_ids: frozenset[str]
    general: Any
    self_general: Any
    standard_shape: Any
    variant: Any
    variant_ids: tuple[str, ...]
    followup: Any = None
    """複合技能第二段的模型（Phase 4-L8；沒有可用的效果或形狀時為 ``None``）。"""


def _shared_types(
    library: ContentLibrary, builder: _Builder, plans: Sequence[LayoutPlan]
) -> _Shared:
    rules = {p.id: CompositionRule.of(p) for p in library.ruleset.primitives.primitives}
    general_ids = [i for i in builder.effects if not is_special(rules[i])]
    used = {i for p in plans for i in p.effects}
    general_ids = [i for i in general_ids if i in used]
    selfish = sorted({i for p in plans for i in p.self_effects}, key=list(builder.effects).index)
    general = _alias("GeneralEffect", _union_or_none([builder.effects[i] for i in general_ids]))
    self_general = _alias("SelfEffect", _union_or_none([builder.self_effect(i) for i in selfish]))
    standard = next((p for p in plans if p.id == STANDARD_LAYOUT), None)
    if standard is None:
        return _Shared(frozenset(general_ids), general, self_general, None, None, ())
    variant_ids = tuple(i for i in standard.effects if i not in builder.lookup_ids)
    if variant_ids == tuple(general_ids):
        variant_effect = general  # 不能用在變奏的原語都在特殊版型裡：與一般原語同一個 union
    else:
        variant_effect = _alias(
            "VariantEffect", _union_or_none([builder.effects[i] for i in variant_ids])
        )
    shape = _alias("StandardShape", builder.shape_union(standard.shapes))
    variant = _variant_model(variant_effect, shape)
    return _Shared(frozenset(general_ids), general, self_general, shape, variant, variant_ids)


def _union_or_none(models: Sequence[Any]) -> Any:
    return _union(models, "type") if models else None


def _effect_tag(value: Any) -> str | None:
    raw = value.get("type") if isinstance(value, dict) else getattr(value, "type", None)
    return raw if isinstance(raw, str) else None


def _layout_effects(builder: _Builder, plan: LayoutPlan, shared: _Shared) -> Any:
    """版型的效果 union：特殊原語各一支（標籤是原語 ID），一般原語共用一個具名 union。"""
    if plan.self_effects:
        members = list(plan.effects)
        general = shared.self_general
    else:
        members = [i for i in plan.effects if i not in shared.general_ids]
        has_general = any(i in shared.general_ids for i in plan.effects)
        general = shared.general if has_general else None
    return _tagged_effects(builder.effects, members, general)


def _tagged_effects(models: Mapping[str, Any], members: Sequence[str], general: Any) -> Any:
    """特殊原語各一支（標籤是原語 ID）＋ 一般原語的具名 union（``general``，可為 ``None``）。"""
    if not members:
        return general
    if general is None and len(members) == 1:
        return models[members[0]]
    tags = frozenset(members)

    def pick(value: Any) -> str | None:
        tag = _effect_tag(value)
        if tag in tags or general is None:
            return tag
        return _GENERAL_TAG

    choices: list[Any] = [Annotated[models[i], Tag(i)] for i in members]
    if general is not None:
        choices.append(Annotated[general, Tag(_GENERAL_TAG)])
    return Annotated[Union[tuple(choices)], Discriminator(pick)]  # noqa: UP007


def _followup_model(
    library: ContentLibrary,
    builder: _Builder,
    shared: _Shared,
    skeleton: Any,
    shape_ids: Iterable[str],
    *,
    moves: Iterable[str] = (),
) -> Any:
    """複合技能第二段（``followup``，Phase 4-L8；見 :mod:`trpg.skillgen.proposal_followup`）。第二段
    能用的一般原語與一般版型相同時共用 ``GeneralEffect``，否則另建 ``FollowupEffect``；``moves``
    是子集外也開放給第二段的施放者自身位移（「動作 → 位移」、「擊殺 → 接下一段」用）。沒有可用的
    效果或形狀時回傳 ``None``（提議不開放 ``followup``）。"""
    allowed = followup_effect_ids(list(builder.effects))
    outside = builder.outside_models(m for m in moves if m in COMPOSITE_MOVES)
    models = {**builder.effects, **outside}
    general_ids = [i for i in allowed if i in shared.general_ids]
    members = [i for i in allowed if i not in shared.general_ids] + list(outside)
    shapes = followup_shape_ids(library, shape_ids)
    if not (general_ids or members) or not shapes:
        return None
    if set(general_ids) == shared.general_ids:
        general = shared.general
    else:
        general = _alias(
            "FollowupEffect", _union_or_none([builder.effects[i] for i in general_ids])
        )
    fields: dict[str, Any] = {
        "when": (_literal(FOLLOWUP_WHEN_VALUES) | None, None),
        "skeleton": (skeleton, ...),
        "shape": (builder.shape_union(shapes), ...),
        "effects": (
            _list_of(_tagged_effects(models, members, general)),
            Field(min_length=1, max_length=MAX_EFFECTS - 1),
        ),
        "release": (_literal(DELAYED_RELEASE_VALUES) | None, None),
    }
    if builder.condition is not None:
        fields["condition"] = (Union[builder.condition, None], None)  # noqa: UP007
    return create_model("Followup", __base__=_Proposal, __doc__=FOLLOWUP_DOC, **fields)


def composite_allowed(rarity: SkillRarity | None) -> bool:
    """這個稀有度能不能做複合技能（``None`` ＝ 不篩；規則同驗證器的 ``rarity.composite``）。"""
    return rarity is None or rarity_rank(rarity) >= rarity_rank(COMPOSITE_MIN_RARITY)


def _followup_skeletons(
    library: ContentLibrary,
    skeleton_ids: Sequence[str],
    wanted: Iterable[str] | None,
    same: Any,
) -> Any:
    """第二段的骨架型別：沒有另外指定（或與第一段相同）時共用 ``Skeleton``，否則另建
    ``FollowupSkeleton``。"""
    if wanted is None:
        return same
    ids = _skeleton_choices(library, wanted)
    if ids == list(skeleton_ids):
        return same
    return _alias("FollowupSkeleton", _literal(ids))


def _layout_model(
    builder: _Builder,
    plan: LayoutPlan,
    common: Mapping[str, Any],
    shared: _Shared,
) -> Any:
    """一個版型的頂層模型（欄位順序：``layout`` 最先，讓模型先決定版型）。"""
    if plan.id == STANDARD_LAYOUT and shared.standard_shape is not None:
        shape = shared.standard_shape
    else:
        shape = builder.shape_union(plan.shapes)
    fields: dict[str, Any] = {
        "layout": (_literal((plan.id,)), ...),
        **common,
        "kind": (_literal(plan.kinds), ...),
        "shape": (shape, ...),
        "effects": (
            _list_of(_layout_effects(builder, plan, shared)),
            Field(min_length=1, max_length=plan.max_effects),
        ),
        "tags": (
            list[Annotated[str, Field(pattern=ID_PATTERN)]],
            Field(default_factory=list, max_length=_MAX_TAGS),
        ),
    }
    if plan.variants and shared.variant is not None:
        fields["variants"] = (
            _list_of(shared.variant),
            Field(default_factory=list, max_length=_MAX_VARIANTS),
        )
    if builder.condition is not None:
        fields["condition"] = (Union[builder.condition, None], None)  # noqa: UP007
    if builder.trigger is not None:
        fields["trigger"] = (Union[builder.trigger, None], None)  # noqa: UP007
    if shared.followup is not None and "active" in plan.kinds:
        fields["followup"] = (shared.followup | None, Field(default=None))
    name = "SkillProposal" if plan.id == STANDARD_LAYOUT else f"SkillProposal_{plan.id}"
    return create_model(
        name,
        __base__=_Proposal,
        __doc__=_SKILL_DOC if plan.id == STANDARD_LAYOUT else None,
        **fields,
    )


def build_proposal_models(
    library: ContentLibrary,
    *,
    primitives: Iterable[str] | None = None,
    shapes: Iterable[str] | None = None,
    conditions: Iterable[str] | None = None,
    triggers: Iterable[str] | None = None,
    skeletons: Iterable[str] | None = None,
    rarity: SkillRarity | None = None,
    followup: bool = True,
    followup_skeletons: Iterable[str] | None = None,
    followup_shapes: Iterable[str] | None = None,
    followup_moves: Iterable[str] = (),
) -> ProposalModels:
    """由內容庫產生提議模型（原語的參數、範圍與可用值全部取自內容資料，不寫死在這裡）。

    ``primitives``、``shapes``、``conditions``、``triggers``、``skeletons`` 只開放這些值（呼叫端依
    稀有度、骨架與題目先篩選，縮小 JSON Schema；``None`` 為全部，Phase 4-L4）。篩掉的值被提議時在
    提議格式階段得到 ``union_tag_invalid``（形狀、條件、觸發）或 ``literal_error``（骨架）。
    條件（或觸發）全部篩掉時，提議不再有 ``condition``（或 ``trigger``）欄位；``kind`` 也只留
    所選骨架適用的種類。巢狀參數沒有可用原語的原語會被排除並記在 ``excluded_primitives``。

    頂層是以 ``layout`` 區分的版型（Phase 4-L5b，見 :mod:`trpg.skillgen.proposal_layouts`）：有組合
    規則的原語各自一個版型，形狀與其他效果依 ``skill_primitives.yaml`` 的組合規則限制。``rarity``
    有給時，``apply_status`` 只列這個稀有度能用的狀態。

    Phase 4-L8 起另開放：反應技能（``reaction``，所選骨架有反應技時）、複合技能第二段
    （``followup``，有主動技能的版型、稀有度不低於複合技能的最低稀有度；``followup=False`` 時不
    開放；第二段的骨架與形狀另由 ``followup_skeletons``／``followup_shapes`` 指定，``None`` ＝
    與第一段相同的骨架、全部形狀；``followup_moves`` 是子集外也開放給第二段的施放者自身位移）、
    代價類欄位（見 :mod:`trpg.skillgen.proposal_costs`）。"""
    statuses = None if rarity is None else rarity_statuses(library, rarity)
    builder = _Builder(
        library,
        _only(primitives),
        _only(shapes),
        _only(conditions),
        _only(triggers),
        statuses=statuses,
        extra_shapes=frozenset(followup_shapes or ()),
    )
    skeleton_ids = _skeleton_choices(library, skeletons)
    plans, layout_excluded = plan_layouts(
        library,
        primitives=builder.effects,
        shapes=builder.shapes,
        kinds=kind_choices(library, skeleton_ids),
    )
    if not plans:
        raise ValueError("提議模型沒有任何可用的版型（篩選後沒有可以組成技能的原語與形狀）")
    shared = _shared_types(library, builder, plans)
    skeleton_type = _alias("Skeleton", _literal(skeleton_ids))
    if followup and composite_allowed(rarity) and any("active" in p.kinds for p in plans):
        second = _followup_skeletons(library, skeleton_ids, followup_skeletons, skeleton_type)
        shape_ids = builder.all_shapes if followup_shapes is None else followup_shapes
        shared = replace(
            shared,
            followup=_followup_model(
                library, builder, shared, second, shape_ids, moves=followup_moves
            ),
        )
    sk = SkillDef.model_fields
    common: dict[str, Any] = {
        # 名稱不在提議裡（4-L8，PM 追加）：由命名步驟（4-L7）產生，沒有命名時用組合式名稱
        "description_zh": (str | None, None),
        "concept": (str, Field(default="", max_length=80)),
        "cast_flavor": (str, Field(default="", max_length=80)),
        "skeleton": (skeleton_type, ...),
        "category": (sk["category"].annotation, ...),
        "weapon_req": (sk["weapon_req"].annotation, ...),
        "scaling_attr": (sk["scaling_attr"].annotation, ...),
        # 技能元素（3-54d）：選填；隆起、下陷、石膚、震波只有 earth 的技能能用（同一條互斥規則）
        "element": (sk["element"].annotation, None),
        "cost_penalty": (
            _penalty_type(penalty_choices(library, rarity)),
            Field(default=None, description=COST_DOCS["cost_penalty"]),
        ),
        "cost_overdraft": (
            Literal[True] | None,
            Field(default=None, description=COST_DOCS["cost_overdraft"]),
        ),
        "cost_once_per_battle": (
            Literal[True] | None,
            Field(default=None, description=COST_DOCS["cost_once_per_battle"]),
        ),
        "cost_hp": (Literal[True] | None, Field(default=None, description=COST_DOCS["cost_hp"])),
    }
    if "reaction" in kind_choices(library, skeleton_ids):
        common["reaction"] = (_reaction_model(library) | None, Field(default=None))
    if on_miss_allowed(rarity):
        common["cost_on_miss"] = (
            _list_of(builder.backlash_union()) | None,
            Field(
                default=None,
                min_length=1,
                max_length=_MAX_NESTED,
                description=COST_DOCS["cost_on_miss"],
            ),
        )
    hints = {p.id: layout_hint(library, p) for p in plans}
    layouts = [_layout_model(builder, p, common, shared) for p in plans]
    skill = layouts[0] if len(layouts) == 1 else _union(layouts, "layout")
    used = {i for p in plans for i in (*p.effects, *p.self_effects)}
    lookup = sorted(i for i in builder.lookup_ids if i in used)
    excluded = (
        *builder.excluded,
        *layout_excluded,
        *((i, "lookup_by_skill_id：只能用在主效果，不能用在變奏") for i in lookup),
    )
    return ProposalModels(
        skill=skill,
        primitive_ids=tuple(i for i in builder.effects if i in used),
        variant_primitive_ids=shared.variant_ids,
        excluded_primitives=excluded,
        layouts=tuple((p.id, hints[p.id]) for p in plans),
    )


# ---------------------------------------------------------------------------
# 轉換
# ---------------------------------------------------------------------------


def _skill_id(body: Mapping[str, Any]) -> str:
    text = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return LLM_ID_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _stack_target(effect: Any, library: ContentLibrary) -> Any:
    """累積／消耗層數的效果：``affects`` 由層數的 ``owner`` 決定（累積在自己身上 → ``self``，疊在
    敵人身上 → ``enemies``）；LLM 填的對象不採用。"""
    if not isinstance(effect, dict) or effect.get("type") not in ("add_stack", "consume_stack"):
        return effect
    stack = library.ruleset.stacks.by_id().get(str(effect.get("stack")))
    if stack is None:
        return effect
    if stack.owner == "target":  # 省略時預設就是敵方；有填才改成敵方
        return {**effect, "affects": "enemies"} if "affects" in effect else effect
    return {**effect, "affects": "self"}


def _skill_data(
    proposal: BaseModel,
    ctx: ProposalContext,
    fill: NumberFiller,
    library: ContentLibrary | None = None,
) -> dict[str, Any]:
    data = proposal.model_dump(mode="json", exclude_none=True)
    data.pop("layout", None)
    penalty = data.pop("cost_penalty", None)  # 自己付的代價（3-50）→ cost.self_status／overdraft
    if penalty is not None:
        data["cost"] = {**data.get("cost", {}), **penalty_cost(library, penalty)}
    if data.pop("cost_overdraft", None):  # 透支（3-50b）：不算自身狀態，可以並用
        data["cost"] = {**data.get("cost", {}), "overdraft": 1}
    apply_cost_choices(data, library)  # 每場一次、HP 代價、失手反噬（4-L8）
    if library is not None:  # 層數的對象由層數決定（3-52），LLM 只挑層數
        data["effects"] = [_stack_target(e, library) for e in data.get("effects", [])]
    data["narrative"] = {"concept": data.pop("concept"), "cast_flavor": data.pop("cast_flavor")}
    data.update(tier=ctx.tier, rarity=ctx.rarity, rank=ctx.rank)
    data["provenance"] = {"origin": ctx.origin, "created_by": "llm"}
    data = fill(data)
    data["name_zh"] = _combined_name(data, library)
    data["id"] = _skill_id(data)
    return data


PLACEHOLDER_NAME = "提議技能"
"""結構不合法、算不出組合式名稱時的名稱（轉換會在 ``skill`` 階段報錯，不會出現在遊戲裡）。"""


def combined_skill_name(library: ContentLibrary, skill: SkillDef) -> str:
    """組合式名稱「元素・骨架」（沒有元素就只有骨架；和隨機組合器、4-L7 的退回名稱同一做法）。
    LLM 提議沒有名稱欄位（4-L8）：轉成技能時先用它，命名步驟（``trpg.llm.naming``）再換成
    生成的名稱。"""
    skeleton = plain_name(skill.skeleton, library)
    elements = sorted(e.display_name for e in skill_elements(skill))
    return f"{elements[0]}・{skeleton}" if elements else skeleton


def _combined_name(data: dict[str, Any], library: ContentLibrary | None) -> str:
    if library is None:
        return PLACEHOLDER_NAME
    try:
        probe = SkillDef.model_validate({**data, "name_zh": PLACEHOLDER_NAME, "id": "skill_probe"})
    except ValidationError:
        return PLACEHOLDER_NAME
    return combined_skill_name(library, probe)


def to_skill_def(
    proposal: BaseModel,
    ctx: ProposalContext,
    fill: NumberFiller,
    library: ContentLibrary | None = None,
) -> SkillDef:
    """已驗證的提議（只有結構）→ :class:`SkillDef`：``fill`` 補上數值（骰子、倍率、持續、AP、法力、
    冷卻等；見 :mod:`trpg.skillgen.proposal_numbers`）。ID 由補完數值後的內容雜湊而來；同一份
    提議加同一份數值永遠得到相同 ID。``ctx.hero_attributes`` 有值（且給了 ``library``）時縮放屬性
    改取主角最高的允許屬性（見 :class:`ProposalContext`）。

    schema 層級的錯誤丟 :class:`pydantic.ValidationError`（:func:`evaluate_proposal` 轉成
    ``stage="skill"`` 的錯誤）。"""
    data = _skill_data(proposal, ctx, fill, library)
    skill = SkillDef.model_validate(data)
    if library is None:
        return skill
    # 武器技一律看武器大類的主屬性（3H-6，不看主角屬性）；其他技能跟主角最高屬性（3H-3）；
    # 沒有主角屬性時收進允許範圍（3H-7：在範圍內不動，否則取範圍裡第一個）
    fitted = (
        fit_scaling(skill, library)
        if ctx.hero_attributes is None
        else grant_dual(  # 3I-3：稀有以上、主角第二高與最高差 ≤ 4 時，以 30% 機率加心智第二屬性
            retarget_scaling(skill, ctx.hero_attributes, library), ctx.hero_attributes, library
        )
    )
    attr, second = fitted.scaling_attr, fitted.secondary_scaling_attr
    if attr == skill.scaling_attr and second == skill.secondary_scaling_attr:
        return skill
    data = {k: v for k, v in data.items() if k not in ("id", "secondary_scaling_attr")}
    data["scaling_attr"] = attr.value
    if second is not None:
        data["secondary_scaling_attr"] = second.value
    data["id"] = _skill_id(data)
    return SkillDef.model_validate(data)


_SUPPORTED_SKILL_KEYS = frozenset(
    {
        "id",
        "schema_version",
        "description_zh",
        "tier",
        "rank",
        "rarity",
        "kind",
        "skeleton",
        "category",
        "weapon_req",
        "ap_cost",
        "scaling_attr",
        "element",
        "shape",
        "effects",
        "condition",
        "trigger",
        "cost",
        "cost_penalty",
        "cost_overdraft",
        "cost_once_per_battle",
        "cost_hp",
        "cost_on_miss",
        "reaction",
        "followup",
        "tags",
        "narrative",
        "provenance",
        "variants",
    }
)


def proposal_from_skill(skill: SkillDef, library: ContentLibrary) -> dict[str, Any]:
    """手寫技能 → 提議 JSON（few-shot 範例與結構往返測試用；數值欄位已移除）。用到提議模型沒有的
    欄位時丟 ``ValueError``。要連同數值一起取得時用
    :func:`~trpg.skillgen.proposal_numbers.split_numbers`。"""
    full = skill.model_dump(mode="json", exclude_defaults=True)
    data, _ = split_numbers(full, library)
    data.update(cost_choices_of(full.get("cost") or {}, data))  # 4-L8 的代價欄位
    data.pop("name_zh", None)  # 名稱由命名步驟產生（4-L8），不在提議裡
    if isinstance(data.get("cost"), dict):  # 自己付的代價（3-50）→ cost_penalty
        penalty, overdraft = penalty_of_cost(data["cost"])
        if penalty is not None:
            data["cost_penalty"] = penalty
        if overdraft:
            data["cost_overdraft"] = True
        if not data["cost"]:
            del data["cost"]
    unsupported = sorted(set(data) - _SUPPORTED_SKILL_KEYS)
    if unsupported:
        raise ValueError(f"{skill.id} 用到提議格式沒有的欄位：{', '.join(unsupported)}")
    for key in CALLER_FIELDS:
        data.pop(key, None)
    narrative = data.pop("narrative", {})
    data["concept"] = narrative.get("concept", "")
    data["cast_flavor"] = narrative.get("cast_flavor", "")
    data["kind"] = skill.kind
    return {"layout": skill_layout(library, skill), **data}


# ---------------------------------------------------------------------------
# 錯誤回饋
# ---------------------------------------------------------------------------

_QUOTED = re.compile(r"'([^']*)'")
_PATH_PREFIX = re.compile(r"^([A-Za-z_][\w.\[\]]*)：(.*)$", re.DOTALL)


def _json_path(loc: Sequence[int | str], data: object) -> str:
    """pydantic 的 ``loc`` → JSON 路徑；discriminated union 插在路徑裡的標籤（例如 ``damage``）
    依原始輸入去掉，讓路徑與 LLM 送來的 JSON 一致。"""
    parts: list[str] = []
    node: object = data
    for item in loc:
        if isinstance(item, int):
            parts.append(f"[{item}]")
            node = node[item] if isinstance(node, list) and item < len(node) else None
            continue
        if (
            isinstance(node, dict)
            and item not in node
            and item
            in (
                node.get("type"),
                node.get("event"),
                node.get("layout"),
                _GENERAL_TAG,
            )
        ):
            continue  # union 標籤
        parts.append(f".{item}" if parts else item)
        node = node.get(item) if isinstance(node, dict) else None
    return "".join(parts)


_MESSAGES: dict[str, Callable[[Mapping[str, Any]], str]] = {
    "missing": lambda _: "缺少必填欄位",
    "extra_forbidden": lambda _: "不認得的欄位（這個類型沒有這個參數）",
    "literal_error": lambda _: "不是可用的值",
    "enum": lambda _: "不是可用的值",
    "union_tag_invalid": lambda c: f"未知的類型 {c.get('tag')!r}",
    "union_tag_not_found": lambda c: f"缺少區分類型的欄位 {c.get('discriminator')}",
    "greater_than_equal": lambda c: f"必須 ≥ {c.get('ge')}",
    "less_than_equal": lambda c: f"必須 ≤ {c.get('le')}",
    "string_pattern_mismatch": lambda c: f"格式不符（{c.get('pattern')}）",
    "too_long": lambda c: f"最多 {c.get('max_length')} 項",
    "too_short": lambda c: f"至少 {c.get('min_length')} 項",
}
"""常見的 pydantic 錯誤型別 → 中文原因（其餘沿用原訊息；自訂驗證器的訊息本來就是中文）。"""
_ALLOWED_CTX = {
    "literal_error": "expected",
    "enum": "expected",
    "union_tag_invalid": "expected_tags",
}
"""哪些錯誤型別的 ``ctx`` 帶有可用值清單。"""


def _message_zh(error: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    kind = str(error["type"])
    ctx: Mapping[str, Any] = error.get("ctx") or {}
    render = _MESSAGES.get(kind)
    message = render(ctx) if render else str(error["msg"]).removeprefix("Value error, ")
    key = _ALLOWED_CTX.get(kind)
    allowed = tuple(_QUOTED.findall(str(ctx.get(key, "")))) if key else ()
    return message, allowed


_EFFECT_REF = re.compile(r"(?:followup\.)?effects\[\d+\](?:\.[A-Za-z_]\w*)?")


def _skill_path(error: Mapping[str, Any], loc_path: str, message: str) -> str:
    """``SkillDef`` 自己的檢查（``stage: skill``）的路徑（Phase 4-L5b）：驗證器以
    :class:`~trpg.content.skills.SkillRuleError` 帶出的路徑優先；否則從訊息找 ``effects[i]``；
    訊息講形狀時指向 ``shape``；都沒有就只用 pydantic 的位置（技能層級為空字串）。"""
    raw = (error.get("ctx") or {}).get("error")
    found = ""
    if isinstance(raw, SkillRuleError):
        found = raw.path
    elif (match := _EFFECT_REF.search(message)) is not None:
        found = match.group(0)
    elif "形狀" in message:
        found = "shape"
    if not found:
        return loc_path
    return f"{loc_path}.{found}" if loc_path else found


def _pydantic_errors(exc: ValidationError, stage: Stage, data: object) -> list[ProposalError]:
    out: list[ProposalError] = []
    for error in exc.errors(include_url=False):
        message, allowed = _message_zh(error)
        path = _json_path(tuple(error["loc"]), data)
        code = str(error["type"])
        if stage == "skill":
            path = _skill_path(error, path, message)
            raw = (error.get("ctx") or {}).get("error")
            if isinstance(raw, SkillRuleError) and raw.code:
                code = raw.code
        out.append(
            ProposalError(
                stage=stage,
                path=path,
                code=code,
                message=message,
                allowed=allowed,
            )
        )
    return out


def _rule_error(rule: str, message: str) -> ProposalError:
    match = _PATH_PREFIX.match(message)
    if match is None:
        return ProposalError(stage="rules", path="", code=rule, message=message)
    return ProposalError(stage="rules", path=match.group(1), code=rule, message=match.group(2))


def _layout_hints(errors: list[ProposalError], models: ProposalModels) -> list[ProposalError]:
    """頂層缺 ``layout`` 時，``allowed`` 列出可用的版型（pydantic 的錯誤不帶這份清單）。"""
    layouts = tuple(f for f, _ in models.layouts)
    return [
        replace(e, path="layout", message="缺少版型欄位 layout", allowed=layouts)
        if e.code == "union_tag_not_found" and e.path == "" and layouts
        else e
        for e in errors
    ]


def evaluate_proposal(
    raw: str | Mapping[str, Any],
    models: ProposalModels,
    library: ContentLibrary,
    ctx: ProposalContext,
    *,
    fill: NumberFiller | None = None,
) -> ProposalResult:
    """驗證一份提議：提議格式 → 補數值並轉成技能 → 跨檔案驗證與預算（``validate_skill``）。

    ``fill`` 補數值；省略時用保守的最小補值（``proposal_numbers.minimal_filler``，不保證通過預算；
    正式流程由 4-L5 傳入預算器）。"""
    try:
        data: object = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except json.JSONDecodeError as exc:
        error = ProposalError("proposal", "", "json_invalid", f"不是合法的 JSON：{exc.msg}")
        return ProposalResult(None, (error,))
    try:
        proposal = TypeAdapter(models.skill).validate_python(data)
    except ValidationError as exc:
        errors = _layout_hints(_pydantic_errors(exc, "proposal", data), models)
        return ProposalResult(None, tuple(errors))
    try:
        skill = to_skill_def(proposal, ctx, fill or minimal_filler(library), library)
    except ValidationError as exc:
        return ProposalResult(None, tuple(_pydantic_errors(exc, "skill", data)))
    violations = validate_skill(skill, library)
    if violations:
        return ProposalResult(None, tuple(_rule_error(v.rule, v.message) for v in violations))
    extra = [*_unheld_errors(skill, ctx), *_topic_errors(skill, ctx, library)]
    return ProposalResult(None, tuple(extra)) if extra else ProposalResult(skill, ())


def _topic_errors(
    skill: SkillDef, ctx: ProposalContext, library: ContentLibrary
) -> list[ProposalError]:
    """題目要求（Phase 4-L6）：帶到題目的關鍵字、用到指定的核心原語。沒有題目要求時不檢查。"""
    errors: list[ProposalError] = []
    if ctx.keywords:
        found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
        lacking = tuple(k for k in ctx.keywords if k not in found)
        if lacking:
            errors.append(
                ProposalError(
                    stage="rules",
                    path="effects",
                    code="keyword.required",
                    message=f"技能必須製造或利用題目的關鍵字 {'、'.join(lacking)}，但提議沒有帶到",
                    allowed=lacking,
                )
            )
    if ctx.weapon_class is not None:
        problem = weapon_problem(skill, ctx.weapon_class, ctx.held or {})
        if problem is not None:
            errors.append(
                ProposalError(
                    stage="rules",
                    path="weapon_req",
                    code="weapon.incompatible",
                    message=f"技能與主角的武器不相容：{problem}",
                )
            )
    core = ctx.core_primitive
    if core is not None and all(e.type != core for e in skill.effects):
        errors.append(
            ProposalError(
                stage="rules",
                path="effects",
                code="core.required",
                message=f"題目指定核心原語 {core}：effects 裡必須有 type 為 {core} 的效果",
                allowed=(core,),
            )
        )
    return errors


def _unheld_errors(skill: SkillDef, ctx: ProposalContext) -> list[ProposalError]:
    """武器親和條件指定了主角沒拿的裝備（Phase 3I-5）：加成永遠不會成立，退回重提。"""
    if ctx.held is None:
        return []
    allowed = tuple(sorted(ctx.held))
    return [
        ProposalError(
            stage="rules",
            path="effects",
            code="gear.not_held",
            message=f"武器親和只能指定主角手上的裝備，收到 {cond.weapon}",
            allowed=allowed,
        )
        for cond in skill_condition_specs(skill)
        if cond.type == WIELDING_WEAPON and cond.weapon not in ctx.held
    ]


def feedback_payload(errors: Sequence[ProposalError], attempt: int, max_attempts: int) -> str:
    """重試時附給 LLM 的錯誤（JSON 文字；放在指令區之外的資料區）。"""
    body = {
        "attempt": attempt,
        "max_attempts": max_attempts,
        "errors": [e.to_json() for e in errors],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)
