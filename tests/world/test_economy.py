"""貨幣、背包、腰包與商店（Phase 5D-1；``docs/phases/Phase5計畫.md`` 25.4）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import (
    AffinityChangedEvent,
    QuestCompletedEvent,
    TravelAction,
)
from trpg.world.economy import (
    after_step,
    battle_gold,
    weekly_left,
    weekly_limit,
)
from trpg.world.economy_actions import (
    BuyAction,
    CurrencyGainedEvent,
    ItemBoughtEvent,
    ItemSoldEvent,
    ItemUsedEvent,
    PouchAction,
    PouchChangedEvent,
    SellAction,
    UseItemAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.inventory import slots_used
from trpg.world.shadows import shadow_snapshot, with_shadow
from trpg.world.state import CharacterState, LocationRef, ShadowRecord
from trpg.world.step import max_hp, max_mana, world_step

MakeChar = Callable[..., CharacterState]
DAY = 86_400
WEEK = 7 * DAY
LIU = "shopkeeper_liu"
SHOP = "shop_liu"
PILL = "item_hp_potion_small"


def _act(library: ContentLibrary, char: CharacterState, action: object, now: int = NOON):  # type: ignore[no-untyped-def]
    return world_step(library, make_world(), char, action, now)  # type: ignore[arg-type]


def _rich(make_char: MakeChar, gold: int = 500, **updates: object) -> CharacterState:
    return make_char(gold=gold, **updates)


# ---------------------------------------------------------------------------
# 買
# ---------------------------------------------------------------------------


def test_new_character_starts_with_rules_gold(make_char: MakeChar) -> None:
    char = make_char()
    assert char.gold == 0 and char.quest_coins == 0 and char.bag == {} and char.pouch == {}


def test_buy_spends_gold_and_fills_bag(library: ContentLibrary, make_char: MakeChar) -> None:
    result = _act(library, _rich(make_char, 50), BuyAction(shop=SHOP, item=PILL, count=2))
    char = result.char
    assert char.gold == 10 and char.bag == {PILL: 2}
    bought = next(e for e in result.events if isinstance(e, ItemBoughtEvent))
    assert bought == ItemBoughtEvent(shop=SHOP, item=PILL, count=2, gold_spent=40, gold=10)


def test_buy_problems(library: ContentLibrary, make_char: MakeChar) -> None:
    rich = _rich(make_char)
    with pytest.raises(WorldActionError, match="金幣不夠"):
        _act(library, make_char(gold=19), BuyAction(shop=SHOP, item=PILL))
    with pytest.raises(WorldActionError, match="不在這裡"):
        _act(
            library,
            rich.model_copy(update={"location": "ferry_steps"}),
            BuyAction(shop=SHOP, item=PILL),
        )
    encounter = rich.model_copy(update={"pending_encounter": make_encounter("ferry_steps")})
    with pytest.raises(WorldActionError, match="遭遇"):
        _act(library, encounter, BuyAction(shop=SHOP, item=PILL))
    with pytest.raises(WorldActionError, match="不賣"):
        _act(library, rich, BuyAction(shop=SHOP, item="item_nothing"))
    with pytest.raises(WorldActionError, match="沒有店"):
        _act(library, rich, BuyAction(shop="shop_nobody", item=PILL))


def test_bag_full(library: ContentLibrary, make_char: MakeChar) -> None:
    # 粗料一格 20 個：29 格滿＋1 格剩 0 → 再買一顆藥要第 31 格
    full = {"item_coarse_material": 20 * 30}
    char = _rich(make_char, bag=full)
    assert slots_used(library, char.bag) == 30
    with pytest.raises(WorldActionError, match="背包放不下"):
        _act(library, char, BuyAction(shop=SHOP, item=PILL))


def test_friendly_gate(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="友善才賣"):
        _act(library, _rich(make_char), BuyAction(shop=SHOP, item="item_mist_flask"))
    friendly = _rich(make_char, affinity={LIU: 20})
    char = _act(library, friendly, BuyAction(shop=SHOP, item="item_mist_flask")).char
    assert char.bag == {"item_mist_flask": 1}


def test_weekly_specialty(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    limit = weekly_limit(library, world, "cloud_ridge", SHOP, "item_green_bamboo", now=NOON)
    assert limit == 5  # 20.1：每週限購 5
    # 同一週任何時間相同、和角色無關
    assert (
        weekly_limit(library, world, "cloud_ridge", SHOP, "item_green_bamboo", now=NOON + 3 * DAY)
        == limit
    )
    char = _rich(make_char, 1000)
    rng_before = dict(char.rng_counters)
    char = _act(library, char, BuyAction(shop=SHOP, item="item_green_bamboo", count=limit)).char
    assert char.rng_counters == rng_before  # 不耗角色亂數
    assert char.bag["item_green_bamboo"] == limit
    assert weekly_left(library, world, char, SHOP, "item_green_bamboo", now=NOON) == 0
    with pytest.raises(WorldActionError, match="賣完"):
        _act(library, char, BuyAction(shop=SHOP, item="item_green_bamboo"))
    # 下一週重新進貨
    later = NOON + WEEK
    left = weekly_left(library, world, char, SHOP, "item_green_bamboo", now=later)
    assert left == weekly_limit(library, world, "cloud_ridge", SHOP, "item_green_bamboo", now=later)
    assert left >= 2
    more = _act(library, char, BuyAction(shop=SHOP, item="item_green_bamboo"), later).char
    assert more.bag["item_green_bamboo"] == limit + 1
    # 其他角色同一週各自算
    other = _rich(make_char, 1000, character_id="bob")
    assert weekly_left(library, world, other, SHOP, "item_green_bamboo", now=NOON) == limit


def test_neutral_gate(library: ContentLibrary, make_char: MakeChar) -> None:
    cold = _rich(make_char, affinity={LIU: -10})  # 冷淡：中立門檻的中回復藥、青竹節不賣（20.1）
    for item in ("item_hp_potion_medium", "item_green_bamboo"):
        with pytest.raises(WorldActionError, match="中立才賣"):
            _act(library, cold, BuyAction(shop=SHOP, item=item))
    neutral = _act(library, _rich(make_char), BuyAction(shop=SHOP, item="item_hp_potion_medium"))
    assert neutral.char.bag == {"item_hp_potion_medium": 1}


def test_buy_supplies(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _rich(make_char, 100, supplies=5)
    result = _act(library, char, BuyAction(shop=SHOP, item="item_supplies", count=3))
    assert result.char.supplies == 8 and result.char.gold == 70 and result.char.bag == {}
    with pytest.raises(WorldActionError, match="補給最多 10"):
        _act(library, result.char, BuyAction(shop=SHOP, item="item_supplies", count=3))


# ---------------------------------------------------------------------------
# 柳掌櫃好感度（18.7.6：消費一次 +2、每天最多 +4）
# ---------------------------------------------------------------------------


def _liu_changes(events: object) -> list[AffinityChangedEvent]:
    return [e for e in events if isinstance(e, AffinityChangedEvent) and e.npc == LIU]  # type: ignore[attr-defined]


def test_shop_affinity_daily_cap(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _rich(make_char)
    first = _act(library, char, BuyAction(shop=SHOP, item=PILL, count=3))
    assert [e.delta for e in _liu_changes(first.events)] == [2]  # 一次 buy＝一次消費，不論個數
    assert _liu_changes(first.events)[0].source == "shop:shop_liu"
    second = _act(library, first.char, BuyAction(shop=SHOP, item=PILL))
    third = _act(library, second.char, BuyAction(shop=SHOP, item=PILL))
    assert [e.delta for e in _liu_changes(second.events)] == [2]
    assert _liu_changes(third.events) == []  # 今天已 +4
    assert third.char.affinity[LIU] == 4
    sold = _act(library, third.char, SellAction(shop=SHOP, item=PILL), NOON + DAY)
    assert _liu_changes(sold.events) == []  # 賣東西不算消費
    tomorrow = _act(library, sold.char, BuyAction(shop=SHOP, item=PILL), NOON + DAY)
    assert [e.delta for e in _liu_changes(tomorrow.events)] == [2]
    assert tomorrow.char.affinity[LIU] == 6


# ---------------------------------------------------------------------------
# 賣、腰包、野外使用
# ---------------------------------------------------------------------------


def test_sell(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(bag={PILL: 3, "item_coarse_material": 1})
    result = _act(library, char, SellAction(shop=SHOP, item=PILL, count=2))
    assert result.char.gold == 20 and result.char.bag == {PILL: 1, "item_coarse_material": 1}
    assert any(isinstance(e, ItemSoldEvent) and e.gold_gained == 20 for e in result.events)
    with pytest.raises(WorldActionError, match="不能賣"):  # 20.1：材料不能賣
        _act(library, char, SellAction(shop=SHOP, item="item_coarse_material"))
    with pytest.raises(WorldActionError, match="只有"):
        _act(library, char, SellAction(shop=SHOP, item=PILL, count=4))
    pouch_only = make_char(pouch={PILL: 1})
    with pytest.raises(WorldActionError, match="腰包"):
        _act(library, pouch_only, SellAction(shop=SHOP, item=PILL))


def test_pouch(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(bag={PILL: 3, "item_oil_flask": 2, "item_coarse_material": 1})
    result = _act(library, char, PouchAction(items={PILL: 2, "item_oil_flask": 1}))
    assert result.char.pouch == {"item_oil_flask": 1, PILL: 2}
    assert result.char.bag == {"item_coarse_material": 1, "item_oil_flask": 1, PILL: 1}
    assert isinstance(result.events[0], PouchChangedEvent)
    # 換一組：舊的先放回背包
    swapped = _act(library, result.char, PouchAction(items={"item_oil_flask": 2})).char
    assert swapped.pouch == {"item_oil_flask": 2}
    assert swapped.bag == {"item_coarse_material": 1, PILL: 3}
    emptied = _act(library, swapped, PouchAction(items={})).char
    assert emptied.pouch == {} and emptied.bag == char.bag
    with pytest.raises(WorldActionError, match="最多 3"):
        _act(library, char, PouchAction(items={PILL: 3, "item_oil_flask": 1}))
    with pytest.raises(WorldActionError, match="只能放消耗品"):
        _act(library, char, PouchAction(items={"item_coarse_material": 1}))
    with pytest.raises(WorldActionError, match="不夠"):
        _act(library, char, PouchAction(items={"item_fire_flask": 1}))
    field = char.model_copy(update={"location": "ferry_steps"})
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        _act(library, field, PouchAction(items={PILL: 1}))
    camp = field.model_copy(
        update={"camped_at": LocationRef(region="cloud_ridge", location="ferry_steps")}
    )
    assert _act(library, camp, PouchAction(items={PILL: 1})).char.pouch == {PILL: 1}


def test_use_item_in_field(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char(bag={PILL: 1, "item_mana_potion": 1}, pouch={PILL: 1})
    top = max_hp(library, char)
    hurt = char.model_copy(update={"hp": 1, "location": "ferry_steps"})
    result = _act(library, hurt, UseItemAction(item=PILL))
    assert result.char.hp == min(top, 1 + top * 200 // 1000)
    assert result.char.bag == {"item_mana_potion": 1} and result.char.pouch == {PILL: 1}
    assert isinstance(result.events[0], ItemUsedEvent)
    again = _act(library, result.char, UseItemAction(item=PILL)).char
    assert again.pouch == {}  # 背包沒有就用腰包的
    with pytest.raises(WorldActionError, match="沒有效果"):
        _act(library, char, UseItemAction(item="item_mana_potion"))  # 法力已滿
    low_mana = char.model_copy(update={"mana": 0})
    used = _act(library, low_mana, UseItemAction(item="item_mana_potion")).char
    assert used.mana == max(1, max_mana(library, char) * 250 // 1000)
    with pytest.raises(WorldActionError, match="不能在野外使用"):
        _act(
            library,
            make_char(bag={"item_oil_flask": 1}, hp=1),
            UseItemAction(item="item_oil_flask"),
        )
    with pytest.raises(WorldActionError, match="沒有"):
        _act(library, make_char(hp=1), UseItemAction(item=PILL))
    encounter = hurt.model_copy(update={"pending_encounter": make_encounter("ferry_steps")})
    with pytest.raises(WorldActionError, match="遭遇"):
        _act(library, encounter, UseItemAction(item=PILL))


# ---------------------------------------------------------------------------
# 金幣與任務幣
# ---------------------------------------------------------------------------


def test_battle_gold_values(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert battle_gold(library, char, elite=False, level=1)[0].gold == 15
    assert battle_gold(library, char, elite=True, level=1)[0].gold == 45
    assert battle_gold(library, char, elite=False, level=5)[0].gold == 21  # 15 × 1.4
    _, events = battle_gold(library, char, elite=False, level=1)
    assert events == [CurrencyGainedEvent(currency="gold", amount=15, total=15, source="battle")]


def test_quest_completion_gives_coins(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    world = make_world()
    _, paid, events = after_step(library, world, char, [QuestCompletedEvent(quest="starter_ferry")])
    assert paid.quest_coins == 2
    assert events == [
        CurrencyGainedEvent(currency="quest_coins", amount=2, total=2, source="quest:starter_ferry")
    ]
    _, main, _ = after_step(library, world, char, [QuestCompletedEvent(quest="main_mist_rift")])
    assert main.quest_coins == 3
    _, same, none = after_step(library, world, char, [])
    assert same is char and none == []


def test_shadow_coins_transfer_once(library: ContentLibrary, make_char: MakeChar) -> None:
    owner = make_char("alice")
    record = ShadowRecord(snapshot=shadow_snapshot(owner, NOON), coins=3)
    world = with_shadow(make_world(), record)
    world2, char, events = after_step(library, world, owner, [])
    assert char.quest_coins == 3
    assert events == [
        CurrencyGainedEvent(currency="quest_coins", amount=3, total=3, source="shadow")
    ]
    claimed = world2.shadow_of("alice")
    assert claimed is not None and claimed.coins == 3 and claimed.coins_claimed == 3
    _, again, more = after_step(library, world2, char, [])
    assert again.quest_coins == 3 and more == []
    # 別人的動作不轉
    _, bob, nothing = after_step(library, world, make_char("bob"), [])
    assert bob.quest_coins == 0 and nothing == []


def test_shadow_coins_through_world_step(library: ContentLibrary, make_char: MakeChar) -> None:
    owner = make_char("alice")
    world = with_shadow(make_world(), ShadowRecord(snapshot=shadow_snapshot(owner, NOON), coins=1))
    result = world_step(library, world, owner, TravelAction(to="ferry_steps"), NOON)
    assert result.char.quest_coins == 1
    assert result.events[-1] == CurrencyGainedEvent(
        currency="quest_coins", amount=1, total=1, source="shadow"
    )
