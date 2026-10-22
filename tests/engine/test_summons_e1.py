"""17 種召喚物（一）＋灌注關鍵字補齊（Phase 3-33e1，``docs/design/06-技能.md`` 6.29.1、6.29.5）：
10 個灌注關鍵字各自生效、9 種召喚物（火靈、冰靈、雷靈、水精、骷髏戰士、影魅、鷹隼、
戰意圖騰、殘影分身）
的特性情境、召喚技能的關鍵字與預算。"""

from __future__ import annotations

from collections.abc import Sequence
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
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, of
from tests.engine.test_summon_growth import arena, cast_at
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.context import Ctx
from trpg.engine.effects.models import ApplyStatusEffect
from trpg.engine.events import ManeuverRolled, UnitSummoned
from trpg.engine.infusion import active_keywords
from trpg.engine.rules.statuses import status_attack_bonus
from trpg.engine.summons import pulse_summon
from trpg.engine.turns import start_turn
from trpg.engine.weapon_traits import apply_hit_traits, attack_dice, chain_targets, height_permille
from trpg.shared.types import Pos, Surface, Team, UnitId
from trpg.skillgen.budget import skill_budget

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))

# 召喚技能 → 範本 → 灌注對照（6.29.5）
NEW_SKILLS = {
    "skill_summon_fire_spirit": ("summon_fire_spirit", "ignite"),
    "skill_summon_ice_spirit": ("summon_ice_spirit", "frozen"),
    "skill_summon_thunder_spirit": ("summon_thunder_spirit", "charged"),
    "skill_summon_water_sprite": ("summon_water_sprite", "wet"),
    "skill_summon_shade": ("summon_shade", "concealed"),
    "skill_summon_hawk": ("summon_hawk", "marked"),
}
TEN_KEYWORDS = {
    "ignite",
    "frozen",
    "marked",
    "collision",
    "wet",
    "charged",
    "prone",
    "high_ground",
    "concealed",
    "summon",
}


def summoned(
    skill_id: str, *, foes: Sequence[tuple[int, int]] = ((3, 3),)
) -> tuple[BattleState, UnitId]:
    """U1 施放 ``skill_id``，召喚物在 (2, 3)；敵人在 ``foes``（U2 起）。"""
    return cast_at(arena([skill_id], foes=foes), skill_id, 2, 3)


def water_at(state: BattleState, xy: tuple[int, int]) -> None:
    state.set_tile(*xy, replace(state.tile(*xy), surface=Surface.WATER, surface_remaining=3))


def hit(state: BattleState, sid: UnitId, target: UnitId = U2) -> Ctx:
    """召喚物 ``sid`` 的普攻命中 ``target`` 後的特性結算（回傳結算後的環境）。"""
    ctx = Ctx(state.clone())
    apply_hit_traits(ctx, ctx.state.units[sid], ctx.state.units[target])
    return ctx


# ---------------------------------------------------------------------------
# 灌注關鍵字：10 個都有對照，各自生效
# ---------------------------------------------------------------------------


def test_the_infusion_table_covers_all_ten_keywords() -> None:
    table = library().ruleset.core.summon_infusions
    assert set(table) == TEN_KEYWORDS
    assert {k.id for k in library().ruleset.keywords.keywords} == TEN_KEYWORDS


def test_wet_creates_water_on_the_target_tile() -> None:
    state, sid = cast_at(
        arena(["skill_summon_tide", "skill_raise_skeleton"]), "skill_raise_skeleton", 2, 3, "summon"
    )
    state.units[sid].infusion = "wet"
    ctx = hit(state, sid)
    assert ctx.state.tile(*ctx.state.units[U2].xy).surface is Surface.WATER


def test_charged_adds_lightning_damage() -> None:
    state, sid = summoned("skill_summon_fire_spirit")
    state.units[sid].infusion = "charged"
    before = state.units[U2].hp
    ctx = hit(state, sid)
    assert ctx.state.units[U2].hp < before
    assert any(getattr(e, "element", None) == "lightning" for e in ctx.events)


