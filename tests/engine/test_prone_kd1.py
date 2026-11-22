"""KD-1（#176，05 5.13）：倒地改版。

第 1 點：倒地期間不能用任何反應；倒地後第一個自己回合少 ``prone_ap_loss`` AP，只扣一次；單格頭目
不扣，巨型頭目照舊免疫，精英照一般單位。
"""

from __future__ import annotations

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    spawn,
    spawn_giant,
    template,
)
from trpg.engine import BattleState, Move, resolve
from trpg.engine.context import Ctx
from trpg.engine.effects import ApplyStatusEffect, RemoveStatusEffect, run_effects
from trpg.engine.events import EffectFizzled, ReactionTriggered
from trpg.engine.turns import start_turn
from trpg.engine.view import project_for
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
