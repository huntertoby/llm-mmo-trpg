"""Phase 3F-3a：複合技能「位移 → 動作」（``docs/phases/Phase3F計畫.md`` 3.1–3.3、3.5；
``docs/design/06-技能.md`` 6.23）。

schema（合法的三種位移 × 兩種動作形狀、不合法的例子）、結算（落點為原點、被擋下不結算、衝鋒與
衝撞以停下的位置為原點）、選取（``legal_actions`` 的組合、``followup_target``）、預覽與實際一致、
重播。預算見 ``tests/skillgen/test_composite_budget.py``。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.skills import SkillDef
from trpg.engine import (
    BattleState,
    ResolveResult,
    UseSkill,
    build_setup,
    legal_actions,
    preview,
    resolve,
)
from trpg.engine.actions import FollowupTarget
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EffectFizzled,
    EventBase,
    SkillFollowup,
    SkillUsed,
    UnitMoved,
)
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.state import TrapState, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId
from trpg.sim.matrix import library_with_builds
from trpg.skillgen.validate import validate_skill

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
SID = "skill_t_combo"
FLAT = "\n".join(["0000000"] * 7)
DEMO = "skill_shadow_whirl"

MOVES: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "teleport": ({"type": "teleport"}, {"type": "ground_tile", "range": 4}),
    "leap": ({"type": "leap"}, {"type": "ground_tile", "range": 4}),
    "dash": ({"type": "dash"}, {"type": "single", "range": 4}),
    "charge_through": (
        {"type": "charge_through", "dice": "1d4", "on_hit": "knock_prone"},
        {"type": "ground_tile", "range": 6},
    ),
    "shadowstep": ({"type": "shadowstep", "landing": "behind"}, {"type": "single", "range": 4}),
}
HIT: dict[str, Any] = {"type": "damage", "multiplier_permille": 1000}
CONE: tuple[str, dict[str, Any]] = ("area", {"type": "cone", "size": 2})
CROSS: tuple[str, dict[str, Any]] = ("area", {"type": "cross", "range": 0})
SINGLE: tuple[str, dict[str, Any]] = ("strike", {"type": "single", "range": 1})


def combo_data(
    move: str = "teleport",
    follow: tuple[str, dict[str, Any]] = CONE,
    effects: Sequence[dict[str, Any]] = (HIT,),
) -> dict[str, Any]:
    effect, shape = MOVES[move]
    skeleton, follow_shape = follow
    return {
        "id": SID,
        "name_zh": "測試複合",
        "tier": 1,
        "rarity": "rare",
        "skeleton": "displace",
        "category": "weapon",
        "weapon_req": "melee",
        "ap_cost": 2,
        "scaling_attr": "str",
        "shape": shape,
        "effects": [effect],
        "followup": {"skeleton": skeleton, "shape": follow_shape, "effects": list(effects)},
        "cost": {"mana": 0},
    }


def combo(
    move: str = "teleport",
    follow: tuple[str, dict[str, Any]] = CONE,
    effects: Sequence[dict[str, Any]] = (HIT,),
) -> SkillDef:
    return SkillDef.model_validate(combo_data(move, follow, effects))


def arena(
    skill: SkillDef,
    *,
    caster: tuple[int, int] = (0, 3),
    foes: Sequence[tuple[int, int]] = ((4, 3),),
    terrain: str | None = None,
) -> BattleState:
    m = make_map(FLAT, terrain, ally=[caster], enemy=list(foes))
    spawns = [spawn(Team.ALLY, caster, caster_template([skill.id], base="hero_fighter"))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(3, sides))


def use(state: BattleState, **fields: Any) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SID, **fields))


def of[E: EventBase](result: ResolveResult, kind: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, kind)]


def damaged(result: ResolveResult) -> list[str]:
    return sorted(
        {d.target_id for d in of(result, DamageDealt) if d.cause == "attack" and d.source_id == U1}
    )


def bear_trap(state: BattleState, xy: tuple[int, int]) -> None:
    state.traps = [
        TrapState(
            owner_id=U2,
            team=Team.ENEMY,
            pos=Pos(x=xy[0], y=xy[1]),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U2].attributes.items()),
        )
    ]


# ---------------------------------------------------------------------------
# schema（驗收 1）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("move", ["teleport", "leap", "dash", "charge_through", "shadowstep"])
@pytest.mark.parametrize("follow", [CONE, CROSS], ids=["cone", "cross"])
def test_legal_composites_pass_the_schema_and_the_structure_rules(
    move: str, follow: tuple[str, dict[str, Any]]
) -> None:
    skill = combo(move, follow)
    follow_skill = skill.followup_skill()
    assert follow_skill is not None and follow_skill.shape == skill.followup.shape  # type: ignore[union-attr]
    rules = [v.rule for v in validate_skill(skill, library())]
    assert [r for r in rules if not r.startswith("budget.")] == []


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"followup_effects": [{"type": "leap"}]}, "不能套娃"),
        (
            {"followup_effects": [{"type": "summon", "unit": "summon_spirit_wolf", "duration": 2}]},
            "召喚",
        ),
        (
            {
                "followup_effects": [
                    {
                        "type": "zone",
                        "duration": 2,
                        "effects": [{"type": "damage", "multiplier_permille": 500}],
                    }
                ]
            },
            "區域",
        ),
        ({"followup_effects": [HIT, HIT, HIT, HIT]}, "兩段合計最多 4 個效果"),
        ({"move_effects": [{"type": "teleport"}, HIT]}, "位移段只能有一個"),
        ({"move_effects": [HIT]}, "位移段只能有一個"),
        ({"followup_shape": {"type": "cross", "range": 2}}, "range 必須是 0"),
        (
            {"followup_shape": {"type": "chain", "range": 2, "jumps": 1, "jump_range": 2}},
            "形狀只能是",
        ),
        ({"kind": "passive"}, "只有主動技能"),
    ],
)
def test_illegal_composites_are_rejected(change: dict[str, Any], message: str) -> None:
    data = combo_data()
    if "followup_effects" in change:
        data["followup"]["effects"] = change["followup_effects"]
    if "followup_shape" in change:
        data["followup"]["shape"] = change["followup_shape"]
    if "move_effects" in change:
        data["effects"] = change["move_effects"]
    if "kind" in change:
        data.update(kind="passive", ap_cost=None, trigger={"event": "on_turn_start"})
    with pytest.raises(ValidationError) as info:
        SkillDef.model_validate(data)
    assert message in str(info.value)


def test_the_followup_is_checked_with_its_own_skeleton_and_the_composite_needs_rare() -> None:
    lib = library()
    # 動作段 strike 骨架不能用錐形：照動作段自己骨架的規則檢查
    wrong = combo(follow=("strike", {"type": "cone", "size": 2}))
    assert "followup.skeleton.shape" in [v.rule for v in validate_skill(wrong, lib)]
    common = SkillDef.model_validate({**combo_data(), "rarity": "common"})
    rules = [v.rule for v in validate_skill(common, lib)]
    assert "rarity.composite" in rules
    # 位移段骨架必須是 displace
    other = SkillDef.model_validate({**combo_data(), "skeleton": "strike"})
    assert "composite.skeleton" in [v.rule for v in validate_skill(other, lib)]


def test_the_demo_skill_is_valid_and_equipped() -> None:
    lib = library()
    skill = lib.skills[DEMO]
    assert skill.followup is not None and skill.followup.when == "after_move"
    assert validate_skill(skill, lib) == []
    charger = lib.builds.by_id()["build_charger"].hero.skills
    assert DEMO in charger and "skill_leap_slam" in charger
    assert validate_skill(lib.skills["skill_leap_slam"], lib) == []


# ---------------------------------------------------------------------------
# 結算（驗收 2）
# ---------------------------------------------------------------------------


def test_teleport_then_cone_uses_the_landing_as_the_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always_hit(monkeypatch)
    # U2 在落點前方的錐形內；U3 在落點背後；U4 在「原位置朝東的錐形」內（原點錯了才會被打到）
    skill = combo("teleport", CONE)
    state = arena(skill, foes=[(4, 3), (2, 3), (1, 3)])
    pick = FollowupTarget(direction="east")
    result = use(state, target_pos=Pos(x=3, y=3), followup_target=pick)
    assert result.state.units[U1].xy == (3, 3)
    follow = of(result, SkillFollowup)
    assert len(follow) == 1 and follow[0].origin == Pos(x=3, y=3)
    assert damaged(result) == [U2]
    # 事件順序：skill_used → 傳送 → skill_followup → 命中判定
    kinds = [type(e) for e in result.events]
    assert kinds.index(SkillUsed) < kinds.index(UnitMoved) < kinds.index(SkillFollowup)
    assert kinds.index(SkillFollowup) < kinds.index(AttackRolled)


def test_leap_then_cross_hits_around_the_landing(monkeypatch: pytest.MonkeyPatch) -> None:
    always_hit(monkeypatch)
    skill = combo("leap", CROSS)
    state = arena(skill, foes=[(3, 2), (4, 3), (5, 3)])
    result = use(state, target_pos=Pos(x=3, y=3))
    assert result.state.units[U1].xy == (3, 3)
    assert damaged(result) == [U2, U3]  # (5, 3) 不在落點的十字內


def test_a_cross_followup_target_pos_must_be_the_landing() -> None:
    skill = combo("leap", CROSS)
    state = arena(skill, foes=[(3, 2)])
    wrong = FollowupTarget(target_pos=Pos(x=2, y=2))
    with pytest.raises(IllegalActionError, match="動作段"):
        use(state, target_pos=Pos(x=3, y=3), followup_target=wrong)
    same = FollowupTarget(target_pos=Pos(x=3, y=3))
    use(state, target_pos=Pos(x=3, y=3), followup_target=same)  # 給落點也可以


def test_dash_then_cone_starts_from_the_tile_beside_the_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always_hit(monkeypatch)
    skill = combo("dash", CONE)
    state = arena(skill, foes=[(4, 3), (5, 3), (2, 4)])  # (2, 4) 在原位置朝東的錐形內
    result = use(state, target_id=U2, followup_target=FollowupTarget(direction="east"))
    assert result.state.units[U1].xy == (3, 3)
    assert of(result, SkillFollowup)[0].origin == Pos(x=3, y=3)
    assert damaged(result) == [U2, U3]


def test_a_blocked_dash_skips_the_followup(monkeypatch: pytest.MonkeyPatch) -> None:
    always_hit(monkeypatch)
    skill = combo("dash", CONE)
    state = arena(skill, foes=[(4, 3)])
    bear_trap(state, (2, 3))
    result = use(state, target_id=U2, followup_target=FollowupTarget(direction="east"))
    assert result.state.units[U1].xy == (2, 3)
    reasons = [e.reason for e in of(result, EffectFizzled)]
    assert reasons == ["dash_blocked", "followup_blocked"]
    assert not of(result, SkillFollowup) and damaged(result) == []
    texts = [describe_event(e, result.state) for e in result.events]
    assert "  位移被擋下，沒有抵達落點：第二段不結算" in texts


def test_charge_through_stopped_by_a_wall_uses_the_stop_as_the_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always_hit(monkeypatch)
    skill = combo("charge_through", CROSS)
    terrain = "\n".join(
        "".join("#" if (x, y) == (4, 3) else "." for x in range(7)) for y in range(7)
    )
    state = arena(skill, foes=[(3, 2), (6, 2)], terrain=terrain)
    result = use(state, target_pos=Pos(x=6, y=3))  # 選了 (6, 3)，牆擋在 (4, 3)
    assert result.state.units[U1].xy == (3, 3)
    assert of(result, SkillFollowup)[0].origin == Pos(x=3, y=3)
    assert damaged(result) == [U2]  # (6, 2) 是選定終點的鄰格，不是原點的


def test_a_charge_stopped_by_a_rooting_trap_skips_the_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always_hit(monkeypatch)
    skill = combo("charge_through", CROSS)
    state = arena(skill, foes=[(5, 2)])
    bear_trap(state, (2, 3))
    result = use(state, target_pos=Pos(x=5, y=3))
    assert result.state.units[U1].xy == (2, 3)
    assert [e.reason for e in of(result, EffectFizzled)] == ["followup_blocked"]
    assert damaged(result) == []


def test_shadowstep_then_single_attacks_from_behind(monkeypatch: pytest.MonkeyPatch) -> None:
    always_hit(monkeypatch)
    skill = combo("shadowstep", SINGLE)
    state = arena(skill, foes=[(3, 3)])
    state.units[U2].facing = "west"
    result = use(state, target_id=U2, followup_target=FollowupTarget(target_id=U2))
    assert result.state.units[U1].xy == (4, 3)
    rolls = [e for e in of(result, AttackRolled) if e.attacker_id == U1]
    assert len(rolls) == 1 and rolls[0].backstab > 0
    assert damaged(result) == [U2]


def test_followup_target_is_only_for_composites_and_required_for_directions() -> None:
    skill = combo("teleport", CONE)
    state = arena(skill)
    with pytest.raises(IllegalActionError, match="動作段"):
        use(state, target_pos=Pos(x=3, y=3))  # 錐形要選方向
    plain = resolve  # 一般技能不能帶 followup_target
    hero = arena(skill)
    hero.units[U1].skills = (*hero.units[U1].skills, "skill_gale_kick")
    hero.units[U1].mana = 99
    with pytest.raises(IllegalActionError, match="只有複合技能"):
        plain(
            hero,
            UseSkill(
                unit_id=U1,
                skill_id="skill_gale_kick",
                target_id=U2,
                followup_target=FollowupTarget(direction="east"),
            ),
        )


# ---------------------------------------------------------------------------
# 選取
# ---------------------------------------------------------------------------


def test_legal_actions_pair_each_landing_with_four_directions_at_most() -> None:
    skill = combo("teleport", CONE)
    state = arena(skill, foes=[(5, 5)])
    actions = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]
    landings = {(a.target_pos.x, a.target_pos.y) for a in actions if a.target_pos is not None}
    assert actions and all(a.followup_target is not None for a in actions)
    for xy in landings:
        dirs = [
            a.followup_target.direction  # type: ignore[union-attr]
            for a in actions
            if a.target_pos == Pos(x=xy[0], y=xy[1])
        ]
        assert 1 <= len(dirs) <= 4 and len(set(dirs)) == len(dirs)
    # 每一個列出的動作都能結算
    resolve(state, actions[0])


def test_single_followups_list_only_targets_in_reach_of_the_landing() -> None:
    skill = combo("dash", SINGLE)
    state = arena(skill, foes=[(4, 3), (6, 6)])
    actions = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]
    picks = {(a.target_id, a.followup_target.target_id) for a in actions if a.followup_target}
    assert (U2, U2) in picks
    assert all(f != U3 for _, f in picks)  # (6, 6) 離落點太遠


# ---------------------------------------------------------------------------
# 預覽與重播（驗收 4）
# ---------------------------------------------------------------------------


def test_the_preview_shows_both_ranges_and_matches_the_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = combo("teleport", CONE)
    state = arena(skill, foes=[(4, 3), (5, 2), (1, 3)])
    action = UseSkill(
        unit_id=U1,
        skill_id=SID,
        target_pos=Pos(x=3, y=3),
        followup_target=FollowupTarget(direction="east"),
    )
    p = preview(state, action)
    assert p.landing == (3, 3)
    assert (3, 3) in p.affected_tiles and set(p.followup_tiles) <= set(p.affected_tiles)
    assert (3, 3) not in p.followup_tiles and (4, 3) in p.followup_tiles
    assert [t.unit_id for t in p.targets] == [U2, U3]
    assert all(t.hit_chance > 0 and t.damage is not None for t in p.targets)
    always_hit(monkeypatch)
    result = resolve(state, action)
    assert damaged(result) == [t.unit_id for t in p.targets]
    used = of(result, SkillUsed)[0]
    assert {(t.x, t.y) for t in used.tiles} == set(p.affected_tiles)
    for target in p.targets:
        assert target.damage is not None
        dealt = sum(
            d.amount - d.absorbed for d in of(result, DamageDealt) if d.target_id == target.unit_id
        )
        assert target.damage.minimum <= dealt <= target.damage.maximum


def _combo_first(state: BattleState) -> Any:
    """主角第一次能用「瞬影旋斬」打到敵人時就用（其餘交給 AI）。"""
    unit = state.active
    assert unit is not None
    if (
        unit.template_id == "build_charger"
        and DEMO in unit.skills
        and unit.cooldowns.get(DEMO) is None
    ):
        for action in legal_actions(state):
            if isinstance(action, UseSkill) and action.skill_id == DEMO:
                p = preview(state, action)
                if any(not t.ally for t in p.targets):
                    return action
    return UtilityAI(library().ai_profiles)(state)


def test_a_battle_with_a_composite_cast_replays_exactly() -> None:
    setup = build_setup(
        library_with_builds(library()),
        "test_flat_6x6",
        ["build_charger", "hero_archer"],
        ["bandit", "bandit", "bandit_archer"],
        max_rounds=12,
    )
    run = run_battle(setup, 2, _combo_first)
    assert any(isinstance(e, SkillFollowup) for e in run.events)
    again = replay(setup, 2, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    composite = [a for a in log.actions if isinstance(a, UseSkill) and a.followup_target]
    assert composite
    assert state_to_json(replay(setup, 2, log.actions).state) == state_to_json(run.state)
