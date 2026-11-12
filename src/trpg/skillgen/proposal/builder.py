"""由內容庫產生效果、形狀、條件、觸發、變奏、反應的提議模型（:class:`_Builder`）。

自 :mod:`trpg.skillgen.proposal` 拆出（Phase R1d），內容未改。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated, Any, Literal, Union, get_args

from pydantic import (
    Discriminator,
    Field,
    Tag,
    create_model,
)

from trpg.content.battle import ID_PATTERN
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    BACKLASH_TYPES,
    SKILL_REACTION_EVENTS,
    VARIANT_CONDITIONS,
    ZONE,
    EffectSpec,
    NestedOnlyDef,
    PrimitiveDef,
    PrimitiveParam,
    TriggerSpec,
)
from trpg.shared.types import Element
from trpg.skillgen.proposal.models import (
    _MAX_NESTED,
    NESTED_EFFECT_TYPES,
    _alias,
    _get,
    _id_choice,
    _list_of,
    _literal,
    _Proposal,
    _union,
    _union_or_none,
)
from trpg.skillgen.proposal.params import (
    _CONDITION_FIELDS,
    _SELF_AFFECTS_DOC,
    _ZONE_AFFECTS_DOC,
    ZONE_AFFECTS,
    _affects_type,
    _field,
    _has_nested,
    _is_numeric,
    _param_type,
    _Refs,
    _required,
    _split_effect,
    _top_only_params,
    budget_statuses,
)
from trpg.skillgen.validate import RARITY_STATUS_PRIMITIVES


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
        # 巢狀位置（then、win／lose、on_kill、zone 的 effects）不能再巢狀：用去掉巢狀參數的模型；
        # 也沒有只能用在技能自己的傷害的旗標（TOP_ONLY_DAMAGE_PARAMS，4-L10a）。
        leaves = {p.id: self._effect_model(p, None, inner=True) for p in primitives}
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
            elif _top_only_params(p):
                self.effects[p.id] = self._effect_model(p, None)
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

    def restricted(self, primitive_id: str, param: str, value: str) -> Any:
        """``param`` 固定為 ``value`` 的版本（版型依參數分支用：瞬步的 ``landing``、持續區域的
        ``anchor``；Phase 4-L10a A3）。"""
        primitive = self.defs[primitive_id]
        return self._effect_model(primitive, self.nested.get(primitive_id), fixed={param: value})

    def _effect_model(
        self,
        primitive: PrimitiveDef,
        nested: Mapping[str, Any] | None,
        *,
        self_only: bool = False,
        mode: Literal["effect", "backlash"] = "effect",
        inner: bool = False,
        fixed: Mapping[str, str] | None = None,
    ) -> Any:
        """一個原語的提議模型；``nested`` 為 ``None`` 時是巢狀位置用的版本（沒有巢狀參數）；
        ``self_only`` 是「其他效果只作用在施放者」的版型用的版本；``mode="backlash"`` 是失手
        反噬用的版本（沒有 ``affects``、``condition``）。

        Phase 4-L10a：``inner``（巢狀位置）與失手反噬的版本沒有只能用在技能自己的傷害的旗標
        （:data:`TOP_ONLY_DAMAGE_PARAMS`）；失手反噬的 ``apply_status`` 不列硬控、跳過回合與持續
        傷害的狀態；持續區域的 ``affects`` 必填；``fixed`` 把參數固定成一個值（版型分支用）；
        「恰好填一個」的參數（``inscribe`` 的 ``element``／``tag``）與 ``split_heal``（須
        ``affects: all``）拆成以欄位區分的分支（見 :func:`_split_effect`）。"""
        fields: dict[str, Any] = {
            "type": (_literal((primitive.id,)), Field(description=primitive.name_zh)),
        }
        if mode == "effect":
            fields["affects"] = self._affects_field(primitive, self_only=self_only)
            if self.condition is not None:
                fields["condition"] = (Union[self.condition, None], None)  # noqa: UP007
        drop = _top_only_params(primitive) if inner or mode == "backlash" else frozenset()
        for name, spec in sorted(primitive.params.items()):
            doc = spec.llm_hint
            if _is_numeric(spec) or name in drop:
                continue
            if spec.type == "effects":
                if nested is None or nested[name] is None:
                    continue
                limits = {"min_length": 1, "max_length": _MAX_NESTED}
                fields[name] = _field(nested[name], limits, required=spec.required, doc=doc)
                continue
            if fixed is not None and name in fixed:
                fields[name] = (_literal((fixed[name],)), Field(description=doc or None))
                continue
            annotation, limits = self._param(primitive, name, spec, backlash=mode == "backlash")
            fields[name] = _field(annotation, limits, required=_required(spec), doc=doc)
        if mode == "backlash":
            prefix = "BacklashEffect"
        elif self_only:
            prefix = "SelfEffect"
        elif inner and (_has_nested(primitive) or _top_only_params(primitive)):
            prefix = "NestedEffect"
        else:
            prefix = "Effect"
        name = f"{prefix}_{primitive.id}"
        if fixed:
            name += "".join(f"_{v}" for _, v in sorted(fixed.items()))
        return _split_effect(name, primitive, fields, fixed_affects=self_only or mode == "backlash")

    def _affects_field(self, primitive: PrimitiveDef, *, self_only: bool) -> tuple[Any, Any]:
        if self_only:
            return (Literal["self"], Field(default="self", description=_SELF_AFFECTS_DOC))
        if primitive.id == ZONE:  # 持續區域：affects 必填（驗證器 _check_zone_effect）
            values = [v for v in ZONE_AFFECTS if v in get_args(_affects_type(primitive))]
            return (_literal(values), Field(description=_ZONE_AFFECTS_DOC))
        return (_affects_type(primitive) | None, None)

    def _param(
        self, primitive: PrimitiveDef, name: str, spec: PrimitiveParam, *, backlash: bool = False
    ) -> tuple[Any, dict[str, Any]]:
        """參數型別；稀有度檢查狀態的原語（``apply_status``）只列稀有度夠的狀態（Phase 4-L5b）；
        以狀態點數計預算的原語（``budget_basis: status``）只列有 ``budget_points`` 的狀態
        （4-L5c）；失手反噬不列不能當反噬的狀態（硬控、跳過回合、持續傷害；4-L10a）。"""
        if spec.type == "status":
            ids = self._status_choices(primitive)
            if backlash:
                unsafe = self.library.ruleset.unsafe_backlash_statuses()
                base = self.refs.statuses if ids is None else ids
                ids = tuple(i for i in base if i not in unsafe)
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
            if (only is not None and cond.id not in only) or cond.enemy_only:
                continue  # enemy_only（LW-1）：只給敵人專用招，LLM 提議不開放
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


def _surface_ids(library: ContentLibrary) -> tuple[str, ...]:
    """``surfaces.yaml`` 的表面 ID（變奏條件可用的表面；驗證器同一份表）。"""
    return tuple(s.id.value for s in library.ruleset.surfaces.surfaces)


_WHEN_DOCS: dict[str, str] = {
    "caster_surface": "施放者所在格的表面是其中之一",
    "caster_high_ground": "施放者所在格比目標點高（填 true）",
    "caster_adjacent_blocker": "施放者相鄰的格子有牆壁或阻擋物（填 true）",
    "target_surface": "目標點的表面是其中之一",
}


def _when_model(surfaces: Sequence[str]) -> Any:
    """變奏條件 ``when``（Phase 4-L10a A3、A4）：四種條件各一支、恰好填一種（驗證器
    :class:`~trpg.content.skills.VariantWhen`）；表面只列 ``surfaces.yaml`` 的表面。分支以填了
    哪個欄位區分（標籤含 ``~``）。"""
    surface: Any = _literal(surfaces) if surfaces else Annotated[str, Field(pattern=ID_PATTERN)]
    listed = (_list_of(surface), Field(min_length=1, max_length=len(surfaces) or None))
    types: dict[str, Any] = {
        "caster_surface": listed,
        "caster_high_ground": (Literal[True], ...),
        "caster_adjacent_blocker": (Literal[True], ...),
        "target_surface": listed,
    }
    branches = []
    for name in VARIANT_CONDITIONS:
        model = create_model(
            f"When_{name}",
            __base__=_Proposal,
            __doc__=f"變奏條件（四種恰好填一種）：{_WHEN_DOCS.get(name, name)}。",
            **{name: types[name]},
        )
        branches.append(Annotated[model, Tag(f"when~{name}")])

    def pick(value: Any) -> str:
        found = next((n for n in VARIANT_CONDITIONS if _get(value, n) is not None), None)
        return f"when~{found or VARIANT_CONDITIONS[0]}"

    return _alias("VariantWhen", Annotated[Union[tuple(branches)], Discriminator(pick)])  # noqa: UP007


def _variant_model(effect: Any | None, shape: Any, surfaces: Sequence[str] = ()) -> Any:
    """戰場變奏；``effect`` 是變奏能加入或替換的效果（不含 ``lookup_by_skill_id`` 原語），
    ``None`` 時不開放 ``add_effect``／``replace_effect``。"""
    fields: dict[str, Any] = {
        "id": (str, Field(pattern=ID_PATTERN)),
        "name_zh": (str, Field(min_length=1, max_length=12)),
        "when": (_when_model(surfaces), ...),
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