def test_prone_trips_once_per_round() -> None:
    state, sid = summoned("skill_raise_skeleton")  # 骷髏戰士固有「倒地」
    assert "prone" in active_keywords(state, state.units[sid])
    state = with_rolls(state, [(20, 19)])
    ctx = hit(state, sid)
    assert ctx.state.units[U2].has_status("prone")
    assert ctx.state.units[sid].trip_round == ctx.state.round
    assert len(of_events(ctx, ManeuverRolled)) == 1
    # 同一輪第二次命中：不再擲絆倒（即使目標已站起來）
    again = ctx.state.clone()
    again.units[U2].statuses = [s for s in again.units[U2].statuses if s.status_id != "prone"]
    second = Ctx(again)
    apply_hit_traits(second, second.state.units[sid], second.state.units[U2])
    assert of_events(second, ManeuverRolled) == []
    # 下一輪恢復
    later = ctx.state.clone()
    later.round += 1
    later.units[U2].statuses = [s for s in later.units[U2].statuses if s.status_id != "prone"]
    third = Ctx(later)
    apply_hit_traits(third, third.state.units[sid], third.state.units[U2])
    assert len(of_events(third, ManeuverRolled)) == 1


def of_events(ctx: Ctx, kind: type) -> list:  # type: ignore[type-arg]
    return [e for e in ctx.events if isinstance(e, kind)]


def test_high_ground_adds_damage_only_when_higher_than_the_target() -> None:
    state, sid = summoned("skill_summon_fire_spirit")
    state.units[sid].infusion = "high_ground"
    assert height_permille(state, state.units[sid], state.units[U2]) == 0
    high = state.clone()
    high.set_tile(*high.units[sid].xy, replace(high.tile(*high.units[sid].xy), height=1))
    assert height_permille(high, high.units[sid], high.units[U2]) == 250
    low = state.clone()
    low.set_tile(*low.units[U2].xy, replace(low.tile(*low.units[U2].xy), height=1))
    assert height_permille(low, low.units[sid], low.units[U2]) == 0


def test_concealed_infusion_conceals_the_summon_for_two_rounds() -> None:
    skill = "skill_summon_shade"
    state, sid = cast_at(arena([skill, "skill_raise_skeleton"]), skill, 2, 3)
    status = next(s for s in state.units[sid].statuses if s.status_id == "concealed")
    assert status.remaining == 2


def test_summon_infusion_adds_twenty_percent_hp() -> None:
    base, bid = cast_at(arena(["skill_raise_skeleton"]), "skill_raise_skeleton", 2, 3, "prone")
    boosted, sid = cast_at(arena(["skill_raise_skeleton"]), "skill_raise_skeleton", 2, 3, "summon")
    assert boosted.units[sid].max_hp == base.units[bid].max_hp * 12 // 10
    assert boosted.units[sid].hp == boosted.units[sid].max_hp


def test_a_chosen_infusion_that_equals_the_innate_one_counts_once() -> None:
    state, sid = cast_at(
        arena(["skill_summon_fire_spirit"]), "skill_summon_fire_spirit", 2, 3, "ignite"
    )
    assert active_keywords(state, state.units[sid]) == ("ignite",)
    plain, pid = cast_at(
        arena(["skill_summon_fire_spirit"]), "skill_summon_fire_spirit", 2, 3, "summon"
    )
    assert active_keywords(plain, plain.units[pid]) == ("ignite", "summon")


# ---------------------------------------------------------------------------
# 召喚技能：關鍵字、預算、圖示、AI
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("skill_id", "expected"), NEW_SKILLS.items())
def test_new_summon_skills_have_their_keyword_and_pass_the_budget(
    skill_id: str, expected: tuple[str, str]
) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    keywords = lib.ruleset.skill_keywords(skill)
    assert expected[1] in keywords.makes and "summon" in keywords.makes
    assert skill_budget(skill, lib).ok
    assert [e.unit for e in skill.effects] == [expected[0]]
    assert expected[0] in lib.ruleset.summons.by_id()


def test_hawk_skill_makes_marked_and_high_ground() -> None:
    lib = library()
    makes = lib.ruleset.skill_keywords(lib.skills["skill_summon_hawk"]).makes
    assert {"marked", "high_ground"} <= set(makes)


def test_the_skeleton_skill_now_makes_prone() -> None:
    lib = library()
    assert "prone" in lib.ruleset.skill_keywords(lib.skills["skill_raise_skeleton"]).makes


def test_ai_casts_the_new_summon_skills() -> None:
    ai = UtilityAI(library().ai_profiles)
    for skill_id in NEW_SKILLS:
        state = arena([skill_id], foes=((6, 6),))
        scored = [s for s in ai.rank(state) if isinstance(s.action, UseSkill) and s.score > 0]
        assert scored, skill_id  # 召喚是有收益的動作


