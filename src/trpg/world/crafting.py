"""鐵匠與附魔台（Phase 5D-3；``docs/phases/Phase5計畫.md`` 30.4）。

- **打造**（鐵匠，08 8.13、8.20、8.26.2）：配方＝部位＋物品等級＋稀有度＋1 條 build 詞條＋材料組合
  （1 種通用料決定物品等級上限，0～3 種特色材料決定其餘詞條的傾向，M2）。配方指紋＝正規化 JSON 的
  SHA-256；同一份配方一定打出同一件裝備（亂數只由指紋衍生，不耗角色亂數）。配方碼＝指紋前 10 碼，
  世界記下每份配方的首位發現者（M6）；部位與特色材料符合隱藏配方時打出獨特裝備（M7）。
- **強化**（鐵匠，8.14）：+1～+3，每級基礎加成 +``step_permille``。
- **分解**（鐵匠，8.14）：背包裡的裝備 → 精華。
- **重骰**、**指定**（附魔台，8.20、8.26.1）：換掉一條詞條；重骰的亂數由「指紋＋位置＋n」決定，
  指定完全沒有隨機；越改越貴。
- **配方＝基礎配方＋重骰序列**（5D-3b，8.20／#33）：打造品每重骰或指定一次，就得到一份帶序列的
  配方（配方碼＝SHA-256(基礎指紋＋序列) 前 10 碼），世界照樣記首位發現者；用這個碼打造時先打基礎
  配方，再照序列重骰與指定（亂數同原裝備），費用照付，結果和原裝備相同。

純函式：不讀時間（``now`` 由呼叫者傳入）、不呼叫 LLM。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final

from trpg.content.equipment import AffixDef, ItemDef
from trpg.content.item_gen import (
    affix_choices,
    generate_item_retrying,
    pick_affix,
    replace_affix,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_crafting import CraftingRules, HiddenRecipe, StationDef
from trpg.shared.rng import Rng
from trpg.world.actions import WorldEvent
from trpg.world.crafting_actions import (
    AffixChangedEvent,
    CraftAction,
    EnhanceAction,
    GearCraftedEvent,
    GearEnhancedEvent,
    GearSalvagedEvent,
    ImbueAction,
    RerollAction,
    SalvageAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.inventory import add_items, check_room, remove_gear, remove_items
from trpg.world.state import (
    CharacterState,
    CraftRecipe,
    GearMod,
    RecipeRecord,
    RecipeStep,
    WorldState,
)

__all__ = [
    "CRAFTING_ACTIONS",
    "CRAFTING_HANDLERS",
    "RESONANCE_TAG",
    "CraftPlan",
    "apply_crafting",
    "build_choices",
    "crafting_rules",
    "enhance_cost",
    "find_gear",
    "fingerprint",
    "grade_item",
    "mod_of",
    "plan_craft",
    "recipe_code",
    "station_problem",
    "stations_here",
    "variant_print",
]

CRAFTING_ACTIONS = (CraftAction, EnhanceAction, RerollAction, ImbueAction, SalvageAction)
RESONANCE_TAG = "resonance_"
"""物品標籤的前綴：``resonance_<關鍵字>``＝這件裝備帶的共鳴關鍵字（M3）。"""


def crafting_rules(library: ContentLibrary) -> CraftingRules | None:
    return library.world_crafting


def _rules(library: ContentLibrary) -> CraftingRules:
    rules = crafting_rules(library)
    if rules is None:
        raise WorldActionError("鐵匠與附魔台還沒有開放")
    return rules


# ---------------------------------------------------------------------------
# 設施
# ---------------------------------------------------------------------------


def stations_here(library: ContentLibrary, char: CharacterState) -> tuple[StationDef, ...]:
    """角色所在地點的設施（依資料順序）。"""
    rules = crafting_rules(library)
    if rules is None:
        return ()
    return tuple(
        s for s in rules.stations if s.region == char.region and s.location == char.location
    )


def station_problem(
    library: ContentLibrary, char: CharacterState, station: StationDef
) -> str | None:
    """不能用這個設施的原因；可以時為 ``None``。"""
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if station.region != char.region or station.location != char.location:
        return f"{station.name_zh}不在這裡"
    return None


def _station(
    library: ContentLibrary, char: CharacterState, station_id: str, kind: str
) -> StationDef:
    station = _rules(library).station(station_id)
    if station is None:
        raise WorldActionError(f"沒有這個設施：{station_id}")
    if station.kind != kind:
        what = "鐵匠" if kind == "smithy" else "附魔台"
        raise WorldActionError(f"{station.name_zh}不是{what}")
    problem = station_problem(library, char, station)
    if problem is not None:
        raise WorldActionError(problem)
    return station


# ---------------------------------------------------------------------------
# 配方
# ---------------------------------------------------------------------------


def fingerprint(recipe: CraftRecipe) -> str:
    """配方指紋：正規化 JSON（鍵排序、無空白）的 SHA-256（8.20；不用內建 ``hash()``）。"""
    data = json.dumps(
        recipe.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def recipe_code(print_: str) -> str:
    """配方碼＝指紋前 10 碼（小寫存、顯示大寫）。"""
    return print_[:10]


def variant_print(base_print: str, steps: tuple[RecipeStep, ...]) -> str:
    """帶重骰序列的配方指紋（5D-3b）：``{"base": 基礎指紋, "steps": [...]}`` 正規化 JSON 的
    SHA-256；
    沒有序列時就是基礎指紋（舊配方碼不變）。"""
    if not steps:
        return base_print
    data = json.dumps(
        {"base": base_print, "steps": [s.model_dump(mode="json") for s in steps]},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _item_print(item: ItemDef) -> str:
    """掉落品的指紋（第一次被改動時）：物品 JSON 的 SHA-256（掉落品沒有配方碼，8.20）。"""
    data = json.dumps(item.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _rng(print_: str, *parts: object) -> Rng:
    label = ":".join([print_, *(str(p) for p in parts)])
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    return Rng(int.from_bytes(digest[:8], "big"))


def build_choices(
    library: ContentLibrary, slot_type: str, weapon_class: str | None = None
) -> list[AffixDef]:
    """這個部位可以指定的 build 詞條（依 id）：``item_gen.yaml`` 的 ``required_picks`` 候選、能掛在
    這個部位、不限定武器種類、不是傳說限定或獨特詞條（代決 5D3-3）。"""
    gen = library.item_gen
    if gen is None:
        return []
    pick = gen.required_picks.get(slot_type)  # type: ignore[call-overload]
    if pick is None:
        return []
    return [
        a
        for _, a in sorted(library.affixes.items())
        if pick.allows(a)
        and slot_type in a.slots
        and not a.legendary_only
        and a.id not in gen.unique_affixes
        and a.id not in gen.held_back_affixes  # LW-1：暫不進產生器
        and not a.weapons
        and (a.weapon_class is None or a.weapon_class == weapon_class or slot_type != "weapon")
    ]


def grade_item(library: ContentLibrary, item_level: int) -> str | None:
    """物品等級對應的通用料（強化用；≤3 粗、≤7 精、其餘上，依 ``grade_cap``）。"""
    rules = _rules(library)
    caps = sorted(rules.craft.grade_cap.items(), key=lambda kv: kv[1])
    grade = next((g for g, cap in caps if item_level <= cap), caps[-1][0])
    return next(
        (i.id for _, i in sorted(library.world_economy.items.items()) if i.grade == grade), None
    )


def _hero_weapon_class(library: ContentLibrary, char: CharacterState) -> str | None:
    weapon = library.weapons.get(char.hero.weapon)
    return None if weapon is None else weapon.weapon_class


def _level_cap(library: ContentLibrary, char: CharacterState, grade: str) -> int:
    rules = _rules(library)
    found = library.world_economy.items.get(grade)
    if found is None or found.kind != "material" or found.grade is None:
        raise WorldActionError(f"{grade} 不是通用料")
    cap = min(char.level, rules.craft.grade_cap[found.grade])
    loot = library.world_loot
    return cap if loot is None else min(cap, loot.gear.max_item_level)


def _recipe_from_fields(
    library: ContentLibrary, char: CharacterState, action: CraftAction
) -> tuple[CraftRecipe, HiddenRecipe | None]:
    rules = _rules(library)
    assert action.slot_type is not None and action.rarity is not None and action.grade is not None
    if action.rarity not in rules.craft.rarities:
        raise WorldActionError(f"不能打造這個稀有度：{action.rarity}")
    materials = tuple(sorted(set(action.materials)))
    if len(materials) != len(action.materials):
        raise WorldActionError("特色材料不能重複")
    if len(materials) > rules.craft.flavor_max:
        raise WorldActionError(f"特色材料最多 {rules.craft.flavor_max} 種")
    unknown = [m for m in materials if m not in rules.materials]
    if unknown:
        raise WorldActionError(f"不是能打造的特色材料：{'、'.join(unknown)}")
    cap = _level_cap(library, char, action.grade)
    level = action.item_level or cap
    if level > cap:
        raise WorldActionError(f"物品等級最高 {cap}（角色等級與通用料上限）")
    weapon_class = _hero_weapon_class(library, char) if action.slot_type == "weapon" else None
    hidden = rules.hidden_for(action.slot_type, materials)
    affix: str | None = None
    rarity = action.rarity
    if hidden is not None:  # 隱藏配方（M7）：稀有度與獨特詞條由配方決定（代決 5D3-7）
        rarity = hidden.rarity
    else:
        if action.affix is None:
            raise WorldActionError("要指定 1 條詞條")
        allowed = {a.id for a in build_choices(library, action.slot_type, weapon_class)}
        if action.affix not in allowed:
            raise WorldActionError(f"這個部位不能指定 {action.affix}")
        affix = action.affix
    recipe = CraftRecipe(
        slot_type=action.slot_type,
        weapon_class=weapon_class,  # type: ignore[arg-type]
        rarity=rarity,
        item_level=level,
        affix=affix,
        grade=action.grade,
        materials=materials,
    )
    return recipe, hidden


def _record_from_code(
    library: ContentLibrary, world: WorldState, char: CharacterState, code: str
) -> tuple[RecipeRecord, HiddenRecipe | None]:
    record = world.recipe_of(code.lower())
    if record is None:
        raise WorldActionError(f"沒有這個配方碼：{code.upper()}")
    recipe = record.recipe
    if recipe.item_level > char.level:
        raise WorldActionError(f"這份配方要 {recipe.item_level} 級（你是 {char.level} 級）")
    if recipe.weapon_class is not None and recipe.weapon_class != _hero_weapon_class(library, char):
        raise WorldActionError("這份配方的武器和你的武器不是同一大類")
    hidden = _rules(library).hidden_for(recipe.slot_type, recipe.materials)
    return record, hidden


@dataclass(frozen=True)
class CraftPlan:
    """打造前算好的配方與費用（API 也用來顯示）。

    ``print_``／``base_code``＝基礎配方的指紋與配方碼（打造的亂數）；``code``＝這次打造的配方碼
    （帶序列時是帶序列的碼）；``steps``＝打好後照順序重骰與指定（5D-3b）。"""

    recipe: CraftRecipe
    hidden: HiddenRecipe | None
    print_: str
    code: str
    spent: dict[str, int]
    gold: int
    quest_coins: int
    base_code: str = ""
    steps: tuple[RecipeStep, ...] = ()


def plan_craft(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: CraftAction
) -> CraftPlan:
    """配方與費用（不檢查地點與夠不夠）；配方不合法拋 :class:`WorldActionError`。"""
    rules = _rules(library)
    steps: tuple[RecipeStep, ...] = ()
    if action.code is not None:
        record, hidden = _record_from_code(library, world, char, action.code)
        recipe, steps = record.recipe, record.steps
    else:
        recipe, hidden = _recipe_from_fields(library, char, action)
    print_ = fingerprint(recipe)
    spent = {recipe.grade: rules.craft.grade_amount[recipe.slot_type]}
    spent.update(dict.fromkeys(recipe.materials, 1))
    cost = rules.craft.rarities[recipe.rarity]
    gold = cost.gold_per_level * recipe.item_level
    essence = 0
    for done, step in enumerate(steps):  # 照序列重骰與指定，費用照付（同原裝備當時的費用）
        mod_cost = rules.reroll if step.affix is None else rules.imbue
        gold += mod_cost.gold(done)
        essence += mod_cost.essence
    if essence:
        spent[rules.essence] = spent.get(rules.essence, 0) + essence
    return CraftPlan(
        recipe=recipe,
        hidden=hidden,
        print_=print_,
        code=recipe_code(variant_print(print_, steps)),
        spent=dict(sorted(spent.items())),
        gold=gold,
        quest_coins=cost.quest_coins,
        base_code=recipe_code(print_),
        steps=steps,
    )


def _make_item(
    library: ContentLibrary, plan: CraftPlan, serial: int, name_zh: str | None
) -> tuple[ItemDef, GearMod]:
    """打出基礎配方的裝備（``name_zh``＝配方第一次打造的名稱），再照序列重骰與指定（5D-3b）。"""
    rules = _rules(library)
    recipe = plan.recipe
    leanings = {
        a: rules.craft.leaning_weight for m in recipe.materials for a in rules.materials[m].leanings
    }
    forced = plan.hidden.affix if plan.hidden is not None else recipe.affix
    rng = Rng(int(plan.print_[:16], 16))
    problems: list[str] = []
    item = generate_item_retrying(
        library,
        rng,
        recipe.slot_type,
        recipe.rarity,
        recipe.item_level,
        weapon_class=recipe.weapon_class,
        forced=forced,
        leanings=leanings,
        problems=problems,
    )
    if item is None:
        raise WorldActionError(f"這份配方打不出來（{problems[-1] if problems else ''}）")
    tags = dict.fromkeys(item.tags)
    for m in recipe.materials:
        keyword = rules.materials[m].resonance
        if keyword is not None:
            tags[f"{RESONANCE_TAG}{keyword}"] = None
    update: dict[str, object] = {
        "id": f"item_craft_{plan.code}_{serial}",
        "tags": tuple(tags),
    }
    if plan.hidden is not None:
        update["name_zh"] = plan.hidden.name_zh
    if name_zh is not None:
        update["name_zh"] = name_zh  # 名稱綁定配方第一次打造（8.20）
    item = item.model_copy(update=update)
    mod = GearMod(fingerprint=plan.print_, recipe=plan.base_code)
    for step in plan.steps:
        try:
            item, mod, _ = _apply_step(library, item, mod, step)
        except WorldActionError as exc:
            raise WorldActionError(f"這份配方的重骰序列在目前的內容下重現不了（{exc}）") from exc
    if plan.steps:
        mod = mod.model_copy(update={"variant": plan.code})
    return item, mod


def _pay(char: CharacterState, gold: int, quest_coins: int = 0) -> dict[str, int]:
    if char.gold < gold:
        raise WorldActionError(f"金幣不夠（要 {gold}，有 {char.gold}）")
    if char.quest_coins < quest_coins:
        raise WorldActionError(f"任務幣不夠（要 {quest_coins}，有 {char.quest_coins}）")
    return {"gold": char.gold - gold, "quest_coins": char.quest_coins - quest_coins}


def _craft(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: CraftAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    station = _station(library, char, action.station, "smithy")
    plan = plan_craft(library, world, char, action)
    if plan.steps and not any(s.kind == "enchanter" for s in stations_here(library, char)):
        raise WorldActionError("這份配方帶重骰序列，要在有附魔台的地方打")
    bag = remove_items(char.bag, plan.spent)
    wallet = _pay(char, plan.gold, plan.quest_coins)
    known = world.recipe_of(plan.code)
    item, mod = _make_item(library, plan, char.crafts + 1, None if known is None else known.name_zh)
    check_room(library, bag, len(char.gear) + 1)
    world, record, discovered = _remember(
        world,
        RecipeRecord(
            code=plan.code,
            recipe=plan.recipe,
            name_zh=item.name_zh,
            discoverer=char.character_id,
            discoverer_name=char.hero.name_zh,
            discovered_at=now,
            hidden=None if plan.hidden is None else plan.hidden.id,
            base=plan.base_code if plan.steps else None,
            steps=plan.steps,
            season_id=world.season_id,
        ),
    )
    mods = {**char.gear_mods, item.id: mod}
    char = char.model_copy(
        update={
            **wallet,
            "bag": bag,
            "gear": (*char.gear, item),
            "crafts": char.crafts + 1,
            "gear_mods": mods,
        }
    )
    event = GearCraftedEvent(
        station=station.id,
        code=plan.code,
        item=item.id,
        name_zh=item.name_zh,
        slot_type=plan.recipe.slot_type,
        rarity=plan.recipe.rarity,
        item_level=plan.recipe.item_level,
        spent=plan.spent,
        gold_spent=plan.gold,
        quest_coins_spent=plan.quest_coins,
        hidden=record.hidden,
        discovered=discovered,
        discoverer_name=record.discoverer_name,
    )
    return world, char, (event,)


def _remember(world: WorldState, record: RecipeRecord) -> tuple[WorldState, RecipeRecord, bool]:
    """世界還沒有這個配方碼 → 記下（首位發現者寫在 ``record``，M6）。

    已經有的碼：一件裝備現在是這個碼了，配方表重新列出它（5D-4，``listed``）；首位發現者不變。
    回傳（世界、世界裡的紀錄、這次是不是新發現）。"""
    known = world.recipe_of(record.code)
    if known is not None:
        return _set_listed(world, known.code, listed=True), known, False
    recipes = sorted((*world.recipes, record), key=lambda r: r.code)
    return world.model_copy(update={"recipes": tuple(recipes)}), record, True


def _set_listed(world: WorldState, code: str, *, listed: bool) -> WorldState:
    """配方表每件裝備只列最新一筆（5D-4，玩法 PM 2026-11-03 代決）：紀錄留著（舊碼照樣能打），
    只改要不要列在配方表上。"""
    if all(r.listed == listed for r in world.recipes if r.code == code):
        return world
    recipes = tuple(
        r.model_copy(update={"listed": listed}) if r.code == code else r for r in world.recipes
    )
    return world.model_copy(update={"recipes": recipes})


# ---------------------------------------------------------------------------
# 強化、分解、重骰、指定
# ---------------------------------------------------------------------------


def find_gear(char: CharacterState, item_id: str) -> ItemDef | None:
    """背包或穿戴中的裝備（先找背包）。"""
    found = next((g for g in char.gear if g.id == item_id), None)
    if found is not None:
        return found
    return next((g for g in char.equipment.values() if g.id == item_id), None)


def mod_of(char: CharacterState, item: ItemDef) -> GearMod:
    """這件裝備的改動紀錄（沒有時以物品 JSON 當指紋開一筆新的，8.20）。"""
    return char.gear_mods.get(item.id) or GearMod(fingerprint=_item_print(item))


def _replace(char: CharacterState, old: ItemDef, new: ItemDef, mod: GearMod) -> CharacterState:
    gear = list(char.gear)
    equipment = dict(char.equipment)
    if old in gear:
        gear[gear.index(old)] = new
    else:
        slot = next(s for s, g in equipment.items() if g.id == old.id)
        equipment[slot] = new
    mods = {**char.gear_mods, new.id: mod}
    return char.model_copy(update={"gear": tuple(gear), "equipment": equipment, "gear_mods": mods})


def _gear_or_raise(char: CharacterState, item_id: str) -> ItemDef:
    item = find_gear(char, item_id)
    if item is None:
        raise WorldActionError(f"沒有這件裝備：{item_id}")
    return item


def enhance_cost(
    library: ContentLibrary, char: CharacterState, item: ItemDef
) -> tuple[int, dict[str, int], int] | str:
    """下一級強化的（目標等級、材料、金幣）；不能強化時回傳原因。"""
    rules = _rules(library)
    if item.item_level is None:
        return "初始裝備不能強化"
    level = mod_of(char, item).enhance + 1
    if level > rules.enhance.max_level:
        return f"已經強化到 +{rules.enhance.max_level}"
    grade = grade_item(library, item.item_level)
    if grade is None:
        return "沒有對應的通用料"
    gold = rules.enhance.gold_per_level * item.item_level * level
    return level, {grade: level}, gold


def _enhance(
    library: ContentLibrary, char: CharacterState, action: EnhanceAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    _station(library, char, action.station, "smithy")
    item = _gear_or_raise(char, action.item)
    cost = enhance_cost(library, char, item)
    if isinstance(cost, str):
        raise WorldActionError(f"不能強化：{cost}")
    level, spent, gold = cost
    bag = remove_items(char.bag, spent)
    wallet = _pay(char, gold)
    step = _rules(library).enhance.step_permille
    new = item.model_copy(update={"base_bonus_permille": item.base_bonus_permille + step})
    mod = mod_of(char, item).model_copy(update={"enhance": level})
    char = _replace(char.model_copy(update={**wallet, "bag": bag}), item, new, mod)
    event = GearEnhancedEvent(
        item=item.id, name_zh=item.name_zh, level=level, spent=spent, gold_spent=gold
    )
    return char, (event,)


def _salvage(
    library: ContentLibrary, char: CharacterState, action: SalvageAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    rules = _rules(library)
    _station(library, char, action.station, "smithy")
    item = next((g for g in char.gear if g.id == action.item), None)
    if item is None:
        if find_gear(char, action.item) is not None:
            raise WorldActionError("穿戴中的裝備不能分解，先換下來")
        raise WorldActionError(f"背包裡沒有這件裝備：{action.item}")
    essence = rules.salvage.get(item.rarity or "")
    if essence is None:
        raise WorldActionError(f"{item.name_zh}不能分解")
    char = remove_gear(char, [item.id])
    bag = add_items(char.bag, {rules.essence: essence})
    check_room(library, bag, len(char.gear))
    char = char.model_copy(update={"bag": bag})
    return char, (GearSalvagedEvent(item=item.id, name_zh=item.name_zh, essence=essence),)


def _apply_step(
    library: ContentLibrary, item: ItemDef, mod: GearMod, step: RecipeStep
) -> tuple[ItemDef, GearMod, tuple[AffixDef, int | None]]:
    """重骰（``step.affix`` 是 ``None``）或指定一條詞條，並把這一步記進改動紀錄。

    重骰的亂數＝「指紋＋位置＋n」（n＝這個位置已重骰的次數，8.20）；打造時照配方序列重現也走這裡。"""
    if step.index >= len(item.affixes):
        raise WorldActionError(f"{item.name_zh}沒有第 {step.index + 1} 條詞條")
    options = affix_choices(library, item, step.index)
    if not options:
        raise WorldActionError(f"{item.name_zh}的第 {step.index + 1} 條詞條不能換")
    if step.affix is not None:
        chosen = next((o for o in options if o[0].id == step.affix), None)
        if chosen is None:
            raise WorldActionError(f"這條不能指定成 {step.affix}")
        update: dict[str, object] = {"imbues": mod.imbues + 1}
    else:
        n = mod.rerolls.count(step.index)
        chosen = pick_affix(library, item, options, _rng(mod.fingerprint, step.index, n))
        update = {"rerolls": (*mod.rerolls, step.index)}
    update["steps"] = (*mod.steps, step)
    new = replace_affix(item, step.index, chosen[0], chosen[1])
    return new, mod.model_copy(update=update), chosen


def _change(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: RerollAction | ImbueAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    rules = _rules(library)
    _station(library, char, action.station, "enchanter")
    item = _gear_or_raise(char, action.item)
    mod = mod_of(char, item)
    imbue = isinstance(action, ImbueAction)
    cost = rules.imbue if imbue else rules.reroll
    gold = cost.gold(mod.changes)
    step = RecipeStep(
        index=action.index, affix=action.affix if isinstance(action, ImbueAction) else None
    )
    new, changed, chosen = _apply_step(library, item, mod, step)
    bag = remove_items(char.bag, {rules.essence: cost.essence}) if cost.essence else dict(char.bag)
    wallet = _pay(char, gold)
    code: str | None = None
    discovered = False
    if mod.traceable:  # 打造品：配方＝基礎配方＋重骰序列（5D-3b）
        assert mod.recipe is not None
        code = recipe_code(variant_print(mod.fingerprint, changed.steps))
        changed = changed.model_copy(update={"variant": code})
        base = world.recipe_of(mod.recipe)
        previous = mod.variant or mod.recipe  # 這件裝備改之前的碼：不再是它的最新一筆（5D-4）
        if previous != code:
            world = _set_listed(world, previous, listed=False)
        if base is not None:
            world, _, discovered = _remember(
                world,
                base.model_copy(
                    update={
                        "code": code,
                        "name_zh": item.name_zh,
                        "discoverer": char.character_id,
                        "discoverer_name": char.hero.name_zh,
                        "discovered_at": now,
                        "base": base.code,
                        "steps": changed.steps,
                        "listed": True,
                    }
                ),
            )
    elif mod.variant is not None:
        changed = changed.model_copy(update={"variant": None})
    char = _replace(char.model_copy(update={**wallet, "bag": bag}), item, new, changed)
    event = AffixChangedEvent(
        mode="imbue" if imbue else "reroll",
        item=item.id,
        name_zh=item.name_zh,
        index=action.index,
        old=item.affixes[action.index].affix,
        new=chosen[0].id,
        value=chosen[1],
        gold_spent=gold,
        essence_spent=cost.essence,
        code=code,
        discovered=discovered,
    )
    return world, char, (event,)


def apply_crafting(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: CraftAction | EnhanceAction | RerollAction | ImbueAction | SalvageAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """鐵匠與附魔台的動作（見模組說明；依 :data:`CRAFTING_HANDLERS` 分派）；不合法拋
    :class:`WorldActionError`（狀態不變）。"""
    return CRAFTING_HANDLERS[type(action)](library, world, char, action, now)


def _keeps_world(
    fn: Callable[
        [ContentLibrary, CharacterState, Any], tuple[CharacterState, tuple[WorldEvent, ...]]
    ],
) -> CraftingHandler:
    def run(
        library: ContentLibrary, world: WorldState, char: CharacterState, action: Any, _now: int
    ) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
        char, events = fn(library, char, action)
        return world, char, events

    return run


type CraftingHandler = Callable[
    [ContentLibrary, WorldState, CharacterState, Any, int],
    tuple[WorldState, CharacterState, tuple[WorldEvent, ...]],
]
CRAFTING_HANDLERS: Final[Mapping[type, CraftingHandler]] = {
    CraftAction: _craft,
    EnhanceAction: _keeps_world(_enhance),
    RerollAction: _change,
    ImbueAction: _change,
    SalvageAction: _keeps_world(_salvage),
}
"""鐵匠與附魔台的動作種類 → 處理 ``(library, world, char, action, now) → (world, char, events)``
（5D-R1）。"""
