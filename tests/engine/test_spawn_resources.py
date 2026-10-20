"""開場 HP／法力（Phase 3-5a：``UnitSpawn.hp``／``mana``）與指令紀錄還原。"""

from __future__ import annotations

from tests.engine.helpers import library, make_map, make_setup, spawn
from trpg.engine import BattleSetup, build_setup, start_battle, state_to_json
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.orders import FocusTarget, OrderRecord, OrderSet
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.runner import run_battle
from trpg.shared.types import Team, UnitId

FLAT = "000000\n" * 5 + "000000"


def _setup(hp: int | None, mana: int | None) -> BattleSetup:
    m = make_map(FLAT, enemy=[(5, 5)])
    ally = spawn(Team.ALLY, (0, 0), "hero_mage").model_copy(update={"hp": hp, "mana": mana})
    return make_setup(m, [ally, spawn(Team.ENEMY, (5, 5))])


def test_default_spawn_starts_full() -> None:
    ally = start_battle(_setup(None, None), 0).units_sorted()[0]
    assert ally.hp == ally.max_hp
    assert ally.mana == ally.max_mana


def test_spawn_hp_and_mana_are_applied_and_capped() -> None:
    ally = start_battle(_setup(7, 3), 0).units_sorted()[0]
    assert (ally.hp, ally.mana) == (7, 3)
    ally = start_battle(_setup(9999, 9999), 0).units_sorted()[0]
    assert (ally.hp, ally.mana) == (ally.max_hp, ally.max_mana)


def test_none_fields_keep_the_old_battle_bit_for_bit() -> None:
    lib = library()
    setup = build_setup(lib, "open_plain", ["hero_fighter"], ["bandit"], max_rounds=10)
    explicit = setup.model_copy(
        update={"units": tuple(u.model_copy(update={"hp": None}) for u in setup.units)}
    )
    a = run_battle(setup, 5)
    b = run_battle(explicit, 5)
    assert state_to_json(a.state) == state_to_json(b.state)


def test_restore_orders_sets_the_current_orders_per_team() -> None:
    ai = CommandedAI(UtilityAI(library().ai_profiles), {})
    first = OrderSet(team_orders=(FocusTarget(target=UnitId("unit_0004")),))
    records = [
        OrderRecord(round=1, team=Team.ALLY, orders=first),
        OrderRecord(round=2, team=Team.ALLY, orders=OrderSet()),
        OrderRecord(round=2, team=Team.ENEMY, orders=first),
    ]
    ai.restore_orders(records)
    assert ai.order_log == records
    assert ai.current_orders(Team.ALLY) == OrderSet()
    assert ai.current_orders(Team.ENEMY) == first
