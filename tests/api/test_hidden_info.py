"""HID-1：隱蔽中的敵人只藏資訊（05 5.1.2，玩法決定 #144）。

伺服器依觀看者陣營遮住隱蔽敵人的 HP、護盾、狀態（揭露、隱蔽解除或和我方上下左右相鄰時完整），
事件與紀錄文字不寫出剩餘 HP；自己的傷害數字照常；引擎投影、重播與存檔照完整狀態。
"""

from __future__ import annotations

from tests.engine.helpers import library, with_rolls
from tests.engine.skill_helpers import U1, U2, U3
from tests.engine.test_facing_backstab import duel
from trpg.api.hidden_info import hidden_unit_ids, mask_outcomes
from trpg.api.presenter import team_events_out, traits_view
from trpg.api.schemas import OutcomeOut
from trpg.engine import project_for, resolve
from trpg.engine.actions import Attack
from trpg.engine.events import DamageDealt, StatusApplied, StatusRemoved
from trpg.engine.state import BattleState, StatusInstance, state_from_json, state_to_json
from trpg.engine.view import UnitView
from trpg.narrative.events import describe_event
from trpg.shared.types import Team, UnitId


def _concealed(state: BattleState, unit_id: UnitId = U2) -> BattleState:
    out = state.clone()
    out.units[unit_id].statuses.append(StatusInstance("concealed", 3))
    out.units[unit_id].statuses.append(StatusInstance("shielded", 3, amount=7))
    out.units[unit_id].statuses.append(StatusInstance("burning", 2))
    return out


def _unit(state: BattleState, unit_id: str, team: Team = Team.ALLY) -> UnitView:
    view = traits_view(state, team, library(), U1)
    return next(u for u in view.units if u.id == unit_id)


def _assert_hidden(u: UnitView) -> None:
    assert u.hidden_info is True
    assert (u.hp, u.shield, u.statuses, u.stacks) == (None, None, (), {})


def _assert_full(u: UnitView) -> None:
    assert u.hidden_info is None
    assert u.hp is not None and u.shield is not None


def test_concealed_enemy_hides_hp_shield_and_statuses_but_keeps_position_and_name() -> None:
    state = _concealed(duel((0, 3), weapon="bow", skills=()))
    foe = _unit(state, U2)
    _assert_hidden(foe)
    assert (foe.pos.x, foe.pos.y) == (3, 3)
    assert foe.name_zh and foe.max_hp == 999
    _assert_full(_unit(state, U1))  # 自己的單位不受影響


def test_adjacent_ally_or_summon_reveals_full_info() -> None:
    _assert_full(_unit(_concealed(duel((2, 3))), U2))  # 主角在左邊相鄰
    third = _concealed(duel((0, 0), extra=((Team.ALLY, (3, 4)),)))  # 另一個我方在下方相鄰
    _assert_full(_unit(third, U2))
    diagonal = _concealed(duel((2, 2)))  # 斜角不算相鄰
    _assert_hidden(_unit(diagonal, U2))


def test_revealed_or_no_longer_concealed_shows_full_info() -> None:
    state = _concealed(duel((0, 3), weapon="bow", skills=()))
    revealed = state.clone()
    revealed.units[U2].statuses.append(StatusInstance("revealed", 2))
    _assert_full(_unit(revealed, U2))
    lifted = state.clone()
    lifted.units[U2].statuses = [s for s in lifted.units[U2].statuses if s.status_id != "concealed"]
    foe = _unit(lifted, U2)
    _assert_full(foe)
    assert foe.shield == 7 and {s.status_id for s in foe.statuses} == {"shielded", "burning"}


def test_info_goes_back_to_unknown_when_the_condition_ends() -> None:
    near = _concealed(duel((2, 3)))
    _assert_full(_unit(near, U2))
    away = near.clone()
    away.units[U1].pos = away.units[U1].pos.model_copy(update={"x": 0})
    _assert_hidden(_unit(away, U2))
    downed = away.clone()
    downed.units[U2].downed = True  # 倒下的看得到（已經不在場上）
    assert U2 not in hidden_unit_ids(downed, Team.ALLY)


