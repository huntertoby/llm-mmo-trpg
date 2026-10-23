"""LLM 提議用盡重試後的退回（Phase 4-L5；使用者決定 #5）。

依序：① 隨機組合器帶題目關鍵字（與候選產生器的 ``from_composer`` 相同做法）② 技能池（內容庫的
手寫技能）③ 工坊選項推導（:func:`~trpg.skillgen.options.draft_options` 依骨架列出合法選項，取
第一組可行值，數值由 :func:`~trpg.skillgen.proposal_budget.budget_filler` 補）。三者都失敗才丟
:class:`FallbackError`。組合器與技能池必須帶題目的全部關鍵字（只看專屬規則，與候選產生器相同）；
工坊推導是最後保底，只守骨架與種類、不保證帶題目的關鍵字（仍要通過驗證器的「至少一個關鍵字」）。

確定性：亂數只來自 ``Rng(seed).fork(<來源>)``；同樣的題目與種子必得同樣的技能。
階級與稀有度取自 ``ctx``（呼叫端決定，與 LLM 提議相同），骨架、種類、關鍵字取自題目。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Literal

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import SkillDef, rarity_rank
from trpg.shared.rng import Rng
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.draft import DraftError, build_skill, draft_id
from trpg.skillgen.option_fill import fill_choice, fill_fields, variants
from trpg.skillgen.option_models import Choice, FieldSpec, StepOptions
from trpg.skillgen.options import draft_options
from trpg.skillgen.proposal import CLOSED_SKELETONS, ProposalContext
from trpg.skillgen.proposal_budget import budget_filler, is_repairable
from trpg.skillgen.proposal_numbers import DEFAULT_ACTIVE_AP
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill

__all__ = [
    "COMPOSER_TRIES",
    "FallbackError",
    "FallbackSource",
    "fallback_skill",
    "wanted_kind",
]

type FallbackSource = Literal["composer", "pool", "workshop"]
type _Source = Callable[[ContentLibrary, ProposalRequest, ProposalContext, int], SkillDef | None]

COMPOSER_TRIES = 8
"""組合器換種子重試的次數（與候選產生器的 ``composer_tries`` 預設相同）。"""
WORKSHOP_MAX_SHAPES = 4
WORKSHOP_MAX_EFFECTS = 6
"""工坊推導每個骨架最多試幾個形狀 × 幾個核心效果（保底用，避免組合爆炸）。"""


class FallbackError(Exception):
    """三種退回來源都做不出符合題目的技能。"""


def wanted_kind(library: ContentLibrary, request: ProposalRequest) -> str:
    """題目的技能種類：有指定就用；否則依骨架；都沒有時為 ``active``。"""
    if request.kind is not None:
        return request.kind
    skeleton = library.skeletons.get(str(request.skeleton))
    return skeleton.kinds[0] if skeleton is not None else "active"


def _fits(skill: SkillDef, request: ProposalRequest, kind: str, library: ContentLibrary) -> bool:
    return (
        skill.kind == kind
        and (request.skeleton is None or skill.skeleton == request.skeleton)
        and skill_has_keywords(skill, request.keywords, library)
    )


# ---------------------------------------------------------------------------
# ① 組合器 ② 技能池
# ---------------------------------------------------------------------------


def _from_composer(
    library: ContentLibrary, request: ProposalRequest, ctx: ProposalContext, seed: int
) -> SkillDef | None:
    kind = wanted_kind(library, request)
    skeleton = request.skeleton
    if skeleton is None and kind != "active" and kind in library.skeletons:
        skeleton = kind  # 被動、姿態各有同名骨架
    rng = Rng(seed).fork("fallback.composer")
    keyword = request.keywords[0] if request.keywords else None
    for _ in range(COMPOSER_TRIES):
        try:
            skill = compose_random_skill(
                rng.next_u32(),
                tier=ctx.tier,
                rarity=ctx.rarity,
                skeleton=skeleton,
                library=library,
                keyword=keyword,
                hero_attributes=ctx.hero_attributes,
            )
        except ComposeError:
            continue
        if _fits(skill, request, kind, library):
            return skill
    return None


def _from_pool(
    library: ContentLibrary, request: ProposalRequest, ctx: ProposalContext, seed: int
) -> SkillDef | None:
    kind = wanted_kind(library, request)
    options = [
        library.skills[skill_id]
        for skill_id in sorted(library.skills)
        if library.skills[skill_id].tier == ctx.tier
        and library.skills[skill_id].rarity == ctx.rarity
        and _fits(library.skills[skill_id], request, kind, library)
    ]
    return Rng(seed).fork("fallback.pool").choice(options) if options else None


# ---------------------------------------------------------------------------
# ③ 工坊選項推導
# ---------------------------------------------------------------------------


def _usable(choice: Choice, rank: int) -> bool:
    return rarity_rank(str(choice.info.get("min_rarity", "common"))) <= rank


def _field(step: StepOptions, name: str) -> FieldSpec | None:
    return next((f for f in step.fields if f.field == name), None)


def _step(draft: dict[str, Any], library: ContentLibrary) -> StepOptions | None:
    """草稿的下一個未完成步驟（全部完成時為 ``None``）。"""
    options = draft_options(draft, library)
    if options.next_step is None:
        return None
    return next(s for s in options.steps if s.id == options.next_step)


def _trigger(kind_choice: Choice, rank: int) -> dict[str, Any] | None:
    trigger = next((p for p in kind_choice.params if p.field == "trigger"), None)
    event = None if trigger is None else _field_of(trigger.fields, "event")
    if event is None:
        return None
    for choice in event.choices:
        if _usable(choice, rank):
            picked = fill_fields([event], {"event": choice})
            if picked is not None:
                return picked
    return None


def _field_of(fields: tuple[FieldSpec, ...], name: str) -> FieldSpec | None:
    return next((f for f in fields if f.field == name), None)


def _basics(
    library: ContentLibrary, skeleton: SkeletonDef, kind: str, ctx: ProposalContext
) -> dict[str, Any] | None:
    draft: dict[str, Any] = {"skeleton": skeleton.id}
    step = _step(draft, library)
    kinds = None if step is None else _field(step, "kind")
    kind_choice = (
        None if kinds is None else next((c for c in kinds.choices if c.value == kind), None)
    )
    if step is None or kind_choice is None:
        return None
    filled = fill_fields(
        [f for f in step.fields if f.field not in ("kind", "tier")], {}
    )  # 類別（含武器需求）、縮放屬性取第一個
    if filled is None:
        return None
    draft.update(filled, kind=kind, tier=ctx.tier, rarity=ctx.rarity)
    if kind == "active":
        draft["ap_cost"] = DEFAULT_ACTIVE_AP
    elif kind == "passive":
        trigger = _trigger(kind_choice, rarity_rank(ctx.rarity))
        if trigger is None:
            return None
        draft["trigger"] = trigger
    return draft


def _choices(step: StepOptions | None, name: str, rank: int, limit: int) -> list[Choice]:
    field = None if step is None else _field(step, name)
    if field is None:
        return []
    return [c for c in field.choices if _usable(c, rank)][:limit]


def _structures(
    library: ContentLibrary, base: dict[str, Any], rank: int
) -> Iterator[dict[str, Any]]:
    """依序產生「形狀 × 核心效果（× 第一個條件）」的草稿。"""
    for shape_choice in _choices(_step(base, library), "shape", rank, WORKSHOP_MAX_SHAPES):
        shape = fill_choice(shape_choice)
        if shape is None:
            continue
        with_shape = {**base, "shape": shape}
        effect_step = _step(with_shape, library)
        effects = _field(effect_step, "effects") if effect_step is not None else None
        if effects is None:
            continue
        cores = [c for c in effects.choices if c.info.get("core") and _usable(c, rank)]
        for core in cores[:WORKSHOP_MAX_EFFECTS]:
            fills = variants(core)
            if not fills:
                continue
            draft = {**with_shape, "effects": [fills[0]]}
            condition = _condition(library, draft, rank)
            if condition is not None:
                draft["condition"] = condition
            yield draft


def _condition(library: ContentLibrary, draft: dict[str, Any], rank: int) -> dict[str, Any] | None:
    step = _step(draft, library)
    if step is None or step.id != "condition":
        return None
    field = _field(step, "condition")
    if field is None or not field.required:
        return None
    for choice in field.choices:
        if _usable(choice, rank):
            filled = fill_choice(choice)
            if filled is not None:
                return filled
    return None


def _finish(library: ContentLibrary, draft: dict[str, Any], seed: int) -> SkillDef | None:
    """補數值（預算器；可修的錯誤修一次）並驗證；不合格時為 ``None``。"""
    repairs: tuple[str, ...] = ()
    for _ in range(2):
        data = budget_filler(library, seed=seed, repairs=repairs)(dict(draft))
        data.setdefault("name_zh", f"{library.skeletons[draft['skeleton']].name_zh}（保底）")
        data["provenance"] = {"origin": "level_up", "created_by": "workshop"}
        try:
            skill = build_skill(data, {"id": draft_id(data)})
        except DraftError:
            return None
        violations = validate_skill(skill, library)
        if not violations:
            return skill
        codes = tuple(sorted({v.rule for v in violations}))
        if repairs or not all(is_repairable(c, library) for c in codes):
            return None
        repairs = codes
    return None  # pragma: no cover - 迴圈最多兩次，第二次一定 return


def _workshop_skeletons(
    library: ContentLibrary, request: ProposalRequest, kind: str, rank: int
) -> list[SkeletonDef]:
    if request.skeleton is not None:
        skeleton = library.skeletons.get(request.skeleton)
        return [] if skeleton is None else [skeleton]
    return [
        s
        for s in library.skeletons.values()
        if s.enabled
        and s.id not in CLOSED_SKELETONS
        and kind in s.kinds
        and rarity_rank(s.min_rarity) <= rank
    ]


def _from_workshop(
    library: ContentLibrary, request: ProposalRequest, ctx: ProposalContext, seed: int
) -> SkillDef | None:
    kind = wanted_kind(library, request)
    rank = rarity_rank(ctx.rarity)
    for skeleton in _workshop_skeletons(library, request, kind, rank):
        base = _basics(library, skeleton, kind, ctx)
        if base is None:
            continue
        for draft in _structures(library, base, rank):
            skill = _finish(library, draft, seed)
            if skill is not None:
                return skill
    return None


def fallback_skill(
    library: ContentLibrary, request: ProposalRequest, ctx: ProposalContext, *, seed: int
) -> tuple[SkillDef, FallbackSource]:
    """依序試組合器、技能池、工坊推導；回傳（技能, 來源）。都失敗時丟 :class:`FallbackError`。"""
    sources: tuple[tuple[FallbackSource, _Source], ...] = (
        ("composer", _from_composer),
        ("pool", _from_pool),
        ("workshop", _from_workshop),
    )
    for name, source in sources:
        skill = source(library, request, ctx, seed)
        if skill is not None:
            return skill, name
    raise FallbackError(
        f"退回失敗：組合器、技能池、工坊推導都做不出符合題目的技能"
        f"（階級 {ctx.tier}、{ctx.rarity}、骨架 {request.skeleton or '不限'}、"
        f"關鍵字 {'、'.join(request.keywords) or '無'}）"
    )
