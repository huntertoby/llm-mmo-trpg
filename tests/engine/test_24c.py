"""Phase 3-24c：撞擊條件 ``target_collided``、獻祭召喚物 ``sacrifice_summon``、火器的武器技。"""

from __future__ import annotations

from collections.abc import Sequence
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
from tests.engine.test_weapons_24a2 import FLAT9, armed, dice, foe, kinds, state_of, weapon
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine import BattleState, EndTurn, UseSkill, legal_actions, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    Healed,
    StatusApplied,
    SummonExpired,
    UnitSummoned,
)
from trpg.engine.rules.combat import is_concealed
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
FLAT = "\n".join(["0000000"] * 7)


# ---------------------------------------------------------------------------
# 撞擊條件
# ---------------------------------------------------------------------------


def _shove_arena() -> BattleState:
    shove = make_skill(
        "skill_t_shove", {"type": "single", "range": 6}, [{"type": "push", "distance": 2}]
    )
    m = make_map(FLAT, None, ally=[(2, 3)], enemy=[(6, 3), (4, 5)])
    spawns = [
        spawn(Team.ALLY, (2, 3), caster_template([shove.id])),
        spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=200)),
        spawn(Team.ENEMY, (4, 5), no_reactions(max_hp=200)),
    ]
    return give_turn(make_state(m, spawns, skills=[shove]), U1)


def test_a_unit_that_hit_the_map_edge_counts_as_collided_this_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = _shove_arena()
    cond = ConditionSpec(type="target_collided")
    caster = state.units[U1]
    assert not condition_met(state, caster, cond, Subject(state.units[U2], state.units[U2].xy))
    after = resolve(state, UseSkill(unit_id=U1, skill_id="skill_t_shove", target_id=U2)).state
    hit, other = after.units[U2], after.units[U3]
    assert condition_met(after, after.units[U1], cond, Subject(hit, hit.xy))
    assert not condition_met(after, after.units[U1], cond, Subject(other, other.xy))  # 沒被撞的不算


def test_collided_expires_with_the_round(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    after = resolve(
        _shove_arena(), UseSkill(unit_id=U1, skill_id="skill_t_shove", target_id=U2)
    ).state
    unit = after.units[U2]
    cond = ConditionSpec(type="target_collided")
    assert condition_met(after, after.units[U1], cond, Subject(unit, unit.xy))
    later = after.clone()
    later.round += 1
    assert not condition_met(later, later.units[U1], cond, Subject(unit, unit.xy))


def test_the_unit_that_was_hit_by_the_pushed_one_is_collided_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    m = make_map(FLAT, None, ally=[(2, 3)], enemy=[(4, 3), (5, 3)])
    shove = make_skill(
        "skill_t_shove", {"type": "single", "range": 6}, [{"type": "push", "distance": 2}]
    )
    spawns = [
        spawn(Team.ALLY, (2, 3), caster_template([shove.id])),
        spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=200)),
        spawn(Team.ENEMY, (5, 3), no_reactions(max_hp=200)),
    ]
    state = give_turn(make_state(m, spawns, skills=[shove]), U1)
    after = resolve(state, UseSkill(unit_id=U1, skill_id="skill_t_shove", target_id=U2)).state
    assert after.units[U2].collided_round == after.round == after.units[U3].collided_round


def test_bone_pursuit_deals_more_only_to_a_collided_target(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=19, die=3)
    skill = library().skills["skill_bone_pursuit"]
    assert skill.effects[1].condition is not None
    assert skill.effects[1].condition.type == "target_collided"

    def total(collided: bool) -> int:
        state = state_of(
            [armed(Team.ALLY, (1, 2), weapon("one_handed_sword"), skills=[skill.id]), foe((2, 2))]
        )
        if collided:
            state.units[U2].collided_round = state.round
        res = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2))
        return sum(e.amount for e in kinds(res.events, DamageDealt))

    assert total(True) > total(False)


# ---------------------------------------------------------------------------
# 獻祭召喚物
# ---------------------------------------------------------------------------

SUMMON = "summon_skeleton_warrior"


def _sacrifice_skill(**effect: Any) -> SkillDef:
    spec = {"type": "sacrifice_summon", "dice": "2d6", "radius": 1, **effect}
    return make_skill("skill_t_sac", {"type": "single", "range": 6}, [spec])


def _summon_skill() -> SkillDef:
    return make_skill(
        "skill_t_call",
        {"type": "ground_tile", "range": 6},
        [{"type": "summon", "unit": SUMMON, "duration": 3}],
    )


