"""LW-1 獨狼條件（#156，06 6.37）：實際跑引擎驗證判定、整場固定、技能／被動／詞條都吃同一個判定。"""

from __future__ import annotations

import json

import pytest

from tests.engine.helpers import (
    give_turn,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, hit_with
from tests.engine.test_gear import _geared
from trpg.content.skills import ConditionSpec, condition_text
from trpg.engine import BattleState, UseSkill, resolve, start_battle
from trpg.engine.events import DamageDealt
from trpg.engine.gear.core import gear_defense_permille
from trpg.engine.lone_wolf import mark_lone_wolves
from trpg.engine.rules.statuses import damage_taken_permille
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import state_from_json, state_to_json
from trpg.shared.types import Team

POUNCE = "skill_lone_wolf_pounce"
SHOT = "skill_unguarded_shot"
STRIDER = "skill_lone_strider"
LONE = ConditionSpec(type="lone_wolf")


def _state(
    allies: int, *, enemies: int = 1, third: int = 0, hero_skills: tuple[str, ...] = ()
) -> BattleState:
    spots = [(1, 1), (1, 3), (1, 5)]
    foes = [(5, 1), (5, 3), (5, 5)]
    m = make_map(FLAT7, ally=spots[: 1 + allies], enemy=foes[:enemies])
    units = [spawn(Team.ALLY, spots[0], "hero_fighter", skills=hero_skills)]
    units += [spawn(Team.ALLY, spots[1 + i], "bandit") for i in range(allies)]
    units += [spawn(Team.ENEMY, foes[i], no_reactions("bandit")) for i in range(enemies)]
    units += [spawn(Team.THIRD, (3, 6 - i), no_reactions("bandit")) for i in range(third)]
    return make_state(m, units)


def _lone(state: BattleState) -> dict[str, bool]:
    return {u.id: u.lone_wolf for u in state.units_sorted()}


# ---------------------------------------------------------------------------
# 判定：各種隊伍組合
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("allies", "enemies", "third", "hero_lone"),
    [
        (0, 1, 0, True),  # 一個人出城
        (0, 3, 0, True),  # 敵人多少不影響
        (1, 1, 0, False),  # 帶一名隊友（傭兵、影子、劇情夥伴都是開場在場的同陣營單位）
        (2, 1, 0, False),
        (0, 1, 2, True),  # 三方混戰的第三方不算隊友
    ],
)
def test_lone_wolf_is_only_you_on_your_side_at_the_start(
    allies: int, enemies: int, third: int, hero_lone: bool
) -> None:
    state = _state(allies, enemies=enemies, third=third)
    assert state.units[U1].lone_wolf is hero_lone
    for unit in state.units_sorted():
        if unit.team is Team.ALLY and unit.id != U1:
            assert not unit.lone_wolf
    # 通用條件：敵方只有一名時敵方也成立；第三方各自看自己的陣營
    enemy = [u for u in state.units_sorted() if u.team is Team.ENEMY]
    assert all(u.lone_wolf is (len(enemy) == 1) for u in enemy)


def test_summons_do_not_count_as_allies() -> None:
    """自己的召喚物與分身不算隊友：場上有召喚物的開場狀態，主角仍是獨狼，召喚物自己不是。"""
    state = _state(1)
    summon = state.units[U2]
    summon.owner_id = U1  # 把同陣營的那名當成主角的召喚物
    mark_lone_wolves(state)
    assert state.units[U1].lone_wolf
    assert not summon.lone_wolf


def test_the_flag_is_fixed_for_the_whole_battle() -> None:
    """隊友倒下不會變成獨狼；有單位加入也不會失去（只在開場算一次）。"""
    with_ally = _state(1)
    with_ally.units[U2].downed = True
    assert not condition_met(with_ally, with_ally.units[U1], LONE, Subject(None, (0, 0)))
    alone = _state(0)
    assert condition_met(alone, alone.units[U1], LONE, Subject(None, (0, 0)))
    # 序列化往返保留
    again = state_from_json(state_to_json(alone))
    assert _lone(again) == _lone(alone)


def test_non_lone_units_do_not_serialize_the_key() -> None:
    state = _state(1, enemies=2)
    assert not any(u.lone_wolf for u in state.units_sorted())
    units = json.loads(state_to_json(state))["units"]
    assert all("lone_wolf" not in u for u in units.values())


