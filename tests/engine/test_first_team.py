"""先手陣營與開場狀態（Phase 5A-6；``BattleSetup.first_team``、``UnitSpawn.opening_statuses``）。"""

from __future__ import annotations

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.engine import build_setup
from trpg.engine.battle import begin_battle
from trpg.engine.setup import BattleSetup
from trpg.shared.types import Team


def _setup(**updates: object) -> BattleSetup:
    setup = build_setup(library(), "test_flat_6x6", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    return setup.model_copy(update=updates) if updates else setup


def _teams(setup: BattleSetup, seed: int) -> list[Team]:
    state = begin_battle(setup, seed).state
    return [state.units[uid].team for uid in state.turn_order]


def test_default_is_unchanged() -> None:
    base = _setup()
    for seed in range(5):
        plain = begin_battle(base, seed).state
        explicit = begin_battle(_setup(first_team=None), seed).state
        assert plain.turn_order == explicit.turn_order


def test_first_team_leads_turn_order_keeping_initiative() -> None:
    for seed in range(8):
        base = begin_battle(_setup(), seed).state
        for first in Team:
            teams = _teams(_setup(first_team=first), seed)
            count = sum(1 for t in teams if t is first)
            assert teams[:count] == [first] * count
            state = begin_battle(_setup(first_team=first), seed).state
            leading = [u for u in base.turn_order if base.units[u].team is first]
            assert state.turn_order[:count] == leading
            assert state.active_unit == leading[0]


def test_opening_statuses_are_applied() -> None:
    setup = _setup()
    hero = setup.units[0].model_copy(update={"opening_statuses": ("weaken", "guarded")})
    setup = setup.model_copy(update={"units": (hero, *setup.units[1:])})
    state = begin_battle(setup, 3).state
    first_ally = next(u for u in state.units_sorted() if u.team is Team.ALLY)
    assert first_ally.has_status("weaken")
    assert first_ally.has_status("guarded")
    others = [u for u in state.units_sorted() if u.id != first_ally.id]
    assert not any(u.has_status("weaken") for u in others)
