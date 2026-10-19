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

from trpg.content.composer_rules import ComposerRules
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skill_triggers import EVERY_N_HITS
from trpg.content.skills import SkillDef, SkillRarity, rarity_rank
from trpg.shared.errors import TrpgError
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_parts import (
    NON_INTERCEPT_EVENTS,
    Ctx,
    Retry,
    build_condition,
    build_cost,
    build_effects,
    build_passive_cost,
    build_passive_effects,
    build_reaction_cost,
    build_reaction_effects,
    build_shape,
    build_stance_effects,
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
_SPELL_ELEMENTS: tuple[Element, ...] = tuple(
    e for e in sorted(Element, key=lambda e: e.value) if e is not Element.PHYSICAL
)


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


def _skeleton_feasible(
    skeleton: SkeletonDef, rarity: SkillRarity, library: ContentLibrary, *, explicit: bool = False
) -> bool:
    """骨架在這個稀有度做得出技能：啟用、稀有度夠、有可用的核心原語，要求條件時有可用條件。

    預設只考慮主動技能；被動骨架（2E-1）、反應與姿態骨架（2E-2）只在明確指定（``explicit``）或由
    :func:`_wants_passive`、:func:`_wants_special` 決定時使用，所以不影響其他種子的抽選。
    """
    rank = rarity_rank(rarity)
    if not skeleton.enabled or rank < rarity_rank(skeleton.min_rarity):
        return False
    if skeleton.id in _HAND_WRITTEN_ONLY:
        return False
    if skeleton.id in _EXPLICIT_ONLY_ACTIVE:
        return explicit and _active_feasible(skeleton, rank, library)
    if "active" not in skeleton.kinds:
        return explicit and skeleton.kinds in (("passive",), ("reaction",), ("stance",))
    return _active_feasible(skeleton, rank, library)


def _active_feasible(skeleton: SkeletonDef, rank: int, library: ContentLibrary) -> bool:
    """主動骨架：有可用的核心原語，要求條件時有可用條件。"""
    primitives = library.ruleset.primitives.by_id()
    if not any(rarity_rank(primitives[p].min_rarity) <= rank for p in skeleton.core.primitives):
        return False
    if skeleton.requires_condition:
        conditions = library.ruleset.conditions.conditions
        return any(rarity_rank(c.min_rarity) <= rank for c in conditions)
    return True


_HAND_WRITTEN_ONLY = frozenset({"consume_status", "summon"})
"""隨機組合器不產生的骨架（3C-3b：``consume_status`` 的 ``then`` 要手寫，組合器不支援巢狀效果；
3D-4a：``summon`` 只給手寫技能，召喚物範本與持續輪數另外設計）。"""

_EXPLICIT_ONLY_ACTIVE = frozenset({"builder_finisher", "trap"})
"""主動骨架中，只在明確指定或由 :func:`_wants_special` 決定時使用的（2E-3；不影響其他種子）。"""


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
            if skeleton is None
            or _skeleton_feasible(_known(library, skeleton), r, library, explicit=True)
        )
        if not rarities:
            raise ComposeError(f"骨架 {skeleton} 在任何稀有度都做不出技能")
        weights = tuple(library.composer.rarity_weights[r] for r in rarities)
        picked = _weighted(rng, rarities, weights)
        if picked == "legendary":
            # 傳說技能必須手寫（Phase 3C-4a：需要源力代價與改寫規則型原語，組合器不產生）；
            # 抽到傳說時降為史詩，其他種子抽到的結果不變
            picked = "epic"
    elif rarity == "legendary":
        raise ComposeError("傳說技能只能手寫（需要源力代價與改寫規則型原語），組合器不產生")
    else:
        picked = rarity
    if skeleton is not None:
        chosen = _known(library, skeleton)
        if not _skeleton_feasible(chosen, picked, library, explicit=True):
            raise ComposeError(f"骨架 {skeleton} 不能產生稀有度 {picked} 的技能")
        return picked, chosen
    feasible = _feasible_skeletons(picked, library)
    if not feasible:
        raise ComposeError(f"稀有度 {picked} 沒有可用的骨架")
    return picked, rng.choice(feasible)