def _sac_arena(
    sac: SkillDef,
    foes: Sequence[tuple[int, int]] = ((4, 3), (5, 3), (6, 6)),
    summon_at: tuple[int, int] = (4, 4),
) -> BattleState:
    call = _summon_skill()
    m = make_map(FLAT, None, ally=[(0, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([call.id, sac.id], max_hp=100))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=300)) for xy in foes]
    state = give_turn(make_state(m, spawns, skills=[call, sac]), U1)
    state.units[U1].ap = 6
    res = resolve(
        state,
        UseSkill(unit_id=U1, skill_id=call.id, target_pos=Pos(x=summon_at[0], y=summon_at[1])),
    )
    (summoned,) = kinds(res.events, UnitSummoned)
    assert summoned.pos == Pos(x=summon_at[0], y=summon_at[1])
    res.state.units[U1].cooldowns[call.id] = 9  # 不再召喚，測試只看獻祭
    return res.state


def _cast_sac(state: BattleState, target: UnitId) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id="skill_t_sac", target_id=target))


def test_sacrifice_explodes_at_the_summons_tile_and_removes_it() -> None:
    state = _sac_arena(_sacrifice_skill(element="fire"))
    summon = next(u for u in state.units.values() if u.owner_id == U1)
    res = _cast_sac(state, summon.id)
    (gone,) = kinds(res.events, SummonExpired)
    assert gone.reason == "sacrificed" and gone.unit_id == summon.id
    assert not res.state.units[summon.id].alive
    hurt = {e.target_id for e in kinds(res.events, DamageDealt)}
    # (4,3) 與召喚物 (4,4) 相鄰 → 波及；(5,3) 距離 2、(6,6) 更遠 → 不波及
    assert hurt == {U2}
    assert not kinds(res.events, AttackRolled)  # 自動命中，不擲命中


def test_sacrifice_radius_comes_from_the_data() -> None:
    state = _sac_arena(_sacrifice_skill(element="fire", radius=2))
    summon = next(u for u in state.units.values() if u.owner_id == U1)
    hurt = {e.target_id for e in kinds(_cast_sac(state, summon.id).events, DamageDealt)}
    assert hurt == {U2, U3}
    state0 = _sac_arena(_sacrifice_skill(element="fire", radius=0))
    summon0 = next(u for u in state0.units.values() if u.owner_id == U1)
    assert not kinds(_cast_sac(state0, summon0.id).events, DamageDealt)


def test_sacrifice_without_element_heals_nearby_allies_not_enemies() -> None:
    state = _sac_arena(_sacrifice_skill(radius=2), summon_at=(1, 3))
    state.units[U1].hp = 30
    summon = next(u for u in state.units.values() if u.owner_id == U1)
    res = _cast_sac(state, summon.id)
    healed = {e.target_id for e in kinds(res.events, Healed)}
    assert U1 in healed and not (healed & {U2, U3, U4})
    assert not kinds(res.events, DamageDealt)
    assert res.state.units[U1].hp > 30


def test_only_your_own_summon_can_be_sacrificed() -> None:
    state = _sac_arena(_sacrifice_skill(element="fire"))
    actions = [
        a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == "skill_t_sac"
    ]
    summon = next(u for u in state.units.values() if u.owner_id == U1)
    assert {a.target_id for a in actions} == {summon.id}
    with pytest.raises(IllegalActionError, match="召喚物"):
        _cast_sac(state, U2)  # 敵人
    with pytest.raises(IllegalActionError):
        _cast_sac(state, U1)  # 自己


def test_ai_sacrifices_a_summon_standing_in_the_enemy() -> None:
    sac = _sacrifice_skill(element="fire", dice="4d6", radius=1)
    state = _sac_arena(sac, foes=((4, 3), (3, 4), (5, 4)))
    state.units[U1].mana = 99
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_t_sac"


def test_ai_does_not_sacrifice_when_nobody_is_near() -> None:
    sac = _sacrifice_skill(element="fire", radius=1)
    state = _sac_arena(sac, foes=((6, 0), (6, 1)))
    action = UtilityAI(library().ai_profiles)(state)
    assert not (isinstance(action, UseSkill) and action.skill_id == "skill_t_sac")


def test_shipped_sacrifice_skills_pass_the_budget() -> None:
    from trpg.skillgen.validate import validate_skill  # noqa: PLC0415

    lib = library()
    for sid in ("skill_soul_burst", "skill_spirit_offering"):
        assert validate_skill(lib.skills[sid], lib) == []


# ---------------------------------------------------------------------------
# 火器的武器技
# ---------------------------------------------------------------------------

SHOT = "skill_high_ground_shot"


def _gun(
    target_at: tuple[int, int] = (6, 2), *, gun: Any = None, moved: bool = False, **kw: Any
) -> BattleState:
    spawns = [
        armed(Team.ALLY, (1, 2), gun or weapon("longgun"), skills=[SHOT], **kw),
        foe(target_at),
    ]
    state = state_of(spawns)
    state.units[U1].moved_this_turn = moved
    return state


def _fire(state: BattleState) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SHOT, target_id=U2))


