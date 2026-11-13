"""RG-3（#162 戰場標記前端）要的 API 欄位：瞄準預告會被誰擋（``ChargeOut.lock_blocker_id``）、
落空事件的射出者與擋下的人（``lock_caster_id``／``lock_blocker_id``；RG-3b 起擋下改打讀
``lock_intercepted``）、盾兵掩護的盾兵（``CoverOut.unit_id``）。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.test_lock_on_rg1 import ARCHER, HERO, THIRD, aim, arena
from tests.engine.test_shield_guard_rg1 import GUARD, SHOOTER, WARD, scene
from trpg.api.presenter import preview_response, team_events_out
from trpg.api.telegraph import telegraph_out
from trpg.engine import Attack, preview, resolve
from trpg.engine.actions import EndTurn
from trpg.engine.events import EventBase
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Pos, Team


def _lock_charge(state: BattleState) -> dict[str, object]:
    out = telegraph_out(state, library(), Team.ALLY)
    (charge,) = [c for c in out.charges if c.lock_target_id is not None]
    return charge.model_dump()


def _to_archer_turn(state: BattleState) -> tuple[list[EventBase], BattleState]:
    events: list[EventBase] = []
    s = state
    for _ in range(8):
        assert s.active_unit is not None
        result = resolve(s, EndTurn(unit_id=s.active_unit))
        events += result.events
        s = result.state
        if s.active_unit == ARCHER:
            return events, s
    raise AssertionError("沒有輪回雲鶴使")


def _fizzle(events: list[EventBase], state: BattleState) -> dict[str, object]:
    out = team_events_out(events, state, Team.ALLY)
    (fizzle,) = [
        e for e in out if e["type"] == "effect_fizzled" and str(e["reason"]).startswith("lock_on")
    ]
    return fizzle


def test_the_telegraph_names_who_would_block_the_shot() -> None:
    state = aim(arena(third=(Team.ALLY, (2, 0), "bandit"))).state
    assert _lock_charge(state)["lock_blocker_id"] is None
    state.units[THIRD].pos = Pos(x=4, y=4)
    charge = _lock_charge(state)
    assert charge["lock_target_id"] == HERO and charge["lock_blocker_id"] == THIRD


def test_the_archers_own_side_is_not_a_blocker() -> None:
    state = aim(arena(third=(Team.ENEMY, (4, 4), "bandit"))).state
    assert _lock_charge(state)["lock_blocker_id"] is None


def test_an_intercepted_shot_names_the_caster_and_the_blocker() -> None:
    """RG-3b（AF-1）：隊友擋在中間時改打擋住的人、不再落空；「被擋下」讀 ``lock_intercepted``
    自帶的 ``unit_id``／``blocker_id``，沒有 ``lock_on_*`` 落空事件。"""
    state = aim(arena(third=(Team.ALLY, (2, 0), "bandit"))).state
    state.units[THIRD].pos = Pos(x=4, y=4)
    events, after = _to_archer_turn(state)
    out = team_events_out(events, after, Team.ALLY)
    (caught,) = [e for e in out if e["type"] == "lock_intercepted"]
    assert caught["unit_id"] == ARCHER and caught["target_id"] == HERO
    assert caught["blocker_id"] == THIRD and "text" in caught
    assert not [e for e in out if str(e.get("reason", "")).startswith("lock_on")]
    shot = [e for e in out if e["type"] == "attack_rolled" and e.get("attacker_id") == ARCHER]
    assert [e["target_id"] for e in shot] == [THIRD]


def test_a_blocker_who_cannot_be_picked_still_fizzles_with_the_blocker() -> None:
    """擋住的人本身選不到（2 格外的隱蔽）才照舊 ``lock_on_blocked`` 落空：引擎事件沒有擋住的人，
    API 仍推算 ``lock_blocker_id``。"""
    state = aim(arena(third=(Team.ALLY, (2, 0), "bandit"))).state
    state.units[THIRD].pos = Pos(x=4, y=4)  # 離弓手 3 格
    state.units[THIRD].statuses.append(StatusInstance("concealed", remaining=3))
    events, after = _to_archer_turn(state)
    out = team_events_out(events, after, Team.ALLY)
    assert not [e for e in out if e["type"] == "lock_intercepted"]
    fizzle = _fizzle(events, after)
    assert fizzle["reason"] == "lock_on_blocked"
    assert fizzle["lock_caster_id"] == ARCHER and fizzle["lock_blocker_id"] == THIRD


def test_a_plain_miss_carries_only_the_caster() -> None:
    state = aim(arena(third=(Team.ALLY, (11, 8), "bandit"))).state  # 還有人在場：戰鬥不結束
    state.units[HERO].downed = True
    events, after = _to_archer_turn(state)
    fizzle = _fizzle(events, after)
    assert fizzle["reason"] == "lock_on_lost"
    assert fizzle["lock_caster_id"] == ARCHER and "lock_blocker_id" not in fizzle


def test_the_preview_cover_names_the_shield_guard() -> None:
    state = scene()
    p = preview_response(preview(state, Attack(unit_id=SHOOTER, target_id=WARD)), state)
    assert p.cover is not None and p.cover.kind == "shield_guard" and p.cover.unit_id == GUARD


def test_object_cover_has_no_unit() -> None:
    state = scene(guard_at=(8, 8))
    p = preview_response(preview(state, Attack(unit_id=SHOOTER, target_id=WARD)), state)
    assert p.cover is None or p.cover.unit_id is None
