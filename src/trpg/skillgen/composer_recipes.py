"""隨機組合器補配方（RC-1，``docs/玩法PM交接.md`` 4.1.19；RC-0 第 4 節 1～5）。

照現行規則與預算，只補組合器不會用的寫法：

- **整招召喚**（第 1 點）：1 階只抽 ``basic_summon_units``；2 階起抽 ``recipes.summon_units``
  （06 6.29.5 清單），指定關鍵字時優先抽固有關鍵字相符的；持續照 ``summon`` 原語的旋鈕，變化照白板
  召喚的冷卻與法力。
- **被動**：累積層數（第 2 點，對自己 ``add_stack`` +1，觸發時機照各層數的個性）、利用層數（條件
  ``self_stack_at_least``，層數不扣）、高處與利用型條件（第 3 點，``height_advantage`` 與倒地、
  標記、潮濕只配有「另一方」的觸發，而且效果作用在另一方）、潮濕造水（06 6.34.1 3W-4b）、伴生
  （第 4 點）。
- **反應**（第 5 點）：層數、高處、護主、潮濕。

伴生、護主用 ``summon_beside``；``skill_keywords.yaml`` 沒有推導它的規則時（RC-1 當時沒有），這兩種
配方帶不到任何關鍵字，所以不列入（:func:`beside_keywords` 為空）。RC-1b（玩法 PM 交接 4.1.20
第 1 點）補上「召喚物」與各召喚物固有關鍵字的 ``summon_beside`` 規則（鏡像 ``summon``）後生效。

這裡只決定「用哪個配方」與組出草稿（``Draft``）；強度調整、命名與驗證在
:mod:`trpg.skillgen.random_composer`。要不要用新配方一律用獨立的亂數串流（:func:`pick_recipe`），組法
本身也用獨立串流，所以沒抽到新配方的種子得到與 RC-1 前相同的技能。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from trpg.content.composer_rules import ComposerRules, RecipeSummonUnit
from trpg.content.library import ContentLibrary
from trpg.content.skill_triggers import EVERY_N_HITS, SkillTriggerDef
from trpg.content.skills import (
    CASTER_CONDITIONS,
    ON_KEYWORD_EXPLOITED,
    SkillRarity,
    rarity_rank,
)
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.composer_parts import (
    NON_INTERCEPT_EVENTS,
    Ctx,
    Retry,
    build_cost,
    build_passive_cost,
    build_passive_effects,
    build_reaction_cost,
    build_reaction_effects,
)

__all__ = [
    "SPELL_ELEMENTS",
    "Draft",
    "Recipe",
    "beside_keywords",
    "passive_drafts",
    "passive_recipes",
    "pick_recipe",
    "reaction_drafts",
    "reaction_recipes",
    "summon_choices",
    "summon_drafts",
    "trigger_params",
    "unit_keywords",
    "weapon_and_attr",
    "weighted",
]

SPELL_ELEMENTS: tuple[Element, ...] = tuple(
    e for e in sorted(Element, key=lambda e: e.value) if e is not Element.PHYSICAL
)

_PARAM_PERMILLE = 500
"""``on_status_applied`` 指定狀態、``on_enter_surface`` 指定表面的機率（其餘為任何狀態或表面）。"""
_SURFACES = ("darkness", "fire", "holy", "ice", "oil", "poison", "water")
_HALF = 500
"""高處二選一（``height_advantage`` 或 ``self_on_high_ground``）的機率。"""
_NO_TARGET_EVENTS = frozenset({"on_kill"})
"""另一方已經倒下的觸發：對它的效果無效，不配利用型條件。"""
_WET_REACTION_EVENTS = ("hit_by_attack", "hit_by_melee")
"""潮濕反應「被攻擊後，在攻擊者腳下造水」（06 6.34.1 3W-4b）。"""
_GUARDIAN_EVENT = "hit_by_melee"
_GUARDIAN_RANGE = 2
_GUARDIAN_COSTS: tuple[dict[str, Any], ...] = (
    {"cooldown": 1},
    {"mana": 2, "cooldown": 1},
    {"cooldown": 2},
    {"mana": 4, "cooldown": 2},
)
"""護主的代價（同 TF-1 轉型 ``flash_major._GUARDIAN_COSTS``）。"""
_COMPANION_COSTS: tuple[dict[str, Any], ...] = ({}, {"mana": 2}, {"mana": 4})
"""伴生的代價（同 TF-1 轉型 ``flash_major._to_companion``）。"""
_POWER_STEP = 100
_MIN_POWER = 100
_NORMAL_POWER = 1000
_WATER = "water"
_STACK_MAKE = "stack_make"
_STACK_USE = "stack_use"
_HIGH_GROUND = "high_ground"
_EXPLOIT = "exploit"
_WET = "wet_surface"
_COMPANION = "companion"
_GUARDIAN = "guardian"

type Draft = tuple[dict[str, Any], list[dict[str, Any]]]
"""一個待調整強度的草稿：技能字典（不含效果）與效果串列（旋鈕在 ``Ctx.knobs``）。"""


# ---------------------------------------------------------------------------
# 共用小工具（原本在 random_composer，搬來共用；亂數呼叫不變）
# ---------------------------------------------------------------------------


def weighted[T](rng: Rng, items: tuple[T, ...], weights: tuple[int, ...]) -> T:
    roll = rng.randint(1, sum(weights))
    for item, weight in zip(items, weights, strict=True):
        roll -= weight
        if roll <= 0:
            return item
    return items[-1]  # pragma: no cover


def _spell_attr(rng: Rng, rules: ComposerRules) -> str:
    w = rules.spell_attr_weights
    return weighted(rng, ("int", "wis", "wil"), (w.int_, w.wis, w.wil))


def weapon_and_attr(rng: Rng, category: str, rules: ComposerRules) -> tuple[str, str]:
    if category == "spell":
        req = "any" if rng.chance_permille(rules.spell_any_weapon_permille) else "focus"
        return req, _spell_attr(rng, rules)
    if rng.chance_permille(rules.melee_permille):
        rng.chance_permille(rules.melee_dex_permille)  # 亂數串流不變；武器技一律 str（3H-6）
        return "melee", "str"
    return "ranged", "dex"


def trigger_params(rng: Rng, library: ContentLibrary, event: str) -> dict[str, Any]:
    """新觸發時機（Phase 3C-6b）的參數：``on_cast_tag`` 必填 ``tag``（元素標籤）；
    ``on_status_applied`` 與 ``on_enter_surface`` 以一半的機率指定狀態或表面。其他時機沒有參數
    （不消耗亂數）。"""
    if event == "on_cast_tag":
        return {"tag": rng.choice([e.value for e in SPELL_ELEMENTS])}
    if event == "on_status_applied" and rng.chance_permille(_PARAM_PERMILLE):
        statuses = sorted(
            s.id
            for s in library.ruleset.statuses.statuses
            if not s.beneficial and not s.stance and not s.skill_pool_excluded  # 5F-5c、AP-2
        )
        return {"status": rng.choice(statuses)}
    if event == "on_enter_surface" and rng.chance_permille(_PARAM_PERMILLE):
        return {"surface": rng.choice(_SURFACES)}
    if event == ON_KEYWORD_EXPLOITED and rng.chance_permille(_PARAM_PERMILLE):
        # SK-3b：一半機率縮小成某種狀態或表面（各半）；只由 composer.exploit 的獨立串流走到
        statuses, surfaces = _exploitable(library)
        if rng.chance_permille(_PARAM_PERMILLE):
            return {"surface": rng.choice(surfaces)}
        return {"status": rng.choice(statuses)}
    return {}


def _exploitable(library: ContentLibrary) -> tuple[list[str], list[str]]:
    """關鍵字推導表（``skill_keywords.yaml`` 的 ``uses``）裡會被利用的狀態（條件「目標有狀態」、
    消耗狀態）與表面（條件「目標站在表面上」），各自排序。"""
    statuses: set[str] = set()
    surfaces: set[str] = set()
    for keyword in library.keywords.keywords:
        for rule in keyword.uses:
            if rule.status is not None and (
                rule.condition == "target_has_status" or rule.effect == "consume_status"
            ):
                statuses.add(rule.status)
            if rule.surface is not None and rule.condition == "target_on_surface":
                surfaces.add(rule.surface.value)
    return sorted(statuses), sorted(surfaces)


# ---------------------------------------------------------------------------
# 配方清單與抽選
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Recipe:
    """一個新配方：種類（``stack_make`` 等）、參數（層數 ID、利用型條件的序號）與帶得到的關鍵字。"""

    name: str
    param: str | None
    keywords: tuple[str, ...]


def unit_keywords(library: ContentLibrary, unit: str, effect: str = "summon") -> tuple[str, ...]:
    """召喚 ``unit`` 的效果（``effect``：``summon`` 或 ``summon_beside``）依專屬規則製造的關鍵字
    （``skill_keywords.yaml`` 的 ``makes``；沒寫 ``unit`` 的規則對每種召喚物都成立，灌注不算）。"""
    found: list[str] = []
    for keyword in library.keywords.keywords:
        for rule in keyword.makes:
            if (
                rule.effect == effect
                and rule.grade == "exclusive"
                and rule.infusion is None
                and rule.unit in (None, unit)
            ):
                found.append(keyword.id)
                break
    return tuple(found)


def beside_keywords(library: ContentLibrary, tier: int) -> tuple[str, ...]:
    """伴生、護主（``summon_beside``）帶得到的關鍵字：這一階可抽的召喚物各自推導的聯集（依關鍵字表
    順序）。推導表沒有 ``summon_beside`` 的規則時是空的。"""
    found = {
        k
        for u in _tier_units(library, tier)
        for k in unit_keywords(library, u.unit, "summon_beside")
    }
    return tuple(k for k in library.keywords.ids() if k in found)


def _tier_units(library: ContentLibrary, tier: int) -> tuple[RecipeSummonUnit, ...]:
    """這一階可抽的召喚物：1 階只有基本召喚物（BAL-19c），2 階起是 ``recipes.summon_units``。
    基本召喚物一定在 ``recipes.summon_units``（HC-4b2 起載入時檢查，射程照那一項）。"""
    units = library.composer.recipes.summon_units
    if tier >= library.budget.min_character_tier.primitives.get("summon", 1):
        return units
    basic = library.budget.min_character_tier.basic_summon_units
    known = {u.unit: u for u in units}
    return tuple(known[b] for b in basic)


def summon_choices(
    library: ContentLibrary, tier: int, keyword: str | None, effect: str = "summon"
) -> tuple[RecipeSummonUnit, ...]:
    """可抽的召喚物；指定關鍵字時優先只留固有關鍵字相符的（沒有相符的就全部）。"""
    units = _tier_units(library, tier)
    if keyword is None:
        return units
    matched = tuple(u for u in units if keyword in unit_keywords(library, u.unit, effect))
    return matched or units


def _usable_timings(library: ContentLibrary, rarity: SkillRarity) -> list[SkillTriggerDef]:
    return [
        t
        for t in sorted(library.ruleset.skill_triggers.triggers, key=lambda t: t.id)
        if rarity_rank(t.min_rarity) <= rarity_rank(rarity) and t.random_composer
    ]


def _target_timings(library: ContentLibrary, rarity: SkillRarity) -> list[SkillTriggerDef]:
    """有「另一方」、而且另一方活著的時機（利用型條件與 ``height_advantage`` 只配這些）。"""
    return [
        t for t in _usable_timings(library, rarity) if t.has_other and t.id not in _NO_TARGET_EVENTS
    ]


def _stack_recipes(library: ContentLibrary, *, makes: bool) -> list[Recipe]:
    rules = library.composer.recipes
    table = rules.stack_events if makes else rules.stack_counts
    name = _STACK_MAKE if makes else _STACK_USE
    known = {s.id for s in library.ruleset.stacks.stacks if s.composer}
    return [Recipe(name, stack, (stack,)) for stack in sorted(table) if stack in known]


def _exploit_recipes(library: ContentLibrary) -> list[Recipe]:
    return [
        Recipe(_EXPLOIT, str(i), (e.keyword,))
        for i, e in enumerate(library.composer.recipes.exploit_conditions)
    ]


def passive_recipes(library: ContentLibrary, tier: int) -> tuple[Recipe, ...]:
    """被動的新配方（依固定順序）。"""
    found = [
        *_stack_recipes(library, makes=True),
        *_stack_recipes(library, makes=False),
        Recipe(_HIGH_GROUND, None, ("high_ground",)),
        *_exploit_recipes(library),
        Recipe(_WET, None, ("wet",)),
    ]
    beside = beside_keywords(library, tier)
    if beside:
        found.append(Recipe(_COMPANION, None, beside))
    return tuple(found)


def reaction_recipes(library: ContentLibrary, tier: int) -> tuple[Recipe, ...]:
    """反應技的新配方（依固定順序）。"""
    found = [
        *_stack_recipes(library, makes=True),
        *_stack_recipes(library, makes=False),
        Recipe(_HIGH_GROUND, None, ("high_ground",)),
        Recipe(_WET, None, ("wet",)),
    ]
    beside = beside_keywords(library, tier)
    if beside:
        found.append(Recipe(_GUARDIAN, None, beside))
    return tuple(found)


def pick_recipe(
    seed: int, kind: str, recipes: Sequence[Recipe], permille: int, keyword: str | None
) -> Recipe | None:
    """要不要改用新配方、用哪一個（獨立串流 ``composer.<kind>.recipe``）。指定關鍵字時只考慮帶得到它
    的配方，一個都沒有就不擲（結果與 RC-1 前相同）。"""
    options = [r for r in recipes if keyword is None or keyword in r.keywords]
    if not options or permille <= 0:
        return None
    rng = Rng(seed).fork(f"composer.{kind}.recipe")
    if not rng.chance_permille(permille):
        return None
    return rng.choice(options)


# ---------------------------------------------------------------------------
# 草稿
# ---------------------------------------------------------------------------


def _merge_cost(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    """代價變化（白板 ``vary`` 的寫法：``{cost: {...}}``）併進技能字典的複本。"""
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **value}
        else:
            out[key] = deepcopy(value)
    return out


def _skill_base(
    seed: int, tier: int, rarity: SkillRarity, ctx: Ctx, **fields: Any
) -> dict[str, Any]:
    return {
        "id": f"skill_rand_{seed}",
        "name_zh": "暫定",
        "tier": tier,
        "rarity": rarity,
        "skeleton": ctx.skeleton.id,
        "shape": {"type": ctx.shape, **ctx.shape_params},
        "condition": None,
        "provenance": {"origin": "level_up"},
        **fields,
    }


def summon_drafts(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    *,
    tier: int,
    rarity: SkillRarity,
    keyword: str | None,
) -> tuple[Ctx, list[Draft]]:
    """整招召喚（4.1.19 第 1 點）：AP 1、單格、照白板召喚；代價先照組合器抽，再依序試冷卻與法力的
    變化。"""
    rules = library.composer
    units = summon_choices(library, tier, keyword)
    if not units:
        raise Retry
    pick = rng.choice(units)
    weapon_req, scaling = weapon_and_attr(rng, "spell", rules)
    ctx = Ctx(library, rng, library.skeletons["summon"], rarity, tier, "spell", 1, pick.theme)
    ctx.shape, ctx.shape_params = "ground_tile", {"range": pick.range}
    ctx.add_knobbed({"type": "summon", "unit": pick.unit}, rules.structure.knob_weight_core)
    ctx.core_count = 1
    base = _skill_base(
        seed, tier, rarity, ctx,
        kind="active", category="spell", weapon_req=weapon_req, scaling_attr=scaling,
        ap_cost=1, cost=build_cost(ctx),
    )  # fmt: skip
    patches = rng.shuffled(list(rules.recipes.summon_costs)) or [{}]
    return ctx, [(_merge_cost(base, p), deepcopy(ctx.effects)) for p in patches]


def _power_tries(start: int, costs: Sequence[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """縮小版召喚物依序試的（強度‰, 代價）：同 TF-1 轉型（``flash_major._power_tries``）。"""
    powers = {start, *range(_MIN_POWER, _NORMAL_POWER + 1, _POWER_STEP)}
    ordered = sorted(powers, key=lambda p: (abs(p - start), -p))
    return [(p, dict(c)) for p in ordered for c in costs]


def _beside(unit: str, duration: int, power: int, *, strike: bool = False) -> dict[str, Any]:
    effect: dict[str, Any] = {"type": "summon_beside", "unit": unit, "duration": duration}
    if power < _NORMAL_POWER:
        effect["power_permille"] = power
    if strike:
        effect["strike_other"] = True
    return effect


def _beside_unit(rng: Rng, library: ContentLibrary, tier: int, keyword: str | None) -> str:
    units = summon_choices(library, tier, keyword, "summon_beside")
    if not units:
        raise Retry
    return rng.choice(units).unit


def _passive_ctx(
    rng: Rng, library: ContentLibrary, tier: int, rarity: SkillRarity
) -> tuple[Ctx, str]:
    scaling = _spell_attr(rng, library.composer)
    ctx = Ctx(
        library, rng, library.skeletons["passive"], rarity, tier, "spell", 1,
        rng.choice(SPELL_ELEMENTS),
    )  # fmt: skip
    ctx.shape = "self"
    return ctx, scaling


def _pick_target(ctx: Ctx, timing: SkillTriggerDef) -> str:
    """同 RC-1 前的被動：有另一方的時機依機率作用在另一方，其餘作用在持有者。"""
    if timing.has_other and ctx.chance(ctx.rules.passive.other_permille):
        return "other"
    return "self"


@dataclass(slots=True)
class _Passive:
    """被動配方決定好的觸發與條件。"""

    timing: SkillTriggerDef
    target: str
    condition: dict[str, Any] | None
    second: bool = True


def _condition_dict(spec: Any) -> dict[str, Any]:
    return dict(spec.model_dump(mode="json", exclude_none=True))


def _is_target_condition(condition: Mapping[str, Any] | None) -> bool:
    return condition is not None and condition["type"] not in CASTER_CONDITIONS


def _passive_plan(ctx: Ctx, recipe: Recipe) -> _Passive:
    """被動配方的觸發時機、對象與條件。目標型條件（``height_advantage``、倒地、標記、潮濕）只配有
    另一方的時機，而且效果作用在另一方：引擎判斷被動的技能條件時，對象是另一方（作用在持有者時是
    持有者自己）。"""
    library, rng = ctx.library, ctx.rng
    rules = library.composer.recipes
    timings = {t.id: t for t in _usable_timings(library, ctx.rarity)}
    if recipe.name == _STACK_MAKE:
        choice = rng.choice(rules.stack_events[str(recipe.param)])
        timing = timings.get(choice.event)
        if timing is None:
            raise Retry
        condition = None if choice.condition is None else _condition_dict(choice.condition)
        target = "other" if _is_target_condition(condition) else _pick_target(ctx, timing)
        return _Passive(timing, target, condition, second=False)
    if recipe.name == _STACK_USE:
        timing = rng.choice(list(timings.values()))
        count = rules.stack_counts[str(recipe.param)]
        condition = {"type": "self_stack_at_least", "stack": recipe.param, "count": count}
        return _Passive(timing, _pick_target(ctx, timing), condition)
    if recipe.name == _HIGH_GROUND:
        timing = rng.choice(list(timings.values()))
        if timing.has_other and timing.id not in _NO_TARGET_EVENTS and rng.chance_permille(_HALF):
            return _Passive(timing, "other", {"type": "height_advantage"})
        return _Passive(timing, _pick_target(ctx, timing), {"type": "self_on_high_ground"})
    if recipe.name == _EXPLOIT:
        targets = _target_timings(library, ctx.rarity)
        if not targets:
            raise Retry
        exploit = rules.exploit_conditions[int(str(recipe.param))]
        return _Passive(rng.choice(targets), "other", _condition_dict(exploit.condition))
    if recipe.name == _WET:  # 被攻擊後在自己腳下造水（06 6.34.1 3W-4b）
        timing = timings.get("on_damaged")
        if timing is None:
            raise Retry
        return _Passive(timing, "self", None, second=False)
    raise Retry


def passive_drafts(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    *,
    tier: int,
    rarity: SkillRarity,
    recipe: Recipe,
    keyword: str | None,
) -> tuple[Ctx, list[Draft]]:
    """被動新配方的一次嘗試。"""
    ctx, scaling = _passive_ctx(rng, library, tier, rarity)
    if recipe.name == _COMPANION:
        return ctx, _companion_drafts(ctx, seed, scaling, keyword)
    plan = _passive_plan(ctx, recipe)
    n = rng.choice((2, 3)) if plan.timing.id == EVERY_N_HITS else None
    build_passive_effects(ctx, plan.target, second=plan.second)
    if recipe.name == _STACK_MAKE:
        ctx.add({"type": "add_stack", "stack": recipe.param, "amount": 1, "affects": "self"}, ())
    elif recipe.name == _WET:
        ctx.add_knobbed({"type": "create_surface", "surface": _WATER, "affects": "self"})
    trigger: dict[str, Any] = {"event": plan.timing.id, "target": plan.target, "max_per_round": 1}
    if n is not None:
        trigger["n"] = n
    trigger.update(trigger_params(rng, library, plan.timing.id))
    base = _skill_base(
        seed, tier, rarity, ctx,
        kind="passive", category="spell", weapon_req="any", ap_cost=None, scaling_attr=scaling,
        trigger=trigger, cost=build_passive_cost(ctx),
    )  # fmt: skip
    base["condition"] = plan.condition
    return ctx, [(base, ctx.effects)]


def _companion_drafts(ctx: Ctx, seed: int, scaling: str, keyword: str | None) -> list[Draft]:
    """伴生（4.1.19 第 4 點，#159）：戰鬥開始時在身邊召出縮小版召喚物（每場一次）。"""
    library = ctx.library
    unit = _beside_unit(ctx.rng, library, ctx.tier, keyword)
    rules = library.budget.flash_transform
    trigger = {"event": "on_battle_start", "target": "self", "max_per_round": 1}
    drafts: list[Draft] = []
    for power, cost in _power_tries(rules.companion_power_permille, _COMPANION_COSTS):
        base = _skill_base(
            seed, ctx.tier, ctx.rarity, ctx,
            kind="passive", category="spell", weapon_req="any", ap_cost=None,
            scaling_attr=scaling, trigger=dict(trigger),
            cost={"mana": 0, **library.ruleset.core.scaled_cost(cost)},
        )  # fmt: skip
        drafts.append((base, [_beside(unit, rules.companion_duration, power)]))
    return drafts


