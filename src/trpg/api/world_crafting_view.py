"""鐵匠與附魔台的顯示資料（Phase 5D-3；``docs/phases/Phase5計畫.md`` 30.5）與事件句子。規則一律
呼叫 :mod:`trpg.world.crafting`，這裡只組裝文字。能不能做以「試做一次」判斷（純函式，不改狀態）。"""

from __future__ import annotations

from trpg.api.world_crafting_schemas import (
    CraftGearView,
    CraftingView,
    CraftMaterialView,
    CraftOptionView,
    CraftRarityView,
    CraftSlotView,
    GearAffixView,
    RecipeView,
    StationView,
)
from trpg.api.world_economy_view import gear_title
from trpg.content.battle import WeaponDef
from trpg.content.equipment import ItemDef, affix_text
from trpg.content.item_budget import RARITY_ZH
from trpg.content.item_gen import affix_choices
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_TYPE_ZH, SLOT_TYPES
from trpg.world.actions import WorldEvent
from trpg.world.crafting import (
    apply_crafting,
    build_choices,
    crafting_rules,
    enhance_cost,
    mod_of,
    station_problem,
    stations_here,
)
from trpg.world.crafting_actions import (
    AffixChangedEvent,
    CraftAction,
    EnhanceAction,
    GearCraftedEvent,
    GearEnhancedEvent,
    GearSalvagedEvent,
)
from trpg.world.errors import WorldActionError
from trpg.world.gear import item_loadout
from trpg.world.resonance import active_resonances
from trpg.world.state import CharacterState, RecipeRecord, WorldState

__all__ = ["crafting_event_line", "crafting_view", "resonance_lines"]

_NOTE = (
    "沒人試過的材料組合只看得到傾向；第一次打出某份配方的人會成為它的首位發現者，配方碼可以分享。"
)


def _name(library: ContentLibrary, item_id: str) -> str:
    found = library.world_economy.items.get(item_id)
    return item_id if found is None else found.name_zh


def _counts_zh(library: ContentLibrary, counts: dict[str, int]) -> str:
    return "、".join(f"{_name(library, k)} ×{v}" for k, v in sorted(counts.items()))


def _keyword_name(library: ContentLibrary, keyword: str) -> str:
    found = library.keywords.by_id().get(keyword)
    return keyword if found is None else found.name_zh


def _affix_zh(library: ContentLibrary, affix_id: str, value: int | None = None) -> str:
    affix = library.affixes.get(affix_id)
    return affix_id if affix is None else affix_text(affix, value)


def _problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: object
) -> str | None:
    try:
        apply_crafting(library, world, char, action, 0)  # type: ignore[arg-type]
    except WorldActionError as exc:
        return str(exc)
    return None


def _materials(library: ContentLibrary, char: CharacterState) -> tuple[CraftMaterialView, ...]:
    rules = crafting_rules(library)
    assert rules is not None
    found: list[CraftMaterialView] = []
    for item_id, count in sorted(char.bag.items()):
        item = library.world_economy.items.get(item_id)
        if item is None or item.kind != "material":
            continue
        if item.grade is not None:
            cap = min(char.level, rules.craft.grade_cap[item.grade])
            found.append(
                CraftMaterialView(
                    item=item_id, name_zh=item.name_zh, count=count, grade=True, level_cap=cap
                )
            )
            continue
        flavor = rules.materials.get(item_id)
        if flavor is None:
            continue
        leaning = "、".join(_affix_zh(library, a).replace("{n}", "n") for a in flavor.leanings)
        found.append(
            CraftMaterialView(
                item=item_id,
                name_zh=item.name_zh,
                count=count,
                grade=False,
                leaning_zh=f"傾向：{leaning}" if leaning else None,
                resonance_zh=None
                if flavor.resonance is None
                else f"共鳴：{_keyword_name(library, flavor.resonance)}",
            )
        )
    return tuple(found)


