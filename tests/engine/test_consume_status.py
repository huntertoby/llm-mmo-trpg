"""``consume_status`` 原語（Phase 3C-3b 5.2）：消耗目標身上的狀態，換取 ``then`` 的效果。"""

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
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import BattleState, UseSkill, preview, resolve
from trpg.engine.events import (
    DamageDealt,
    EffectFizzled,
    EventBase,
    StacksChanged,
    StatusApplied,
    StatusRemoved,
)
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId

U3, U4 = UnitId("unit_0003"), UnitId("unit_0004")
CASTER_XY, TARGET_XY, NEIGHBOR_XY, FAR_XY, ALLY_XY = (2, 3), (4, 3), (5, 3), (4, 6), (3, 3)

_FIRE_1D4 = {"type": "damage", "dice": "1d4", "element": "fire"}


def consume(
    then: Sequence[dict[str, Any]] = (_FIRE_1D4,),
    *,
    status: str = "burning",
    scale: str | None = None,
    splash: int | None = None,
    stack: str | None = None,
    skill_id: str = "skill_t_consume",
) -> SkillDef:
    effect: dict[str, Any] = {"type": "consume_status", "status": status, "then": list(then)}
    effect |= {k: v for k, v in (("scale", scale), ("splash", splash), ("stack", stack)) if v}
    skill = make_skill(skill_id, {"type": "single", "range": 5}, [effect])
    return skill.model_copy(update={"skeleton": "consume_status"})


def scene(skill: SkillDef) -> BattleState:
    """U1 法師（施放者）、U2 目標、U3 與 U2 相鄰的敵人、U4 遠處的敵人；U5 站在 U2 旁的隊友。"""
    m = make_map(
        FLAT7,
        ally=[CASTER_XY, ALLY_XY],
        enemy=[TARGET_XY, NEIGHBOR_XY, FAR_XY],
    )
    foe = no_reactions(max_hp=999)
    state = make_state(
        m,
        [
            spawn(Team.ALLY, CASTER_XY, caster_template([skill])),
            spawn(Team.ENEMY, TARGET_XY, foe),
            spawn(Team.ENEMY, NEIGHBOR_XY, foe),
            spawn(Team.ENEMY, FAR_XY, foe),
            spawn(Team.ALLY, ALLY_XY, no_reactions(max_hp=999)),
        ],
        skills=[skill],
    )
    return give_turn(state, U1)


def ignite(state: BattleState, unit: str, remaining: int | None = 2) -> None:
    state.units[UnitId(unit)].statuses = [StatusInstance("burning", remaining, U1)]


def cast(state: BattleState, skill: SkillDef) -> Any:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2))


def damage_to(events: Sequence[EventBase]) -> dict[str, DamageDealt]:
    return {e.target_id: e for e in events if isinstance(e, DamageDealt) and e.cause == "attack"}


def test_it_removes_the_status_then_resolves_the_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume()
    state = scene(skill)
    ignite(state, U2)
    result = cast(state, skill)
    assert not result.state.units[U2].has_status("burning")
    removed = [e for e in result.events if isinstance(e, StatusRemoved)]
    assert [(e.target_id, e.status_id, e.reason) for e in removed] == [(U2, "burning", "consumed")]
    hit = damage_to(result.events)
    assert list(hit) == [U2] and hit[U2].element.value == "fire"
    assert removed[0].seq < hit[U2].seq  # 先移除狀態，再結算效果
    assert not [e for e in result.events if isinstance(e, EffectFizzled)]


def test_without_the_status_nothing_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume()
    result = cast(scene(skill), skill)
    assert damage_to(result.events) == {}
    assert [e for e in result.events if isinstance(e, StatusRemoved)] == []
    (fizzled,) = [e for e in result.events if isinstance(e, EffectFizzled)]
    assert (fizzled.effect_kind, fizzled.reason) == ("consume_status", "no_status")


