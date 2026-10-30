"""Boss 地圖盜賊巢穴與盜賊首領（Phase 3-5b）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.sessions import playable_maps
from trpg.cli.sim import default_sim_maps
from trpg.content.maps import BOSS_ARCHETYPE, check_map
from trpg.content.roguelite import roguelite_problems
from trpg.engine.events import UnitSpawned
from trpg.roguelite.start import new_run
from trpg.sim.batch import map_spec
from trpg.sim.metrics import run_tracked

LAIR = "bandit_lair"


def test_lair_passes_content_validation_and_has_the_required_features() -> None:
    lib = library()
    arena = lib.map(LAIR)
    rules = lib.ruleset
    assert arena.archetype == BOSS_ARCHETYPE
    assert check_map(arena, rules.terrain.by_id(), rules.core, rules.objects.by_id()) == []
    terrain = {t for row in arena.grid() for _h, t in row}
    assert "lava" in terrain
    assert max(int(c) for row in arena.height_rows() for c in row) == 2
    assert len(arena.source_wells) >= 1
    kinds = {o.kind for o in arena.objects}
    assert {"stone_pillar", "crate", "oil_barrel"} <= kinds
    assert any(e.kind == "spawn_units" for e in arena.events)


def test_boss_uses_the_lair_and_the_warlord() -> None:
    lib = library()
    rules = lib.roguelite
    assert rules.boss.map == LAIR
    assert rules.boss.enemies[0] == "bandit_warlord"
    assert roguelite_problems(rules, lib.maps, lib.units, lib.ruleset.core.tier_budget) == []
    warlord, boss = lib.unit("bandit_warlord"), lib.unit("bandit_boss")
    assert {"boss", "elite"} <= set(warlord.tags)
    # BAL-9c：首領 HP 為原型專用的 700‰（60），比 bandit_boss 少；加強版改看護甲與屬性
    assert warlord.armor_bonus > boss.armor_bonus
    assert sum(warlord.attributes.values()) > sum(boss.attributes.values())
    assert 3 <= len(rules.boss.enemies) - 1 <= 4


def test_lair_stays_out_of_the_general_pool_lists_and_sims() -> None:
    lib = library()
    assert LAIR not in lib.roguelite.map_pool
    assert LAIR not in default_sim_maps(lib)
    assert LAIR not in playable_maps(lib)


def test_a_run_plans_the_boss_battle_on_the_lair() -> None:
    lib = library()
    run = new_run(lib, "build_banisher", 3)
    boss = [p for p in run.plan if p.boss]
    assert [p.map_id for p in boss] == [LAIR]
    assert boss[0].enemies[0] == "bandit_warlord"
    assert LAIR not in {p.map_id for p in run.plan if not p.boss}


def test_lair_battle_runs_to_the_end_and_reinforcements_arrive() -> None:
    lib = library()
    spec = map_spec(lib, LAIR, [6])
    run = run_tracked(spec.setup, 6, spec.policy_factory())
    spawned = [e for e in run.events if isinstance(e, UnitSpawned)]
    assert len(spawned) >= 1  # 援軍 1 名（BAL-7 由 2 名減為 1 名）
