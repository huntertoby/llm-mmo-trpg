"""E6-b2 第 1 項：招牌勾選的保存（``RunState.gear_chosen``）與開戰時帶進 ``Loadout.chosen``。"""

from __future__ import annotations

import json

from tests.roguelite.helpers import library
from tests.roguelite.signature_helpers import GRAPPLE, gear_item, sig_library
from trpg.roguelite import RunSave, RunState, battle_setup, dumps_save, loads_save, new_keyword_run
from trpg.roguelite.gear import run_loadout
from trpg.roguelite.save import SAVE_FORMAT

KEYWORDS = ("ignite", "prone")
PICK = f"hands:{GRAPPLE}"


def _run() -> RunState:
    return new_keyword_run(library(), "one_handed_sword", KEYWORDS, 3)


def _save(run: RunState) -> str:
    lib = library()
    return dumps_save(RunSave(run_id="c", run=run, quantity_scale=lib.ruleset.core.quantity_scale))


def test_gear_chosen_is_not_written_when_empty() -> None:
    raw = json.loads(_save(_run()))
    assert "gear_chosen" not in raw["run"]
    assert raw["format"] == SAVE_FORMAT


def test_gear_chosen_round_trips() -> None:
    run = _run().model_copy(update={"gear_chosen": (PICK,)})
    raw = json.loads(_save(run))
    assert raw["run"]["gear_chosen"] == [PICK]
    assert loads_save(json.dumps(raw)).run.gear_chosen == (PICK,)


def test_old_save_without_gear_chosen_still_loads() -> None:
    run = _run()
    raw = json.loads(_save(run))
    assert "gear_chosen" not in raw["run"]  # 舊存檔就是這個樣子
    loaded = loads_save(json.dumps(raw)).run
    assert loaded.gear_chosen == () and loaded == run


def test_battle_setup_carries_gear_chosen_into_the_loadout() -> None:
    lib = sig_library(library())
    run = _run().model_copy(
        update={"equipment": {"hands": gear_item("g", "hands", GRAPPLE)}, "gear_chosen": (PICK,)}
    )
    assert run_loadout(lib, run).chosen == (PICK,)
    hero = battle_setup(lib, run).units[0]
    assert hero.equipment.chosen == (PICK,)


def test_no_gear_chosen_leaves_the_loadout_unchanged() -> None:
    lib = library()
    run = _run()
    assert run_loadout(lib, run) == lib.loadout_of(run.hero)
    assert run_loadout(lib, run).chosen == ()
