"""隨機技能組合器（``docs/phases/Phase2B計畫.md`` 5.1）。

``compose_random_skill(seed, ...)`` 依資料表（骨架、原語、形狀、狀態、表面、條件）隨機組出一個
通過 :func:`trpg.skillgen.validate.validate_skill` 的技能。流程：骨架 → 核心原語 → 形狀與參數 →
效果與參數 → 條件 → 代價 → 調整強度（比例 0.75–0.95）→ 驗證。失敗則用同一個亂數串流重抽，
每個種子最多 ``skill_composer.yaml`` 的 ``search.composer_attempts`` 次。

確定性：只用 :class:`trpg.shared.rng.Rng`；相同的種子與參數必得相同的技能。
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from pydantic import ValidationError

from trpg.content.composer_rules import ComposerRules
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skill_scaling import ScalingFacts
from trpg.content.skill_triggers import EVERY_N_HITS
from trpg.content.skills import (
    BORROW_AP,
    ON_AP_SPENT_ALL,
    ON_KEYWORD_EXPLOITED,
    REROLL,
    REROLL_EVENTS,
    SkillDef,
    SkillRarity,
    rarity_rank,
)
from trpg.shared.errors import TrpgError
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element
from trpg.skillgen.affinity import grant_affinity
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
from trpg.skillgen.composer_recipes import (
    SPELL_ELEMENTS,
    Draft,
    is_guardian,
    passive_drafts,
    passive_recipes,
    pick_recipe,
    reaction_drafts,
    reaction_recipes,
    summon_drafts,
    trigger_params,
    weapon_and_attr,
    weighted,
)
from trpg.skillgen.composer_rider import SUMMON_KEYWORD, add_rider, rider_keywords
from trpg.skillgen.composer_special import compose_legendary, compose_modifier
from trpg.skillgen.composer_tuning import RatioMemo, tune
from trpg.skillgen.keywords import has_keyword
from trpg.skillgen.mechanics import mechanic_tags
from trpg.skillgen.memo import by_id, draft_key, library_memo
from trpg.skillgen.scaling import retarget_scaling
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.variant_gen import variant_specs

__all__ = [
    "ComposeError",
    "ComposeResult",
    "KeywordExhaustedError",
    "compose_random_skill",
    "compose_with_stats",
    "default_library",
]

# 重抽上限（``search.composer_attempts``，HC-5b 搬進資料）。控場等骨架的核心原語若沒有旋鈕（地形、
# 障礙、驅散…），高階時強度到不了預算窗，單次成功率只有約一成，50 次偶爾全軍覆沒（Phase 3-34b，
# 種子 966）；只有原本失敗的種子會用到後半段。帶變奏的重抽次數是 ``search.variant_attempts``
# （維持 Phase 3-25b 的 25 次，已成功種子的結果不變）。

_RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic", "legendary")
_SPELL_ELEMENTS = SPELL_ELEMENTS
_weighted = weighted
_weapon_and_attr = weapon_and_attr
_trigger_params = trigger_params
_SUMMON = "summon"
"""整招召喚的骨架（RC-1：組法在 :mod:`trpg.skillgen.composer_recipes`，不走一般主動流程）。"""

type Kinds = Collection[str] | None
"""呼叫端要的技能種類（RC-1b，玩法 PM 交接 4.1.20 第 4 點；``SkillKind`` 的值）：``None`` ＝
不指定、組合器自由抽（原行為）；有值時結果的 ``kind`` 一定在其中
（見 :func:`compose_with_stats`）。"""


class ComposeError(TrpgError):
    """參數無解，或重抽上限（``search.composer_attempts``）次都做不出合格的技能。"""


class KeywordExhaustedError(ComposeError):
    """指定關鍵字時，``variants`` 個種子變體都做不出帶該關鍵字的技能（PERF-3：呼叫端用
    ``variants`` 扣搜尋上限）。"""

    def __init__(self, message: str, variants: int) -> None:
        super().__init__(message)
        self.variants = variants


@dataclass(frozen=True, slots=True)
class ComposeResult:
    """組合結果與重抽次數（``attempts`` 為 1 表示第一次就成功）。"""

    skill: SkillDef
    attempts: int
    variants: int = 1
    """指定關鍵字時用掉的種子變體數（PERF-3；沒指定關鍵字時是 1）。"""


@cache
def default_library() -> ContentLibrary:
    """預設的內容庫（``content/``），行程內只載入一次。"""
    return load_library()


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
    if skeleton.composer.hand_written_only:
        return False
    if skeleton.composer.explicit_only_active:
        return explicit and _active_feasible(skeleton, rank, library)
    if "active" not in skeleton.kinds:
        return explicit and skeleton.kinds in (
            ("passive",),
            ("reaction",),
            ("stance",),
            ("modifier",),
        )
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


def _explicit_only_active(library: ContentLibrary, name: str) -> bool:
    """主動骨架中，只在明確指定或由 :func:`_wants_special` 決定時使用的（2E-3；不影響其他種子）。
    來源：骨架 YAML 的 ``composer.explicit_only_active``（3T-8）。"""
    skeleton = library.skeletons.get(name)
    return skeleton is not None and skeleton.composer.explicit_only_active


def _legendary_skeletons(library: ContentLibrary) -> tuple[str, ...]:
    """傳說技能可用的骨架（3C-6b；骨架 YAML 的 ``composer.legendary``，依 ID 排序）。"""
    return tuple(n for n in sorted(library.skeletons) if library.skeletons[n].composer.legendary)


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
            or (r == "legendary" and skeleton in _legendary_skeletons(library))
            or (
                r != "legendary"
                and _skeleton_feasible(_known(library, skeleton), r, library, explicit=True)
            )
        )
        if not rarities:
            raise ComposeError(f"骨架 {skeleton} 在任何稀有度都做不出技能")
        weights = tuple(library.composer.rarity_weights[r] for r in rarities)
        picked = _weighted(rng, rarities, weights)
    else:
        picked = rarity
    if picked == "legendary":
        # 傳說（Phase 3C-6b）：由 composer_special 組合（核心三擇一 ＋ 源力），不走一般的骨架流程
        if skeleton is not None and skeleton not in _legendary_skeletons(library):
            allowed = "、".join(_legendary_skeletons(library))
            raise ComposeError(f"骨架 {skeleton} 不能產生傳說技能（可用：{allowed}）")
        return picked, _known(library, skeleton or "aura")
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


def _wants_special(
    seed: int, rarity: SkillRarity, library: ContentLibrary, kinds: Kinds = None
) -> str | None:
    """未指定骨架時，這個種子是否改組反應技、姿態、蓄力與終結（``builder_finisher``）或陷阱（``trap``）。

    與 :func:`_wants_passive` 一樣用獨立的亂數串流；抽中但組不出合格技能時由呼叫端退回一般主動技能。
    ``kinds``（RC-1b）：呼叫端指定種類時，種類不在其中的骨架不擲（其餘骨架各自的串流不變）。
    """
    for name, permille in (
        ("reaction", library.composer.reaction.skeleton_permille),
        ("stance", library.composer.stance.skeleton_permille),
        ("builder_finisher", library.composer.builder.skeleton_permille),
        ("trap", library.composer.trap.skeleton_permille),
        ("rune", library.composer.rune.skeleton_permille),
        ("sacrifice", library.composer.sacrifice.skeleton_permille),
        ("modifier", library.composer.special.modifier_permille),
        (_SUMMON, library.composer.recipes.summon_permille),  # RC-1：排最後，前面沒抽中的種子才擲
    ):
        skeleton = library.skeletons.get(name)
        if (
            skeleton is not None
            and (kinds is None or skeleton.kinds[0] in kinds)
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
    *,
    variant: bool = False,
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
    if core == [BORROW_AP]:  # AP-2：預支的基本款（獨立串流抽中；不走一般的形狀、效果與代價）
        if ap_cost is not None:
            raise Retry  # 指定了 AP 的題目做不出 0 AP 的預支
        return _borrow_skill(library, seed, fixed, weapon_req, scaling, ctx)
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
    elif variant:
        draft = {**base, "ap_cost": order[0], "cost": {}, "effects": ctx.effects}
        picked = _pick_variant(rng, library, draft)
        if picked is not None:
            base["variants"] = [picked]
    for ap in order:
        ctx.ap_cost = ap
        base = {**base, "ap_cost": ap, "cost": build_cost(ctx)}
        if tune(rng, library, base, ctx.effects, ctx.knobs):
            return _finish(library, seed, _with_scaling_extras(rng, library, base, ctx), ctx)
    raise Retry


def _borrow_skill(  # noqa: PLR0917 — 一次組合的參數（同 _attempt）
    library: ContentLibrary,
    seed: int,
    fixed: tuple[int, SkillRarity, SkeletonDef, str],
    weapon_req: str,
    scaling: str,
    ctx: Ctx,
) -> SkillDef:
    """預支的基本款（AP-2，06 6.3）：0 AP、冷卻 ``structure.borrow_cooldown``、形狀自身、預支 1 AP、
    只給自己，不花法力、耐力（06 6.10 最低花費的例外，AP-2b）；沒有條件與附帶效果。"""
    tier, rarity, skeleton, category = fixed
    ctx.shape, ctx.shape_params = "self", {}
    ctx.effects = [{"type": BORROW_AP, "amount": 1}]
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
        "shape": {"type": "self"},
        "condition": None,
        "provenance": {"origin": "level_up"},
        "ap_cost": 0,
        "cost": {"cooldown": library.composer.structure.borrow_cooldown},
    }
    return _finish(library, seed, base, ctx)


def _with_scaling_extras(
    rng: Rng, library: ContentLibrary, base: dict[str, Any], ctx: Ctx
) -> dict[str, Any]:
    """雙屬性縮放與專精加成（Phase 2H-2）：兩者預算都不計，所以強度調整之後才抽，只在合法時給。
    第二屬性從允許範圍（主屬性以外）抽（3H-7，06 6.10：法術技的第二屬性限在組合主題允許的集合
    內）；範圍裡沒有別的屬性時不給，改看專精。武器技不帶第二屬性（3H-6）。"""
    rules = library.composer.scaling
    base = _fit_attr(library, base, ctx)
    primary = base["scaling_attr"]
    if rarity_rank(base["rarity"]) >= rarity_rank(
        library.ruleset.core.dual_scaling_min_rarity
    ) and rng.chance_permille(rules.dual_permille):
        # 武器技的第二屬性是心智屬性（3I-3，#46）；身體類法術沒有第二屬性。給了主角屬性時，
        # 之後的 retarget_scaling 才依「第二高與最高差 ≤ 4」決定留不留、並換成主角最高的心智屬性
        facts = ScalingFacts.of_draft(
            {**base, "effects": ctx.effects, "tags": _tags(library, base, ctx)}
        )
        others = [a.value for a in library.secondary_range(facts) if a.value != primary]
        if others:
            return {**base, "secondary_scaling_attr": rng.choice(others)}
    options = []
    if ctx.shape_params.get("range") is not None:
        options.append("range")
    if any(effect["type"] == "apply_status" for effect in ctx.effects):
        options.append("duration")
    if options and rng.chance_permille(rules.mastery_permille):
        return {**base, "mastery": rng.choice(options)}
    return base


def _tags(library: ContentLibrary, base: dict[str, Any], ctx: Ctx) -> list[str]:
    """組合器技能的標籤：主題元素、骨架與機制標籤（:func:`mechanic_tags`）。機制標籤以草稿內容
    快取（PERF-2：同一次組合常對同樣的草稿算好幾次）。"""
    data = {**base, "effects": ctx.effects}
    key = draft_key(data)
    memo = library_memo(library, "composer.mechanic_tags")
    found: tuple[str, ...] | None = None if key is None else memo.get(key)
    if found is None:
        found = tuple(mechanic_tags(SkillDef.model_validate(data), library.ruleset))
        if key is not None:
            memo[key] = found
    tags: list[str] = [ctx.theme.value, ctx.skeleton.id]
    return tags + [t for t in found if t not in tags]


def _range(library: ContentLibrary, base: dict[str, Any], ctx: Ctx) -> tuple[Attribute, ...]:
    """組好的技能（含之後 :func:`_finish` 會加上的標籤）的縮放允許範圍（3H-7）。"""
    facts = ScalingFacts.of_draft(
        {**base, "effects": ctx.effects, "tags": _tags(library, base, ctx)}
    )
    return library.scaling_range(facts)


def _fit_attr(library: ContentLibrary, base: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
    """法術技的縮放屬性收進允許範圍（3H-7）：抽到的在範圍內就不動，否則取範圍裡第一個（亂數串流
    不變）。武器技已是武器大類的主屬性。"""
    if base["category"] == "weapon":
        return base
    allowed = [a.value for a in _range(library, base, ctx)]
    if not allowed or base["scaling_attr"] in allowed:
        return base
    return {**base, "scaling_attr": allowed[0]}


def _attempt_passive(  # noqa: PLR0917
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    tier: int,
    rarity: SkillRarity,
    timing_id: str | None = None,
) -> SkillDef:
    """被動技能的一次嘗試：觸發時機 → 作用對象 → 效果 → 代價 → 調整強度。``timing_id``（SK-3b）：
    指定觸發時機（不抽，例：獨立串流的「你造的關鍵字被利用時」）。"""
    rules = library.composer
    skeleton = library.skeletons["passive"]
    if timing_id is not None:
        timing = library.ruleset.skill_triggers.by_id()[timing_id]
    else:
        timings = [
            t
            for t in sorted(library.ruleset.skill_triggers.triggers, key=lambda t: t.id)
            if rarity_rank(t.min_rarity) <= rarity_rank(rarity) and t.random_composer
        ]
        timing = rng.choice(timings)
    n = (
        rng.choice(library.ruleset.core.skill_limits.every_n_hits)
        if timing.id == EVERY_N_HITS
        else None
    )
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
    trigger.update(_trigger_params(rng, library, timing.id))
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
        "cost": {"mana": ctx.quantity_randint(mana.min, mana.max) + (tier - 1) * ctx.scale},
        "provenance": {"origin": "level_up"},
    }
    if tune(rng, library, base, ctx.effects, ctx.knobs):
        return _finish(library, seed, base, ctx)
    raise Retry


def _finish(library: ContentLibrary, seed: int, base: dict[str, Any], ctx: Ctx) -> SkillDef:
    """加上名稱、標籤與暫定的敘事文字；代價依類別換成該花的資源（3H-2：武器技的法力換成等價的
    耐力，預算點數不變）；縮放屬性收進允許範圍（3H-7）。"""
    base = {**base, "cost": library.budget.resource_cost(base["cost"], base["category"])}
    base = _fit_attr(library, base, ctx)
    data = {
        **base,
        "effects": ctx.effects,
        # 名稱不帶種子（2026-10-23 使用者：「組合技能名稱拿掉 #編號」）；
        # 同一輪撞名由 roguelite 加「（二）」
        "name_zh": f"{ctx.theme.display_name}・{ctx.skeleton.name_zh}",
        "tags": _tags(library, base, ctx),
        "narrative": {
            "concept": f"隨機組合器產生的{ctx.skeleton.name_zh}技能（種子 {seed}，暫定）",
            "cast_flavor": "（暫定）力量依你的意志成形。",
        },
    }
    return SkillDef.model_validate(data)


def _tune_drafts(
    rng: Rng,
    lib: ContentLibrary,
    seed: int,
    ctx: Ctx,
    drafts: list[Draft],
    *,
    memo: RatioMemo | None = None,
) -> SkillDef:
    """RC-1 配方的草稿依序調整強度，第一個進得了預算窗的完成（旋鈕在 ``ctx.knobs``）。
    ``memo``：預算比例的快取表（QF-4b，見 :func:`tune`），不影響結果與亂數。"""
    for base, effects in drafts:
        if tune(rng, lib, base, effects, ctx.knobs, memo=memo):
            ctx.effects = effects
            return _finish(lib, seed, base, ctx)
    raise Retry


def _first_valid(lib: ContentLibrary, build: Callable[[], SkillDef]) -> ComposeResult | None:
    """RC-1 配方：最多重抽上限次，第一個通過驗證的；都做不出來回傳 ``None``。"""
    for attempt in range(1, lib.composer.search.composer_attempts + 1):
        try:
            skill = build()
        except (Retry, ValidationError, BudgetError):
            continue
        if not validate_skill(skill, lib):
            return ComposeResult(skill, attempt)
    return None


def _compose_summon(
    seed: int, lib: ContentLibrary, *, tier: int, rarity: SkillRarity, keyword: str | None
) -> ComposeResult | None:
    """整招召喚（RC-1，4.1.19 第 1 點）：獨立串流 ``composer.summon.build``。"""
    rng = Rng(seed).fork("composer.summon.build")

    def build() -> SkillDef:
        ctx, drafts = summon_drafts(rng, lib, seed, tier=tier, rarity=rarity, keyword=keyword)
        return _tune_drafts(rng, lib, seed, ctx, drafts)

    return _first_valid(lib, build)


def _compose_exploit_passive(
    seed: int, lib: ContentLibrary, *, tier: int, rarity: SkillRarity, keyword: str | None
) -> ComposeResult | None:
    """「你造的關鍵字被利用時」的被動（SK-3b，玩法交接 4.1.30 第 5 點）：獨立串流
    ``composer.exploit`` 以 ``structure.exploit_passive_permille`` 決定要不要用，組法用
    ``composer.exploit.build``；沒抽中、指定了關鍵字或組不出合格技能回傳 ``None``，呼叫端照原本的
    組法（主串流沒動過，結果與改前相同）。"""
    permille = lib.composer.structure.exploit_passive_permille
    timing = lib.ruleset.skill_triggers.by_id().get(ON_KEYWORD_EXPLOITED)
    if keyword is not None or permille <= 0 or timing is None:
        return None
    if rarity_rank(timing.min_rarity) > rarity_rank(rarity):
        return None
    if not Rng(seed).fork("composer.exploit").chance_permille(permille):
        return None
    rng = Rng(seed).fork("composer.exploit.build")

    def build() -> SkillDef:
        return _attempt_passive(rng, lib, seed, tier, rarity, ON_KEYWORD_EXPLOITED)

    return _first_valid(lib, build)


def _compose_ap_spent_passive(
    seed: int, lib: ContentLibrary, *, tier: int, rarity: SkillRarity, keyword: str | None
) -> ComposeResult | None:
    """「這回合用完所有 AP 時」的被動（AP-2，#168，05 5.2）：獨立串流 ``composer.ap_spent`` 以
    ``structure.ap_spent_passive_permille`` 決定要不要用，組法用 ``composer.ap_spent.build``；
    沒抽中、指定了關鍵字或組不出合格技能回傳 ``None``，呼叫端照原本的組法（主串流沒動過，結果與改前
    相同）。"""
    permille = lib.composer.structure.ap_spent_passive_permille
    timing = lib.ruleset.skill_triggers.by_id().get(ON_AP_SPENT_ALL)
    if keyword is not None or permille <= 0 or timing is None:
        return None
    if rarity_rank(timing.min_rarity) > rarity_rank(rarity):
        return None
    if not Rng(seed).fork("composer.ap_spent").chance_permille(permille):
        return None
    rng = Rng(seed).fork("composer.ap_spent.build")

    def build() -> SkillDef:
        return _attempt_passive(rng, lib, seed, tier, rarity, ON_AP_SPENT_ALL)

    return _first_valid(lib, build)


_AROUND = "ring"
"""被動的「自身周圍」形狀（WC-2）。"""


def _compose_around_passive(
    seed: int, lib: ContentLibrary, *, tier: int, rarity: SkillRarity
) -> ComposeResult | None:
    """「自身周圍」小範圍的被動（WC-2，#167；06 6.9）：獨立串流 ``composer.passive.around`` 以
    ``passive.around_permille`` 決定要不要用，組法用 ``composer.passive.around.build``；被動骨架
    沒有開環形、沒抽中或組不出合格技能回傳 ``None``，呼叫端照原本的組法（主串流沒動過，結果與改前
    相同）。"""
    permille = lib.composer.passive.around_permille
    skeleton = lib.skeletons.get("passive")
    if permille <= 0 or skeleton is None or _AROUND not in skeleton.shapes:
        return None
    if not Rng(seed).fork("composer.passive.around").chance_permille(permille):
        return None
    rng = Rng(seed).fork("composer.passive.around.build")

    def build() -> SkillDef:
        return _attempt_around_passive(rng, lib, seed, tier, rarity)

    return _first_valid(lib, build)


def _attempt_around_passive(
    rng: Rng, library: ContentLibrary, seed: int, tier: int, rarity: SkillRarity
) -> SkillDef:
    """「自身周圍」被動的一次嘗試：觸發時機 → 持有者周圍一圈（半徑照骨架的 ``max_radius``）→ 對敵的
    傷害或有害狀態（同 ``target: other`` 的效果候選）→ 代價 → 調整強度。"""
    rules = library.composer
    skeleton = library.skeletons["passive"]
    timings = [
        t
        for t in sorted(library.ruleset.skill_triggers.triggers, key=lambda t: t.id)
        if rarity_rank(t.min_rarity) <= rarity_rank(rarity) and t.random_composer
    ]
    timing = rng.choice(timings)
    n = (
        rng.choice(library.ruleset.core.skill_limits.every_n_hits)
        if timing.id == EVERY_N_HITS
        else None
    )
    w = rules.spell_attr_weights
    scaling = _weighted(rng, ("int", "wis", "wil"), (w.int_, w.wis, w.wil))
    theme = rng.choice(_SPELL_ELEMENTS)
    ctx = Ctx(library, rng, skeleton, rarity, tier, "spell", 1, theme)
    radius = skeleton.max_radius or 1
    ctx.shape, ctx.shape_params = _AROUND, {"radius": radius}
    build_passive_effects(ctx, "other")
    for effect in ctx.effects:
        effect["affects"] = "enemies"
    trigger: dict[str, Any] = {"event": timing.id, "target": "self", "max_per_round": 1}
    if n is not None:
        trigger["n"] = n
    trigger.update(_trigger_params(rng, library, timing.id))
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
        "shape": {"type": _AROUND, "radius": radius},
        "condition": None,
        "trigger": trigger,
        "cost": build_passive_cost(ctx),
        "provenance": {"origin": "level_up"},
    }
    if tune(rng, library, base, ctx.effects, ctx.knobs):
        return _finish(library, seed, base, ctx)
    raise Retry


def _compose_reroll_reaction(
    seed: int, lib: ContentLibrary, *, tier: int, rarity: SkillRarity, keyword: str | None
) -> ComposeResult | None:
    """重擲反應技（SK-3b，玩法交接 4.1.30 第 5 點）：獨立串流 ``composer.reroll`` 以
    ``structure.reroll_reaction_permille`` 決定要不要用；時機在「隊友擲失手時」「敵人擲中你時」
    兩個裡抽，效果只有重擲（形狀自身）。沒抽中、指定了關鍵字或組不出合格技能回傳 ``None``。"""
    permille = lib.composer.structure.reroll_reaction_permille
    reroll = by_id(lib.ruleset.primitives).get(REROLL)
    if keyword is not None or permille <= 0 or reroll is None:
        return None
    if rarity_rank(reroll.min_rarity) > rarity_rank(rarity):
        return None
    if not Rng(seed).fork("composer.reroll").chance_permille(permille):
        return None
    rng = Rng(seed).fork("composer.reroll.build")

    def build() -> SkillDef:
        return _attempt_reroll(rng, lib, seed, tier=tier, rarity=rarity)

    return _first_valid(lib, build)


def _attempt_reroll(
    rng: Rng, library: ContentLibrary, seed: int, *, tier: int, rarity: SkillRarity
) -> SkillDef:
    """重擲反應技的一次嘗試：時機 → 代價（照反應技的代價抽法）→ 不調強度（重擲沒有旋鈕）。
    縮放屬性取身體類（重擲沒有法術主題，``scaling.range`` 只收力量、敏捷、體質）。"""
    skeleton = library.skeletons["reaction"]
    event = rng.choice(REROLL_EVENTS)
    ctx = Ctx(library, rng, skeleton, rarity, tier, "spell", 1, Element.PHYSICAL)
    ctx.shape = "self"
    ctx.effects = [{"type": REROLL}]
    base: dict[str, Any] = {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": rarity,
        "kind": "reaction",
        "skeleton": skeleton.id,
        "category": "spell",
        "weapon_req": "any",
        "scaling_attr": rng.choice(("dex", "con")),
        "shape": {"type": "self"},
        "condition": None,
        "reaction": {"event": event},
        "ap_cost": None,
        "cost": build_reaction_cost(ctx),
        "provenance": {"origin": "level_up"},
    }
    return _finish(library, seed, base, ctx)


def _compose_passive_recipe(
    seed: int, lib: ContentLibrary, *, tier: int, rarity: SkillRarity, keyword: str | None
) -> ComposeResult | None:
    """被動新配方（RC-1）：獨立串流決定要不要用（:func:`pick_recipe`）與組法；沒抽中或組不出來
    回傳 ``None``，呼叫端照原本的組法（亂數串流沒動過，結果與 RC-1 前相同）。"""
    rules = lib.composer.recipes
    recipe = pick_recipe(
        seed, "passive", passive_recipes(lib, tier), rules.passive_permille, keyword
    )
    if recipe is None:
        return None
    rng = Rng(seed).fork("composer.passive.recipe.build")

    def build() -> SkillDef:
        ctx, drafts = passive_drafts(
            rng, lib, seed, tier=tier, rarity=rarity, recipe=recipe, keyword=keyword
        )
        return _tune_drafts(rng, lib, seed, ctx, drafts)

    return _first_valid(lib, build)


def _compose_reaction_recipe(
    seed: int,
    lib: ContentLibrary,
    *,
    tier: int,
    rarity: SkillRarity,
    category: str | None,
    keyword: str | None,
) -> ComposeResult | None:
    """反應技新配方（RC-1）：同 :func:`_compose_passive_recipe`。

    護主（QF-4b）：3 階起每份草稿在最弱強度就進不了預算窗，每次嘗試卻都重算約 40 份（召喚物、
    屬性、強度、代價的組合有限，只差種子）；預算比例改由內容庫上的快取表記住，亂數與結果不變。
    """
    rules = lib.composer.recipes
    recipe = pick_recipe(
        seed, "reaction", reaction_recipes(lib, tier), rules.reaction_permille, keyword
    )
    if recipe is None:
        return None
    rng = Rng(seed).fork("composer.reaction.recipe.build")
    chosen = category or _choose_category(rng, lib.skeletons["reaction"], None, lib.composer)
    memo: RatioMemo | None = (
        library_memo(lib, "composer.guardian.ratio") if is_guardian(recipe) else None
    )

    def build() -> SkillDef:
        ctx, drafts = reaction_drafts(
            rng, lib, seed, tier=tier, rarity=rarity, category=chosen, recipe=recipe,
            keyword=keyword,
        )  # fmt: skip
        return _tune_drafts(rng, lib, seed, ctx, drafts, memo=memo)

    return _first_valid(lib, build)


def _compose_special(
    seed: int,
    lib: ContentLibrary,
    kind: str,
    *,
    tier: int,
    rarity: SkillRarity,
    category: str | None,
    ap_cost: int | None = None,
    keyword: str | None = None,
) -> ComposeResult | None:
    """反應技、姿態、蓄力與終結、陷阱、整招召喚：用獨立的亂數串流重抽；做不出合格技能回傳 ``None``。
    ``keyword``（RC-1）：整招召喚優先抽固有關鍵字相符的召喚物；反應技的新配方只考慮帶得到它的。"""
    if kind == _SUMMON:
        return _compose_summon(seed, lib, tier=tier, rarity=rarity, keyword=keyword)
    if kind == "reaction":
        reroll = category in (None, "spell")  # 重擲是法術技（不看武器）
        found = (
            _compose_reroll_reaction(seed, lib, tier=tier, rarity=rarity, keyword=keyword)
            if reroll
            else None
        ) or _compose_reaction_recipe(
            seed, lib, tier=tier, rarity=rarity, category=category, keyword=keyword
        )
        if found is not None:
            return found
    rng = Rng(seed).fork(f"composer.{kind}.build")
    if kind == "modifier":
        modifier = compose_modifier(seed, lib)
        return None if modifier is None else ComposeResult(modifier, 1)
    chosen = category
    if kind in ("reaction", "builder_finisher", "trap", "rune") and chosen is None:
        chosen = _choose_category(rng, lib.skeletons[kind], None, lib.composer)
    if kind == "sacrifice":
        chosen = chosen or "spell"  # 獻祭是法術技
    for attempt in range(1, lib.composer.search.composer_attempts + 1):
        try:
            if _explicit_only_active(lib, kind):  # 主動骨架：走一般的主動技能流程
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


def _check_passive_args(passive: bool, ap_cost: int | None, category: str | None) -> None:
    if passive and (ap_cost is not None or category not in (None, "spell")):
        raise ComposeError("被動技能是法術技、不花 AP：不能指定 ap_cost 或武器技")


def _compose_legendary_result(
    seed: int, lib: ContentLibrary, tier: int | None, skeleton: str | None, ap_cost: int | None
) -> ComposeResult:
    """傳說技能（Phase 3C-6b）：``composer_special.compose_legendary``；``skeleton`` 為 ``modifier``
    時核心只能是修正規則，``aura`` 時只能是規則改變或改寫規則型原語。"""
    if ap_cost is not None and ap_cost != lib.ruleset.core.legendary_activation_ap:
        raise ComposeError("傳說技能的 AP 固定為啟動 AP，不能指定 ap_cost")
    only = (
        None
        if skeleton is None
        else ("modifier",)
        if skeleton == "modifier"
        else ("rule_change", "rule_rewrite")
    )
    skill = compose_legendary(seed, lib, tier=tier, cores=only)
    if skill is None:
        raise ComposeError(f"種子 {seed}：做不出合格的傳說技能（階級 {tier}、骨架 {skeleton}）")
    return ComposeResult(skill, 1)


_VARIANT_STEP = 1_000_003


def _relabel(skill: SkillDef, variant: int, seed: int) -> SkillDef:
    """把變體種子組出的技能改回使用者給的種子（ID、名稱與暫定敘事文字）。"""
    swaps = ((f"skill_rand_{variant}", f"skill_rand_{seed}"), (f"#{variant}", f"#{seed}"))

    def fix(text: str) -> str:
        for old, new in swaps:
            text = text.replace(old, new)
        return text.replace(f"種子 {variant}", f"種子 {seed}")

    narrative = skill.narrative.model_copy(
        update={
            "concept": fix(skill.narrative.concept),
            "cast_flavor": fix(skill.narrative.cast_flavor),
        }
    )
    return skill.model_copy(
        update={"id": fix(skill.id), "name_zh": fix(skill.name_zh), "narrative": narrative}
    )


def _allows_active(kinds: Kinds) -> bool:
    return kinds is None or "active" in kinds


def _kind_skeleton(kinds: Kinds, lib: ContentLibrary) -> str | None:
    """指定種類（RC-1b）只有一種、而且不是主動時，用同名骨架（被動、反應、姿態、修正各有同名骨架）。"""
    if kinds is None or _allows_active(kinds) or len(kinds) != 1:
        return None
    (kind,) = kinds
    return kind if kind in lib.skeletons else None


def _kind_ok(skill: SkillDef, kinds: Kinds) -> bool:
    return kinds is None or skill.kind in kinds


_STACK_SKELETON = "builder_finisher"
"""累積、消耗層數的骨架（KW-2：層數關鍵字指定時用）。"""


def _is_stack_keyword(keyword: str, lib: ContentLibrary) -> bool:
    """關鍵字 ID 就是組合器會抽的層數 ID（KW-1／KW-2：連擊、怒氣、專注、氣）。"""
    return any(s.id == keyword and s.composer for s in lib.ruleset.stacks.stacks)


def _rider_permille(keyword: str, lib: ContentLibrary) -> int:
    """關鍵字附帶配方（WC-2）的機率：召喚物 ``summon_rider_permille``、層數
    ``stack_rider_permille``。"""
    rules = lib.composer.structure
    if keyword == SUMMON_KEYWORD:
        return rules.summon_rider_permille
    return rules.stack_rider_permille


def _compose_rider(
    variant: int, keyword: str, lib: ContentLibrary, kwargs: Mapping[str, Any]
) -> ComposeResult | None:
    """關鍵字附帶配方（WC-2，#167 第 5 題；:mod:`trpg.skillgen.composer_rider`）：獨立串流
    ``composer.rider`` 以 :func:`_rider_permille` 決定這個變體要不要改走附帶配方——不指定關鍵字組一招
    主動技，再多一個累積／消耗層數或號令；沒抽中或做不出來回傳 ``None``，呼叫端照原本的組法（主串流
    沒動過，結果與改前相同）。呼叫端指定了骨架或種類不含主動時不用。"""
    permille = _rider_permille(keyword, lib)
    kinds: Kinds = kwargs.get("kinds")
    if (
        permille <= 0
        or keyword not in rider_keywords(lib)
        or kwargs.get("skeleton") is not None
        or not _allows_active(kinds)
    ):
        return None
    if not Rng(variant).fork("composer.rider").chance_permille(permille):
        return None
    fixed = {**kwargs, "kinds": ("active",)}
    try:
        found = _compose_plain(variant, lib, **fixed)
    except ComposeError:
        return None
    skill = add_rider(lib, found.skill, keyword, Rng(variant).fork("composer.rider.build"))
    return None if skill is None else ComposeResult(skill, found.attempts)


def _compose_with_keyword(
    seed: int,
    keyword: str,
    lib: ContentLibrary,
    *,
    tries: int | None = None,
    skip_legendary: bool = False,
    rarity: SkillRarity | None,
    **kwargs: Any,
) -> ComposeResult:
    """依種子變體重抽，直到技能製造或利用 ``keyword``（確定性：同樣的參數必得同樣的技能）。

    PERF-3（玩法 PM 2026-11-03）：``skip_legendary`` 為真且沒有指定稀有度時，**抽到傳說的變體直接
    跳過**（不組；三選一的候選產生器用：傳說不當候選，而且多半做不出指定關鍵字），跳過的變體也
    算一次嘗試。``tries``：最多試幾個變體（``None`` ＝ ``search.keyword_tries``，也是上限；橋接搜尋
    用剩下的上限）。"""
    if keyword not in lib.keywords.ids():
        raise ComposeError(f"未知的關鍵字 {keyword!r}（可用：{'、'.join(lib.keywords.ids())}）")
    if not lib.keywords.by_id()[keyword].composable:
        raise ComposeError(f"組合器做不出關鍵字 {keyword} 的技能（該關鍵字需要手寫技能）")
    kinds: Kinds = kwargs.get("kinds")
    original = dict(kwargs)
    if kwargs.get("skeleton") is None and _is_stack_keyword(keyword, lib) and _allows_active(kinds):
        # KW-2（#161）：層數關鍵字只有蓄力骨架做得出來（累積或消耗層數），不指定骨架時固定用它；
        # 這四個關鍵字 KW-2 前組合器不做，所以既有關鍵字的結果不變
        kwargs = {**kwargs, "skeleton": _STACK_SKELETON}
    most = lib.composer.search.keyword_tries
    limit = most if tries is None else min(tries, most)
    plain = {"rarity": rarity, "no_legendary": skip_legendary and rarity is None, **original}
    for index in range(limit):
        variant = seed + index * _VARIANT_STEP
        rider = _compose_rider(variant, keyword, lib, plain)  # WC-2：沒抽中＝None，照原本
        try:
            found = rider or _with_affinity(
                _compose_plain(
                    variant,
                    lib,
                    rarity=rarity,
                    no_legendary=skip_legendary and rarity is None,
                    keyword=keyword,
                    **kwargs,
                ),
                None,
                lib,
            )
        except ComposeError:
            continue
        # PERF-2：只看這個關鍵字的規則；RC-1：只認專屬規則（和退回路徑、三選一的候選一致，
        # 只帶到通用規則的技能交出去也會被拒）；RC-1b：呼叫端指定種類時種類也要對（傳說）
        if _kind_ok(found.skill, kinds) and has_keyword(
            found.skill, keyword, lib.keywords, exclusive_only=True
        ):
            skill = found.skill if index == 0 else _relabel(found.skill, variant, seed)
            return ComposeResult(skill, found.attempts, index + 1)
    raise KeywordExhaustedError(
        f"種子 {seed}：{limit} 次嘗試都做不出帶有關鍵字 {keyword} 的技能", limit
    )


def compose_with_stats(
    seed: int,
    *,
    tier: int | None = None,
    rarity: SkillRarity | None = None,
    skeleton: str | None = None,
    category: str | None = None,
    ap_cost: int | None = None,
    library: ContentLibrary | None = None,
    keyword: str | None = None,
    hero_attributes: Mapping[Attribute, int] | None = None,
    avoid_attr: Attribute | None = None,
    held: Mapping[str, str] | None = None,
    keyword_tries: int | None = None,
    skip_legendary: bool = False,
    kinds: Kinds = None,
) -> ComposeResult:
    """:func:`compose_random_skill`，另外回傳重抽次數。PERF-3（三選一的候選產生器用）：
    ``keyword_tries`` ＝ 指定關鍵字時最多試幾個種子變體（橋接搜尋上限，最多
    ``search.keyword_tries``；``None`` ＝ 上限），
    ``skip_legendary`` ＝ 指定關鍵字時抽到傳說的變體跳過。預設值＝原行為。

    ``kinds``（RC-1b，玩法 PM 交接 4.1.20 第 4 點）：呼叫端知道要哪一種技能時傳入（``SkillKind``
    的值）。沒指定骨架時：只有一種、而且不是主動（被動、反應、姿態、修正）＝ 用同名骨架；含主動
    時，被動與特殊組法裡種類不在其中的不擲（各自的獨立串流不變）。結果的 ``kind`` 不在其中時
    （例：傳說）指定關鍵字的變體跳過、不指定關鍵字的丟 :class:`ComposeError`。
    ``None`` ＝ 原行為。"""
    lib = library if library is not None else default_library()
    fixed: dict[str, Any] = {
        "tier": tier,
        "rarity": rarity,
        "skeleton": skeleton if skeleton is not None else _kind_skeleton(kinds, lib),
        "category": category,
        "ap_cost": ap_cost,
        "kinds": kinds,
    }
    if keyword is not None:
        found = _compose_with_keyword(
            seed, keyword, lib, tries=keyword_tries, skip_legendary=skip_legendary, **fixed
        )
    else:
        found = _compose_plain(seed, lib, **fixed)
        if not _kind_ok(found.skill, kinds):
            raise ComposeError(f"種子 {seed}：組出的技能種類 {found.skill.kind} 不在指定的種類內")
    if hero_attributes is None:
        return _with_affinity(found, held, lib)
    # 新技能跟主屬性（Phase 3H-3）：亂數串流不變，組完之後才改縮放屬性（武器技一律看武器大類）
    skill = retarget_scaling(found.skill, hero_attributes, lib, avoid=avoid_attr)
    found = found if skill is found.skill else ComposeResult(skill, found.attempts)
    return _with_affinity(found, held, lib)


def _with_affinity(
    found: ComposeResult, held: Mapping[str, str] | None, library: ContentLibrary
) -> ComposeResult:
    """武器親和（Phase 3I-5）：給了主角手上的裝備時，附帶效果上的常見條件換成手持武器條件。"""
    skill = grant_affinity(found.skill, held, library)
    return found if skill is found.skill else ComposeResult(skill, found.attempts)


def _wants_variant(seed: int, rarity: SkillRarity, library: ContentLibrary) -> bool:
    """稀有以上的主動技能以低權重帶一個戰場變奏（Phase 3-25b）：獨立的亂數串流，沒有抽中的種子
    結果與以往完全相同。"""
    return rarity != "common" and (
        Rng(seed).fork("composer.variant").chance_permille(library.composer.variant.permille)
    )


def _pick_variant(
    rng: Rng, library: ContentLibrary, draft: dict[str, Any]
) -> dict[str, Any] | None:
    """候選中第一個（亂數順序）能和已組好的結構組成合法 schema 的變奏；預算窗在強度調整與最後的
    驗證處理。"""
    for spec in rng.shuffled(variant_specs(library)):
        try:
            SkillDef.model_validate({**draft, "variants": [spec]})
        except ValidationError:
            continue
        return spec
    return None


def _legendary_unless(  # noqa: PLR0917 — 傳說的參數照原樣轉交
    skip: bool,
    seed: int,
    lib: ContentLibrary,
    tier: int | None,
    skeleton: str | None,
    ap_cost: int | None,
) -> ComposeResult:
    """抽到傳說：``skip``（PERF-3，指定關鍵字的組合不抽傳說）時這個變體跳過，否則照常組傳說。"""
    if skip:
        raise ComposeError(f"種子 {seed}：抽到傳說（指定關鍵字時跳過）")
    return _compose_legendary_result(seed, lib, tier, skeleton, ap_cost)


def _special_kind(
    seed: int,
    rarity: SkillRarity,
    skeleton: str | None,
    skeleton_def: SkeletonDef,
    lib: ContentLibrary,
    *,
    kinds: Kinds = None,
) -> str | None:
    """主動以外的組法：明確指定的種類（反應、姿態……；RC-1 起含整招召喚），沒指定骨架時由
    :func:`_wants_special` 的獨立串流決定。"""
    if skeleton == _SUMMON:  # RC-1：整招召喚不走一般主動流程
        return _SUMMON
    if skeleton_def.kinds[0] != "active":
        return skeleton_def.kinds[0]
    return _wants_special(seed, rarity, lib, kinds) if skeleton is None else None


def _special_result(
    seed: int,
    lib: ContentLibrary,
    special: str,
    *,
    explicit: bool,
    fixed: tuple[int, SkillRarity, str | None, int | None],
    keyword: str | None,
) -> ComposeResult | None:
    """反應技、姿態等特殊組法；``explicit``（明確指定骨架）時組不出來就拋出 :class:`ComposeError`，
    否則回傳 ``None`` 讓呼叫端退回一般主動技能。"""
    tier, rarity, category, ap_cost = fixed
    if not _explicit_only_active(lib, special) and (
        ap_cost is not None or (special == "stance" and category not in (None, "spell"))
    ):
        raise ComposeError("反應技與姿態不花 AP：不能指定 ap_cost（姿態也不能是武器技）")
    found = _compose_special(
        seed,
        lib,
        special,
        tier=tier,
        rarity=rarity,
        category=category,
        ap_cost=ap_cost,
        keyword=keyword,
    )
    if found is None and explicit:
        raise ComposeError(
            f"種子 {seed}：{lib.composer.search.composer_attempts} 次重抽都做不出合格的{special}"
            f"（階級 {tier}、{rarity}）"
        )
    return found


def _compose_plain(
    seed: int,
    lib: ContentLibrary,
    *,
    tier: int | None,
    rarity: SkillRarity | None,
    skeleton: str | None,
    category: str | None,
    ap_cost: int | None,
    no_legendary: bool = False,
    keyword: str | None = None,
    kinds: Kinds = None,
) -> ComposeResult:
    rng = Rng(seed)
    tier_value = tier if tier is not None else rng.randint(1, lib.ruleset.core.skill_limits.tiers)
    if tier_value not in lib.ruleset.core.tier_budget:
        raise ComposeError(f"沒有階級 {tier_value} 的預算")
    rarity_value, skeleton_def = _choose_rarity_and_skeleton(rng, rarity, skeleton, lib)
    if rarity_value == "legendary":
        return _legendary_unless(no_legendary, seed, lib, tier, skeleton, ap_cost)
    passive = skeleton_def.kinds == ("passive",) or (
        skeleton is None
        and (kinds is None or "passive" in kinds)
        and _wants_passive(seed, rarity_value, lib)
    )
    special = (
        None
        if passive
        else _special_kind(seed, rarity_value, skeleton, skeleton_def, lib, kinds=kinds)
    )
    if special is not None:
        found = _special_result(
            seed,
            lib,
            special,
            explicit=skeleton is not None,
            fixed=(tier_value, rarity_value, category, ap_cost),
            keyword=keyword,
        )
        if found is not None:
            return found
    _check_passive_args(passive, ap_cost, category)
    recipe = (
        _compose_exploit_passive(seed, lib, tier=tier_value, rarity=rarity_value, keyword=keyword)
        or _compose_ap_spent_passive(
            seed, lib, tier=tier_value, rarity=rarity_value, keyword=keyword
        )
        or _compose_around_passive(seed, lib, tier=tier_value, rarity=rarity_value)
        or _compose_passive_recipe(seed, lib, tier=tier_value, rarity=rarity_value, keyword=keyword)
        if passive
        else None
    )
    if recipe is not None:
        return recipe
    category_value = (
        "spell" if passive else _choose_category(rng, skeleton_def, category, lib.composer)
    )
    fixed = (tier_value, rarity_value, skeleton_def, category_value)
    wants_variant = not passive and _wants_variant(seed, rarity_value, lib)
    search = lib.composer.search
    for attempt in range(1, search.composer_attempts + 1):
        try:
            if passive:
                skill = _attempt_passive(rng, lib, seed, tier_value, rarity_value)
            else:
                # 前半的重抽帶變奏；都做不出來時退回不帶變奏，確保一定有結果
                variant = wants_variant and attempt <= search.variant_attempts
                skill = _attempt(rng, lib, seed, fixed, ap_cost, variant=variant)
        except (Retry, ValidationError, BudgetError):
            continue
        if not validate_skill(skill, lib):
            return ComposeResult(skill, attempt)
    raise ComposeError(
        f"種子 {seed}：{search.composer_attempts} 次重抽都做不出合格的技能"
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
    keyword: str | None = None,
    hero_attributes: Mapping[Attribute, int] | None = None,
    avoid_attr: Attribute | None = None,
    held: Mapping[str, str] | None = None,
    kinds: Kinds = None,
) -> SkillDef:
    """依種子組出一個合格的隨機技能（``id`` 為 ``skill_rand_<seed>``）。

    ``keyword``（Phase 3-24b1，6.27.4）：技能必須製造或利用這個關鍵字；沒有指定時結果與以往
    完全相同（亂數串流不變）。

    ``hero_attributes``（Phase 3H-3，07 7.2）：給主角的屬性時，縮放屬性改取其中最高的、且在
    ``skill_scaling.yaml`` 允許範圍內的屬性（同分依六屬性順序；見
    :func:`trpg.skillgen.scaling.retarget_scaling`），``avoid_attr`` 為不要取的屬性（候選的
    「新方向」）。其餘內容與沒給時完全相同。

    ``held``（Phase 3I-5，06 6.10 #50）：主角手上的主手武器與副手（ID → 中文名）；給了就可能把
    附帶效果上的常見條件換成「手持某種武器時」（:func:`trpg.skillgen.affinity.grant_affinity`）。

    ``kinds``（RC-1b）：呼叫端知道種類時傳入，見 :func:`compose_with_stats`。"""
    return compose_with_stats(
        seed,
        tier=tier,
        rarity=rarity,
        skeleton=skeleton,
        category=category,
        ap_cost=ap_cost,
        library=library,
        keyword=keyword,
        hero_attributes=hero_attributes,
        avoid_attr=avoid_attr,
        held=held,
        kinds=kinds,
    ).skill
