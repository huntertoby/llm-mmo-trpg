"""跑步（Phase 3-20，玩法 #22）：+3 格、每回合 1 次、定身不能跑、AI 只在追擊與撤離時跑。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
    template,
)
from trpg.api.presenter import run_option_out
from trpg.engine import (
    Action,
    BattleState,
    EndTurn,
    Move,
    Run,
    legal_actions,
    resolve,
    state_to_json,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import run_problem
from trpg.engine.effects import ApplyStatusEffect, run_effects
from trpg.engine.events import UnitRan
from trpg.engine.preview import preview
from trpg.engine.rules.statuses import move_points_for_turn
from trpg.engine.runner import replay, run_battle
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")


def _duel(
    width: int = 14, *, foe_x: int | None = None, hero_x: int = 0, hero: str = "hero_fighter"
) -> BattleState:
    m = make_map("0" * width, ally=[(hero_x, 0)], enemy=[(width - 1, 0)])
    foe = spawn(Team.ENEMY, (foe_x if foe_x is not None else width - 1, 0), no_reactions())
    state = make_state(m, [spawn(Team.ALLY, (hero_x, 0), hero), foe])
    return give_turn(state, U1)


def _with_status(state: BattleState, status: str) -> BattleState:
    out = run_effects(state, [ApplyStatusEffect(target_id=U1, status_id=status, duration=3)]).state
    unit = out.units[U1]
    unit.move_points = move_points_for_turn(out.ruleset, unit)
    return out


def test_run_adds_three_move_points_and_costs_one_ap() -> None:
    state = _duel()
    result = resolve(state, Run(unit_id=U1))
    unit = result.state.units[U1]
    assert unit.move_points == state.units[U1].move_points + 3
    assert unit.ap == state.units[U1].ap - 1
    assert unit.pos == state.units[U1].pos  # 跑步本身不移動
    assert unit.ran_this_turn and unit.moved_this_turn  # 算移動類動作
    (event,) = [e for e in result.events if isinstance(e, UnitRan)]
    assert (event.unit_id, event.bonus, event.move_points) == (U1, 3, unit.move_points)
    assert state.units[U1].move_points == 5  # 純函式：原狀態不變


def test_run_value_comes_from_core_rules_not_hardcoded() -> None:
    m = make_map("0" * 14, ally=[(0, 0)], enemy=[(13, 0)])
    state = give_turn(
        make_state(
            m,
            [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (13, 0))],
            run_move_bonus=5,
            run_ap_cost=2,
        ),
        U1,
    )
    unit = resolve(state, Run(unit_id=U1)).state.units[U1]
    assert unit.move_points == 10 and unit.ap == 1


def test_run_extends_move_range() -> None:
    state = _duel()
    far = Pos(x=8, y=0)
    path = tuple(Pos(x=x, y=0) for x in range(9))
    assert far not in {a.dest for a in legal_actions(state) if isinstance(a, Move)}
    after = resolve(state, Run(unit_id=U1)).state
    assert far in {a.dest for a in legal_actions(after) if isinstance(a, Move)}
    moved = resolve(after, Move(unit_id=U1, path=path)).state
    assert moved.units[U1].pos == far and moved.units[U1].move_points == 0


def test_run_only_once_per_turn() -> None:
    state = _duel()
    after = resolve(state, Run(unit_id=U1)).state
    assert not any(isinstance(a, Run) for a in legal_actions(after))
    with pytest.raises(IllegalActionError, match="已經跑過了"):
        resolve(after, Run(unit_id=U1))
    assert run_problem(after, after.units[U1]) == "已經跑過了"
    option = run_option_out(after, U1)
    assert not option.legal and option.reason == "已經跑過了"


def test_rooted_unit_cannot_run() -> None:
    state = _with_status(_duel(), "root")
    assert not any(isinstance(a, Run) for a in legal_actions(state))
    with pytest.raises(IllegalActionError, match="被定身，不能跑"):
        resolve(state, Run(unit_id=U1))
    assert run_option_out(state, U1).reason == "被定身，不能跑"


def test_run_needs_ap() -> None:
    state = _duel()
    state.units[U1].ap = 0
    assert not any(isinstance(a, Run) for a in legal_actions(state))
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(state, Run(unit_id=U1))
    assert (run_option_out(state, U1).reason or "").startswith("AP 不足")


@pytest.mark.parametrize(("status", "base"), [("hasted", 7), ("slow", 2)])
def test_run_bonus_ignores_haste_and_slow_multiplier(status: str, base: int) -> None:
    state = _with_status(_duel(), status)
    assert state.units[U1].move_points == base  # 速度 5 × 1.5／× 0.5（無條件捨去）
    ran = resolve(state, Run(unit_id=U1)).state
    assert ran.units[U1].move_points == base + 3  # 固定 +3 格，不乘倍率


def test_run_expires_at_turn_end() -> None:
    state = resolve(_duel(), Run(unit_id=U1)).state
    assert state.units[U1].ran_this_turn
    state = resolve(state, EndTurn(unit_id=U1)).state
    for _ in range(4):  # 敵人回合結束後輪到自己
        if state.active_unit == U1:
            break
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    assert state.active_unit == U1
    unit = state.units[U1]
    assert not unit.ran_this_turn and unit.move_points == unit.speed
    assert any(isinstance(a, Run) for a in legal_actions(state))


def test_same_seed_replays_identically() -> None:
    state = _duel()
    script: list[Action] = [
        Run(unit_id=U1),
        Move(unit_id=U1, path=tuple(Pos(x=x, y=0) for x in range(9))),
    ]
    outcomes = []
    for _ in range(2):
        s = state
        for step in script:
            s = resolve(s, step).state
        outcomes.append(state_to_json(s))
    assert outcomes[0] == outcomes[1]


def test_preview_shows_move_range_after_run() -> None:
    state = _duel()
    before = {(a.dest.x, a.dest.y) for a in legal_actions(state) if isinstance(a, Move)}
    p = preview(state, Run(unit_id=U1))
    assert p.ap_cost == 1
    assert set(p.run_range) > before
    assert (8, 0) in p.run_range and (9, 0) not in p.run_range
    assert list(p.run_range) == sorted(p.run_range, key=lambda t: (t[1], t[0]))
    assert state.units[U1].move_points == 5  # 預覽不改變狀態


# ---- AI ----------------------------------------------------------------------


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def test_ai_runs_when_target_is_outside_move_range_but_within_run_range() -> None:
    # 戰士（攻擊距離 1）在 x=0，敵人在 x=4，移動點數已用完：走不到；跑步 +3 後可走到 x=3 打得到
    state = _duel(foe_x=4)
    state.units[U1].move_points = 0
    assert _ai()(state) == Run(unit_id=U1)


def test_ai_does_not_run_when_already_in_reach_or_far_away() -> None:
    near = _duel(foe_x=4)  # 移動點數夠走到攻擊距離：直接走過去
    assert not isinstance(_ai()(near), Run)
    far = _duel(width=30)  # 跑了也夠不到
    far.units[U1].move_points = 0
    assert not isinstance(_ai()(far), Run)
    mid = _duel(foe_x=9)  # 滿移動點數走 5 格夠不到、跑步後夠得到：先走（走位分數較高），不是先跑
    assert isinstance(_ai()(mid), Move)
    far.units[U1].move_points = 0
    assert not isinstance(_ai()(far), Run)
    adjacent = _duel(foe_x=1)
    assert not isinstance(_ai()(adjacent), Run)


def test_ai_runs_to_retreat_when_low_on_hp() -> None:
    state = _duel(width=14, foe_x=8, hero_x=5)
    state.units[U1].hp = 5
    state.units[U1].move_points = 0
    assert _ai()(state) == Run(unit_id=U1)


def test_ai_does_not_retreat_with_healthy_hp_or_distant_enemy() -> None:
    healthy = _duel(foe_x=6, hero_x=5)  # 血量正常、敵人已在攻擊距離內：不跑
    healthy.units[U1].move_points = 0
    assert not isinstance(_ai()(healthy), Run)
    distant = _duel(width=30)
    distant.units[U1].hp = 5
    assert not isinstance(_ai()(distant), Run)


def test_enemy_can_run_too() -> None:
    m = make_map("0" * 14, ally=[(0, 0)], enemy=[(13, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter")),
            spawn(Team.ENEMY, (4, 0), no_reactions()),
        ],
    )
    state = give_turn(state, U2)
    state.units[U2].move_points = 0
    assert _ai()(state) == Run(unit_id=U2)


def test_ai_run_battle_logs_run_and_replays() -> None:
    m = make_map("0" * 10, ally=[(0, 0)], enemy=[(9, 0)])
    setup = make_setup(
        m, [spawn(Team.ALLY, (0, 0), "hero_fighter"), spawn(Team.ENEMY, (9, 0), no_reactions())]
    )
    result = run_battle(setup, 7, policy=_ai())
    assert any(isinstance(e, UnitRan) for e in result.events)
    assert any(isinstance(a, Run) for a in result.actions)
    assert replay(setup, 7, result.actions).events == result.events
