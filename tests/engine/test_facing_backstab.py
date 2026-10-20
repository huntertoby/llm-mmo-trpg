"""Phase 3D-8d：朝向、背刺 ``from_behind``、瞬步 ``shadowstep``、潛行偷襲 ``self_concealed``
（``docs/phases/Phase3D計畫.md`` 9.3）。

朝向：開場、步行與衝鋒後更新、攻擊後面向目標、強制位移不改、序列化與重播；背刺：背後格近戰有
加成、側面沒有、Boss 也適用、預覽與紀錄顯示「背刺」；瞬步：``choose`` 兩段選取、``behind`` 背後格
可站、被占時改最近空格、都沒有則不能施放、不觸發藉機攻擊、接傷害吃到背刺；潛行偷襲：隱蔽中攻擊有
加成、攻擊後脫離隱蔽。
"""

from __future__ import annotations

import io
from fractions import Fraction
from pathlib import Path

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from tests.engine.skill_helpers import U1, U2, U3, of
from tests.engine.test_modifiers import mod
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine import (
    Attack,
    BattleState,
    Move,
    ResolveResult,
    Shove,
    UseSkill,
    legal_actions,
    preview,
    resolve,
)
from trpg.engine import modifiers as mods
from trpg.engine.ai.utility import _facing_terms, _unit_position_value
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    ReactionTriggered,
    StatusRemoved,
    SurfaceEntered,
    UnitMoved,
)
from trpg.engine.rules.facing import back_xy, facing_between, is_behind, opening_facing
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import StatusInstance, state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team

BACKSTAB = "skill_shadow_backstab"
AMBUSH = "skill_shadow_ambush"
SEVEN = "\n".join(["0000000"] * 7)


