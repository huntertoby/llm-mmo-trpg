"""Phase 5A-M1：引擎機制①（``docs/phases/Phase5計畫.md`` 第 13 節）。

開場隱蔽（範本 ``opening_statuses``、詞綴 ``add_opening_statuses``）、死亡時留下表面（狀態
``on_death_surface``）、同門相護（內建反應 ``kin_ward``）、蓄力強招「九轉回天」與 AI 的估值。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn, template
from trpg.content.battle import OpeningStatus, StatusDef, UnitTemplate
from trpg.content.skills import CHARGING
from trpg.content.world_enemies import apply_affix
from trpg.engine import BattleState, UseSkill, preview, resolve
from trpg.engine.actions import Attack, EndTurn
from trpg.engine.ai.priority import is_kin_warden, priority_points
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, DamageEffect
from trpg.engine.events import (
    FollowupCancelled,
    FollowupCharged,
    Healed,
    ReactionTriggered,
    ShieldGained,
    SurfaceChanged,
    UnitDowned,
)
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.shared.rng import Rng
from trpg.shared.types import Surface, Team, UnitId

FLAT = "\n".join(["0000000"] * 7)
U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
REVIVAL = "skill_nine_turns_revival"


def _state(
    allies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    enemies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    seed: int = 0,
) -> BattleState:
    m = make_map(FLAT, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    spawns = [spawn(Team.ALLY, p, t) for p, t in allies]
    spawns += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    return make_state(m, spawns, seed=seed)


def _hero() -> UnitTemplate:
    return template("hero_fighter", reactions=[], skills=[])


def _always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 18 if sides == 20 else min(2, sides))


# ---------------------------------------------------------------------------
# 開場隱蔽
# ---------------------------------------------------------------------------


def test_template_opening_concealment_lasts_one_turn() -> None:
    veiled = template("bandit", opening_statuses=[{"status": "concealed", "duration": 1}])
    state = _state([((0, 0), _hero())], [((6, 6), veiled)])
    status = state.units[U2].get_status("concealed")
    assert status is not None and status.remaining == 1
    assert not state.units[U1].has_status("concealed")
    for _ in range(20):  # 敵人自己的第 1 回合結束後就沒有了
        if state.round > 1:
            break
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    assert not state.units[U2].has_status("concealed")


def test_mist_veiled_affix_adds_opening_concealment() -> None:
    lib = library()
    affix = lib.world_enemies.affix_by_id()["mist_veiled"]  # type: ignore[union-attr]
    veiled = apply_affix(lib.unit("mist_wolf"), affix, lib.ruleset.reactions.default_rules)
    assert veiled.opening_statuses == (OpeningStatus(status="concealed", duration=1),)
    assert veiled.skills == lib.unit("mist_wolf").skills  # 不再加受擊隱蔽的反應技
    state = _state([((0, 0), _hero())], [((6, 6), veiled)])
    assert state.units[U2].has_status("concealed")


def test_opening_status_schema_limits() -> None:
    with pytest.raises(ValidationError):
        OpeningStatus(status="concealed", duration=3)


# ---------------------------------------------------------------------------
# 死亡時留下表面
# ---------------------------------------------------------------------------


def _down(state: BattleState, uid: UnitId) -> tuple[BattleState, list[str]]:
    """把 ``uid`` 打倒，回傳狀態與事件文字。"""
    s = state.clone()
    ctx = Ctx(s)
    execute(ctx, [DamageEffect(target_id=uid, source_id=U1, flat=999)])
    texts = [
        text
        for e in ctx.events
        if isinstance(e, SurfaceChanged) and (text := describe_event(e, s)) is not None
    ]
    return s, texts


def test_shard_golem_leaves_water_when_downed() -> None:
    golem = library().unit("shard_golem")
    state = _state([((0, 0), _hero())], [((3, 3), golem)])
    assert state.units[U2].has_status("shard_burst")
    after, texts = _down(state, U2)
    assert not after.units[U2].alive
    wet = {(x, y) for x in range(7) for y in range(7) if after.tile(x, y).surface is Surface.WATER}
    assert wet == {(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)}  # 半徑 1（曼哈頓）
    assert len(texts) == 5 and all("倒下時留下的" in text for text in texts)


def test_no_death_surface_without_status() -> None:
    state = _state([((0, 0), _hero())], [((3, 3), template("bandit"))])
    after, texts = _down(state, U2)
    assert not texts
    assert after.tile(3, 3).surface is Surface.NONE


def test_death_surface_status_rules() -> None:
    lib = library()
    burst = lib.ruleset.status_def("shard_burst")
    assert burst.polarity == "neutral" and burst.expires == "never"
    with pytest.raises(ValidationError):
        StatusDef.model_validate(
            {
                "id": "bad",
                "name_zh": "壞",
                "description_zh": "壞",
                "polarity": "buff",
                "beneficial": True,
                "expires": "never",
                "on_death_surface": {"surface": "fire"},
            }
        )


# ---------------------------------------------------------------------------
# 同門相護
# ---------------------------------------------------------------------------


def _sect(base: str = "sect_swordsman", **kw: object) -> UnitTemplate:
    return template(base, **kw)


def _kin_state(
    healer_at: tuple[int, int] = (3, 1), *, healer_tags: Sequence[str] = ("humanoid", "sect")
) -> BattleState:
    swordsman = _sect(reactions=[], max_hp=60)
    healer = template("sect_acolyte", tags=list(healer_tags))
    state = _state([((3, 4), _hero())], [((3, 3), swordsman), (healer_at, healer)])
    return give_turn(state, U1)


def test_kin_ward_shields_kin_within_two_tiles(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    state = _kin_state()
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    reacted = [e for e in result.events if isinstance(e, ReactionTriggered)]
    assert [(e.unit_id, e.reaction) for e in reacted] == [(U3, "kin_ward")]
    shields = [e for e in result.events if isinstance(e, ShieldGained)]
    assert shields and shields[0].unit_id == U2
    assert result.state.units[U3].reactions_used == 1
    texts = [describe_event(e, result.state) for e in reacted]
    assert "同門相護" in (texts[0] or "")


def test_kin_ward_once_per_round(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    state = _kin_state()
    first = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    second = resolve(give_turn(first, U1), Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in second.events)


def test_kin_ward_out_of_range_or_not_kin(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    far = _kin_state(healer_at=(3, 0))  # 距離 3
    result = resolve(far, Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in result.events)
    stranger = _kin_state(healer_tags=("humanoid",))
    result = resolve(stranger, Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in result.events)


def test_kin_ward_blocked_by_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    state = _kin_state()
    state.units[U3].statuses.append(StatusInstance("silenced", remaining=1, source_id=U1))
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in result.events)


def test_kin_ward_triggers_on_skill_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    hero = template("hero_fighter", reactions=[], skills=["skill_first_strike"], max_mana=99)
    swordsman = _sect(reactions=[], max_hp=60)
    healer = library().unit("sect_acolyte")
    state = give_turn(_state([((3, 4), hero)], [((3, 3), swordsman), ((3, 1), healer)]), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_first_strike", target_id=U2))
    assert any(isinstance(e, ReactionTriggered) and e.unit_id == U3 for e in result.events)


def test_cloud_ridge_kin_wardens() -> None:
    lib = library()
    state = _state(
        [((0, 0), _hero())],
        [
            ((6, 6), lib.unit("sect_acolyte")),
            ((5, 6), lib.unit("sect_alchemist")),
            ((4, 6), lib.unit("sect_steward")),
            ((3, 6), lib.unit("sect_swordsman")),
        ],
    )
    wardens = [is_kin_warden(state, state.units[u]) for u in (U2, U3, U4)]
    assert wardens == [True, True, True]
    assert not is_kin_warden(state, state.units[UnitId("unit_0005")])
    assert "skill_stand_firm" not in lib.unit("sect_swordsman").skills


# ---------------------------------------------------------------------------
# 蓄力強招「九轉回天」
# ---------------------------------------------------------------------------


def _revival_state() -> BattleState:
    steward = library().unit("sect_steward")
    swordsman = _sect(reactions=[], max_hp=60)
    state = _state([((0, 6), _hero())], [((3, 3), steward), ((3, 2), swordsman)])
    state = give_turn(state, U2)
    state.units[U2].hp = state.units[U2].max_hp - 20
    state.units[U3].hp = 10
    return state


def test_revival_charges_then_heals_next_turn() -> None:
    state = _revival_state()
    result = resolve(state, UseSkill(unit_id=U2, skill_id=REVIVAL))
    charged = [e for e in result.events if isinstance(e, FollowupCharged)]
    assert charged and charged[0].name_zh == "九轉回天"
    assert result.state.units[U2].has_status(CHARGING)
    assert result.state.units[U2].ap == 0  # 整回合（3 AP）
    s = result.state
    healed: list[Healed] = []
    for _ in range(30):
        assert s.active_unit is not None
        step = resolve(s, EndTurn(unit_id=s.active_unit))
        healed += [e for e in step.events if isinstance(e, Healed) and e.source_id == U2]
        s = step.state
        if not s.units[U2].has_status(CHARGING):
            break
    assert {e.target_id for e in healed} == {U2, U3}  # 3×3 內的友方；主角（敵方）不受治療


def test_revival_cancelled_by_stun() -> None:
    state = resolve(_revival_state(), UseSkill(unit_id=U2, skill_id=REVIVAL)).state
    s = state.clone()
    ctx = Ctx(s)
    execute(ctx, [ApplyStatusEffect(target_id=U2, status_id="stun", source_id=U1, duration=1)])
    assert any(isinstance(e, FollowupCancelled) for e in ctx.events)
    assert not s.units[U2].has_status(CHARGING)


def test_ai_casts_revival_when_kin_hurt() -> None:
    state = _revival_state()
    state.units[U2].cooldowns = {}
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill)
    assert action.skill_id in {REVIVAL, "skill_sanctuary"}


def test_ai_values_interrupting_charge_and_kin_wardens() -> None:
    lib = library()
    state = resolve(_revival_state(), UseSkill(unit_id=U2, skill_id=REVIVAL)).state
    state = give_turn(state, U1)
    hero = state.units[U1]
    hero.pos = hero.pos.model_copy(update={"x": 3, "y": 4})
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    if not any(isinstance(e, UnitDowned) for e in p.max_events):  # 打不倒：不加分
        assert priority_points(state, hero, p.min_events, p.max_events, Fraction(1), rules) == 0
    state.units[U2].hp = 1
    state.units[U2].statuses = [s for s in state.units[U2].statuses if s.status_id != "shielded"]
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    points = priority_points(state, hero, p.min_events, p.max_events, Fraction(1), rules)
    assert points == rules.priority_kill_points + rules.interrupt_points
    # 暈眩正在蓄力的敵人也算打斷
    stun = ApplyStatusEffect(target_id=U2, status_id="stun", source_id=U1, duration=1)
    s = state.clone()
    ctx = Ctx(s)
    execute(ctx, [stun])
    controlled = priority_points(state, hero, tuple(ctx.events), (), Fraction(1), rules)
    assert controlled == rules.interrupt_points
