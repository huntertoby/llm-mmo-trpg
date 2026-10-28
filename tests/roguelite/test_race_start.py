"""主角的種族（Phase 3R-2）：開局可指定（3R-3 才有選種族的流程）、隨存檔保存、帶進戰鬥。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import library
from trpg.engine import start_battle
from trpg.roguelite import ChoiceError, RunSave, new_run
from trpg.roguelite.progress import battle_setup
from trpg.roguelite.save import write_save
from trpg.roguelite.start import with_race
from trpg.shared.types import Team


def test_with_race_sets_the_hero_race_and_none_changes_nothing() -> None:
    lib = library()
    run = new_run(lib, "build_push", 3)
    assert run.hero.race is None
    assert with_race(lib, run, None) is run
    assert with_race(lib, run, "orc").hero.race == "orc"


def test_with_race_rejects_unknown_races() -> None:
    lib = library()
    with pytest.raises(ChoiceError, match="未知的種族"):
        with_race(lib, new_run(lib, "build_push", 3), "elfin")


def test_the_race_is_saved_and_reaches_the_battle() -> None:
    lib = library()
    run = with_race(lib, new_run(lib, "build_push", 3), "dwarf")
    saved = RunSave(run_id="r", run=run)
    assert RunSave.model_validate_json(saved.model_dump_json()).run.hero.race == "dwarf"
    state = start_battle(battle_setup(lib, run), 1)
    hero = next(u for u in state.units.values() if u.team is Team.ALLY)
    assert hero.race == "dwarf"
    assert state.ruleset.races is not None


def test_write_save_roundtrip_keeps_race(tmp_path) -> None:  # type: ignore[no-untyped-def]
    lib = library()
    run = with_race(lib, new_run(lib, "build_push", 3), "seafolk")
    path = write_save(tmp_path, RunSave(run_id="abcd", run=run))
    assert '"race": "seafolk"' in path.read_text(encoding="utf-8")
