"""17 種召喚物（二）b（Phase 3-33e2b，``docs/design/06-技能.md`` 6.29.5）：藤蔓、守護靈、吸引圖騰、
高台圖騰、鷹隼飛行、灌注失效紀錄。"""

from __future__ import annotations

from dataclasses import replace

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
from tests.engine.skill_helpers import of
from tests.engine.test_summon_growth import arena, cast_at
from trpg.engine import BattleState, Move, UseSkill, legal_actions, resolve
from trpg.engine.context import Ctx
from trpg.engine.events import (
    InfusionFizzled,
    SnareTriggered,
    SummonPulled,
    TerrainChanged,
    UnitSummoned,
)
from trpg.engine.lifecycle import dismiss_summon, down_unit
from trpg.engine.rules.movement import find_path, reachable_tiles
from trpg.engine.state import InfusedSkill
from trpg.engine.summons import pulse_summon, weakest_ally
from trpg.engine.turns import end_turn, start_turn
from trpg.narrative.events import describe_event
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, Surface, Team, UnitId
from trpg.skillgen.budget import skill_budget

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))

NEW_SKILLS = {
    "skill_summon_vine": ("summon_vine", "prone"),
    "skill_summon_guardian_spirit": ("summon_guardian_spirit", "summon"),
    "skill_summon_pull_totem": ("summon_pull_totem", "collision"),
    "skill_summon_plateau_totem": ("summon_plateau_totem", "high_ground"),
}


def path(*xy: tuple[int, int]) -> tuple[Pos, ...]:
    return tuple(Pos(x=x, y=y) for x, y in xy)


def summoned(
    skill_id: str, at: tuple[int, int] = (2, 3), *, foes: tuple[tuple[int, int], ...] = ((6, 6),)
) -> tuple[BattleState, UnitId]:
    return cast_at(arena([skill_id], foes=foes), skill_id, *at)


def pulse(state: BattleState, sid: UnitId) -> Ctx:
    ctx = Ctx(state.clone())
    pulse_summon(ctx, ctx.state.units[sid])
    return ctx


def statuses(state: BattleState, uid: UnitId) -> set[str]:
    return {s.status_id for s in state.units[uid].statuses}


# ---------------------------------------------------------------------------
# 內容：技能的關鍵字與預算、範本欄位
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", sorted(NEW_SKILLS))
def test_new_summon_skills_have_their_keyword_and_pass_the_budget(skill_id: str) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    template_id, keyword = NEW_SKILLS[skill_id]
    makes = lib.ruleset.skill_keywords(skill).makes
    assert keyword in makes and "summon" in makes
    assert skill_budget(skill, lib).ok
    assert [e.unit for e in skill.effects] == [template_id]
    assert any(skill_id in p.skills for p in lib.dev_starters.packs)


def test_new_templates_have_modes_looks_and_traits() -> None:
    summons = library().ruleset.summons.by_id()
    expected_modes = {
        "summon_vine": "hold",
        "summon_guardian_spirit": "guard",
        "summon_pull_totem": "hold",
        "summon_plateau_totem": "hold",
    }
    for template_id, mode in expected_modes.items():
        template = summons[template_id].template
        assert template.default_mode == mode and template.look is not None
    assert summons["summon_vine"].template.snare is not None
    assert summons["summon_vine"].template.speed == 0
    assert summons["summon_pull_totem"].template.pulse is not None
    assert summons["summon_pull_totem"].template.inert
    assert summons["summon_plateau_totem"].template.platform is not None
    assert summons["summon_guardian_spirit"].template.pulse is not None


# ---------------------------------------------------------------------------
# 藤蔓
# ---------------------------------------------------------------------------


def vine_arena() -> tuple[BattleState, UnitId]:
    """藤蔓在 (3, 3)；敵人 U2 在 (3, 6)、U3 在 (6, 3)。"""
    state, sid = summoned("skill_summon_vine", (3, 3), foes=((3, 6), (6, 3)))
    return state, sid


def test_vine_cannot_move() -> None:
    state, sid = vine_arena()
    assert state.units[sid].speed == 0
    assert reachable_tiles(give_turn(state, sid), sid) == {}


def test_vine_snares_an_enemy_walking_next_to_it() -> None:
    state, sid = vine_arena()
    result = resolve(give_turn(state, U2), Move(unit_id=U2, path=path((3, 6), (3, 5), (3, 4))))
    assert statuses(result.state, U2) >= {"slow", "prone"}
    [event] = of(result, SnareTriggered)
    assert (event.unit_id, event.target_id) == (sid, U2)
    assert result.state.units[U2].xy == (3, 4)