def duel(
    hero_xy: tuple[int, int],
    foe_xy: tuple[int, int] = (3, 3),
    *,
    foe_facing: str = "west",
    skills: tuple[str, ...] = (BACKSTAB, AMBUSH),
    weapon: str = "dagger",
    base: str = "hero_fighter",
    foe: str = "bandit",
    foe_tags: tuple[str, ...] | None = None,
    extra: tuple[tuple[Team, tuple[int, int]], ...] = (),
    surfaces: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    """U1（英雄）在 ``hero_xy``、U2（敵人，HP 999，朝 ``foe_facing``）在 ``foe_xy``；``extra`` 依序
    是 U3、U4……（沒有反應的盜賊或英雄）。輪到 U1。"""
    allies = [hero_xy, *(xy for team, xy in extra if team is Team.ALLY)]
    enemies = [foe_xy, *(xy for team, xy in extra if team is Team.ENEMY)]
    m = make_map(SEVEN, ally=allies, enemy=enemies, surfaces=surfaces)
    hero = caster_template(list(skills), base=base, weapon=weapon)
    overrides: dict[str, object] = {"max_hp": 999}
    if foe_tags is not None:
        overrides["tags"] = list(foe_tags)
    spawns = [
        spawn(Team.ALLY, hero_xy, hero),
        spawn(Team.ENEMY, foe_xy, no_reactions(foe, **overrides)),
    ]
    for team, xy in extra:
        spawns.append(spawn(team, xy, no_reactions("bandit", max_hp=999)))
    state = give_turn(make_state(m, spawns), U1)
    state.units[U2].facing = foe_facing  # type: ignore[assignment]
    return state


def log_text(result: ResolveResult) -> str:
    lines = (describe_event(e, result.state) for e in result.events)
    return "\n".join(line for line in lines if line)


def rolled(result: ResolveResult, attacker: str = U1) -> list[AttackRolled]:
    return [e for e in of(result, AttackRolled) if e.attacker_id == attacker]


# ---------------------------------------------------------------------------
# 朝向
# ---------------------------------------------------------------------------


def test_opening_facing_faces_the_enemy_start_zone() -> None:
    state = duel((1, 3), (5, 3), foe_facing="west")
    fresh = make_state(
        make_map(SEVEN, ally=[(1, 3)], enemy=[(5, 3)]),
        [spawn(Team.ALLY, (1, 3), "hero_fighter"), spawn(Team.ENEMY, (5, 3))],
    )
    assert fresh.units[U1].facing == "east" and fresh.units[U2].facing == "west"
    vertical = make_state(
        make_map(SEVEN, ally=[(3, 0)], enemy=[(3, 6)]),
        [spawn(Team.ALLY, (3, 0), "hero_fighter"), spawn(Team.ENEMY, (3, 6))],
    )
    assert vertical.units[U1].facing == "south" and vertical.units[U2].facing == "north"
    assert state.units[U1].facing == "east"
    # 重心重合（算不出方向）時：我方朝東、敵方朝西
    assert opening_facing(Team.ALLY, [(2, 2)], [(2, 2)]) == "east"
    assert opening_facing(Team.ENEMY, [(2, 2)], [(2, 2)]) == "west"


def test_facing_between_takes_the_major_axis_and_prefers_left_right_on_ties() -> None:
    assert facing_between((3, 3), (3, 1)) == "north"
    assert facing_between((3, 3), (5, 4)) == "east"
    assert facing_between((3, 3), (2, 2)) == "west"  # 兩軸相同：左右
    assert facing_between((3, 3), (3, 3)) is None


def test_walking_faces_the_last_step() -> None:
    state = duel((1, 1), (5, 5))
    path = tuple(Pos(x=x, y=y) for x, y in ((1, 1), (2, 1), (2, 2)))
    after = resolve(state, Move(unit_id=U1, path=path)).state
    assert after.units[U1].facing == "south"


def test_dash_leap_and_charge_face_the_way_they_moved() -> None:
    dash = duel((0, 3), (4, 3), skills=("skill_tiger_charge",), weapon="one_handed_sword")
    dash.units[U1].facing = "north"
    action = UseSkill(unit_id=U1, skill_id="skill_tiger_charge", target_id=U2)
    after = resolve(with_rolls(dash, [(20, 2)]), action).state
    assert after.units[U1].xy == (3, 3) and after.units[U1].facing == "east"
    leap = duel((3, 5), (6, 0), skills=("skill_vault_leap",), weapon="one_handed_sword")
    after = resolve(
        leap, UseSkill(unit_id=U1, skill_id="skill_vault_leap", target_pos=Pos(x=3, y=3))
    ).state
    assert after.units[U1].facing == "north"
    charge = duel((0, 1), (6, 6), skills=("skill_bull_rush",), weapon="one_handed_sword")
    charge.units[U1].facing = "south"
    after = resolve(
        charge, UseSkill(unit_id=U1, skill_id="skill_bull_rush", target_pos=Pos(x=3, y=1))
    ).state
    assert after.units[U1].xy == (3, 1) and after.units[U1].facing == "east"


def test_attacking_and_casting_on_a_unit_face_the_target() -> None:
    state = duel((3, 2), (3, 3))
    state.units[U1].facing = "east"
    after = resolve(with_rolls(state, [(20, 2)]), Attack(unit_id=U1, target_id=U2)).state
    assert after.units[U1].facing == "south"
    assert after.units[U2].facing == "north"  # 被近戰攻擊後轉身面向攻擊者（3C-6a）
    skill = duel((3, 4), (3, 3), skills=("skill_pincer_strike",))
    action = UseSkill(unit_id=U1, skill_id="skill_pincer_strike", target_id=U2)
    assert resolve(with_rolls(skill, [(20, 2)]), action).state.units[U1].facing == "north"


def test_forced_moves_teleports_and_swaps_keep_facing() -> None:
    state = duel((2, 3), (3, 3))
    state.units[U2].facing = "north"
    shoved = resolve(with_rolls(state, [(20, 20)]), Shove(unit_id=U1, target_id=U2)).state
    assert shoved.units[U2].xy == (4, 3) and shoved.units[U2].facing == "north"
    blink = duel((1, 1), (5, 5), skills=("skill_blink",), weapon="dagger", base="hero_mage")
    blink.units[U1].facing = "west"
    after = resolve(
        blink, UseSkill(unit_id=U1, skill_id="skill_blink", target_pos=Pos(x=1, y=3))
    ).state
    assert after.units[U1].xy == (1, 3) and after.units[U1].facing == "west"


def test_facing_round_trips_through_json_and_clone() -> None:
    state = duel((2, 3), (3, 3), foe_facing="south")
    assert state.units[U2].clone().facing == "south"
    restored = state_from_json(state_to_json(state))
    assert restored.units[U2].facing == "south" and state_to_json(restored) == state_to_json(state)


def test_ai_battle_with_backstabs_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "assassin.json"
    argv = ["battle", "--map", "dark_forest", "--seed", "3", "--ally-build", "build_assassin"]
    assert main([*argv, "--log-json", str(log)]) == 0
    text = capsys.readouterr().out
    assert "從背後以「瞬步背刺」攻擊" in text and "背刺 +2" in text
    out = io.StringIO()
    assert cmd_replay(log, out) == 0 and "重播驗證通過" in out.getvalue()


# ---------------------------------------------------------------------------
# 背刺
# ---------------------------------------------------------------------------


def test_the_back_tile_is_opposite_the_facing() -> None:
    state = duel((2, 3), (3, 3), foe_facing="west")
    assert back_xy(state.units[U2]) == (4, 3)
    assert is_behind((4, 3), state.units[U2]) and not is_behind((3, 2), state.units[U2])


def test_a_melee_attack_from_behind_gets_hit_and_crit_bonuses() -> None:
    # 單手劍暴擊 20；背刺擴大為 19–20
    behind = duel((4, 3), foe_facing="west", weapon="one_handed_sword")
    result = resolve(with_rolls(behind, [(20, 19)]), Attack(unit_id=U1, target_id=U2))
    roll = rolled(result)[0]
    assert roll.backstab == 2 and roll.crit and roll.ambush == 0
    assert roll.total == roll.natural + roll.hit_modifier + roll.proficiency + 2
    side = duel((3, 4), foe_facing="west", weapon="one_handed_sword")
    roll = rolled(resolve(with_rolls(side, [(20, 19)]), Attack(unit_id=U1, target_id=U2)))[0]
    assert roll.backstab == 0 and roll.hit and not roll.crit
    front = duel((2, 3), foe_facing="west", weapon="one_handed_sword")
    assert (
        rolled(resolve(with_rolls(front, [(20, 19)]), Attack(unit_id=U1, target_id=U2)))[0].backstab
        == 0
    )


def test_bosses_can_be_backstabbed() -> None:
    state = duel((4, 3), foe="bandit_boss", foe_facing="west")
    assert state.units[U2].has_tag("boss")
    assert (
        rolled(resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2)))[0].backstab
        == 2
    )


