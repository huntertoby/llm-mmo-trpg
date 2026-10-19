"""Phase 3D-8c：監視射擊（``overwatch``、反應事件 ``enemy_moves_in_range``）與夾擊條件 ``flanked``
（``docs/phases/Phase3D計畫.md`` 8.3）。

監視：射程與視線、每輪 1 次（佔反應）、狀態移除時機、詢問模式、AI 會進入監視；夾擊：條件成立與
不成立、技能條件、效果條件與修正規則。
"""

from __future__ import annotations

import io
from collections.abc import Sequence
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
from trpg.content.skills import ConditionSpec
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    EndTurn,
    Move,
    ResolveResult,
    SetReactionMode,
    UseSkill,
    legal_actions,
    preview,
    resolve,
    resume,
)
from trpg.engine import modifiers as mods
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    ReactionDeclined,
    ReactionTriggered,
    StatusRemoved,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.skills.conditions import Subject, condition_met, flank_xy, is_flanked
from trpg.shared.types import Pos, Team

OVERWATCH = "skill_overwatch"
PINCER = "skill_pincer_strike"
WIDE = "\n".join(["0" * 14] * 5)


def watch_world(
    foe_xy: tuple[int, int] = (11, 2),
    *,
    watching: bool = True,
    terrain: str | None = None,
    foe_hp: int = 999,
    equipped: Sequence[str] = (OVERWATCH,),
) -> BattleState:
    """U1（弓手，射程 8，裝備監視射擊）在 (1, 2)；U2（盜賊）在 ``foe_xy``，輪到 U2。"""
    m = make_map(WIDE, terrain, ally=[(1, 2)], enemy=[foe_xy])
    archer = caster_template(list(equipped), base="hero_archer")
    spawns = [
        spawn(Team.ALLY, (1, 2), archer),
        spawn(Team.ENEMY, foe_xy, no_reactions(max_hp=foe_hp)),
    ]
    state = give_turn(make_state(m, spawns), U2)
    if watching:
        state = resolve(give_turn(state, U1), UseSkill(unit_id=U1, skill_id=OVERWATCH)).state
        state = give_turn(state, U2)
    return state


def walk(*path: tuple[int, int]) -> Move:
    return Move(unit_id=U2, path=tuple(Pos(x=x, y=y) for x, y in path))


def fired(result: ResolveResult) -> list[ReactionTriggered]:
    return [e for e in of(result, ReactionTriggered) if e.reaction == "overwatch_shot"]


def set_mode(state: BattleState, mode: str) -> BattleState:
    """U1 把監視射擊的反應模式改成 ``mode``，再回到 U2 的回合。"""
    changed = resolve(
        give_turn(state, U1),
        SetReactionMode(unit_id=U1, reaction="overwatch_shot", mode=mode),  # type: ignore[arg-type]
    ).state
    return give_turn(changed, U2)


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_the_overwatch_status_reaction_and_skill_are_defined() -> None:
    rules = library().ruleset
    assert rules.status_def("overwatch").expires == "own_turn_start"
    definition = rules.reaction_def("overwatch_shot")
    assert definition.events == ("enemy_moves_in_range",)
    assert definition.requires_status == "overwatch" and definition.effect == "basic_attack"
    skill = library().skills[OVERWATCH]
    assert [(e.type, e.status) for e in skill.effects] == [("apply_status", "overwatch")]
    assert OVERWATCH in library().builds.by_id()["build_ranged"].hero.skills


def test_a_unit_gets_the_overwatch_rule_only_when_it_has_an_overwatch_skill() -> None:
    with_skill = watch_world(watching=False).units[U1]
    assert [r.reaction for r in with_skill.reactions] == ["overwatch_shot"]
    assert with_skill.reactions[0].when.event == "enemy_moves_in_range"
    assert with_skill.reactions[0].mode == "auto"
    without = watch_world(watching=False, equipped=("skill_piercing_shot",)).units[U1]
    assert without.reactions == ()


# ---------------------------------------------------------------------------
# 觸發：射程與視線、每輪一次、佔反應、移除時機
# ---------------------------------------------------------------------------