def test_a_different_status_is_not_consumed(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume()
    state = scene(skill)
    state.units[U2].statuses = [StatusInstance("slow", 2, U1)]
    result = cast(state, skill)
    assert damage_to(result.events) == {} and result.state.units[U2].has_status("slow")


def test_scale_remaining_rounds_multiplies_the_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume(scale="remaining_rounds")
    counts = {}
    for remaining in (1, 2, 3):
        state = scene(skill)
        ignite(state, U2, remaining)
        counts[remaining] = len(damage_to(cast(state, skill).events)[U2].rolls)
    assert counts == {1: 1, 2: 2, 3: 3}


def test_scale_is_capped_and_a_permanent_status_counts_as_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    skill = consume(scale="remaining_rounds")
    cap = scene(skill).ruleset.core.consume_status_max_scale
    state = scene(skill)
    ignite(state, U2, cap + 4)
    assert len(damage_to(cast(state, skill).events)[U2].rolls) == cap
    state = scene(skill)
    ignite(state, U2, None)
    assert len(damage_to(cast(state, skill).events)[U2].rolls) == 1


def test_scale_stacks_consumes_the_targets_stacks(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume(scale="stacks", stack="sunder")
    state = scene(skill)
    ignite(state, U2, 1)
    state.units[U2].stacks = {"sunder": 2}
    result = cast(state, skill)
    assert len(damage_to(result.events)[U2].rolls) == 2
    changes = [e for e in result.events if isinstance(e, StacksChanged)]
    assert [(e.unit_id, e.stack_id, e.before, e.after, e.reason) for e in changes] == [
        (U2, "sunder", 2, 0, "consumed")
    ]
    assert "sunder" not in result.state.units[U2].stacks


def test_scale_stacks_without_stacks_is_one_and_without_the_status_keeps_the_stacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    skill = consume(scale="stacks", stack="sunder")
    state = scene(skill)
    ignite(state, U2, 1)
    assert len(damage_to(cast(state, skill).events)[U2].rolls) == 1
    state = scene(skill)  # 沒有燃燒：整個原語不結算，層數保留
    state.units[U2].stacks = {"sunder": 2}
    result = cast(state, skill)
    assert damage_to(result.events) == {} and result.state.units[U2].stacks == {"sunder": 2}


def test_splash_also_hits_adjacent_enemies_but_not_allies_or_far_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    skill = consume(splash=1)
    state = scene(skill)
    ignite(state, U2)
    result = cast(state, skill)
    assert sorted(damage_to(result.events)) == [U2, U3]  # U4 太遠；隊友 U5 緊鄰 U2 但不受傷
    assert result.state.units[U3].hp < 999 and not result.state.units[U3].statuses


def test_only_the_consumed_target_is_hit_without_splash(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume()
    state = scene(skill)
    ignite(state, U2)
    assert sorted(damage_to(cast(state, skill).events)) == [U2]


def test_then_can_apply_a_status_after_consuming(monkeypatch: pytest.MonkeyPatch) -> None:
    """把燃燒換成流血：先移除燃燒，再施加流血（流血不需要抵抗）。"""
    always(monkeypatch)
    skill = consume([{"type": "apply_status", "status": "bleed", "duration": 2}])
    state = scene(skill)
    ignite(state, U2)
    result = cast(state, skill)
    assert not result.state.units[U2].has_status("burning")
    assert result.state.units[U2].has_status("bleed")
    assert [e.status_id for e in result.events if isinstance(e, StatusApplied)] == ["bleed"]


def test_the_preview_does_not_change_the_state(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = consume(scale="remaining_rounds", splash=1)
    state = scene(skill)
    ignite(state, U2)
    p = preview(state, UseSkill(unit_id=U1, skill_id=skill.id, target_id=U2))
    assert state.units[U2].has_status("burning")
    assert any(isinstance(e, DamageDealt) for e in p.max_events)


def test_the_same_inputs_give_the_same_outcome() -> None:
    skill = consume(scale="remaining_rounds", splash=1)

    def run() -> list[str]:
        state = scene(skill)
        ignite(state, U2)
        return [e.model_dump_json() for e in cast(state, skill).events]

    assert run() == run()


# ---------------------------------------------------------------------------
# 結構與跨檔案驗證
# ---------------------------------------------------------------------------


def _skill_with(effect: dict[str, Any]) -> dict[str, Any]:
    base = consume().model_dump(mode="json")
    base["effects"] = [effect]
    return base


def _consume_effect(**extra: Any) -> dict[str, Any]:
    return {"type": "consume_status", "status": "burning", "then": [_FIRE_1D4]} | extra


@pytest.mark.parametrize(
    "effect",
    [
        _consume_effect(then=[]),
        _consume_effect(then=[_FIRE_1D4, _FIRE_1D4, _FIRE_1D4]),
        _consume_effect(then=[{"type": "push", "distance": 1}]),
        _consume_effect(then=[{**_FIRE_1D4, "affects": "allies"}]),
        _consume_effect(scale="stacks"),
        _consume_effect(stack="sunder"),
        _consume_effect(splash=2),
        {"type": "damage", "dice": "1d4", "element": "fire", "splash": 1},
        {"type": "damage", "dice": "1d4", "element": "fire", "scale": "stacks"},
    ],
)
def test_structural_errors_are_rejected(effect: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SkillDef.model_validate(_skill_with(effect))


def _problems(effect: dict[str, Any]) -> list[str]:
    rules = library().ruleset
    skill = SkillDef.model_validate(_skill_with(effect))
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
        stacks={s.id: s for s in rules.stacks.stacks},
    )


def test_cross_file_references_are_checked() -> None:
    assert _problems(_consume_effect()) == []
    assert any("未知的狀態" in p for p in _problems(_consume_effect(status="nope")))
    then_bad = _consume_effect(then=[{"type": "apply_status", "status": "nope"}])
    assert any("then" in p and "未知的狀態" in p for p in _problems(then_bad))
    assert any("未知的層數" in p for p in _problems(_consume_effect(scale="stacks", stack="nope")))
    # static_charge 是施放者型層數，scale: stacks 需要目標型
    owner_self = _consume_effect(scale="stacks", stack="static_charge")
    assert any("目標型層數" in p for p in _problems(owner_self))
    assert _problems(_consume_effect(scale="stacks", stack="sunder")) == []
