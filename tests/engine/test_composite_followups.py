"""Phase 3F-4a：複合技能的四種即時第二段（``docs/phases/Phase3F計畫.md`` 4.1、4.3；
``docs/design/06-技能.md`` 6.23）。

``after_action``（動作 → 位移）、``after_gather``（聚集 → 範圍打擊）、``on_kill``（擊殺 →
接下一段）、``on_hit``（命中 → 加碼段）：schema、結算（含不觸發時第二段不結算）、``pending``
選取（暫停、接受、放棄、壞選取、存讀）與一次帶完整選取的結果相同、預覽、重播、示範技能。
預算與元素連鎖規則見 ``tests/skillgen/test_composite_followup_budget.py``。
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
    template,
)
from trpg.content.battle import UnitTemplate
from trpg.content.skills import SkillDef
from trpg.engine import (
    BattleState,
    ResolveResult,
    UseSkill,
    build_setup,
    legal_actions,
    preview,
    resolve,
    resume,
)
from trpg.engine.actions import Decision, FollowupTarget
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    DamageDealt,
    EffectFizzled,
    EventBase,
    SkillFollowup,
    UnitDowned,
)
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.state import state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId
from trpg.sim.matrix import library_with_builds
from trpg.skillgen.validate import validate_skill

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
FLAT = "\n".join(["0000000"] * 7)
SLASH = "skill_retreating_slash"
GATHER = "skill_gravity_burst"
SPIRAL = "skill_death_spiral"
COMBO = "skill_armor_break_combo"
DEMOS = {
    SLASH: ("after_action", "build_assassin"),
    GATHER: ("after_gather", "build_fire"),
    SPIRAL: ("on_kill", "build_bomber"),
    COMBO: ("on_hit", "build_striker"),
}


def demo(skill_id: str) -> SkillDef:
    return library().skills[skill_id]


def arena(
    skill_id: str,
    *,
    caster: tuple[int, int] = (3, 3),
    foes: Sequence[tuple[int, int]] = ((4, 3),),
    foe_hp: int = 200,
    caster_hp: int | None = None,
    foe_template: UnitTemplate | None = None,
) -> BattleState:
    m = make_map(FLAT, None, ally=[caster], enemy=list(foes))
    extra: dict[str, Any] = {} if caster_hp is None else {"max_hp": caster_hp}
    spawns = [spawn(Team.ALLY, caster, caster_template([skill_id], base="hero_fighter", **extra))]
    spawns += [
        spawn(Team.ENEMY, xy, foe_template or no_reactions(max_hp=foe_hp, speed=0)) for xy in foes
    ]
    return give_turn(make_state(m, spawns), U1)


def always(monkeypatch: pytest.MonkeyPatch, d20: int) -> None:
    """d20 一律擲出 ``d20``（19 命中、1 失手），其他骰子取 3（不超過面數）。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(3, sides))


def use(state: BattleState, skill_id: str, **fields: Any) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def fizzles(events: Sequence[EventBase]) -> list[str]:
    return [e.reason for e in of(events, EffectFizzled) if e.effect_kind == "followup"]


def damaged(events: Sequence[EventBase]) -> list[str]:
    return sorted(
        {d.target_id for d in of(events, DamageDealt) if d.cause == "attack" and d.source_id == U1}
    )


def decide(state: BattleState, **fields: Any) -> ResolveResult:
    return resume(state, Decision(unit_id=U1, **fields))


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def kind_data(
    when: str,
    effects: Sequence[dict[str, Any]],
    shape: dict[str, Any],
    follow: tuple[str, dict[str, Any], Sequence[dict[str, Any]]],
    *,
    skeleton: str = "area",
) -> dict[str, Any]:
    follow_skeleton, follow_shape, follow_effects = follow
    return {
        "id": "skill_t_kind",
        "name_zh": "測試第二段",
        "tier": 1,
        "rarity": "rare",
        "skeleton": skeleton,
        "category": "weapon",
        "weapon_req": "melee",
        "ap_cost": 2,
        "scaling_attr": "str",
        "shape": shape,
        "effects": list(effects),
        "followup": {
            "when": when,
            "skeleton": follow_skeleton,
            "shape": follow_shape,
            "effects": list(follow_effects),
        },
        "cost": {"stamina": 1, "cooldown": 2},
    }


HIT: dict[str, Any] = {"type": "damage", "multiplier_permille": 1000}
CONE = {"type": "cone", "size": 2}
SINGLE = {"type": "single", "range": 1}
LEAP = ("displace", {"type": "ground_tile", "range": 2}, [{"type": "leap"}])
CONE_HIT = ("area", CONE, [HIT])
PULL = {"type": "pull", "distance": 1}


