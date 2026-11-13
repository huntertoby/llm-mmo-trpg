"""KW-2（#161，06 6.32.1）：示範招的引擎行為與新條件「自己站在高處」。

每列一條規則句、實際跑引擎（內建技能，不是測試專用技能）：

- 鷹眼（被動 ``on_turn_end``）：回合結束時自己站在高度至少 1 層的格子上，專注 +1 並得到小護盾；
  站在平地上什麼都不發生。條件 ``self_on_high_ground`` 只看施放者所在格（占位定義：高度 ≥ 1）。
- 斷喉：先花光連擊點換傷害；「滿 5 層讓目標流血」照施放開始時的層數判斷——5 層流血、4 層不流血。
- 咬牙撐住：花光怒氣，每層提高護盾（``fury.consumer.boosts`` 加 ``shield``）。
- 貫心箭：「滿 3 層標記目標」——3 層標記、2 層不標記；專注照樣被花光。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_dual_dagger_skills_dd1 import HIT, d20s
from trpg.content.skills import ConditionSpec
from trpg.engine import BattleState, resolve
from trpg.engine.actions import EndTurn, UseSkill
from trpg.engine.events import ShieldGained, StacksChanged, StatusApplied
from trpg.engine.skills.conditions import skill_condition_met
from trpg.shared.types import Team

HIGH = ConditionSpec.model_validate({"type": "self_on_high_ground"})


def scene(
    skills: list[str],
    *,
    height: int = 0,
    stacks: dict[str, int] | None = None,
    weapon: str | None = None,
    base: str = "hero_fighter",
) -> BattleState:
    """U1 在 (3, 3)（那一格高 ``height`` 層）帶 ``skills``；敵人（沒有反應）在 (4, 3)。"""
    rows = [list(r) for r in FLAT7.split("\n")]
    rows[3][3] = str(height)
    m = make_map("\n".join("".join(r) for r in rows), ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template(skills, base=base)),
        spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=300, resist={})),
    ]
    state = give_turn(make_state(m, spawns), U1)
    for stack, count in (stacks or {}).items():
        state.units[U1].stacks[stack] = count
    if weapon is not None:
        state.units[U1].weapon = library().weapons[weapon]
    return state


def stack_of(state: BattleState, stack: str) -> int:
    return state.units[U1].stacks.get(stack, 0)


# ---------------------------------------------------------------------------
# 自己站在高處（鷹眼）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("height", "met"), [(0, False), (1, True), (2, True)])
def test_self_on_high_ground_reads_the_casters_own_tile(height: int, met: bool) -> None:
    state = scene(["skill_eagle_eye"], height=height)
    eagle = library().skills["skill_eagle_eye"]
    assert eagle.condition == HIGH
    assert skill_condition_met(state, state.units[U1], eagle, ()) is met


@pytest.mark.parametrize(("height", "gained"), [(0, 0), (1, 1)])
def test_eagle_eye_adds_focus_at_turn_end_only_on_high_ground(height: int, gained: int) -> None:
    state = scene(["skill_eagle_eye"], height=height)
    result = resolve(state, EndTurn(unit_id=U1))
    assert stack_of(result.state, "focus") == gained
    shields = [e for e in of(result, ShieldGained) if e.unit_id == U1]
    assert bool(shields) is bool(gained)


# ---------------------------------------------------------------------------
# 「滿 N 層」的示範終結技
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("have", "bleeds"), [(4, False), (5, True)])
def test_throat_cut_bleeds_only_from_five_combo_points(
    have: int, bleeds: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = scene(["skill_throat_cut"], stacks={"combo_point": have}, weapon="dagger")
    d20s(monkeypatch, [HIT])
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_throat_cut", target_id=U2))
    spent = [e for e in of(result, StacksChanged) if e.reason == "consumed"]
    assert [(e.before, e.after) for e in spent] == [(have, 0)]
    bled = [e for e in of(result, StatusApplied) if e.status_id == "bleed" and e.target_id == U2]
    assert bool(bled) is bleeds


@pytest.mark.parametrize(("have", "marked"), [(2, False), (3, True)])
def test_heart_piercer_marks_only_from_three_focus(
    have: int, marked: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = scene(["skill_heart_piercer"], stacks={"focus": have}, base="hero_archer")
    d20s(monkeypatch, [HIT])
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_heart_piercer", target_id=U2))
    assert stack_of(result.state, "focus") == 0
    hits = [e for e in of(result, StatusApplied) if e.status_id == "marked" and e.target_id == U2]
    assert bool(hits) is marked


def test_grit_teeth_spends_fury_for_a_bigger_shield(monkeypatch: pytest.MonkeyPatch) -> None:
    """咬牙撐住：同樣的骰子，4 層怒氣的護盾比 0 層大，怒氣花光。"""
    d20s(monkeypatch, [])
    amounts = []
    for fury in (0, 4):
        state = scene(["skill_grit_teeth"], stacks={"fury": fury})
        result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_grit_teeth"))
        [shield] = [e for e in of(result, ShieldGained) if e.unit_id == U1]
        amounts.append(shield.amount)
        assert stack_of(result.state, "fury") == 0
    assert amounts[1] > amounts[0]
