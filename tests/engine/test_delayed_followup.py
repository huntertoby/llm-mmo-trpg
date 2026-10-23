"""Phase 3F-4b：延遲段（``docs/phases/Phase3F計畫.md`` 4.2、4.3；設計 6.23 #5）。

``followup.when: delayed``：第一段照常結算，施放者帶上 ``charging``；``release: next_turn`` 在施放者
下回合開始時、``release: attacked`` 在下回合開始前被敵人攻擊時以施放者 **當下** 的位置為中心
結算第二段。倒下、暈眩、冰凍時取消；序列化、重播、預覽、環境預告與視圖都看得到倒數與預計範圍。
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
from trpg.content.skills import CHARGING, SkillDef
from trpg.engine import (
    BattleState,
    ResolveResult,
    UseSkill,
    build_setup,
    preview,
    project_for,
    resolve,
    telegraph,
)
from trpg.engine.actions import Attack, EndTurn, Move
from trpg.engine.context import Ctx
from trpg.engine.delayed import DELAYED_RELEASE
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, DamageEffect
from trpg.engine.events import (
    DamageDealt,
    EffectFizzled,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    SkillFollowup,
)
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.skill_triggers import _DELAYED_RELEASE
from trpg.engine.state import StatusInstance, state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId
from trpg.sim.matrix import library_with_builds
from trpg.skillgen.validate import validate_skill

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
FLAT = "\n".join(["0000000"] * 7)
CLEAVE = "skill_charged_cleave"
RIPOSTE = "skill_parry_riposte"


def arena(
    skill_id: str,
    *,
    caster: tuple[int, int] = (3, 3),
    foes: Sequence[tuple[int, int]] = ((4, 3),),
    caster_hp: int | None = None,
) -> BattleState:
    m = make_map(FLAT, None, ally=[caster], enemy=list(foes))
    extra: dict[str, Any] = {} if caster_hp is None else {"max_hp": caster_hp}
    spawns = [spawn(Team.ALLY, caster, caster_template([skill_id], base="hero_fighter", **extra))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200, speed=3)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def always(monkeypatch: pytest.MonkeyPatch, d20: int) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(3, sides))


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def cast(state: BattleState, skill_id: str) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id))


def until_turn_of(state: BattleState, uid: UnitId) -> tuple[BattleState, list[EventBase]]:
    """每個行動者直接結束回合，直到輪到 ``uid``（回傳那時的狀態與途中的事件）。"""
    events: list[EventBase] = []
    state = resolve(state, EndTurn(unit_id=U1)).state if state.active_unit == U1 else state
    for _ in range(20):
        if state.active_unit == uid or state.ended:
            break
        assert state.active_unit is not None
        result = resolve(state, EndTurn(unit_id=state.active_unit))
        events += result.events
        state = result.state
    return state, events


def hurt_by_caster(events: Sequence[EventBase]) -> list[str]:
    return sorted(
        {d.target_id for d in of(events, DamageDealt) if d.source_id == U1 and d.cause == "attack"}
    )


# ---------------------------------------------------------------------------
# schema 與示範技能
# ---------------------------------------------------------------------------


def delayed_data(**follow: Any) -> dict[str, Any]:
    data = {
        "when": "delayed",
        "release": "next_turn",
        "skeleton": "area",
        "shape": {"type": "square3", "range": 0},
        "effects": [{"type": "damage", "multiplier_permille": 1000}],
    }
    data.update(follow)
    return {
        "id": "skill_t_delayed",
        "name_zh": "測試延遲段",
        "tier": 1,
        "rarity": "rare",
        "skeleton": "aura",
        "category": "weapon",
        "weapon_req": "melee",
        "ap_cost": 2,
        "scaling_attr": "str",
        "shape": {"type": "self"},
        "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
        "followup": data,
        "cost": {"mana": 0, "cooldown": 2},
    }


@pytest.mark.parametrize(
    ("follow", "message"),
    [
        ({"release": None}, "延遲段必須指定 release"),
        ({"shape": {"type": "cone", "size": 2}}, "形狀只能是"),
        ({"shape": {"type": "cross", "range": 2}}, "range 必須是 0"),
        ({"effects": [{"type": "leap"}]}, "不能套娃"),
        ({"when": "on_hit", "release": "attacked"}, "只有延遲段"),
    ],
)
def test_illegal_delayed_segments_are_rejected(follow: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(delayed_data(**follow))


@pytest.mark.parametrize("release", ["next_turn", "attacked"])
@pytest.mark.parametrize("shape", [{"type": "cross", "range": 0}, {"type": "ring", "radius": 1}])
def test_legal_delayed_segments_pass(release: str, shape: dict[str, Any]) -> None:
    skill = SkillDef.model_validate(delayed_data(release=release, shape=shape))
    rules = [v.rule for v in validate_skill(skill, library())]
    assert all(r.startswith("budget.") for r in rules), rules


@pytest.mark.parametrize(
    ("skill_id", "release", "owner"),
    [(CLEAVE, "next_turn", "build_push"), (RIPOSTE, "attacked", "build_tank")],
)
def test_the_demo_skills_are_valid_and_equipped(skill_id: str, release: str, owner: str) -> None:
    skill = library().skills[skill_id]
    assert skill.followup is not None and skill.followup.release == release
    assert validate_skill(skill, library()) == []
    assert skill_id in library_with_builds(library()).unit(owner).skills


def test_the_release_constant_matches_the_trigger_module() -> None:
    assert DELAYED_RELEASE == _DELAYED_RELEASE


# ---------------------------------------------------------------------------
# 下回合開始時釋放
# ---------------------------------------------------------------------------


def test_casting_charges_and_the_slash_lands_when_the_next_turn_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = arena(CLEAVE, foes=((4, 3), (3, 2), (6, 6)))
    result = cast(state, CLEAVE)
    assert hurt_by_caster(result.events) == []  # 第一段只有護盾
    charged = of(result.events, FollowupCharged)
    assert [(c.release, len(c.tiles)) for c in charged] == [("next_turn", 9)]
    status = result.state.units[U1].get_status(CHARGING)
    assert status is not None and status.skill_id == CLEAVE and status.remaining == 1
    state, events = until_turn_of(result.state, U1)
    follow = of(events, SkillFollowup)
    assert [(f.when, f.origin) for f in follow] == [("delayed", Pos(x=3, y=3))]
    assert hurt_by_caster(events) == [U2, U3]  # (6, 6) 在方陣外
    assert not state.units[U1].has_status(CHARGING)
    texts = [describe_event(e, state) for e in [*charged, *follow]]
    assert "開始蓄力「蓄力斬」：下回合開始時釋放" in (texts[0] or "")
    assert "釋放蓄力" in (texts[1] or "")


def test_the_release_is_centred_where_the_caster_stands_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = arena(CLEAVE, foes=((4, 3), (1, 5)))
    result = cast(state, CLEAVE)
    moved = resolve(
        result.state, Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=2, y=3), Pos(x=2, y=4)))
    )
    state, events = until_turn_of(moved.state, U1)
    assert [f.origin for f in of(events, SkillFollowup)] == [Pos(x=2, y=4)]
    assert hurt_by_caster(events) == [U3]


def test_a_release_with_nobody_around_still_resolves_without_hits() -> None:
    state = arena(CLEAVE, foes=((6, 6),))
    state, events = until_turn_of(cast(state, CLEAVE).state, U1)
    assert len(of(events, SkillFollowup)) == 1
    assert hurt_by_caster(events) == []


# ---------------------------------------------------------------------------
# 被攻擊時釋放
# ---------------------------------------------------------------------------


def test_being_attacked_releases_the_riposte_after_the_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = arena(RIPOSTE, foes=((4, 3), (3, 4), (4, 4)))
    result = cast(state, RIPOSTE)
    assert [c.release for c in of(result.events, FollowupCharged)] == ["attacked"]
    state = resolve(result.state, EndTurn(unit_id=U1)).state
    while state.active_unit != U2:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    hit = resolve(state, Attack(unit_id=U2, target_id=U1))
    kinds = [type(e).__name__ for e in hit.events]
    attack_at = kinds.index("AttackRolled")
    follow_at = kinds.index("SkillFollowup")
    assert attack_at < follow_at  # 那次攻擊結算完才反擊
    assert hurt_by_caster(hit.events) == [U2, U3]  # 十字：(4, 3)、(3, 4)；(4, 4) 在對角
    assert not hit.state.units[U1].has_status(CHARGING)


def test_only_one_riposte_per_charge(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    state = arena(RIPOSTE, foes=((4, 3), (3, 4)))
    state = resolve(cast(state, RIPOSTE).state, EndTurn(unit_id=U1)).state
    follows = 0
    for _ in range(6):
        actor = state.active_unit
        if actor is None or actor == U1:
            break
        result = resolve(state, Attack(unit_id=actor, target_id=U1))
        follows += len(of(result.events, SkillFollowup))
        state = resolve(result.state, EndTurn(unit_id=actor)).state
    assert follows == 1


def test_an_unattacked_riposte_expires_when_the_next_turn_starts() -> None:
    state = arena(RIPOSTE, foes=((6, 6),))
    state, events = until_turn_of(cast(state, RIPOSTE).state, U1)
    assert [e.reason for e in of(events, FollowupCancelled)] == ["expired"]
    assert of(events, SkillFollowup) == []
    assert not state.units[U1].has_status(CHARGING)


# ---------------------------------------------------------------------------
# 取消：倒下、暈眩、冰凍；換一招蓄力
# ---------------------------------------------------------------------------


def _charged(skill_id: str = CLEAVE) -> BattleState:
    return cast(arena(skill_id, foes=((4, 3),)), skill_id).state


@pytest.mark.parametrize(
    ("effect", "reason"),
    [
        (ApplyStatusEffect(target_id=U1, status_id="stun"), "controlled"),
        (ApplyStatusEffect(target_id=U1, status_id="frozen"), "controlled"),
        (DamageEffect(target_id=U1, cause="status", mode="lethal"), "downed"),
    ],
)
def test_downed_stunned_or_frozen_casters_lose_the_charge(effect: Any, reason: str) -> None:
    state = _charged()
    ctx = Ctx(state)
    execute(ctx, [effect])
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == [reason]
    assert not state.units[U1].has_status(CHARGING)
    state, events = until_turn_of(state, U1) if state.units[U1].alive else (state, [])
    assert of(events, SkillFollowup) == []


def test_other_statuses_keep_the_charge() -> None:
    state = _charged()
    ctx = Ctx(state)
    execute(ctx, [ApplyStatusEffect(target_id=U1, status_id="slow")])
    assert of(ctx.events, FollowupCancelled) == []
    assert state.units[U1].has_status(CHARGING)


def test_charging_cannot_be_cleansed_or_dispelled() -> None:
    definition = library().ruleset.status_def(CHARGING)
    assert definition.polarity == "neutral" and definition.beneficial


def test_a_controlled_caster_never_charges(monkeypatch: pytest.MonkeyPatch) -> None:
    """第一段結算完施放者已被控制（這裡直接讓施放者帶著暈眩再結算）：沒有蓄力。"""
    always(monkeypatch, 19)
    state = arena(CLEAVE, foes=((4, 3),))
    state.units[U1].statuses.append(StatusInstance("stun", remaining=1))
    ctx = Ctx(state)
    from trpg.engine.delayed import charge  # noqa: PLC0415

    charge(ctx, state.units[U1], library().skills[CLEAVE])
    reasons = [e.reason for e in of(ctx.events, EffectFizzled)]
    assert reasons == ["followup_caster_down"]
    assert not state.units[U1].has_status(CHARGING)


# ---------------------------------------------------------------------------
# 序列化、預覽、環境預告、視圖、重播
# ---------------------------------------------------------------------------


def test_the_charge_survives_save_and_load(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    state = state_from_json(state_to_json(_charged()))
    status = state.units[U1].get_status(CHARGING)
    assert status is not None and status.skill_id == CLEAVE
    _, events = until_turn_of(state, U1)
    assert hurt_by_caster(events) == [U2]


def test_the_preview_shows_the_planned_area() -> None:
    state = arena(CLEAVE, foes=((4, 3),))
    p = preview(state, UseSkill(unit_id=U1, skill_id=CLEAVE))
    assert p.landing == (3, 3)
    assert len(p.followup_tiles) == 9


def test_the_telegraph_and_the_view_show_the_countdown_and_the_area() -> None:
    state = _charged(RIPOSTE)
    forecast = telegraph(state)
    assert [(c.unit_id, c.release, c.remaining, len(c.tiles)) for c in forecast.charges] == [
        (U1, "attacked", 1, 5)
    ]
    view = project_for(state, Team.ALLY)
    me = next(u for u in view.units if u.id == U1)
    status = next(s for s in me.statuses if s.status_id == CHARGING)
    assert status.skill_id == RIPOSTE and status.release == "attacked"
    assert len(status.charge_tiles) == 5


def _cleave_first(state: BattleState) -> Any:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415

    unit = state.active
    assert unit is not None
    if unit.template_id == "build_push" and unit.cooldowns.get(CLEAVE) is None:
        action = UseSkill(unit_id=unit.id, skill_id=CLEAVE)
        if unit.ap >= 2 and unit.stamina >= 10:
            return action
    return UtilityAI(library().ai_profiles)(state)


def test_a_battle_with_a_charge_replays_exactly() -> None:
    lib = library_with_builds(library())
    setup = build_setup(lib, "test_flat_6x6", ["build_push"], ["bandit", "bandit"], max_rounds=6)
    run = run_battle(setup, 4, _cleave_first)
    assert any(isinstance(e, FollowupCharged) for e in run.events)
    assert any(isinstance(e, SkillFollowup) and e.when == "delayed" for e in run.events)
    again = replay(setup, 4, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    assert state_to_json(replay(setup, 4, log.actions).state) == state_to_json(run.state)
