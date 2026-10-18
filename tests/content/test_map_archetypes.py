"""地圖類型與 10 張非測試地圖（Phase 2C-3 5.1、5.2、5.6-2）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.main import main
from trpg.content.maps import ARCHETYPES, TEST_ARCHETYPE, MapDef, check_map
from trpg.shared.types import Team
from trpg.sim.batch import map_spec, run_batches

EXPECTED_TYPES = {
    "bridge_chasm",
    "oil_depot",
    "swamp",
    "ruined_heights",
    "forest",
    "corridor",
    "open_plain",
    "frozen_lake",
}


def _real_maps() -> dict[str, MapDef]:
    return {k: v for k, v in library().maps.items() if v.archetype != TEST_ARCHETYPE}


def test_archetype_is_required() -> None:
    data = library().map("swamp").model_dump(mode="json")
    del data["archetype"]
    with pytest.raises(ValueError, match="archetype"):
        MapDef.model_validate(data)
    data["archetype"] = "volcano"
    with pytest.raises(ValueError, match="archetype"):
        MapDef.model_validate(data)


def test_test_maps_are_tagged_test_and_everything_else_is_not() -> None:
    maps = library().maps
    assert {k for k, v in maps.items() if v.archetype == TEST_ARCHETYPE} == {
        k for k in maps if k.startswith("test_")
    }
    assert set(ARCHETYPES) == EXPECTED_TYPES | {TEST_ARCHETYPE}


def test_there_are_ten_real_maps_covering_all_eight_archetypes() -> None:
    real = _real_maps()
    assert len(real) == 10
    assert {m.archetype for m in real.values()} == EXPECTED_TYPES


@pytest.mark.parametrize("map_id", sorted(_real_maps()))
def test_every_real_map_passes_check_map_has_an_encounter_and_a_fitting_size(map_id: str) -> None:
    lib = library()
    map_def = lib.map(map_id)
    problems = check_map(
        map_def, lib.ruleset.terrain.by_id(), lib.ruleset.core, lib.ruleset.objects.by_id()
    )
    assert problems == []
    assert map_def.encounter is not None
    assert 8 <= map_def.width <= 12 and 8 <= map_def.height <= 12
    for unit_id in (*map_def.encounter.allies, *map_def.encounter.enemies):
        assert unit_id in lib.units
    assert len(map_def.start_zones[Team.ALLY]) >= len(map_def.encounter.allies)
    assert len(map_def.start_zones[Team.ENEMY]) >= len(map_def.encounter.enemies)


def test_forest_has_plenty_of_flammable_concealing_grass() -> None:
    lib = library()
    forest = lib.map("dark_forest")
    grass = [o for o in forest.objects if o.kind == "grass"]
    assert len(grass) >= 12
    tags = lib.ruleset.objects.by_id()["grass"].tags
    assert "conceal" in tags and "flammable" in tags


def test_corridor_has_two_corridors_of_one_and_two_tiles_wide() -> None:
    halls = library().map("narrow_halls")
    rows = halls.terrain_rows()
    middle = halls.width // 2
    gaps = [y for y, row in enumerate(rows) if row[middle - 1] != "#" and row[middle] != "#"]
    runs: list[list[int]] = []
    for y in gaps:
        if runs and runs[-1][-1] == y - 1:
            runs[-1].append(y)
        else:
            runs.append([y])
    assert sorted(len(r) for r in runs) == [1, 2]


def test_open_plain_has_at_most_four_objects_and_gentle_heights() -> None:
    plain = library().map("open_plain")
    assert len(plain.objects) <= 4
    assert max(int(c) for row in plain.height_rows() for c in row) <= 1
    assert not plain.surfaces


def test_frozen_lake_has_ice_surface_holes_and_thin_ice() -> None:
    lib = library()
    lake = lib.map("frozen_lake")
    assert sum(1 for s in lake.surfaces if s.surface.value == "ice") >= 30
    assert all(s.duration is None for s in lake.surfaces)
    holes = [
        (x, y) for y, row in enumerate(lake.terrain_rows()) for x, c in enumerate(row) if c == "O"
    ]
    assert len(holes) >= 3
    assert lib.ruleset.terrain.by_id()["ice_hole"].deadly
    thin = [o for o in lake.objects if o.kind == "thin_ice"]
    assert thin and all(o.at in holes for o in thin)
    thin_def = lib.ruleset.objects.by_id()["thin_ice"]
    assert {"breakable", "over_chasm"} <= set(thin_def.tags)
    assert thin_def.max_hp is not None and thin_def.max_hp <= 10


def test_map_list_command_shows_every_map_with_its_archetype(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["map", "list"]) == 0
    out = capsys.readouterr().out
    for map_id, map_def in library().maps.items():
        assert f"| {map_id} | {map_def.archetype} |" in out


@pytest.mark.parametrize("map_id", ["dark_forest", "narrow_halls", "open_plain", "frozen_lake"])
def test_new_maps_play_through_without_errors(map_id: str) -> None:
    # frozen_lake 種子 3 曾因滑倒後與友軍疊在同一格而拋出例外
    (report,) = run_batches([map_spec(library(), map_id, (0, 3))], jobs=1)
    assert report.anomaly("exception") is None
    assert report.anomaly("max_actions") is None
    assert report.completed == 2


def test_breaking_thin_ice_drops_the_unit_into_the_hole_and_credits_the_breaker() -> None:
    from trpg.engine import begin_battle  # noqa: PLC0415
    from trpg.engine.effects import DamageObjectEffect, MoveUnitEffect, run_effects  # noqa: PLC0415
    from trpg.engine.events import DamageDealt  # noqa: PLC0415

    state = begin_battle(map_spec(library(), "frozen_lake", (0,)).setup, 0).state
    ally = next(u for u in state.units_sorted() if u.team is Team.ALLY)
    enemy = next(u for u in state.units_sorted() if u.team is Team.ENEMY)
    ice_id = state.tile(6, 3).object_id
    assert ice_id is not None
    on_ice = run_effects(state, [MoveUnitEffect(unit_id=enemy.id, dest=(6, 3), mode="teleport")])
    assert on_ice.state.units[enemy.id].alive  # 薄冰撐得住
    broken = run_effects(
        on_ice.state, [DamageObjectEffect(object_id=ice_id, flat=100, source_id=ally.id)]
    )
    dealt = [e for e in broken.events if isinstance(e, DamageDealt)]
    assert [(e.cause, e.source_id, e.target_id) for e in dealt] == [
        ("deadly_terrain", ally.id, enemy.id)
    ]
    assert not broken.state.units[enemy.id].alive
