"""Phase BAL-21a：頭目進入新階段時回復法力（``BossPhase.mana_restore``，預設不回復）。

行為一致測試：合成頭目（不改 ``content/``），實際跑引擎觸發階段（HP 門檻＋結束回合，同
``test_boss_phases.py``），再用 ``run_battle``／``replay`` 確認重播一致。
"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import give_turn, library, make_setup, spawn, template
from trpg.content.battle import UnitTemplate
from trpg.engine import BattleState, resolve
from trpg.engine.actions import EndTurn
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import start_battle
from trpg.engine.events import BossPhaseChanged, EffectFizzled, ResourceRestored
from trpg.engine.results import ResolveResult
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import BattleSetup, with_phase_assets
from trpg.engine.state import state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.types import Team, UnitId

HERO = UnitId("unit_0001")
BOSS = UnitId("unit_0002")


def _phases(restore: int | None) -> tuple[dict[str, Any], ...]:
    two: dict[str, Any] = {
        "id": "two",
        "name_zh": "二",
        "trigger": {"kind": "hp_below", "permille": 600},
        "text_zh": "火又旺了起來。",
    }
    if restore is not None:
        two["mana_restore"] = restore
    return ({"id": "one", "name_zh": "一"}, two)


def _boss(restore: int | None) -> UnitTemplate:
    return template(
        "bandit",
        max_hp=100,
        max_mana=40,
        tags=("boss", "humanoid"),
        skills=(),
        phases=_phases(restore),
        reactions=(),
    )


def _setup(restore: int | None, *, boss_mana: int | None = None) -> BattleSetup:
    lib = library()
    hero = template("hero_fighter", reactions=())
    boss = spawn(Team.ENEMY, (4, 0), _boss(restore)).model_copy(update={"mana": boss_mana})
    setup = make_setup(
        lib.map("test_flat_6x6"), [spawn(Team.ALLY, (0, 4), hero), boss], max_rounds=30
    )
    return with_phase_assets(lib, setup)


def _enter_phase_two(restore: int | None, mana: int) -> tuple[BattleState, ResolveResult]:
    state = give_turn(start_battle(_setup(restore), 0), HERO)
    state.units[BOSS].hp = 50
    state.units[BOSS].mana = mana
    return state, resolve(state, EndTurn(unit_id=HERO))


def _restored(result: ResolveResult) -> list[ResourceRestored]:
    return [e for e in result.events if isinstance(e, ResourceRestored)]


def test_the_default_restores_nothing() -> None:
    _, result = _enter_phase_two(None, 5)
    assert [e.phase_id for e in result.events if isinstance(e, BossPhaseChanged)] == ["two"]
    assert result.state.units[BOSS].mana == 5
    assert _restored(result) == []


def test_entering_the_phase_restores_mana() -> None:
    _, result = _enter_phase_two(20, 5)
    boss = result.state.units[BOSS]
    assert boss.mana == 25
    (event,) = _restored(result)
    assert (event.unit_id, event.source_id, event.resource, event.amount, event.mana_after) == (
        BOSS,
        BOSS,
        "mana",
        20,
        25,
    )
    order = [type(e).__name__ for e in result.events]
    assert order.index("BossPhaseChanged") < order.index("ResourceRestored")
    assert describe_event(event, result.state)


def _max_mana() -> int:
    return start_battle(_setup(None), 0).units[BOSS].max_mana


def test_the_restore_is_capped_at_max_mana() -> None:
    top = _max_mana()
    _, result = _enter_phase_two(30, top - 15)
    assert result.state.units[BOSS].mana == top
    assert [e.amount for e in _restored(result)] == [15]


def test_a_full_boss_gets_no_event() -> None:
    top = _max_mana()
    _, result = _enter_phase_two(30, top)
    assert result.state.units[BOSS].mana == top
    assert _restored(result) == []
    assert not any(isinstance(e, EffectFizzled) for e in result.events)


def test_a_battle_with_a_restore_replays_exactly() -> None:
    setup = _setup(20, boss_mana=3)  # 頭目沒有技能、不花法力：進第二階段時一定從 3 回到 23
    run = run_battle(setup, 2, UtilityAI(library().ai_profiles))
    assert [e.phase_id for e in run.events if isinstance(e, BossPhaseChanged)] == ["two"]
    restored = [e for e in run.events if isinstance(e, ResourceRestored) and e.unit_id == BOSS]
    assert [(e.amount, e.mana_after) for e in restored] == [(20, 23)]
    again = replay(setup, 2, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
