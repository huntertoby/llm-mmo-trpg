"""隨機技能組合器（``docs/phases/Phase2B計畫.md`` 5.1）。

``compose_random_skill(seed, ...)`` 依資料表（骨架、原語、形狀、狀態、表面、條件）隨機組出一個
通過 :func:`trpg.skillgen.validate.validate_skill` 的技能。流程：骨架 → 核心原語 → 形狀與參數 →
效果與參數 → 條件 → 代價 → 調整強度（比例 0.75–0.95）→ 驗證。失敗則用同一個亂數串流重抽，
每個種子最多 :data:`MAX_ATTEMPTS` 次。

確定性：只用 :class:`trpg.shared.rng.Rng`；相同的種子與參數必得相同的技能。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import SkillDef, SkillRarity, rarity_rank
from trpg.shared.errors import TrpgError
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_parts import (
    Ctx,
    Retry,
    build_condition,
    build_cost,
    build_effects,
    build_shape,
    choose_core,
)
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.mechanics import mechanic_tags
from trpg.skillgen.validate import validate_skill

__all__ = [
    "MAX_ATTEMPTS",
    "ComposeError",
    "ComposeResult",
    "compose_random_skill",
    "compose_with_stats",
    "default_library",
]

MAX_ATTEMPTS = 50

_RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic", "legendary")
_RARITY_WEIGHTS = (35, 35, 20, 10)
_AP_WEIGHTS = ((1, 35), (2, 50), (3, 15))
_SPELL_SHARE_PERMILLE = {"aura": 850}
_SPELL_SHARE_DEFAULT = 500
_SPELL_ELEMENTS: tuple[Element, ...] = tuple(
    e for e in sorted(Element, key=lambda e: e.value) if e is not Element.PHYSICAL
)
_INFUSE_PERMILLE = 350


class ComposeError(TrpgError):
    """參數無解，或 :data:`MAX_ATTEMPTS` 次重抽都做不出合格的技能。"""


@dataclass(frozen=True, slots=True)
class ComposeResult:
    """組合結果與重抽次數（``attempts`` 為 1 表示第一次就成功）。"""

    skill: SkillDef
    attempts: int


@cache
def default_library() -> ContentLibrary:
    """預設的內容庫（``content/``），行程內只載入一次。"""
    return load_library()


def _weighted[T](rng: Rng, items: tuple[T, ...], weights: tuple[int, ...]) -> T:
    roll = rng.randint(1, sum(weights))
    for item, weight in zip(items, weights, strict=True):
        roll -= weight
        if roll <= 0:
            return item
    return items[-1]  # pragma: no cover


def _skeleton_feasible(skeleton: SkeletonDef, rarity: SkillRarity, library: ContentLibrary) -> bool:
    """骨架在這個稀有度做得出技能：啟用、是主動技能、有可用的核心原語，要求條件時有可用條件。"""
    if not skeleton.enabled or "active" not in skeleton.kinds:
        return False
    rank = rarity_rank(rarity)
    primitives = library.ruleset.primitives.by_id()
    if not any(rarity_rank(primitives[p].min_rarity) <= rank for p in skeleton.core.primitives):
        return False
    if skeleton.requires_condition:
        conditions = library.ruleset.conditions.conditions
        return any(rarity_rank(c.min_rarity) <= rank for c in conditions)
    return True


def _feasible_skeletons(rarity: SkillRarity, library: ContentLibrary) -> list[SkeletonDef]:
    return [
        library.skeletons[name]
        for name in sorted(library.skeletons)
        if _skeleton_feasible(library.skeletons[name], rarity, library)
    ]


def _choose_rarity_and_skeleton(
    rng: Rng, rarity: SkillRarity | None, skeleton: str | None, library: ContentLibrary
) -> tuple[SkillRarity, SkeletonDef]:
    if rarity is None:
        rarities = tuple(
            r
            for r in _RARITIES
            if skeleton is None or _skeleton_feasible(_known(library, skeleton), r, library)
        )
        if not rarities:
            raise ComposeError(f"骨架 {skeleton} 在任何稀有度都做不出技能")
        weights = tuple(_RARITY_WEIGHTS[_RARITIES.index(r)] for r in rarities)
        picked = _weighted(rng, rarities, weights)
    else:
        picked = rarity
    if skeleton is not None:
        chosen = _known(library, skeleton)
        if not _skeleton_feasible(chosen, picked, library):
            raise ComposeError(f"骨架 {skeleton} 不能產生稀有度 {picked} 的主動技能")
        return picked, chosen
    feasible = _feasible_skeletons(picked, library)
    if not feasible:
        raise ComposeError(f"稀有度 {picked} 沒有可用的骨架")
    return picked, rng.choice(feasible)


def _known(library: ContentLibrary, skeleton: str) -> SkeletonDef:
    if skeleton not in library.skeletons:
        raise ComposeError(
            f"未知的骨架 {skeleton!r}（可用：{', '.join(sorted(library.skeletons))}）"
        )
    return library.skeletons[skeleton]


def _choose_category(rng: Rng, skeleton: SkeletonDef, category: str | None) -> str:
    if category is not None:
        return category
    share = _SPELL_SHARE_PERMILLE.get(skeleton.id, _SPELL_SHARE_DEFAULT)
    return "spell" if rng.chance_permille(share) else "weapon"


def _weapon_and_attr(rng: Rng, category: str) -> tuple[str, str]:
    if category == "spell":
        req = "any" if rng.chance_permille(250) else "focus"
        return req, _weighted(rng, ("int", "wis", "wil"), (60, 20, 20))
    if rng.chance_permille(500):
        return "melee", "dex" if rng.chance_permille(250) else "str"
    return "ranged", "dex"


def _ap_order(rng: Rng, ap_cost: int | None) -> list[int]:
    """AP 的嘗試順序：指定時只有它；否則依權重抽出（不重複）。"""
    if ap_cost is not None:
        return [ap_cost]
    remaining = [ap for ap, _ in _AP_WEIGHTS]
    weights = dict(_AP_WEIGHTS)
    order: list[int] = []
    while remaining:
        pick = _weighted(rng, tuple(remaining), tuple(weights[a] for a in remaining))
        order.append(pick)
        remaining.remove(pick)
    return order


def _attempt(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    fixed: tuple[int, SkillRarity, SkeletonDef, str],
    ap_cost: int | None,
) -> SkillDef:
    """一次嘗試；做不出合格技能時拋出 ``Retry``、``ValidationError`` 或 ``BudgetError``。

    結構（形狀、效果、條件）決定後，AP 依權重的順序逐一嘗試（AP 決定可用預算，結構太弱或太強
    的技能換個 AP 常常就合格）；每個 AP 各抽一次代價並調整強度，第一個成功的為準。
    """
    tier, rarity, skeleton, category = fixed
    order = _ap_order(rng, ap_cost)
    weapon_req, scaling = _weapon_and_attr(rng, category)
    if category == "spell":
        theme = rng.choice(_SPELL_ELEMENTS)
    else:
        theme = (
            rng.choice(_SPELL_ELEMENTS)
            if rng.chance_permille(_INFUSE_PERMILLE)
            else Element.PHYSICAL
        )
    ctx = Ctx(library, rng, skeleton, rarity, tier, category, order[0], theme)
    core = choose_core(ctx)
    build_shape(ctx, core)
    build_effects(ctx, core)
    condition = build_condition(ctx)
    base: dict[str, Any] = {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": rarity,
        "kind": "active",
        "skeleton": skeleton.id,
        "category": category,
        "weapon_req": weapon_req,
        "scaling_attr": scaling,
        "shape": {"type": ctx.shape, **ctx.shape_params},
        "condition": condition,
        "provenance": {"origin": "level_up"},
    }
    for ap in order:
        ctx.ap_cost = ap
        base = {**base, "ap_cost": ap, "cost": build_cost(ctx)}
        if tune(rng, library, base, ctx.effects, ctx.knobs):
            return _finish(library, seed, base, ctx)
    raise Retry


def _finish(library: ContentLibrary, seed: int, base: dict[str, Any], ctx: Ctx) -> SkillDef:
    """加上名稱、標籤與暫定的敘事文字。"""
    draft = SkillDef.model_validate({**base, "effects": ctx.effects})
    tags: list[str] = [ctx.theme.value, ctx.skeleton.id]
    tags += [t for t in mechanic_tags(draft, library.ruleset) if t not in tags]
    data = {
        **base,
        "effects": ctx.effects,
        "name_zh": f"{ctx.theme.display_name}・{ctx.skeleton.name_zh} #{seed}",
        "tags": tags,
        "narrative": {
            "concept": f"隨機組合器產生的{ctx.skeleton.name_zh}技能（種子 {seed}，暫定）",
            "cast_flavor": "（暫定）力量依你的意志成形。",
        },
    }
    return SkillDef.model_validate(data)


def compose_with_stats(
    seed: int,
    *,
    tier: int | None = None,
    rarity: SkillRarity | None = None,
    skeleton: str | None = None,
    category: str | None = None,
    ap_cost: int | None = None,
    library: ContentLibrary | None = None,
) -> ComposeResult:
    """:func:`compose_random_skill`，另外回傳重抽次數。"""
    lib = library if library is not None else default_library()
    rng = Rng(seed)
    tier_value = tier if tier is not None else rng.randint(1, 5)
    if tier_value not in lib.ruleset.core.tier_budget:
        raise ComposeError(f"沒有階級 {tier_value} 的預算")
    rarity_value, skeleton_def = _choose_rarity_and_skeleton(rng, rarity, skeleton, lib)
    category_value = _choose_category(rng, skeleton_def, category)
    fixed = (tier_value, rarity_value, skeleton_def, category_value)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            skill = _attempt(rng, lib, seed, fixed, ap_cost)
        except (Retry, ValidationError, BudgetError):
            continue
        if not validate_skill(skill, lib):
            return ComposeResult(skill, attempt)
    raise ComposeError(
        f"種子 {seed}：{MAX_ATTEMPTS} 次重抽都做不出合格的技能"
        f"（階級 {tier_value}、{rarity_value}、{skeleton_def.id}、{category_value}、AP {ap_cost}）"
    )


def compose_random_skill(
    seed: int,
    *,
    tier: int | None = None,
    rarity: SkillRarity | None = None,
    skeleton: str | None = None,
    category: str | None = None,
    ap_cost: int | None = None,
    library: ContentLibrary | None = None,
) -> SkillDef:
    """依種子組出一個合格的隨機技能（``id`` 為 ``skill_rand_<seed>``）。"""
    return compose_with_stats(
        seed,
        tier=tier,
        rarity=rarity,
        skeleton=skeleton,
        category=category,
        ap_cost=ap_cost,
        library=library,
    ).skill
