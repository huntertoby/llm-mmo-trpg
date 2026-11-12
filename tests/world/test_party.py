"""隊伍與系統傭兵（Phase 5C-1；``docs/phases/Phase5計畫.md`` 22）。"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute, Team
from trpg.world.actions import (
    BattleStartedEvent,
    FightAction,
    HireAction,
    PartyChangedEvent,
    ShadowSavedEvent,
    TeleportAction,
    TravelAction,
)
from trpg.world.battle import auto_steps, grow_allies, prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.party import ESCORT_PARTED, hire_problem, party_spawns
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]


def _hire(library: ContentLibrary, char: CharacterState, *ids: str) -> CharacterState:
    return world_step(library, make_world(), char, HireAction(mercenaries=ids), NOON).char


def test_hire_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    assert char.location == "mist_ferry"
    assert hire_problem(library, char) is None
    result = world_step(
        library,
        make_world(),
        char,
        HireAction(mercenaries=("merc_huichun", "merc_qingfeng")),
        NOON,
    )
    assert result.char.mercenaries == ("merc_huichun", "merc_qingfeng")  # 依選擇順序
    assert result.events == (
        PartyChangedEvent(mercenaries=("merc_huichun", "merc_qingfeng")),
        ShadowSavedEvent(level=1),  # 城鎮整備存成影子（5C-2）
    )
    # 免費：其他欄位不變；開局的護衛賽倫換下了，記旗標（OB-7，#154：之後再雇用不顯示來歷）
    assert result.char.story_flags == (ESCORT_PARTED,)
    restored = {"mercenaries": char.mercenaries, "story_flags": char.story_flags}
    assert result.char.model_copy(update=restored) == char


def test_keeping_escort_records_nothing(library: ContentLibrary, make_char: MakeChar) -> None:
    """OB-7（#154）：留著賽倫、只多雇一名，賽倫仍是開局帶來的那一位。"""
    kept = _hire(library, make_char(), "merc_tiebi", "merc_qingfeng")
    assert ESCORT_PARTED not in kept.story_flags


@pytest.mark.parametrize(
    "ids", [(), ("merc_tiebi",), ("merc_jinglei", "merc_fuying")], ids=["zero", "one", "two"]
)
def test_hire_replaces_whole_party(
    library: ContentLibrary, make_char: MakeChar, ids: tuple[str, ...]
) -> None:
    char = _hire(library, make_char(), "merc_chiyan", "merc_panshi")
    assert _hire(library, char, *ids).mercenaries == ids


@pytest.mark.parametrize(
    ("ids", "match"),
    [
        (("merc_tiebi", "merc_panshi", "merc_huichun"), "最多帶 2 名"),
        (("merc_tiebi", "merc_tiebi"), "兩次"),
        (("merc_nobody",), "沒有這名傭兵"),
    ],
)
def test_hire_rejects_bad_lists(
    library: ContentLibrary, make_char: MakeChar, ids: tuple[str, ...], match: str
) -> None:
    with pytest.raises(WorldActionError, match=match):
        world_step(library, make_world(), make_char(), HireAction(mercenaries=ids), NOON)


def test_hire_only_in_town(library: ContentLibrary, make_char: MakeChar) -> None:
    field = make_char(location="ferry_steps")
    assert hire_problem(library, field) == "出城前在城鎮選好，野外不能換"
    with pytest.raises(WorldActionError, match="野外不能換"):
        world_step(library, make_world(), field, HireAction(mercenaries=("merc_tiebi",)), NOON)
    encounter = make_encounter("mist_ferry")
    busy = make_char(pending_encounter=encounter)
    with pytest.raises(WorldActionError, match="遭遇"):
        world_step(library, make_world(), busy, HireAction(), NOON)


def test_hire_without_roster(library: ContentLibrary, make_char: MakeChar) -> None:
    bare = dataclasses.replace(library, world_mercenaries=None)
    with pytest.raises(WorldActionError, match="傭兵名單"):
        world_step(bare, make_world(), make_char(), HireAction(), NOON)


def test_party_kept_when_traveling_and_teleport_rejected(
    calm: ContentLibrary, make_char: MakeChar
) -> None:
    char = _hire(calm, make_char(), "merc_qingyin")
    moved = world_step(calm, make_world(), char, TravelAction(to="ferry_steps"), NOON).char
    assert moved.location == "ferry_steps"
    assert moved.mercenaries == ("merc_qingyin",)
    back = world_step(calm, make_world(), moved, TravelAction(to="mist_ferry"), NOON + 60).char
    assert back.mercenaries == ("merc_qingyin",)
    with pytest.raises(WorldActionError):
        world_step(calm, make_world(), back, TeleportAction(region="ashen_waste"), NOON + 120)


