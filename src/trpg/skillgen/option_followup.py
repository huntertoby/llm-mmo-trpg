"""技能工坊的「動作段」步驟（Phase 3F-3b）：複合技能（位移 → 動作，``docs/design/06-技能.md``
6.23）的第二段的選項推導。

位移段就是技能本身（骨架 ``displace``、效果恰好一個施放者自身位移原語）；動作段（``followup``）
有自己的骨架、形狀與效果。這裡不寫規則：骨架、形狀、效果的候選都沿用一般技能的推導
（:func:`trpg.skillgen.options.draft_options` 的形狀與效果步驟，以動作段的骨架與形狀當作一個
獨立技能試組），再套上複合技能的限制（:data:`~trpg.content.skills.FOLLOWUP_SHAPES`、
:data:`~trpg.content.skills.FOLLOWUP_FORBIDDEN`、兩段合計的效果上限）。

欄位路徑都是 ``followup.*``（和 ``cost.mana`` 一樣的點號路徑），網頁照一般欄位處理；
``followup.skeleton`` 是「要不要接動作段」：不選＝普通的位移技能。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import (
    COMPOSITE_MOVES,
    FOLLOWUP_CENTERED,
    FOLLOWUP_FORBIDDEN,
    FOLLOWUP_SHAPES,
    SKELETON_IDS,
)
from trpg.skillgen.draft import Draft
from trpg.skillgen.option_models import Choice, FieldSpec
from trpg.skillgen.option_params import shape_param_fields

__all__ = [
    "FOLLOWUP_SKELETON",
    "followup_eligible",
    "followup_fields",
    "followup_notes",
    "followup_visible",
]

FOLLOWUP_SKELETON = "displace"
"""位移段（技能本身）的骨架。"""
_CARRIED = ("kind", "category", "weapon_req", "scaling_attr", "tier", "ap_cost")
"""動作段沿用位移段的欄位（:meth:`~trpg.content.skills.SkillDef.followup_skill`）。"""

type EffectChoices = Callable[[Draft, ContentLibrary, SkeletonDef], list[Choice]]


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def followup_eligible(draft: Draft) -> bool:
    """位移段已經是「複合技能的位移段」：主動技、骨架 ``displace``、恰好一個自身位移原語。"""
    effects: list[Any] = list(draft.get("effects") or ())
    return (
        draft.get("skeleton") == FOLLOWUP_SKELETON
        and draft.get("kind") == "active"
        and len(effects) == 1
        and _mapping(effects[0]).get("type") in COMPOSITE_MOVES
    )


def followup_visible(draft: Draft) -> bool:
    """要不要顯示「動作段」步驟：可以接動作段，或草稿已經有動作段（讓使用者能移除）。"""
    return draft.get("followup") is not None or followup_eligible(draft)


def _fits(library: ContentLibrary, skeleton: SkeletonDef, shape_id: str) -> bool:
    primitives = library.ruleset.primitives.by_id()
    cores = [primitives[p] for p in skeleton.core.primitives if p in primitives]
    return any(p.allowed_shapes is None or shape_id in p.allowed_shapes for p in cores)


def _shape_ids(library: ContentLibrary, skeleton: SkeletonDef) -> list[str]:
    known = library.ruleset.shapes.by_id()
    return [
        s
        for s in skeleton.shapes
        if s in FOLLOWUP_SHAPES and s in known and _fits(library, skeleton, s)
    ]


def _skeleton_choices(library: ContentLibrary) -> tuple[Choice, ...]:
    out: list[Choice] = []
    for skeleton_id in SKELETON_IDS:
        skeleton = library.skeletons.get(skeleton_id)
        if skeleton is None or not skeleton.enabled or "active" not in skeleton.kinds:
            continue
        if skeleton.requires_condition:
            continue  # 動作段的條件欄位工坊還不開放（保守做法）
        if skeleton.core.primitives and _shape_ids(library, skeleton):
            out.append(
                Choice(
                    value=skeleton.id,
                    name_zh=skeleton.name_zh,
                    description_zh=skeleton.description_zh,
                    info={
                        "min_rarity": skeleton.min_rarity,
                        "core_primitives": list(skeleton.core.primitives),
                        "secondary_max_count": skeleton.secondary.max_count,
                    },
                )
            )
    return tuple(out)


def _shape_params(library: ContentLibrary, shape_id: str) -> tuple[FieldSpec, ...]:
    """動作段形狀的參數；以落點為中心的形狀（十字、方陣）射程固定 0。"""
    params = shape_param_fields(library.ruleset.shapes.by_id()[shape_id])
    if shape_id not in FOLLOWUP_CENTERED:
        return params
    return tuple(
        FieldSpec(
            field=p.field,
            name_zh=p.name_zh,
            description_zh="以落點為中心，固定 0",
            type="int",
            required=True,
            min=0,
            max=0,
        )
        if p.field == "range"
        else p
        for p in params
    )


def _shape_field(library: ContentLibrary, skeleton: SkeletonDef) -> FieldSpec:
    shapes = library.ruleset.shapes.by_id()
    choices = tuple(
        Choice(
            value=s,
            name_zh=shapes[s].name_zh,
            description_zh=shapes[s].description_zh,
            params=_shape_params(library, s),
            info={"min_rarity": shapes[s].min_rarity, "targeting": shapes[s].targeting},
        )
        for s in _shape_ids(library, skeleton)
    )
    return FieldSpec(
        field="followup.shape",
        name_zh="動作段的形狀",
        description_zh="以位移後的落點為原點；十字、方陣以落點為中心，其他在落點選方向或目標",
        type="choice",
        required=True,
        choices=choices,
    )


def _pseudo_draft(draft: Draft, skeleton: SkeletonDef, follow: Mapping[str, Any]) -> dict[str, Any]:
    """把動作段當成一個獨立的技能草稿（沿用位移段的種類、類別、縮放屬性、階級與 AP）。"""
    out: dict[str, Any] = {k: draft[k] for k in _CARRIED if draft.get(k) is not None}
    out["skeleton"] = skeleton.id
    out["shape"] = follow["shape"]
    out["effects"] = list(follow.get("effects") or ())
    return out


def _effects_field(
    draft: Draft,
    library: ContentLibrary,
    skeleton: SkeletonDef,
    follow: Mapping[str, Any],
    effect_choices: EffectChoices,
) -> FieldSpec:
    choices = tuple(
        c
        for c in effect_choices(_pseudo_draft(draft, skeleton, follow), library, skeleton)
        if str(c.value) not in FOLLOWUP_FORBIDDEN
    )
    room = max(r.max_effects for r in library.budget.rarity.values()) - 1
    return FieldSpec(
        field="followup.effects",
        name_zh="動作段的效果",
        description_zh="位移到落點後依序結算；不能再放位移、召喚、區域、陷阱",
        type="effects",
        required=True,
        choices=choices,
        min_count=1,
        max_count=room,
    )


def followup_fields(
    draft: Draft, library: ContentLibrary, effect_choices: EffectChoices
) -> tuple[FieldSpec, ...]:
    """動作段步驟的欄位：骨架 →（選了骨架後）形狀 →（形狀填好後）效果。"""
    skeleton_field = FieldSpec(
        field="followup.skeleton",
        name_zh="接一個動作段",
        description_zh="選一個骨架就是複合技能：位移到落點後，以落點為原點再做一次動作；"
        "不選就是普通的位移技能",
        type="choice",
        choices=_skeleton_choices(library),
    )
    follow = _mapping(draft.get("followup"))
    skeleton = library.skeletons.get(str(follow.get("skeleton")))
    if skeleton is None or not skeleton.enabled:
        return (skeleton_field,)
    shape_field = _shape_field(library, skeleton)
    shape = _mapping(follow.get("shape"))
    if shape.get("type") is None or all(shape.get("type") != c.value for c in shape_field.choices):
        return (skeleton_field, shape_field)
    effects_field = _effects_field(draft, library, skeleton, follow, effect_choices)
    return (skeleton_field, shape_field, effects_field)


def followup_notes(library: ContentLibrary) -> tuple[str, ...]:
    tax = library.budget.composite_tax_permille
    return (
        "位移段（技能本身）只能有一個自身位移效果；動作段不能再放位移、召喚、區域、陷阱",
        f"兩段的點數各自依骨架與形狀計算，加總後再 +{tax / 10:g}%（省下一次行動的代價）",
        "兩段的效果合計最多 4 個；最低稀有度至少稀有",
    )
