"""Phase 2D-1 3.9 第 8 項：嘲諷（``taunted``）——劣勢、來源倒下時移除、刷新換來源、AI 服從。"""

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
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, of, script_rolls
from trpg.engine import Attack, Move, UseSkill, preview, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.effects import ApplyStatusEffect, DamageEffect, run_effects
from trpg.engine.events import StatusApplied, StatusRemoved
from trpg.engine.rules.combat import advantage_state
from trpg.engine.state import BattleState, StatusInstance
from trpg.shared.types import Team, UnitId

ROAR = "skill_taunting_roar"


def _scene(*, taunter: UnitId | None = U2, weak_hp: int | None = None) -> BattleState:
    """U1 我方戰士 (3, 3)；相鄰的敵人 U2（高物理抗性）(4, 3)、U3 (3, 4)；U1 被 ``taunter`` 嘲諷。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3), (3, 4)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter", skills=[])),
            spawn(
                Team.ENEMY, (4, 3), no_reactions(resist={"physical": 900})
            ),  # 嘲諷者：幾乎不受物理傷害
            spawn(Team.ENEMY, (3, 4), no_reactions()),
        ],
    )
    state = give_turn(state, U1)
    if weak_hp is not None:
        state.units[U3].hp = weak_hp
    if taunter is not None:
        state.units[U1].statuses = [StatusInstance("taunted", 2, taunter)]
    return state


def test_attacking_anyone_but_the_taunter_has_disadvantage() -> None:
    state = _scene()
    assert advantage_state(state, state.units[U1], state.units[U2]) == "none"
    assert advantage_state(state, state.units[U1], state.units[U3]) == "disadvantage"
    # preview 與擲骰共用同一個函式：對非嘲諷者的命中率較低
    plain = _scene(taunter=None)
    hit = preview(state, Attack(unit_id=U1, target_id=U3)).hit_chance
    assert hit is not None
    assert hit < (preview(plain, Attack(unit_id=U1, target_id=U3)).hit_chance or 0)
    assert (
        preview(state, Attack(unit_id=U1, target_id=U2)).hit_chance
        == preview(plain, Attack(unit_id=U1, target_id=U2)).hit_chance
    )


def test_a_taunt_without_a_source_has_no_effect() -> None:
    state = _scene()
    state.units[U1].statuses = [StatusInstance("taunted", 2, None)]
    assert advantage_state(state, state.units[U1], state.units[U3]) == "none"


def test_the_taunt_is_removed_when_its_source_goes_down() -> None:
    state = _scene()
    kill = DamageEffect(target_id=U2, source_id=U1, mode="lethal")
    result = run_effects(state, [kill])
    assert result.state.units[U1].get_status("taunted") is None
    removed = of(result, StatusRemoved)
    assert [(e.target_id, e.status_id, e.reason) for e in removed] == [
        (U1, "taunted", "source_lost")
    ]
    # 另一名敵人倒下時不影響
    other = run_effects(state, [DamageEffect(target_id=U3, source_id=U1, mode="lethal")])
    assert other.state.units[U1].get_status("taunted") is not None


def test_reapplying_the_taunt_changes_the_source_to_the_latest_caster() -> None:
    state = _scene()
    effect = ApplyStatusEffect(target_id=U1, status_id="taunted", source_id=U3)
    result = run_effects(state, [effect])
    status = result.state.units[U1].get_status("taunted")
    assert status is not None and status.source_id == U3 and status.remaining == 2
    (applied,) = of(result, StatusApplied)
    assert applied.refreshed and applied.source_id == U3
    assert advantage_state(result.state, result.state.units[U1], result.state.units[U2]) == (
        "disadvantage"
    )


def test_the_taunting_roar_skill_taunts_adjacent_enemies(monkeypatch: pytest.MonkeyPatch) -> None:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3), (3, 4), (6, 6)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([ROAR], base="hero_fighter")),
            spawn(Team.ENEMY, (4, 3), no_reactions()),
            spawn(Team.ENEMY, (3, 4), no_reactions()),
            spawn(Team.ENEMY, (6, 6), no_reactions()),
        ],
    )
    state = give_turn(state, U1)
    script_rolls(monkeypatch, [20] * 10)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=ROAR))
    taunted = [u.id for u in result.state.living_units() if u.has_status("taunted")]
    assert taunted == [U2, U3]  # (6, 6) 的敵人不在環形範圍內
    assert all(result.state.units[u].get_status("taunted").source_id == U1 for u in taunted)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def _ai() -> UtilityAI:
    return UtilityAI(library().ai_profiles)


def test_a_taunted_ai_attacks_the_taunter_even_when_another_target_is_weaker() -> None:
    free = _ai()(_scene(taunter=None, weak_hp=1))
    assert isinstance(free, Attack) and free.target_id == U3  # 對照：沒有嘲諷時收割殘血的 U3
    taunted = _ai()(_scene(weak_hp=1))
    assert isinstance(taunted, Attack) and taunted.target_id == U2


def test_a_taunted_ai_that_cannot_reach_the_taunter_acts_normally() -> None:
    m = make_map(FLAT7, ally=[(0, 0)], enemy=[(6, 6), (1, 0)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (0, 0), no_reactions("hero_fighter", skills=[])),
            spawn(Team.ENEMY, (6, 6), no_reactions()),
            spawn(Team.ENEMY, (1, 0), no_reactions()),
        ],
    )
    state = give_turn(state, U1)
    state.units[U3].hp = 1
    state.units[U1].statuses = [StatusInstance("taunted", 2, U2)]
    action = _ai()(state)
    # 打不到嘲諷者：照一般規則行動（不會僵住；這個局面下走向嘲諷者或收割 U3 都可以）
    assert isinstance(action, Attack | Move)
