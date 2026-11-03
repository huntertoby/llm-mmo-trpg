"""灰燼荒原的接線（Phase 5F-5a；``docs/phases/Phase5計畫.md`` 39）：渡口、熔心坑開放、世界事件 #2
熔岩潰堤、村落的守點戰、灰燼之心的護甲調整與 Boss 戰、荒原世界日誌重播；5F-5b：熔岩潰堤失敗後
餘燼集商店買價 +20% 到季末。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_encounters import ArmorMod, ArmorMods
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import run_battle
from trpg.world.actions import (
    BattleEndedEvent,
    BattleStartedEvent,
    TeleportAction,
    TravelAction,
    WorldEvent,
)
from trpg.world.battle import armored, prepare_battle
from trpg.world.calendar import day_of
from trpg.world.economy import item_def, shop_buy_price
from trpg.world.economy_actions import BuyAction, ItemBoughtEvent, ItemSoldEvent, SellAction
from trpg.world.encounters import EncounterLineup, LineupMember, roll_lineup
from trpg.world.errors import WorldActionError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.season_board import after_season_step, roll_season
from trpg.world.solutions import make_encounter
from trpg.world.state import (
    CharacterState,
    DailyActivity,
    EncounterResult,
    ThreadState,
    WorldState,
)
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]
DAY = 24 * 3600
REGION = "ashen_waste"
VILLAGES = ("red_sand_village", "ash_well_village", "iron_forge_village")
BOSS = "ashen_heart"
IRON_LADY = "shop_iron_lady"


def _day(n: int) -> int:
    """賽季第 ``n`` 天的中午。"""
    return NOON + (n - 1) * DAY


def _ashen(
    make_char: MakeChar, location: str = "ember_market", **updates: object
) -> CharacterState:
    return make_char(
        region=REGION, location=location, visited_towns=("cloud_ridge", REGION), **updates
    )


def _won_at(location: str, *, won: bool = True) -> list[WorldEvent]:
    lineup = EncounterLineup(
        region=REGION,
        location=location,
        group="village_raid_light",
        members=(LineupMember(unit="ember_lizard"), LineupMember(unit="ember_lizard")),
    )
    started = BattleStartedEvent(
        location=location,
        battle_map="open_plain",
        region=REGION,
        lineup=lineup,
        enemy_level=6,
        weather="clear",
        hero_hp=40,
        fatigued=False,
    )
    ended = BattleEndedEvent(
        won=won, end_reason=None, rounds=3, hp=30, mana=5, xp_gained=100, level=6
    )
    return [started, ended]


def _encounter(location: str, **updates: object) -> EncounterResult:
    data: dict[str, object] = {
        "region": REGION,
        "location": location,
        "level": 9,
        "battle_map": "molten_heart_pit" if location == "molten_heart_pit" else None,
        "battle_seed": 7,
        "weather": "clear",
        "day_phase": "day",
        "at": NOON,
    }
    data.update(updates)
    return EncounterResult.model_validate(data)


# ---------------------------------------------------------------------------
# 渡口與熔心坑
# ---------------------------------------------------------------------------


def test_ferries_connect_both_regions(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world(flags=("ashen_waste_open",))
    char = make_char(location="ashen_ferry")
    there = world_step(library, world, char, TeleportAction(region=REGION), NOON).char
    assert (there.region, there.location) == (REGION, "ember_market")
    assert REGION in there.visited_towns
    back_at_gate = there.model_copy(update={"location": "ash_ferry"})
    back = world_step(library, world, back_at_gate, TeleportAction(region="cloud_ridge"), NOON)
    assert (back.char.region, back.char.location) == ("cloud_ridge", "mist_ferry")


def test_heart_pit_opens_with_flag(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _ashen(make_char, "ruined_fortress")
    with pytest.raises(WorldActionError, match="還沒開放"):
        world_step(library, make_world(), char, TravelAction(to="molten_heart_pit"), NOON)
    opened = make_world(flags=("heart_pit_open",))
    moved = world_step(library, opened, char, TravelAction(to="molten_heart_pit"), NOON).char
    assert moved.location == "molten_heart_pit"


# ---------------------------------------------------------------------------
# 世界事件 #2 熔岩潰堤（19.9）
# ---------------------------------------------------------------------------


def _at_day(library: ContentLibrary, day: int, *, players: int | None = None) -> WorldState:
    world, _ = roll_season(library, make_world(), NOON)
    if players is not None:
        before = day_of(library, _day(day - 1))
        actors = tuple(sorted(f"a{i}" for i in range(players)))
        world, _ = roll_season(library, world, _day(day - 1))
        world = world.model_copy(update={"activity": (DailyActivity(day=before, actors=actors),)})
    world, _ = roll_season(library, world, _day(day))
    return world


def test_lava_breach_counts_only_village_wins(library: ContentLibrary, make_char: MakeChar) -> None:
    world = _at_day(library, 4)
    state = world.world_event("lava_breach")
    assert state is not None and state.status == "active" and state.target == 24
    char = _ashen(make_char)
    for events in (_won_at("scorched_outskirts"), _won_at("red_sand_village", won=False)):
        world, char, _ = after_season_step(library, world, char, events, now=_day(4), actor="a")
    for village in VILLAGES:
        world, char, _ = after_season_step(
            library, world, char, _won_at(village), now=_day(4), actor="a"
        )
    state = world.world_event("lava_breach")
    assert state is not None and state.progress == 3


def test_lava_breach_success_opens_pit_and_adds_keys(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = _at_day(library, 4, players=1)
    state = world.world_event("lava_breach")
    assert state is not None and state.target == 6  # 24 × 1 ÷ 8 ＝ 3 → 下限 1/4 ＝ 6
    char = _ashen(make_char)
    keys = world.seal_keys
    for _ in range(6):
        world, char, _ = after_season_step(
            library, world, char, _won_at("ash_well_village"), now=_day(4), actor="a"
        )
    state = world.world_event("lava_breach")
    assert state is not None and state.status == "succeeded"
    assert world.has_flag("heart_pit_open")
    assert world.seal_keys == keys + 5
    assert REGION not in world.level_bonus or world.level_bonus[REGION] == 1  # 只有霧潮入侵的 +1
    assert world.shop_price == {}


def test_lava_breach_failure_opens_pit_late_and_raises_level(library: ContentLibrary) -> None:
    early = _at_day(library, 7)
    assert not early.has_flag("heart_pit_open")
    world = _at_day(library, 8)
    state = world.world_event("lava_breach")
    assert state is not None and state.status == "failed"
    assert world.has_flag("heart_pit_open")
    assert world.level_bonus[REGION] == 2  # 霧潮入侵失敗 +1、熔岩潰堤失敗 +1
    assert world.shop_price == {IRON_LADY: 200}  # 5F-5b：餘燼集商店買價 +20% 到季末
    later = _at_day(library, 10)
    assert later.shop_price == {IRON_LADY: 200}  # 到季末都不會自己消失


def test_shop_price_rounds_up_and_only_affects_that_shop() -> None:
    world = make_world().model_copy(update={"shop_price": {IRON_LADY: 200}})
    assert shop_buy_price(world, IRON_LADY, 10) == 12
    assert shop_buy_price(world, IRON_LADY, 11) == 14  # 13.2 → 無條件進位
    assert shop_buy_price(world, IRON_LADY, 1) == 2
    assert shop_buy_price(world, "shop_liu", 11) == 11
    assert shop_buy_price(make_world(), IRON_LADY, 11) == 11


def test_iron_lady_charges_more_after_breach_failure(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    potion = "item_hp_potion_small"
    base = item_def(library, potion).price
    raised = make_world().model_copy(update={"shop_price": {IRON_LADY: 200}})
    char = _ashen(make_char, gold=500)
    plain = world_step(library, make_world(), char, BuyAction(shop=IRON_LADY, item=potion), NOON)
    step = world_step(library, raised, char, BuyAction(shop=IRON_LADY, item=potion, count=2), NOON)
    bought = next(e for e in step.events if isinstance(e, ItemBoughtEvent))
    assert plain.char.gold == 500 - base
    assert (
        bought.gold_spent == 2 * (-(-base * 1200 // 1000))
        and step.char.gold == 500 - bought.gold_spent
    )
    sold = world_step(library, raised, step.char, SellAction(shop=IRON_LADY, item=potion), NOON)
    gained = next(e for e in sold.events if isinstance(e, ItemSoldEvent))
    sold_plain = world_step(
        library, make_world(), step.char, SellAction(shop=IRON_LADY, item=potion), NOON
    )
    assert gained == next(e for e in sold_plain.events if isinstance(e, ItemSoldEvent))  # 賣價不變


# ---------------------------------------------------------------------------
# 遭遇：村落守點、灰燼之心的護甲
# ---------------------------------------------------------------------------


def test_village_encounters_are_defend(library: ContentLibrary, make_char: MakeChar) -> None:
    places = library.world_maps[REGION].location_by_id()
    char = _ashen(make_char)
    for village in VILLAGES:
        result, _ = make_encounter(library, make_world(), char, places[village], NOON)
        assert result.objective == "defend"
    plain, _ = make_encounter(library, make_world(), char, places["scorched_outskirts"], NOON)
    assert plain.objective is None
    forced, _ = make_encounter(
        library, make_world(), char, places["red_sand_village"], NOON, objective="escape"
    )
    assert forced.objective == "escape"  # 骨架的戰鬥解法優先


def _boss_armor(library: ContentLibrary, char: CharacterState, encounter: EncounterResult) -> int:
    (boss,) = armored(library, char, encounter, [library.unit(BOSS)])
    return boss.armor_bonus


def test_ashen_heart_armor_mods(library: ContentLibrary, make_char: MakeChar) -> None:
    base = library.unit(BOSS).armor_bonus
    char = _ashen(make_char, "molten_heart_pit")
    plain = _encounter("molten_heart_pit")
    assert _boss_armor(library, char, plain) == base
    hardened = _encounter("molten_heart_pit", world_flags=("ashen_heart_hardened",))
    assert _boss_armor(library, char, hardened) == base + 1
    thread = ThreadState(
        thread="convoy_intercepted",
        skeleton="ashen_convoy",
        region=REGION,
        created_at=NOON - 10,
        expires_at=NOON + 10,
    )
    stopped = char.model_copy(
        update={"story_flags": ("ashen_convoy_stopped",), "threads": (thread,)}
    )
    assert _boss_armor(library, stopped, hardened) == base - 1
    assert _boss_armor(library, stopped, plain) == base - 2
    expired = _encounter("molten_heart_pit", at=NOON + 10)  # 線頭在遇敵時刻已到期
    assert _boss_armor(library, stopped, expired) == base - 1
    other = [library.unit("ember_lizard")]
    assert armored(library, stopped, plain, other) == tuple(other)  # 只調灰燼之心


def test_armor_mods_clamp_and_schema() -> None:
    mods = ArmorMods(
        unit=BOSS,
        min_total=-3,
        max_total=1,
        mods=(
            ArmorMod(world_flag="a", amount=2),
            ArmorMod(story_flag="b", amount=-2),
            ArmorMod(thread="c", amount=-2),
        ),
    )
    assert mods.total(world_flags={"a"}, story_flags=(), threads=()) == 1
    assert mods.total(world_flags=(), story_flags={"b"}, threads={"c"}) == -3
    with pytest.raises(ValueError, match="恰好填"):
        ArmorMod(world_flag="a", story_flag="b", amount=1)
    with pytest.raises(ValueError, match="不可為 0"):
        ArmorMod(thread="c", amount=0)


def test_ashen_heart_boss_battle(library: ContentLibrary, make_char: MakeChar) -> None:
    encounter = _encounter("molten_heart_pit")
    lineup = roll_lineup(library, encounter)
    assert [m.unit for m in lineup.members] == [BOSS, "ember_lizard", "ember_lizard"]
    char = _ashen(make_char, "molten_heart_pit", pending_encounter=encounter, level=9)
    prepared = prepare_battle(library, char)
    setup = prepared.setup
    assert setup.map.id == "molten_heart_pit" and setup.map.objective.leader_retreat
    assert "ember_lizard" in setup.spawn_templates  # 第 2 階段的召喚
    boss = next(u for u in setup.units if u.template.id == BOSS)
    for phase in boss.template.phases:
        for skill_id in phase.skills or ():
            setup.ruleset.skill_def(skill_id)
    run = run_battle(setup, prepared.seed, UtilityAI(library.ai_profiles))
    assert run.state.ended


# ---------------------------------------------------------------------------
# 世界日誌重播
# ---------------------------------------------------------------------------


def test_ashen_world_log_replays(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world(flags=("ashen_waste_open",))
    alice = make_char("alice", location="ashen_ferry", supplies=5)
    actions: list[TeleportAction | TravelAction] = [
        TeleportAction(region=REGION),
        TravelAction(to="old_iron_post"),
        TravelAction(to="cooling_well"),
    ]
    entries = [
        WorldLogEntry(seq=i + 1, now=_day(4) + 60 * i, character_id="alice", action=a)
        for i, a in enumerate(actions)
    ]
    live, char = world, alice
    applied: list[WorldLogEntry] = []
    for entry in entries:  # 遇到遭遇或事件就停（之後的移動不合法）
        if char.pending_encounter is not None or char.pending_event is not None:
            break
        result = world_step(library, live, char, entry.action, entry.now)
        live, char = result.world, result.char
        applied.append(entry)
    assert char.region == REGION
    replayed = replay(library, world, {"alice": alice}, applied)
    assert replayed.world == live and replayed.characters["alice"] == char
