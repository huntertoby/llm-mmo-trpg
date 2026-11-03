"""休戰（``truce``）與 ``expires: round_end``（Phase 5F-4b；循環賽第 1 輪不能造成傷害）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.content.battle import StatusDef
from trpg.engine import EndTurn, build_setup, resolve
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.events import DamageDealt, StatusRemoved
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup


def _setup(statuses: tuple[str, ...]) -> BattleSetup:
    setup = build_setup(library(), "test_flat_6x6", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    units = tuple(u.model_copy(update={"opening_statuses": statuses}) for u in setup.units)
    return setup.model_copy(update={"units": units})


def test_truce_status_content() -> None:
    truce = library().ruleset.status_def("league_truce")
    assert truce.truce and truce.expires == "round_end" and truce.duration == 1
    assert truce.polarity == "neutral"  # 不被淨化、驅散、奪取


def test_truce_must_be_neutral() -> None:
    with pytest.raises(ValueError, match="truce"):
        StatusDef(
            id="bad_truce",
            name_zh="壞",
            description_zh="壞",
            duration=1,
            expires="round_end",
            polarity="debuff",
            truce=True,
        )
    with pytest.raises(ValueError, match="round_end"):
        StatusDef(
            id="bad_round",
            name_zh="壞",
            description_zh="壞",
            expires="round_end",
            polarity="neutral",
        )


def test_round_end_expiry() -> None:
    """``round_end``：第 1 輪結束時所有人一起移除（不是各自的回合結束）。"""
    state = begin_battle(_setup(("league_truce",)), 3).state
    seen_turn_ends = 0
    while state.round == 1 and not state.ended:
        assert state.active_unit is not None
        assert all(u.has_status("league_truce") for u in state.units_sorted())
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
        seen_turn_ends += 1
    assert seen_turn_ends == len(DEMO_ALLIES) + len(DEMO_ENEMIES)
    assert state.round == 2
    assert not any(u.has_status("league_truce") for u in state.units_sorted())


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_truce_blocks_all_round_one_damage(seed: int) -> None:
    setup = _setup(("league_truce",))
    run = run_battle(setup, seed, CommandedAI(UtilityAI(library().ai_profiles), {}))
    assert not [e for e in run.events if e.round == 1 and isinstance(e, DamageDealt)]
    removed = [
        e
        for e in run.events
        if isinstance(e, StatusRemoved) and e.status_id == "league_truce" and e.round == 1
    ]
    assert len(removed) == len(setup.units)
    assert [e for e in run.events if isinstance(e, DamageDealt)]  # 第 2 輪起照常
    assert replay(setup, seed, run.actions).state == run.state


def test_without_truce_round_one_has_damage() -> None:
    """對照：沒有休戰時同樣的設定第 1 輪就會有傷害（確認上面的測試量得到東西）。"""
    hits = 0
    for seed in (1, 2, 3, 4):
        run = run_battle(_setup(()), seed, CommandedAI(UtilityAI(library().ai_profiles), {}))
        hits += len([e for e in run.events if e.round == 1 and isinstance(e, DamageDealt)])
    assert hits > 0
