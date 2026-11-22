"""KD-1（#176，05 5.13）：倒地改版。

第 1 點：倒地期間不能用任何反應；倒地後第一個自己回合少 ``prone_ap_loss`` AP，只扣一次；單格頭目
不扣，巨型頭目照舊免疫，精英照一般單位。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    spawn,
    spawn_giant,
    template,
)
from trpg.engine import BattleState, HelpUp, Move, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.basics import help_up_problem
from trpg.engine.context import Ctx
from trpg.engine.effects import ApplyStatusEffect, RemoveStatusEffect, run_effects
from trpg.engine.events import EffectFizzled, ReactionTriggered, UnitMoved, UnitStoodUp
from trpg.engine.turns import start_turn
from trpg.engine.view import project_for
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
CORE = library().ruleset.core


def _pair(enemy_tags: tuple[str, ...] = ()) -> BattleState:
    m = make_map("0000\n0000", enemy=[(1, 0)])
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter")),
            spawn(Team.ENEMY, (1, 0), template("bandit", tags=enemy_tags)),
        ],
    )


def _knock(state: BattleState, uid: UnitId = U2) -> BattleState:
    return run_effects(state, [ApplyStatusEffect(target_id=uid, status_id="prone")]).state


def _turn(state: BattleState, uid: UnitId) -> BattleState:
    ctx = Ctx(state.clone())
    start_turn(ctx, uid)
    return ctx.state


def test_prone_costs_ap_once_on_the_next_own_turn() -> None:
    state = _knock(_pair())
    foe = state.units[U2]
    assert foe.prone_ap_due
    first = _turn(state, U2)
    assert first.units[U2].ap == foe.ap_per_turn - CORE.prone_ap_loss
    assert first.units[U2].ap_lost == CORE.prone_ap_loss
    assert not first.units[U2].prone_ap_due
    assert first.units[U2].has_status("prone")  # 沒站起來，倒地照舊
    second = _turn(first, U2)
    assert second.units[U2].ap == foe.ap_per_turn  # 只扣這一次


def test_reapplying_prone_while_down_does_not_charge_again() -> None:
    state = _turn(_knock(_pair()), U2)
    again = _knock(state)
    assert not again.units[U2].prone_ap_due


def test_stood_up_before_the_turn_still_pays() -> None:
    state = _knock(_pair())
    stood = run_effects(
        state, [RemoveStatusEffect(target_id=U2, status_id="prone", reason="stood_up")]
    ).state
    assert not stood.units[U2].has_status("prone")
    assert stood.units[U2].prone_ap_due
    turn = _turn(stood, U2)
    assert turn.units[U2].ap == stood.units[U2].ap_per_turn - CORE.prone_ap_loss


def test_single_tile_boss_falls_but_keeps_ap() -> None:
    state = _knock(_pair(("boss",)))
    assert state.units[U2].has_status("prone")
    assert not state.units[U2].prone_ap_due
    assert _turn(state, U2).units[U2].ap == state.units[U2].ap_per_turn


def test_elite_pays_like_a_normal_unit() -> None:
    state = _knock(_pair(("elite",)))
    assert state.units[U2].prone_ap_due


def test_giant_is_still_immune() -> None:
    m = make_map("\n".join("0" * 6 for _ in range(6)), enemy=[(3, 3)])
    state = make_state(
        m, [spawn(Team.ALLY, (0, 0), template("hero_fighter")), spawn_giant(Team.ENEMY, (3, 3))]
    )
    result = run_effects(state, [ApplyStatusEffect(target_id=U2, status_id="prone")])
    assert not result.state.units[U2].has_status("prone")
    assert any(isinstance(e, EffectFizzled) for e in result.events)
    assert not result.state.units[U2].prone_ap_due


def test_prone_units_make_no_opportunity_attack() -> None:
    """站在倒地敵人旁邊走開：沒有藉機攻擊（站著時有）。"""
    base = give_turn(_pair(), U1)
    walk = Move(unit_id=U1, path=(Pos(x=0, y=0), Pos(x=0, y=1)))
    standing = resolve(base, walk)
    assert any(isinstance(e, ReactionTriggered) and e.unit_id == U2 for e in standing.events)
    lying = resolve(give_turn(_knock(base), U1), walk)
    assert not any(isinstance(e, ReactionTriggered) for e in lying.events)


def test_view_marks_reactions_unavailable_while_prone() -> None:
    state = _knock(_pair())
    view = project_for(state, Team.ENEMY)
    unit = next(u for u in view.units if u.id == U2)
    assert not unit.reaction_available


# ---------------------------------------------------------------------------
# 第 2 點：扶起
# ---------------------------------------------------------------------------


def _trio(heights: str = "0000\n0000", ally2: tuple[int, int] = (1, 0)) -> BattleState:
    """U1 英雄在 (0, 0)、U2 隊友、U3 敵人在 (3, 1)。"""
    m = make_map(heights, ally=[(0, 0), ally2], enemy=[(3, 1)])
    return make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), template("hero_fighter")),
            spawn(Team.ALLY, ally2, template("hero_fighter")),
            spawn(Team.ENEMY, (3, 1), template("bandit")),
        ],
    )


def _help(uid: UnitId = U1, target: UnitId = U2) -> HelpUp:
    return HelpUp(unit_id=uid, target_id=target)


def test_help_up_stands_the_ally_for_ap_without_his_move() -> None:
    state = give_turn(_knock(_trio()), U1)
    assert _help() in legal_actions(state)
    before = state.units[U2].move_points
    result = resolve(state, _help())
    after = result.state.units[U2]
    assert not after.has_status("prone")
    assert after.move_points == before
    assert result.state.units[U1].ap == state.units[U1].ap - CORE.help_up_ap_cost
    stood = [e for e in result.events if isinstance(e, UnitStoodUp)]
    assert [(e.unit_id, e.cost, e.helper_id) for e in stood] == [(U2, 0, U1)]
    assert not any(isinstance(e, ReactionTriggered | UnitMoved) for e in result.events)
    assert after.prone_ap_due  # 被扶起也照扣 AP


def test_help_up_needs_a_prone_adjacent_ally() -> None:
    standing = give_turn(_trio(), U1)
    assert not any(isinstance(a, HelpUp) for a in legal_actions(standing))
    far = give_turn(_knock(_trio(ally2=(2, 0))), U1)
    assert not any(isinstance(a, HelpUp) for a in legal_actions(far))
    assert help_up_problem(far, far.units[U1], U2) is not None
    foe = give_turn(_knock(_trio(), U3), U1)
    assert help_up_problem(foe, foe.units[U1], U3) is not None
    with pytest.raises(IllegalActionError):
        resolve(standing, _help())


def test_help_up_respects_the_melee_height_limit() -> None:
    limit = CORE.melee_height_limit
    state = give_turn(_knock(_trio(heights=f"0{limit + 1}00\n0000")), U1)
    assert "高度差" in (help_up_problem(state, state.units[U1], U2) or "")


@pytest.mark.parametrize("status", ["prone", "root"])
def test_a_prone_or_rooted_helper_cannot_help(status: str) -> None:
    state = _knock(_trio())
    state = run_effects(state, [ApplyStatusEffect(target_id=U1, status_id=status)]).state
    state = give_turn(state, U1)
    assert help_up_problem(state, state.units[U1], U2) is not None
    assert not any(isinstance(a, HelpUp) for a in legal_actions(state))


def test_enemies_help_each_other_too() -> None:
    m = make_map("0000\n0000", enemy=[(2, 0), (3, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 1), template("hero_fighter")),
            spawn(Team.ENEMY, (2, 0), template("bandit")),
            spawn(Team.ENEMY, (3, 0), template("bandit")),
        ],
    )
    state = give_turn(_knock(state, U3), U2)
    assert _help(U2, U3) in legal_actions(state)
    assert not resolve(state, _help(U2, U3)).state.units[U3].has_status("prone")


def test_ai_scores_help_up_from_the_prone_value() -> None:
    """效用 AI 不寫死規則：扶起的分數來自 ``support`` × 倒地的 ``status_values``（正分才會選）。"""
    state = give_turn(_knock(_trio()), U1)
    scored = [
        s for s in UtilityAI(library().ai_profiles).rank(state) if isinstance(s.action, HelpUp)
    ]
    assert scored and scored[0].score > 0
