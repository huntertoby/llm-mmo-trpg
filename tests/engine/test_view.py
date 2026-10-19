"""Phase 3-1 3.1：依陣營過濾的戰場視圖 ``project_for``。"""

from __future__ import annotations

import json
from dataclasses import replace

from tests.engine.helpers import give_turn
from tests.engine.skill_helpers import U1, U2, U3
from tests.engine.test_pending_serialization import _two_guards
from tests.engine.test_reactions import P, _prompt_state
from tests.engine.test_traps import BEAR, CINDER, place, scene
from trpg.engine import Move, resolve
from trpg.engine.view import BattleView, project_for
from trpg.shared.types import Team

FORBIDDEN_KEYS = {
    "rng_state",
    "seed",
    "ruleset",
    "base_state_json",
    "action_json",
    "decisions",
    "events_emitted",
}


def _keys(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            found |= _keys(value)
    elif isinstance(node, list):
        for item in node:
            found |= _keys(item)
    return found


def test_the_view_has_no_hidden_fields() -> None:
    paused = resolve(_prompt_state(), Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0)))).state
    for state in (scene(), place(scene(), BEAR, (4, 3)), paused):
        for team in Team:
            text = project_for(state, team).model_dump_json()
            assert not _keys(json.loads(text)) & FORBIDDEN_KEYS
            for word in FORBIDDEN_KEYS - {"seed", "decisions"}:
                assert word not in text


def test_an_enemy_trap_is_invisible_to_the_other_team() -> None:
    state = place(scene(), BEAR, (4, 3))
    enemy_text = project_for(state, Team.ENEMY).model_dump_json()
    assert project_for(state, Team.ENEMY).traps == ()
    assert BEAR not in enemy_text
    assert '"x":4,"y":3}' not in enemy_text  # 沒有 pos 形式的陷阱位置


def test_the_owner_team_sees_its_own_traps_only() -> None:
    state = place(give_turn(place(scene(), BEAR, (4, 3)), U1), CINDER, (3, 2))
    view = project_for(state, Team.ALLY)
    assert [(t.skill_id, t.pos.x, t.pos.y, t.owner_id) for t in view.traps] == [
        (CINDER, 3, 2, U1),
        (BEAR, 4, 3, U1),
    ]  # 依 (y, x) 排序
    assert project_for(state, Team.ENEMY).traps == ()


def test_a_trap_placed_by_the_enemy_is_visible_only_to_the_enemy() -> None:
    state = place(scene(), BEAR, (4, 3))
    state.traps = [replace(t, team=Team.ENEMY) for t in state.traps]
    assert project_for(state, Team.ALLY).traps == ()
    (trap,) = project_for(state, Team.ENEMY).traps
    assert trap.team is Team.ENEMY and trap.skill_id == BEAR


def test_a_paused_state_has_a_view_with_only_the_public_pending_fields() -> None:
    paused = resolve(_two_guards(), Move(unit_id=U3, path=(P(2, 0), P(3, 0), P(4, 0)))).state
    view = project_for(paused, Team.ALLY)
    assert view.pending is not None and view.pending.unit_id == U1
    assert set(view.pending.model_dump()) == {
        "kind",
        "unit_id",
        "reaction",
        "trigger_unit_id",
        "skill_id",
        "copy_skill_id",
        "trigger_event_seq",
        "stamina_cost",
        "mana_cost",
        "hp_cost_permille",
    }
    assert project_for(_two_guards(), Team.ALLY).pending is None


def test_the_view_is_deterministic_and_round_trips_through_json() -> None:
    state = place(scene(), BEAR, (4, 3))
    first = project_for(state, Team.ALLY).model_dump_json()
    assert project_for(state.clone(), Team.ALLY).model_dump_json() == first
    assert BattleView.model_validate_json(first) == project_for(state, Team.ALLY)


def test_the_view_describes_the_map_and_units() -> None:
    state = scene()
    view = project_for(state, Team.ENEMY)
    assert view.team is Team.ENEMY
    assert (view.width, view.height) == (state.width, state.height)
    assert len(view.tiles) == state.width * state.height
    assert [(t.x, t.y) for t in view.tiles[:3]] == [(0, 0), (1, 0), (2, 0)]  # 列優先
    assert [u.id for u in view.units] == sorted(state.units)
    mage = next(u for u in view.units if u.id == U1)
    unit = state.units[U1]
    assert (mage.hp, mage.mana, mage.stamina, mage.ap) == (
        unit.hp,
        unit.mana,
        unit.stamina,
        unit.ap,
    )
    assert view.active_unit == U1 and view.round == state.round
    assert view.ended is False and view.winner is None