def _wants_passive(seed: int, rarity: SkillRarity, library: ContentLibrary) -> bool:
    """未指定骨架時，這個種子是否改組被動：稀有度夠、骨架啟用，且（獨立亂數串流）抽中機率。

    用 ``Rng(seed).fork`` 的獨立串流抽，所以沒有抽到被動的種子，得到與加入被動之前完全相同的技能。
    """
    skeleton = library.skeletons.get("passive")
    if skeleton is None or not _skeleton_feasible(skeleton, rarity, library, explicit=True):
        return False
    return (
        Rng(seed)
        .fork("composer.passive")
        .chance_permille(library.composer.passive.skeleton_permille)
    )


def _wants_special(seed: int, rarity: SkillRarity, library: ContentLibrary) -> str | None:
    """未指定骨架時，這個種子是否改組反應技、姿態、蓄力與終結（``builder_finisher``）或陷阱（``trap``）。

    與 :func:`_wants_passive` 一樣用獨立的亂數串流；抽中但組不出合格技能時由呼叫端退回一般主動技能。
    """
    for name, permille in (
        ("reaction", library.composer.reaction.skeleton_permille),
        ("stance", library.composer.stance.skeleton_permille),
        ("builder_finisher", library.composer.builder.skeleton_permille),
        ("trap", library.composer.trap.skeleton_permille),
    ):
        skeleton = library.skeletons.get(name)
        if (
            skeleton is not None
            and _skeleton_feasible(skeleton, rarity, library, explicit=True)
            and Rng(seed).fork(f"composer.{name}").chance_permille(permille)
        ):
            return name
    return None


def _known(library: ContentLibrary, skeleton: str) -> SkeletonDef:
    if skeleton not in library.skeletons:
        raise ComposeError(
            f"未知的骨架 {skeleton!r}（可用：{', '.join(sorted(library.skeletons))}）"
        )
    return library.skeletons[skeleton]


def _choose_category(
    rng: Rng, skeleton: SkeletonDef, category: str | None, rules: ComposerRules
) -> str:
    if category is not None:
        return category
    shares = rules.spell_share_permille
    share = shares.get(skeleton.id, shares["default"])
    return "spell" if rng.chance_permille(share) else "weapon"


def _weapon_and_attr(rng: Rng, category: str, rules: ComposerRules) -> tuple[str, str]:
    if category == "spell":
        req = "any" if rng.chance_permille(rules.spell_any_weapon_permille) else "focus"
        w = rules.spell_attr_weights
        return req, _weighted(rng, ("int", "wis", "wil"), (w.int_, w.wis, w.wil))
    if rng.chance_permille(rules.melee_permille):
        return "melee", "dex" if rng.chance_permille(rules.melee_dex_permille) else "str"
    return "ranged", "dex"


