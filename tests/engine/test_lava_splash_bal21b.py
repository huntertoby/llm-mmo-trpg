"""Phase BAL-21b：灰燼之心第 1 階段的「熔岩濺落」（``skill_lava_splash``）。

取代 ``skill_lava_spout``（規格 ``docs/phases/PhaseBAL-21計畫.md`` 第 0.0 節、第 2 節 Q1／Q2、
第 5 節）：施放時選 4 格內一格（給自己護盾 1d4），下一個自己的回合開始在那格的 3×3 落下
1d6 火＋火地 2 回合；法力 6、冷卻 2、2 AP；``molten_lord`` 不換。
行為一致測試：實際跑引擎（內建技能，不另造測試技能）。
GB-2（#164 R5）起不選格：落點由引擎選（``followup.anchor: farthest_enemy``，最遠的敵人當下的格子），
第一段形狀 ``self``；本檔的落點跟著改成最遠的那名敵人（引擎規則的細節在
``tests/engine/test_giant_parts_gb1c.py``）。
"""

from __future__ import annotations

from collections.abc import Sequence

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
from trpg.content.skills import CHARGING
from trpg.engine import BattleState, ResolveResult, UseSkill, resolve, telegraph
from trpg.engine.actions import EndTurn
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    FollowupCharged,
    ShieldGained,
    SkillFollowup,
)
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Surface, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
FLAT9 = "\n".join(["000000000"] * 9)
SPLASH = "skill_lava_splash"
SPOUT = "skill_lava_spout"
CASTER = (1, 4)
SPOT = Pos(x=4, y=5)  # GB-2：最遠的敵人（(4, 4) 距 3、(4, 5) 距 4）


def arena(foes: Sequence[tuple[int, int]] = ((4, 4), (4, 5))) -> BattleState:
    """施放者 U1 在 (1, 4)，身邊一圈沒人；敵人不動（速度 0）、沒有反應。"""
    m = make_map(FLAT9, None, ally=[CASTER], enemy=list(foes))
    spawns = [spawn(Team.ALLY, CASTER, caster_template([SPLASH]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200, speed=0)) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def square(center: Pos) -> tuple[Pos, ...]:
    return tuple(Pos(x=center.x + dx, y=center.y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1))


def cast(state: BattleState) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=SPLASH))


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


def test_the_shell_phase_swaps_spout_for_splash_and_molten_lord_keeps_spout() -> None:
    lib = library()
    heart = lib.units["ashen_heart"]
    assert SPLASH in heart.skills and SPOUT not in heart.skills
    assert heart.phases[0].skills is None  # 第 1 階段用範本的技能組
    assert (
        SPOUT in lib.units["molten_lord"].skills and SPLASH not in lib.units["molten_lord"].skills
    )


def test_the_numbers_follow_the_q1_defaults() -> None:
    skill = library().skills[SPLASH]
    assert skill.enemy_only and skill.ap_cost == 2
    assert (skill.cost.mana, skill.cost.cooldown) == (6, 2)
    assert skill.shape.type == "self"  # GB-2：不選格
    assert [(e.type, str(e.dice), e.affects) for e in skill.effects] == [("shield", "1d4", "self")]
    follow = skill.followup
    assert follow is not None
    assert (follow.when, follow.release, follow.anchor) == (
        "delayed",
        "next_turn",
        "farthest_enemy",
    )
    assert (follow.shape.type, follow.shape.range) == ("square3", 0)
    assert follow.effects is not None
    kinds = [
        (e.type, e.dice and str(e.dice), e.element, e.surface, e.duration) for e in follow.effects
    ]
    assert kinds == [
        ("damage", "1d6", "fire", None, None),
        ("create_surface", None, None, "fire", 2),
    ]


def test_casting_shields_the_caster_and_marks_the_chosen_square() -> None:
    result = cast(arena())
    charged = of(result.events, FollowupCharged)
    assert [(c.pos, c.anchored, c.tiles) for c in charged] == [(SPOT, True, square(SPOT))]
    assert [s.unit_id for s in of(result.events, ShieldGained)] == [U1]
    assert not of(result.events, DamageDealt)  # 施放回合不傷人
    (charge,) = telegraph(result.state).charges
    assert charge.pos == SPOT and charge.anchored


def test_the_next_turn_drops_fire_on_the_chosen_square(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(3, sides))
    state, events = until_turn_of(cast(arena()).state, U1)
    assert [(f.when, f.origin) for f in of(events, SkillFollowup)] == [("delayed", SPOT)]
    hurt = sorted({d.target_id for d in of(events, DamageDealt) if d.source_id == U1})
    assert hurt == [U2, U3]
    assert all(state.tile(t.x, t.y).surface is Surface.FIRE for t in square(SPOT))
    assert state.tile(*CASTER).surface is Surface.NONE
    assert not state.units[U1].has_status(CHARGING)


def test_the_ai_casts_it_when_nobody_is_adjacent() -> None:
    """lava_spout 施放率低的原因（身邊一圈沒人就不列入）：熔岩濺落在同樣的場面有正分候選。"""
    scored = UtilityAI(library().ai_profiles).rank(arena())
    mine = [s for s in scored if isinstance(s.action, UseSkill) and s.action.skill_id == SPLASH]
    assert mine and max(s.score for s in mine) > 0