def test_vine_stops_the_walk_with_prone() -> None:
    state, _ = vine_arena()
    # 走進相鄰格就倒地：不會繼續走到更遠的格子
    result = resolve(give_turn(state, U2), Move(unit_id=U2, path=path((3, 6), (3, 5), (3, 4))))
    assert result.state.units[U2].xy == (3, 4)


def test_vine_snares_once_per_round_and_again_next_round() -> None:
    state, sid = vine_arena()
    first = resolve(give_turn(state, U2), Move(unit_id=U2, path=path((3, 6), (3, 5), (3, 4))))
    assert first.state.units[sid].snare_round == first.state.round
    # 同一輪、另一個敵人也走過來：這一輪已經用過
    again = give_turn(first.state, U3)
    second = resolve(again, Move(unit_id=U3, path=path((6, 3), (5, 3), (4, 3))))
    assert of(second, SnareTriggered) == []
    assert "prone" not in statuses(second.state, U3)
    # 下一輪恢復
    later = give_turn(second.state, U3)
    later.round += 1
    third = resolve(later, Move(unit_id=U3, path=path((4, 3), (4, 2), (3, 2))))
    assert len(of(third, SnareTriggered)) == 1


def test_vine_ignores_allies() -> None:
    state, _ = vine_arena()
    result = resolve(give_turn(state, U1), Move(unit_id=U1, path=path((0, 3), (1, 3), (2, 3))))
    assert of(result, SnareTriggered) == []
    assert "prone" not in statuses(result.state, U1)


def test_vine_snares_an_enemy_pushed_next_to_it() -> None:
    from trpg.engine.effects import run_effects  # noqa: PLC0415
    from trpg.engine.effects.models import PushEffect  # noqa: PLC0415

    state, sid = vine_arena()
    state.units[U2].pos = Pos(x=3, y=5)
    result = run_effects(state, [PushEffect(target_id=U2, direction=(0, -1), distance=1)])
    assert result.state.units[U2].xy == (3, 4)
    assert "prone" in statuses(result.state, U2)
    assert any(isinstance(e, SnareTriggered) and e.unit_id == sid for e in result.events)


# ---------------------------------------------------------------------------
# 守護靈
# ---------------------------------------------------------------------------


def guardian_with_wounded_allies() -> tuple[BattleState, UnitId, UnitId]:
    """U1 施放者、守護靈、骷髏戰士（較虛弱）。"""
    state = arena(["skill_summon_guardian_spirit", "skill_raise_skeleton"])
    state, guardian = cast_at(state, "skill_summon_guardian_spirit", 2, 3)
    state, skeleton = cast_at(give_turn(state, U1), "skill_raise_skeleton", 1, 3, "summon")
    return state, guardian, skeleton


def test_guardian_shields_the_weakest_ally_including_summons() -> None:
    state, guardian, skeleton = guardian_with_wounded_allies()
    state.units[U1].hp = state.units[U1].max_hp - 1
    state.units[skeleton].hp = state.units[skeleton].max_hp // 2  # 最虛弱：骷髏
    ctx = pulse(state, guardian)
    assert "shielded" in statuses(ctx.state, skeleton)
    assert "shielded" not in statuses(ctx.state, U1)
    assert weakest_ally(state, state.units[guardian]) is state.units[skeleton]


def test_guardian_shields_the_owner_when_the_owner_is_weakest() -> None:
    state, guardian, skeleton = guardian_with_wounded_allies()
    state.units[U1].hp = 3
    ctx = pulse(state, guardian)
    assert "shielded" in statuses(ctx.state, U1)
    assert "shielded" not in statuses(ctx.state, skeleton)


def test_guardian_never_shields_itself_and_ties_break_by_hp_then_id() -> None:
    state, guardian, _ = guardian_with_wounded_allies()
    state.units[guardian].hp = 1
    chosen = weakest_ally(state, state.units[guardian])
    assert chosen is not None and chosen.id != guardian
    # 全員滿血：HP 較少者（骷髏 20 < 法師）；再來依 ID
    state.units[guardian].hp = state.units[guardian].max_hp
    lowest = min(
        (u for u in state.living_units() if u.team is Team.ALLY and u.id != guardian),
        key=lambda u: (u.hp, u.id),
    )
    chosen = weakest_ally(state, state.units[guardian])
    assert chosen is not None and chosen.hp == lowest.hp