def _ap_order(rng: Rng, ap_cost: int | None, rules: ComposerRules) -> list[int]:
    """AP 的嘗試順序：指定時只有它；否則依權重抽出（不重複）。"""
    if ap_cost is not None:
        return [ap_cost]
    weights = rules.ap_weights
    remaining = sorted(weights)
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
    rules = library.composer
    order = _ap_order(rng, ap_cost, rules)
    weapon_req, scaling = _weapon_and_attr(rng, category, rules)
    if category == "spell":
        theme = rng.choice(_SPELL_ELEMENTS)
    else:
        theme = (
            rng.choice(_SPELL_ELEMENTS)
            if rng.chance_permille(rules.infuse_permille)
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
    if ctx.trap is not None:
        base["trap"] = ctx.trap
    for ap in order:
        ctx.ap_cost = ap
        base = {**base, "ap_cost": ap, "cost": build_cost(ctx)}
        if tune(rng, library, base, ctx.effects, ctx.knobs):
            return _finish(library, seed, _with_scaling_extras(rng, library, base, ctx), ctx)
    raise Retry


def _with_scaling_extras(
    rng: Rng, library: ContentLibrary, base: dict[str, Any], ctx: Ctx
) -> dict[str, Any]:
    """雙屬性縮放與專精加成（Phase 2H-2）：兩者預算都不計，所以強度調整之後才抽，只在合法時給。"""
    rules = library.composer.scaling
    primary = base["scaling_attr"]
    if rarity_rank(base["rarity"]) >= rarity_rank(
        library.ruleset.core.dual_scaling_min_rarity
    ) and rng.chance_permille(rules.dual_permille):
        others = sorted(a for a in rules.dual_attrs if a != primary)
        return {**base, "secondary_scaling_attr": rng.choice(others)}
    options = []
    if ctx.shape_params.get("range") is not None:
        options.append("range")
    if any(effect["type"] == "apply_status" for effect in ctx.effects):
        options.append("duration")
    if options and rng.chance_permille(rules.mastery_permille):
        return {**base, "mastery": rng.choice(options)}
    return base


def _attempt_passive(
    rng: Rng, library: ContentLibrary, seed: int, tier: int, rarity: SkillRarity
) -> SkillDef:
    """被動技能的一次嘗試：觸發時機 → 作用對象 → 效果 → 代價 → 調整強度。"""
    rules = library.composer
    skeleton = library.skeletons["passive"]
    timings = [
        t
        for t in sorted(library.ruleset.skill_triggers.triggers, key=lambda t: t.id)
        if rarity_rank(t.min_rarity) <= rarity_rank(rarity) and t.random_composer
    ]
    timing = rng.choice(timings)
    n = rng.choice((2, 3)) if timing.id == EVERY_N_HITS else None
    target = (
        "other"
        if timing.has_other and rng.chance_permille(rules.passive.other_permille)
        else "self"
    )
    w = rules.spell_attr_weights
    scaling = _weighted(rng, ("int", "wis", "wil"), (w.int_, w.wis, w.wil))
    theme = rng.choice(_SPELL_ELEMENTS)
    ctx = Ctx(library, rng, skeleton, rarity, tier, "spell", 1, theme)
    ctx.shape = "self"
    build_passive_effects(ctx, target)
    trigger: dict[str, Any] = {"event": timing.id, "target": target, "max_per_round": 1}
    if n is not None:
        trigger["n"] = n
    base: dict[str, Any] = {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": rarity,
        "kind": "passive",
        "skeleton": skeleton.id,
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": scaling,
        "shape": {"type": "self"},
        "condition": None,
        "trigger": trigger,
        "cost": build_passive_cost(ctx),
        "provenance": {"origin": "level_up"},
    }
    if tune(rng, library, base, ctx.effects, ctx.knobs):
        return _finish(library, seed, base, ctx)
    raise Retry


def _attempt_reaction(
    rng: Rng, library: ContentLibrary, seed: int, *, tier: int, rarity: SkillRarity, category: str
) -> SkillDef:
    """反應技的一次嘗試：事件 → 形狀與效果 → 代價 → 調整強度。"""
    rules = library.composer
    skeleton = library.skeletons["reaction"]
    if rng.chance_permille(rules.reaction.intercept_permille):
        event = "ally_hit_adjacent"
    else:
        event = rng.choice(NON_INTERCEPT_EVENTS)
    weapon_req, scaling = _weapon_and_attr(rng, category, rules)
    if category == "spell" or event == "ally_hit_adjacent":
        theme = rng.choice(_SPELL_ELEMENTS)
    else:
        infuse = rng.chance_permille(rules.infuse_permille)
        theme = rng.choice(_SPELL_ELEMENTS) if infuse else Element.PHYSICAL
    ctx = Ctx(library, rng, skeleton, rarity, tier, category, 1, theme)
    build_reaction_effects(ctx, event)
    base: dict[str, Any] = {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": rarity,
        "kind": "reaction",
        "skeleton": skeleton.id,
        "category": category,
        "weapon_req": weapon_req,
        "scaling_attr": scaling,
        "shape": {"type": ctx.shape, **ctx.shape_params},
        "condition": None,
        "reaction": {"event": event},
        "ap_cost": None,
        "cost": build_reaction_cost(ctx),
        "provenance": {"origin": "level_up"},
    }
    if tune(rng, library, base, ctx.effects, ctx.knobs):
        return _finish(library, seed, base, ctx)
    raise Retry


def _attempt_stance(
    rng: Rng, library: ContentLibrary, seed: int, tier: int, rarity: SkillRarity
) -> SkillDef:
    """姿態的一次嘗試：姿態狀態（＋自身護盾）→ 代價 → 調整強度。"""
    rules = library.composer
    skeleton = library.skeletons["stance"]
    w = rules.spell_attr_weights
    scaling = _weighted(rng, ("int", "wis", "wil"), (w.int_, w.wis, w.wil))
    theme = rng.choice(_SPELL_ELEMENTS)
    ctx = Ctx(library, rng, skeleton, rarity, tier, "spell", 1, theme)
    build_stance_effects(ctx)
    mana = rules.stance.mana
    base: dict[str, Any] = {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": rarity,
        "kind": "stance",
        "skeleton": skeleton.id,
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": scaling,
        "shape": {"type": "self"},
        "condition": None,
        "cost": {"mana": rng.randint(mana.min, mana.max) + (tier - 1)},
        "provenance": {"origin": "level_up"},
    }
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


def _compose_special(
    seed: int,
    lib: ContentLibrary,
    kind: str,
    *,
    tier: int,
    rarity: SkillRarity,
    category: str | None,
    ap_cost: int | None = None,
) -> ComposeResult | None:
    """反應技、姿態、蓄力與終結、陷阱：用獨立的亂數串流重抽；做不出合格技能回傳 ``None``。"""
    rng = Rng(seed).fork(f"composer.{kind}.build")
    chosen = category
    if kind in ("reaction", "builder_finisher", "trap") and chosen is None:
        chosen = _choose_category(rng, lib.skeletons[kind], None, lib.composer)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if kind in _EXPLICIT_ONLY_ACTIVE:  # 主動骨架：走一般的主動技能流程
                fixed = (tier, rarity, lib.skeletons[kind], chosen or "spell")
                skill = _attempt(rng, lib, seed, fixed, ap_cost)
            elif kind == "reaction":
                skill = _attempt_reaction(
                    rng, lib, seed, tier=tier, rarity=rarity, category=chosen or "weapon"
                )
            else:
                skill = _attempt_stance(rng, lib, seed, tier, rarity)
        except (Retry, ValidationError, BudgetError):
            continue
        if not validate_skill(skill, lib):
            return ComposeResult(skill, attempt)
    return None


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
    passive = skeleton_def.kinds == ("passive",) or (
        skeleton is None and _wants_passive(seed, rarity_value, lib)
    )
    special: str | None = None
    if not passive:
        explicit_kind = skeleton_def.kinds[0] if skeleton_def.kinds[0] != "active" else None
        special = explicit_kind or (
            _wants_special(seed, rarity_value, lib) if skeleton is None else None
        )
    if special is not None:
        if special not in _EXPLICIT_ONLY_ACTIVE and (
            ap_cost is not None or (special == "stance" and category not in (None, "spell"))
        ):
            raise ComposeError("反應技與姿態不花 AP：不能指定 ap_cost（姿態也不能是武器技）")
        found = _compose_special(
            seed,
            lib,
            special,
            tier=tier_value,
            rarity=rarity_value,
            category=category,
            ap_cost=ap_cost,
        )
        if found is not None:
            return found
        if skeleton is not None:
            raise ComposeError(
                f"種子 {seed}：{MAX_ATTEMPTS} 次重抽都做不出合格的{special}"
                f"（階級 {tier_value}、{rarity_value}）"
            )
    if passive and (ap_cost is not None or category not in (None, "spell")):
        raise ComposeError("被動技能是法術技、不花 AP：不能指定 ap_cost 或武器技")
    category_value = (
        "spell" if passive else _choose_category(rng, skeleton_def, category, lib.composer)
    )
    fixed = (tier_value, rarity_value, skeleton_def, category_value)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if passive:
                skill = _attempt_passive(rng, lib, seed, tier_value, rarity_value)
            else:
                skill = _attempt(rng, lib, seed, fixed, ap_cost)
        except (Retry, ValidationError, BudgetError):
            continue
        if not validate_skill(skill, lib):
            return ComposeResult(skill, attempt)
    raise ComposeError(
        f"種子 {seed}：{MAX_ATTEMPTS} 次重抽都做不出合格的技能"
        f"（階級 {tier_value}、{rarity_value}、{'passive' if passive else skeleton_def.id}、"
        f"{category_value}、AP {ap_cost}）"
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
