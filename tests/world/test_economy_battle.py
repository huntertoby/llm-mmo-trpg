"""腰包的道具在戰鬥中（Phase 5D-1；``docs/phases/Phase5計畫.md`` 25.4）：1 AP、次數＝個數、
不佔技能欄位；用掉的戰後從腰包扣；打贏給金幣；「不使用道具」誓約；日誌重播。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.content.skills import skill_slot_problems
from trpg.world.actions import (
    BattleEndedEvent,
    FightAction,
    OathBrokenEvent,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.economy import pouch_skills
from trpg.world.economy_actions import BuyAction, CurrencyGainedEvent, PouchAction, PouchUsedEvent
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState, OathState
from trpg.world.step import StepResult, world_step

MakeChar = Callable[..., CharacterState]
POUCH = {"item_spring_pill": 2, "item_oil_flask": 1}


def _ready(make_char: MakeChar, seed: int, **updates: object) -> CharacterState:
    data: dict[str, object] = {
        "location": "ferry_steps",
        "mercenaries": PARTY,
        "pouch": POUCH,
        "pending_encounter": make_encounter("ferry_steps", seed=seed),
        **updates,
    }
    return make_char(**data)


def _fight(library: ContentLibrary, char: CharacterState) -> StepResult:
    return world_step(
        library, make_world(), char, FightAction(steps=auto_steps(library, char)), NOON
    )


def _used_seed(library: ContentLibrary, make_char: MakeChar) -> tuple[CharacterState, StepResult]:
    for seed in range(12):
        char = _ready(make_char, seed)
        result = _fight(library, char)
        if any(isinstance(e, PouchUsedEvent) for e in result.events):
            return char, result
    raise AssertionError("12 個種子都沒有用到道具")


def test_pouch_items_join_hero_skills(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _ready(make_char, 0)
    prepared = prepare_battle(library, char)
    hero = prepared.setup.units[0].template
    assert hero.skills[-2:] == ("skill_item_oil_flask", "skill_item_spring_pill")
    assert hero.skills[:-2] == char.hero.skills  # 裝備的技能照舊
    pill = prepared.setup.ruleset.skill_def("skill_item_spring_pill")
    assert pill.cost.uses_per_battle == 2 and pill.ap_cost == 1  # 次數＝個數
    defs = [prepared.setup.ruleset.skill_def(s) for s in hero.skills]
    assert skill_slot_problems(defs, library.ruleset.core.skill_slots) == []  # 不佔欄位
    assert "skill_item_spring_pill" not in char.hero.skills


def test_no_pouch_keeps_skills(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _ready(make_char, 0).model_copy(update={"pouch": {}})
    assert pouch_skills(library, char) == ()
    assert prepare_battle(library, char).setup.units[0].template.skills == char.hero.skills


def test_used_items_leave_pouch(library: ContentLibrary, make_char: MakeChar) -> None:
    char, result = _used_seed(library, make_char)
    used = next(e for e in result.events if isinstance(e, PouchUsedEvent))
    for item, n in used.items.items():
        assert result.char.pouch.get(item, 0) == POUCH[item] - n
    assert result.char.bag == char.bag  # 背包不動
    assert "skill_item_spring_pill" not in result.char.skill_usage  # 用法統計只看裝備的技能


def test_win_gives_gold(library: ContentLibrary, make_char: MakeChar) -> None:
    for seed in range(12):
        result = _fight(library, _ready(make_char, seed, pouch={}))
        ended = next(e for e in result.events if isinstance(e, BattleEndedEvent))
        gold = [e for e in result.events if isinstance(e, CurrencyGainedEvent)]
        if ended.won:
            assert result.char.gold == 15
            assert gold == [
                CurrencyGainedEvent(currency="gold", amount=15, total=15, source="battle")
            ]
            return
        assert gold == [] and result.char.gold == 0
    pytest.fail("12 個種子都打不贏")


def test_oath_no_items_breaks(library: ContentLibrary, make_char: MakeChar) -> None:
    oath = OathState(template="oath_no_items", difficulty="easy", sworn_at=NOON)
    for seed in range(12):
        char = _ready(make_char, seed, oath=oath)
        result = _fight(library, char)
        if any(isinstance(e, PouchUsedEvent) for e in result.events):
            broken = [e for e in result.events if isinstance(e, OathBrokenEvent)]
            assert broken and broken[0].template == "oath_no_items"
            return
    pytest.fail("12 個種子都沒有用到道具")


def test_replay_shop_pouch_fight(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    shop: list[object] = [
        BuyAction(shop="shop_liu", item="item_spring_pill", count=2),
        PouchAction(items={"item_spring_pill": 2}),
    ]
    entries = [
        WorldLogEntry(seq=n, now=NOON, character_id="alice", action=a)  # type: ignore[arg-type]
        for n, a in enumerate(shop, 1)
    ]
    start = make_char(gold=100)
    first = replay(library, world, {"alice": start}, entries)
    second = replay(library, world, {"alice": start}, entries)
    done = first.characters["alice"]
    assert dumps_char(done) == dumps_char(second.characters["alice"])
    assert done.pouch == {"item_spring_pill": 2} and done.gold == 70
    assert done.affinity["shopkeeper_liu"] == 2
    # 帶腰包打一場：重播兩次逐字相同
    char, _ = _used_seed(library, make_char)
    fight = [
        WorldLogEntry(
            seq=1,
            now=NOON,
            character_id="alice",
            action=FightAction(steps=auto_steps(library, char)),
        )
    ]
    a = replay(library, world, {"alice": char}, fight)
    b = replay(library, world, {"alice": char}, fight)
    assert dumps_char(a.characters["alice"]) == dumps_char(b.characters["alice"])
    assert a.events == b.events