def test_casting_overwatch_applies_the_status() -> None:
    state = watch_world()
    assert state.units[U1].has_status("overwatch")
    assert state.units[U1].reactions_used == 0


def test_an_enemy_moving_in_range_and_sight_is_shot_once_and_overwatch_ends() -> None:
    state = watch_world((11, 2))
    result = resolve(state, walk((11, 2), (10, 2), (9, 2), (8, 2), (7, 2)))
    assert [e.unit_id for e in fired(result)] == [U1]
    shots = [e for e in of(result, AttackRolled) if e.attacker_id == U1]
    assert len(shots) == 1 and shots[0].target_id == U2  # 每輪最多一次：之後的步伐不再射擊
    ended = [e for e in of(result, StatusRemoved) if e.status_id == "overwatch"]
    assert [e.reason for e in ended] == ["fired"]
    assert not result.state.units[U1].has_status("overwatch")
    assert result.state.units[U1].reactions_used == 1  # 佔本輪的反應


def test_the_shot_comes_from_the_first_step_that_ends_in_range() -> None:
    state = watch_world((12, 2))  # 與 (1, 2) 距離 11；射程 8
    result = resolve(state, walk((12, 2), (11, 2), (10, 2), (9, 2), (8, 2)))
    trigger = next(i for i, e in enumerate(result.events) if isinstance(e, ReactionTriggered))
    before = [e for e in result.events[:trigger] if isinstance(e, UnitMoved)]
    assert [e.to_pos for e in before][-1] == Pos(x=9, y=2)  # 第一次距離 ≤ 8 是 (9, 2)


def test_a_move_that_stays_out_of_range_does_not_trigger() -> None:
    state = watch_world((13, 2))
    result = resolve(state, walk((13, 2), (12, 2)))
    assert fired(result) == []
    assert result.state.units[U1].has_status("overwatch")


def test_no_line_of_sight_means_no_shot() -> None:
    walled = "\n".join(["." * 14, "." * 14, "...#..........", "." * 14, "." * 14])
    state = watch_world((9, 2), terrain=walled)
    result = resolve(state, walk((9, 2), (8, 2)))
    assert fired(result) == []
    assert result.state.units[U1].has_status("overwatch")


def test_without_the_overwatch_status_there_is_no_shot() -> None:
    state = watch_world((11, 2), watching=False)
    assert fired(resolve(state, walk((11, 2), (10, 2), (9, 2)))) == []


def test_a_used_up_reaction_blocks_the_shot() -> None:
    state = watch_world((11, 2))
    state.units[U1].reactions_used = state.ruleset.core.reactions_per_round
    result = resolve(state, walk((11, 2), (10, 2), (9, 2)))
    assert fired(result) == []
    assert result.state.units[U1].has_status("overwatch")


def test_overwatch_expires_when_the_holders_next_turn_starts() -> None:
    state = watch_world((13, 2))
    assert state.units[U1].has_status("overwatch")
    for _ in range(4):  # 把回合推進到 U1 的下一個回合
        active = state.active_unit
        assert active is not None
        state = resolve(state, EndTurn(unit_id=active)).state
        if state.active_unit == U1:
            break
    assert state.active_unit == U1
    assert not state.units[U1].has_status("overwatch")


def test_a_killed_mover_stops_walking_and_the_shot_still_ends_overwatch() -> None:
    state = with_rolls(watch_world((11, 2), foe_hp=1), [(20, 19), (8, 8)])
    result = resolve(state, walk((11, 2), (10, 2), (9, 2), (8, 2)))
    assert of(result, UnitDowned)[0].unit_id == U2
    assert not result.state.units[U1].has_status("overwatch")
    assert len(of(result, UnitMoved)) <= 2  # 倒下就不再走


# ---------------------------------------------------------------------------
# 反應模式：prompt／off
# ---------------------------------------------------------------------------