def test_guardian_pulse_runs_at_the_start_of_its_turn() -> None:
    state, guardian, _ = guardian_with_wounded_allies()
    state.units[U1].hp = 3
    ctx = Ctx(state.clone())
    start_turn(ctx, guardian)
    assert "shielded" in statuses(ctx.state, U1)


# ---------------------------------------------------------------------------
# 吸引圖騰
# ---------------------------------------------------------------------------


def pull_arena(
    foes: tuple[tuple[int, int], ...] = ((3, 5),),
) -> tuple[BattleState, UnitId]:
    return summoned("skill_summon_pull_totem", (3, 3), foes=foes)


def test_pull_totem_has_no_actions() -> None:
    state, sid = pull_arena()
    ctx = Ctx(state.clone())
    start_turn(ctx, sid)
    assert ctx.state.units[sid].ap == 0


def test_pull_totem_pulls_the_nearest_enemy_one_tile() -> None:
    state, sid = pull_arena(((3, 5), (5, 3)))
    ctx = pulse(state, sid)
    # 兩個敵人距離相同（2）：依座標 (y, x) 先 (5, 3)（y 較小）
    assert ctx.state.units[U3].xy == (4, 3)
    assert ctx.state.units[U2].xy == (3, 5)
    [event] = [e for e in ctx.events if isinstance(e, SummonPulled)]
    assert (event.unit_id, event.target_id) == (sid, U3)


def test_pull_totem_only_pulls_within_two_tiles() -> None:
    state, sid = pull_arena(((3, 6),))
    ctx = pulse(state, sid)
    assert ctx.state.units[U2].xy == (3, 6)
    assert not [e for e in ctx.events if isinstance(e, SummonPulled)]


def test_pull_totem_skips_blocked_and_adjacent_enemies() -> None:
    # U2 已經相鄰（拉不動）、U3 在 (3, 5) 但前面 (3, 4) 被 U2 擋住 → 沒有人被拉
    state, sid = pull_arena(((3, 4), (3, 5)))
    ctx = pulse(state, sid)
    assert ctx.state.units[U2].xy == (3, 4) and ctx.state.units[U3].xy == (3, 5)
    assert not [e for e in ctx.events if isinstance(e, SummonPulled)]


def test_pull_totem_pulls_enemies_into_fire() -> None:
    state, sid = pull_arena()
    state.set_tile(3, 4, replace(state.tile(3, 4), surface=Surface.FIRE, surface_remaining=3))
    ctx = pulse(state, sid)
    assert ctx.state.units[U2].xy == (3, 4)
    assert "burning" in statuses(ctx.state, U2)  # 拉進火裡照常結算


def test_pull_totem_does_not_pull_allies() -> None:
    state, sid = pull_arena()
    state.units[U1].pos = Pos(x=3, y=5)
    ctx = pulse(state, sid)
    assert ctx.state.units[U1].xy == (3, 5)


# ---------------------------------------------------------------------------
# 高台圖騰
# ---------------------------------------------------------------------------


def test_plateau_totem_raises_the_tile_nearest_the_owner() -> None:
    state, sid = summoned("skill_summon_plateau_totem", (2, 3))
    assert state.tile(1, 3).height == 1  # 離施放者 (0, 3) 最近的相鄰格
    assert state.units[sid].platform_pos == Pos(x=1, y=3)
    others = [state.tile(x, y).height for y in range(7) for x in range(7) if (x, y) != (1, 3)]
    assert set(others) == {0}


def test_plateau_is_restored_when_the_totem_expires() -> None:
    state, sid = summoned("skill_summon_plateau_totem", (2, 3))
    ctx = Ctx(state.clone())
    ctx.state.units[sid].summon_expires_round = ctx.state.round
    ctx.state.active_unit = U1
    end_turn(ctx)
    assert ctx.state.units[sid].dismissed
    assert ctx.state.tile(1, 3).height == 0
    assert any(isinstance(e, TerrainChanged) and e.height_after == 0 for e in ctx.events)


def test_plateau_is_restored_when_the_totem_is_downed() -> None:
    state, sid = summoned("skill_summon_plateau_totem", (2, 3))
    ctx = Ctx(state.clone())
    down_unit(ctx, ctx.state.units[sid])
    assert ctx.state.tile(1, 3).height == 0
    assert ctx.state.units[sid].platform_pos is None


