"""白板技能：組合器的「單一效果」模式與白板定義的驗證（Phase 3W-4，
``docs/design/06-技能.md`` 6.34.1）。

**白板** ＝ 1 階、一個核心效果、一個關鍵字、形狀簡單（單體或小範圍）、沒有附帶效果；主動技用預設費用
（AP 2、冷卻 0～2）；預算照同階規則（比例 70～100%）。分主動、被動、反應三種（升級與任務三選一的
種類比例 70／20／10，``content/skill_composer.yaml`` 的 ``whiteboard.kind_permille``）。

**單一效果模式**（:func:`compose_whiteboard`）：從 ``whiteboard`` 的配方（一個關鍵字的一個核心效果）
挑一個，再用組合器既有的零件填形狀、旋鈕（骰子、倍率、持續……）與費用，強度調整到預算區間內，最後過
``validate_skill`` 與 :func:`whiteboard_problems`。完整模式（:func:`~trpg.skillgen.random_composer.
compose_random_skill`）不受影響，留給之後的完整技能三選一。

**確定性**：亂數只來自 ``Rng(seed).fork("whiteboard")``；相同的種子與參數必得相同的白板。
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from fractions import Fraction
from typing import Any, Literal

from pydantic import ValidationError

from trpg.content.composer_rules import WhiteboardRecipe, WhiteboardRules
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, SkillRarity, rarity_rank, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Ctx, Retry, _needs_cooldown, build_shape
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.random_composer import (
    ComposeError,
    _finish,
    _weapon_and_attr,
    default_library,
)
from trpg.skillgen.scaling import retarget_scaling
from trpg.skillgen.validate import rarity_requirements, validate_skill

__all__ = [
    "WHITEBOARD_KINDS",
    "WhiteboardKind",
    "compose_whiteboard",
    "is_whiteboard",
    "whiteboard_keywords",
    "whiteboard_problems",
]

type WhiteboardKind = Literal["active", "passive", "reaction"]
"""白板的種類：``active``（主動）、``passive``（被動）、``reaction``（反應）。"""
WHITEBOARD_KINDS: tuple[WhiteboardKind, ...] = ("active", "passive", "reaction")

_MIN_RATIO = Fraction(7, 10)
_MAX_RATIO = Fraction(1)
_SIMPLE_SHAPES = frozenset({"self", "single", "ground_tile", "cross", "square3"})
"""白板允許的形狀：自身、單體、單格、十字與 3×3（小範圍）。"""


def _rules(library: ContentLibrary) -> WhiteboardRules:
    return library.composer.whiteboard


def whiteboard_keywords(library: ContentLibrary, kind: str = "active") -> frozenset[str]:
    """``kind`` 的白板配方涵蓋的關鍵字（沒有配方的關鍵字由呼叫端退回別的來源）。"""
    return frozenset(r.keyword for r in _rules(library).recipes(kind))


# ---------------------------------------------------------------------------
# 驗證
# ---------------------------------------------------------------------------


def whiteboard_problems(
    skill: SkillDef, library: ContentLibrary, tier: int | None = None
) -> list[str]:
    """白板定義的檢查（06 6.34.1）；空串列 ＝ 是白板。逐條列出不符合的地方（繁體中文）。

    - 階級等於 ``tier``（角色目前階級，6.34.9；省略 ＝ 不檢查），主動／被動／反應；
    - 一個核心效果：所有層級的效果合計 1 個，沒有附帶效果、條件、修正規則、變奏、第二段、陷阱；
    - 一個關鍵字（專屬規則推導）；
    - 形狀簡單（自身、單體、單格、十字、3×3）；
    - 主動技用預設費用：AP ＝ ``ap_cost``、冷卻不超過範圍上限，沒有每場次數、自身狀態、透支；
    - 預算比例在 70～100%（同階規則）。
    """
    rules = _rules(library)
    problems: list[str] = []
    if tier is not None and skill.tier != tier:
        problems.append(f"白板必須是 {tier} 階，收到 {skill.tier} 階")
    if skill.kind not in WHITEBOARD_KINDS:
        problems.append(f"白板只能是主動、被動或反應，收到 {skill.kind}")
    problems += _structure_problems(skill)
    keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    if len(keywords) != 1:
        problems.append(f"白板必須剛好一個關鍵字，收到 {len(keywords)} 個（{'、'.join(keywords)}）")
    if skill.shape.type not in _SIMPLE_SHAPES:
        problems.append(f"白板的形狀必須簡單（單體或小範圍），收到 {skill.shape.type}")
    if skill.kind == "active":
        problems += _cost_problems(skill, rules)
    try:
        ratio = skill_budget(skill, library).ratio
    except BudgetError as exc:
        problems.append(f"預算算不出來：{exc}")
    else:
        if not _MIN_RATIO <= ratio <= _MAX_RATIO:
            problems.append(f"預算比例必須在 70%～100%，收到 {float(ratio) * 100:.0f}%")
    return problems


def _structure_problems(skill: SkillDef) -> list[str]:
    problems: list[str] = []
    effect_count = len(list(skill.iter_effects(include_followup=True, include_variants=True)))
    if len(skill.effects) != 1 or effect_count != 1:
        problems.append(f"白板只能有 1 個核心效果（沒有附帶效果），收到 {effect_count} 個")
    if skill.condition is not None or any(e.condition is not None for e in skill.effects):
        problems.append("白板不能有條件")
    extras = (
        ("修正規則", bool(skill.modifiers)),
        ("變奏", bool(skill.variants)),
        ("第二段", skill.followup is not None),
        ("陷阱", skill.trap is not None),
        ("專精", skill.mastery is not None),
        ("第二縮放屬性", skill.secondary_scaling_attr is not None),
    )
    problems += [f"白板不能有{label}" for label, present in extras if present]
    return problems


def _cost_problems(skill: SkillDef, rules: WhiteboardRules) -> list[str]:
    problems: list[str] = []
    cost = skill.cost
    if skill.ap_cost != rules.ap_cost:
        problems.append(f"主動白板的 AP 必須是 {rules.ap_cost}，收到 {skill.ap_cost}")
    if (cost.cooldown or 0) > rules.cooldown.max:
        problems.append(f"主動白板的冷卻最多 {rules.cooldown.max}，收到 {cost.cooldown}")
    for label, present in (
        ("每場次數", cost.uses_per_battle is not None),
        ("自身狀態代價", cost.self_status is not None),
        ("透支", cost.overdraft is not None),
        ("層數需求", cost.stacks is not None),
        ("生命代價", cost.hp_percent is not None),
        ("失手反噬", bool(cost.on_miss)),
    ):
        if present:
            problems.append(f"主動白板用預設費用，不能有{label}")
    return problems


def is_whiteboard(skill: SkillDef, library: ContentLibrary, tier: int | None = None) -> bool:
    """技能符合白板定義（:func:`whiteboard_problems` 為空）。"""
    return not whiteboard_problems(skill, library, tier)


# ---------------------------------------------------------------------------
# 單一效果模式
# ---------------------------------------------------------------------------


def _theme(recipe: WhiteboardRecipe) -> Element:
    if recipe.theme is not None:
        return recipe.theme
    element = recipe.effect.get("element")
    return Element(element) if element is not None else Element.PHYSICAL


def _category_options(recipe: WhiteboardRecipe, weapon_class: str | None) -> tuple[str, ...]:
    """配方在這種武器大類下能用的類別（法器只能用法術技；近戰與遠程兩者皆可）。"""
    if weapon_class == "focus":
        return tuple(c for c in recipe.categories if c == "spell")
    return tuple(recipe.categories)


def _pick_recipe(
    rng: Rng, rules: WhiteboardRules, kind: str, keyword: str | None, weapon_class: str | None
) -> WhiteboardRecipe:
    options = [
        r
        for r in rules.recipes(kind)
        if (keyword is None or r.keyword == keyword) and _category_options(r, weapon_class)
    ]
    if not options:
        raise ComposeError(f"沒有關鍵字 {keyword} 的{kind}白板配方")
    return rng.choice(options)


def _pick_category(
    rng: Rng, library: ContentLibrary, recipe: WhiteboardRecipe, weapon_class: str | None
) -> str:
    options = _category_options(recipe, weapon_class)
    if len(options) == 1:
        return options[0]
    shares = library.composer.spell_share_permille
    spell = rng.chance_permille(shares.get(recipe.skeleton, shares["default"]))
    return "spell" if spell else "weapon"


def _weapon_req(
    rng: Rng, library: ContentLibrary, category: str, weapon_class: str | None
) -> tuple[str, str]:
    """（武器需求，縮放屬性）；給了武器大類時，武器技的需求就是那一類。"""
    req, attr = _weapon_and_attr(rng, category, library.composer)
    if weapon_class in ("melee", "ranged") and category == "weapon":
        return weapon_class, ("str" if weapon_class == "melee" else "dex")
    if weapon_class in ("melee", "ranged") and category == "spell":
        return "any", attr
    return req, attr


def _min_rarity(
    base: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary
) -> str:
    """配方需要的最低稀有度（不增加強度，只是開放原語、狀態、形狀與觸發時機）。"""
    draft = SkillDef.model_validate({**base, "rarity": "epic", "effects": effects})
    ranks = [rarity_rank(n.minimum) for n in rarity_requirements(draft, library)]
    order: tuple[SkillRarity, ...] = ("common", "rare", "epic")
    return order[min(max(ranks, default=0), len(order) - 1)]


def _active_cost(ctx: Ctx, rules: WhiteboardRules) -> dict[str, Any]:
    """主動白板的預設費用：AP 2（在 ``ap_cost``）、冷卻 0～2、法力（法術）或耐力（武器）。"""
    cost_rules = ctx.rules.cost
    rng, ap = ctx.rng, ctx.ap_cost
    if ctx.category == "spell":
        span = cost_rules.spell_mana_per_ap
        mana = (
            rng.randint(span.min, span.max) * ap + (ctx.tier - 1) * cost_rules.spell_mana_per_tier
        )
    else:
        span = cost_rules.weapon_mana_per_ap
        mana = (
            1
            if ctx.chance(cost_rules.weapon_free_permille)
            else rng.randint(span.min, span.max) * ap
        )
    cost: dict[str, Any] = {"mana": mana}
    cooldown = rng.randint(rules.cooldown.min, rules.cooldown.max)
    if _needs_cooldown(ctx):  # 互斥規則「無冷卻的大範圍」（3×3 等）：至少冷卻 1
        cooldown = max(cooldown, 1)
    if cooldown:
        cost["cooldown"] = cooldown
    return cost


def _build_effect(ctx: Ctx, recipe: WhiteboardRecipe) -> None:
    spec = deepcopy(recipe.effect)
    ctx.add_knobbed(spec, ctx.rules.structure.knob_weight_core)
    ctx.core_count = 1


def _base(
    recipe: WhiteboardRecipe, seed: int, tier: int, category: str, ctx: Ctx
) -> dict[str, Any]:
    return {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": "epic",
        "kind": "active",
        "skeleton": recipe.skeleton,
        "category": category,
        "condition": None,
        "provenance": {"origin": "level_up"},
        "shape": {"type": ctx.shape, **ctx.shape_params},
    }


def _shapes(rules: WhiteboardRules, recipe: WhiteboardRecipe, tier: int) -> tuple[str, ...]:
    """配方的形狀裡，角色階級已開放的（``shape_min_tier``；例如 3×3 要 2 階，6.34.9）。"""
    found = tuple(s for s in recipe.shapes if rules.shape_min_tier.get(s, 1) <= tier)
    if not found:
        raise Retry
    return found


def _attempt_active(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    recipe: WhiteboardRecipe,
    weapon_class: str | None,
    *,
    tier: int,
) -> SkillDef:
    rules = _rules(library)
    category = _pick_category(rng, library, recipe, weapon_class)
    req, scaling = _weapon_req(rng, library, category, weapon_class)
    skeleton = library.skeletons[recipe.skeleton]
    ctx = Ctx(library, rng, skeleton, "epic", tier, category, rules.ap_cost, _theme(recipe))
    build_shape(ctx, [str(recipe.effect["type"])], only=_shapes(rules, recipe, tier))
    _build_effect(ctx, recipe)
    base = _base(recipe, seed, tier, category, ctx)
    base |= {"weapon_req": req, "scaling_attr": scaling, "ap_cost": rules.ap_cost}
    base["rarity"] = _min_rarity({**base, "cost": {}}, ctx.effects, library)
    base["cost"] = _active_cost(ctx, rules)
    if not tune(rng, library, base, ctx.effects, ctx.knobs):
        raise Retry
    return _named(_finish(library, seed, base, ctx), recipe)


def _attempt_passive(
    rng: Rng, library: ContentLibrary, seed: int, recipe: WhiteboardRecipe, tier: int
) -> SkillDef:
    rules = _rules(library)
    composer = library.composer
    weights = composer.spell_attr_weights
    scaling = rng.choice(["int"] * weights.int_ + ["wis"] * weights.wis + ["wil"] * weights.wil)
    ctx = Ctx(library, rng, library.skeletons["passive"], "epic", tier, "spell", 1, _theme(recipe))
    ctx.shape = "self"
    _build_effect(ctx, recipe)
    timing = next(
        t for t in library.ruleset.skill_triggers.triggers if t.id == recipe.trigger_event
    )
    trigger = {
        "event": recipe.trigger_event,
        "target": "other" if timing.has_other else "self",
        "max_per_round": 1,
    }
    mana = rng.randint(rules.passive_mana.min, rules.passive_mana.max)
    base: dict[str, Any] = {
        **_base(recipe, seed, tier, "spell", ctx),
        "kind": "passive",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": scaling,
        "shape": {"type": "self"},
        "trigger": trigger,
        "cost": {"mana": mana + (tier - 1) * composer.passive.mana_per_tier},
    }
    base["rarity"] = _min_rarity(base, ctx.effects, library)
    if not tune(rng, library, base, ctx.effects, ctx.knobs):
        raise Retry
    return _named(_finish(library, seed, base, ctx), recipe)


def _attempt_reaction(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    recipe: WhiteboardRecipe,
    weapon_class: str | None,
    *,
    tier: int,
) -> SkillDef:
    rules = _rules(library)
    category = _pick_category(rng, library, recipe, weapon_class)
    req, scaling = _weapon_req(rng, library, category, weapon_class)
    ctx = Ctx(
        library, rng, library.skeletons["reaction"], "epic", tier, category, 1, _theme(recipe)
    )
    build_shape(
        ctx,
        [] if recipe.shapes == ("self",) else [str(recipe.effect["type"])],
        only=_shapes(rules, recipe, tier),
    )
    _build_effect(ctx, recipe)
    mana = rng.randint(rules.reaction_mana.min, rules.reaction_mana.max)
    cooldown = rng.randint(rules.reaction_cooldown.min, rules.reaction_cooldown.max)
    base: dict[str, Any] = {
        **_base(recipe, seed, tier, category, ctx),
        "kind": "reaction",
        "weapon_req": req,
        "scaling_attr": scaling,
        "ap_cost": None,
        "reaction": {"event": recipe.reaction_event},
        "cost": {
            "mana": mana + (tier - 1) * library.composer.reaction.mana_per_tier,
            "cooldown": cooldown,
        },
    }
    base["rarity"] = _min_rarity(base, ctx.effects, library)
    if not tune(rng, library, base, ctx.effects, ctx.knobs):
        raise Retry
    return _named(_finish(library, seed, base, ctx), recipe)


def _named(skill: SkillDef, recipe: WhiteboardRecipe) -> SkillDef:
    """名稱與敘事取配方的（組合器的「元素・骨架」名稱與暫定敘事不適合白板）。"""
    narrative = skill.narrative.model_copy(
        update={"concept": recipe.concept_zh, "cast_flavor": recipe.flavor_zh}
    )
    return skill.model_copy(update={"name_zh": recipe.name_zh, "narrative": narrative})


def compose_whiteboard(
    seed: int,
    *,
    kind: str = "active",
    keyword: str | None = None,
    weapon_class: str | None = None,
    tier: int | None = None,
    library: ContentLibrary | None = None,
    hero_attributes: Mapping[Attribute, int] | None = None,
    avoid_attr: Attribute | None = None,
    held: Mapping[str, str] | None = None,
) -> SkillDef:
    """依種子組出一個白板技能（``id`` 為 ``skill_rand_<seed>``；單一效果模式）。

    ``kind``：``active``／``passive``／``reaction``；``keyword``：指定關鍵字（省略 ＝ 任何有
    配方的）；
    ``tier``：角色目前階級（預算與可用的形狀照這一階，6.34.9；省略 ＝ ``whiteboard.tier``，
    創角用）；
    ``weapon_class``：``melee``／``ranged``／``focus``，給了就只組出這類武器能用的白板；
    ``hero_attributes``／``avoid_attr``：與完整模式相同，縮放屬性跟著主角最高屬性（新方向避開）。
    組不出來（沒有配方、或 ``max_attempts`` 次都做不出合格的白板）拋出 :class:`ComposeError`。
    """
    lib = library if library is not None else default_library()
    if kind not in WHITEBOARD_KINDS:
        raise ComposeError(f"未知的白板種類 {kind!r}（可用：{'、'.join(WHITEBOARD_KINDS)}）")
    rules = _rules(lib)
    tier = rules.tier if tier is None else tier
    rng = Rng(seed).fork("whiteboard")
    for _ in range(rules.max_attempts):
        recipe = _pick_recipe(rng, rules, kind, keyword, weapon_class)
        try:
            if kind == "active":
                skill = _attempt_active(rng, lib, seed, recipe, weapon_class, tier=tier)
            elif kind == "passive":
                skill = _attempt_passive(rng, lib, seed, recipe, tier)
            else:
                skill = _attempt_reaction(rng, lib, seed, recipe, weapon_class, tier=tier)
        except (Retry, ValidationError, BudgetError):
            continue
        if hero_attributes is not None:
            skill = retarget_scaling(skill, hero_attributes, lib, avoid=avoid_attr)
        if (
            not validate_skill(skill, lib)
            and not whiteboard_problems(skill, lib, tier)
            and (weapon_class is None or weapon_problem(skill, weapon_class, held or {}) is None)
        ):
            return skill
    raise ComposeError(
        f"種子 {seed}：{rules.max_attempts} 次重抽都做不出合格的{kind}白板（關鍵字 {keyword}）"
    )