def test_ranged_attacks_never_backstab() -> None:
    state = duel((4, 3), foe_facing="west", weapon="bow", base="hero_archer", skills=())
    assert (
        rolled(resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2)))[0].backstab
        == 0
    )


def test_the_preview_and_log_show_the_backstab() -> None:
    behind = duel((4, 3), foe_facing="west", weapon="one_handed_sword")
    front = duel((2, 3), foe_facing="west", weapon="one_handed_sword")
    action = Attack(unit_id=U1, target_id=U2)
    seen, plain = preview(behind, action), preview(front, action)
    assert seen.backstab == (U2,) and plain.backstab == ()
    assert seen.hit_chance is not None and plain.hit_chance is not None
    assert seen.hit_chance - plain.hit_chance == Fraction(2, 20)  # 命中 +2
    assert seen.crit_chance == Fraction(2, 20)  # 暴擊 19–20
    assert any("背刺" in note for note in seen.notes)
    result = resolve(with_rolls(behind, [(20, 12)]), action)
    text = log_text(result)
    assert "從背後攻擊" in text and "背刺 +2" in text


def test_from_behind_condition_and_modifier() -> None:
    spec = ConditionSpec(type="from_behind")
    for hero_xy, expected in (((4, 3), True), ((3, 4), False), ((2, 3), False)):
        state = duel(hero_xy, foe_facing="west")
        subject = Subject(state.units[U2], state.units[U2].xy)
        assert condition_met(state, state.units[U1], spec, subject) is expected
    rule = {
        "applies_to": {"actions": ["attack"]},
        "condition": {"type": "from_behind"},
        "change": {"damage_permille": 500},
    }
    skill = mod("skill_t_behind", rule)
    m = make_map(SEVEN, ally=[(4, 3)], enemy=[(3, 3)])
    hero = template("hero_fighter", reactions=[], skills=[skill.id], weapon="dagger")
    spawns = [spawn(Team.ALLY, (4, 3), hero), spawn(Team.ENEMY, (3, 3), no_reactions(max_hp=999))]
    state = give_turn(make_state(m, spawns, skills=[skill]), U1)
    state.units[U2].facing = "west"
    subject = Subject(state.units[U2], state.units[U2].xy)
    assert mods.damage_permille(state, state.units[U1], mods.ATTACK, subject) == 1500