def _recipe_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    record: RecipeRecord,
    smithy: str | None,
) -> RecipeView:
    recipe = record.recipe
    mats = [_name(library, recipe.grade), *(_name(library, m) for m in recipe.materials)]
    summary = "・".join(
        [
            SLOT_TYPE_ZH.get(recipe.slot_type, recipe.slot_type),
            RARITY_ZH.get(recipe.rarity, recipe.rarity),
            f"物品等級 {recipe.item_level}",
            "＋".join(mats),
        ]
    )
    if record.steps:  # 帶重骰序列的配方（5D-3b）
        rerolls = sum(1 for s in record.steps if s.affix is None)
        imbues = len(record.steps) - rerolls
        parts = [f"重骰 {rerolls} 次" if rerolls else "", f"指定 {imbues} 次" if imbues else ""]
        summary += "・" + "、".join(p for p in parts if p)
        if record.base is not None:
            summary += f"（基礎配方 {record.base.upper()}）"
    problem = (
        "這裡沒有鐵匠"
        if smithy is None
        else _problem(library, world, char, CraftAction(station=smithy, code=record.code))
    )
    return RecipeView(
        code=record.code.upper(),
        name_zh=record.name_zh,
        summary_zh=summary,
        discoverer_name=record.discoverer_name,
        mine=record.discoverer == char.character_id,
        can_craft=problem is None,
        problem_zh=problem,
    )


def _affix_views(library: ContentLibrary, item: ItemDef, usable: bool) -> tuple[GearAffixView, ...]:
    views: list[GearAffixView] = []
    for index, roll in enumerate(item.affixes):
        options = affix_choices(library, item, index) if usable else []
        views.append(
            GearAffixView(
                index=index,
                text_zh=_affix_zh(library, roll.affix, roll.value),
                can_change=bool(options),
                choices=tuple(
                    CraftOptionView(id=a.id, text_zh=affix_text(a, v)) for a, v in options
                ),
            )
        )
    return tuple(views)


def _gear_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    item: ItemDef,
    *,
    worn: bool,
    smithy: str | None,
    enchanter: str | None,
) -> CraftGearView:
    rules = crafting_rules(library)
    assert rules is not None
    mod = mod_of(char, item)
    enhance_zh: str | None
    can_enhance = False
    cost = enhance_cost(library, char, item)
    if isinstance(cost, str):
        enhance_zh = cost
    else:
        level, spent, gold = cost
        enhance_zh = f"強化到 +{level}：{_counts_zh(library, spent)}、金幣 {gold}"
        if smithy is not None:
            problem = _problem(library, world, char, EnhanceAction(station=smithy, item=item.id))
            can_enhance = problem is None
            if problem is not None:
                enhance_zh = f"{enhance_zh}（{problem}）"
    salvage = rules.salvage.get(item.rarity or "")
    can_salvage = not worn and salvage is not None and smithy is not None
    if worn:
        salvage_zh: str | None = "穿戴中的裝備不能分解"
    elif salvage is None:
        salvage_zh = "這件不能分解"
    else:
        salvage_zh = f"分解得到精華 ×{salvage}"
    essence = _name(library, rules.essence)
    return CraftGearView(
        item=item.id,
        name_zh=gear_title(item),
        worn=worn,
        description_zh="；".join(_affix_zh(library, r.affix, r.value) for r in item.affixes),
        code=None if mod.code is None else mod.code.upper(),
        enhance=mod.enhance,
        can_enhance=can_enhance,
        enhance_zh=enhance_zh,
        can_salvage=can_salvage,
        salvage_zh=salvage_zh,
        reroll_zh=f"{essence} ×{rules.reroll.essence}、金幣 {rules.reroll.gold(mod.changes)}",
        imbue_zh=f"{essence} ×{rules.imbue.essence}、金幣 {rules.imbue.gold(mod.changes)}",
        affixes=_affix_views(library, item, enchanter is not None),
    )


def _rarity_views(library: ContentLibrary) -> tuple[CraftRarityView, ...]:
    rules = crafting_rules(library)
    assert rules is not None
    views = []
    for rarity, cost in rules.craft.rarities.items():
        text = f"金幣 {cost.gold_per_level} × 物品等級"
        if cost.quest_coins:
            text += f"＋任務幣 {cost.quest_coins}"
        views.append(
            CraftRarityView(rarity=rarity, name_zh=RARITY_ZH.get(rarity, rarity), cost_zh=text)
        )
    return tuple(views)


def _slot_views(library: ContentLibrary, char: CharacterState) -> tuple[CraftSlotView, ...]:
    rules = crafting_rules(library)
    assert rules is not None
    weapon = library.weapons.get(char.hero.weapon)
    weapon_class = None if weapon is None else weapon.weapon_class
    return tuple(
        CraftSlotView(
            slot_type=slot,
            name_zh=SLOT_TYPE_ZH.get(slot, slot),
            grade_amount=rules.craft.grade_amount[slot],
            affixes=tuple(
                CraftOptionView(
                    id=a.id, text_zh=affix_text(a, None if a.value is None else a.value.max)
                )
                for a in build_choices(library, slot, weapon_class)
            ),
        )
        for slot in SLOT_TYPES
    )


