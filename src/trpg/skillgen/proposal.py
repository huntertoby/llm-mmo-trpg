"""LLM 技能提議模型（Phase 3E-2g 原型；設計見 ``docs/phases/Phase4-LLM技能提議設計.md``）。

LLM 不直接寫 :class:`~trpg.content.skills.SkillDef`（扁平的 ``EffectSpec`` 有約 40 個選填欄位，
LLM 容易填錯又難以定位），而是填「提議」：效果、形狀、條件、觸發都是以 ``type``（觸發為 ``event``）
區分的 discriminated union，每一支只有該原語自己的參數，範圍與可用值取自內容資料
（``skill_primitives.yaml`` 的 ``params``、``skill_shapes.yaml``、``skill_conditions.yaml``、
``skill_triggers.yaml`` 與各 ID 表）。

流程：:func:`build_proposal_models` 由內容庫產生模型與 JSON Schema → :func:`evaluate_proposal`
依序做「提議驗證（``proposal``）→ 轉成 ``SkillDef``（``skill``）→ 跨檔案驗證與預算（``rules``）」，
任一階段失敗就回傳結構化的 :class:`ProposalError`（路徑、代碼、中文原因、可用值），給 LLM 重試。

ID、稀有度、階級、來源由呼叫端（:class:`ProposalContext`）決定，LLM 不能填。原型不涵蓋的部分
（複合技能第二段、反應、陷阱、修正規則、非原語的巢狀效果等）見設計文件。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Union, get_args

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, create_model

from trpg.content.battle import ID_PATTERN
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    AFFECTS_VALUES,
    CONSUME_THEN_TYPES,
    GAMBLE_BRANCH_TYPES,
    ON_KILL_TYPES,
    SKILL_ID_PATTERN,
    ZONE_EFFECT_TYPES,
    EffectSpec,
    Origin,
    PrimitiveDef,
    PrimitiveParam,
    SkillDef,
    SkillRarity,
    VariantWhen,
)
from trpg.shared.types import Element, Surface
from trpg.skillgen.validate import validate_skill

__all__ = [
    "LLM_ID_PREFIX",
    "ProposalContext",
    "ProposalError",
    "ProposalModels",
    "ProposalResult",
    "build_proposal_models",
    "evaluate_proposal",
    "feedback_payload",
    "proposal_from_skill",
    "to_skill_def",
]

LLM_ID_PREFIX = "skill_llm_"
DICE_PATTERN = r"^[1-9][0-9]*d[1-9][0-9]*$"

PROPOSAL_KINDS: tuple[str, ...] = ("active", "passive", "stance")
"""原型開放的技能種類（反應、修正型需要 ``reaction``／``modifiers``，原型不開放）。"""
CLOSED_SKELETONS: frozenset[str] = frozenset({"reaction", "modifier", "trap"})
"""原型不開放的骨架（需要提議模型沒有的欄位）。"""

NESTED_EFFECT_TYPES: dict[str, tuple[str, ...]] = {
    "then": CONSUME_THEN_TYPES,
    "win": GAMBLE_BRANCH_TYPES,
    "lose": GAMBLE_BRANCH_TYPES,
    "on_kill": ON_KILL_TYPES,
    "effects": ZONE_EFFECT_TYPES,
}
"""巢狀效果參數（``type: effects``）可用的效果類型；只開放其中是原語的類型（``refund_ap``、
``damage_multiplier`` 等非原語效果原型不開放）。"""
_MAX_NESTED = 2
_MAX_EFFECTS = 4
_MAX_VARIANTS = 2
_MAX_TAGS = 8
_MAX_AP = 3
_MAX_COOLDOWN = 6

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
    """呼叫端決定的欄位（LLM 不能填）：階級、稀有度、等級、來源。"""

    tier: int
    rarity: SkillRarity
    rank: int = 1
    origin: Origin = "level_up"


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
    """由內容庫產生的提議模型。``skill`` 是頂層模型；``excluded_primitives`` 是沒有開放或限制用途的
    原語（與原因）。"""

    skill: type[BaseModel]
    primitive_ids: tuple[str, ...]
    variant_primitive_ids: tuple[str, ...]
    excluded_primitives: tuple[tuple[str, str], ...]

    def json_schema(self) -> dict[str, Any]:
        """給 LLM（structured output／tool input schema）的 JSON Schema。"""
        return self.skill.model_json_schema()


# ---------------------------------------------------------------------------
# 模型產生
# ---------------------------------------------------------------------------


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
        }
        return table.get(param_type)


_FIXED_PARAM_TYPES: dict[str, tuple[Any, dict[str, Any]]] = {
    "dice": (str, {"pattern": DICE_PATTERN}),
    "bool": (bool, {}),
    "element": (Element, {}),
    "surface": (Surface, {}),
    "tag": (str, {"pattern": ID_PATTERN}),
    "skill": (str, {"pattern": SKILL_ID_PATTERN}),
}
"""與內容庫無關的參數型別。"""


def _param_type(
    name: str, spec: PrimitiveParam, refs: _Refs, fallback: Mapping[str, Any]
) -> tuple[Any, dict[str, Any]]:
    """一個參數的型別與 ``Field`` 限制（範圍、格式、可用值）。"""
    if spec.type == "int":
        return int, {"ge": spec.min, "le": spec.max}
    fixed = _FIXED_PARAM_TYPES.get(spec.type)
    if fixed is not None:
        return fixed[0], dict(fixed[1])
    ids = refs.ids_for(spec.type)
    if ids is not None:
        return _id_choice(ids)
    # 其餘型別（which、scale、resource、on_hit、landing、anchor、zone_when、scope、scaling、count）
    # 沿用 EffectSpec 欄位的型別：可用值寫在 schema 的 Literal 或子模型裡。
    return _strip_none(fallback[name].annotation), {}


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


CONDITIONALLY_REQUIRED: frozenset[tuple[str, str]] = frozenset(
    {("damage", "dice"), ("inscribe", "element")}
)
"""YAML 標 ``required: true``、但實際上依情況才必填的參數（照抄
``trpg.content.skills._filled_by_category``：武器技的傷害骰來自武器、符文填了 ``tag`` 可省略
元素）。提議模型讓它們可省略，缺了由 ``rules`` 階段的跨檔案驗證報錯；Phase 4 建議改成 YAML 的
``required_when`` 宣告，讓兩邊同源。"""


def _required(primitive_id: str, name: str, spec: PrimitiveParam) -> bool:
    return spec.required and (primitive_id, name) not in CONDITIONALLY_REQUIRED


def _has_nested(primitive: PrimitiveDef) -> bool:
    return any(p.type == "effects" for p in primitive.params.values())


class _Builder:
    def __init__(self, library: ContentLibrary, only: frozenset[str] | None) -> None:
        self.library = library
        self.refs = _Refs.of(library)
        self.condition = self._condition_union()
        self.shape = self._shape_union()
        primitives = [
            p for p in library.ruleset.primitives.primitives if only is None or p.id in only
        ]
        # 巢狀位置（then、win／lose、on_kill、zone 的 effects）不能再巢狀：用去掉巢狀參數的模型。
        leaves = {p.id: self._effect_model(p, None) for p in primitives}
        self.effects: dict[str, Any] = {}
        self.excluded: list[tuple[str, str]] = []
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
                self.effects[p.id] = self._effect_model(p, nested)
            else:
                self.effects[p.id] = leaves[p.id]
        self.lookup_ids = {
            p.id for p in primitives if p.lookup_by_skill_id and p.id in self.effects
        }

    def _nested_type(self, name: str, leaves: Mapping[str, Any]) -> Any:
        allowed = [t for t in NESTED_EFFECT_TYPES.get(name, ()) if t in leaves]
        if not allowed:
            return None
        item = _union([leaves[t] for t in allowed], "type")
        return _list_of(item)

    def _effect_model(self, primitive: PrimitiveDef, nested: Mapping[str, Any] | None) -> Any:
        """一個原語的提議模型；``nested`` 為 ``None`` 時是巢狀位置用的版本（沒有巢狀參數）。"""
        fields: dict[str, Any] = {
            "type": (_literal((primitive.id,)), Field(description=primitive.name_zh)),
            "affects": (_affects_type(primitive) | None, None),
            "condition": (self.condition | None, None),
        }
        for name, spec in sorted(primitive.params.items()):
            doc = spec.description_zh
            if spec.type == "effects":
                if nested is None or nested[name] is None:
                    continue
                limits = {"min_length": 1, "max_length": _MAX_NESTED}
                fields[name] = _field(nested[name], limits, required=spec.required, doc=doc)
                continue
            annotation, limits = _param_type(name, spec, self.refs, EffectSpec.model_fields)
            required = _required(primitive.id, name, spec)
            fields[name] = _field(annotation, limits, required=required, doc=doc)
        prefix = "NestedEffect" if nested is None and _has_nested(primitive) else "Effect"
        model = create_model(
            f"{prefix}_{primitive.id}",
            __base__=_Proposal,
            __doc__=primitive.player_description or primitive.description_zh,
            **fields,
        )
        return model

    def _condition_union(self) -> Any:
        models = []
        for cond in self.library.ruleset.conditions.conditions:
            fields: dict[str, Any] = {"type": (_literal((cond.id,)), ...)}
            for name, spec in sorted(cond.params.items()):
                annotation, limits = _param_type(name, spec, self.refs, EffectSpec.model_fields)
                fields[name] = _field(
                    annotation, limits, required=spec.required, doc=spec.description_zh
                )
            models.append(
                create_model(
                    f"Condition_{cond.id}",
                    __base__=_Proposal,
                    __doc__=cond.description_zh,
                    **fields,
                )
            )
        return _union(models, "type")

    def _shape_union(self) -> Any:
        models = []
        for shape in self.library.ruleset.shapes.shapes:
            fields: dict[str, Any] = {"type": (_literal((shape.id,)), ...)}
            for name, spec in sorted(shape.params.items()):
                annotation: Any = int
                if spec.allow_weapon:
                    annotation = Union[int, Literal["weapon"]]  # noqa: UP007
                limits = {} if spec.allow_weapon else {"ge": spec.min, "le": spec.max}
                fields[name] = _field(annotation, limits, required=spec.required, doc="")
            models.append(
                create_model(
                    f"Shape_{shape.id}",
                    __base__=_Proposal,
                    __doc__=shape.description_zh,
                    **fields,
                )
            )
        return _union(models, "type")

    def trigger_union(self) -> Any:
        """觸發時機（``skill_triggers.yaml``）：只有「有另一方」的時機能填 ``target: other`` 與
        ``max_distance``；帶參數的時機（``n``、``tag``、``status``、``surface``）的規則目前寫在
        ``TriggerSpec`` 的驗證器裡，原型照抄（Phase 4 建議搬到 YAML 的 ``params``）。"""
        models = []
        for trig in self.library.ruleset.skill_triggers.triggers:
            fields: dict[str, Any] = {
                "event": (_literal((trig.id,)), ...),
                "max_per_round": (int, Field(default=1, ge=1, le=3)),
            }
            if trig.has_other:
                fields["target"] = (Literal["self", "other"], "self")
                fields["max_distance"] = (int | None, Field(default=None, ge=1))
            fields.update(self._trigger_params(trig.id))
            models.append(
                create_model(
                    f"Trigger_{trig.id}",
                    __base__=_Proposal,
                    __doc__=trig.description_zh,
                    **fields,
                )
            )
        return _union(models, "event")

    def _trigger_params(self, event: str) -> dict[str, Any]:
        if event == "every_n_hits":
            return {"n": (Literal[2, 3], ...)}
        if event == "on_cast_tag":
            return {"tag": (str, Field(pattern=ID_PATTERN))}
        if event == "on_status_applied":
            status, limits = _id_choice(self.refs.statuses)
            return {"status": (status | None, Field(default=None, **limits))}
        if event == "on_enter_surface":
            return {"surface": (Surface | None, None)}
        return {}


def _variant_model(effect: Any | None, shape: Any) -> Any:
    """戰場變奏；``effect`` 是變奏能加入或替換的效果（不含 ``lookup_by_skill_id`` 原語），
    ``None`` 時不開放 ``add_effect``／``replace_effect``。"""
    fields: dict[str, Any] = {
        "id": (str, Field(pattern=ID_PATTERN)),
        "name_zh": (str, Field(min_length=1, max_length=12)),
        "when": (VariantWhen, ...),
        "shape": (shape | None, None),
        "range_delta": (int | None, None),
        "element": (Element | None, None),
    }
    if effect is not None:
        swap = create_model(
            "VariantEffectSwap",
            __base__=_Proposal,
            index=(int, Field(ge=0)),
            effect=(effect, ...),
        )
        fields["add_effect"] = (effect | None, None)
        fields["replace_effect"] = (swap | None, None)
    return create_model(
        "Variant",
        __base__=_Proposal,
        __doc__="戰場變奏：when 條件成立時套用 1～2 項替換（shape、range_delta、element、"
        "add_effect、replace_effect）。",
        **fields,
    )


def build_proposal_models(
    library: ContentLibrary, *, primitives: Iterable[str] | None = None
) -> ProposalModels:
    """由內容庫產生提議模型（原語的參數、範圍與可用值全部取自內容資料，不寫死在這裡）。

    ``primitives`` 只開放這些原語（呼叫端依稀有度、骨架與這次升級的主題先篩選，縮小 JSON Schema；
    ``None`` 為全部）。巢狀參數沒有可用原語的原語會被排除並記在 ``excluded_primitives``。"""
    only = None if primitives is None else frozenset(primitives)
    builder = _Builder(library, only)
    primitive_ids = tuple(builder.effects)
    variant_ids = tuple(i for i in primitive_ids if i not in builder.lookup_ids)
    effect = _union([builder.effects[i] for i in primitive_ids], "type")
    variant_effect = (
        _union([builder.effects[i] for i in variant_ids], "type") if variant_ids else None
    )
    skeletons = sorted(set(library.skeletons) - CLOSED_SKELETONS)
    cost = create_model(
        "Cost",
        __base__=_Proposal,
        mana=(int, Field(default=0, ge=0)),
        cooldown=(int | None, Field(default=None, ge=1, le=_MAX_COOLDOWN)),
    )
    sk = SkillDef.model_fields
    variant = _variant_model(variant_effect, builder.shape)
    fields: dict[str, Any] = {
        "name_zh": (str, Field(min_length=1, max_length=12)),
        "description_zh": (str | None, None),
        "concept": (str, Field(default="", max_length=80)),
        "cast_flavor": (str, Field(default="", max_length=80)),
        "kind": (_literal(PROPOSAL_KINDS), ...),
        "skeleton": (_literal(skeletons), ...),
        "category": (sk["category"].annotation, ...),
        "weapon_req": (sk["weapon_req"].annotation, ...),
        "scaling_attr": (sk["scaling_attr"].annotation, ...),
        "ap_cost": (int | None, Field(default=None, ge=1, le=_MAX_AP)),
        "shape": (builder.shape, ...),
        "effects": (_list_of(effect), Field(min_length=1, max_length=_MAX_EFFECTS)),
        "condition": (builder.condition | None, None),
        "trigger": (builder.trigger_union() | None, None),
        "cost": (cost, Field(default_factory=cost)),
        "tags": (
            list[Annotated[str, Field(pattern=ID_PATTERN)]],
            Field(default_factory=list, max_length=_MAX_TAGS),
        ),
        "variants": (_list_of(variant), Field(default_factory=list, max_length=_MAX_VARIANTS)),
    }
    skill = create_model(
        "SkillProposal",
        __base__=_Proposal,
        __doc__="LLM 提議的技能（ID、稀有度、階級與來源由遊戲決定，不要填）。",
        **fields,
    )
    lookup = sorted(builder.lookup_ids)
    excluded = (
        *builder.excluded,
        *((i, "lookup_by_skill_id：只能用在主效果，不能用在變奏") for i in lookup),
    )
    return ProposalModels(
        skill=skill,
        primitive_ids=primitive_ids,
        variant_primitive_ids=variant_ids,
        excluded_primitives=excluded,
    )


# ---------------------------------------------------------------------------
# 轉換
# ---------------------------------------------------------------------------


def _skill_id(body: Mapping[str, Any]) -> str:
    text = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return LLM_ID_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _skill_data(proposal: BaseModel, ctx: ProposalContext) -> dict[str, Any]:
    data = proposal.model_dump(mode="json", exclude_none=True)
    data["narrative"] = {"concept": data.pop("concept"), "cast_flavor": data.pop("cast_flavor")}
    data.update(tier=ctx.tier, rarity=ctx.rarity, rank=ctx.rank)
    data["provenance"] = {"origin": ctx.origin, "created_by": "llm"}
    data["id"] = _skill_id(data)
    return data


def to_skill_def(proposal: BaseModel, ctx: ProposalContext) -> SkillDef:
    """已驗證的提議 → :class:`SkillDef`（ID 由內容雜湊而來；同一份提議永遠得到相同 ID）。

    schema 層級的錯誤丟 :class:`pydantic.ValidationError`（:func:`evaluate_proposal` 轉成
    ``stage="skill"`` 的錯誤）。"""
    return SkillDef.model_validate(_skill_data(proposal, ctx))


_SUPPORTED_SKILL_KEYS = frozenset(
    {
        "id",
        "schema_version",
        "name_zh",
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
        "shape",
        "effects",
        "condition",
        "trigger",
        "cost",
        "tags",
        "narrative",
        "provenance",
        "variants",
    }
)


def proposal_from_skill(skill: SkillDef) -> dict[str, Any]:
    """手寫技能 → 提議 JSON（few-shot 範例與往返測試用）。用到提議模型沒有的欄位時丟
    ``ValueError``。"""
    data = skill.model_dump(mode="json", exclude_defaults=True)
    unsupported = sorted(set(data) - _SUPPORTED_SKILL_KEYS)
    if unsupported:
        raise ValueError(f"{skill.id} 用到提議格式沒有的欄位：{', '.join(unsupported)}")
    for key in CALLER_FIELDS:
        data.pop(key, None)
    narrative = data.pop("narrative", {})
    data["concept"] = narrative.get("concept", "")
    data["cast_flavor"] = narrative.get("cast_flavor", "")
    data["kind"] = skill.kind
    return data


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


def _pydantic_errors(exc: ValidationError, stage: Stage, data: object) -> list[ProposalError]:
    out: list[ProposalError] = []
    for error in exc.errors(include_url=False):
        message, allowed = _message_zh(error)
        out.append(
            ProposalError(
                stage=stage,
                path=_json_path(tuple(error["loc"]), data),
                code=str(error["type"]),
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


def evaluate_proposal(
    raw: str | Mapping[str, Any],
    models: ProposalModels,
    library: ContentLibrary,
    ctx: ProposalContext,
) -> ProposalResult:
    """驗證一份提議：提議格式 → 轉成技能 → 跨檔案驗證與預算（``validate_skill``）。"""
    try:
        data: object = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except json.JSONDecodeError as exc:
        error = ProposalError("proposal", "", "json_invalid", f"不是合法的 JSON：{exc.msg}")
        return ProposalResult(None, (error,))
    try:
        proposal = TypeAdapter(models.skill).validate_python(data)
    except ValidationError as exc:
        return ProposalResult(None, tuple(_pydantic_errors(exc, "proposal", data)))
    try:
        skill = to_skill_def(proposal, ctx)
    except ValidationError as exc:
        return ProposalResult(None, tuple(_pydantic_errors(exc, "skill", data)))
    violations = validate_skill(skill, library)
    if violations:
        return ProposalResult(None, tuple(_rule_error(v.rule, v.message) for v in violations))
    return ProposalResult(skill, ())


def feedback_payload(errors: Sequence[ProposalError], attempt: int, max_attempts: int) -> str:
    """重試時附給 LLM 的錯誤（JSON 文字；放在指令區之外的資料區）。"""
    body = {
        "attempt": attempt,
        "max_attempts": max_attempts,
        "errors": [e.to_json() for e in errors],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)
