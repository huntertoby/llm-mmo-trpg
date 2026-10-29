"""一輪的耐力（Phase 3H-2）：上限依屬性、戰鬥之間不回復、營火回滿、存檔往返與舊存檔、
``refill_after_battle`` 設定點。"""

from __future__ import annotations

import json
from dataclasses import replace

from tests.roguelite.helpers import library
from trpg.content.library import ContentLibrary
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
from trpg.shared.types import Attribute, Team


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
    off = replace(lib, roguelite=lib.roguelite.model_copy(update={"refill_after_battle": ()}))
    after = finish_battle(off, first, battle.state, len(battle.steps))  # 不回滿時照剩餘帶入
    assert after.stamina == hero.stamina
    assert after.history[-1].stamina == hero.stamina


def test_the_campfire_refills_stamina() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, "build_push", 2)
    camp = next_node(
        lib,
        run.model_copy(
            update={"battles_done": 3, "stamina": 0, "mana": 0, "complete_offers_done": (3,)}
        ),
    )
    assert isinstance(camp.node, CampfireNode)
    assert (camp.stamina, camp.mana) == (run.max_stamina_in(core), run.max_mana_in(core))


def _won_battle(lib: ContentLibrary) -> tuple[ActiveBattle, RunState]:
    """第一場打贏的 (戰鬥, 起始一輪)：試幾個種子直到主角贏（自動代打）。"""
    for seed in range(40):
        first = new_run(lib, "build_push", seed).model_copy(update={"stamina": 5, "mana": 2})
        battle = ActiveBattle(lib, first)
        battle.auto()
        if battle_result(battle.state).winner == Team.ALLY:
            return battle, first
    raise AssertionError("no winning seed")


def test_refill_after_battle_refills_stamina_but_not_mana() -> None:
    lib = library()
    assert lib.roguelite.refill_after_battle == ("stamina",)
    battle, first = _won_battle(lib)
    hero = battle_result(battle.state).ally(battle.hero_id)
    assert hero is not None
    done = finish_battle(lib, first, battle.state, len(battle.steps))
    core = lib.ruleset.core
    assert done.stamina is not None
    assert done.stamina >= max(first.max_stamina_in(core), hero.max_stamina)  # 回滿
    assert done.mana == hero.mana  # 法力只在營火回滿
    # 設定點關掉時，耐力照戰鬥結束時的剩餘帶入
    off = replace(lib, roguelite=lib.roguelite.model_copy(update={"refill_after_battle": ()}))
    plain = finish_battle(off, first, battle.state, len(battle.steps))
    assert plain.stamina == hero.stamina
    both = replace(
        lib, roguelite=lib.roguelite.model_copy(update={"refill_after_battle": ("mana", "stamina")})
    )
    full = finish_battle(both, first, battle.state, len(battle.steps))
    assert full.mana >= max(first.max_mana_in(core), hero.max_mana)


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