def test_plateau_is_restored_when_the_owner_is_downed() -> None:
    state, _ = summoned("skill_summon_plateau_totem", (2, 3))
    ctx = Ctx(state.clone())
    down_unit(ctx, ctx.state.units[U1])
    assert ctx.state.tile(1, 3).height == 0


def test_plateau_picks_a_free_neighbour_and_survives_no_site() -> None:
    state = arena(["skill_summon_plateau_totem"])
    # (2, 3) 四周都被佔住（單位或牆）：沒有高台，也不報錯
    walled = state.clone()
    walled.units[U2].pos = Pos(x=1, y=3)
    for xy in ((3, 3), (2, 2), (2, 4)):
        walled.set_tile(*xy, replace(walled.tile(*xy), terrain="wall"))
    walled, sid = cast_at(walled, "skill_summon_plateau_totem", 2, 3)
    assert walled.units[sid].platform_pos is None
    # (1, 3) 有單位時改用別的相鄰格
    blocked = state.clone()
    blocked.units[U2].pos = Pos(x=1, y=3)
    blocked, sid = cast_at(blocked, "skill_summon_plateau_totem", 2, 3)
    site = blocked.units[sid].platform_pos
    assert site is not None and site != Pos(x=1, y=3)
    assert blocked.tile(site.x, site.y).height == 1


def test_plateau_can_be_climbed() -> None:
    state, _ = summoned("skill_summon_plateau_totem", (2, 3))
    moves = reachable_tiles(give_turn(state, U1), U1)
    assert Pos(x=1, y=3) in moves and moves[Pos(x=1, y=3)] == 2  # 往上 1 層：成本 1 + 額外 1


# ---------------------------------------------------------------------------
# 鷹隼飛行
# ---------------------------------------------------------------------------

HEIGHTS = "\n".join(["0003000", "0003000", "0003000", "0003000", "0003000", "0003000", "0003000"])
TERRAIN = "\n".join(["...x...", "...#...", "...x...", "...#...", "...x...", "...#...", "...x..."])


def hawk_arena() -> tuple[BattleState, UnitId]:
    """中間一條 (x = 3) 的牆／深淵、高度 3 的帶子；鷹隼與施放者在左邊，敵人在右邊。"""
    m = make_map(HEIGHTS, TERRAIN, ally=[(0, 3)], enemy=[(6, 3)])
    spawns = [
        spawn(Team.ALLY, (0, 3), caster_template(["skill_summon_hawk"])),
        spawn(Team.ENEMY, (6, 3), no_reactions(max_hp=300)),
    ]
    state = give_turn(make_state(m, spawns), U1)
    return cast_at(state, "skill_summon_hawk", 2, 3)


def test_hawk_flies_over_walls_chasms_and_height_differences() -> None:
    state, hawk = hawk_arena()
    unit = give_turn(state, hawk)
    reach = reachable_tiles(unit, hawk)
    assert Pos(x=4, y=3) in reach  # 越過牆／深淵／高度差
    assert Pos(x=3, y=2) not in reach  # 但不能停在深淵或牆裡
    assert Pos(x=3, y=3) not in reach and Pos(x=3, y=4) not in reach
    assert all(cost == abs(p.x - 2) + abs(p.y - 3) for p, cost in reach.items())


def test_hawk_cannot_end_a_move_inside_a_wall() -> None:
    state, hawk = hawk_arena()
    unit = give_turn(state, hawk)
    with pytest.raises(IllegalActionError):
        resolve(unit, Move(unit_id=hawk, path=path((2, 3), (3, 3))))
    result = resolve(unit, Move(unit_id=hawk, path=path((2, 3), (3, 3), (4, 3))))
    assert result.state.units[hawk].xy == (4, 3)
    assert find_path(unit, hawk, Pos(x=3, y=3)) is None


def test_a_walker_cannot_do_the_same() -> None:
    state, _ = hawk_arena()
    walker = give_turn(state, U1)
    reach = reachable_tiles(walker, U1)
    assert Pos(x=4, y=3) not in reach


