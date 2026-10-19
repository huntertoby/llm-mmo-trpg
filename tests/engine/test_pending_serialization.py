"""Phase 3-1 3.3：``Pending`` 的欄位與「序列化 → 反序列化 → resume」往返。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, make_map, make_state, no_reactions, spawn, template
from tests.engine.skill_helpers import FLAT7, of
from tests.engine.test_passive_triggers import always
from tests.engine.test_reaction_skills import RIPOSTE
from tests.engine.test_reactions import PROMPT_OA, U1, U2, U3, P, _prompt_state
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    Move,
    Pending,
    ResolveResult,
    resolve,
    resume,
    state_from_json,
    state_to_json,
)
from trpg.engine.events import EVENT_LIST_ADAPTER, AttackRolled, DamageDealt
from trpg.shared.types import Team

PROMPT_BLOCK = [{"reaction": "block", "when": {"event": "targeted_by_melee"}, "mode": "prompt"}]


def _events_json(result: ResolveResult) -> bytes:
    return EVENT_LIST_ADAPTER.dump_json(result.events)  # type: ignore[arg-type]


def _assert_round_trip(paused: ResolveResult, unit: str, accept: bool) -> ResolveResult:
    """直接 resume 與「狀態存成 JSON 再讀回來 resume」的結果完全相同。"""
    direct = resume(paused.state, Decision(unit_id=unit, accept=accept))  # type: ignore[arg-type]
    restored = state_from_json(state_to_json(paused.state))
    assert state_to_json(restored) == state_to_json(paused.state)
    again = resume(restored, Decision(unit_id=unit, accept=accept))  # type: ignore[arg-type]
    assert state_to_json(again.state) == state_to_json(direct.state)
    assert _events_json(again) == _events_json(direct)
    assert again.pending == direct.pending
    return direct


def test_builtin_reaction_pending_carries_the_public_fields() -> None:
    paused = resolve(_prompt_state(), Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0))))
    pending = paused.pending
    assert pending is not None
    assert pending.kind == "reaction" and pending.skill_id is None
    assert pending.stamina_cost == 0 and pending.mana_cost == 0
    # 藉機攻擊的移動事件尚未發出，找不到引發事件
    assert pending.trigger_event_seq is None
    assert paused.state.pending is not None
    stored = paused.state.pending
    assert (stored.kind, stored.skill_id, stored.trigger_event_seq) == (
        pending.kind,
        pending.skill_id,
        pending.trigger_event_seq,
    )
    assert (stored.stamina_cost, stored.mana_cost) == (pending.stamina_cost, pending.mana_cost)


@pytest.mark.parametrize("accept", [True, False])
def test_round_trip_of_a_paused_state_matches_a_direct_resume(accept: bool) -> None:
    paused = resolve(_prompt_state(), Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0))))
    resumed = _assert_round_trip(paused, U1, accept)
    assert resumed.pending is None and resumed.state.pending is None


def test_block_pending_points_at_the_attack_roll_and_shows_the_stamina_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    guard = template("hero_fighter", reactions=PROMPT_BLOCK)
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (3, 3), guard), spawn(Team.ENEMY, (4, 3), no_reactions())]),
        U2,
    )
    paused = resolve(state, Attack(unit_id=U2, target_id=U1))
    pending = paused.pending
    assert pending is not None and pending.reaction == "block"
    assert pending.skill_id is None
    assert pending.stamina_cost == state.ruleset.reaction_def("block").stamina_cost > 0
    (rolled,) = of(paused, AttackRolled)
    assert pending.trigger_event_seq == rolled.seq
    for accept in (True, False):
        _assert_round_trip(paused, U1, accept)


def test_reaction_skill_pending_has_the_skill_id_mana_cost_and_damage_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    prompt = [{"reaction": RIPOSTE, "when": {"event": "hit_by_melee"}, "mode": "prompt"}]
    owner = template("hero_fighter", reactions=prompt, max_mana=99, skills=[RIPOSTE])
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    base = make_state(
        m, [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=999))]
    )
    state = give_turn(base, U2)
    paused = resolve(state, Attack(unit_id=U2, target_id=U1))
    pending = paused.pending
    assert pending is not None
    assert pending.skill_id == RIPOSTE and pending.reaction == RIPOSTE
    assert pending.mana_cost == state.ruleset.skill_def(RIPOSTE).cost.mana
    damage = [e for e in paused.events if isinstance(e, DamageDealt) and e.target_id == U1]
    assert damage and pending.trigger_event_seq == damage[-1].seq
    accepted = _assert_round_trip(paused, U1, True)
    declined = _assert_round_trip(paused, U1, False)
    assert accepted.state.units[U1].reactions_used == 1
    assert declined.state.units[U1].reactions_used == 0


def _two_guards() -> BattleState:
    """敵人 U3 在 (2, 0) 離開，兩名守衛（U1 在 (1, 0)、U2 在 (2, 1)）都會被詢問藉機攻擊。"""
    guard = template("hero_fighter", reactions=PROMPT_OA)
    m = make_map("0000000\n0000000", ally=[(1, 0), (2, 1)], enemy=[(2, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (1, 0), guard),
            spawn(Team.ALLY, (2, 1), guard),
            spawn(Team.ENEMY, (2, 0), template("bandit", max_hp=300, reactions=[])),
        ],
    )
    return give_turn(state, U3)


@pytest.mark.parametrize("answers", [(True, True), (True, False), (False, True), (False, False)])
def test_two_consecutive_prompts_survive_serialization_between_each_step(
    answers: tuple[bool, bool],
) -> None:
    move = Move(unit_id=U3, path=(P(2, 0), P(3, 0), P(4, 0)))
    paused = resolve(_two_guards(), move)
    first = paused.pending
    assert first is not None and first.unit_id == U1
    # 第一次回答：往返版與直接版相同，且回傳第二個詢問
    second_result = _assert_round_trip(paused, U1, answers[0])
    second = second_result.pending
    assert second is not None and second.unit_id == U2
    assert second_result.state.pending is not None
    assert second_result.state.pending.unit_id == U2  # resume 後的新 Pending 也帶欄位
    assert (second.kind, second.skill_id, second.stamina_cost) == ("reaction", None, 0)
    # 第二次回答：從「讀回來的」暫停狀態繼續
    final = _assert_round_trip(second_result, U2, answers[1])
    assert final.pending is None and final.state.pending is None
    assert Pending.model_validate(second.model_dump()) == second
