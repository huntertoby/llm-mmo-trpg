"""``clone`` 明確列出欄位（效能），這裡確保新增欄位時不會漏掉。"""

from __future__ import annotations

from dataclasses import fields

from tests.engine.helpers import make_map, make_state, spawn
from trpg.engine.state import BattleState, ObjectState, UnitState, state_to_json
from trpg.shared.types import Team

_COPIED = {
    BattleState: {"tiles", "units", "objects", "turn_order", "traps", "zones"},
    UnitState: {
        "statuses",
        "cooldowns",
        "skill_uses",
        "control_dr",
        "trigger_counts",
        "stacks",
        "stack_expiry",
    },
    ObjectState: set(),
}


def _state() -> BattleState:
    m = make_map("000\n000", objects=[(1, 0, "crate")], enemy=[(2, 1)])
    return make_state(m, [spawn(Team.ALLY, (0, 0)), spawn(Team.ENEMY, (2, 1))])


def test_clone_copies_every_field() -> None:
    state = _state()
    unit = next(iter(state.units.values()))
    obj = next(iter(state.objects.values()))
    for instance in (state, unit, obj):
        cls = type(instance)
        for f in fields(cls):
            if f.name in _COPIED[cls]:
                continue
            sentinel = object()
            probe = instance.clone()
            object.__setattr__(probe, f.name, sentinel)
            assert getattr(probe.clone(), f.name) is sentinel, f"{cls.__name__}.{f.name}"


def test_clone_is_independent_and_equal() -> None:
    state = _state()
    copy = state.clone()
    assert copy == state and state_to_json(copy) == state_to_json(state)
    for name in ("tiles", "turn_order"):
        assert getattr(copy, name) is not getattr(state, name)
    for uid, unit in state.units.items():
        assert copy.units[uid] is not unit and copy.units[uid].statuses is not unit.statuses
        assert copy.units[uid].cooldowns is not unit.cooldowns
        assert copy.units[uid].skill_uses is not unit.skill_uses
        assert copy.units[uid].control_dr is not unit.control_dr
        assert copy.units[uid].trigger_counts is not unit.trigger_counts
        assert copy.units[uid].stacks is not unit.stacks
        assert copy.units[uid].stack_expiry is not unit.stack_expiry
    assert copy.traps is not state.traps
    for oid, obj in state.objects.items():
        assert copy.objects[oid] is not obj
    copy.units[next(iter(copy.units))].hp = 1
    copy.objects[next(iter(copy.objects))].hp = 1
    assert state_to_json(copy) != state_to_json(state)


def test_legal_moves_equal_validated_moves() -> None:
    from trpg.engine import Move, legal_actions  # noqa: PLC0415
    from trpg.engine.actions import ACTION_ADAPTER  # noqa: PLC0415

    state = _state()
    moves = [a for a in legal_actions(state) if isinstance(a, Move)]
    assert moves
    for move in moves:
        validated = Move(unit_id=move.unit_id, path=tuple(move.path))
        assert move == validated and hash(move) == hash(validated)
        assert ACTION_ADAPTER.validate_json(ACTION_ADAPTER.dump_json(move)) == move
