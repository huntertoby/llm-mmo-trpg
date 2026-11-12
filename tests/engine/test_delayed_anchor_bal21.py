"""Phase BAL-21a：延遲段落在施放時選的格子（``followup.anchor: cast_tile``）。

規格 ``docs/phases/PhaseBAL-21計畫.md`` 第 4 節：施放時第一段選格 → 蓄力狀態記住那格；預告、釋放都以
那格為中心（不重驗射程與視線），施放者移動或被推開也不跟著走；命中、抵抗仍以施放者本人計。沒填
``anchor`` 的延遲段照舊跟著施放者。行為一致測試：都實際跑引擎。測試專用技能不放 ``content/``。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.skills import CHARGING, SkillDef
from trpg.engine import (
    BattleState,
    ResolveResult,
    UseSkill,
    preview,
    project_for,
    resolve,
    telegraph,
)
from trpg.engine.actions import Attack, EndTurn, Move
from trpg.engine.ai.composite import composite_estimate
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, DamageEffect
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    SkillFollowup,
)
from trpg.engine.runner import BattleLog, replay, run_battle
from trpg.engine.skills.targeting import selections
from trpg.engine.state import state_from_json, state_to_json
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Surface, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
FLAT9 = "\n".join(["000000000"] * 9)
ANCHOR = "skill_t_anchor"
LOOSE = "skill_t_loose"
SPOUT = "skill_lava_spout"
CASTER = (1, 4)
SPOT = Pos(x=4, y=4)


def delayed_skill(
    skill_id: str = ANCHOR, *, anchor: str | None = "cast_tile", release: str = "next_turn"
) -> SkillDef:
    """熔岩濺落型的測試技能：第一段選 4 格內一格、給自己護盾；第二段以那格（``anchor``）或施放者
    （沒有 ``anchor``）為中心的 3×3 火傷＋火地。"""
    follow: dict[str, Any] = {
        "when": "delayed",
        "release": release,
        "skeleton": "area",
        "shape": {"type": "square3", "range": 0},
        "effects": [
            {"type": "damage", "dice": "1d6", "element": "fire"},
            {"type": "create_surface", "surface": "fire", "duration": 2},
        ],
    }
    if anchor is not None:
        follow["anchor"] = anchor
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"測試落點 {skill_id[-6:]}",
            "tier": 1,
            "rarity": "rare",
            "skeleton": "aura",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": 1,
            "scaling_attr": "int",
            "shape": {"type": "ground_tile", "range": 4},
            "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
            "followup": follow,
            "cost": {"mana": 6},
        }
    )


def arena(
    skills: Sequence[SkillDef] = (),
    *,
    foes: Sequence[tuple[int, int]] = ((4, 4), (4, 5)),
    extra: Sequence[str] = (),
) -> BattleState:
    """施放者 U1 在 (1, 4)；敵人不動（速度 0）、沒有反應。"""
    m = make_map(FLAT9, None, ally=[CASTER], enemy=list(foes))
    ids = [*(s.id for s in skills), *extra]
    spawns = [spawn(Team.ALLY, CASTER, caster_template(ids))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200, speed=0)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=list(skills)), U1)


def always(monkeypatch: pytest.MonkeyPatch, d20: int) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(3, sides))


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def cast_at(state: BattleState, at: Pos = SPOT, skill_id: str = ANCHOR) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, target_pos=at))


def square(center: Pos) -> tuple[Pos, ...]:
    return tuple(Pos(x=center.x + dx, y=center.y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1))


def until_turn_of(state: BattleState, uid: UnitId) -> tuple[BattleState, list[EventBase]]:
    events: list[EventBase] = []
    for _ in range(20):
        if state.active_unit == uid and events:
            break
        assert state.active_unit is not None
        result = resolve(state, EndTurn(unit_id=state.active_unit))
        events += result.events
        state = result.state
    return state, events


def hurt_by_caster(events: Sequence[EventBase]) -> list[str]:
    return sorted({d.target_id for d in of(events, DamageDealt) if d.source_id == U1})


def walk_away(state: BattleState) -> BattleState:
    """施放者往左上走兩格（離開原本的位置）。"""
    path = (Pos(x=1, y=4), Pos(x=0, y=4), Pos(x=0, y=3))
    return resolve(state, Move(unit_id=U1, path=path)).state


# ---------------------------------------------------------------------------
# 施放：選格、預告
# ---------------------------------------------------------------------------


def test_casting_charges_on_the_chosen_tile() -> None:
    result = cast_at(arena([delayed_skill()]))
    charged = of(result.events, FollowupCharged)
    assert [(c.pos, c.anchored, c.tiles) for c in charged] == [(SPOT, True, square(SPOT))]
    status = result.state.units[U1].get_status(CHARGING)
    assert status is not None and status.skill_id == ANCHOR and status.anchor == SPOT
    assert hurt_by_caster(result.events) == []  # 第一段只有護盾
    text = describe_event(charged[0], result.state) or ""
    assert "落在指定位置" in text


def test_the_preview_shows_the_chosen_tile() -> None:
    p = preview(arena([delayed_skill()]), UseSkill(unit_id=U1, skill_id=ANCHOR, target_pos=SPOT))
    assert p.landing == (SPOT.x, SPOT.y)
    assert sorted(p.followup_tiles) == sorted((t.x, t.y) for t in square(SPOT))


def test_the_planned_area_stays_put_when_the_caster_moves() -> None:
    state = walk_away(cast_at(arena([delayed_skill()])).state)
    assert state.units[U1].xy == (0, 3)
    charges = telegraph(state).charges
    assert [(c.pos, c.anchored, c.tiles) for c in charges] == [(SPOT, True, square(SPOT))]
    me = next(u for u in project_for(state, Team.ALLY).units if u.id == U1)
    status = next(s for s in me.statuses if s.status_id == CHARGING)
    assert status.charge_anchored and status.charge_tiles == square(SPOT)


def test_a_tile_out_of_reach_is_illegal() -> None:
    with pytest.raises(IllegalActionError):
        cast_at(arena([delayed_skill()]), Pos(x=8, y=4))  # 曼哈頓距離 7 > 4


# ---------------------------------------------------------------------------
# 釋放：在原格結算
# ---------------------------------------------------------------------------


def test_the_release_lands_on_the_chosen_tile_after_the_caster_moved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = walk_away(cast_at(arena([delayed_skill()])).state)
    state, events = until_turn_of(state, U1)
    follow = of(events, SkillFollowup)
    assert [(f.when, f.origin, f.tiles) for f in follow] == [("delayed", SPOT, square(SPOT))]
    assert hurt_by_caster(events) == [U2, U3]
    assert not state.units[U1].has_status(CHARGING)
    burning = {
        xy for xy in ((t.x, t.y) for t in square(SPOT)) if state.tile(*xy).surface is Surface.FIRE
    }
    assert burning == {(t.x, t.y) for t in square(SPOT)}
    assert state.tile(0, 3).surface is Surface.NONE  # 施放者站的地方沒事


def test_the_release_is_not_rechecked_for_reach(monkeypatch: pytest.MonkeyPatch) -> None:
    """施放者走到 4 格外（第一段的射程外），第二段照樣在原格落下（T2：不重驗射程與視線）。"""
    always(monkeypatch, 19)
    cast = cast_at(arena([delayed_skill()]), Pos(x=4, y=5))  # 距離 4
    path = (Pos(x=1, y=4), Pos(x=0, y=4), Pos(x=0, y=3), Pos(x=0, y=2))
    state = resolve(cast.state, Move(unit_id=U1, path=path)).state
    assert abs(state.units[U1].xy[0] - 4) + abs(state.units[U1].xy[1] - 5) > 4
    _, events = until_turn_of(state, U1)
    assert [f.origin for f in of(events, SkillFollowup)] == [Pos(x=4, y=5)]
    assert hurt_by_caster(events) == [U2, U3]


def test_an_attacked_release_lands_on_the_chosen_tile(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    state = arena([delayed_skill(release="attacked")], foes=((2, 4), (4, 6)))
    state = cast_at(state, Pos(x=4, y=5)).state
    attacker = give_turn(state, U2)
    result = resolve(attacker, Attack(unit_id=U2, target_id=U1))
    follow = of(result.events, SkillFollowup)
    assert [f.origin for f in follow] == [Pos(x=4, y=5)]
    hurt = sorted({d.target_id for d in of(result.events, DamageDealt) if d.source_id == U1})
    assert hurt == [U3]  # (2, 4) 貼著施放者，但不在落點的 3×3 內


# ---------------------------------------------------------------------------
# 取消照舊
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effect", "reason"),
    [
        (ApplyStatusEffect(target_id=U1, status_id="stun"), "controlled"),
        (DamageEffect(target_id=U1, cause="status", mode="lethal"), "downed"),
    ],
)
def test_control_or_downing_cancels_an_anchored_charge(effect: Any, reason: str) -> None:
    state = cast_at(arena([delayed_skill()])).state
    ctx = Ctx(state)
    execute(ctx, [effect])
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == [reason]
    assert not state.units[U1].has_status(CHARGING)


def test_a_new_charge_replaces_the_anchored_one() -> None:
    first, second = delayed_skill(), delayed_skill("skill_t_anchor2")
    state = cast_at(arena([first, second])).state
    result = cast_at(give_turn(state, U1), Pos(x=4, y=5), second.id)
    assert [e.reason for e in of(result.events, FollowupCancelled)] == ["replaced"]
    status = result.state.units[U1].get_status(CHARGING)
    assert status is not None and status.skill_id == second.id and status.anchor == Pos(x=4, y=5)


# ---------------------------------------------------------------------------
# 沒填 anchor 的延遲段照舊跟著施放者
# ---------------------------------------------------------------------------


def test_lava_spout_still_follows_its_caster() -> None:
    state = arena(extra=[SPOUT])
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SPOUT))
    charged = of(result.events, FollowupCharged)
    assert [(c.pos, c.anchored) for c in charged] == [(Pos(x=1, y=4), False)]
    status = result.state.units[U1].get_status(CHARGING)
    assert status is not None and status.anchor is None
    moved = walk_away(result.state)
    (charge,) = telegraph(moved).charges
    assert charge.pos == Pos(x=0, y=3) and not charge.anchored
    assert Pos(x=1, y=3) in charge.tiles and Pos(x=1, y=4) in charge.tiles  # 以 (0, 3) 為中心的環


def test_a_loose_twin_with_the_same_first_stage_releases_around_the_caster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, 19)
    state = cast_at(arena([delayed_skill(LOOSE, anchor=None)]), skill_id=LOOSE).state
    _, events = until_turn_of(state, U1)
    assert [f.origin for f in of(events, SkillFollowup)] == [Pos(x=1, y=4)]
    assert hurt_by_caster(events) == []


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_the_ai_lists_the_anchored_skill_when_nobody_is_adjacent() -> None:
    """貼身沒人、4 格內有 2 名敵人：落在選定格的招有正分的候選；同數值、不帶 anchor 的招不列入。"""
    anchored, loose = delayed_skill(), delayed_skill(LOOSE, anchor=None)
    state = arena([anchored, loose])
    caster = state.units[U1]
    best = max(
        (
            v
            for pick, area in selections(state, caster, anchored)
            if (v := composite_estimate(state, caster, anchored, area, pick)) is not None
        ),
        default=None,
    )
    assert best is not None and best > 0
    assert all(
        composite_estimate(state, caster, loose, area, pick) is None
        for pick, area in selections(state, caster, loose)
    )
    scored = UtilityAI(library().ai_profiles).rank(state)
    mine = [s for s in scored if isinstance(s.action, UseSkill) and s.action.skill_id == ANCHOR]
    assert mine and max(s.score for s in mine) > 0
    assert not any(isinstance(s.action, UseSkill) and s.action.skill_id == LOOSE for s in scored)


# ---------------------------------------------------------------------------
# 序列化、重播
# ---------------------------------------------------------------------------


def test_the_anchor_survives_clone_and_json(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, 19)
    state = cast_at(arena([delayed_skill()])).state
    copy = state.clone()
    assert copy.units[U1].get_status(CHARGING) == state.units[U1].get_status(CHARGING)
    loaded = state_from_json(state_to_json(state))
    status = loaded.units[U1].get_status(CHARGING)
    assert status is not None and status.anchor == SPOT
    _, events = until_turn_of(walk_away(loaded), U1)
    assert [f.origin for f in of(events, SkillFollowup)] == [SPOT]


def test_a_battle_with_an_anchored_charge_replays_exactly() -> None:
    skill = delayed_skill()
    m = make_map(FLAT9, None, ally=[CASTER], enemy=[(4, 4), (4, 5)])
    spawns = [spawn(Team.ALLY, CASTER, caster_template([skill.id]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=30, speed=0)) for xy in ((4, 4), (4, 5))]
    setup = make_setup(m, spawns, max_rounds=6, skills=[skill])
    run = run_battle(setup, 3, UtilityAI(library().ai_profiles))
    assert any(isinstance(e, FollowupCharged) and e.anchored for e in run.events)
    assert any(isinstance(e, SkillFollowup) and e.when == "delayed" for e in run.events)
    log = BattleLog.model_validate_json(run.to_log().model_dump_json())
    again = replay(setup, 3, log.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert again.state.rng_state == run.state.rng_state
