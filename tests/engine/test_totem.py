"""圖騰（Phase 3D-4b）：不移動、不攻擊，自己的回合開始時給範圍內友方光環。"""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.test_summons import FLAT, SID, U1, cast, end, of, summon_skill
from trpg.content.battle import UnitTemplate
from trpg.engine import BattleState, EndTurn, UseSkill, legal_actions, preview
from trpg.engine.ai.summon import summon_estimate, summon_gains
from trpg.engine.events import EventBase, StatusApplied, TotemPulsed, TurnStarted, UnitSummoned
from trpg.shared.types import Pos, Team, UnitId

TOTEM = "summon_war_totem"
U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(2, 5))


def arena(
    *,
    allies: tuple[tuple[int, int], ...] = ((1, 3),),
    foes: tuple[tuple[int, int], ...] = ((3, 4),),
) -> BattleState:
    """U1（施放者，(0, 3)）、友方 ``allies``、敵人 ``foes``；U1 裝備召喚圖騰的技能。"""
    skill = summon_skill(TOTEM, duration=3)
    m = make_map(FLAT, None, ally=[(0, 3), *allies], enemy=list(foes) or [(6, 6)], objective=None)
    spawns = [spawn(Team.ALLY, (0, 3), caster_template([skill.id]))]
    spawns += [spawn(Team.ALLY, xy, no_reactions()) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def totem_turn(state: BattleState, x: int, y: int) -> tuple[BattleState, list[EventBase]]:
    """U1 在 (x, y) 立起圖騰並結束回合：回傳輪到圖騰時的狀態與這段事件。"""
    state = cast(state, x, y).state
    result = end(state)
    return result.state, list(result.events)


def test_the_totem_template_is_an_immobile_summon() -> None:
    template = library().ruleset.summon_def(TOTEM).template
    assert template.speed == 0 and template.summon and template.totem is not None
    assert template.totem.status == "empowered"


def test_a_totem_must_be_a_speed_zero_summon() -> None:
    base = library().ruleset.summon_def(TOTEM).template.model_dump()
    with pytest.raises(ValueError, match="speed 為 0"):
        UnitTemplate.model_validate({**base, "speed": 3})
    with pytest.raises(ValueError, match="speed 為 0"):
        UnitTemplate.model_validate({**base, "summon": False})


def test_the_totem_neither_moves_nor_attacks() -> None:
    # 敵人就在圖騰旁：圖騰的回合沒有 AP、沒有移動點數，合法動作只有結束回合
    state, events = totem_turn(arena(foes=((3, 3),)), 2, 3)
    [started] = [e for e in events if isinstance(e, TurnStarted)]
    totem = state.active
    assert totem is not None and totem.template_id == TOTEM
    assert (started.ap, started.move_points) == (0, 0)
    assert [type(a) for a in legal_actions(state)] == [EndTurn]


def test_the_totem_empowers_allies_within_its_radius_each_turn() -> None:
    # 圖騰在 (2, 3)，半徑 2：施放者 U1 (0, 3)、U2 (1, 3)、U3 (4, 3) 在範圍內，U4 (5, 3) 在範圍外，
    # 敵人 (3, 4) 不受影響
    state, events = totem_turn(arena(allies=((1, 3), (4, 3), (5, 3))), 2, 3)
    [pulse] = of(events, TotemPulsed)
    assert pulse.targets == [U1, U2, U3]  # 依單位 ID 排序
    for uid in (U1, U2, U3):
        status = state.units[uid].get_status("empowered")
        assert status is not None and status.remaining == 2 and status.source_id == pulse.unit_id
    assert not state.units[U4].has_status("empowered")
    assert not state.units[UnitId("unit_0005")].has_status("empowered")  # 敵人
    applied = of(events, StatusApplied)
    assert [e.target_id for e in applied] == [U1, U2, U3]


def test_the_aura_refreshes_every_round() -> None:
    state, _ = totem_turn(arena(allies=()), 1, 3)
    assert state.units[U1].has_status("empowered")  # 施放者 (0, 3) 在 1 格內
    pulses = 0
    for _ in range(12):  # 輪過幾回合：每次輪到圖騰都再給一次
        result = end(state)
        state = result.state
        pulses += len(of(result, TotemPulsed))
        assert state.active is not None
    assert pulses >= 2


def test_no_pulse_event_when_nobody_is_in_range() -> None:
    state, events = totem_turn(arena(allies=()), 4, 3)
    assert not of(events, TotemPulsed)
    assert state.active is not None and state.active.template_id == TOTEM


def test_two_totems_do_not_buff_each_other() -> None:
    skill = summon_skill(TOTEM, duration=3)
    state = arena(allies=())
    state = cast(state, 1, 3).state
    ready = state.clone()
    ready.units[U1].cooldowns = {}
    ready.units[U1].ap = ready.ruleset.core.ap_per_turn
    ready.units[U1].mana = 99
    state = cast(ready, 1, 2).state
    assert skill.id == SID
    state = end(state).state
    totems = [u for u in state.units_sorted() if u.template_id == TOTEM]
    assert len(totems) == 2
    assert all(not t.has_status("empowered") for t in totems)


def test_the_ai_values_a_totem_by_the_allies_in_its_aura() -> None:
    state = arena(allies=((1, 3),))
    profile = library().ai_profiles.by_id()["archer"]
    near = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=1, y=2))
    far = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=4, y=3))
    gains_near = summon_gains(state, state.units[U1], preview(state, near).min_events, profile)
    gains_far = summon_gains(state, state.units[U1], preview(state, far).min_events, profile)
    assert gains_near > gains_far >= 0
    points = profile.ally_status_values["empowered"]
    # 光環範圍 2：U1 (0, 3) 與 U2 (1, 3) 都在 (1, 2) 的範圍內；持續 3 輪
    expected = (
        profile.weights.support * points * 2 * 3 * Fraction(profile.summon.hit_permille, 1000)
    )
    assert gains_near == expected
    assert [e.template_id for e in of(preview(state, near).min_events, UnitSummoned)] == [TOTEM]


