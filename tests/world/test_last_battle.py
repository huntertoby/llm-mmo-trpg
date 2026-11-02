"""最近一次戰鬥結果留在角色上（Phase 5A-7；``docs/phases/Phase5計畫.md`` 13.4）。"""

from __future__ import annotations

import json

import pytest

from tests.world.helpers import NOON, PARTY, hero, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.world.actions import BattleEndedEvent, FightAction, RestAction
from trpg.world.battle import auto_steps
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState, EncounterResult
from trpg.world.step import new_character, world_step


def _start(library: ContentLibrary, location: str, **updates: object) -> CharacterState:
    char = new_character(library, "alice", hero(library), region="cloud_ridge")
    return char.model_copy(update={"location": location, "mercenaries": PARTY, **updates})


def _find(
    library: ContentLibrary,
    char: CharacterState,
    make: object,
    *,
    won: bool,
) -> tuple[CharacterState, FightAction]:
    assert callable(make)
    for seed in range(16):
        start = char.model_copy(update={"pending_encounter": make(seed)})
        action = FightAction(steps=auto_steps(library, start))
        result = world_step(library, make_world(), start, action, NOON)
        ended = next(e for e in result.events if isinstance(e, BattleEndedEvent))
        if ended.won is won:
            return start, action
    raise AssertionError(f"16 個種子都找不到 won={won} 的戰鬥")


def _win_encounter(seed: int) -> EncounterResult:
    return make_encounter(
        "ferry_steps", seed=seed, battle_map="cliff_outpost", from_location="mist_ferry"
    )


def _loss_encounter(seed: int) -> EncounterResult:
    return make_encounter(
        "elixir_cave", seed=seed, level=5, battle_map="narrow_halls", from_location="herb_valley"
    )


@pytest.fixture(scope="module")
def won_fight(library: ContentLibrary) -> tuple[CharacterState, FightAction]:
    return _find(library, _start(library, "ferry_steps"), _win_encounter, won=True)


def test_win_is_recorded(
    library: ContentLibrary, won_fight: tuple[CharacterState, FightAction]
) -> None:
    start, action = won_fight
    result = world_step(library, make_world(), start, action, NOON)
    last = result.char.last_battle
    assert last is not None
    assert last.won and last.location == "ferry_steps" and last.at == NOON
    assert last.xp_gained > 0 and last.rounds > 0
    assert last.level_before == 1 and last.level == result.char.level
    # 之後的動作不清掉
    rested = world_step(
        library,
        result.world,
        result.char.model_copy(update={"location": "mist_ferry"}),
        RestAction(),
        NOON + 5,
    )
    assert rested.char.last_battle == last


def test_loss_is_recorded(library: ContentLibrary) -> None:
    char = _start(library, "elixir_cave", hp=1, camped_at=None)
    start, action = _find(library, char, _loss_encounter, won=False)
    result = world_step(library, make_world(), start, action, NOON)
    last = result.char.last_battle
    assert last is not None
    assert not last.won and last.xp_gained == 0 and last.location == "elixir_cave"


def test_old_snapshot_reads_without_field(library: ContentLibrary) -> None:
    char = _start(library, "mist_ferry")
    data = json.loads(dumps_char(char))
    assert "last_battle" in data
    data.pop("last_battle")
    assert loads_char(json.dumps(data)).last_battle is None


def test_replay_gives_same_last_battle(
    library: ContentLibrary, won_fight: tuple[CharacterState, FightAction]
) -> None:
    start, action = won_fight
    world = make_world()
    live = world_step(library, world, start, action, NOON)
    entry = WorldLogEntry(seq=1, now=NOON, character_id=start.character_id, action=action)
    replayed = replay(library, world, {start.character_id: start}, [entry])
    assert replayed.characters[start.character_id].last_battle == live.char.last_battle
