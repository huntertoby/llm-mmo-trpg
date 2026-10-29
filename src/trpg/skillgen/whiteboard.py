"""白板技能：組合器的「單一效果」模式（Phase 3W-4／3W-4b，``docs/design/06-技能.md`` 6.34.1、
6.34.9）。白板定義的驗證在 :mod:`trpg.skillgen.whiteboard_check`。

**白板** ＝ 角色目前階級的預算、一個核心效果、一個關鍵字、形狀簡單（單體或小範圍）、沒有附帶效果；
主動技用預設費用（AP 2、冷卻 0～2）；預算照同階規則（比例 70～100%）。分主動、被動、反應三種（升級與
任務三選一的種類比例 70／20／10，``content/skill_composer.yaml`` 的 ``whiteboard.kind_permille``）。

**種類依角色階級開放**（6.34.9；配方的 ``min_tier``）：1 階是數值型、簡單形狀、簡單觸發的被動與
反應；2 階起有召喚、陷阱、姿態、自身位移或互換；3 階起有修正型被動與雙屬性縮放。姿態佔主動欄、
修正型被動佔被動欄，所以出題的種類比例（主動 70／被動 20／反應 10）不變。沒有關鍵字的基礎白板
（通用池，#55）配方用 ``whiteboard.generic_keyword``。

**單一效果模式**（:func:`compose_whiteboard`）：從 ``whiteboard`` 的配方挑一個，再用組合器既有的零件
填形狀、旋鈕（骰子、倍率、持續……）與費用，強度調整到預算區間內，最後過 ``validate_skill`` 與
:func:`whiteboard_problems`。基本配方（``species: basic``）走 :func:`_attempt_active`、
:func:`_attempt_passive`、:func:`_attempt_reaction`；新種類的配方把技能欄位直接寫在配方裡
（``skill``），走 :func:`_attempt_template`。完整模式（:func:`~trpg.skillgen.random_composer.
compose_random_skill`）不受影響，留給之後的完整技能三選一。

**確定性**：亂數只來自 ``Rng(seed).fork("whiteboard")``；相同的種子與參數必得相同的白板。
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal

from pydantic import ValidationError

from trpg.content.composer_rules import WhiteboardRecipe, WhiteboardRules
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, SkillRarity, rarity_rank, weapon_problem
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_parts import Ctx, Retry, _needs_cooldown, build_shape
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.random_composer import (
    ComposeError,
    _finish,
    _weapon_and_attr,
    default_library,
)
from trpg.skillgen.scaling import retarget_scaling
from trpg.skillgen.validate import rarity_requirements, validate_skill
from trpg.skillgen.whiteboard_check import (
    is_whiteboard,
    whiteboard_keywords_of,
    whiteboard_problems,
)

__all__ = [
    "WHITEBOARD_KINDS",
    "WhiteboardKind",
    "compose_whiteboard",
    "is_whiteboard",
    "whiteboard_keywords",
    "whiteboard_problems",
]

type WhiteboardKind = Literal["active", "passive", "reaction"]
"""白板的種類（出題比例的分類）：``active``（主動欄：含召喚、陷阱、姿態、位移）、``passive``
（被動欄：含修正型被動）、``reaction``（反應）。"""
WHITEBOARD_KINDS: tuple[WhiteboardKind, ...] = ("active", "passive", "reaction")


def _rules(library: ContentLibrary) -> WhiteboardRules:
    return library.composer.whiteboard


def whiteboard_keywords(
    library: ContentLibrary, kind: str = "active", tier: int | None = None
) -> frozenset[str]:
    """``kind`` 的白板配方涵蓋的關鍵字（沒有配方的關鍵字由呼叫端退回別的來源）；給了 ``tier``
    就只算該角色階級開放的配方。沒有關鍵字的基礎白板用 ``whiteboard.generic_keyword``。"""
    return frozenset(r.keyword for r in _rules(library).recipes(kind, tier))


# ---------------------------------------------------------------------------
# 單一效果模式
# ---------------------------------------------------------------------------


def _theme(recipe: WhiteboardRecipe) -> Element:
    if recipe.theme is not None:
        return recipe.theme
    element = recipe.effect.get("element")
    return Element(element) if element is not None else Element.PHYSICAL


def _category_options(recipe: WhiteboardRecipe, weapon_class: str | None) -> tuple[str, ...]:
    """配方在這種武器大類下能用的類別（法器只能用法術技；近戰與遠程兩者皆可；配方指定近戰或遠程的
    武器需求時，只給同類的武器）。"""
    required = recipe.skill.get("weapon_req")
    if required in ("melee", "ranged") and weapon_class is not None and required != weapon_class:
        return ()
    if weapon_class == "focus":
        return tuple(c for c in recipe.categories if c == "spell")
    return tuple(recipe.categories)


def _pick_recipe(
    rng: Rng,
    rules: WhiteboardRules,
    kind: str,
    *,
    keyword: str | None,
    weapon_class: str | None,
    tier: int,
    recipe_id: str | None = None,
) -> WhiteboardRecipe:
    options = [
        r
        for r in rules.recipes(kind, tier)
        if (keyword is None or r.keyword == keyword)
        and (recipe_id is None or r.id == recipe_id)
        and _category_options(r, weapon_class)
    ]
    if not options:
        raise ComposeError(f"沒有關鍵字 {keyword} 的{kind}白板配方（{tier} 階）")
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
    if base.get("secondary_scaling_attr") is not None:  # 雙屬性縮放（驗證器另查）
        ranks.append(rarity_rank(library.ruleset.core.dual_scaling_min_rarity))
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
    """核心效果（可帶條件：利用者例外）與配方的第二個效果（製造者例外、位移的小補強）。"""
    if not recipe.effect:  # 修正型被動：沒有效果，規則在 skill.modifiers
        return
    spec = deepcopy(recipe.effect)
    if recipe.condition is not None:
        spec["condition"] = deepcopy(recipe.condition)
    ctx.add_knobbed(spec, ctx.rules.structure.knob_weight_core)
    ctx.core_count = len(ctx.effects)
    if recipe.rider is not None:
        ctx.add_knobbed(deepcopy(recipe.rider), ctx.rules.structure.knob_weight_other)


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
    ap = int(recipe.skill.get("ap_cost", rules.ap_cost))
    ctx = Ctx(library, rng, skeleton, "epic", tier, category, ap, _theme(recipe))
    build_shape(ctx, [str(recipe.effect["type"])], only=_shapes(rules, recipe, tier))
    _build_effect(ctx, recipe)
    base = _base(recipe, seed, tier, category, ctx)
    base |= {"weapon_req": req, "scaling_attr": scaling, "ap_cost": ap}
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
    shape = deepcopy(recipe.skill.get("shape", {"type": "self"}))  # 例：回合開始標記 3 格內的敵人
    ctx.shape = str(shape["type"])
    _build_effect(ctx, recipe)
    timing = next(
        t for t in library.ruleset.skill_triggers.triggers if t.id == recipe.trigger_event
    )
    trigger = {
        "event": recipe.trigger_event,
        "target": "other" if timing.has_other else "self",
        "max_per_round": 1,
    }
    trigger |= recipe.skill.get("trigger", {})  # 例：擊倒時得護盾，作用在自己而不是倒下的敵人
    mana = rng.randint(rules.passive_mana.min, rules.passive_mana.max)
    base: dict[str, Any] = {
        **_base(recipe, seed, tier, "spell", ctx),
        "kind": "passive",
        "weapon_req": "any",
        "ap_cost": None,
        "scaling_attr": scaling,
        "shape": shape,
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


def _merge(target: dict[str, Any], patch: Mapping[str, Any]) -> None:
    """``patch`` 深度合併進 ``target``（字典合併；長度相同的字典串列逐項合併；其餘整個取代）。"""
    for key, value in patch.items():
        current = target.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            _merge(current, value)
        elif (
            isinstance(value, list)
            and isinstance(current, list)
            and len(value) == len(current)
            and all(isinstance(v, dict) for v in (*value, *current))
        ):
            for old, new in zip(current, value, strict=True):
                _merge(old, new)
        else:
            target[key] = deepcopy(value)


def _apply_patch(
    base: dict[str, Any], effects: list[dict[str, Any]], patch: Mapping[str, Any]
) -> None:
    """配方 ``vary`` 的一個選項：``effect0``／``effect1`` 合併進對應的效果，其餘合併進技能字典。"""
    for key, value in patch.items():
        if key.startswith("effect"):
            _merge(effects[int(key.removeprefix("effect"))], value)
        else:
            _merge(base, {key: value})


def _template_cost(ctx: Ctx, rules: WhiteboardRules, kind: str) -> dict[str, Any]:
    if kind == "active":
        return _active_cost(ctx, rules)
    if kind == "stance":
        span = ctx.rules.stance.mana
        return {"mana": ctx.rng.randint(span.min, span.max) + (ctx.tier - 1)}
    return {}


def _attempt_template(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    recipe: WhiteboardRecipe,
    weapon_class: str | None,
    *,
    tier: int,
) -> SkillDef:
    """新種類的白板（召喚、陷阱、姿態、位移、修正型被動、雙屬性縮放；3W-4b）：技能欄位由配方的
    ``skill`` 給，旋鈕仍用組合器的強度調整；``vary`` 的選項（例如召喚的冷卻）隨機挑一個試。"""
    rules = _rules(library)
    spec = deepcopy(recipe.skill)
    kind = str(spec.pop("kind", "active"))
    category = str(spec.pop("category", None) or _pick_category(rng, library, recipe, weapon_class))
    req, scaling = _weapon_req(rng, library, category, weapon_class)
    req = str(spec.pop("weapon_req", req))
    shape = spec.pop("shape", {"type": "single"})
    ap = spec.pop("ap_cost", rules.ap_cost) if kind == "active" else None
    ctx = Ctx(
        library, rng, library.skeletons[recipe.skeleton], "epic", tier, category, ap or 1,
        _theme(recipe),
    )  # fmt: skip
    ctx.shape = str(shape["type"])
    if "trap" in spec:
        ctx.add({"type": "place_trap"}, ())
    _build_effect(ctx, recipe)
    base: dict[str, Any] = {
        **_base(recipe, seed, tier, category, ctx),
        "kind": kind,
        "weapon_req": req,
        "scaling_attr": scaling,
        "ap_cost": ap,
        "shape": deepcopy(shape),
        "cost": _template_cost(ctx, rules, kind),
    }
    cost_patch = spec.pop("cost", {})
    _merge(base["cost"], cost_patch)
    _merge(base, spec)
    base["rarity"] = _min_rarity({**base, "cost": {}}, ctx.effects, library)
    for patch in rng.shuffled(list(recipe.vary)) if recipe.vary else [{}]:
        trial, effects = deepcopy(base), deepcopy(ctx.effects)
        _apply_patch(trial, effects, patch)
        if tune(rng, library, trial, effects, ctx.knobs):
            ctx.effects = effects
            return _named(_finish(library, seed, trial, ctx), recipe)
    raise Retry


def _named(skill: SkillDef, recipe: WhiteboardRecipe) -> SkillDef:
    """名稱與敘事取配方的（組合器的「元素・骨架」名稱與暫定敘事不適合白板）。"""
    narrative = skill.narrative.model_copy(
        update={"concept": recipe.concept_zh, "cast_flavor": recipe.flavor_zh}
    )
    return skill.model_copy(update={"name_zh": recipe.name_zh, "narrative": narrative})


def _attempt(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    kind: str,
    recipe: WhiteboardRecipe,
    *,
    weapon_class: str | None,
    tier: int,
) -> SkillDef:
    if recipe.species != "basic":
        return _attempt_template(rng, library, seed, recipe, weapon_class, tier=tier)
    if kind == "active":
        return _attempt_active(rng, library, seed, recipe, weapon_class, tier=tier)
    if kind == "passive":
        return _attempt_passive(rng, library, seed, recipe, tier)
    return _attempt_reaction(rng, library, seed, recipe, weapon_class, tier=tier)


def _keyword_matches(
    skill: SkillDef, recipe: WhiteboardRecipe, keyword: str | None, library: ContentLibrary
) -> bool:
    """指定關鍵字時，召喚白板推導出來的關鍵字必須就是它（3W-2b，3664e63f）：近戰的骷髏戰士會
    推導成「倒地」，所以選「召喚物」時優先給遠程的基本召喚物（推導出來沒有別的關鍵字）。"""
    if keyword is None or recipe.species != "summon":
        return True
    return whiteboard_keywords_of(skill, library) == (keyword,)


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
    recipe_id: str | None = None,
) -> SkillDef:
    """依種子組出一個白板技能（``id`` 為 ``skill_rand_<seed>``；單一效果模式）。

    ``kind``：``active``／``passive``／``reaction``（出題的分類；姿態、召喚、陷阱、位移屬
    ``active``，修正型被動屬 ``passive``）；
    ``keyword``：指定關鍵字（省略 ＝ 任何有配方的；沒有關鍵字的基礎白板用
    ``whiteboard.generic_keyword``）；
    ``tier``：角色目前階級（預算、可用的形狀與種類照這一階，6.34.9；省略 ＝ ``whiteboard.tier``，
    創角用）；
    ``weapon_class``：``melee``／``ranged``／``focus``，給了就只組出這類武器能用的白板；
    ``hero_attributes``／``avoid_attr``：與完整模式相同，縮放屬性跟著主角最高屬性（新方向避開）；
    雙屬性縮放白板的屬性由配方決定，不跟著主角；``recipe_id``：只用這個配方（測試與覆蓋表用）。
    組不出來（沒有配方、或 ``max_attempts`` 次都做不出合格的白板）拋出 :class:`ComposeError`。
    """
    lib = library if library is not None else default_library()
    if kind not in WHITEBOARD_KINDS:
        raise ComposeError(f"未知的白板種類 {kind!r}（可用：{'、'.join(WHITEBOARD_KINDS)}）")
    rules = _rules(lib)
    tier = rules.tier if tier is None else tier
    rng = Rng(seed).fork("whiteboard")
    for _ in range(rules.max_attempts):
        recipe = _pick_recipe(
            rng, rules, kind, keyword=keyword, weapon_class=weapon_class, tier=tier,
            recipe_id=recipe_id,
        )  # fmt: skip
        try:
            skill = _attempt(rng, lib, seed, kind, recipe, weapon_class=weapon_class, tier=tier)
        except (Retry, ValidationError, BudgetError):
            continue
        if hero_attributes is not None and recipe.species != "dual":
            skill = retarget_scaling(skill, hero_attributes, lib, avoid=avoid_attr)
        if not _keyword_matches(skill, recipe, keyword, lib):
            continue
        if (
            not validate_skill(skill, lib)
            and not whiteboard_problems(skill, lib, tier)
            and (weapon_class is None or weapon_problem(skill, weapon_class, held or {}) is None)
        ):
            return skill
    raise ComposeError(
        f"種子 {seed}：{rules.max_attempts} 次重抽都做不出合格的{kind}白板（關鍵字 {keyword}）"
    )
