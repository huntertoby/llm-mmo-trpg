"""Phase 2E-2 4.2／4.5：``intercept``（挺身而出）——把單體攻擊改由相鄰的友方承受。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4, of
from tests.engine.test_passive_triggers import always
from trpg.engine import Attack, BattleState, UseSkill, preview, resolve, state_to_json
from trpg.engine.events import (
    EVENT_LIST_ADAPTER,
    AttackIntercepted,
    AttackRolled,
    DamageDealt,
    ReactionTriggered,
    UnitMoved,
)
from trpg.shared.types import Pos, Team

STAND = "skill_stand_firm"


def scene(
    *,
    guardians: tuple[tuple[int, int], ...] = ((4, 4),),
    target_xy: tuple[int, int] = (4, 3),
    attacker_skills: tuple[str, ...] = (),
    guardian_skills: tuple[str, ...] = (STAND,),
) -> BattleState:
    """U1（我方戰士）在 (3, 3) 手上有回合；U2（敵人，被攻擊者）在 ``target_xy``；
    U3、U4…（敵人，守護者）在 ``guardians``，各帶 ``guardian_skills``。"""
    xy = [target_xy, *guardians]
    m = make_map(FLAT7, ally=[(3, 3)], enemy=xy)
    attacker = caster_template(list(attacker_skills), base="hero_fighter")
    spawns = [spawn(Team.ALLY, (3, 3), attacker), spawn(Team.ENEMY, target_xy, no_reactions())]
    for pos in guardians:
        tmpl = no_reactions("hero_fighter", max_mana=99, skills=list(guardian_skills), max_hp=999)
        spawns.append(spawn(Team.ENEMY, pos, tmpl))
    return give_turn(make_state(m, spawns), U1)


def test_a_melee_attack_is_taken_by_the_adjacent_guardian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene()
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (hit,) = of(result, AttackIntercepted)
    assert (hit.guardian_id, hit.attacker_id, hit.target_id, hit.skill_id) == (U3, U1, U2, None)
    (trig,) = of(result, ReactionTriggered)
    assert (trig.unit_id, trig.reaction, trig.trigger_unit_id) == (U3, STAND, U1)
    assert trig.stamina_spent == 0
    (dmg,) = of(result, DamageDealt)
    assert dmg.target_id == U3
    assert result.state.units[U2].hp == state.units[U2].hp  # 原目標毫髮無傷
    assert result.state.units[U3].hp < state.units[U3].hp
    assert len(of(result, AttackRolled)) == 1  # 不重擲命中
    assert any(s.status_id == "guarded" for s in result.state.units[U3].statuses)
    assert result.state.units[U3].reactions_used == 1


def test_a_skill_attack_with_a_single_shape_is_intercepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(attacker_skills=("skill_shield_bash",))
    state.units[U1].mana = 99
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_shield_bash", target_id=U2))
    (hit,) = of(result, AttackIntercepted)
    assert hit.guardian_id == U3 and hit.skill_id == "skill_shield_bash"
    assert result.state.units[U2].hp == state.units[U2].hp
    assert not any(s.status_id == "stun" for s in result.state.units[U2].statuses)
    assert any(s.status_id == "stun" for s in result.state.units[U3].statuses)


def test_area_skills_are_not_intercepted(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(attacker_skills=("skill_cleave",))
    state.units[U1].mana = 99
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_cleave", direction="east"))
    assert of(result, DamageDealt) and not of(result, AttackIntercepted)
    assert result.state.units[U2].hp < state.units[U2].hp


def test_a_guardian_must_be_adjacent_to_the_target(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(guardians=((6, 6),))
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not of(result, AttackIntercepted)
    assert result.state.units[U2].hp < state.units[U2].hp


def test_the_target_itself_never_intercepts(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(guardians=())
    state.units[U2].reactions = ()
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not of(result, AttackIntercepted)


def test_a_miss_is_not_intercepted(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, d20=1)
    result = resolve(scene(), Attack(unit_id=U1, target_id=U2))
    assert not of(result, AttackIntercepted) and not of(result, ReactionTriggered)


def test_the_first_guardian_by_unit_id_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = scene(guardians=((5, 3), (4, 4)))  # U3 在 (5, 3)、U4 在 (4, 4)，都和 U2 相鄰
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (hit,) = of(result, AttackIntercepted)
    assert hit.guardian_id == U3
    assert result.state.units[U4].reactions_used == 0


def test_an_unavailable_first_guardian_falls_through_to_the_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(guardians=((5, 3), (4, 4)))
    state.units[U3].cooldowns[STAND] = 2
    (hit,) = of(resolve(state, Attack(unit_id=U1, target_id=U2)), AttackIntercepted)
    assert hit.guardian_id == U4


def test_the_intercept_does_not_refresh_taunts_and_ignores_the_targets_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene()
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not any(s.status_id == "taunted" for s in result.state.units[U1].statuses)
    assert not any(e.reaction == "block" for e in of(result, ReactionTriggered))


def test_displacement_is_recomputed_from_the_attacker_to_the_guardian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = scene(attacker_skills=("skill_gale_kick",), guardians=((4, 4),))
    state.units[U1].mana = 99
    # U1 (3,3) 踢 U2 (4,3)：原本往東推；改由 U3 (4,4) 承受，從 U1 (3,3) 看過去是往東南
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_gale_kick", target_id=U2))
    assert of(result, AttackIntercepted)
    moved = of(result, UnitMoved)
    assert result.state.units[U2].pos == state.units[U2].pos
    assert moved and all(m.unit_id == U3 for m in moved)
    assert result.state.units[U3].pos != Pos(x=4, y=4)


def test_preview_follows_the_real_branch_and_is_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene()
    before = state_to_json(state)
    pv = preview(state, Attack(unit_id=U1, target_id=U2))
    assert state_to_json(state) == before
    assert any(
        o.kind == "intercepted" and o.unit_id == U3 and o.detail == U2
        for o in pv.certain + pv.possible
    )
    always(monkeypatch)
    real = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert real.state.units[U3].hp < state.units[U3].hp


def test_the_intercept_is_deterministic_and_replayable(monkeypatch: pytest.MonkeyPatch) -> None:
    state = scene()
    first = resolve(state, Attack(unit_id=U1, target_id=U2))
    again = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert EVENT_LIST_ADAPTER.dump_json(first.events) == EVENT_LIST_ADAPTER.dump_json(again.events)  # type: ignore[arg-type]
    assert state_to_json(first.state) == state_to_json(again.state)
