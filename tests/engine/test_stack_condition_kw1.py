"""KW-1（#161，06 6.32.1）：條件「自身層數達 N」與雙匕首每次出招只 +1 連擊點。

每列一條規則句、實際跑引擎：

- 技能層級：層數不足時不在 ``legal_actions``、施放被擋、原因是中文；足夠時能放而且不消耗層數。
- 效果層級：以施放開始時的層數判斷——終結技先花光層數，「滿 N 層」的效果照樣成立；N−1 層不成立。
- 雙匕首施放單體武器技：兩下都中 +1、第一下沒中第二下中 +1、兩下都沒中 0；單手武器 +1；範圍武器技
  打中兩個目標仍各 +1（每個目標一次）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, U3, of
from tests.engine.test_dual_dagger_skills_dd1 import HIT, MISS, d20s
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine import BattleState, legal_actions, resolve
from trpg.engine.actions import UseSkill
from trpg.engine.events import DamageDealt, ShieldGained, StacksChanged
from trpg.engine.skills.targeting import skill_problem
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Team

FINISHER = "skill_combo_finisher"
"""身上帶連擊點的消耗技，武器技命中才會自動累積連擊點。"""


def combo_at_least(count: int, stack: str = "combo_point") -> dict[str, Any]:
    return {"type": "self_stack_at_least", "stack": stack, "count": count}


def weapon_skill(
    effects: Sequence[Mapping[str, Any]],
    *,
    shape: Mapping[str, Any] | None = None,
    condition: Mapping[str, Any] | None = None,
) -> SkillDef:
    skill = make_skill(SID, shape or {"type": "single", "range": 1}, effects, category="weapon")
    if condition is None:
        return skill
    return skill.model_copy(update={"condition": ConditionSpec.model_validate(condition)})


def scene(
    skill: SkillDef,
    *,
    combo: int = 0,
    foes: Sequence[tuple[int, int]] = ((4, 3),),
    weapon: str | None = None,
) -> BattleState:
    """U1 在 (3, 3) 帶 ``skill`` 與連擊終結、身上 ``combo`` 層連擊點；敵人（沒有反應）在
    ``foes``。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill, FINISHER], base="hero_fighter"))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=300, resist={})) for xy in foes]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    if combo:
        state.units[U1].stacks["combo_point"] = combo
    if weapon is not None:
        state.units[U1].weapon = library().weapons[weapon]
    return state


def use(state: BattleState, **fields: Any):  # type: ignore[no-untyped-def]
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2, **fields))


def combo_of(state: BattleState) -> int:
    return state.units[U1].stacks.get("combo_point", 0)


# ---------------------------------------------------------------------------
# 1. 技能層級：層數不足不能放，足夠時能放而且不消耗
# ---------------------------------------------------------------------------

STRIKE: list[dict[str, Any]] = [{"type": "damage", "multiplier_permille": 1000}]


