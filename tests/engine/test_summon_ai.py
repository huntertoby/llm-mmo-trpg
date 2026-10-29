"""召喚的 AI 與整場戰鬥（Phase 3D-4a）：召喚者的評分與選位、召喚物由效用 AI 行動、重播一致。"""

from __future__ import annotations

from fractions import Fraction
from functools import cache
from typing import Any

from tests.engine.helpers import library
from tests.engine.test_summons import SID, U1, arena, cast, summon_skill
from trpg.content.summons import summon_dpr
from trpg.engine import UseSkill, preview, state_to_json
from trpg.engine.ai.summon import summon_estimate, summon_gains
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import AttackRolled, SummonExpired, TurnStarted, UnitSummoned
from trpg.engine.rules.geometry import manhattan
from trpg.engine.summons.core import growth_of
from trpg.shared.types import Pos


def test_preview_shows_the_summon_without_changing_the_state() -> None:
    state = arena()
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=2, y=3))
    p = preview(state, action)
    assert any(isinstance(e, UnitSummoned) for e in p.min_events)
    assert len(state.units) == 2
    assert len(p.min_state.units) == 3


def test_summon_gains_are_dpr_times_rounds_minus_distance() -> None:
    state = arena(summon_skill(duration=2), foes=((6, 3),))
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=2, y=3))
    p = preview(state, action)
    profile = library().ai_profiles.by_id()["cunning"]
    grown = growth_of(state, state.units[U1], SID)  # 3-33c：估值納入施放者的成長
    dpr = summon_dpr(
        state.ruleset.summon_def("summon_skeleton_warrior"),
        flat=grown.flat,
        bonus_permille=grown.bonus_permille,
    )
    [summoned] = [e for e in p.min_events if isinstance(e, UnitSummoned)]
    assert summoned.infusion == "prone"  # 3-33e1：技能製造「倒地」「召喚物」，預設灌注第一個
    dpr += profile.summon.infusion_points  # 帶灌注的召喚物每輪多算 infusion_points
    hit = Fraction(profile.summon.hit_permille, 1000)
    cost = Fraction(profile.summon.distance_cost_permille, 1000)
    expected = profile.weights.damage * dpr * 2 * hit - cost * 4
    assert summon_gains(state, state.units[U1], p.min_events, profile) == expected


def test_replacing_the_oldest_summon_costs_its_remaining_value() -> None:
    state = cast(arena(summon_skill(duration=3)), 2, 3).state
    state = cast(_ready(state), 2, 4).state
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=2, y=2))
    ready = _ready(state)
    p = preview(ready, action)
    assert any(isinstance(e, SummonExpired) and e.reason == "limit" for e in p.min_events)
    profile = library().ai_profiles.by_id()["cunning"]
    fresh = summon_gains(
        ready, ready.units[U1], [e for e in p.min_events if isinstance(e, UnitSummoned)], profile
    )
    assert summon_gains(ready, ready.units[U1], p.min_events, profile) < fresh


def _ready(state: Any) -> Any:
    s = state.clone()
    s.units[U1].cooldowns = {}
    s.units[U1].ap = s.ruleset.core.ap_per_turn
    return s


def test_the_estimate_prefers_tiles_next_to_the_enemy() -> None:
    state = arena(foes=((4, 3),))
    caster = state.units[U1]
    near = summon_estimate(state, caster, (3, 3))
    far = summon_estimate(state, caster, (1, 3))
    assert near is not None and far is not None and near > far


def test_the_ai_summons_next_to_the_enemy_when_it_cannot_attack() -> None:
    # 施放者是法師（法杖射程 5），敵人在射程外：召喚是唯一有收益的動作之一
    state = arena(summon_skill(duration=3), foes=((6, 6),))
    ai = UtilityAI(library().ai_profiles)
    scored = [(s.score, s.action) for s in ai.rank(state) if isinstance(s.action, UseSkill)]
    assert scored
    score, action = max(scored, key=lambda item: item[0])
    assert score > 0
    pos = action.target_pos
    assert pos is not None
    reach = [a.target_pos for _, a in scored if a.target_pos is not None]
    assert manhattan((pos.x, pos.y), (6, 6)) == min(manhattan((p.x, p.y), (6, 6)) for p in reach)


# ---------------------------------------------------------------------------
# 整場戰鬥（build_trapper 裝備了示範技能「喚起骷髏」）
# ---------------------------------------------------------------------------


@cache
def _trapper_run(map_id: str, seed: int) -> Any:
    from trpg.engine.runner import run_battle  # noqa: PLC0415
    from trpg.engine.setup import build_setup  # noqa: PLC0415
    from trpg.sim.lineup import build_allies, default_lineup  # noqa: PLC0415

    lib, allies = build_allies(library(), ["build_trapper"])
    _, enemies = default_lineup(lib, map_id)
    setup = build_setup(lib, map_id, allies, enemies, max_rounds=30)
    return setup, run_battle(setup, seed, UtilityAI(lib.ai_profiles))


def test_the_ai_casts_the_summon_and_the_summon_acts() -> None:
    _, run = _trapper_run("dark_forest", 6)
    # 3D-6：build_trapper 另有殘影之誓（倒下時的分身，orphan），這裡只看喚起骷髏；
    # 原本的 swamp 種子 1
    # 改為啟動殘影之誓後不再召喚，換成 dark_forest 種子 0；
    # 3-20 加入跑步後戰鬥節奏變快，換成種子 25；
    # 3-21a 加入守護、換位、瞄準後換成種子 10；
    # 3-24a1 弓有拋射、AI 軌跡改變後換成種子 0；
    # 3-33c 召喚物依模式行動（跟隨預設待在召喚者附近）、軌跡改變後換成種子 6
    [summoned] = [e for e in run.events if isinstance(e, UnitSummoned) and not e.orphan]
    assert summoned.skill_id == "skill_raise_skeleton"
    turns = [e for e in run.events if isinstance(e, TurnStarted) and e.unit_id == summoned.unit_id]
    attacks = [
        e for e in run.events if isinstance(e, AttackRolled) and e.attacker_id == summoned.unit_id
    ]
    assert turns and attacks
    first_turn = run.events.index(turns[0])
    owner_turns = [
        i
        for i, e in enumerate(run.events)
        if isinstance(e, TurnStarted) and e.unit_id == summoned.owner_id and i < first_turn
    ]
    between = run.events[owner_turns[-1] : first_turn]
    assert not [e for e in between if isinstance(e, TurnStarted) and e.unit_id != summoned.owner_id]
    assert run.state.ended


def test_a_summoning_battle_replays_exactly() -> None:
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _trapper_run("dark_forest", 0)
    again = replay(setup, 0, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]