def test_condition_text() -> None:
    assert condition_text(LONE) == "獨狼（開戰時我方只有你）"
    lacks = ConditionSpec(type="self_lacks_status", status="root")
    assert (
        condition_text(lacks, status_name=lambda s: {"root": "定身"}[s]) == "自身沒有狀態「定身」"
    )


# ---------------------------------------------------------------------------
# 技能：效果層級（孤狼撲擊、無人掩護）與被動（獨行者）
# ---------------------------------------------------------------------------


def _duel(allies: int, skill: str) -> BattleState:
    m = make_map(FLAT7, ally=[(2, 3), (0, 0)][: 1 + allies], enemy=[(3, 3)])
    units = [spawn(Team.ALLY, (2, 3), "hero_fighter", skills=(skill,))]
    units += [spawn(Team.ALLY, (0, 0), "bandit")] * allies
    units += [spawn(Team.ENEMY, (3, 3), no_reactions("bandit"))]
    state = make_state(m, units)
    state.units[U2 if allies == 0 else U3].hp = 999
    state.units[U2 if allies == 0 else U3].max_hp = 999
    return give_turn(state, U1)


@pytest.mark.parametrize(("allies", "hits"), [(0, 2), (1, 1)])
def test_pounce_adds_a_second_hit_only_when_alone(allies: int, hits: int) -> None:
    state = hit_with(_duel(allies, POUNCE))
    target = U2 if allies == 0 else U3
    result = resolve(state, UseSkill(unit_id=U1, skill_id=POUNCE, target_id=target))
    dealt = [e for e in result.events if isinstance(e, DamageDealt) and e.target_id == target]
    assert len(dealt) == hits


def _ranged_duel(allies: int) -> BattleState:
    m = make_map(FLAT7, ally=[(0, 3), (0, 0)][: 1 + allies], enemy=[(4, 3)])
    units = [spawn(Team.ALLY, (0, 3), "hero_archer", skills=(SHOT,))]
    units += [spawn(Team.ALLY, (0, 0), "bandit")] * allies
    units += [spawn(Team.ENEMY, (4, 3), no_reactions("bandit"))]
    return give_turn(make_state(m, units), U1)


@pytest.mark.parametrize(("allies", "concealed"), [(0, True), (1, False)])
def test_unguarded_shot_conceals_only_when_alone(allies: int, concealed: bool) -> None:
    state = hit_with(_ranged_duel(allies))
    target = U2 if allies == 0 else U3
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SHOT, target_id=target))
    assert result.state.units[U1].has_status("concealed") is concealed


@pytest.mark.parametrize(("allies", "buffed"), [(0, True), (1, False)])
def test_strider_passive_buffs_at_turn_start_only_when_alone(allies: int, buffed: bool) -> None:
    m = make_map(FLAT7, ally=[(1, 3), (0, 0)][: 1 + allies], enemy=[(5, 3)])
    units = [spawn(Team.ALLY, (1, 3), "hero_fighter", skills=(STRIDER,))]
    units += [spawn(Team.ALLY, (0, 0), "bandit")] * allies
    units += [spawn(Team.ENEMY, (5, 3), no_reactions("bandit"))]
    setup = make_setup(m, units).model_copy(update={"first_team": Team.ALLY})
    state = start_battle(setup, 0)
    assert state.active_unit == U1
    hero = state.units[U1]
    for status in ("empowered", "guarded"):  # 造成的傷害提高（屬性縮放）、受到的傷害降低
        assert hero.has_status(status) is buffed, status
    taken = damage_taken_permille(state.ruleset, hero)
    assert (taken < 1000) is buffed


# ---------------------------------------------------------------------------
# 08「獨自」詞條＝同一個判定
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("allies", "bonus"), [(0, 150), (1, 0)])
def test_lone_affix_uses_the_same_rule(allies: int, bonus: int) -> None:
    hero = _geared({"body": [("affix_cond_lone_defense", 150)]})
    m = make_map(FLAT7, ally=[(0, 0), (0, 2)][: 1 + allies], enemy=[(6, 6)])
    units = [hero, *([spawn(Team.ALLY, (0, 2), "bandit")] * allies)]
    units += [spawn(Team.ENEMY, (6, 6), no_reactions("bandit"))]
    state = start_battle(make_setup(m, units), 0)
    assert gear_defense_permille(state.units[U1]) == bonus