# ---------------------------------------------------------------------------
# 瞬步
# ---------------------------------------------------------------------------


def backstab(state: BattleState, rolls: list[tuple[int, int]] | None = None) -> ResolveResult:
    action = UseSkill(unit_id=U1, skill_id=BACKSTAB, target_id=U2)
    return resolve(with_rolls(state, rolls or [(20, 12), (20, 12)]), action)


def test_behind_lands_on_the_back_tile_and_the_damage_is_a_backstab() -> None:
    state = duel((0, 3), foe_facing="west")
    result = backstab(state)
    moved = [e for e in of(result, UnitMoved) if e.unit_id == U1]
    assert [(e.mode, (e.to_pos.x, e.to_pos.y)) for e in moved] == [("shadowstep", (4, 3))]
    assert result.state.units[U1].facing == "west"  # 落地後面向目標
    rolls = rolled(result)
    assert rolls and all(r.backstab == 2 for r in rolls)
    text = log_text(result)
    assert "瞬步到 (4, 3)" in text and "從背後以「瞬步背刺」攻擊" in text


def test_behind_takes_the_nearest_free_tile_when_the_back_is_taken() -> None:
    # 背後 (4, 3) 被另一個敵人占住：改落在側面（上、右、下、左的順序 → 上 (3, 2)）
    state = duel((1, 1), foe_facing="west", extra=((Team.ENEMY, (4, 3)),))
    result = backstab(state)
    assert result.state.units[U1].xy == (3, 2)
    assert all(r.backstab == 0 for r in rolled(result))  # 側面不是背刺
    # 背後與兩側都被占：落在正面
    crowded = duel(
        (1, 1),
        foe_facing="west",
        extra=((Team.ENEMY, (4, 3)), (Team.ENEMY, (3, 2)), (Team.ENEMY, (3, 4))),
    )
    assert backstab(crowded).state.units[U1].xy == (2, 3)


def test_behind_cannot_be_cast_when_no_adjacent_tile_is_free() -> None:
    state = duel(
        (1, 1),
        foe_facing="west",
        extra=(
            (Team.ENEMY, (4, 3)),
            (Team.ENEMY, (3, 2)),
            (Team.ENEMY, (3, 4)),
            (Team.ENEMY, (2, 3)),
        ),
    )
    with pytest.raises(IllegalActionError, match="沒有可以瞬步落腳的空格"):
        backstab(state)
    assert not any(
        isinstance(a, UseSkill) and a.skill_id == BACKSTAB and a.target_id == U2
        for a in legal_actions(state)
    )


