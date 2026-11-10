"""這一趟的陣容固定（Phase 6D-R2）：``FieldVisit`` 記進圖時每隊的重生世代，別人打贏造成的世代 +1
下一趟才生效；舊存檔（``trpg-char/5``，沒有 ``generations``）照世界現在的世代。"""

from __future__ import annotations

import dataclasses
import json

import pytest

from tests.world.helpers import NOON, make_world, with_rules
from tests.world.test_field_lineup_seed import GUARD, _char, _steps_map
from trpg.content.library import ContentLibrary
from trpg.world.field_actions import WalkAction
from trpg.world.field_enemies import (
    _with_win,
    enemy_lineup,
    field_enemies,
    lineup_seed,
    visit_for,
    with_visit,
)
from trpg.world.rng import STREAM_FIELD
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import world_step

SPOT = ("cloud_ridge", "ferry_steps")


@pytest.fixture(scope="module")
def personal_lib(field_library: ContentLibrary) -> ContentLibrary:
    calm = with_rules(field_library, encounter={"base_permille": 0, "per_level_permille": 0})
    fields = {k: m.model_copy(update={"spawns": ()}) for k, m in calm.field_maps.items()}
    found = _steps_map([{**GUARD, "personal": True}])
    return dataclasses.replace(calm, field_maps={**fields, found.id: found})


def _entered(library: ContentLibrary, world: WorldState, name: str, counter: int) -> CharacterState:
    char = _char(library, name, (1, 6), rng_counters={STREAM_FIELD: counter})
    return with_visit(library, world, char)


def test_visit_records_generations(personal_lib: ContentLibrary) -> None:
    world = make_world()
    alice = _entered(personal_lib, world, "alice", 0)
    assert alice.field_visit is not None and alice.field_visit.generations == (0,)
    later = _with_win(world, alice.field_visit, 0, NOON)
    bob = _entered(personal_lib, later, "bob", 3)
    assert bob.field_visit is not None and bob.field_visit.generations == (1,)


def test_other_win_keeps_this_trips_lineup(personal_lib: ContentLibrary) -> None:
    """兩個角色同圖、alice 打贏 personal 隊伍（世界的世代 +1）：bob 這一趟看到與碰到的陣容不變；
    bob 下一趟（重新進圖）才換。"""
    lib = personal_lib
    world = make_world()
    alice = _entered(lib, world, "alice", 0)
    bob = _entered(lib, world, "bob", 3)
    [enemy] = field_enemies(lib, world, bob, NOON)
    before = enemy_lineup(lib, world, bob, enemy, NOON)
    assert alice.field_visit is not None and before is not None
    won = _with_win(
        world, alice.field_visit, 0, NOON
    )  # 打贏 personal 隊伍（同 FightAction 的路徑）
    assert won.spawn_generation(*SPOT, 0) == 1
    assert visit_for(lib, won, bob) == bob.field_visit  # 還是同一趟
    [still] = field_enemies(lib, won, bob, NOON)  # personal：對 bob 不消失
    assert enemy_lineup(lib, won, bob, still, NOON) == before
    # bob 走過去開打：記下的陣容種子仍是進圖時的世代
    path = tuple((x, 6) for x in range(2, 8))
    step = world_step(lib, won, bob, WalkAction(path=path), NOON)
    encounter = step.char.pending_encounter
    assert encounter is not None and encounter.contact is not None
    assert encounter.contact.lineup_seed == lineup_seed(world, *SPOT, 0)
    assert encounter.contact.lineup_seed != lineup_seed(won, *SPOT, 0)
    # 下一趟：重新進圖，照新的世代
    again = with_visit(lib, won, bob.model_copy(update={"field_visit": None}))
    assert again.field_visit is not None and again.field_visit.generations == (1,)
    assert lineup_seed(won, *SPOT, 0, again.field_visit.generation(0)) == lineup_seed(won, *SPOT, 0)


def test_old_char_visit_uses_world_generation(personal_lib: ContentLibrary) -> None:
    """``trpg-char/5`` 的 ``field_visit`` 沒有 ``generations``：照讀，陣容照世界現在的世代。"""
    world = make_world()
    bob = _entered(personal_lib, world, "bob", 3)
    data = json.loads(dumps_char(bob))
    data["format"] = "trpg-char/5"
    del data["field_visit"]["generations"]
    old = loads_char(json.dumps(data))
    assert old.format == "trpg-char/13"
    assert old.field_visit is not None and old.field_visit.generations == ()
    assert old.field_visit.generation(0) is None
    assert loads_char(dumps_char(bob)) == bob