@pytest.mark.parametrize(("have", "ok"), [(0, False), (2, False), (3, True), (5, True)])
def test_a_skill_level_stack_condition_gates_the_skill(
    have: int, ok: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill = weapon_skill(STRIKE, condition=combo_at_least(3))
    state = scene(skill, combo=have)
    listed = any(isinstance(a, UseSkill) and a.skill_id == SID for a in legal_actions(state))
    problem = skill_problem(state, state.units[U1], skill)
    assert listed is ok
    assert problem is None  # 層數條件不是代價（cost.stacks），由技能條件擋
    if not ok:
        with pytest.raises(IllegalActionError, match="自身「連擊點」達 3 層"):
            use(state)
        return
    d20s(monkeypatch, [MISS])  # 沒打中：不消耗、也不自動累積
    assert combo_of(use(state).state) == have


# ---------------------------------------------------------------------------
# 2. 效果層級：看施放開始時的層數（終結技先花光也照樣成立）
# ---------------------------------------------------------------------------

FINISH: list[dict[str, Any]] = [
    {"type": "damage", "multiplier_permille": 1000},
    {"type": "consume_stack", "stack": "combo_point", "per_stack_permille": 200, "affects": "self"},
    {"type": "shield", "dice": "1d4", "affects": "self", "condition": combo_at_least(3)},
]


@pytest.mark.parametrize(("have", "shielded"), [(2, False), (3, True), (5, True)])
def test_an_effect_stack_condition_reads_the_stacks_before_the_finisher_spends_them(
    have: int, shielded: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = scene(weapon_skill(FINISH), combo=have)
    d20s(monkeypatch, [HIT])
    result = use(state)
    spent = [e for e in of(result, StacksChanged) if e.reason == "consumed"]
    assert [(e.before, e.after) for e in spent] == [(have, 0)]
    assert bool(of(result, ShieldGained)) is shielded
    # 命中那一層在整招結算完才加（終結技之後剩 1 層），不影響這次的判斷
    assert combo_of(result.state) == 1


def test_an_effect_stack_condition_ignores_stacks_the_same_cast_adds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """同一招先 +2 再判斷「達 3 層」：看的是施放開始時的 1 層，不成立。"""
    effects: list[dict[str, Any]] = [
        {"type": "damage", "multiplier_permille": 1000},
        {"type": "add_stack", "stack": "combo_point", "amount": 2, "affects": "self"},
        {"type": "shield", "dice": "1d4", "affects": "self", "condition": combo_at_least(3)},
    ]
    state = scene(weapon_skill(effects), combo=1)
    d20s(monkeypatch, [HIT])
    result = use(state)
    assert not of(result, ShieldGained)
    assert combo_of(result.state) == 4  # 1 ＋ 技能 2 ＋ 命中自動 1


def test_an_any_of_branch_reads_the_snapshot_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """「或」的分支裡也看快照：先花光層數，`any_of` 的層數分支仍成立。"""
    cond: dict[str, Any] = {"type": "first_round", "any_of": [combo_at_least(3)]}
    effects: list[dict[str, Any]] = [*FINISH[:2], {**FINISH[2], "condition": cond}]
    state = scene(weapon_skill(effects), combo=3)
    d20s(monkeypatch, [HIT])
    state.round = 2  # 第一輪的分支不成立，只剩層數分支
    assert of(use(state), ShieldGained)


# ---------------------------------------------------------------------------
# 3. 雙匕首每次出招只 +1 連擊點（同一次施放對同一個目標最多一次）
# ---------------------------------------------------------------------------

DUAL = [
    # (說明, d20 序列, 連擊點)
    ("兩下都中", [HIT, HIT], 1),
    ("第一下中、第二下沒中", [HIT, MISS], 1),
    ("第一下沒中、第二下中", [MISS, HIT], 1),
    ("兩下都沒中", [MISS, MISS], 0),
]


@pytest.mark.parametrize(("name", "seq", "combo"), DUAL)
def test_dual_daggers_gain_one_combo_point_per_cast(
    name: str, seq: list[int], combo: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = scene(weapon_skill(STRIKE), weapon="dual_dagger")
    d20s(monkeypatch, seq)
    result = use(state)
    assert combo_of(result.state) == combo, name
    gained = [e for e in of(result, StacksChanged) if e.reason == "gained"]
    assert len(gained) == combo, name


def test_a_one_handed_weapon_skill_still_gains_one(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene(weapon_skill(STRIKE), weapon="dagger")
    d20s(monkeypatch, [HIT])
    assert combo_of(use(state).state) == 1


def test_an_area_weapon_skill_gains_once_per_target_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """範圍武器技打中兩個目標仍各 +1（每個目標一次，現況；待 PM）。"""
    line = {"type": "line", "size": 2}
    state = scene(weapon_skill(STRIKE, shape=line), foes=((4, 3), (5, 3)), weapon="dual_dagger")
    d20s(monkeypatch, [HIT, HIT])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, direction="east"))
    hit = {e.target_id for e in of(result, DamageDealt)}
    assert hit == {U2, U3}
    assert combo_of(result.state) == 2
