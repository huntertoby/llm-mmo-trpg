"""大世界經濟的顯示資料（Phase 5D-1；``docs/phases/Phase5計畫.md`` 26.5）：金幣與任務幣、背包與
腰包、這裡的店、事件句子。規則一律呼叫 :mod:`trpg.world.economy`，這裡只組裝文字。"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.api.gear import item_info
from trpg.api.gear_trade import gear_trade
from trpg.api.opening_gear_note import opening_gear_note
from trpg.api.run_presenter import gear_candidate
from trpg.api.run_schemas import HeroGearSlotOut
from trpg.api.world_economy_schemas import (
    BagItemView,
    InventoryView,
    PendingLootView,
    ShopItemView,
    ShopView,
    WalletView,
)
from trpg.content.equipment import ItemDef, affix_text
from trpg.content.item_budget import RARITY_ZH
from trpg.content.library import ContentLibrary
from trpg.content.slots import SLOT_TYPE_ZH, SLOT_ZH, SLOTS
from trpg.content.world_economy import ITEM_KINDS, WorldItemDef
from trpg.content.world_quests import AFFINITY_RANKS, AffinityRank
from trpg.roguelite.gear import current_item
from trpg.world.actions import WorldEvent
from trpg.world.affinity import affinity_rules, rank_at_least, rank_of
from trpg.world.economy import (
    buy_problem,
    economy_rules,
    gear_price,
    pouch_problem,
    shop_affinity_left,
    shop_buy_price,
    shop_here,
    shop_price_notes,
    weekly_left,
)
from trpg.world.economy_actions import (
    CurrencyGainedEvent,
    ItemBoughtEvent,
    ItemEquippedEvent,
    ItemSoldEvent,
    ItemUsedEvent,
    LootAbandonedEvent,
    LootChosenEvent,
    LootGainedEvent,
    PouchChangedEvent,
    PouchUsedEvent,
)
from trpg.world.gear import equip_problem, gear_run, worn_gear
from trpg.world.inventory import slots_over, slots_used
from trpg.world.opening import opening_limits
from trpg.world.state import CharacterState, LastBattle, WorldState

__all__ = [
    "economy_event_line",
    "gear_title",
    "inventory_view",
    "last_loot_line",
    "pending_loot_view",
    "shop_view",
    "wallet_view",
]


def wallet_view(library: ContentLibrary, char: CharacterState) -> WalletView | None:
    if economy_rules(library) is None:
        return None
    return WalletView(gold=char.gold, quest_coins=char.quest_coins)


def _item(library: ContentLibrary, item_id: str) -> WorldItemDef | None:
    return library.world_economy.items.get(item_id)


def _name(library: ContentLibrary, item_id: str) -> str:
    found = _item(library, item_id)
    return item_id if found is None else found.name_zh


def _use_zh(item: WorldItemDef) -> str | None:
    parts = []
    if item.field_hp_permille:
        parts.append(f"HP +{item.field_hp_permille // 10}%")
    if item.field_mana_permille:
        parts.append(f"法力 +{item.field_mana_permille // 10}%")
    return "、".join(parts) or None


def _battle_zh(item: WorldItemDef) -> str | None:
    if item.skill is None:
        return None
    return "放進腰包：戰鬥中花 1 AP 使用，每個用一次（不佔技能欄位）"


def _bag_item(library: ContentLibrary, item_id: str, count: int) -> BagItemView:
    rules = economy_rules(library)
    found = _item(library, item_id)
    if found is None or rules is None:
        return BagItemView(
            item=item_id,
            name_zh=item_id,
            kind_zh="",
            count=count,
            description_zh="",
            sell_price=0,
            sellable=False,
            field_usable=False,
        )
    return BagItemView(
        item=item_id,
        name_zh=found.name_zh,
        kind_zh=ITEM_KINDS[found.kind],
        count=count,
        description_zh=found.description_zh,
        sell_price=rules.sell_price(found.price) if rules.sellable(found.kind) else 0,
        sellable=rules.sellable(found.kind),
        field_usable=found.field_usable,
        use_zh=_use_zh(found),
        battle_zh=_battle_zh(found),
        tradable=_kind_tradable(library, found.kind),  # 6T-1a
    )


def _kind_tradable(library: ContentLibrary, kind: str) -> bool:
    """背包裡這種物品能不能郵寄（6T-1a：``trade.yaml`` 的 ``tradable_kinds``；沒有交易規則＝
    不能）。"""
    rules = library.world_trade
    return rules is not None and kind in rules.trade.tradable_kinds


def gear_title(item: ItemDef) -> str:
    """裝備的一句話名稱：「稀有布衣（3 級）」（沒有物品等級時只有名稱）。"""
    return item.name_zh if item.item_level is None else f"{item.name_zh}（{item.item_level} 級）"


def _gear_description(library: ContentLibrary, item: ItemDef) -> str:
    parts = [SLOT_TYPE_ZH.get(item.slot_type, item.slot_type)]
    if item.rarity is not None:
        parts.append(RARITY_ZH.get(item.rarity, item.rarity))
    if item.item_level is not None:
        parts.append(f"物品等級 {item.item_level}")
    lines = [
        affix_text(library.affixes[r.affix], r.value)
        for r in item.affixes
        if r.affix in library.affixes
    ]
    text = "・".join(parts)
    return f"{text}：{'；'.join(lines)}" if lines else text


def _gear_item(
    library: ContentLibrary,
    item: ItemDef,
    problem: str | None,
    char: CharacterState | None = None,
) -> BagItemView:
    price = gear_price(library, item)
    trade = None if char is None else gear_trade(library, char, item)  # 6T-1a
    return BagItemView(
        item=item.id,
        name_zh=gear_title(item),
        kind_zh="裝備",
        count=1,
        description_zh=_gear_description(library, item),
        sell_price=price or 0,
        sellable=price is not None,
        field_usable=False,
        gear=True,
        can_equip=problem is None,
        equip_problem_zh=problem,
        tradable=trade is not None and trade.tradable and library.world_trade is not None,
        bound_zh=None if trade is None else trade.bound_zh,
        origin_zh=None if trade is None else trade.origin_zh,
        holder_zh=None if trade is None else trade.holder_zh,
        cross_class_zh=None if trade is None else trade.cross_class_zh,
        cross_class_lost_zh=None if trade is None else trade.cross_class_lost_zh,
        opening_note_zh=None if char is None else opening_gear_note(library, char, item.id),
    )


def _equipped_lines(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    worn = worn_gear(library, char)
    return tuple(f"{SLOT_ZH[s]}：{gear_title(worn[s])}" for s in SLOTS if s in worn)


def _views(library: ContentLibrary, counts: Mapping[str, int]) -> tuple[BagItemView, ...]:
    return tuple(_bag_item(library, k, v) for k, v in sorted(counts.items()))


def inventory_view(
    library: ContentLibrary, char: CharacterState, *, in_battle: bool
) -> InventoryView | None:
    rules = economy_rules(library)
    if rules is None:
        return None
    problem = "戰鬥中" if in_battle else pouch_problem(library, char)
    total: dict[str, int] = {}
    for counts in (char.bag, char.pouch):
        for item_id, count in counts.items():
            found = _item(library, item_id)
            if found is not None and found.kind == "consumable":
                total[item_id] = total.get(item_id, 0) + count
    gear_problem = "戰鬥中" if in_battle else equip_problem(library, char)
    # OB-5（#150 第 7 點）：入門期不能換主手——背包裡的武器先標成不能換上（原因同動作被拒的那一句）
    main_hand = opening_limits(char).get("main_hand")
    gear = tuple(
        _gear_item(
            library, g, (main_hand if g.slot_type == "weapon" else None) or gear_problem, char
        )
        for g in char.gear
    )
    return InventoryView(
        bag=(*_views(library, char.bag), *gear),
        slots_used=slots_used(library, char.bag, len(char.gear)),
        slots_max=rules.bag_slots,
        pouch=_views(library, char.pouch),
        pouch_count=sum(char.pouch.values()),
        pouch_max=rules.pouch_slots,
        can_pouch=problem is None,
        pouch_problem_zh=problem,
        consumables=_views(library, total),
        equipped_zh=_equipped_lines(library, char),
        equipment=_equipment(library, char),
        gear_cards=tuple(
            gear_candidate(library, gear_run(char), g, cross_class=True) for g in char.gear
        ),
    )


def _equipment(library: ContentLibrary, char: CharacterState) -> tuple[HeroGearSlotOut, ...]:
    run = gear_run(char)
    return tuple(
        HeroGearSlotOut(
            slot=slot,
            slot_zh=SLOT_ZH[slot],
            item=None
            if (held := current_item(library, run, slot)) is None
            else item_info(library, held),
            opening_note_zh=None if held is None else opening_gear_note(library, char, held.id),
        )
        for slot in SLOTS
    )


def _rank_name(library: ContentLibrary, rank: AffinityRank) -> str:
    rules = affinity_rules(library)
    return rules.ranks[AFFINITY_RANKS.index(rank)].name_zh


def _npc_name(library: ContentLibrary, region: str, npc: str) -> str:
    table = library.world_event_content.npcs.get(region)
    card = None if table is None else table.npc_by_id().get(npc)
    return npc if card is None else card.name_zh


def shop_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    in_battle: bool,
) -> ShopView | None:
    """角色所在地點的店；沒有店為 ``None``。"""
    shop = shop_here(library, char)
    if shop is None:
        return None
    npc_name = _npc_name(library, char.region, shop.npc)
    trade_problem = (
        "戰鬥中"
        if in_battle
        else "還有沒處理的遭遇"
        if char.pending_encounter is not None
        else None
    )
    current = rank_of(library, char, shop.npc)
    items: list[ShopItemView] = []
    entries = [(s.item, s.rank, False) for s in shop.stock]
    entries += [(w.item, w.rank, True) for w in shop.weekly]
    for item_id, rank, weekly in entries:
        found = _item(library, item_id)
        if found is None:
            continue
        problem = trade_problem or buy_problem(
            library, world, char, shop, item_id, count=1, now=now
        )
        locked = rank is not None and not rank_at_least(current, rank)
        stock_zh = None
        if weekly:
            stock_zh = f"本週剩 {weekly_left(library, world, char, shop.id, item_id, now=now)} 個"
        items.append(
            ShopItemView(
                item=item_id,
                name_zh=found.name_zh,
                kind_zh=ITEM_KINDS[found.kind],
                description_zh=found.description_zh,
                price=shop_buy_price(world, shop.id, found.price),
                weekly=weekly,
                stock_zh=stock_zh,
                locked=locked,
                lock_zh=None
                if rank is None
                else f"{npc_name}好感度到{_rank_name(library, rank)}才賣",
                can_buy=problem is None,
                problem_zh=problem,
                battle_zh=_battle_zh(found),
            )
        )
    affinity_zh = None
    if shop.affinity is not None:
        left = shop_affinity_left(library, char, shop, now)
        affinity_zh = (
            f"每次消費{npc_name}好感度 +{shop.affinity.per_purchase}"
            f"（每天最多 +{shop.affinity.daily_max}，今天還能 +{left}）"
        )
    return ShopView(
        shop=shop.id,
        name_zh=shop.name_zh,
        npc=shop.npc,
        npc_name_zh=npc_name,
        rank_zh=_rank_name(library, current),
        affinity_zh=affinity_zh,
        items=tuple(items),
        can_trade=trade_problem is None,
        trade_problem_zh=trade_problem,
        price_notes_zh=shop_price_notes(library, world, shop.id),
    )


def _counts_zh(library: ContentLibrary, counts: Mapping[str, int]) -> str:
    return "、".join(f"{_name(library, k)} ×{v}" for k, v in sorted(counts.items())) or "空"


def _shop_name(library: ContentLibrary, shop_id: str) -> str:
    for table in library.world_economy.shops.values():
        found = table.shop_by_id().get(shop_id)
        if found is not None:
            return found.name_zh
    return shop_id


def economy_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """買、賣、腰包、用道具、得到貨幣的句子。"""
    if isinstance(event, CurrencyGainedEvent):
        if event.currency == "gold":
            return f"獲得 {event.amount} 金幣（共 {event.total}）。"
        if event.source == "shadow":
            return f"影子被借用的任務幣 +{event.amount}（共 {event.total}）。"
        if event.source.startswith(("bounty:", "daily_goal:")):  # 5F-1：懸賞、今日目標另有句子
            return f"任務幣共 {event.total}。"
        return f"獲得 {event.amount} 任務幣（完成任務，共 {event.total}）。"
    return _item_line(library, event)


def _item_line(library: ContentLibrary, event: WorldEvent) -> str | None:
    if isinstance(event, ItemBoughtEvent):
        shop = _shop_name(library, event.shop)
        name = _name(library, event.item)
        return f"在{shop}買了{name} ×{event.count}（−{event.gold_spent} 金幣，剩 {event.gold}）。"
    if isinstance(event, ItemSoldEvent):
        name = event.name_zh or _name(library, event.item)
        return f"賣掉{name} ×{event.count}（+{event.gold_gained} 金幣，共 {event.gold}）。"
    if isinstance(event, PouchChangedEvent):
        return f"腰包：{_counts_zh(library, event.pouch)}。"
    if isinstance(event, PouchUsedEvent):
        return f"這場用掉了：{_counts_zh(library, event.items)}。"
    if isinstance(event, ItemUsedEvent):
        return f"用了{_name(library, event.item)}：HP {event.hp}、法力 {event.mana}。"
    return _gear_line(library, event)


def _gear_line(library: ContentLibrary, event: WorldEvent) -> str | None:
    """掉落與換裝備的句子（Phase 5D-2）。"""
    if isinstance(event, LootGainedEvent):
        text = _loot_text(
            library,
            event.materials,
            event.gear_names,
            event.lost_materials,
            event.lost_gear_names,
        )
        waiting = _pending_text(library, event.pending_materials, event.pending_gear_names)
        return "".join(t for t in (text, waiting) if t) or None
    if isinstance(event, LootChosenEvent | LootAbandonedEvent):
        return _choice_line(library, event)
    if isinstance(event, ItemEquippedEvent):
        removed = f"，換下{'、'.join(event.removed)}" if event.removed else ""
        return f"{SLOT_ZH.get(event.slot, event.slot)}換上{event.name_zh}{removed}。"
    return None


def _loot_text(
    library: ContentLibrary,
    materials: Mapping[str, int],
    gear: tuple[str, ...],
    lost_materials: Mapping[str, int],
    lost_gear: tuple[str, ...],
) -> str | None:
    got = [f"{_name(library, k)} ×{v}" for k, v in sorted(materials.items())] + list(gear)
    lost = [f"{_name(library, k)} ×{v}" for k, v in sorted(lost_materials.items())]
    lost += list(lost_gear)
    parts = []
    if got:
        parts.append(f"掉落：{'、'.join(got)}。")
    if lost:
        parts.append(f"背包滿了，沒撿到：{'、'.join(lost)}。")
    return "".join(parts) or None


def _listing(library: ContentLibrary, counts: Mapping[str, int], names: tuple[str, ...]) -> str:
    return "、".join([f"{_name(library, k)} ×{v}" for k, v in sorted(counts.items())] + list(names))


def _pending_text(
    library: ContentLibrary, materials: Mapping[str, int], gear: tuple[str, ...]
) -> str | None:
    if not materials and not gear:
        return None
    return f"背包滿了，先選要丟哪件才收得下：{_listing(library, materials, gear)}。"


def _choice_line(library: ContentLibrary, event: LootChosenEvent | LootAbandonedEvent) -> str:
    if isinstance(event, LootAbandonedEvent):
        left = _listing(library, event.materials, event.gear_names)
        return f"上一場沒收下的戰利品留在原地：{left}。"
    parts = []
    if event.dropped_items or event.dropped_gear_names:
        parts.append(f"丟掉了{_listing(library, event.dropped_items, event.dropped_gear_names)}。")
    if event.materials or event.gear_names:
        parts.append(f"收下了{_listing(library, event.materials, event.gear_names)}。")
    return "".join(parts) or "戰利品整理好了。"


def pending_loot_view(library: ContentLibrary, char: CharacterState) -> PendingLootView | None:
    """背包滿了、等戰後結算選要丟哪件的戰利品（Phase 5D-2b）；沒有為 ``None``。"""
    loot = char.pending_loot
    rules = economy_rules(library)
    if loot is None or rules is None:
        return None
    bag = dict(char.bag)
    for item, count in loot.materials.items():
        bag[item] = bag.get(item, 0) + count
    over = slots_over(library, bag, len(char.gear) + len(loot.gear))
    rows = (
        *_views(library, loot.materials),
        *(_gear_item(library, g, "還沒收進背包") for g in loot.gear),
    )
    return PendingLootView(
        items=rows,
        over_slots=over,
        hint_zh=(
            f"背包滿了：勾選要丟的（新拿到的或背包裡原本的），騰出 {over} 格就能收下其他的。"
            "沒決定的在下一場打贏時留在原地。"
        ),
    )


def last_loot_line(library: ContentLibrary, last: LastBattle | None) -> str | None:
    """最近一次戰鬥的掉落（Phase 5D-2）；沒有掉落為 ``None``。"""
    if last is None or last.loot is None:
        return None
    loot = last.loot
    return _loot_text(library, loot.materials, loot.gear, loot.lost_materials, loot.lost_gear)