def test_prompt_mode_asks_and_declining_keeps_overwatch() -> None:
    state = set_mode(watch_world((11, 2)), "prompt")
    result = resolve(state, walk((11, 2), (10, 2), (9, 2)))
    assert result.pending is not None and result.pending.reaction == "overwatch_shot"
    assert result.pending.unit_id == U1 and result.pending.trigger_unit_id == U2
    declined = resume(result.state, Decision(unit_id=U1, accept=False))
    assert {e.reaction for e in of(declined, ReactionDeclined)} == {"overwatch_shot"}
    assert declined.state.units[U1].has_status("overwatch") and declined.pending is None


def test_prompt_mode_accepting_fires_the_shot() -> None:
    state = set_mode(watch_world((11, 2)), "prompt")
    result = resolve(state, walk((11, 2), (10, 2), (9, 2)))
    assert result.pending is not None
    accepted = resume(result.state, Decision(unit_id=U1, accept=True))
    assert len(fired(accepted)) == 1
    assert not accepted.state.units[U1].has_status("overwatch")


def test_off_mode_never_shoots() -> None:
    state = set_mode(watch_world((11, 2)), "off")
    result = resolve(state, walk((11, 2), (10, 2), (9, 2)))
    assert fired(result) == [] and result.pending is None
    assert result.state.units[U1].has_status("overwatch")


def test_the_preview_of_a_move_includes_the_overwatch_shot() -> None:
    pv = preview(watch_world((11, 2)), walk((11, 2), (10, 2), (9, 2)))
    assert any(isinstance(e, ReactionTriggered) for e in pv.max_events)


# ---------------------------------------------------------------------------
# AI 與重播
# ---------------------------------------------------------------------------


def test_ai_battle_with_overwatch_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "overwatch.json"
    argv = ["battle", "--map", "narrow_halls", "--seed", "1", "--ally-build", "build_ranged"]
    assert main([*argv, "--log-json", str(log)]) == 0
    text = capsys.readouterr().out
    assert "施放「監視射擊」" in text and "反應：監視射擊" in text
    out = io.StringIO()
    assert cmd_replay(log, out) == 0 and "重播驗證通過" in out.getvalue()


# ---------------------------------------------------------------------------
# 夾擊 flanked
# ---------------------------------------------------------------------------


def test_flank_xy_is_the_tile_opposite_the_caster() -> None:
    assert flank_xy((2, 3), (3, 3)) == (4, 3)  # 施放者在左，對面在右
    assert flank_xy((4, 3), (3, 3)) == (2, 3)
    assert flank_xy((3, 2), (3, 3)) == (3, 4)
    assert flank_xy((3, 4), (3, 3)) == (3, 2)
    assert flank_xy((1, 3), (3, 3)) == (4, 3)  # 遠程：看目標背對施放者的一格
    assert flank_xy((2, 2), (3, 3)) == (4, 3)  # 斜角：左右優先
    assert flank_xy((3, 3), (3, 3)) is None


def flank_world(
    friend_xy: tuple[int, int] | None, *, friend_team: Team = Team.ALLY, friend_alive: bool = True
) -> BattleState:
    """U1（匕首，在 (2, 3)）、U2（敵人，在 (3, 3)）；``friend_xy`` 另有一個單位 U3。"""
    heights = "\n".join(["0000000"] * 7)
    extra = [friend_xy] if friend_xy is not None else []
    ally = [(2, 3), *(extra if friend_team is Team.ALLY else [])]
    enemy = [(3, 3), *(extra if friend_team is Team.ENEMY else [])]
    m = make_map(heights, ally=ally, enemy=enemy)
    fighter = caster_template([PINCER], base="hero_fighter", weapon="dagger")
    spawns = [
        spawn(Team.ALLY, (2, 3), fighter),
        spawn(Team.ENEMY, (3, 3), no_reactions(max_hp=999)),
    ]
    if friend_xy is not None:
        spawns.append(spawn(friend_team, friend_xy, no_reactions("hero_archer", max_hp=999)))
    state = give_turn(make_state(m, spawns), U1)
    if not friend_alive and friend_xy is not None:
        state.units[U3].downed = True
    return state


def flanked(state: BattleState) -> bool:
    return is_flanked(state, state.units[U1], state.units[U2])


