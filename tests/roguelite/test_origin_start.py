"""出身（Phase 3R-3a）：開局可指定、只記在 ``run.origin``、不影響戰鬥、存檔相容。"""

from __future__ import annotations

import json

import pytest

from tests.roguelite.helpers import library
from trpg.roguelite import ChoiceError, RunSave, new_run
from trpg.roguelite.progress import battle_setup
from trpg.roguelite.save import dumps_save, loads_save
from trpg.roguelite.start import with_origin, with_race


def test_with_origin_sets_the_origin_without_touching_the_hero_or_the_battle() -> None:
    lib = library()
    run = new_run(lib, "build_push", 3)
    assert run.origin is None and with_origin(lib, run, None) is run
    chosen = with_origin(lib, run, "origin_ashen_waste")
    assert chosen.origin == "origin_ashen_waste" and chosen.hero == run.hero
    assert battle_setup(lib, chosen) == battle_setup(lib, run)


def test_with_origin_rejects_unknown_origins() -> None:
    lib = library()
    with pytest.raises(ChoiceError, match="未知的出身"):
        with_origin(lib, new_run(lib, "build_push", 3), "origin_nowhere")


def test_race_and_origin_roundtrip_and_old_saves_without_them_load() -> None:
    lib = library()
    run = with_origin(
        lib, with_race(lib, new_run(lib, "build_push", 3), "orc"), "origin_cloud_ridge"
    )
    text = dumps_save(RunSave(run_id="r", run=run))
    loaded = loads_save(text).run
    assert loaded.origin == "origin_cloud_ridge" and loaded.hero.race == "orc"
    raw = json.loads(text)
    del raw["run"]["origin"]
    del raw["run"]["hero"]["race"]
    for old in ("trpg-run/5", "trpg-run/6"):
        raw["format"] = old
        back = loads_save(json.dumps(raw))
        assert back.format == "trpg-run/11"
        assert back.run.origin is None and back.run.hero.race is None