def test_hawk_is_not_affected_by_surfaces() -> None:
    state, hawk = hawk_arena()
    fire = state.clone()
    fire.set_tile(2, 3, replace(fire.tile(2, 3), surface=Surface.FIRE, surface_remaining=3))
    ctx = Ctx(fire)
    start_turn(ctx, hawk)
    assert "burning" not in statuses(ctx.state, hawk)
    walker = Ctx(fire.clone())
    walker.state.units[U1].pos = Pos(x=2, y=3)
    walker.state.units[hawk].pos = Pos(x=1, y=3)
    start_turn(walker, U1)
    assert "burning" in statuses(walker.state, U1)  # 同一格，會走路的照常著火


def test_hawk_enemy_still_blocks_the_path() -> None:
    state, hawk = hawk_arena()
    blocked = give_turn(state, hawk)
    blocked.units[U2].pos = Pos(x=3, y=3)  # 敵人站在牆格（測試用）擋住直線
    with pytest.raises(IllegalActionError):
        resolve(blocked, Move(unit_id=hawk, path=path((2, 3), (3, 3), (4, 3))))


def test_hawk_marks_and_reveals_as_before() -> None:
    template = library().ruleset.summon_def("summon_hawk").template
    assert template.innate == "marked" and "flying" in template.tags
    assert any(r.status == "revealed" for r in template.hit_rules)


def test_hawk_legal_moves_include_the_far_side() -> None:
    state, hawk = hawk_arena()
    moves = [a for a in legal_actions(give_turn(state, hawk)) if isinstance(a, Move) and a.path]
    assert any(a.path[-1] == Pos(x=4, y=3) for a in moves)


# ---------------------------------------------------------------------------
# 灌注失效紀錄
# ---------------------------------------------------------------------------


def infused_summon() -> tuple[BattleState, UnitId]:
    state, sid = summoned("skill_summon_guardian_spirit")
    state.units[sid].infused_skill = InfusedSkill(
        skill_id="skill_summon_guardian_spirit",
        owner_id=U1,
        attributes=((Attribute.WIS, 14),),
        round=state.round,
    )
    return state, sid


def test_downing_an_infused_summon_logs_a_fizzle_line() -> None:
    state, sid = infused_summon()
    ctx = Ctx(state.clone())
    down_unit(ctx, ctx.state.units[sid])
    [event] = [e for e in ctx.events if isinstance(e, InfusionFizzled)]
    assert (event.unit_id, event.reason) == (sid, "downed")
    assert ctx.state.units[sid].infused_skill is None
    line = describe_event(event, ctx.state)
    assert line is not None and "灌注技能失效" in line and "召喚守護靈" in line


def test_a_vanishing_infused_summon_logs_a_fizzle_line() -> None:
    state, sid = infused_summon()
    ctx = Ctx(state.clone())
    dismiss_summon(ctx, ctx.state.units[sid], "expired")
    [event] = [e for e in ctx.events if isinstance(e, InfusionFizzled)]
    assert event.reason == "gone"
    assert "灌注技能失效" in (describe_event(event, ctx.state) or "")


def test_no_fizzle_line_without_a_pending_infusion() -> None:
    state, sid = summoned("skill_summon_guardian_spirit")
    ctx = Ctx(state.clone())
    down_unit(ctx, ctx.state.units[sid])
    assert not [e for e in ctx.events if isinstance(e, InfusionFizzled)]


def test_owner_downed_logs_a_fizzle_line_for_each_infused_summon() -> None:
    state, sid = infused_summon()
    ctx = Ctx(state.clone())
    down_unit(ctx, ctx.state.units[U1])
    assert [e.unit_id for e in ctx.events if isinstance(e, InfusionFizzled)] == [sid]


# ---------------------------------------------------------------------------
# 確定性
# ---------------------------------------------------------------------------


def test_same_seed_and_inputs_give_the_same_battle() -> None:
    def run() -> tuple[tuple[int, ...], tuple[str, ...]]:
        state, sid = pull_arena(((3, 5), (5, 3)))
        ctx = pulse(state, sid)
        return (
            tuple(u.hp for u in ctx.state.units_sorted()),
            tuple(type(e).__name__ for e in ctx.events),
        )

    assert run() == run()


def test_summoned_events_carry_the_new_templates() -> None:
    for skill_id, (template_id, _) in NEW_SKILLS.items():
        result = resolve(
            arena([skill_id]),
            UseSkill(unit_id=U1, skill_id=skill_id, target_pos=Pos(x=2, y=3)),
        )
        [event] = of(result, UnitSummoned)
        assert event.template_id == template_id
