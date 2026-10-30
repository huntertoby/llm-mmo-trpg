"""一輪消耗量測的覆寫（BAL-6）：只改記憶體副本，預設不變。"""

from __future__ import annotations

from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import SpawnUnitsEvent
from trpg.shared.types import Team
from trpg.sim.attrition import NO_REINFORCE, AttritionConfig, apply_config, format_rows


def _library() -> ContentLibrary:
    return load_library()


def test_default_config_is_identity() -> None:
    library = _library()
    assert apply_config(library, AttritionConfig()) is library
    assert AttritionConfig().label == "現況"


def test_defend_rounds_delta_applies_to_every_defend_map() -> None:
    library = _library()
    out = apply_config(library, AttritionConfig(defend_rounds_delta=-2))
    seen = 0
    for map_id, map_def in sorted(library.maps.items()):
        alt = map_def.alt_objectives
        if alt is None or alt.defend is None:
            continue
        seen += 1
        new = out.maps[map_id].alt_objectives
        assert new is not None
        assert new.defend is not None
        assert new.defend.rounds == max(1, alt.defend.rounds - 2)
        assert new.defend.tiles == alt.defend.tiles
    assert seen > 0
    # 原 library 不受影響
    original = library.maps["open_plain"].alt_objectives
    assert original is not None
    assert original.defend is not None
    overridden = out.maps["open_plain"].alt_objectives
    assert overridden is not None
    assert overridden.defend is not None
    assert original.defend.rounds - 2 == overridden.defend.rounds  # 原 library 沒被改到


def test_tile_modes_stay_legal() -> None:
    library = _library()
    wide = apply_config(library, AttritionConfig(tile_mode="wide"))
    back = apply_config(library, AttritionConfig(tile_mode="back"))
    for map_id, map_def in sorted(library.maps.items()):
        alt = map_def.alt_objectives
        if alt is None or alt.defend is None:
            continue
        zones = {c for cells in map_def.start_zones.values() for c in cells}
        for variant in (wide, back):
            tiles = variant.maps[map_id].alt_objectives.defend.tiles  # type: ignore[union-attr]
            assert not zones & set(tiles)
        assert set(alt.defend.tiles) <= set(wide.maps[map_id].alt_objectives.defend.tiles)  # type: ignore[union-attr]
        (cell,) = back.maps[map_id].alt_objectives.defend.tiles  # type: ignore[union-attr]
        starts = map_def.start_zones[Team.ALLY]
        old = alt.defend.tiles[0]
        near = min(abs(cell[0] - s[0]) + abs(cell[1] - s[1]) for s in starts)
        near_old = min(abs(old[0] - s[0]) + abs(old[1] - s[1]) for s in starts)
        assert near <= near_old


def test_third_battle_enemies_trimmed() -> None:
    library = _library()
    out = apply_config(library, AttritionConfig(third_battle_enemies=3))
    before = library.roguelite.encounters
    after = out.roguelite.encounters
    assert after[:2] == before[:2]
    assert after[3:] == before[3:]
    for old, new in zip(before[2].options, after[2].options, strict=True):
        assert new == old[:3]
        assert len(new) == 3


def test_format_rows_header() -> None:
    assert format_rows([]).startswith("| 設定 | 一輪勝率")


def test_boss_overrides_guards_and_reinforcements() -> None:
    library = _library()
    boss = library.roguelite.boss
    base_events = [e for e in library.maps[boss.map].events if isinstance(e, SpawnUnitsEvent)]
    assert base_events

    out = apply_config(library, AttritionConfig(boss_guards_delta=-2))
    assert out.roguelite.boss.enemies == boss.enemies[:-2]
    assert out.roguelite.boss.enemies[0] == boss.enemies[0]  # 頭目保留
    assert library.roguelite.boss.enemies == boss.enemies

    out = apply_config(library, AttritionConfig(boss_reinforce_round=4, boss_reinforce_delta=-1))
    events = [e for e in out.maps[boss.map].events if isinstance(e, SpawnUnitsEvent)]
    assert [e.round for e in events] == [4] * len(base_events)
    assert [len(e.units) for e in events] == [len(e.units) - 1 for e in base_events]

    out = apply_config(library, AttritionConfig(boss_reinforce_round=NO_REINFORCE))
    assert not [e for e in out.maps[boss.map].events if isinstance(e, SpawnUnitsEvent)]
    assert "無援軍" in AttritionConfig(boss_reinforce_round=NO_REINFORCE).label
