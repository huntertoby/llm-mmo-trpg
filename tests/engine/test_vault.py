"""攀跳（Phase 3-21b，玩法 #24）：攀爬（相鄰高 2 層）與跳躍（越過 1 格寬的缺口）。"""

from __future__ import annotations

from dataclasses import replace
from typing import get_args

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of
from tests.engine.test_passive_triggers import always
from trpg.engine import BattleState, EndTurn, Vault, legal_actions, resolve
from trpg.engine.actions import Action
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.basics import vault_destinations, vault_problem
from trpg.engine.battle import has_only_end_turn
from trpg.engine.effects import ApplyStatusEffect, run_effects
from trpg.engine.events import DamageDealt, UnitMoved, UnitVaulted
from trpg.engine.runner import replay, run_battle
from trpg.engine.state import ObjectState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import ObjectId, Pos, Team

_ROWS = ["0000000"] * 7


def _heights(y3: str) -> str:
    rows = list(_ROWS)
    rows[3] = y3
    return "\n".join(rows)


def _terrain(y3: str) -> str:
    rows = ["......."] * 7
    rows[3] = y3
    return "\n".join(rows)


_PLATEAU = _heights("0002000")  # (3,3) 比 (2,3) 高 2 層
_GAP = _terrain("...x...")
_WALL = "\n".join(["...x..."] * 7)  # 貫穿全圖的深淵牆


def _vault(x: int, y: int) -> Vault:
    return Vault(unit_id=U1, dest=Pos(x=x, y=y))


