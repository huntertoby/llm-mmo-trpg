"""頂層提議模型：版型 × 種類組 × 參數分支 × 技能類別的 union（:func:`build_proposal_models`）。

自 :mod:`trpg.skillgen.proposal` 拆出（Phase R1d），內容未改。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from typing import Annotated, Any, Literal, Union

from pydantic import (
    Discriminator,
    Field,
    Tag,
    create_model,
)

from trpg.content.battle import ID_PATTERN
from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    COMPOSITE_MOVES,
    DELAYED_RELEASE_VALUES,
    FOLLOWUP_WHEN_VALUES,
    MAX_EFFECTS,
    SHADOWSTEP,
    ZONE,
    ZONE_CASTER_SHAPES,
    ZONE_MOVING_SHAPES,
    CompositionRule,
    SkillDef,
    SkillRarity,
    rarity_rank,
)
from trpg.content.skills.constants import SHADOWSTEP_SHAPES
from trpg.skillgen.proposal.builder import _Builder, _reaction_model, _surface_ids, _variant_model
from trpg.skillgen.proposal.models import (
    _GENERAL_TAG,
    _MAX_NESTED,
    _MAX_TAGS,
    _MAX_VARIANTS,
    CLOSED_SKELETONS,
    PROPOSAL_KINDS,
    ProposalModels,
    _alias,
    _get,
    _list_of,
    _literal,
    _Proposal,
    _union_or_none,
)
from trpg.skillgen.proposal.params import rarity_statuses
from trpg.skillgen.proposal_costs import (
    COST_DOCS,
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
)
from trpg.skillgen.self_penalty import penalty_choices
from trpg.skillgen.validate import COMPOSITE_MIN_RARITY


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


_SKILL_DOC = "LLM 提議的技能（ID、稀有度、階級與來源由遊戲決定，不要填）。"


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
    reaction: Any = None
    """反應技能的 ``reaction`` 模型（所選骨架有反應技時；反應技分支必填，4-L10a）。"""


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
    variant = _variant_model(variant_effect, shape, _surface_ids(library))
    return _Shared(frozenset(general_ids), general, self_general, shape, variant, variant_ids)


def _effect_tag(value: Any) -> str | None:
    raw = value.get("type") if isinstance(value, dict) else getattr(value, "type", None)
    return raw if isinstance(raw, str) else None


def _layout_effects(
    builder: _Builder,
    plan: LayoutPlan,
    shared: _Shared,
    models: Mapping[str, Any] | None = None,
) -> Any:
    """版型的效果 union：特殊原語各一支（標籤是原語 ID），一般原語共用一個具名 union；
    ``models`` 可換掉特殊原語的模型（參數分支，4-L10a）。"""
    if plan.self_effects:
        members = list(plan.effects)
        general = shared.self_general
    else:
        members = [i for i in plan.effects if i not in shared.general_ids]
        has_general = any(i in shared.general_ids for i in plan.effects)
        general = shared.general if has_general else None
    return _tagged_effects(builder.effects if models is None else models, members, general)


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


WEAPON_REQ_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "weapon": ("melee", "ranged"),
    "spell": ("focus", "any"),
}
"""技能類別 → 可用的武器需求（驗證器 ``SkillDef`` 的 weapon_req 檢查；Phase 4-L10a A2）。