def test_a_weapon_skill_spends_a_round_and_an_empty_magazine_blocks_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = _gun(target_at=(4, 2))
    assert state.units[U1].ammo == 1
    after = _fire(state).state
    assert after.units[U1].ammo == 0
    after.units[U1].ap = 3
    after.units[U1].cooldowns = {}
    assert not [a for a in legal_actions(after) if isinstance(a, UseSkill) and a.skill_id == SHOT]
    with pytest.raises(IllegalActionError, match="空膛"):
        _fire(after)


def test_the_weapon_skill_gunshot_reveals_a_hidden_shooter(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    base = state_of(
        [armed(Team.ALLY, (1, 2), weapon("longgun"), skills=[SHOT]), foe((4, 2))],
        objects=[(1, 2, "grass")],
    )
    assert is_concealed(base, base.units[U1])
    res = _fire(base)
    assert "revealed" in [e.status_id for e in kinds(res.events, StatusApplied)]
    quiet = state_of(
        [armed(Team.ALLY, (1, 2), weapon("longgun", gunshot=False), skills=[SHOT]), foe((4, 2))],
        objects=[(1, 2, "grass")],
    )
    assert "revealed" not in [e.status_id for e in kinds(_fire(quiet).events, StatusApplied)]


def test_the_weapon_skill_gets_steady_point_blank_and_far_modifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    steady = kinds(_fire(_gun(target_at=(3, 2))).events, AttackRolled)[0]
    moved = kinds(_fire(_gun(target_at=(3, 2), moved=True)).events, AttackRolled)[0]
    assert steady.modifier_bonus == moved.modifier_bonus + 2 or steady.total == moved.total + 2
    near = kinds(_fire(_gun(target_at=(2, 2), moved=True)).events, AttackRolled)[0]
    assert near.total == moved.total - 2  # 貼臉命中 −2
    dmg = {
        d: sum(
            e.amount
            for e in kinds(_fire(_gun(target_at=(1 + d, 2), moved=True)).events, DamageDealt)
        )
        for d in (1, 3, 6)
    }
    assert dmg[1] < dmg[3] < dmg[6]  # 貼臉 −50%、遠距 +25%


def test_a_bow_weapon_skill_is_not_affected(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = state_of([armed(Team.ALLY, (1, 2), weapon("bow"), skills=[SHOT]), foe((2, 2))])
    res = _fire(state)
    assert res.state.units[U1].ammo == 0
    assert kinds(res.events, AttackRolled)[0].modifier_bonus == 0


def test_spell_skills_do_not_use_the_magazine() -> None:
    bolt = make_skill(
        "skill_t_bolt",
        {"type": "single", "range": 5},
        [{"type": "damage", "dice": "1d6", "element": "fire"}],
        weapon_req="any",
    )
    m = make_map(FLAT9, None, ally=[(1, 2)], enemy=[(3, 2)])
    spawns = [
        armed(
            Team.ALLY, (1, 2), weapon("longgun"), base="hero_archer", skills=[bolt.id], max_mana=99
        ),
        spawn(Team.ENEMY, (3, 2), no_reactions(max_hp=100)),
    ]
    state = give_turn(make_state(m, spawns, skills=[bolt]), U1)
    state.units[U1].ammo = 0  # 空膛也能放法術
    res = resolve(state, UseSkill(unit_id=U1, skill_id=bolt.id, target_id=U2))
    assert res.state.units[U1].ammo == 0 and kinds(res.events, DamageDealt)


def test_end_turn_is_still_legal_with_an_empty_gun() -> None:
    state = _gun(target_at=(4, 2))
    state.units[U1].ammo = 0
    assert any(isinstance(a, EndTurn) for a in legal_actions(state))


# ---------------------------------------------------------------------------
# 重播
# ---------------------------------------------------------------------------


def test_a_battle_with_gun_skills_and_sacrifice_replays_identically() -> None:
    from tests.engine.helpers import make_setup  # noqa: PLC0415
    from trpg.engine.runner import LOG_FORMAT, replay, run_battle  # noqa: PLC0415
    from trpg.engine.state import state_to_json  # noqa: PLC0415

    call = _summon_skill()
    sac = _sacrifice_skill(element="fire", dice="3d6", radius=2)
    m = make_map(FLAT9, None, ally=[(0, 1), (0, 3)], enemy=[(8, 2), (7, 3)])
    spawns = [
        armed(Team.ALLY, (0, 1), weapon("longgun"), base="hero_archer", skills=[SHOT]),
        spawn(Team.ALLY, (0, 3), caster_template([call.id, sac.id], max_hp=120)),
        foe((8, 2)),
        foe((7, 3)),
    ]
    setup = make_setup(m, spawns, max_rounds=12, skills=[call, sac])
    policy = UtilityAI(library().ai_profiles)
    run = run_battle(setup, 7, policy)
    again = replay(setup, 7, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert LOG_FORMAT.endswith("/93")
