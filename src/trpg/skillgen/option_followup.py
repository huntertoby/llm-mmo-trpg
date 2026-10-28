"""技能工坊的「第二段」步驟（Phase 3F-3b；3F-4b 擴充到六種）：複合技能（``docs/design/06-技能.md``
6.23）第二段的選項推導。

第一段就是技能本身；第二段（``followup``）有自己的種類（``when``）、骨架、形狀、效果與條件。這裡
不寫規則：骨架、形狀、效果、條件的候選都沿用一般技能的推導（:func:`trpg.skillgen.options.draft_options`
的效果步驟，以第二段的骨架與形狀當作一個獨立技能試組），再套上各種類的結構限制（與
:mod:`trpg.content.skills` 的 ``_FOLLOWUP_CHECKS`` 相同的常數：形狀、禁止的原語、兩段合計的效果
上限）。

欄位路徑都是 ``followup.*``（和 ``cost.mana`` 一樣的點號路徑），網頁照一般欄位處理：

1. ``followup.when``「接第二段」：只列第一段目前能接的種類；不選＝普通技能；
2. ``followup.release``（延遲段才有）：下回合開始時、或被攻擊時釋放；
3. ``followup.skeleton`` → ``followup.shape`` → ``followup.effects``、``followup.condition``。

舊草稿（3F-3b）沒有 ``when`` 但有 ``followup.skeleton`` 時視為「位移 → 動作」。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import (
    COMPOSITE_KIND_ZH,
    COMPOSITE_MOVES,
    DELAYED_SHAPES,
    FOLLOWUP_CENTERED,
    FOLLOWUP_FORBIDDEN,
    FOLLOWUP_SHAPES,
    FOLLOWUP_WHEN_VALUES,
    GATHER_SHAPES,
    ON_KILL_SECOND_SHAPES,
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
    "followup_when",
    "kind_eligible",
]

FOLLOWUP_SKELETON = "displace"
"""「位移 → 動作」的位移段（技能本身）與「動作 → 位移」的位移段的骨架。"""
_CARRIED = ("kind", "category", "weapon_req", "scaling_attr", "element", "tier", "ap_cost")
"""第二段沿用第一段的欄位（:meth:`~trpg.content.skills.SkillDef.followup_skill`）。"""

type EffectChoices = Callable[[Draft, ContentLibrary, SkeletonDef], list[Choice]]

_KIND_TEXT: dict[str, str] = {
    "after_move": "第一段是一個自身位移；到達落點後，以落點為原點再做一次動作",
    "after_action": "第一段結算後，施放者再做一個自身位移（打帶跑），落點自選",
    "after_gather": "第一段把敵人拉向一點（只有一個拉扯），第二段以該點為中心打擊",
    "on_kill": "第一段打倒敵人才結算；從自己的位置選下一個目標（可以先衝鋒再打）",
    "on_hit": "第一段命中才結算；自動對命中的同一個目標加碼",
    "delayed": "施放後開始蓄力：下回合開始時、或被攻擊時，以自己為中心釋放第二段",
}
_RELEASE_CHOICES = (
    Choice(value="next_turn", name_zh="下回合開始時", description_zh="施放者下回合開始時自動釋放"),
    Choice(
        value="attacked",
        name_zh="被攻擊時",
        description_zh="到施放者下回合開始之前被敵人攻擊就釋放；沒被攻擊就失效",
    ),
)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_types(draft: Draft) -> list[str]:
    return [str(_mapping(e).get("type")) for e in draft.get("effects") or ()]


def kind_eligible(when: str, draft: Draft) -> bool:
    """第一段（草稿本身）能不能接 ``when`` 種類的第二段（與 schema 的結構規則相同）。"""
    types = _first_types(draft)
    if draft.get("kind") != "active" or not types:
        return False
    bad = [t for t in types if t in FOLLOWUP_FORBIDDEN]
    shape = str(_mapping(draft.get("shape")).get("type"))
    checks: dict[str, Callable[[], bool]] = {
        "after_move": lambda: (
            draft.get("skeleton") == FOLLOWUP_SKELETON
            and len(types) == 1
            and types[0] in COMPOSITE_MOVES
        ),
        "after_action": lambda: not bad,
        "after_gather": lambda: types == ["pull"] and shape in GATHER_SHAPES,
        "on_kill": lambda: not bad and "damage" in types,
        "on_hit": lambda: not bad and "damage" in types,
        "delayed": lambda: all(t in COMPOSITE_MOVES for t in bad),
    }
    return checks[when]()


def followup_eligible(draft: Draft) -> bool:
    """第一段目前至少能接一種第二段。"""
    return any(kind_eligible(w, draft) for w in FOLLOWUP_WHEN_VALUES)


def followup_visible(draft: Draft) -> bool:
    """要不要顯示「第二段」步驟：可以接第二段，或草稿已經有第二段（讓使用者能移除）。"""
    return draft.get("followup") is not None or followup_eligible(draft)


_KNOWN_WHEN = ("after_move", "after_action", "after_gather", "on_kill", "on_hit", "delayed")


def followup_when(draft: Draft) -> str | None:
    """草稿第二段的種類；沒有 ``when`` 但已選骨架的舊草稿視為「位移 → 動作」。"""
    follow = _mapping(draft.get("followup"))
    when = follow.get("when")
    if when is None and follow.get("skeleton") is not None:
        return "after_move"
    return when if isinstance(when, str) and when in _KNOWN_WHEN else None  # 垃圾值視為還沒選


def _move_shapes(library: ContentLibrary) -> tuple[str, ...]:
    primitives = library.ruleset.primitives.by_id()
    found: set[str] = set()
    for move in COMPOSITE_MOVES:
        allowed = primitives[move].allowed_shapes if move in primitives else None
        found |= set(allowed or ())
    return tuple(sorted(found))


def _kind_shapes(when: str, library: ContentLibrary) -> tuple[str, ...]:
    """各種類第二段可用的形狀（與 schema 的 ``_FOLLOWUP_CHECKS`` 相同）。"""
    table: dict[str, tuple[str, ...]] = {
        "after_move": FOLLOWUP_SHAPES,
        "after_action": _move_shapes(library),
        "after_gather": FOLLOWUP_CENTERED,
        "on_kill": ON_KILL_SECOND_SHAPES,
        "on_hit": FOLLOWUP_SHAPES,
        "delayed": DELAYED_SHAPES,
    }
    return table.get(str(when), ())


def _fits(library: ContentLibrary, skeleton: SkeletonDef, shape_id: str) -> bool:
    primitives = library.ruleset.primitives.by_id()
    cores = [primitives[p] for p in skeleton.core.primitives if p in primitives]
    return any(p.allowed_shapes is None or shape_id in p.allowed_shapes for p in cores)


def _shape_ids(library: ContentLibrary, skeleton: SkeletonDef, when: str) -> list[str]:
    known = library.ruleset.shapes.by_id()
    allowed = _kind_shapes(when, library)
    return [
        s for s in skeleton.shapes if s in allowed and s in known and _fits(library, skeleton, s)
    ]


def _when_field(draft: Draft) -> FieldSpec:
    choices = tuple(
        Choice(value=w, name_zh=COMPOSITE_KIND_ZH[w], description_zh=_KIND_TEXT[w])
        for w in FOLLOWUP_WHEN_VALUES
        if kind_eligible(w, draft) or w == followup_when(draft)
    )
    return FieldSpec(
        field="followup.when",
        name_zh="接第二段",
        description_zh="選一種就是複合技能（兩段各有骨架、形狀與效果）；不選就是普通技能",
        type="choice",
        choices=choices,
    )


def _release_field() -> FieldSpec:
    return FieldSpec(
        field="followup.release",
        name_zh="何時釋放",
        description_zh="延遲段等待期間，施放者倒下、暈眩或冰凍時取消",
        type="choice",
        required=True,
        choices=_RELEASE_CHOICES,
    )


def _skeleton_choices(library: ContentLibrary, when: str) -> tuple[Choice, ...]:
    out: list[Choice] = []
    for skeleton_id in SKELETON_IDS:
        skeleton = library.skeletons.get(skeleton_id)
        if skeleton is None or not skeleton.enabled or "active" not in skeleton.kinds:
            continue
        if when == "after_action" and skeleton.id != FOLLOWUP_SKELETON:
            continue  # 打帶跑的第二段只是一個自身位移：骨架只能是位移
        if skeleton.core.primitives and _shape_ids(library, skeleton, when):
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


def _gather_reach(draft: Draft) -> int:
    shape = _mapping(draft.get("shape"))
    if shape.get("type") in FOLLOWUP_CENTERED and isinstance(shape.get("range"), int):
        return int(shape["range"])
    return 0


def _shape_params(
    library: ContentLibrary, shape_id: str, reach: int, center: str
) -> tuple[FieldSpec, ...]:
    """第二段形狀的參數；以原點為中心的形狀（十字、方陣）射程固定（聚集段的射程，其他為 0）。"""
    params = shape_param_fields(library.ruleset.shapes.by_id()[shape_id])
    if shape_id not in FOLLOWUP_CENTERED:
        return params
    return tuple(
        FieldSpec(
            field=p.field,
            name_zh=p.name_zh,
            description_zh=f"以{center}為中心，固定 {reach}",
            type="int",
            required=True,
            min=reach,
            max=reach,
        )
        if p.field == "range"
        else p
        for p in params
    )


_ORIGIN_TEXT: dict[str, tuple[str, str]] = {
    "after_move": ("落點", "以位移後的落點為原點；十字、方陣以落點為中心，其他在落點選方向或目標"),
    "after_action": ("自己", "從施放者的位置選落點"),
    "after_gather": ("聚集點", "以聚集點為中心（射程與聚集段相同）"),
    "on_kill": ("自己", "從施放者的位置選下一個目標或格子"),
    "on_hit": ("自己", "自動朝命中的同一個目標；十字、方陣以自己為中心"),
    "delayed": ("自己", "釋放時以施放者當下的位置為中心"),
}


def _shape_field(
    draft: Draft, library: ContentLibrary, skeleton: SkeletonDef, when: str
) -> FieldSpec:
    shapes = library.ruleset.shapes.by_id()
    center, text = _ORIGIN_TEXT[when]
    reach = _gather_reach(draft) if when == "after_gather" else 0
    choices = tuple(
        Choice(
            value=s,
            name_zh=shapes[s].name_zh,
            description_zh=shapes[s].description_zh,
            params=_shape_params(library, s, reach, center),
            info={"min_rarity": shapes[s].min_rarity, "targeting": shapes[s].targeting},
        )
        for s in _shape_ids(library, skeleton, when)
    )
    return FieldSpec(
        field="followup.shape",
        name_zh="第二段的形狀",
        description_zh=text,
        type="choice",
        required=True,
        choices=choices,
    )


def _pseudo_draft(draft: Draft, skeleton: SkeletonDef, follow: Mapping[str, Any]) -> dict[str, Any]:
    """把第二段當成一個獨立的技能草稿（沿用第一段的種類、類別、縮放屬性、階級與 AP）。"""
    out: dict[str, Any] = {k: draft[k] for k in _CARRIED if draft.get(k) is not None}
    out["skeleton"] = skeleton.id
    out["shape"] = follow["shape"]
    out["effects"] = list(follow.get("effects") or ())
    return out


def _allowed_effect(when: str, primitive: str) -> bool:
    if when == "after_action":
        return primitive in COMPOSITE_MOVES
    if when == "on_kill":
        return primitive not in FOLLOWUP_FORBIDDEN or primitive in COMPOSITE_MOVES
    return primitive not in FOLLOWUP_FORBIDDEN


def _effects_field(  # noqa: PLR0917
    draft: Draft,
    library: ContentLibrary,
    skeleton: SkeletonDef,
    follow: Mapping[str, Any],
    effect_choices: EffectChoices,
    when: str,
) -> FieldSpec:
    choices = tuple(
        c
        for c in effect_choices(_pseudo_draft(draft, skeleton, follow), library, skeleton)
        if _allowed_effect(when, str(c.value))
    )
    total = max(r.max_effects for r in library.budget.rarity.values())
    room = max(1, total - len(_first_types(draft)))
    if when == "after_action":
        room = 1
    return FieldSpec(
        field="followup.effects",
        name_zh="第二段的效果",
        description_zh="依序結算；兩段合計最多 4 個效果"
        + ("；只能是一個自身位移" if when == "after_action" else "；不能放召喚、區域、陷阱"),
        type="effects",
        required=True,
        choices=choices,
        min_count=1,
        max_count=room,
    )


def _condition_field(
    library: ContentLibrary, skeleton: SkeletonDef, condition_choice: Callable[..., Choice]
) -> FieldSpec:
    return FieldSpec(
        field="followup.condition",
        name_zh="第二段的條件",
        description_zh="不成立時第二段不生效（條件會讓第二段的點數打折）",
        type="choice",
        required=skeleton.requires_condition,
        choices=tuple(condition_choice(c, library) for c in library.ruleset.conditions.conditions),
    )


def followup_fields(
    draft: Draft,
    library: ContentLibrary,
    effect_choices: EffectChoices,
    condition_choice: Callable[..., Choice],
) -> tuple[FieldSpec, ...]:
    """第二段步驟的欄位：種類 →（延遲段的釋放時機）→ 骨架 → 形狀 → 效果與條件。"""
    fields: list[FieldSpec] = [_when_field(draft)]
    when = followup_when(draft)
    if when is None:
        return tuple(fields)
    if when == "delayed":
        fields.append(_release_field())
    skeleton_field = FieldSpec(
        field="followup.skeleton",
        name_zh="第二段的骨架",
        description_zh="第二段照這個骨架的規則檢查（核心效果、附帶效果、占比）",
        type="choice",
        required=True,
        choices=_skeleton_choices(library, when),
    )
    fields.append(skeleton_field)
    follow = _mapping(draft.get("followup"))
    skeleton = library.skeletons.get(str(follow.get("skeleton")))
    if skeleton is None or not skeleton.enabled:
        return tuple(fields)
    shape_field = _shape_field(draft, library, skeleton, when)
    fields.append(shape_field)
    shape = _mapping(follow.get("shape"))
    if shape.get("type") is None or all(shape.get("type") != c.value for c in shape_field.choices):
        return tuple(fields)
    fields.append(_effects_field(draft, library, skeleton, follow, effect_choices, when))
    fields.append(_condition_field(library, skeleton, condition_choice))
    return tuple(fields)


def followup_notes(library: ContentLibrary) -> tuple[str, ...]:
    budget = library.budget
    tax = budget.composite_tax_permille
    delayed = budget.composite_delayed_discount_permille
    return (
        "第二段不能再接第二段（不套娃），也不能放召喚、持續區域、陷阱",
        f"兩段的點數各自依骨架與形狀計算，加總後再 +{tax / 10:g}%（省下一次行動的代價）",
        f"擊殺後、命中後的第二段點數 × 觸發機率（{budget.on_kill_expected_permille}‰、"
        f"{budget.modifier.hit_rate_permille}‰）；延遲段 × {delayed}‰"
        "（敵人看得到、能反應）",
        "兩段之間自己造環境又引爆它（例如先造油再點火）時點數大幅加價",
        "兩段的效果合計最多 4 個；最低稀有度至少稀有",
    )