def test_battle_uses_hired_mercenaries(library: ContentLibrary, make_char: MakeChar) -> None:
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    char = _hire(library, make_char(), "merc_tiebi", "merc_huichun")
    char = char.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    allies = [u for u in prepare_battle(library, char).setup.units if u.team is Team.ALLY]
    assert [u.template.id for u in allies] == [char.hero.id, "merc_tiebi", "merc_huichun"]
    assert [u.template.name_zh for u in allies[1:]] == ["賽倫", "回春"]
    builds = library.builds.by_id()
    assert allies[1].template.skills == builds["build_tank"].hero.skills  # 1 級：底稿原樣
    assert allies[2].template.ai_profile == builds["build_healer"].hero.ai_profile


def test_one_mercenary_means_party_of_two(library: ContentLibrary, make_char: MakeChar) -> None:
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    char = _hire(library, make_char(), "merc_chuanyun")
    char = char.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    allies = [u for u in prepare_battle(library, char).setup.units if u.team is Team.ALLY]
    assert [u.template.id for u in allies[1:]] == ["merc_chuanyun"]


def test_no_mercenaries_means_solo(library: ContentLibrary, make_char: MakeChar) -> None:
    """雇 0 名＝獨行（5C-2 玩法 PM 定 ③）：我方只有主角，標準隊友只留在 roguelite。"""
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    char = make_char(location="ferry_steps", pending_encounter=encounter, mercenaries=())
    allies = [u for u in prepare_battle(library, char).setup.units if u.team is Team.ALLY]
    assert [u.template.id for u in allies] == [char.hero.id]


def test_mercenaries_grow_with_hero_level(library: ContentLibrary, make_char: MakeChar) -> None:
    encounter = make_encounter("ferry_steps", seed=3, battle_map="cliff_outpost")
    char = _hire(library, make_char(), "merc_jinglei")
    char = char.model_copy(
        update={"location": "ferry_steps", "pending_encounter": encounter, "level": 5}
    )
    prepared = prepare_battle(library, char)
    merc = next(u for u in prepared.setup.units if u.template.id == "merc_jinglei")
    base = library.builds.by_id()["build_storm"].hero
    grown, skills = grow_allies(library, party_spawns(library, char), 5)
    assert merc.template == grown[0].template  # 同標準隊友的成長（5A-SIM2）
    assert merc.template.level == 5
    assert merc.template.attributes[Attribute.INT] == base.attributes[Attribute.INT] + 8
    assert merc.template.max_hp > base.max_hp
    tier = library.world_rules.enemy_growth.tier_for(5) if library.world_rules else 1
    assert all(s.endswith(f"_t{tier}") for s in merc.template.skills if s not in base.skills)
    assert {s.id for s in skills} <= set(prepared.setup.ruleset.skills.by_id())


def test_fight_records_mercenaries_and_is_deterministic(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    encounter = make_encounter(
        "ferry_steps", seed=5, battle_map="cliff_outpost", from_location="mist_ferry"
    )
    hired = _hire(library, make_char(), "merc_panshi", "merc_chiyan")
    ready = hired.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})
    steps = auto_steps(library, ready)
    first = world_step(library, make_world(), ready, FightAction(steps=steps), NOON + 60)
    second = world_step(library, make_world(), ready, FightAction(steps=steps), NOON + 60)
    started = next(e for e in first.events if isinstance(e, BattleStartedEvent))
    assert started.mercenaries == ("merc_panshi", "merc_chiyan")
    assert first.char.mercenaries == ("merc_panshi", "merc_chiyan")
    assert dumps_char(first.char) == dumps_char(second.char)
    assert first.events == second.events


def test_hire_replays(calm: ContentLibrary, make_char: MakeChar) -> None:
    start = make_char()
    who = start.character_id
    entries = [
        WorldLogEntry(
            seq=1, now=NOON, character_id=who, action=HireAction(mercenaries=("merc_tiebi",))
        ),
        WorldLogEntry(
            seq=2, now=NOON + 30, character_id=who, action=TravelAction(to="ferry_steps")
        ),
        WorldLogEntry(seq=3, now=NOON + 60, character_id=who, action=TravelAction(to="mist_ferry")),
        WorldLogEntry(
            seq=4,
            now=NOON + 90,
            character_id=who,
            action=HireAction(mercenaries=("merc_qingyin", "merc_tiebi")),
        ),
    ]
    first = replay(calm, make_world(), {who: start}, entries)
    second = replay(calm, make_world(), {who: start}, entries)
    assert dumps_char(first.characters[who]) == dumps_char(second.characters[who])
    assert first.characters[who].mercenaries == ("merc_qingyin", "merc_tiebi")
    assert first.events == second.events
