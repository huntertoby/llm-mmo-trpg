"""貨幣、背包、腰包與商店（Phase 5D-1；``docs/phases/Phase5計畫.md`` 26.4）。

- **金幣**（08 8.15）：打贏戰鬥（:func:`battle_gold`）、賣東西；買消耗品、粗料、染料。
- **任務幣**：完成任務（:func:`after_step`）；朋友借用自己的影子時暫記在世界快照的影子紀錄，主人自己
  下一個世界動作時轉進角色（5C-2 留下的，代決 5D1-12）。
- **背包** 30 格（每種物品照疊數算格）、**腰包** 3 個（只放消耗品）；腰包的消耗品在戰鬥中是「道具
  技能」（:func:`pouch_skills`：1 AP、每個用一次、不佔技能欄位，8.17），用掉的戰後扣掉
  （:func:`spend_pouch`）。野外可以喝藥水（09 9.6.11 #113）。
- **商店**（8.26.1）：店在店主 NPC 的地點；只賣消耗品、粗料、染料與每週限量的區域特產（數量由賽季
  種子決定，每個角色各自算）；商品可有好感度門檻；每次 ``buy`` 算消費一次，店主好感度
  +``per_purchase``、每天最多 +``daily_max``（18.7.6 柳掌櫃 +2／每天 +4）。

純函式：不讀時間（``now`` 由呼叫者傳入）、不呼叫 LLM；限量數量用 ``{season_seed}:{region}:shop:…``
衍生的亂數，不耗角色的亂數串流。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Final

from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_economy import ITEM_KINDS, EconomyRules, ShopDef, WorldItemDef
from trpg.content.world_quests import AFFINITY_RANKS
from trpg.engine.state import BattleState
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import UnitId
from trpg.world.actions import QuestCompletedEvent, WorldEvent
from trpg.world.affinity import affinity_rules, change_affinity, rank_at_least, rank_of
from trpg.world.clock import refresh_day
from trpg.world.common import max_hp, max_mana
from trpg.world.economy_actions import (
    BuyAction,
    CurrencyGainedEvent,
    ItemBoughtEvent,
    ItemSoldEvent,
    ItemUsedEvent,
    PouchAction,
    PouchChangedEvent,
    PouchUsedEvent,
    SellAction,
    UseItemAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.growth import at_service
from trpg.world.inventory import add_items, check_room, remove_gear, remove_items, room_problem
from trpg.world.season import week_of
from trpg.world.state import CharacterState, CompanionAffinity, ShopPurchase, WorldState

__all__ = [
    "ECONOMY_ACTIONS",
    "ECONOMY_HANDLERS",
    "after_step",
    "apply_economy",
    "battle_gold",
    "buy_problem",
    "economy_rules",
    "gear_price",
    "item_def",
    "pouch_problem",
    "pouch_skills",
    "shop_affinity_left",
    "shop_here",
    "shop_location",
    "spend_pouch",
    "weekly_left",
    "weekly_limit",
]

ECONOMY_ACTIONS = (BuyAction, SellAction, PouchAction, UseItemAction)
"""經濟的世界動作（:func:`apply_economy` 分派）。"""


# ---------------------------------------------------------------------------
# 內容與查詢
# ---------------------------------------------------------------------------


def economy_rules(library: ContentLibrary) -> EconomyRules | None:
    """經濟規則；內容庫沒有 ``world/economy.yaml`` 時為 ``None``（經濟功能關閉）。"""
    return library.world_economy.rules


def _rules(library: ContentLibrary) -> EconomyRules:
    rules = economy_rules(library)
    if rules is None:
        raise WorldActionError("這個世界還沒有開放經濟（沒有 world/economy.yaml）")
    return rules


def item_def(library: ContentLibrary, item: str) -> WorldItemDef:
    found = library.world_economy.items.get(item)
    if found is None:
        raise WorldActionError(f"沒有物品 {item}")
    return found


def shop_location(library: ContentLibrary, region: str, shop: ShopDef) -> str | None:
    """店所在的地點（店主 NPC 的地點）；人設卡沒有他時為 ``None``。"""
    table = library.world_event_content.npcs.get(region)
    npc = None if table is None else table.npc_by_id().get(shop.npc)
    return None if npc is None else npc.location


def shop_here(library: ContentLibrary, char: CharacterState) -> ShopDef | None:
    """角色所在地點的店（第一家；沒有為 ``None``）。"""
    table = library.world_economy.shops.get(char.region)
    if table is None or economy_rules(library) is None:
        return None
    for shop in table.shops:
        if shop_location(library, char.region, shop) == char.location:
            return shop
    return None


def _shop(library: ContentLibrary, char: CharacterState, shop_id: str) -> ShopDef:
    _rules(library)
    table = library.world_economy.shops.get(char.region)
    shop = None if table is None else table.shop_by_id().get(shop_id)
    if shop is None:
        raise WorldActionError(f"這一區沒有店 {shop_id}")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能買賣")
    if shop_location(library, char.region, shop) != char.location:
        raise WorldActionError(f"{shop.name_zh}不在這裡")
    return shop


def weekly_limit(
    library: ContentLibrary, world: WorldState, region: str, shop: str, item: str, *, now: int
) -> int:
    """本週這家店的限量商品有幾個（同週大家相同；不耗角色亂數，代決 5D1-6）。"""
    table = library.world_economy.shops.get(region)
    found = None if table is None else table.shop_by_id().get(shop)
    weekly = None if found is None else found.weekly_of(item)
    if weekly is None:
        return 0
    week = week_of(library, world, now)
    rng = Rng(fnv1a64(f"{world.season_seed}:{region}:shop:{shop}:{week}:{item}".encode()))
    return rng.randint(weekly.min, weekly.max)


def _bought_this_week(char: CharacterState, shop: str, item: str, week: int) -> int:
    for row in char.shop_week:
        if row.shop == shop and row.item == item and row.week == week:
            return row.bought
    return 0


def weekly_left(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    shop: str,
    item: str,
    *,
    now: int,
) -> int:
    """這個角色本週還能買幾個限量商品。"""
    week = week_of(library, world, now)
    limit = weekly_limit(library, world, char.region, shop, item, now=now)
    return max(0, limit - _bought_this_week(char, shop, item, week))


def shop_affinity_left(
    library: ContentLibrary, char: CharacterState, shop: ShopDef, now: int
) -> int:
    """今天在這家店消費還能加多少店主好感度。"""
    if shop.affinity is None:
        return 0
    row = char.shop_affinity.get(shop.npc)
    gained = row.gained if row is not None and row.day == refresh_day(now) else 0
    return max(0, shop.affinity.daily_max - gained)


def buy_problem(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    shop: ShopDef,
    item: str,
    *,
    count: int,
    now: int,
) -> str | None:
    """不能買的原因（地點與遭遇另外檢查）；可以買時為 ``None``。"""
    problem = _stock_problem(library, world, char, shop, item, count=count, now=now)
    if problem is not None:
        return problem
    found = item_def(library, item)
    cost = found.price * count
    if char.gold < cost:
        return f"金幣不夠（要 {cost}，有 {char.gold}）"
    return _room_problem(library, char, found, count)


def _stock_problem(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    shop: ShopDef,
    item: str,
    *,
    count: int,
    now: int,
) -> str | None:
    """店有沒有賣、好感度門檻（常駐與限購都看 ``rank``）、本週限購剩餘。"""
    stock = shop.stock_of(item)
    weekly = shop.weekly_of(item)
    if stock is None and weekly is None:
        return f"{shop.name_zh}不賣這個"
    rank = stock.rank if stock is not None else weekly.rank if weekly is not None else None
    if rank is not None and not rank_at_least(rank_of(library, char, shop.npc), rank):
        name = affinity_rules(library).ranks[AFFINITY_RANKS.index(rank)].name_zh
        return f"店主好感度到{name}才賣"
    if weekly is not None:
        left = weekly_left(library, world, char, shop.id, item, now=now)
        if left < count:
            return "本週已經賣完了" if left == 0 else f"本週只剩 {left} 個"
    return None


def _room_problem(
    library: ContentLibrary, char: CharacterState, item: WorldItemDef, count: int
) -> str | None:
    """放不放得下：補給看補給上限（20.1：直接加補給、不進背包），其他看背包格數。"""
    if item.kind == "supply":
        cap = library.world_rules.supplies.max if library.world_rules is not None else 0
        if char.supplies + item.supplies * count > cap:
            return f"補給最多 {cap}（現在 {char.supplies}）"
        return None
    if room_problem(library, add_items(char.bag, {item.id: count}), len(char.gear)) is None:
        return None
    return "背包放不下"


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


def apply_economy(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: BuyAction | SellAction | PouchAction | UseItemAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """經濟的世界動作（不動世界快照；依 :data:`ECONOMY_HANDLERS` 分派）。"""
    return ECONOMY_HANDLERS[type(action)](library, world, char, action, now)


def _buy(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: BuyAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    shop = _shop(library, char, action.shop)
    problem = buy_problem(library, world, char, shop, action.item, count=action.count, now=now)
    if problem is not None:
        raise WorldActionError(problem)
    found = item_def(library, action.item)
    cost = found.price * action.count
    update: dict[str, object] = {"gold": char.gold - cost}
    if found.kind == "supply":  # 20.1：補給直接加在角色上（代決 5D1-7）
        update["supplies"] = char.supplies + found.supplies * action.count
    else:
        update["bag"] = add_items(char.bag, {action.item: action.count})
    if shop.weekly_of(action.item) is not None:
        week = week_of(library, world, now)
        bought = _bought_this_week(char, shop.id, action.item, week) + action.count
        rows = [r for r in char.shop_week if (r.shop, r.item) != (shop.id, action.item)]
        rows.append(ShopPurchase(shop=shop.id, item=action.item, week=week, bought=bought))
        update["shop_week"] = tuple(sorted(rows, key=lambda r: (r.shop, r.item)))
    char = char.model_copy(update=update)
    events: list[WorldEvent] = [
        ItemBoughtEvent(
            shop=shop.id, item=action.item, count=action.count, gold_spent=cost, gold=char.gold
        )
    ]
    left = shop_affinity_left(library, char, shop, now)
    if shop.affinity is not None and left > 0:  # 消費一次 +per_purchase、每天上限（18.7.6）
        delta = min(shop.affinity.per_purchase, left)
        row = char.shop_affinity.get(shop.npc)
        day = refresh_day(now)
        gained = (row.gained if row is not None and row.day == day else 0) + delta
        rows_aff = {**char.shop_affinity, shop.npc: CompanionAffinity(day=day, gained=gained)}
        char = char.model_copy(update={"shop_affinity": rows_aff})
        char, changed = change_affinity(library, char, shop.npc, delta, f"shop:{shop.id}")
        events.append(changed)
    return char, tuple(events)


def _sell(
    library: ContentLibrary, char: CharacterState, action: SellAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    shop = _shop(library, char, action.shop)
    piece = next((g for g in char.gear if g.id == action.item), None)
    if piece is not None:  # 裝備回收（20.1；5D-2）
        return _sell_gear(library, char, shop, piece, action.count)
    have = char.bag.get(action.item, 0)
    if have < action.count:
        raise WorldActionError(f"背包裡只有 {have} 個（腰包裡的要先拿出來）")
    found = item_def(library, action.item)
    rules = _rules(library)
    if not rules.sellable(found.kind):
        raise WorldActionError(f"{found.name_zh}不能賣（{ITEM_KINDS[found.kind]}不收）")
    gained = rules.sell_price(found.price) * action.count
    char = char.model_copy(
        update={
            "gold": char.gold + gained,
            "bag": remove_items(char.bag, {action.item: action.count}),
        }
    )
    event = ItemSoldEvent(
        shop=shop.id, item=action.item, count=action.count, gold_gained=gained, gold=char.gold
    )
    return char, (event,)


def gear_price(library: ContentLibrary, item: ItemDef) -> int | None:
    """裝備回收價：物品等級 × 稀有度係數（``loot.yaml``，20.1）；不收為 ``None``（代決 5D2-8）。"""
    rules = library.world_loot
    return None if rules is None else rules.sell_price(item.rarity, item.item_level)


def _sell_gear(
    library: ContentLibrary, char: CharacterState, shop: ShopDef, piece: ItemDef, count: int
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    if count != 1:
        raise WorldActionError("裝備一次賣一件")
    price = gear_price(library, piece)
    if price is None:
        raise WorldActionError(f"{piece.name_zh}不能賣（初始裝備與傳說不收）")
    char = remove_gear(char, [piece.id])  # 5D-3 的改動紀錄一併刪掉
    char = char.model_copy(update={"gold": char.gold + price})
    event = ItemSoldEvent(
        shop=shop.id,
        item=piece.id,
        count=1,
        gold_gained=price,
        gold=char.gold,
        name_zh=piece.name_zh,
    )
    return char, (event,)


def pouch_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """不能整理腰包的原因（城鎮或營火、沒有遭遇）；可以時為 ``None``。"""
    if economy_rules(library) is None:
        return "還沒有開放"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if not at_service(library, char):
        return "只有城鎮與營火能整理腰包"
    return None


def _pouch(
    library: ContentLibrary, char: CharacterState, action: PouchAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    rules = _rules(library)
    problem = pouch_problem(library, char)
    if problem is not None:
        raise WorldActionError(problem)
    wanted = dict(sorted(action.items.items()))
    for item, count in wanted.items():
        if item_def(library, item).kind != "consumable":
            raise WorldActionError(f"腰包只能放消耗品：{item}")
        if count < 1:
            raise WorldActionError("腰包的個數至少 1")
    total = sum(wanted.values())
    if total > rules.pouch_slots:
        raise WorldActionError(f"腰包最多 {rules.pouch_slots} 個（要放 {total} 個）")
    bag = dict(char.bag)
    for item, count in char.pouch.items():  # 舊腰包先放回背包
        bag = add_items(bag, {item: count})
    for item, count in wanted.items():
        if bag.get(item, 0) < count:
            raise WorldActionError(
                f"{item_def(library, item).name_zh}不夠（有 {bag.get(item, 0)} 個）"
            )
        bag = remove_items(bag, {item: count})
    check_room(library, bag, len(char.gear))
    char = char.model_copy(update={"bag": bag, "pouch": wanted})
    return char, (PouchChangedEvent(pouch=wanted),)


def _use(
    library: ContentLibrary, char: CharacterState, action: UseItemAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    _rules(library)
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇（戰鬥中用道具要在戰場上用）")
    item = item_def(library, action.item)
    if not item.field_usable:
        raise WorldActionError(f"{item.name_zh}不能在野外使用")
    top_hp, top_mana = max_hp(library, char), max_mana(library, char)
    gain_hp = max(1, top_hp * item.field_hp_permille // 1000) if item.field_hp_permille else 0
    gain_mana = (
        max(1, top_mana * item.field_mana_permille // 1000) if item.field_mana_permille else 0
    )
    hp = min(top_hp, char.hp + gain_hp)
    mana = min(top_mana, char.mana + gain_mana)
    if hp == char.hp and mana == char.mana:
        raise WorldActionError(f"現在用{item.name_zh}沒有效果（已經是滿的）")
    if char.bag.get(item.id, 0) > 0:
        update: dict[str, object] = {"bag": remove_items(char.bag, {item.id: 1})}
    elif char.pouch.get(item.id, 0) > 0:
        update = {"pouch": remove_items(char.pouch, {item.id: 1})}
    else:
        raise WorldActionError(f"沒有{item.name_zh}")
    char = char.model_copy(update={**update, "hp": hp, "mana": mana})
    return char, (ItemUsedEvent(item=item.id, hp=hp, mana=mana),)


type EconomyHandler = Callable[
    [ContentLibrary, WorldState, CharacterState, Any, int],
    tuple[CharacterState, tuple[WorldEvent, ...]],
]
ECONOMY_HANDLERS: Final[Mapping[type, EconomyHandler]] = {
    BuyAction: _buy,
    SellAction: lambda library, _world, char, action, _now: _sell(library, char, action),
    PouchAction: lambda library, _world, char, action, _now: _pouch(library, char, action),
    UseItemAction: lambda library, _world, char, action, _now: _use(library, char, action),
}
"""經濟動作種類 → 處理 ``(library, world, char, action, now) → (char, events)``（5D-R1）。"""


# ---------------------------------------------------------------------------
# 戰鬥：道具技能與戰後
# ---------------------------------------------------------------------------


def pouch_skills(library: ContentLibrary, char: CharacterState) -> tuple[SkillDef, ...]:
    """腰包的道具技能（依物品 ID 排序；每場可用次數＝個數，8.17）。"""
    if economy_rules(library) is None:
        return ()
    skills: list[SkillDef] = []
    for item_id, count in sorted(char.pouch.items()):
        item = library.world_economy.items.get(item_id)
        if item is None or item.skill is None:
            continue
        cost = item.skill.cost.model_copy(update={"uses_per_battle": count})
        skills.append(item.skill.model_copy(update={"cost": cost}))
    return tuple(skills)


def spend_pouch(
    library: ContentLibrary, char: CharacterState, state: BattleState, hero_id: UnitId
) -> tuple[CharacterState, list[WorldEvent]]:
    """戰後：主角用掉的道具（戰鬥結束狀態的 ``skill_uses``）從腰包扣（勝負都扣）。"""
    if not char.pouch:
        return char, []
    uses = state.units[hero_id].skill_uses
    by_skill = library.world_economy.item_skills()
    used: dict[str, int] = {}
    pouch = dict(char.pouch)
    for skill_id, n in sorted(uses.items()):
        item = by_skill.get(skill_id)
        if item is None or n <= 0 or item.id not in pouch:
            continue
        spent = min(n, pouch[item.id])
        used[item.id] = spent
        pouch = remove_items(pouch, {item.id: spent})
    if not used:
        return char, []
    char = char.model_copy(update={"pouch": pouch})
    return char, [PouchUsedEvent(items=dict(sorted(used.items())))]


def battle_gold(
    library: ContentLibrary, char: CharacterState, *, elite: bool, level: int
) -> tuple[CharacterState, list[WorldEvent]]:
    """打贏一場的金幣（8.15；代決 5D1-3）。"""
    rules = economy_rules(library)
    if rules is None:
        return char, []
    amount = rules.battle_gold.gold_for(elite=elite, level=level)
    if amount <= 0:
        return char, []
    char = char.model_copy(update={"gold": char.gold + amount})
    event = CurrencyGainedEvent(currency="gold", amount=amount, total=char.gold, source="battle")
    return char, [event]


# ---------------------------------------------------------------------------
# 每個動作之後：任務幣、影子的任務幣
# ---------------------------------------------------------------------------


def _quest_kind(library: ContentLibrary, quest: str) -> str | None:
    for table in library.world_quests.quests.values():
        found = table.quest_by_id().get(quest)
        if found is not None:
            return found.kind
    return None


def _coins(char: CharacterState, amount: int, source: str) -> tuple[CharacterState, WorldEvent]:
    char = char.model_copy(update={"quest_coins": char.quest_coins + amount})
    event = CurrencyGainedEvent(
        currency="quest_coins", amount=amount, total=char.quest_coins, source=source
    )
    return char, event


def after_step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    events: Iterable[WorldEvent],
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    """每個世界動作的最後：完成任務給任務幣（代決 5D1-4）；影子被借用累計的任務幣轉進主人角色
    （代決 5D1-12）。沒有經濟規則時不做任何事。"""
    rules = economy_rules(library)
    if rules is None:
        return world, char, []
    extra: list[WorldEvent] = []
    for event in events:
        if not isinstance(event, QuestCompletedEvent):
            continue
        kind = _quest_kind(library, event.quest)
        amount = 0 if kind is None else rules.quest_coins.coins_for(event.quest, kind)
        if amount > 0:
            char, gained = _coins(char, amount, f"quest:{event.quest}")
            extra.append(gained)
    record = world.shadow_of(char.character_id)
    if record is not None and record.coins > record.coins_claimed:
        char, gained = _coins(char, record.coins - record.coins_claimed, "shadow")
        extra.append(gained)
        claimed = record.model_copy(update={"coins_claimed": record.coins})
        shadows = tuple(claimed if s is record else s for s in world.shadows)
        world = world.model_copy(update={"shadows": shadows})
    return world, char, extra
