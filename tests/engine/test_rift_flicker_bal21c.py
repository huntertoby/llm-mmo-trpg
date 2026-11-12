"""BAL-21c 碎晶之主第 3 階段「界隙閃擊」：實際跑引擎驗證換招、數值、先打再閃走、AI 會放。"""

from __future__ import annotations

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.engine import UseSkill, legal_actions, resolve, resume
from trpg.engine.events import DamageDealt
from trpg.engine.events.movement import UnitMoved
from trpg.engine.events.skills import SkillFollowup, SkillUsed
from trpg.engine.runner import accept_all
from trpg.shared.types import Team

FLICK = "skill_rift_flicker"


def test_the_overload_phase_swaps_blink_for_flicker_and_collapse_inherits_it() -> None:
    lord = library().units["rift_shard_lord"]
    overload = next(p for p in lord.phases if p.id == "core_overload")
    assert overload.skills == ("skill_rift_shatter", FLICK, "skill_rift_tremor")
    collapse = next(p for p in lord.phases if p.id == "rift_collapse")
    assert collapse.skills is None  # 第 4 階段沒有自己的招式組，沿用第 3 階段（含界隙閃擊）


def test_flicker_values_follow_the_decision() -> None:
    skill = library().skills[FLICK]
    assert skill.enemy_only
    assert skill.ap_cost == 1
    assert skill.cost.cooldown == 3  # #149：冷卻 3
    assert skill.followup is not None and skill.followup.when == "after_action"
    assert [e.type for e in skill.followup.effects] == ["teleport"]


def _arena():  # type: ignore[no-untyped-def]
    lib = library()
    tpl = lib.enemy_catalog().template("rift_shard_lord")
    tpl = tpl.model_copy(update={"skills": (FLICK,), "phases": ()})
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(4, 3)])
    spawns = [spawn(Team.ALLY, (1, 3), "hero_fighter", skills=None), spawn(Team.ENEMY, (4, 3), tpl)]
    return give_turn(make_state(m, spawns), U2)


def test_flicker_strikes_first_then_teleports() -> None:
    state = _arena()
    action = next(
        a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == FLICK
    )
    assert action.target_id == U1
    first = resolve(state, action)
    assert first.pending is not None and first.pending.kind == "followup"
    assert any(isinstance(e, SkillUsed) and e.skill_id == FLICK for e in first.events)
    decision = accept_all(first.state, first.pending)
    assert decision.accept and decision.followup_target is not None
    second = resume(first.state, decision)
    # 先打：第一段的傷害（命中時）全在第一次結算裡；閃走的 skill_followup 在續答之後
    assert not any(isinstance(e, DamageDealt) for e in second.events)
    assert any(isinstance(e, SkillFollowup) for e in second.events)
    assert not any(isinstance(e, SkillFollowup) for e in first.events)
    moved = [e for e in second.events if isinstance(e, UnitMoved) and e.unit_id == U2]
    assert len(moved) == 1 and moved[0].mode == "teleport"
    assert second.state.units[U2].pos == decision.followup_target.target_pos
    assert second.state.units[U2].pos != state.units[U2].pos
