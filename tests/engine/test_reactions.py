"""反應規則（藉機攻擊、格擋）與暫停點（prompt 反應、resume）（6.1-9、6.2-3）。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_setup,
    make_state,
    spawn,
    template,
    with_rolls,
)
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    EndTurn,
    Move,
    legal_actions,
    resolve,
    resume,
    state_to_json,
)
from trpg.engine.events import (
    EVENT_LIST_ADAPTER,
    AttackRolled,
    DamageDealt,
    EventBase,
    ReactionDeclined,
    ReactionTriggered,
)
from trpg.engine.runner import replay, run_battle
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")

PROMPT_OA = [
    {"reaction": "opportunity_attack", "when": {"event": "enemy_leaves_adjacent"}, "mode": "prompt"}
]


def P(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)


def _line(guard: object = "hero_fighter", mover: object = "bandit") -> BattleState:
    """守衛在 (1, 0)，移動者在 (2, 0)。"""
    m = make_map("000000\n000000", ally=[(1, 0)], enemy=[(2, 0)])
    return make_state(
        m,
        [spawn(Team.ALLY, (1, 0), guard), spawn(Team.ENEMY, (2, 0), mover)],  # type: ignore[arg-type]
    )


def _walk_away(state: BattleState) -> list[EventBase]:
    s = give_turn(state, "unit_0002")
    return resolve(s, Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0)))).events


def test_opportunity_attack_when_enemy_leaves() -> None:
    events = _walk_away(_line(mover=template("bandit", max_hp=300, reactions=[])))
    triggered = [e for e in events if isinstance(e, ReactionTriggered)]
    assert [(t.unit_id, t.reaction, t.trigger_unit_id) for t in triggered] == [
        (U1, "opportunity_attack", U2)
    ]
    rolls = [e for e in events if isinstance(e, AttackRolled)]
    assert len(rolls) == 1 and rolls[0].attacker_id == U1 and rolls[0].target_id == U2
    # 藉機攻擊在離開相鄰格「之前」結算
    first_move = next(i for i, e in enumerate(events) if e.type == "unit_moved")  # type: ignore[attr-defined]
    assert events.index(rolls[0]) < first_move


def test_no_opportunity_attack_when_staying_adjacent_or_ranged() -> None:
    state = give_turn(_line(mover=template("bandit", max_hp=300, reactions=[])), "unit_0002")
    # (2, 0) → (2, 1)：離開相鄰格 → 觸發；(2, 0) → (1, 1)：仍相鄰 → 不觸發
    events = resolve(state, Move(unit_id=U2, path=(P(2, 0), P(2, 1), P(1, 1)))).events
    assert sum(isinstance(e, ReactionTriggered) for e in events) == 1
    archer = _walk_away(
        _line(guard="hero_archer", mover=template("bandit", max_hp=300, reactions=[]))
    )
    assert not any(isinstance(e, ReactionTriggered) for e in archer)


def test_reaction_once_per_round() -> None:
    state = give_turn(_line(mover=template("bandit", max_hp=300, reactions=[])), "unit_0002")
    s = resolve(state, Move(unit_id=U2, path=(P(2, 0), P(2, 1)))).state  # 離開 → 藉機攻擊
    assert s.units[U1].reactions_used == 1
    s = resolve(s, Move(unit_id=U2, path=(P(2, 1), P(1, 1)))).state  # 回到相鄰
    events = resolve(s, Move(unit_id=U2, path=(P(1, 1), P(0, 1)))).events  # 再離開
    assert not any(isinstance(e, ReactionTriggered) for e in events)


def test_block_halves_melee_damage_and_costs_stamina() -> None:
    m = make_map("000", ally=[(0, 0)], enemy=[(1, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", max_hp=300)),
            spawn(Team.ENEMY, (1, 0), "bandit"),
        ],
    )
    s = give_turn(state, "unit_0002")
    s = with_rolls(s, [(20, 15), (4, 4)])
    result = resolve(s, Attack(unit_id=U2, target_id=U1))
    blocked = [e for e in result.events if isinstance(e, ReactionTriggered)]
    assert [(b.unit_id, b.reaction, b.stamina_spent) for b in blocked] == [(U1, "block", 10)]
    damage = next(e for e in result.events if isinstance(e, DamageDealt))
    # 匕首 1d4=4 + 敏捷 14 × 0.3 = 8.2；格擋 ×0.5 → 4.1 → 4（再套用戰士物理抗性 10%：3.69 → 3）
    assert damage.multiplier_permille == 500 and damage.amount == 3
    assert result.state.units[U1].stamina == 20


def test_block_unless_stamina_below_threshold() -> None:
    m = make_map("000", ally=[(0, 0)], enemy=[(1, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", max_hp=300, stamina=15)),
            spawn(Team.ENEMY, (1, 0)),
        ],
    )
    s = with_rolls(give_turn(state, "unit_0002"), [(20, 15), (4, 4)])
    events = resolve(s, Attack(unit_id=U2, target_id=U1)).events
    assert not any(isinstance(e, ReactionTriggered) for e in events)


def test_block_does_not_trigger_on_ranged_with_default_rule() -> None:
    m = make_map("00000", ally=[(0, 0)], enemy=[(4, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", max_hp=300)),
            spawn(Team.ENEMY, (4, 0), "bandit_archer"),
        ],
    )
    s = with_rolls(give_turn(state, "unit_0002"), [(20, 15), (8, 4)])
    events = resolve(s, Attack(unit_id=U2, target_id=U1)).events
    assert any(isinstance(e, DamageDealt) for e in events)
    assert not any(isinstance(e, ReactionTriggered) for e in events)


# ---------------------------------------------------------------------------
# prompt 反應：暫停與恢復
# ---------------------------------------------------------------------------


def _prompt_state() -> BattleState:
    guard = template("hero_fighter", reactions=PROMPT_OA)
    return give_turn(
        _line(guard=guard, mover=template("bandit", max_hp=300, reactions=[])), "unit_0002"
    )


def _events_json(events: list[EventBase]) -> bytes:
    return EVENT_LIST_ADAPTER.dump_json(events)  # type: ignore[arg-type]


@pytest.mark.parametrize("accept", [True, False])
def test_prompt_reaction_pauses_and_resumes(accept: bool) -> None:
    state = _prompt_state()
    move = Move(unit_id=U2, path=(P(2, 0), P(3, 0), P(4, 0)))
    before = state_to_json(state)
    paused = resolve(state, move)
    assert state_to_json(state) == before  # 純函式
    assert paused.pending is not None
    assert (paused.pending.unit_id, paused.pending.reaction, paused.pending.trigger_unit_id) == (
        U1,
        "opportunity_attack",
        U2,
    )
    ps = paused.state
    assert ps.pending is not None
    assert legal_actions(ps) == []
    with pytest.raises(IllegalActionError, match="結算暫停中"):
        resolve(ps, EndTurn(unit_id=U2))
    with pytest.raises(IllegalActionError, match="等待的是"):
        resume(ps, Decision(unit_id=U2, accept=True))
    paused_json = state_to_json(ps)
    resumed = resume(ps, Decision(unit_id=U1, accept=accept))
    assert state_to_json(ps) == paused_json  # resume 也是純函式
    assert resumed.pending is None and resumed.state.pending is None
    all_events = paused.events + resumed.events
    assert [e.seq for e in all_events] == list(
        range(all_events[0].seq, all_events[0].seq + len(all_events))
    )
    attacks = [e for e in all_events if isinstance(e, AttackRolled)]
    if accept:
        assert len(attacks) == 1 and any(isinstance(e, ReactionTriggered) for e in all_events)
    else:
        assert not attacks and any(isinstance(e, ReactionDeclined) for e in all_events)
    assert resumed.state.units[U2].pos == P(4, 0) or resumed.state.units[U2].downed


def test_resume_without_pending_is_rejected() -> None:
    with pytest.raises(IllegalActionError, match="沒有等待中的決定"):
        resume(_prompt_state(), Decision(unit_id=U1, accept=True))


def test_prompt_battle_replays_identically() -> None:
    """雙方都帶 prompt 反應的整場對戰：步驟列表含決定，重播得到相同的最終狀態與事件。"""
    m = make_map("000000\n000000\n000000", ally=[(0, 0), (0, 1)], enemy=[(5, 2), (5, 1)])
    prompt_rules = [
        *PROMPT_OA,
        {"reaction": "block", "when": {"event": "targeted_by_melee"}, "mode": "prompt"},
    ]
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter", reactions=prompt_rules)),
            spawn(Team.ALLY, (0, 1), template("hero_archer", reactions=prompt_rules)),
            spawn(Team.ENEMY, (5, 2), template("bandit", reactions=prompt_rules)),
            spawn(Team.ENEMY, (5, 1), template("bandit", reactions=prompt_rules)),
        ],
        max_rounds=15,
    )
    for seed in (1, 2, 3):
        flip = [False]

        def decide(state: BattleState, pending: object, flip: list[bool] = flip) -> Decision:
            flip[0] = not flip[0]
            return Decision(unit_id=pending.unit_id, accept=flip[0])  # type: ignore[attr-defined]

        run = run_battle(setup, seed, decide=decide)
        decisions = [s for s in run.actions if isinstance(s, Decision)]
        assert decisions, "應該至少暫停一次"
        again = replay(setup, seed, run.actions)
        assert state_to_json(again.state) == state_to_json(run.state)
        assert _events_json(again.events) == _events_json(run.events)