def _state(
    heights: str = FLAT7,
    terrain: str | None = None,
    *,
    foe: tuple[int, int] = (6, 6),
    ally2: tuple[int, int] | None = None,
) -> BattleState:
    """U1（我方戰士）在 (2,3)；``foe`` 為敵人位置，``ally2`` 為另一個我方單位。"""
    allies = [(2, 3)] + ([ally2] if ally2 else [])
    m = make_map(heights, terrain, ally=allies, enemy=[foe])
    spawns = [spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", max_hp=999))]
    if ally2:
        spawns.append(spawn(Team.ALLY, ally2, no_reactions("hero_fighter", max_hp=999)))
    spawns.append(spawn(Team.ENEMY, foe, no_reactions("bandit", max_hp=999)))
    return give_turn(make_state(m, spawns), U1)


def _problem(state: BattleState, x: int, y: int) -> str:
    return vault_problem(state, state.units[U1], (x, y)) or ""


def test_climb_moves_up_two_levels_and_costs_ap_and_move_points() -> None:
    state = _state(_PLATEAU)
    core = state.ruleset.core
    result = resolve(state, _vault(3, 3))
    unit = result.state.units[U1]
    assert unit.xy == (3, 3)
    assert unit.ap == state.units[U1].ap - core.vault_ap_cost
    assert unit.move_points == state.units[U1].move_points - core.vault_move_cost
    (vaulted,) = of(result, UnitVaulted)
    assert vaulted.kind == "climb"
    (moved,) = of(result, UnitMoved)
    assert (moved.mode, moved.cost) == ("walk", core.vault_move_cost)


def test_a_normal_move_cannot_climb_two_levels_but_vault_can() -> None:
    state = _state(_PLATEAU)
    assert not any(a.type == "move" and a.path[-1] == Pos(x=3, y=3) for a in legal_actions(state))
    assert _vault(3, 3) in legal_actions(state)


def test_climbing_one_level_is_a_plain_move_not_a_vault() -> None:
    state = _state(_heights("0001000"))
    assert "直接走上去" in _problem(state, 3, 3)
    assert not any(isinstance(a, Vault) for a in legal_actions(state))


def test_climbing_three_levels_is_too_high() -> None:
    state = _state(_heights("0003000"))
    assert "太高" in _problem(state, 3, 3)


def test_climb_onto_an_occupied_tile_is_illegal() -> None:
    state = _state(_PLATEAU, ally2=(3, 3))
    with pytest.raises(IllegalActionError, match="已有單位"):
        resolve(state, _vault(3, 3))
    assert not any(isinstance(a, Vault) for a in legal_actions(state))


def test_jump_over_a_one_tile_chasm() -> None:
    state = _state(FLAT7, _GAP)
    assert _vault(4, 3) in legal_actions(state)
    result = resolve(state, _vault(4, 3))
    assert result.state.units[U1].xy == (4, 3)
    (vaulted,) = of(result, UnitVaulted)
    assert (vaulted.kind, vaulted.from_pos, vaulted.to_pos) == (
        "jump",
        Pos(x=2, y=3),
        Pos(x=4, y=3),
    )


def test_jump_is_not_offered_when_the_middle_tile_is_walkable() -> None:
    state = _state()
    assert not any(isinstance(a, Vault) for a in legal_actions(state))
    assert "不需要跳躍" in _problem(state, 4, 3)


def test_jump_over_a_two_wide_chasm_is_too_far() -> None:
    state = _state(FLAT7, _terrain("...xx.."))
    assert "太遠" in _problem(state, 5, 3)


def test_jump_over_a_unit_standing_on_the_gap_is_illegal() -> None:
    state = _state(FLAT7, _GAP, ally2=(0, 0))
    state.units[U2].pos = Pos(x=3, y=3)  # 缺口上站著單位（例如浮空）
    assert "有單位" in _problem(state, 4, 3)


def test_jump_over_a_blocking_object_is_illegal() -> None:
    state = _state(FLAT7, _GAP)
    pillar = ObjectState(
        id=ObjectId("pillar"), kind="stone_pillar", pos=Pos(x=3, y=3), hp=None, max_hp=None
    )
    state.objects[pillar.id] = pillar
    state.set_tile(3, 3, replace(state.tile(3, 3), object_id=pillar.id))
    assert "擋路" in _problem(state, 4, 3)


def test_jump_over_a_wall_is_illegal() -> None:
    state = _state(FLAT7, _terrain("...#..."))
    assert "不是缺口" in _problem(state, 4, 3)


def test_jump_landing_occupied_or_unstandable_is_illegal() -> None:
    occupied = _state(FLAT7, _GAP, ally2=(4, 3))
    assert "已有單位" in _problem(occupied, 4, 3)
    two = _state(FLAT7, _terrain("...xx.."))
    assert "不能站立" in _problem(two, 4, 3)


def test_jump_landing_too_high_or_too_low_is_illegal() -> None:
    high = _state(_heights("0000200"), _GAP)
    assert "落點太高" in _problem(high, 4, 3)
    low = _state(_heights("0020000"), _GAP)  # 起點 (2,3) 高 2，落點 (4,3) 高 0：落差達摔傷門檻
    assert "太低" in _problem(low, 4, 3)
    ok = _state(_heights("0010100"), _GAP)  # 落差 1：可以
    assert _problem(ok, 4, 3) == ""


def test_vault_needs_ap_and_move_points() -> None:
    state = _state(_PLATEAU)
    no_ap = state.clone()
    no_ap.units[U1].ap = 0
    assert "AP 不足" in _problem(no_ap, 3, 3)
    tired = state.clone()
    tired.units[U1].move_points = 1
    assert "移動點數不足" in _problem(tired, 3, 3)
    assert vault_destinations(tired, tired.units[U1]) == []


def test_vault_is_illegal_when_rooted_prone_or_speed_zero() -> None:
    state = _state(_PLATEAU)
    for status, word in (("root", "定身"), ("prone", "倒地")):
        hit = run_effects(
            state.clone(), [ApplyStatusEffect(target_id=U1, status_id=status, source_id=U3)]
        ).state
        assert word in _problem(hit, 3, 3)
    still = state.clone()
    still.units[U1].speed = 0
    assert "不能移動" in _problem(still, 3, 3)


def test_vault_rejects_bad_destinations() -> None:
    state = _state(_PLATEAU)
    for dest in ((2, 3), (4, 4), (2, 6), (9, 9)):
        with pytest.raises(IllegalActionError):
            resolve(state, _vault(*dest))


def test_leaving_an_adjacent_enemy_provokes_an_opportunity_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    m = make_map(_PLATEAU, ally=[(2, 3)], enemy=[(2, 4)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", max_hp=999)),
                spawn(Team.ENEMY, (2, 4), "bandit"),  # 保留反應：會藉機攻擊
            ],
        ),
        U1,
    )
    result = resolve(state, _vault(3, 3))
    assert any(d.target_id == U1 for d in of(result, DamageDealt))
    assert result.state.units[U1].xy == (3, 3)


