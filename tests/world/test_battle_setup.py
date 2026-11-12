"""遇敵的開戰設定（Phase 5A-4；``docs/phases/Phase5計畫.md`` 9.3）。"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.world.helpers import make_encounter
from trpg.content.library import ContentLibrary
from trpg.shared.types import Team
from trpg.world.battle import encounter_map, hero_start_hp, prepare_battle, reskin
from trpg.world.encounters import roll_lineup
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState
from trpg.world.step import max_hp

MakeChar = Callable[..., CharacterState]


def test_location_map_is_used_and_reskinned(library: ContentLibrary) -> None:
    encounter = make_encounter("ferry_steps", battle_map="cliff_outpost")
    map_def = encounter_map(library, encounter)
    assert map_def.id == "cliff_outpost"
    assert map_def.region == "cloud_ridge"
    original = library.map("cliff_outpost")
    if original.region != "cloud_ridge":
        assert library.regions is not None
        assert map_def.look == library.regions.region_by_id()["cloud_ridge"].look
    # 機制不動：只換外觀
    assert map_def.terrain == original.terrain
    assert map_def.archetype == original.archetype


def test_reskin_same_region_is_identity(library: ContentLibrary) -> None:
    forest = library.map("dark_forest")
    assert forest.region is not None
    assert reskin(library, forest, forest.region) is forest


def test_location_without_map_draws_from_region_pool(library: ContentLibrary) -> None:
    assert library.regions is not None
    pool = set(library.regions.region_by_id()["cloud_ridge"].map_pool)
    picked = set()
    for seed in range(30):
        encounter = make_encounter("old_pine_altar", seed=seed, level=3)
        map_def = encounter_map(library, encounter)
        assert map_def.archetype in pool
        assert map_def.archetype != "boss"
        assert map_def.region == "cloud_ridge"
        assert encounter_map(library, encounter).id == map_def.id  # 確定性
        picked.add(map_def.id)
    assert len(picked) > 1


def test_setup_units_weather_and_seed(library: ContentLibrary, make_char: MakeChar) -> None:
    encounter = make_encounter("rain_terraces", seed=11, battle_map="swamp", weather="rain")
    char = make_char(location="rain_terraces", pending_encounter=encounter, hp=17, mana=3)
    prepared = prepare_battle(library, char)
    setup = prepared.setup
    assert prepared.seed == 11
    assert setup.weather is not None
    assert setup.weather.id == "rain"
    assert setup.max_rounds == 30
    allies = [u for u in setup.units if u.team is Team.ALLY]
    enemies = [u for u in setup.units if u.team is Team.ENEMY]
    assert setup.units[0].template.id == char.hero.id
    assert setup.units[0].hp == 17
    assert setup.units[0].mana == 3
    # 新角色預設只帶賽倫（5C-3；#154）
    assert [u.template.id for u in allies[1:]] == ["merc_tiebi"]
    lineup = roll_lineup(library, encounter)
    assert prepared.lineup == lineup
    assert len(enemies) == len(lineup.members)


def test_fatigue_caps_opening_hp(library: ContentLibrary, make_char: MakeChar) -> None:
    char = make_char()
    full = max_hp(library, char)
    assert hero_start_hp(library, char) == full
    tired = char.model_copy(update={"fatigued": True})
    assert hero_start_hp(library, tired) == full * 800 // 1000
    low = tired.model_copy(update={"hp": 3})
    assert hero_start_hp(library, low) == 3
    assert hero_start_hp(library, char.model_copy(update={"hp": 0})) == 1
    encounter = make_encounter("ferry_steps", battle_map="cliff_outpost")
    prepared = prepare_battle(library, tired.model_copy(update={"pending_encounter": encounter}))
    assert prepared.hero_hp == full * 800 // 1000
    assert prepared.setup.units[0].hp == full * 800 // 1000


def test_no_encounter_is_rejected(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError, match="沒有遭遇"):
        prepare_battle(library, make_char())
