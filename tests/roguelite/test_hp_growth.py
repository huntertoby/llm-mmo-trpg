"""體質與升級的最大 HP（Phase 3-7）：配點、升級、戰鬥中的主角、存檔。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import library
from trpg.engine import begin_battle
from trpg.roguelite import (
    apply_choice,
    battle_setup,
    dumps_save,
    loads_save,
    new_run,
    next_node,
)
from trpg.roguelite.progress import hero_unit_id, with_hp_change
from trpg.roguelite.save import RunSave
from trpg.roguelite.state import LevelUpChoice, LevelUpNode, RunState
from trpg.shared.types import Attribute


def _leveled(run: RunState, level: int) -> RunState:
    """直接升到 ``level`` 級並進入該級的升級節點（目前 HP 同步增加）。"""
    current = run
    while current.level < level:
        current = next_node(library(), current.model_copy(update={"levels_pending": 1}))
    assert isinstance(current.node, LevelUpNode)
    return current


def test_start_hp_is_authored_hp_when_constitution_is_not_allocated() -> None:
    lib = library()
    core = lib.ruleset.core
    for build in lib.builds.builds:
        free = {Attribute.STR: lib.roguelite.start_free_points}
        run = new_run(lib, build.id, 1, free)
        assert run.hp == run.max_hp_in(core) == core.template_max_hp(build.hero), build.id


def test_allocating_constitution_at_the_start_raises_the_starting_hp() -> None:
    lib = library()
    core = lib.ruleset.core
    plain = new_run(lib, "build_fire", 1, {Attribute.INT: 4})
    tough = new_run(lib, "build_fire", 1, {Attribute.INT: 1, Attribute.CON: 3})
    assert tough.hp == tough.max_hp_in(core) == plain.hp + 3 * core.hp_per_con_point


def test_max_hp_formula_for_a_run() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_fire", 1, {Attribute.INT: 4})  # 基礎 40、體質 10
    assert run.max_hp_in(core) == 40
    attrs = {**run.hero.attributes, Attribute.CON: 14}
    run = run.model_copy(
        update={"hero": run.hero.model_copy(update={"attributes": attrs}), "level": 5}
    )
    # 40 + (14 − 10) × 3 + 40 × 50‰ × 4
    assert run.max_hp_in(core) == 40 + 12 + 8


def test_level_up_raises_max_hp_and_current_hp_by_the_same_amount() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_push", 2, {Attribute.STR: 4})  # 基礎 60
    hurt = run.model_copy(update={"hp": 25})
    leveled = _leveled(hurt, 2)
    gain = core.level_hp_bonus(60, 2)
    assert gain == 3
    assert leveled.max_hp_in(core) == run.max_hp_in(core) + gain
    assert leveled.hp == 25 + gain


def test_level_up_allocation_to_constitution_raises_max_and_current_hp() -> None:
    lib = library()
    core = lib.ruleset.core
    run = _leveled(
        new_run(lib, "build_fire", 3, {Attribute.INT: 4}).model_copy(update={"hp": 20}), 2
    )
    node = run.node
    assert isinstance(node, LevelUpNode)
    before_max, before_hp = run.max_hp_in(core), run.hp
    choice = LevelUpChoice(attributes={Attribute.CON: 2}, pick=None)
    after = apply_choice(lib, run, choice)
    gain = 2 * core.hp_per_con_point
    assert after.hero.attributes[Attribute.CON] == run.hero.attributes[Attribute.CON] + 2
    assert after.max_hp_in(core) == before_max + gain
    assert after.hp == before_hp + gain


def test_level_up_without_constitution_keeps_current_hp() -> None:
    lib = library()
    core = lib.ruleset.core
    run = _leveled(
        new_run(lib, "build_fire", 3, {Attribute.INT: 4}).model_copy(update={"hp": 20}), 2
    )
    after = apply_choice(lib, run, LevelUpChoice(attributes={Attribute.INT: 2}, pick=None))
    assert after.hp == run.hp
    assert after.max_hp_in(core) == run.max_hp_in(core)


def test_a_decrease_never_drops_current_hp_below_one() -> None:
    lib = library()
    run = new_run(lib, "build_fire", 3, {Attribute.INT: 4}).model_copy(update={"hp": 2})
    lowered = run.model_copy(
        update={
            "hero": run.hero.model_copy(
                update={"attributes": {**run.hero.attributes, Attribute.CON: 1}}
            )
        }
    )
    assert with_hp_change(lib, run, lowered).hp == 1


@pytest.mark.parametrize("level", [1, 3])
def test_the_battle_hero_has_the_runs_max_hp(level: int) -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_fire", 4, {Attribute.INT: 1, Attribute.CON: 3})
    while run.level < level:
        run = _leveled(run, run.level + 1)
    run = run.model_copy(update={"node": new_run(lib, "build_fire", 4).node})
    state = begin_battle(battle_setup(lib, run), run.plan[0].seed).state
    hero = state.units[hero_unit_id(state)]
    assert hero.max_hp == run.max_hp_in(core)
    assert hero.hp == run.hp  # 滿血的主角開場滿血


def test_save_and_load_keep_max_and_current_hp() -> None:
    lib = library()
    core = lib.ruleset.core
    run = apply_choice(
        lib,
        _leveled(new_run(lib, "build_push", 5, {Attribute.STR: 4}), 3),
        LevelUpChoice(attributes={Attribute.CON: 2}, pick=None),
    )
    loaded = loads_save(dumps_save(RunSave(run_id="hp", run=run))).run
    assert loaded == run
    assert loaded.max_hp_in(core) == run.max_hp_in(core)
    assert loaded.hp == run.hp