def test_the_estimate_skips_tiles_without_allies_in_range() -> None:
    state = arena(allies=((1, 3),))
    caster = state.units[U1]
    assert summon_estimate(state, caster, (4, 3), TOTEM) is None
    near = summon_estimate(state, caster, (1, 2), TOTEM)
    assert near is not None and near > 0


# ---------------------------------------------------------------------------
# 整場戰鬥（build_summoner）
# ---------------------------------------------------------------------------


@cache
def _summoner_run(map_id: str, seed: int) -> tuple[Any, Any]:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415
    from trpg.engine.runner import run_battle  # noqa: PLC0415
    from trpg.engine.setup import build_setup  # noqa: PLC0415
    from trpg.sim.lineup import build_allies, default_lineup  # noqa: PLC0415

    lib, allies = build_allies(library(), ["build_summoner"])
    _, enemies = default_lineup(lib, map_id)
    setup = build_setup(lib, map_id, allies, enemies, max_rounds=30)
    return setup, run_battle(setup, seed, UtilityAI(lib.ai_profiles))


def test_the_summoner_build_summons_and_the_totem_empowers_allies_in_a_full_battle() -> None:
    _, run = _summoner_run("swamp", 4)
    summoned = next(e for e in of(run.events, UnitSummoned) if e.template_id == TOTEM)
    assert summoned.skill_id == "skill_plant_totem"
    pulses = [p for p in of(run.events, TotemPulsed) if p.unit_id == summoned.unit_id]
    assert pulses and all(p.unit_id == summoned.unit_id for p in pulses)
    allied = {u.id for u in run.state.units.values() if u.team is Team.ALLY}
    assert all(set(p.targets) <= allied for p in pulses)
    totem = run.state.units[summoned.unit_id]
    assert totem.xy == (summoned.pos.x, summoned.pos.y)  # 沒有移動
    from trpg.engine.events import AttackRolled, UnitMoved  # noqa: PLC0415

    assert not [e for e in run.events if isinstance(e, AttackRolled) and e.attacker_id == totem.id]
    assert not [e for e in run.events if isinstance(e, UnitMoved) and e.unit_id == totem.id]
    assert run.state.ended


def test_a_totem_battle_replays_exactly() -> None:
    from trpg.engine import state_to_json  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _summoner_run("swamp", 4)
    again = replay(setup, 4, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


def test_the_summoner_build_also_summons_skeletons_and_spirits() -> None:
    kinds = {
        e.template_id
        for map_id, seed in (("swamp", 3), ("cliff_outpost", 4), ("cliff_outpost", 2))
        for e in _summoner_run(map_id, seed)[1].events
        if isinstance(e, UnitSummoned)
    }
    assert {"summon_skeleton_warrior", "summon_elemental_spirit"} <= kinds
