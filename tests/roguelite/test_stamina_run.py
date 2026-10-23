"""一輪的耐力（Phase 3H-2）：上限依屬性、戰鬥之間不回復、營火回滿、存檔往返與舊存檔、
``refill_after_battle`` 設定點。"""

from __future__ import annotations

import json
from dataclasses import replace

from tests.roguelite.helpers import library
from trpg.engine import battle_result, begin_battle
from trpg.roguelite import (
    ActiveBattle,
    RunSave,
    RunState,
    battle_setup,
    dumps_save,
    finish_battle,
    loads_save,
    new_keyword_run,
    new_run,
    next_node,
)
from trpg.roguelite.progress import hero_unit_id
from trpg.roguelite.state import CampfireNode
from trpg.shared.types import Attribute


def test_a_new_run_starts_with_full_resources_from_the_formula() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_keyword_run(lib, "lightning_staff", ["wet", "charged"], 7)
    base = lib.roguelite.start.heroes["focus"]
    best_mental = max(run.hero.attributes[a] for a in (Attribute.INT, Attribute.WIS, Attribute.WIL))
    best_body = max(run.hero.attributes[a] for a in (Attribute.STR, Attribute.DEX, Attribute.CON))
    assert run.max_mana_in(core) == base.max_mana + (best_mental - 10) * 2
    assert run.max_stamina_in(core) == (base.stamina or core.default_stamina) + (best_body - 10) * 2
    assert run.mana == run.max_mana_in(core)
    assert run.stamina is None and run.stamina_in(core) == run.max_stamina_in(core)
    state = begin_battle(battle_setup(lib, run), 0).state
    hero = state.units[hero_unit_id(state)]
    assert (hero.max_mana, hero.max_stamina) == (run.max_mana_in(core), run.max_stamina_in(core))
    assert hero.stamina == hero.max_stamina


def test_stamina_carries_between_battles_and_into_the_next_battle() -> None:
    lib = library()
    run = new_run(lib, "build_push", 4).model_copy(update={"stamina": 11})
    state = begin_battle(battle_setup(lib, run), 0).state
    assert state.units[hero_unit_id(state)].stamina == 11
    first = new_run(lib, "build_push", 0)
    battle = ActiveBattle(lib, first)
    battle.auto()
    hero = battle_result(battle.state).ally(battle.hero_id)
    assert hero is not None
    after = finish_battle(lib, first, battle.state, len(battle.steps))
    assert after.stamina == hero.stamina
    assert after.history[-1].stamina == hero.stamina


def test_the_campfire_refills_stamina() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_push", 2)
    camp = next_node(lib, run.model_copy(update={"battles_done": 3, "stamina": 0, "mana": 0}))
    assert isinstance(camp.node, CampfireNode)
    assert (camp.stamina, camp.mana) == (run.max_stamina_in(core), run.max_mana_in(core))


def test_refill_after_battle_is_a_setting_and_off_by_default() -> None:
    lib = library()
    assert lib.roguelite.refill_after_battle == ()
    first = new_run(lib, "build_push", 0).model_copy(update={"stamina": 5, "mana": 2})
    battle = ActiveBattle(lib, first)
    battle.auto()
    hero = battle_result(battle.state).ally(battle.hero_id)
    assert hero is not None
    assert hero.stamina < hero.max_stamina  # 以 5 點耐力開戰
    plain = finish_battle(lib, first, battle.state, len(battle.steps))
    assert (plain.mana, plain.stamina) == (hero.mana, hero.stamina)
    rules = lib.roguelite.model_copy(update={"refill_after_battle": ("mana", "stamina")})
    refilled = finish_battle(replace(lib, roguelite=rules), first, battle.state, len(battle.steps))
    core = lib.ruleset.core
    # 回滿到戰鬥中的上限（升級帶來的上限差再補上）
    assert refilled.mana >= max(first.max_mana_in(core), hero.max_mana)
    assert refilled.stamina is not None
    assert refilled.stamina >= max(first.max_stamina_in(core), hero.max_stamina)


def test_raising_a_body_attribute_raises_current_stamina_with_the_cap() -> None:
    from trpg.roguelite.progress import with_hp_change  # noqa: PLC0415

    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_push", 2).model_copy(update={"stamina": 5})
    attrs = dict(run.hero.attributes)
    best = max(attrs[a] for a in (Attribute.STR, Attribute.DEX, Attribute.CON))
    attrs[Attribute.STR] = best + 2
    after = with_hp_change(
        lib, run, run.model_copy(update={"hero": run.hero.model_copy(update={"attributes": attrs})})
    )
    assert after.max_stamina_in(core) == run.max_stamina_in(core) + 4
    assert after.stamina == 9


def test_save_round_trip_keeps_stamina_and_old_saves_load_as_full() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_push", 3).model_copy(update={"stamina": 7})
    text = dumps_save(RunSave(run_id="t", run=run))
    assert loads_save(text).run.stamina == 7
    raw = json.loads(text)
    del raw["run"]["stamina"]  # 3H-2 之前的存檔沒有這個欄位
    old = loads_save(json.dumps(raw)).run
    assert isinstance(old, RunState)
    assert old.stamina is None and old.stamina_in(core) == old.max_stamina_in(core)
    state = begin_battle(battle_setup(lib, old), 0).state
    hero = state.units[hero_unit_id(state)]
    assert hero.stamina == hero.max_stamina
