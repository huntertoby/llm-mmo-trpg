"""遭遇的敵方陣容（Phase 5A-3；``docs/phases/Phase5計畫.md`` 7.2 第 5 項）。"""

from __future__ import annotations

import dataclasses
from collections import Counter

import pytest

from tests.world.helpers import NOON
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng, fnv1a64
from trpg.world.encounters import (
    EncounterLineup,
    LineupMember,
    lineup_rng,
    lineup_templates,
    roll_lineup,
)
from trpg.world.errors import WorldError
from trpg.world.state import EncounterResult

SEEDS = range(200)


def _encounter(location: str, seed: int, region: str = "cloud_ridge") -> EncounterResult:
    return EncounterResult(
        region=region,
        location=location,
        level=3,
        battle_map=None,
        battle_seed=seed,
        weather="fog",
        day_phase="day",
        at=NOON,
    )


def _with_camp_elite(library: ContentLibrary, permille: int) -> ContentLibrary:
    table = library.world_encounters["cloud_ridge"]
    changed = table.model_copy(update={"camp_elite_permille": permille})
    return dataclasses.replace(library, world_encounters={"cloud_ridge": changed})


def test_rng_derivation() -> None:
    expected = Rng(fnv1a64(b"42:lineup")).randint(0, 999)
    assert lineup_rng(42).randint(0, 999) == expected


def test_roll_is_deterministic(library: ContentLibrary) -> None:
    for seed in (0, 7, 123456):
        first = roll_lineup(library, _encounter("bamboo_path", seed))
        assert roll_lineup(library, _encounter("bamboo_path", seed)) == first
    groups = {roll_lineup(library, _encounter("bamboo_path", s)).group for s in SEEDS}
    assert groups == {"mist_wolf_pack", "bandit_wolf_handler"}  # 不同種子會抽到不同陣容


def test_lineup_comes_from_location_table(library: ContentLibrary) -> None:
    table = library.world_encounters["cloud_ridge"]
    groups = table.group_by_id()
    for entry in table.locations:
        allowed = {g.group for g in entry.groups}
        for seed in range(20):
            lineup = roll_lineup(library, _encounter(entry.location, seed))
            assert lineup.group in allowed
            units = [m.unit for m in lineup.members]
            if entry.elite is None:
                assert units == list(groups[lineup.group].units)


def test_north_slope_has_the_wolf_king(library: ContentLibrary) -> None:
    for seed in range(20):
        lineup = roll_lineup(library, _encounter("north_slope", seed))
        assert lineup.members[0] == LineupMember(unit="mist_wolf", affix="berserk")
        assert len(lineup.members) == 4
        assert sum(m.affix is not None for m in lineup.members) == 1
        templates = lineup_templates(library, lineup)
        assert templates[0].name_zh == "狂暴的霧狼"


def test_camp_elite_never_when_zero(library: ContentLibrary) -> None:
    never = _with_camp_elite(library, 0)
    for seed in SEEDS:
        assert not roll_lineup(never, _encounter("ferry_steps", seed)).has_elite_affix


def test_camp_elite_always_when_full(library: ContentLibrary) -> None:
    always = _with_camp_elite(library, 1000)
    table = always.world_encounters["cloud_ridge"]
    catalog = always.enemy_catalog()
    for seed in SEEDS:
        lineup = roll_lineup(always, _encounter("ferry_steps", seed))
        original = table.group_by_id()[lineup.group].units
        assert [m.unit for m in lineup.members] == list(original)  # 人數與成員不變
        upgraded = [m for m in lineup.members if m.affix is not None]
        assert len(upgraded) == 1
        member = upgraded[0]
        assert member.affix in table.affixes
        assert catalog.affix_problem(catalog.template(member.unit), member.affix) is None


def test_camp_elite_rate_is_close_to_table(library: ContentLibrary) -> None:
    hits = sum(
        roll_lineup(library, _encounter("ferry_steps", s)).has_elite_affix for s in range(2000)
    )
    assert 100 <= hits <= 300  # 100‰ × 2000 ≈ 200


def test_camp_with_elite_group_does_not_mix(library: ContentLibrary) -> None:
    always = _with_camp_elite(library, 1000)
    seen = Counter[str]()
    for seed in SEEDS:
        lineup = roll_lineup(always, _encounter("cliff_gang_fort", seed))
        seen[lineup.group] += 1
        if lineup.group == "cliff_gang_core":  # 已有盜賊隊長（精英）
            assert not lineup.has_elite_affix
        else:
            assert lineup.has_elite_affix
    assert set(seen) == {"cliff_gang_core", "cliff_gang_hounds"}


@pytest.mark.parametrize("location", ["hunter_hut", "herb_valley", "crystal_rift", "elixir_cave"])
def test_non_camp_locations_never_mix(library: ContentLibrary, location: str) -> None:
    always = _with_camp_elite(library, 1000)
    for seed in range(50):
        assert not roll_lineup(always, _encounter(location, seed)).has_elite_affix


def test_lineup_templates_resolve_variants(library: ContentLibrary) -> None:
    lineup = EncounterLineup(
        region="cloud_ridge",
        location="sword_tomb",
        group="tomb_swordsmen",
        members=(
            LineupMember(unit="sect_swordsman"),
            LineupMember(unit="thunder_talisman_caster"),
            LineupMember(unit="frost_crane_archer", affix="regenerating"),
        ),
    )
    templates = lineup_templates(library, lineup)
    assert [t.id for t in templates] == [
        "sect_swordsman",
        "thunder_talisman_caster",
        "frost_crane_archer_regenerating",
    ]
    assert templates[2].name_zh == "再生的冰鶴使"
    assert "elite" in templates[2].tags
    catalog = library.enemy_catalog()
    assert sum(catalog.is_ranged(t) for t in templates) == 2


def test_rolled_lineups_respect_ranged_cap(library: ContentLibrary) -> None:
    always = _with_camp_elite(library, 1000)
    table = always.world_encounters["cloud_ridge"]
    catalog = always.enemy_catalog()
    for entry in table.locations:
        for seed in range(10):
            templates = lineup_templates(
                always, roll_lineup(always, _encounter(entry.location, seed))
            )
            assert sum(catalog.is_ranged(t) for t in templates) <= table.ranged_cap
            assert sum(catalog.is_elite(t) for t in templates) <= 1


def test_unknown_region_or_location(library: ContentLibrary) -> None:
    with pytest.raises(WorldError, match="沒有遭遇表"):
        roll_lineup(library, _encounter("ferry_steps", 1, region="ashen_waste"))
    with pytest.raises(WorldError, match="沒有遭遇表"):
        roll_lineup(library, _encounter("mist_ferry", 1))