def crafting_view(
    library: ContentLibrary, world: WorldState, char: CharacterState, *, in_battle: bool
) -> CraftingView | None:
    """角色所在地點的鐵匠與附魔台；這裡沒有設施為 ``None``。"""
    rules = crafting_rules(library)
    here = stations_here(library, char)
    if rules is None or not here:
        return None
    problem = "戰鬥中" if in_battle else station_problem(library, char, here[0])
    smithy = next((s.id for s in here if s.kind == "smithy"), None)
    enchanter = next((s.id for s in here if s.kind == "enchanter"), None)
    if problem is not None:
        smithy_ok, enchanter_ok = None, None
    else:
        smithy_ok, enchanter_ok = smithy, enchanter
    npcs = library.world_event_content.npcs.get(char.region)
    cards = {} if npcs is None else npcs.npc_by_id()
    stations = tuple(
        StationView(
            station=s.id,
            kind=s.kind,
            name_zh=s.name_zh,
            npc_name_zh=None if s.npc is None or s.npc not in cards else cards[s.npc].name_zh,
        )
        for s in here
    )
    gear = [
        _gear_view(library, world, char, g, worn=False, smithy=smithy_ok, enchanter=enchanter_ok)
        for g in char.gear
    ]
    gear += [
        _gear_view(library, world, char, g, worn=True, smithy=smithy_ok, enchanter=enchanter_ok)
        for g in char.equipment.values()
        if g.item_level is not None
    ]
    return CraftingView(
        stations=stations,
        smithy=smithy,
        enchanter=enchanter,
        can_use=problem is None,
        problem_zh=problem,
        slots=_slot_views(library, char),
        rarities=_rarity_views(library),
        materials=_materials(library, char),
        flavor_max=rules.craft.flavor_max,
        recipes=tuple(
            _recipe_view(library, world, char, r, smithy_ok) for r in world.recipes if r.listed
        ),
        gear=tuple(gear),
        essence=char.bag.get(rules.essence, 0),
        note_zh=_NOTE,
    )


def resonance_lines(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """目前觸發的共鳴（背包面板顯示；M3）。"""
    weapon: WeaponDef | None = library.weapons.get(char.hero.weapon)
    if weapon is None or not char.equipment:
        return ()
    loadout = item_loadout(library, char.equipment)
    return tuple(r.text_zh(library) for r in active_resonances(library, loadout, weapon))


def crafting_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """打造、強化、重骰、指定、分解的句子。"""
    if isinstance(event, GearCraftedEvent):
        cost = [_counts_zh(library, event.spent), f"金幣 {event.gold_spent}"]
        if event.quest_coins_spent:
            cost.append(f"任務幣 {event.quest_coins_spent}")
        code = event.code.upper()
        line = (
            f"打造了{event.name_zh}（{event.item_level} 級，配方碼 {code}；"
            f"用掉 {'、'.join(cost)}）。"
        )
        if event.discovered:
            line += "你是這份配方的首位發現者！"
            if event.hidden is not None:
                line += "這是一份隱藏配方。"
        else:
            line += f"首位發現者：{event.discoverer_name}。"
        return line
    if isinstance(event, GearEnhancedEvent):
        spent = _counts_zh(library, event.spent)
        return f"{event.name_zh}強化到 +{event.level}（用掉 {spent}、金幣 {event.gold_spent}）。"
    if isinstance(event, AffixChangedEvent):
        verb = "重骰" if event.mode == "reroll" else "指定"
        new = _affix_zh(library, event.new, event.value)
        old = _affix_zh(library, event.old)
        line = (
            f"{event.name_zh}的第 {event.index + 1} 條詞條{verb}成「{new}」（原本「{old}」；"
            f"精華 ×{event.essence_spent}、金幣 {event.gold_spent}）。"
        )
        if event.code is not None:
            line += f"新的配方碼 {event.code.upper()}（含重骰序列）。"
            if event.discovered:
                line += "你是這份配方的首位發現者！"
        return line
    if isinstance(event, GearSalvagedEvent):
        return f"分解了{event.name_zh}，得到精華 ×{event.essence}。"
    return None