# ---------------------------------------------------------------------------
# 各召喚物的特性
# ---------------------------------------------------------------------------


def test_fire_spirit_burns_its_target() -> None:
    state, sid = summoned("skill_summon_fire_spirit")
    assert hit(state, sid).state.units[U2].has_status("burning")


def test_ice_spirit_slows_and_freezes_targets_standing_in_water() -> None:
    state, sid = summoned("skill_summon_ice_spirit")
    dry = hit(state, sid).state.units[U2]
    assert dry.has_status("slow") and not dry.has_status("frozen")
    wet = state.clone()
    water_at(wet, wet.units[U2].xy)
    assert hit(wet, sid).state.units[U2].has_status("frozen")


def test_thunder_spirit_chains_through_water_only_when_standing_in_it() -> None:
    state, sid = summoned("skill_summon_thunder_spirit", foes=((3, 3), (3, 4)))
    before = state.units[U3].hp
    assert hit(state, sid).state.units[U3].hp == before  # 沒站在水裡：不連鎖
    wet = state.clone()
    water_at(wet, wet.units[sid].xy)
    ctx = hit(wet, sid)
    assert ctx.state.units[U3].hp < before
    rule = library().ruleset.summon_def("summon_thunder_spirit").template.hit_rules[0]
    assert [u.id for u in chain_targets(wet, wet.units[sid], wet.units[U2], rule)] == [U3]


def test_water_sprite_makes_water_and_heals_adjacent_allies_each_turn() -> None:
    state, sid = summoned("skill_summon_water_sprite")
    ctx = Ctx(state.clone())
    pulse_summon(ctx, ctx.state.units[sid])
    assert ctx.state.tile(*ctx.state.units[sid].xy).surface is Surface.WATER


def test_water_sprite_pulse_reaches_only_adjacent_wounded_allies() -> None:
    state, sid = cast_at(arena(["skill_summon_water_sprite"]), "skill_summon_water_sprite", 1, 3)
    far = cast_at(arena(["skill_summon_water_sprite"]), "skill_summon_water_sprite", 4, 3)
    for s, unit_id, adjacent in ((state, sid, True), (far[0], far[1], False)):
        s.units[U1].hp -= 10
        start = s.units[U1].hp
        ctx = Ctx(s.clone())
        pulse_summon(ctx, ctx.state.units[unit_id])
        assert (ctx.state.units[U1].hp > start) is adjacent


def test_water_sprite_pulse_runs_at_the_start_of_its_turn() -> None:
    state, sid = cast_at(arena(["skill_summon_water_sprite"]), "skill_summon_water_sprite", 1, 3)
    state.units[U1].hp -= 10
    start = state.units[U1].hp
    ctx = Ctx(state.clone())
    ctx.state.active_unit = sid
    ctx.state.turn_pos = ctx.state.turn_order.index(sid)
    start_turn(ctx, sid)
    assert ctx.state.units[U1].hp > start


def test_skeleton_warrior_trips_with_its_shield_bash() -> None:
    state, sid = summoned("skill_raise_skeleton")
    state = with_rolls(state, [(20, 19)])
    assert hit(state, sid).state.units[U2].has_status("prone")


def test_shade_starts_concealed_and_stabs_harder_from_behind() -> None:
    state, sid = summoned("skill_summon_shade")
    shade = state.units[sid]
    assert shade.has_status("concealed")
    assert attack_dice(state, shade, backstab=True).count == attack_dice(state, shade).count + 2


def test_hawk_marks_and_reveals_its_target_and_is_fast() -> None:
    state, sid = summoned("skill_summon_hawk")
    assert state.units[sid].speed == 7
    state.units[U2].statuses = []
    concealed = state.clone()
    ctx = Ctx(concealed)
    execute_conceal = ApplyStatusEffect(target_id=U2, status_id="concealed", duration=2)
    from trpg.engine.effects import execute  # noqa: PLC0415

    execute(ctx, [execute_conceal])
    apply_hit_traits(ctx, ctx.state.units[sid], ctx.state.units[U2])
    target = ctx.state.units[U2]
    assert target.has_status("marked") and target.has_status("revealed")


