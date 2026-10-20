"""靶場地圖與木樁（Phase 3F-1 1.1A、驗收 6）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.cli.sim import default_sim_maps
from trpg.content.library import ContentLibrary
from trpg.content.maps import TRAINING_ARCHETYPE, check_map
from trpg.content.roguelite import roguelite_problems
from trpg.content.workshop import workshop_problems
from trpg.engine.actions import EndTurn
from trpg.engine.events import AttackRolled, UnitMoved
from trpg.engine.runner import BattleRun, run_battle
from trpg.engine.setup import build_setup
from trpg.shared.types import Team
from trpg.sim.commanders import build_commanded_ai
from trpg.sim.lineup import build_allies

DUMMY = "training_dummy"


def test_training_range_and_dummy_pass_content_validation() -> None:
    lib = library()
    arena = lib.map("training_range")
    assert arena.name_zh == "靶場"
    assert arena.archetype == TRAINING_ARCHETYPE
    assert (arena.width, arena.height) == (12, 10)
    rules = lib.ruleset
    assert check_map(arena, rules.terrain.by_id(), rules.core, rules.objects.by_id()) == []
    terrain = {t for row in arena.grid() for _h, t in row}
    assert {"wall", "lava"} <= terrain
    kinds = {o.kind for o in arena.objects}
    assert {"crate", "oil_barrel", "stone_pillar", "dead_tree", "grass"} <= kinds
    assert {s.surface.value for s in arena.surfaces} == {"water"}
    assert max(int(c) for row in arena.height_rows() for c in row) == 2
    assert len(arena.source_wells) == 1
    dummy = lib.unit(DUMMY)
    assert dummy.speed == 0 and dummy.reactions == () and dummy.ai_profile == "idle"
    assert dummy.max_hp >= 200 and not dummy.skills


def test_workshop_rules_offer_dummy_and_fighting_opponents() -> None:
    lib = library()
    rules = lib.workshop
    assert rules.map == "training_range" and rules.max_rounds == 30
    assert [o.id for o in rules.opponents] == ["dummy", "fighting"]
    assert set(rules.opponents[0].enemies) == {DUMMY}
    assert "bandit" in rules.opponents[1].enemies
    assert rules.opponent(None) is rules.opponents[0]
    assert rules.opponent("nope") is None
    bad = rules.model_copy(update={"map": "open_plain"})
    assert "地圖 open_plain 的類型必須是 training，收到 open_plain" in workshop_problems(
        bad, lib.maps, lib.units
    )


def test_training_range_is_kept_out_of_roguelite_and_sims() -> None:
    lib = library()
    assert "training_range" not in lib.roguelite.map_pool
    assert "training_range" not in default_sim_maps(lib)
    pool = (*lib.roguelite.map_pool, "training_range")
    rules = lib.roguelite.model_copy(update={"map_pool": pool})
    problems = roguelite_problems(rules, lib.maps, lib.units, lib.ruleset.core.tier_budget)
    assert "技能工坊的靶場不能進地圖池：training_range" in problems


def _run(lib: ContentLibrary, opponents: str, seed: int) -> BattleRun:
    built, allies = build_allies(lib, ["build_charger"], fill=False)
    chosen = lib.workshop.opponent(opponents)
    assert chosen is not None
    setup = build_setup(
        built, "training_range", allies, chosen.enemies, max_rounds=lib.workshop.max_rounds
    )
    return run_battle(setup, seed, build_commanded_ai(lib.ai_profiles))


@pytest.mark.parametrize(("opponents", "seed"), [("dummy", 0), ("fighting", 1)])
def test_dummies_never_move_or_attack(opponents: str, seed: int) -> None:
    lib = library()
    run = _run(lib, opponents, seed)
    units = run.state.units
    dummies = {uid for uid, u in units.items() if u.template_id == DUMMY}
    assert len(dummies) == 3
    dummy_actions = [a for a in run.actions if getattr(a, "unit_id", None) in dummies]
    assert dummy_actions and all(isinstance(a, EndTurn) for a in dummy_actions)
    assert not [e for e in run.events if isinstance(e, AttackRolled) and e.attacker_id in dummies]
    assert not [
        e
        for e in run.events
        if isinstance(e, UnitMoved) and e.unit_id in dummies and e.mode == "walk"
    ]
    if opponents == "fighting":
        bandits = {uid for uid, u in units.items() if u.template_id == "bandit"}
        assert any(isinstance(e, AttackRolled) and e.attacker_id in bandits for e in run.events), (
            "會反擊的盜賊應該會攻擊"
        )
    assert all(u.team is Team.ENEMY for uid, u in units.items() if uid in dummies)