def test_flanked_needs_a_living_friend_on_the_opposite_side() -> None:
    assert flanked(flank_world((4, 3)))
    assert not flanked(flank_world((3, 4)))  # 友方在旁邊而不是對面
    assert not flanked(flank_world(None))
    assert not flanked(flank_world((4, 3), friend_team=Team.ENEMY))  # 對面是目標的同伴
    assert not flanked(flank_world((4, 3), friend_alive=False))


def test_the_flanked_condition_in_condition_met() -> None:
    spec = ConditionSpec(type="flanked")
    for state, expected in ((flank_world((4, 3)), True), (flank_world((3, 4)), False)):
        subject = Subject(state.units[U2], state.units[U2].xy)
        assert condition_met(state, state.units[U1], spec, subject) is expected
    on = flank_world((4, 3))
    assert not condition_met(on, on.units[U1], spec, Subject(None, (3, 3)))  # 沒有單位


def pincer_damages(state: BattleState) -> list[DamageDealt]:
    action = UseSkill(unit_id=U1, skill_id=PINCER, target_id=U2)
    result = resolve(with_rolls(state, [(20, 19)]), action)
    return [e for e in of(result, DamageDealt) if e.source_id == U1]


def test_the_pincer_skill_adds_a_hit_only_when_flanked() -> None:
    assert len(pincer_damages(flank_world((4, 3)))) == 2
    assert len(pincer_damages(flank_world((3, 4)))) == 1
    assert len(pincer_damages(flank_world(None))) == 1


def test_the_pincer_demo_is_in_build_assassin() -> None:
    lib = library()
    assert PINCER in lib.builds.by_id()["build_assassin"].hero.skills
    skill = lib.skills[PINCER]
    assert [e.condition.type if e.condition else None for e in skill.effects] == [None, "flanked"]


def flank_modifier_state(rule: dict[str, object], friend_xy: tuple[int, int] | None) -> BattleState:
    skill = mod("skill_t_flank", rule)
    heights = "\n".join(["0000000"] * 7)
    m = make_map(heights, ally=[(2, 3), *([friend_xy] if friend_xy else [])], enemy=[(3, 3)])
    hero = template("hero_fighter", reactions=[], skills=[skill.id], weapon="dagger")
    spawns = [spawn(Team.ALLY, (2, 3), hero), spawn(Team.ENEMY, (3, 3), no_reactions(max_hp=999))]
    if friend_xy:
        spawns.append(spawn(Team.ALLY, friend_xy, no_reactions("hero_archer")))
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


@pytest.mark.parametrize(
    ("change", "probe"),
    [({"hit_bonus": 3}, "hit"), ({"damage_permille": 500}, "damage")],
)
def test_flanked_works_as_a_modifier_condition(change: dict[str, int], probe: str) -> None:
    rule = {
        "applies_to": {"actions": ["attack"]},
        "condition": {"type": "flanked"},
        "change": change,
    }
    for friend_xy, expected in (((4, 3), True), ((3, 4), False), (None, False)):
        state = flank_modifier_state(rule, friend_xy)
        subject = Subject(state.units[U2], state.units[U2].xy)
        if probe == "hit":
            bonus = mods.hit_bonus(state, state.units[U1], mods.ATTACK, subject)
            assert (bonus == 3) is expected
        else:
            permille = mods.damage_permille(state, state.units[U1], mods.ATTACK, subject)
            assert (permille == 1500) is expected


def test_flanked_is_rejected_for_changes_decided_before_targeting() -> None:
    with pytest.raises(ValueError, match="self_hp_below"):
        mod(
            "skill_t_flank_bad",
            {
                "applies_to": {"all_skills": True},
                "condition": {"type": "flanked"},
                "change": {"ap_delta": -1},
            },
        )


def test_legal_actions_include_the_pincer_skill() -> None:
    state = flank_world((4, 3))
    assert any(isinstance(a, UseSkill) and a.skill_id == PINCER for a in legal_actions(state))
    assert any(isinstance(a, Attack) for a in legal_actions(state))