def test_shadowstep_needs_an_enemy_and_cannot_be_used_rooted() -> None:
    state = duel((0, 3), foe_facing="west", extra=((Team.ALLY, (0, 5)),))
    with pytest.raises(IllegalActionError, match="無法對友方使用"):
        resolve(state, UseSkill(unit_id=U1, skill_id=BACKSTAB, target_id=U3))
    rooted = state.clone()
    rooted.units[U1].statuses.append(StatusInstance("root", 2))
    with pytest.raises(IllegalActionError, match="定身"):
        backstab(rooted)


def test_shadowstep_does_not_provoke_opportunity_attacks() -> None:
    # U1 從 (1, 3) 瞬步離開，原本相鄰的 U3（有藉機攻擊規則）不會出手
    m = make_map(SEVEN, ally=[(1, 3)], enemy=[(3, 3), (0, 3)])
    hero = caster_template([BACKSTAB], base="hero_fighter", weapon="dagger")
    spawns = [
        spawn(Team.ALLY, (1, 3), hero),
        spawn(Team.ENEMY, (3, 3), no_reactions(max_hp=999)),
        spawn(Team.ENEMY, (0, 3), template("bandit", max_hp=999)),
    ]
    state = give_turn(make_state(m, spawns), U1)
    state.units[U2].facing = "west"
    result = backstab(state)
    assert result.state.units[U1].xy == (4, 3)
    assert not of(result, ReactionTriggered)
    assert all(e.attacker_id == U1 for e in of(result, AttackRolled))


def test_the_landing_tile_interacts_as_usual() -> None:
    state = duel((0, 3), foe_facing="west", surfaces=((4, 3, "fire"),))
    result = backstab(state, [(20, 12), (20, 12), (20, 12), (20, 12)])
    assert any(e.unit_id == U1 for e in of(result, SurfaceEntered))


def test_choose_lists_every_adjacent_landing_and_uses_the_chosen_one() -> None:
    state = duel((1, 1), foe_facing="west")
    choices = sorted(
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill)
        and a.skill_id == AMBUSH
        and a.target_pos is not None
        and a.target_id == U2
    )
    assert choices == [(2, 3), (3, 2), (3, 4), (4, 3)]
    action = UseSkill(unit_id=U1, skill_id=AMBUSH, target_id=U2, target_pos=Pos(x=3, y=4))
    result = resolve(with_rolls(state, [(20, 12), (20, 12)]), action)
    assert result.state.units[U1].xy == (3, 4) and result.state.units[U1].facing == "north"
    assert preview(state, action).moves[0].kind == "shadowstep"
    behind = UseSkill(unit_id=U1, skill_id=AMBUSH, target_id=U2, target_pos=Pos(x=4, y=3))
    assert all(r.backstab == 2 for r in rolled(resolve(with_rolls(state, [(20, 12)] * 2), behind)))


def test_choose_rejects_far_tiles_and_allies() -> None:
    state = duel((1, 1), foe_facing="west", extra=((Team.ALLY, (1, 4)),))
    far = UseSkill(unit_id=U1, skill_id=AMBUSH, target_id=U2, target_pos=Pos(x=5, y=3))
    with pytest.raises(IllegalActionError, match="相鄰格"):
        resolve(state, far)
    ally = UseSkill(unit_id=U1, skill_id=AMBUSH, target_id=U3, target_pos=Pos(x=1, y=5))
    with pytest.raises(IllegalActionError, match="只能以敵人為目標"):
        resolve(state, ally)


def test_the_schema_checks_landing_and_shape() -> None:
    base = library().skills[BACKSTAB].model_dump()
    with pytest.raises(ValueError, match="landing"):
        SkillDef.model_validate({**base, "effects": [{"type": "shadowstep"}, base["effects"][1]]})
    with pytest.raises(ValueError, match="第一個效果"):
        SkillDef.model_validate({**base, "effects": [base["effects"][1], base["effects"][0]]})
    with pytest.raises(ValueError, match="unit_then_tile"):
        effects = [{"type": "shadowstep", "landing": "choose"}, base["effects"][1]]
        SkillDef.model_validate({**base, "effects": effects})