``split_category=True`` 時頂層依類別分支，武器技只列 melee／ranged、法術技只列 focus／any；
預設不分支（分支讓頂層模型數加倍，寬題目的 schema 超過 ``SCHEMA_CHAR_LIMIT``），改在
``weapon_req`` 的說明寫清楚（:data:`WEAPON_REQ_DOC`），見 4-L10a 報告。"""


CATEGORIES: tuple[str, ...] = tuple(WEAPON_REQ_BY_CATEGORY)


WEAPON_REQ_DOC = (
    "必須與 category 配對：category: weapon（武器技）只能填 melee 或 ranged；"
    "category: spell（法術技）只能填 focus 或 any。"
)


ACTIVE_ONLY_FIELDS: tuple[str, ...] = (
    "cost_penalty",
    "cost_overdraft",
    "cost_on_miss",
    "variants",
    "trigger",
    "followup",
)
"""反應技分支不提供的欄位（驗證器：自身代價、透支、失手反噬、變奏、複合技能只有主動技能可以有；
trigger 只有被動技能可以有；Phase 4-L10a A2）。反應技分支的 ``reaction`` 必填。"""


LAYOUT_SPLITS: dict[str, tuple[str, dict[str, tuple[str, ...] | None]]] = {
    SHADOWSTEP: ("landing", {k: (v,) for k, v in SHADOWSTEP_SHAPES.items()}),
    ZONE: (
        "anchor",
        {"tile": None, "caster": ZONE_CASTER_SHAPES, "moving": ZONE_MOVING_SHAPES},
    ),
}
"""依特殊原語的參數決定形狀的版型（驗證器 ``_check_shadowstep``、``_check_zone_effect``）：版型依
參數值分支，各支只列該值可用的形狀（``None`` ＝ 不限；Phase 4-L10a A3）。"""


_MAIN, _REACTION = "main", "reaction"


@cache
def _weapon_req_type() -> Any:
    """``weapon_req``（不依類別分支時）：四種值，說明寫明與 category 的配對（具名型別，各分支以
    ``$ref`` 引用）。"""
    values = [v for pair in WEAPON_REQ_BY_CATEGORY.values() for v in pair]
    return _alias("WeaponReq", Annotated[_literal(values), Field(description=WEAPON_REQ_DOC)])


@dataclass(frozen=True, slots=True)
class _Branch:
    """頂層的一支：版型 × 種類組（一般／反應技）× 參數分支 × 技能類別。"""

    plan: LayoutPlan
    group: str
    kinds: tuple[str, ...]
    split: tuple[str, str, str] | None
    """（原語、參數、值）。"""
    shapes: tuple[str, ...]
    category: str | None
    """技能類別（``None`` ＝ 不依類別分支）。"""

    @property
    def tag(self) -> str:
        sub = "" if self.split is None else self.split[2]
        return "~".join((self.plan.id, self.group, sub, self.category or ""))

    @property
    def model_name(self) -> str:
        base = (
            "SkillProposal" if self.plan.id == STANDARD_LAYOUT else f"SkillProposal_{self.plan.id}"
        )
        parts = [base]
        if self.split is not None:
            parts.append(self.split[2])
        if self.group == _REACTION:
            parts.append(_REACTION)
        if self.category is not None:
            parts.append(self.category)
        return "_".join(parts)


def _kind_groups(plan: LayoutPlan) -> list[tuple[str, tuple[str, ...]]]:
    main = tuple(k for k in plan.kinds if k != "reaction")
    groups = [(_MAIN, main)] if main else []
    if "reaction" in plan.kinds:
        groups.append((_REACTION, ("reaction",)))
    return groups


def _splits(plan: LayoutPlan) -> list[tuple[tuple[str, str, str] | None, tuple[str, ...]]]:
    for lead in plan.leads:
        if lead not in LAYOUT_SPLITS:
            continue
        param, table = LAYOUT_SPLITS[lead]
        out: list[tuple[tuple[str, str, str] | None, tuple[str, ...]]] = []
        for value, allowed in table.items():
            shapes = (
                plan.shapes if allowed is None else tuple(s for s in plan.shapes if s in allowed)
            )
            if shapes:
                out.append(((lead, param, value), shapes))
        if out:
            return out
    return [(None, plan.shapes)]


def _branches(plan: LayoutPlan, *, split_category: bool = False) -> list[_Branch]:
    categories: tuple[str | None, ...] = CATEGORIES if split_category else (None,)
    return [
        _Branch(plan, group, kinds, split, shapes, category)
        for group, kinds in _kind_groups(plan)
        for split, shapes in _splits(plan)
        for category in categories
    ]


def _branch_picker(branches: Sequence[_Branch]) -> Callable[[Any], str | None]:
    """頂層的判別函式：版型 → 種類組（``kind: reaction`` 走反應技分支）→ 參數分支（版型的特殊
    原語的參數值）→ 技能類別。值不合法時退回第一支，讓錯誤落在該欄位上。"""
    by_layout: dict[str, list[_Branch]] = {}
    for branch in branches:
        by_layout.setdefault(branch.plan.id, []).append(branch)

    def pick(value: Any) -> str | None:
        layout = _get(value, "layout")
        options = by_layout.get(layout) if isinstance(layout, str) else None
        if options is None:
            return layout if isinstance(layout, str) else None
        groups = [b.group for b in options]
        group = (
            _REACTION if _get(value, "kind") == "reaction" and _REACTION in groups else groups[0]
        )
        split = options[0].split
        sub = ""
        if split is not None:
            values = [b.split[2] for b in options if b.split is not None]
            found = next(
                (
                    _get(e, split[1])
                    for e in _get(value, "effects") or ()
                    if _get(e, "type") == split[0]
                ),
                None,
            )
            sub = found if found in values else values[0]
        category = ""
        if options[0].category is not None:
            given = _get(value, "category")
            category = given if given in CATEGORIES else CATEGORIES[0]
        return "~".join((layout, group, sub, category))

    return pick


def _layout_model(
    builder: _Builder,
    branch: _Branch,
    common: Mapping[str, Any],
    shared: _Shared,
) -> Any:
    """頂層的一支（欄位順序：``layout``、``kind``、``category`` 最先，讓模型先決定分支）。"""
    plan = branch.plan
    if branch.split is None and plan.id == STANDARD_LAYOUT and shared.standard_shape is not None:
        shape = shared.standard_shape
    else:
        shape = builder.shape_union(branch.shapes)
    models: Mapping[str, Any] = builder.effects
    if branch.split is not None:
        lead, param, value = branch.split
        models = {**builder.effects, lead: builder.restricted(lead, param, value)}
    reaction = branch.group == _REACTION
    fields: dict[str, Any] = {
        "layout": (_literal((plan.id,)), ...),
        "kind": (_literal(branch.kinds), ...),
    }
    if branch.category is not None:
        fields["category"] = (_literal((branch.category,)), ...)
        fields["weapon_req"] = (_literal(WEAPON_REQ_BY_CATEGORY[branch.category]), ...)
    else:
        fields["category"] = (SkillDef.model_fields["category"].annotation, ...)
        fields["weapon_req"] = (_weapon_req_type(), ...)
    fields.update({k: v for k, v in common.items() if not (reaction and k in ACTIVE_ONLY_FIELDS)})
    if reaction:
        fields["reaction"] = (shared.reaction, ...)
    fields["shape"] = (shape, ...)
    fields["effects"] = (
        _list_of(_layout_effects(builder, plan, shared, models)),
        Field(min_length=1, max_length=plan.max_effects),
    )
    fields["tags"] = (
        list[Annotated[str, Field(pattern=ID_PATTERN)]],
        Field(default_factory=list, max_length=_MAX_TAGS),
    )
    if plan.variants and shared.variant is not None and not reaction:
        fields["variants"] = (
            _list_of(shared.variant),
            Field(default_factory=list, max_length=_MAX_VARIANTS),
        )
    if builder.condition is not None:
        fields["condition"] = (Union[builder.condition, None], None)  # noqa: UP007
    if builder.trigger is not None and not reaction:
        fields["trigger"] = (Union[builder.trigger, None], None)  # noqa: UP007
    if shared.followup is not None and "active" in branch.kinds:
        fields["followup"] = (shared.followup | None, Field(default=None))
    return create_model(
        branch.model_name,
        __base__=_Proposal,
        __doc__=_SKILL_DOC if plan.id == STANDARD_LAYOUT else None,
        **fields,
    )


def _optional_alias(name: str, annotation: Any, doc: str, **limits: Any) -> tuple[Any, Any]:
    """選填欄位的具名型別（說明寫在 ``$defs`` 一次，各分支以 ``$ref`` 引用；4-L10a 縮小
    schema）。"""
    inner: Any = Annotated[annotation, Field(**limits)] if limits else annotation
    optional = Annotated[Union[inner, None], Field(description=doc)]  # noqa: UP007
    return (_alias(name, optional), None)


def _common_fields(
    library: ContentLibrary, builder: _Builder, skeleton_type: Any, rarity: SkillRarity | None
) -> dict[str, Any]:
    """各分支共用的欄位（種類、類別、武器需求、反應另依分支）。"""
    sk = SkillDef.model_fields
    common: dict[str, Any] = {
        # 名稱不在提議裡（4-L8，PM 追加）：由命名步驟（4-L7）產生，沒有命名時用組合式名稱
        "description_zh": (str | None, None),
        "concept": (str, Field(default="", max_length=80)),
        "cast_flavor": (str, Field(default="", max_length=80)),
        "skeleton": (skeleton_type, ...),
        "scaling_attr": (sk["scaling_attr"].annotation, ...),
        # 技能元素（3-54d）：選填；隆起、下陷、石膚、震波只有 earth 的技能能用（同一條互斥規則）
        "element": (sk["element"].annotation, None),
        "cost_penalty": _optional_alias(
            "CostPenalty",
            _literal(penalty_choices(library, rarity)),
            COST_DOCS["cost_penalty"],
        ),
        "cost_overdraft": _optional_alias(
            "CostOverdraft", Literal[True], COST_DOCS["cost_overdraft"]
        ),
        "cost_once_per_battle": _optional_alias(
            "CostOncePerBattle", Literal[True], COST_DOCS["cost_once_per_battle"]
        ),
        "cost_hp": _optional_alias("CostHp", Literal[True], COST_DOCS["cost_hp"]),
    }
    if on_miss_allowed(rarity):
        common["cost_on_miss"] = _optional_alias(
            "CostOnMiss",
            _list_of(builder.backlash_union()),
            COST_DOCS["cost_on_miss"],
            min_length=1,
            max_length=_MAX_NESTED,
        )
    return common


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
    split_category: bool = False,
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
    代價類欄位（見 :mod:`trpg.skillgen.proposal_costs`）。

    Phase 4-L10a：每個版型再依「種類組（反應技另一支，``reaction`` 必填、沒有只限主動技能的
    欄位）× 參數分支（:data:`LAYOUT_SPLITS`）」分支，以判別函式選支（JSON Schema 是 ``oneOf``）；
    ``split_category=True`` 時再依技能類別分支（:data:`WEAPON_REQ_BY_CATEGORY`；預設關，
    見該常數）。"""
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
    if "reaction" in kind_choices(library, skeleton_ids):
        shared = replace(shared, reaction=_reaction_model(library))
    common = _common_fields(library, builder, skeleton_type, rarity)
    hints = {p.id: layout_hint(library, p) for p in plans}
    branches = [b for p in plans for b in _branches(p, split_category=split_category)]
    choices = [Annotated[_layout_model(builder, b, common, shared), Tag(b.tag)] for b in branches]
    skill: Any = Annotated[
        Union[tuple(choices)],  # noqa: UP007
        Discriminator(_branch_picker(branches)),
    ]
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
        kinds=tuple((p.id, p.kinds) for p in plans),
    )
