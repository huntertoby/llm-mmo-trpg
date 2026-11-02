"""大世界經濟的顯示資料（Phase 5D-1；``docs/phases/Phase5計畫.md`` 25.5）：金幣與任務幣、背包與
腰包、這裡的店、事件句子。規則一律呼叫 :mod:`trpg.world.economy`，這裡只組裝文字。"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.api.world_economy_schemas import (
    BagItemView,
    InventoryView,
    ShopItemView,
    ShopView,
    WalletView,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_economy import ITEM_KINDS, WorldItemDef
from trpg.content.world_quests import AFFINITY_RANKS, AffinityRank
from trpg.world.actions import WorldEvent
from trpg.world.affinity import affinity_rules, rank_at_least, rank_of
from trpg.world.economy import (
    bag_slots_used,
    buy_problem,
    economy_rules,
    pouch_problem,
    shop_affinity_left,
    shop_here,
    weekly_left,
)
from trpg.world.economy_actions import (
    CurrencyGainedEvent,
    ItemBoughtEvent,
    ItemSoldEvent,
    ItemUsedEvent,
    PouchChangedEvent,
    PouchUsedEvent,
)
from trpg.world.state import CharacterState, WorldState

__all__ = ["economy_event_line", "inventory_view", "shop_view", "wallet_view"]


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
            field_usable=False,
        )
    return BagItemView(
        item=item_id,
        name_zh=found.name_zh,
        kind_zh=ITEM_KINDS[found.kind],
        count=count,
        description_zh=found.description_zh,
        sell_price=rules.sell_price(found.price),
        field_usable=found.field_usable,
        use_zh=_use_zh(found),
        battle_zh=_battle_zh(found),
    )


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
    return InventoryView(
        bag=_views(library, char.bag),
        slots_used=bag_slots_used(library, char.bag),
        slots_max=rules.bag_slots,
        pouch=_views(library, char.pouch),
        pouch_count=sum(char.pouch.values()),
        pouch_max=rules.pouch_slots,
        can_pouch=problem is None,
        pouch_problem_zh=problem,
        consumables=_views(library, total),
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
    entries += [(w.item, None, True) for w in shop.weekly]
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
                price=found.price,
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
        return f"獲得 {event.amount} 任務幣（完成任務，共 {event.total}）。"
    return _item_line(library, event)


def _item_line(library: ContentLibrary, event: WorldEvent) -> str | None:
    if isinstance(event, ItemBoughtEvent):
        shop = _shop_name(library, event.shop)
        name = _name(library, event.item)
        return f"在{shop}買了{name} ×{event.count}（−{event.gold_spent} 金幣，剩 {event.gold}）。"
    if isinstance(event, ItemSoldEvent):
        name = _name(library, event.item)
        return f"賣掉{name} ×{event.count}（+{event.gold_gained} 金幣，共 {event.gold}）。"
    if isinstance(event, PouchChangedEvent):
        return f"腰包：{_counts_zh(library, event.pouch)}。"
    if isinstance(event, PouchUsedEvent):
        return f"這場用掉了：{_counts_zh(library, event.items)}。"
    if isinstance(event, ItemUsedEvent):
        return f"用了{_name(library, event.item)}：HP {event.hp}、法力 {event.mana}。"
    return None