def test_staying_adjacent_to_the_enemy_does_not_provoke_an_opportunity_attack() -> None:
    state = _state(_PLATEAU, foe=(4, 3))
    result = resolve(state, _vault(3, 3))
    assert not any(d.target_id == U1 for d in of(result, DamageDealt))


def test_vault_alone_keeps_the_turn_open() -> None:
    state = _state(_PLATEAU)
    unit = state.units[U1]
    unit.ap = 1
    unit.ran_this_turn = True
    unit.aimed = True
    unit.move_points = 2
    unit.statuses = []
    assert any(isinstance(a, Vault) for a in legal_actions(state))
    assert not has_only_end_turn(state)


def test_has_only_end_turn_agrees_with_legal_actions() -> None:
    for state in (_state(_PLATEAU), _state(FLAT7, _GAP), _state()):
        for ap, mp in ((3, 5), (1, 2), (0, 0), (1, 0)):
            state.units[U1].ap, state.units[U1].move_points = ap, mp
            only_end = [type(a) for a in legal_actions(state)] == [EndTurn]
            assert has_only_end_turn(state) == only_end


def test_vault_numbers_come_from_core_rules() -> None:
    cheap = make_setup(
        make_map(_PLATEAU, ally=[(2, 3)], enemy=[(6, 6)]),
        [
            spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (6, 6), no_reactions("bandit")),
        ],
        vault_move_cost=1,
        vault_climb_height=3,
    )
    assert cheap.ruleset.core.vault_move_cost == 1
    assert cheap.ruleset.core.vault_climb_height == 3


def _chasm_wall_state(*, move_points: int) -> BattleState:
    """貫穿全圖的 1 格寬深淵牆（x=3）：走路到不了敵人，只有跳過去才行。"""
    m = make_map(FLAT7, _WALL, ally=[(2, 3)], enemy=[(5, 3)])
    state = give_turn(
        make_state(
            m,
            [
                spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter", max_hp=999)),
                spawn(Team.ENEMY, (5, 3), no_reactions("bandit", max_hp=999)),
            ],
        ),
        U1,
    )
    state.units[U1].move_points = move_points
    return state


def test_ai_jumps_a_chasm_that_blocks_the_whole_path() -> None:
    state = _chasm_wall_state(move_points=2)
    assert UtilityAI(library().ai_profiles)(state) == _vault(4, 3)


def test_ai_does_not_vault_for_a_small_saving() -> None:
    state = _state(_PLATEAU, foe=(4, 4))  # 繞過高台只多一兩步
    assert not isinstance(UtilityAI(library().ai_profiles)(state), Vault)


def test_vault_battle_replays_identically() -> None:
    terrain = "\n".join(["...x..."] * 7)
    m = make_map(FLAT7, terrain, ally=[(1, 3)], enemy=[(5, 3)])
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, (1, 3), no_reactions("hero_fighter")),
            spawn(Team.ENEMY, (5, 3), no_reactions()),
        ],
    )
    ai = UtilityAI(library().ai_profiles)
    result = run_battle(setup, 3, policy=ai)
    assert any(isinstance(a, Vault) for a in result.actions)
    assert replay(setup, 3, result.actions).events == result.events


def test_basic_actions_stay_within_the_limit_of_ten() -> None:
    """``docs/design/05-戰鬥.md`` 5.2.2：基本動作總數上限 10（不含技能與管理動作）。"""
    union = get_args(get_args(Action.__value__)[0])
    types = {get_args(cls.model_fields["type"].annotation)[0] for cls in union}
    basic = types - {"use_skill", "end_turn", "end_stance", "set_reaction_mode"}
    assert {"move", "attack", "run", "defend", "swap", "aim", "vault"} <= basic
    assert len(basic) <= 10
