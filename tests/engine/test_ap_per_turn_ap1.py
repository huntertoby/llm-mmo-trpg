"""每回合 AP 依單位（AP-1，#168，05 5.2「⚠ AP 改版」）：玩家方 4、一般敵人 3、精英與頭目 4、
召喚物照現行；範本可以寫 ``ap_per_turn``；保留上限＝每回合 AP＋1；數值來自核心規則（工坊可調）。
實際跑引擎的表格測試。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library, make_map, make_state, spawn, template
from trpg.content.battle import UnitTemplate
from trpg.engine import BattleState, EndTurn, resolve
from trpg.engine.rewrites import ap_cap
from trpg.shared.types import Team, UnitId

FLAT = "\n".join(["00000"] * 3)


def _state(tmpl: UnitTemplate | str, team: Team, **core: Any) -> tuple[BattleState, UnitId]:
    """``tmpl`` 放在 (0, 0)、另一方一個木頭人在 (4, 2)；回傳狀態與那個單位的 ID。"""
    other = Team.ENEMY if team is Team.ALLY else Team.ALLY
    foe = template("hero_fighter" if other is Team.ALLY else "bandit", max_hp=999, reactions=[])
    m = make_map(FLAT)
    state = make_state(m, [spawn(team, (0, 0), tmpl), spawn(other, (4, 2), foe)], **core)
    return state, UnitId("unit_0001")


@pytest.mark.parametrize(
    ("tmpl", "team", "expected"),
    [
        ("hero_fighter", Team.ALLY, 4),  # 玩家方
        ("bandit", Team.ALLY, 4),  # 敵人範本當隊友：照玩家方
        ("bandit_captain", Team.ALLY, 4),
        ("bandit", Team.ENEMY, 3),  # 一般敵人
        ("bandit_captain", Team.ENEMY, 4),  # 精英
        ("bandit_boss", Team.ENEMY, 4),  # 頭目（也是精英）
        ("hero_fighter", Team.ENEMY, 3),  # 沒有標籤的範本當敵人：一般
    ],
)
def test_turn_ap_by_side_and_rank(tmpl: str, team: Team, expected: int) -> None:
    state, uid = _state(tmpl, team)
    unit = state.units[uid]
    assert unit.ap_per_turn == expected
    assert ap_cap(state.ruleset.core, unit) == expected + state.ruleset.core.ap_carry_max


def test_a_template_value_overrides_the_rank_default_for_enemies_only() -> None:
    tmpl = template("bandit_captain", ap_per_turn=2)
    enemy, uid = _state(tmpl, Team.ENEMY)
    assert enemy.units[uid].ap_per_turn == 2
    ally, uid = _state(tmpl, Team.ALLY)
    assert ally.units[uid].ap_per_turn == 4  # 玩家方一律照玩家方


def test_a_world_elite_tag_counts_as_elite() -> None:
    """大世界的精英詞條把 ``elite`` 加進範本標籤：照精英。"""
    tmpl = template("bandit", tags=("humanoid", "elite"))
    state, uid = _state(tmpl, Team.ENEMY)
    assert state.units[uid].ap_per_turn == 4


def test_summons_keep_the_old_turn_ap() -> None:
    core = library().ruleset.core
    summon = template("bandit_captain").model_copy(update={"summon": True})
    assert core.template_ap_per_turn(summon, party=True) == core.ap_per_turn == 3
    assert core.template_ap_per_turn(summon, party=False) == 3


def _turn_ap_after_keeping_one(tmpl: str, team: Team, **core: Any) -> tuple[int, int]:
    """開場的 AP、用掉到剩 1 點保留後下一個自己回合開始時的 AP。"""
    state, uid = _state(tmpl, team, **core)
    while state.active_unit != uid:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    first = state.units[uid].ap
    state.units[uid].ap = 1  # 只留 1 點
    state = resolve(state, EndTurn(unit_id=uid)).state
    while state.active_unit != uid:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    return first, state.units[uid].ap


@pytest.mark.parametrize(
    ("tmpl", "team", "expected"),
    [
        ("hero_fighter", Team.ALLY, (4, 5)),
        ("bandit", Team.ENEMY, (3, 4)),
        ("bandit_captain", Team.ENEMY, (4, 5)),
    ],
)
def test_turn_start_gives_turn_ap_plus_the_kept_point(
    tmpl: str, team: Team, expected: tuple[int, int]
) -> None:
    assert _turn_ap_after_keeping_one(tmpl, team) == expected


def test_the_workshop_values_can_turn_everything_back_to_three() -> None:
    """工坊把玩家方與精英改回 3：全部單位每回合 3、上限 4（改版前的行為）。"""
    old = {"party_ap_per_turn": 3, "elite_ap_per_turn": 3}
    for tmpl, team in [("hero_fighter", Team.ALLY), ("bandit_boss", Team.ENEMY)]:
        assert _turn_ap_after_keeping_one(tmpl, team, **old) == (3, 4)


def test_initial_values() -> None:
    core = library().ruleset.core
    assert (core.party_ap_per_turn, core.ap_per_turn, core.elite_ap_per_turn) == (4, 3, 4)
    assert core.ap_carry_max == 1