def test_war_totem_gives_rallied_to_allies_and_other_summons_within_two() -> None:
    state, tid = cast_at(
        arena(["skill_plant_totem", "skill_raise_skeleton"]), "skill_plant_totem", 1, 3
    )
    skeleton_state = resolve(
        give_turn(state, U1),
        UseSkill(unit_id=U1, skill_id="skill_raise_skeleton", target_pos=Pos(x=2, y=2)),
    ).state
    skeleton = next(
        u for u in skeleton_state.units.values() if u.template_id == "summon_skeleton_warrior"
    )
    ctx = Ctx(skeleton_state.clone())
    from trpg.engine.summons import pulse_totem  # noqa: PLC0415

    pulse_totem(ctx, ctx.state.units[tid])
    rules = ctx.state.ruleset
    assert ctx.state.units[U1].has_status("rallied")
    assert ctx.state.units[skeleton.id].has_status("rallied")
    assert status_attack_bonus(rules, ctx.state.units[U1]) == 1
    assert not ctx.state.units[U2].has_status("rallied")


def test_rallied_raises_the_attack_value_by_one() -> None:
    from trpg.engine.rules.combat import attack_value  # noqa: PLC0415

    state, _ = summoned("skill_summon_fire_spirit")
    ctx = Ctx(state.clone())
    base = attack_value(ctx.state.units[U1], ctx.state.ruleset)
    from trpg.engine.effects import execute  # noqa: PLC0415

    execute(ctx, [ApplyStatusEffect(target_id=U1, status_id="rallied", duration=2)])
    assert attack_value(ctx.state.units[U1], ctx.state.ruleset) == base + 1


def test_afterimage_keeps_its_look_fields() -> None:
    look = library().ruleset.summon_def("summon_afterimage").template.look
    assert look is not None
    assert (look.body, look.variant, look.trait) == ("humanoid", "afterimage", "translucent")


def test_all_new_templates_have_default_modes_and_looks() -> None:
    summons = library().ruleset.summons.by_id()
    for template_id, mode in (
        ("summon_water_sprite", "guard"),
        ("summon_war_totem", "hold"),
        ("summon_fire_spirit", "follow"),
        ("summon_shade", "follow"),
    ):
        assert summons[template_id].template.default_mode == mode
    for summon in summons.values():
        assert summon.template.look is not None, summon.id


def test_same_seed_and_inputs_give_the_same_battle() -> None:
    def run() -> tuple[int, ...]:
        state, sid = summoned("skill_summon_thunder_spirit", foes=((3, 3), (3, 4)))
        water_at(state, state.units[sid].xy)
        ctx = hit(state, sid)
        return tuple(u.hp for u in ctx.state.units_sorted())

    assert run() == run()


def test_summoned_events_carry_the_innate_template() -> None:
    state = arena(["skill_summon_ice_spirit"])
    result = resolve(
        state, UseSkill(unit_id=U1, skill_id="skill_summon_ice_spirit", target_pos=Pos(x=2, y=3))
    )
    [event] = of(result, UnitSummoned)
    assert event.template_id == "summon_ice_spirit"


def test_make_map_helpers_are_importable() -> None:
    # 保持 helpers 的匯入被使用（make_map／caster_template／no_reactions／spawn／make_state／FLAT7）
    m = make_map(FLAT7, ally=[(0, 3)], enemy=[(6, 6)])
    state = make_state(
        m,
        [spawn(Team.ALLY, (0, 3), caster_template([])), spawn(Team.ENEMY, (6, 6), no_reactions())],
    )
    assert len(state.units) == 2


def test_summon_only_weapons_are_not_start_weapons() -> None:
    from trpg.roguelite.start import start_weapons  # noqa: PLC0415

    lib = library()
    only = {w for w, d in lib.weapons.items() if d.summon_only}
    assert only == {
        "spark_staff",
        "water_jet",
        "shade_blades",
        "talons",
        # 3-33e2b
        "vine_lash",
        "guardian_rod",
        "totem_stone",
        # 3-33e2a
        "bomb_casing",
        "stone_fist",
        "fangs",
    }
    assert only.isdisjoint(start_weapons(lib))
    for summon in lib.ruleset.summons.summons:  # 召喚物範本用的武器都存在
        assert summon.template.weapon in lib.weapons


def test_innate_summons_keep_their_own_element_colour_in_the_view() -> None:
    from trpg.engine.view import _summon_look  # noqa: PLC0415

    state, sid = cast_at(
        arena(["skill_summon_fire_spirit"]), "skill_summon_fire_spirit", 2, 3, "summon"
    )
    assert state.units[sid].infusion == "summon"
    look = _summon_look(state, state.units[sid])
    assert look is not None and look.element == "ignite"
