"""裝備測試介面的伺服器端邏輯（Phase 3G-G4）：目錄、驗證、套用到靶場戰鬥的主角。

規則全部沿用既有函式（守則 3：只能提議，由引擎的驗證裁決）：物品以
:func:`trpg.content.equipment.item_problems`（詞條在白名單、可掛在這個欄位／武器／標籤、數值在初值範圍內、
條數上限）檢查，穿戴以 :func:`~trpg.content.equipment.loadout_problems`（種類、占用、同一枚戒指、
代價型條數）檢查，技能與武器相容用 :func:`trpg.content.skills.weapon_problem`。快照內嵌在
``BattleSetup``，
下載的戰鬥紀錄可以直接 ``trpg battle replay``。
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ValidationError

from trpg.api.gear_schemas import (
    GearAffixInfo,
    GearCatalog,
    GearChoice,
    GearCustomItem,
    GearItemInfo,
    GearItemLine,
    GearSlotInfo,
    GearWeaponInfo,
)
from trpg.content.appearance import derive_keywords, item_appearance_problems
from trpg.content.equipment import (
    AFFIX_CATEGORY_NUMBER,
    AFFIX_CATEGORY_ZH,
    AffixDef,
    AffixRoll,
    ItemDef,
    Loadout,
    affix_text,
    item_problems,
    loadout_problems,
    resolve_loadout,
)
from trpg.content.library import ContentLibrary
from trpg.content.skills import weapon_problem
from trpg.content.slots import SLOT_TYPE_OF, SLOT_TYPE_ZH, SLOT_ZH, SLOTS, Slot
from trpg.engine.setup import BattleSetup
from trpg.engine.view import AppearanceView
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team

__all__ = ["GearRequestError", "equip_gear", "gear_catalog", "gear_problems"]


class GearRequestError(TrpgError):
    """裝備不合法（422，中文原因；多個原因以「；」連接）。"""


def _appearance(item: ItemDef, affixes: Mapping[str, AffixDef]) -> AppearanceView:
    defs = [affixes[r.affix] for r in item.affixes if r.affix in affixes]
    return AppearanceView(
        kind=item.kind,
        form=item.form,
        material=item.material,
        dye=item.dye,
        style=item.style,
        rarity=item.rarity or ("legendary" if item.legendary else "common"),
        keywords=derive_keywords(defs),
    )


def _item_info(library: ContentLibrary, item: ItemDef) -> GearItemInfo:
    affixes = library.affixes
    weapon = library.weapons.get(item.weapon) if item.weapon is not None else None
    return GearItemInfo(
        id=item.id,
        name_zh=item.name_zh,
        slot_type=item.slot_type,
        weapon=item.weapon,
        weapon_name_zh=None if weapon is None else weapon.name_zh,
        two_handed=weapon is not None and weapon.two_handed,
        paired=item.paired,
        tags=item.tags,
        legendary=item.legendary,
        affixes=tuple(
            GearItemLine(affix_id=r.affix, text_zh=affix_text(affixes[r.affix], r.value))
            for r in item.affixes
        ),
        appearance=_appearance(item, affixes),
    )


def gear_catalog(library: ContentLibrary) -> GearCatalog:
    """欄位、測試物品、詞條白名單與武器（測試介面的選單）。"""
    rules = library.ruleset.equipment
    return GearCatalog(
        slots=tuple(
            GearSlotInfo(
                slot=s,
                name_zh=SLOT_ZH[s],
                slot_type=SLOT_TYPE_OF[s],
                slot_type_zh=SLOT_TYPE_ZH[SLOT_TYPE_OF[s]],
            )
            for s in SLOTS
        ),
        items=tuple(_item_info(library, i) for i in library.items.values()),
        affixes=tuple(_affix_info(a) for a in library.affixes.values()),
        weapons=tuple(
            GearWeaponInfo(
                id=w.id, name_zh=w.name_zh, weapon_class=w.weapon_class, two_handed=w.two_handed
            )
            for w in sorted(library.weapons.values(), key=lambda w: w.id)
        ),
        max_affixes_per_item=rules.max_affixes_per_item,
        max_cost_affixes=rules.caps.cost_affixes,
        diminishing_permille=rules.diminishing_permille,
    )


def _affix_info(affix: AffixDef) -> GearAffixInfo:
    return GearAffixInfo(
        id=affix.id,
        name_zh=affix.name_zh,
        category=affix.category,
        category_number=AFFIX_CATEGORY_NUMBER[affix.category],
        category_zh=AFFIX_CATEGORY_ZH[affix.category],
        slot_types=affix.slots,
        weapons=affix.weapons,
        weapon_class=affix.weapon_class,
        item_tags={k: tuple(v) for k, v in affix.item_tags.items()},
        legendary_only=affix.legendary_only,
        value_min=None if affix.value is None else affix.value.min,
        value_max=None if affix.value is None else affix.value.max,
        value_unit=affix.value_unit,
    )


# ---------------------------------------------------------------------------
# 驗證
# ---------------------------------------------------------------------------


def _custom_item(slot: Slot, custom: GearCustomItem) -> ItemDef:
    """自訂物品 → :class:`ItemDef`（schema 不合法時拋出 :class:`ValidationError`）。"""
    return ItemDef(
        id=f"custom_{slot}",
        name_zh=custom.name_zh.strip() or "自訂物品",
        slot_type=SLOT_TYPE_OF[slot],
        weapon=custom.weapon,
        paired=custom.paired,
        tags=custom.tags,
        legendary=custom.legendary,
        kind=custom.kind,
        affixes=tuple(AffixRoll(affix=a.affix, value=a.value) for a in custom.affixes),
    )


def _friendly(text: str, item: ItemDef, affixes: Mapping[str, AffixDef]) -> str:
    """把錯誤訊息裡的物品與詞條 id 換成玩家看得懂的名稱。"""
    text = text.replace(f"物品 {item.id} ", f"「{item.name_zh}」").replace(
        f"物品 {item.id}", f"「{item.name_zh}」"
    )
    for roll in item.affixes:
        affix = affixes.get(roll.affix)
        if affix is not None:
            label = affix.name_zh.replace("{n}", "N")
            text = text.replace(f"詞條 {affix.id}", f"詞條「{label}」")
    return text


def _build_custom(
    library: ContentLibrary, slot: Slot, custom: GearCustomItem, problems: list[str]
) -> ItemDef | None:
    label = f"{SLOT_ZH[slot]}的自訂物品「{custom.name_zh}」"
    try:
        item = _custom_item(slot, custom)
    except ValidationError as exc:
        problems += [f"{label}：{e['msg'].removeprefix('Value error, ')}" for e in exc.errors()]
        return None
    affixes = library.affixes
    found = item_problems(item, affixes, library.weapons, library.ruleset.equipment)
    if not item.affixes:
        found.append(f"{item.name_zh}：至少要掛 1 條詞條")
    if library.appearance is not None:
        found += item_appearance_problems(item, library.appearance)
    problems += [_friendly(p, item, affixes) for p in found]
    return None if found else item


def _resolve_choices(
    library: ContentLibrary, equipment: Mapping[str, GearChoice]
) -> tuple[dict[str, str], dict[str, ItemDef], list[str]]:
    """每個欄位的選擇 → ``(欄位 → 物品 id, 物品表, 問題)``；物品本身的問題在這裡檢查。"""
    problems: list[str] = []
    chosen: dict[str, str] = {}
    items: dict[str, ItemDef] = dict(library.items)
    for slot, choice in equipment.items():
        if slot not in SLOTS:
            problems.append(f"未知的裝備欄位：{slot}")
        elif choice.custom is None:
            if choice.item_id not in items:
                problems.append(f"{SLOT_ZH[slot]}：未知的物品 {choice.item_id}")
            else:
                chosen[slot] = choice.item_id
        else:
            item = _build_custom(library, slot, choice.custom, problems)
            if item is not None:
                items[item.id] = item
                chosen[slot] = item.id
    return chosen, items, problems


def _hero_index(setup: BattleSetup) -> int:
    return next(i for i, u in enumerate(setup.units) if u.team is Team.ALLY)


def _equipped_hero(
    setup: BattleSetup, library: ContentLibrary, loadout: Loadout
) -> tuple[BattleSetup, list[str]]:
    """主角換上 ``loadout``（沒選的欄位清空）；主手有武器物品時武器跟著換。回傳新設定與穿戴問題。"""
    index = _hero_index(setup)
    hero = setup.units[index]
    main = loadout.item_in("main_hand")
    weapon = hero.weapon
    template = hero.template
    if main is not None and main.item.weapon is not None:
        weapon = library.weapons[main.item.weapon]
        template = template.model_copy(update={"weapon": weapon.id})
    problems = loadout_problems(loadout, weapon, setup.ruleset.equipment)
    defs = setup.ruleset.skills.by_id()
    for skill_id in template.skills:
        skill = defs.get(skill_id)
        found = None if skill is None else weapon_problem(skill, weapon.weapon_class)
        if found is not None:
            problems.append(f"主手換成{weapon.name_zh}後：{found}")
    units = list(setup.units)
    units[index] = hero.model_copy(
        update={"template": template, "weapon": weapon, "equipment": loadout}
    )
    return setup.model_copy(update={"units": tuple(units)}), problems


def gear_problems(
    setup: BattleSetup, library: ContentLibrary, equipment: Mapping[str, GearChoice]
) -> tuple[BattleSetup, list[str]]:
    """套用 ``equipment`` 後的設定與全部問題（空 ＝ 合法）；物品本身有問題時設定維持原樣。"""
    chosen, items, problems = _resolve_choices(library, equipment)
    if problems:
        return setup, problems
    loadout = resolve_loadout(chosen, items, library.affixes)
    return _equipped_hero(setup, library, loadout)


def equip_gear(
    setup: BattleSetup, library: ContentLibrary, equipment: Mapping[str, GearChoice]
) -> BattleSetup:
    """把 ``equipment`` 穿到主角（我方第一個單位）身上；不合法時拋出 :class:`GearRequestError`。"""
    result, problems = gear_problems(setup, library, equipment)
    if problems:
        raise GearRequestError("；".join(problems))
    return result
