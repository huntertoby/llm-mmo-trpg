"""AP 列要的資料（AP-1 第 6 項，#168）：戰鬥狀態輸出每回合 AP、上限、這回合帶進來的保留、
這回合被扣的、下回合會少的。實際跑引擎（結束回合、透支技能）再看 ``project_for`` 的視圖。"""

from __future__ import annotations

from tests.engine.helpers import (
    caster_template,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.engine import BattleState, EndTurn, UseSkill, project_for, resolve, state_to_json
from trpg.engine.state import UnitState
from trpg.engine.view import UnitView
from trpg.shared.types import Team, UnitId

HERO, FOE = UnitId("unit_0001"), UnitId("unit_0002")
STRIKE = "skill_overdraft_strike"  # 透支 1（下回合 −1）
FLAT = "\n".join(["0000000"] * 3)


def _state() -> BattleState:
    m = make_map(FLAT)
    hero = caster_template([STRIKE], base="hero_fighter", stamina=99)
    spawns = [
        spawn(Team.ALLY, (0, 0), hero),
        spawn(Team.ENEMY, (1, 0), no_reactions("bandit", max_hp=999)),
    ]
    return make_state(m, spawns)


def _until(state: BattleState, uid: UnitId) -> BattleState:
    while state.active_unit != uid:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    return state


def _end(state: BattleState) -> BattleState:
    assert state.active_unit is not None
    return resolve(state, EndTurn(unit_id=state.active_unit)).state


def _view(state: BattleState, uid: UnitId = HERO) -> UnitView:
    return {u.id: u for u in project_for(state, Team.ALLY).units}[uid]


def test_turn_ap_and_cap_are_in_the_view() -> None:
    state = _until(_state(), HERO)
    hero, foe = _view(state), _view(state, FOE)
    assert (hero.ap_per_turn, hero.ap_max, hero.ap) == (4, 5, 4)
    assert (foe.ap_per_turn, foe.ap_max) == (3, 4)
    assert (hero.ap_carried_in, hero.ap_lost, hero.ap_next_loss) == (0, 0, 0)


def test_the_kept_point_shows_on_the_next_turn_only() -> None:
    state = _until(_state(), HERO)
    state.units[HERO].ap = 1
    ended = _end(state)
    off = _view(ended)
    assert (off.ap_carry, off.ap_carried_in) == (1, 0)  # 還沒輪到：寫在 ap_carry
    again = _until(ended, HERO)
    view = _view(again)
    assert (view.ap, view.ap_carried_in, view.ap_carry) == (5, 1, 0)
    assert _view(_end(again)).ap_carried_in == 0  # 回合結束就清掉


def _overdraw(state: BattleState) -> BattleState:
    return resolve(state, UseSkill(unit_id=HERO, skill_id=STRIKE, target_id=FOE)).state


def test_overdraft_shows_next_turn_then_this_turn() -> None:
    state = _until(_state(), HERO)
    state.units[HERO].ap = 2  # 用光，不保留（只看透支）
    cast = _overdraw(state)
    assert _view(cast).ap_next_loss == 1  # 施放的回合：下回合會少 1
    off = _end(cast)
    assert _view(off).ap_next_loss == 1  # 回合外仍是下回合會少 1
    turn = _until(off, HERO)
    view = _view(turn)
    assert (view.ap, view.ap_lost, view.ap_next_loss) == (3, 1, 0)  # 這回合已扣，下回合不再少
    assert _view(_end(turn)).ap_lost == 0


def test_the_new_fields_only_show_in_json_when_set() -> None:
    state = _until(_state(), HERO)
    text = state_to_json(state)
    assert '"ap_carried_in"' not in text and '"ap_lost"' not in text
    unit: UnitState = state.units[HERO]
    assert unit.clone().ap_carried_in == unit.ap_carried_in
    assert library().ruleset.core.ap_carry_max == 1
