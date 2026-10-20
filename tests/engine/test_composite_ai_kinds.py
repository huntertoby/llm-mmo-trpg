"""Phase 3F-4b：AI 使用 3F-4a 的四種即時第二段與延遲段（``docs/phases/Phase3F計畫.md`` 4.2）。

- 候選估計（``composite_estimate``）：四種即時第二段看第一段（聚集含打擊段）的影響範圍、延遲段看
  以施放者目前位置推算的預計範圍；
- 第二段的暫停由 ``runner.accept_all`` → ``choose_followup`` 回答：打帶跑的後跳選離敵人最遠的
  落點、其他選範圍內敵人最多的選取，沒有值得的選取時放棄。
"""

from __future__ import annotations

from collections.abc import Sequence

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.ai.composite import choose_followup, composite_estimate
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.results import Pending
from trpg.engine.runner import accept_all
from trpg.engine.skills.targeting import selections
from trpg.shared.types import Pos, Team, UnitId

U1 = UnitId("unit_0001")
FLAT = "\n".join(["0000000"] * 7)


def arena(skills: Sequence[str], foes: Sequence[tuple[int, int]], hp: int = 200) -> BattleState:
    m = make_map(FLAT, None, ally=[(3, 3)], enemy=list(foes))
    spawns = [spawn(Team.ALLY, (3, 3), caster_template(list(skills), base="hero_fighter"))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=hp, speed=0)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def pending(skill_id: str) -> Pending:
    return Pending(kind="followup", unit_id=U1, skill_id=skill_id)


def test_the_hit_and_run_leap_lands_as_far_from_the_foes_as_it_can() -> None:
    state = arena(["skill_retreating_slash"], [(4, 3)])
    decision = choose_followup(state, pending("skill_retreating_slash"))
    assert decision.accept and decision.followup_target is not None
    pos = decision.followup_target.target_pos
    assert pos is not None and abs(pos.x - 4) + abs(pos.y - 3) == 3  # 2 格內離 (4, 3) 最遠
    assert accept_all(state, pending("skill_retreating_slash")) == decision


def test_the_next_target_is_the_one_with_a_foe() -> None:
    state = arena(["skill_death_spiral"], [(5, 3), (3, 6)])
    decision = choose_followup(state, pending("skill_death_spiral"))
    assert decision.accept and decision.followup_target is not None
    assert decision.followup_target.target_id is not None


def test_nothing_worth_hitting_declines_the_second_segment() -> None:
    state = arena(["skill_death_spiral"], [(6, 6)])
    decision = choose_followup(state, pending("skill_death_spiral"))
    assert not decision.accept and decision.followup_target is None


def test_every_kind_is_estimated_when_foes_are_in_reach() -> None:
    lib = library()
    kinds = [
        "skill_retreating_slash",
        "skill_gravity_burst",
        "skill_death_spiral",
        "skill_armor_break_combo",
        "skill_charged_cleave",
        "skill_parry_riposte",
    ]
    state = arena(kinds, [(4, 3), (3, 4)])
    caster = state.units[U1]
    for skill_id in kinds:
        skill = lib.skills[skill_id]
        values = [
            composite_estimate(state, caster, skill, area)
            for _, area in selections(state, caster, skill)
        ]
        assert any(v is not None and v > 0 for v in values), skill_id


def test_a_charge_with_nobody_in_the_planned_area_is_not_a_candidate() -> None:
    state = arena(["skill_charged_cleave"], [(6, 6)])
    caster = state.units[U1]
    skill = library().skills["skill_charged_cleave"]
    assert all(
        composite_estimate(state, caster, skill, a) is None
        for _, a in selections(state, caster, skill)
    )


def test_the_ai_charges_when_surrounded() -> None:
    state = arena(["skill_charged_cleave"], [(4, 3), (2, 3), (3, 4), (3, 2)], hp=300)
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_charged_cleave"


def test_the_ai_slashes_and_then_answers_the_pause() -> None:
    state = arena(["skill_retreating_slash"], [(4, 3), (5, 2), (5, 4)], hp=300)
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill) and action.skill_id == "skill_retreating_slash"
    result = resolve(state, action)
    assert result.pending is not None and result.pending.kind == "followup"
    from trpg.engine import resume  # noqa: PLC0415

    done = resume(result.state, accept_all(result.state, result.pending))
    assert done.pending is None
    assert done.state.units[U1].pos != Pos(x=3, y=3)