def reaction_drafts(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    *,
    tier: int,
    rarity: SkillRarity,
    category: str,
    recipe: Recipe,
    keyword: str | None,
) -> tuple[Ctx, list[Draft]]:
    """反應技新配方的一次嘗試（4.1.19 第 5 點）。"""
    rules = library.composer
    if recipe.name == _GUARDIAN:
        return _guardian_drafts(rng, library, seed, tier=tier, rarity=rarity, keyword=keyword)
    event = rng.choice(_WET_REACTION_EVENTS if recipe.name == _WET else NON_INTERCEPT_EVENTS)
    weapon_req, scaling = weapon_and_attr(rng, category, rules)
    if category == "spell":
        theme = rng.choice(SPELL_ELEMENTS)
    else:
        infuse = rng.chance_permille(rules.infuse_permille)
        theme = rng.choice(SPELL_ELEMENTS) if infuse else Element.PHYSICAL
    ctx = Ctx(library, rng, library.skeletons["reaction"], rarity, tier, category, 1, theme)
    condition: dict[str, Any] | None = None
    if recipe.name == _STACK_MAKE:
        build_reaction_effects(ctx, event, second=False)
        ctx.add({"type": "add_stack", "stack": recipe.param, "amount": 1, "affects": "self"}, ())
    elif recipe.name == _STACK_USE:
        build_reaction_effects(ctx, event)
        count = rules.recipes.stack_counts[str(recipe.param)]
        condition = {"type": "self_stack_at_least", "stack": recipe.param, "count": count}
    elif recipe.name == _HIGH_GROUND:
        if rng.chance_permille(_HALF):  # 攻擊者比你低時才觸發：比的是形狀 single 的觸發者
            build_reaction_effects(ctx, event, branch="other")
            condition = {"type": "height_advantage"}
        else:
            build_reaction_effects(ctx, event)
            condition = {"type": "self_on_high_ground"}
    elif recipe.name == _WET:  # 被攻擊後，在攻擊者腳下造水（06 6.34.1 3W-4b）
        build_reaction_effects(ctx, event, second=False, branch="other")
        ctx.add_knobbed({"type": "create_surface", "surface": _WATER})
    else:
        raise Retry
    base = _skill_base(
        seed, tier, rarity, ctx,
        kind="reaction", category=category, weapon_req=weapon_req, scaling_attr=scaling,
        reaction={"event": event}, ap_cost=None, cost=build_reaction_cost(ctx),
    )  # fmt: skip
    base["condition"] = condition
    return ctx, [(base, ctx.effects)]


def _guardian_drafts(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    *,
    tier: int,
    rarity: SkillRarity,
    keyword: str | None,
) -> tuple[Ctx, list[Draft]]:
    """護主（4.1.19 第 5 點，#159）：被近戰攻擊時在身邊召出縮小版召喚物，立刻反咬攻擊者一次。"""
    unit = _beside_unit(rng, library, tier, keyword)
    scaling = _spell_attr(rng, library.composer)
    ctx = Ctx(
        library, rng, library.skeletons["reaction"], rarity, tier, "spell", 1, Element.PHYSICAL
    )
    ctx.shape, ctx.shape_params = "single", {"range": _GUARDIAN_RANGE}
    rules = library.budget.flash_transform
    drafts: list[Draft] = []
    for power, cost in _power_tries(rules.guardian_power_permille, _GUARDIAN_COSTS):
        base = _skill_base(
            seed, tier, rarity, ctx,
            kind="reaction", category="spell", weapon_req="any", scaling_attr=scaling,
            reaction={"event": _GUARDIAN_EVENT}, ap_cost=None,
            cost=library.ruleset.core.scaled_cost(cost),
        )  # fmt: skip
        drafts.append((base, [_beside(unit, rules.guardian_duration, power, strike=True)]))
    return ctx, drafts