def test_symmetric_for_the_enemy_side() -> None:
    state = _concealed(duel((0, 3), weapon="bow", skills=()), U1)
    _assert_hidden(_unit(state, U1, Team.ENEMY))
    _assert_full(_unit(state, U1, Team.ALLY))
    assert hidden_unit_ids(state, Team.ENEMY) == {U1}
    assert hidden_unit_ids(state, Team.ALLY) == frozenset()


def test_my_damage_number_is_shown_but_not_the_remaining_hp() -> None:
    state = _concealed(duel((1, 3), weapon="bow", skills=()))
    result = resolve(with_rolls(state, [(20, 18), (20, 18)]), Attack(unit_id=U1, target_id=U2))
    damage = [e for e in result.events if isinstance(e, DamageDealt) and e.target_id == U2]
    assert damage and damage[0].amount > 0
    assert U2 in hidden_unit_ids(result.state, Team.ALLY)
    out = team_events_out(result.events, result.state, Team.ALLY)
    dealt = [d for d in out if d["type"] == "damage_dealt" and d["target_id"] == U2]
    assert dealt[0]["amount"] == damage[0].amount
    assert dealt[0]["hp_before"] is None and dealt[0]["hp_after"] is None
    assert "HP" not in dealt[0]["text"] and str(damage[0].amount) in dealt[0]["text"]
    absorbed = [d for d in out if d["type"] == "shield_absorbed"]
    assert all(d["remaining"] is None and "剩餘" not in d["text"] for d in absorbed)
    # 全知（CLI、重播）照寫剩餘 HP
    full = describe_event(damage[0], result.state)
    assert full is not None and f"→ {damage[0].hp_after}" in full


def _status_on_u2(status_id: str, source_id: UnitId) -> StatusApplied:
    return StatusApplied(
        seq=1,
        round=1,
        target_id=U2,
        duration=2,
        refreshed=False,
        status_id=status_id,
        source_id=source_id,
    )


def test_status_events_on_hidden_enemies_only_from_my_side() -> None:
    state = _concealed(duel((0, 3), weapon="bow", skills=(), extra=((Team.ENEMY, (5, 5)),)))
    mine = _status_on_u2("burning", U1)
    theirs = _status_on_u2("shielded", U3)
    ended = StatusRemoved(seq=2, round=1, target_id=U2, status_id="burning", reason="expired")
    out = team_events_out([mine, theirs, ended], state, Team.ALLY)
    assert [(d["type"], d["source_id"]) for d in out] == [("status_applied", U1)]
    seen_by_enemy = team_events_out([mine, theirs, ended], state, Team.ENEMY)
    assert len(seen_by_enemy) == 3  # 對自己陣營不藏


def test_replay_and_save_keep_the_full_state() -> None:
    state = _concealed(duel((0, 3), weapon="bow", skills=()))
    restored = state_from_json(state_to_json(state))
    foe = restored.units[U2]
    assert foe.hp == 999 and foe.has_status("concealed") and foe.has_status("burning")
    engine_view = next(u for u in project_for(restored, Team.ALLY).units if u.id == U2)
    _assert_full(engine_view)  # 引擎投影一律完整，只有 API 遮


def test_preview_drops_downed_and_shield_outcomes_of_hidden_units() -> None:
    outcomes = (
        OutcomeOut(kind="damaged", unit_id=U2, object_id=None, pos=None, detail="attack"),
        OutcomeOut(kind="downed", unit_id=U2, object_id=None, pos=None, detail=None),
        OutcomeOut(kind="shield", unit_id=U2, object_id=None, pos=None, detail=None),
        OutcomeOut(kind="downed", unit_id=U3, object_id=None, pos=None, detail=None),
    )
    kept = mask_outcomes(outcomes, frozenset({U2}))
    assert [(o.kind, o.unit_id) for o in kept] == [("damaged", U2), ("downed", U3)]