def test_the_demo_skills_are_in_build_assassin() -> None:
    lib = library()
    hero = lib.builds.by_id()["build_assassin"].hero
    assert BACKSTAB in hero.skills and AMBUSH in hero.skills
    first = lib.skills[BACKSTAB].effects[0]
    assert (first.type, first.landing) == ("shadowstep", "behind")
    first = lib.skills[AMBUSH].effects[0]
    assert (first.type, first.landing) == ("shadowstep", "choose")


# ---------------------------------------------------------------------------
# 潛行偷襲
# ---------------------------------------------------------------------------


def conceal(state: BattleState) -> BattleState:
    hidden = state.clone()
    hidden.units[U1].statuses.append(StatusInstance("concealed", 2))
    return hidden


def test_attacking_while_concealed_gets_the_ambush_bonus_and_reveals_the_attacker() -> None:
    state = conceal(duel((2, 3), foe_facing="west"))
    result = resolve(with_rolls(state, [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    assert rolled(result)[0].ambush == 2
    removed = [e for e in of(result, StatusRemoved) if e.target_id == U1]
    assert [(e.status_id, e.reason) for e in removed] == [("concealed", "ambushed")]
    assert not result.state.units[U1].has_status("concealed")
    text = log_text(result)
    assert "偷襲 +2" in text and "在偷襲之後解除了" in text
    plain = resolve(with_rolls(duel((2, 3)), [(20, 10)]), Attack(unit_id=U1, target_id=U2))
    assert rolled(plain)[0].ambush == 0


def test_self_concealed_bonus_damage_needs_the_status_and_ends_it_after_the_skill() -> None:
    action = UseSkill(unit_id=U1, skill_id=AMBUSH, target_id=U2, target_pos=Pos(x=3, y=2))
    hidden = resolve(with_rolls(conceal(duel((1, 1))), [(20, 12)] * 4), action)
    seen = resolve(with_rolls(duel((1, 1)), [(20, 12)] * 4), action)
    hidden_hits = [e for e in of(hidden, DamageDealt) if e.source_id == U1]
    seen_hits = [e for e in of(seen, DamageDealt) if e.source_id == U1]
    assert len(hidden_hits) == 2 and len(seen_hits) == 1
    assert not hidden.state.units[U1].has_status("concealed")
    spec = ConditionSpec(type="self_concealed")
    state = conceal(duel((1, 1)))
    assert condition_met(state, state.units[U1], spec, Subject(None, (1, 1)))
    assert not condition_met(duel((1, 1)), duel((1, 1)).units[U1], spec, Subject(None, (1, 1)))


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_ai_values_standing_behind_and_dislikes_showing_its_back() -> None:
    lib = library()
    weights = next(p for p in lib.ai_profiles.profiles if p.id == "brute").weights
    assert weights.backstab > 0 and weights.back_exposed > 0
    state = duel((4, 3), foe_facing="west")
    hero = state.units[U1]
    at_back = _unit_position_value(state, hero, weights)
    side = hero.clone()
    side.pos = Pos(x=3, y=4)
    assert at_back - _unit_position_value(state, side, weights) == weights.backstab
    # 夾在兩個近戰敵人之間：面向最近的敵人時，背後站著另一個近戰敵人
    sandwich = duel((3, 3), (2, 3), foe_facing="east", extra=((Team.ENEMY, (4, 3)),))
    foes = [u for u in sandwich.living_units() if u.team is Team.ENEMY]
    assert _facing_terms(sandwich, sandwich.units[U1], weights, foes) == -weights.back_exposed
    alone = duel((3, 3), (2, 3), foe_facing="east")
    foes = [u for u in alone.living_units() if u.team is Team.ENEMY]
    assert _facing_terms(alone, alone.units[U1], weights, foes) == 0