@pytest.mark.parametrize(
    ("label", "data"),
    [
        ("after_action：錐形 → 跳躍", kind_data("after_action", [HIT], CONE, LEAP)),
        (
            "after_action：單體 → 衝鋒",
            kind_data(
                "after_action",
                [HIT],
                SINGLE,
                ("displace", {"type": "single", "range": 3}, [{"type": "dash"}]),
                skeleton="strike",
            ),
        ),
        (
            "after_gather：環形拉 → 方陣",
            kind_data(
                "after_gather",
                [PULL],
                {"type": "ring", "radius": 2},
                ("area", {"type": "square3", "range": 0}, [HIT]),
                skeleton="displace",
            ),
        ),
        (
            "after_gather：方陣拉 → 同中心十字",
            kind_data(
                "after_gather",
                [PULL],
                {"type": "square3", "range": 3},
                ("area", {"type": "cross", "range": 3}, [HIT]),
                skeleton="displace",
            ),
        ),
        (
            "on_kill：單體 → 衝鋒再打",
            kind_data(
                "on_kill",
                [HIT],
                SINGLE,
                ("strike", {"type": "single", "range": 3}, [{"type": "dash"}, HIT]),
                skeleton="strike",
            ),
        ),
        ("on_kill：單體 → 跳躍", kind_data("on_kill", [HIT], SINGLE, LEAP, skeleton="strike")),
        ("on_hit：單體 → 錐形", kind_data("on_hit", [HIT], SINGLE, CONE_HIT, skeleton="strike")),
    ],
)
def test_legal_kinds_pass_the_schema_and_the_structure_rules(
    label: str, data: dict[str, Any]
) -> None:
    skill = SkillDef.model_validate(data)
    rules = [v.rule for v in validate_skill(skill, library())]
    assert all(r.startswith("budget.") for r in rules), (label, rules)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            kind_data(
                "after_action", [{"type": "leap"}], {"type": "ground_tile", "range": 2}, LEAP
            ),
            "第一段不能有位移",
        ),
        (kind_data("after_action", [HIT], CONE, CONE_HIT), "第二段（位移）只能有一個"),
        (
            kind_data("after_gather", [HIT], {"type": "ring", "radius": 2}, CONE_HIT),
            "聚集段只能有一個拉扯原語",
        ),
        (
            kind_data(
                "after_gather", [PULL], SINGLE, ("area", {"type": "cross", "range": 0}, [HIT])
            ),
            "聚集段的形狀只能是",
        ),
        (
            kind_data(
                "after_gather",
                [PULL],
                {"type": "square3", "range": 3},
                ("area", {"type": "cross", "range": 0}, [HIT]),
            ),
            "range 必須與聚集段相同",
        ),
        (
            kind_data(
                "on_kill",
                [{"type": "apply_status", "status": "slow"}],
                SINGLE,
                CONE_HIT,
                skeleton="control",
            ),
            "第一段必須有傷害效果",
        ),
        (kind_data("on_hit", [HIT], SINGLE, LEAP), "形狀只能是"),
        (
            kind_data(
                "on_hit",
                [HIT],
                SINGLE,
                ("area", {"type": "cone", "size": 2}, [{"type": "summon", "unit": "x"}]),
            ),
            "不能套娃",
        ),
        (
            kind_data("on_kill", [HIT, HIT, HIT], SINGLE, ("strike", SINGLE, [HIT, HIT])),
            "兩段合計最多 4 個效果",
        ),
    ],
)
def test_illegal_kinds_are_rejected(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(data)


@pytest.mark.parametrize("skill_id", sorted(DEMOS))
def test_each_demo_skill_is_valid_and_equipped(skill_id: str) -> None:
    when, owner = DEMOS[skill_id]
    skill = demo(skill_id)
    assert skill.followup is not None and skill.followup.when == when
    assert validate_skill(skill, library()) == []
    lib = library_with_builds(library())
    assert skill_id in lib.unit(owner).skills


# ---------------------------------------------------------------------------
# after_action：動作 → 位移（打帶跑）
# ---------------------------------------------------------------------------


def test_after_action_pauses_for_the_landing_after_the_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = arena(SLASH, foes=((4, 3), (5, 4)))
    first = use(state, SLASH, direction="east")
    assert first.pending is not None and first.pending.kind == "followup"
    assert first.pending.skill_id == SLASH and first.pending.unit_id == U1
    assert damaged(first.events) == [U2, U3]  # 錐形斬擊先結算
    assert first.state.units[U1].xy == (3, 3)  # 還沒跳
    assert legal_actions(first.state) == []
    again = state_from_json(state_to_json(first.state))  # 暫停的狀態可以存讀
    assert again.pending == first.state.pending
    second = decide(again, accept=True, followup_target=FollowupTarget(target_pos=Pos(x=1, y=3)))
    assert second.pending is None
    follow = of(second.events, SkillFollowup)
    assert [(f.when, (f.origin.x, f.origin.y)) for f in follow] == [("after_action", (3, 3))]
    assert second.state.units[U1].xy == (1, 3)
    assert not of(second.events, DamageDealt)  # 只回傳暫停之後的事件
    # 一次帶完整選取（AI、重播）的結果逐位元相同
    full = use(
        state, SLASH, direction="east", followup_target=FollowupTarget(target_pos=Pos(x=1, y=3))
    )
    assert state_to_json(full.state) == state_to_json(second.state)
    assert [type(e) for e in full.events] == [type(e) for e in [*first.events, *second.events]]


def test_after_action_bad_choice_keeps_the_pause_and_decline_skips_the_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    paused = use(arena(SLASH), SLASH, direction="east").state
    with pytest.raises(IllegalActionError, match="第二段"):
        decide(paused, accept=True, followup_target=FollowupTarget(target_pos=Pos(x=6, y=6)))
    with pytest.raises(IllegalActionError, match="必須指定第二段的目標"):
        decide(paused, accept=True)
    assert paused.pending is not None  # 暫停不變
    declined = decide(paused, accept=False)
    assert declined.pending is None
    assert fizzles(declined.events) == ["followup_declined"]
    assert declined.state.units[U1].xy == (3, 3)
    assert (
        declined.state.units[U1].stamina < arena(SLASH).units[U1].stamina
    )  # 代價照付（武器技花耐力）
    assert any("放棄了第二段" in (describe_event(e, declined.state) or "") for e in declined.events)


def test_after_action_does_not_happen_when_the_caster_falls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    duelist = template("sim_duelist", reactions=[])  # 只有「還擊」（不格擋，反應不會被用掉）
    state = arena(SLASH, caster_hp=1, foe_template=duelist)  # 還擊打倒施放者
    result = use(state, SLASH, direction="east")
    assert result.pending is None
    assert any(e.unit_id == U1 for e in of(result.events, UnitDowned))
    assert fizzles(result.events) == ["followup_caster_down"]
    lines = [describe_event(e, result.state) or "" for e in result.events]
    assert "  施放者倒下了：第二段不結算" in lines
    assert not of(result.events, SkillFollowup)


# ---------------------------------------------------------------------------
# after_gather：聚集 → 範圍打擊
# ---------------------------------------------------------------------------


def test_after_gather_pulls_then_bursts_around_the_gather_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = arena(GATHER, foes=((5, 3), (3, 1), (6, 6)))
    result = use(state, GATHER)
    assert result.pending is None
    assert result.state.units[U2].xy == (4, 3) and result.state.units[U3].xy == (3, 2)
    assert result.state.units[U4].xy == (6, 6)  # 環形外
    follow = of(result.events, SkillFollowup)
    assert [(f.when, (f.origin.x, f.origin.y)) for f in follow] == [("after_gather", (3, 3))]
    assert damaged(result.events) == [U2, U3]
    lines = [describe_event(e, result.state) or "" for e in result.events]
    assert any("以聚集點" in line for line in lines)
    with pytest.raises(IllegalActionError, match="不能指定 followup_target"):
        use(state, GATHER, followup_target=FollowupTarget(direction="east"))


def test_after_gather_preview_shows_the_burst() -> None:
    state = arena(GATHER, foes=((5, 3),))
    p = preview(state, UseSkill(unit_id=U1, skill_id=GATHER))
    assert p.landing == (3, 3)
    assert set(p.followup_tiles) == {(x, y) for x in (2, 3, 4) for y in (2, 3, 4)}
    assert U2 in p.affected_units
    (action,) = [
        a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == GATHER
    ]
    assert action.followup_target is None


# ---------------------------------------------------------------------------
# on_kill：擊殺 → 接下一段
# ---------------------------------------------------------------------------


def test_on_kill_asks_for_the_next_target_only_after_a_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = arena(SPIRAL, foes=((4, 3), (3, 6)), foe_hp=1)
    first = use(state, SPIRAL, target_id=U2)
    assert any(e.unit_id == U2 for e in of(first.events, UnitDowned))
    assert first.pending is not None and first.pending.kind == "followup"
    second = decide(first.state, accept=True, followup_target=FollowupTarget(target_id=U3))
    assert second.state.units[U1].xy == (3, 5)  # 衝到下一個敵人身邊
    assert [f.when for f in of(second.events, SkillFollowup)] == ["on_kill"]
    assert damaged(second.events) == [U3]
    full = use(state, SPIRAL, target_id=U2, followup_target=FollowupTarget(target_id=U3))
    assert state_to_json(full.state) == state_to_json(second.state)


def test_on_kill_does_nothing_without_a_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    state = arena(SPIRAL, foes=((4, 3), (3, 6)))
    result = use(state, SPIRAL, target_id=U2, followup_target=FollowupTarget(target_id=U3))
    assert result.pending is None
    assert fizzles(result.events) == ["followup_not_triggered"]
    assert result.state.units[U1].xy == (3, 3)
    assert damaged(result.events) == [U2]
    lines = [describe_event(e, result.state) or "" for e in result.events]
    assert any("沒有達成條件" in line for line in lines)


def test_on_kill_without_a_next_target_does_not_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    result = use(arena(SPIRAL, foes=((4, 3),), foe_hp=1), SPIRAL, target_id=U2)
    assert result.pending is None
    assert fizzles(result.events) == ["followup_no_target"]


# ---------------------------------------------------------------------------
# on_hit：命中 → 加碼段
# ---------------------------------------------------------------------------


def test_on_hit_follows_up_toward_the_same_target(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    state = arena(COMBO, caster=(2, 3), foes=((3, 3), (4, 3), (5, 3)))
    result = use(state, COMBO, target_id=U2)
    assert result.pending is None
    follow = of(result.events, SkillFollowup)
    assert [f.when for f in follow] == ["on_hit"]
    assert {(t.x, t.y) for t in follow[0].tiles} == {(3, 3), (4, 2), (4, 3), (4, 4)}
    hits = [d.target_id for d in of(result.events, DamageDealt) if d.source_id == U1]
    assert hits.count(U2) == 2 and U3 in hits and U4 not in hits
    with pytest.raises(IllegalActionError, match="不能指定 followup_target"):
        use(state, COMBO, target_id=U2, followup_target=FollowupTarget(direction="east"))


def test_on_hit_does_nothing_on_a_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 1)
    state = arena(COMBO, caster=(2, 3), foes=((3, 3), (4, 3)))
    result = use(state, COMBO, target_id=U2)
    assert fizzles(result.events) == ["followup_not_triggered"]
    assert not of(result.events, SkillFollowup)
    assert not damaged(result.events)


def test_on_hit_preview_shows_the_shockwave() -> None:
    state = arena(COMBO, caster=(2, 3), foes=((3, 3), (4, 3)))
    p = preview(state, UseSkill(unit_id=U1, skill_id=COMBO, target_id=U2))
    assert p.landing == (2, 3)
    assert set(p.followup_tiles) == {(3, 3), (4, 2), (4, 3), (4, 4)}
    assert U3 in p.affected_units


# ---------------------------------------------------------------------------
# legal_actions、AI、重播
# ---------------------------------------------------------------------------


def test_choice_kinds_list_one_bare_action_per_first_selection() -> None:
    state = arena(SLASH, foes=((4, 3),))
    actions = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SLASH]
    assert [a.direction for a in actions] == ["north", "east", "south", "west"]
    assert all(a.followup_target is None for a in actions)


def _slash_first(state: BattleState) -> Any:
    """主角第一次能用「回馬斬」打到敵人時用（不帶第二段，結算時暫停），其餘交給 AI。"""
    unit = state.active
    assert unit is not None
    if unit.template_id == "build_assassin" and unit.cooldowns.get(SLASH) is None:
        for action in legal_actions(state):
            if (
                isinstance(action, UseSkill)
                and action.skill_id == SLASH
                and any(not t.ally for t in preview(state, action).targets)
            ):
                return action
    return UtilityAI(library().ai_profiles)(state)


def test_a_battle_with_a_paused_followup_replays_exactly() -> None:
    setup = build_setup(
        library_with_builds(library()),
        "test_flat_6x6",
        ["build_assassin"],
        ["bandit", "bandit"],
        max_rounds=10,
    )
    run = run_battle(setup, 3, _slash_first)
    decisions = [a for a in run.actions if isinstance(a, Decision) and a.followup_target]
    assert decisions, "回馬斬應該暫停並由預設決策選落點"
    assert any(isinstance(e, SkillFollowup) and e.when == "after_action" for e in run.events)
    again = replay(setup, 3, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    assert state_to_json(replay(setup, 3, log.actions).state) == state_to_json(run.state)
