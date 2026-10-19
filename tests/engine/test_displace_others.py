"""位移他人（Phase 3D-2b）：``teleport_target``（傳送他人）、``swap_any``（任意兩者互換）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import BattleState, ResolveResult, UseSkill, legal_actions, resolve
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    ManeuverRolled,
    ReactionTriggered,
    SurfaceEntered,
    TrapTriggered,
    UnitFell,
    UnitMoved,
)
from trpg.engine.maneuvers import contest_chance
from trpg.engine.preview import preview
from trpg.engine.skills.scaling import skill_scaling_value
from trpg.engine.state import TrapState
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
TELE = "skill_t_tele"
PAIR = "skill_t_pair"
FLAT = "\n".join(["0000000"] * 7)
PIT = "\n".join(["......." for _ in range(7)])


def of[E: EventBase](events: Sequence[EventBase] | ResolveResult, kind: type[E]) -> list[E]:
    items = events.events if isinstance(events, ResolveResult) else events
    return [e for e in items if isinstance(e, kind)]


def tele_skill(reach: int = 5) -> SkillDef:
    return make_skill(
        TELE, {"type": "unit_then_tile", "range": reach}, [{"type": "teleport_target"}], ap_cost=2
    )


def pair_skill(reach: int = 5) -> SkillDef:
    return make_skill(
        PAIR, {"type": "unit_pair", "range": reach}, [{"type": "swap_any"}], ap_cost=2
    )


def terrain_with(cells: dict[tuple[int, int], str], width: int = 7, height: int = 7) -> str:
    rows = [["."] * width for _ in range(height)]
    for (x, y), ch in cells.items():
        rows[y][x] = ch
    return "\n".join("".join(r) for r in rows)


def arena(
    skill: SkillDef,
    *,
    caster: tuple[int, int] = (0, 3),
    allies: Sequence[tuple[int, int]] = (),
    foes: Sequence[tuple[int, int]] = (),
    foe_tags: Sequence[str] = (),
    reactive: Sequence[int] = (),
    heights: str = FLAT,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    surfaces: Sequence[tuple[int, int, str]] = (),
) -> BattleState:
    """U1 是施放者（我方法師，裝備 ``skill``，INT 與敵人相同：同級）；之後依序是 ``allies``、
    ``foes``（同級法師範本、不反應、HP 200；``reactive`` 列出的敵人保留反應規則）。"""
    m = make_map(
        heights,
        terrain,
        ally=[caster, *allies],
        enemy=list(foes),
        objects=objects,
        surfaces=surfaces,
    )
    spawns = [spawn(Team.ALLY, caster, caster_template([skill.id]))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_mage")) for xy in allies]
    for index, xy in enumerate(foes):
        kwargs: dict[str, Any] = {"max_hp": 200}
        if foe_tags:
            kwargs["tags"] = list(foe_tags)
        foe = template("hero_mage", **kwargs)
        if index not in reactive:
            foe = foe.model_copy(update={"reactions": []})
        spawns.append(spawn(Team.ENEMY, xy, foe))
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def tele(state: BattleState, target: UnitId, x: int, y: int) -> ResolveResult:
    return resolve(
        state, UseSkill(unit_id=U1, skill_id=TELE, target_id=target, target_pos=Pos(x=x, y=y))
    )


def pair(state: BattleState, first: UnitId, second: UnitId) -> ResolveResult:
    return resolve(
        state, UseSkill(unit_id=U1, skill_id=PAIR, target_id=first, second_target_id=second)
    )


def rolled(state: BattleState, natural: int) -> BattleState:
    """下一個 d20 一定是 ``natural``。"""
    return with_rolls(state, [(20, natural)])


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def test_the_primitives_need_their_own_shape_and_must_be_the_only_effect() -> None:
    with pytest.raises(ValueError, match="teleport_target 的形狀必須是 unit_then_tile"):
        make_skill(TELE, {"type": "single", "range": 4}, [{"type": "teleport_target"}])
    with pytest.raises(ValueError, match="必須有對應的位移他人效果"):
        make_skill(PAIR, {"type": "unit_then_tile", "range": 4}, [{"type": "swap_any"}])
    with pytest.raises(ValueError, match="必須有對應的位移他人效果"):
        make_skill(TELE, {"type": "unit_then_tile", "range": 4}, [{"type": "damage"}])
    with pytest.raises(ValueError, match="必須是技能唯一的效果"):
        make_skill(
            TELE,
            {"type": "unit_then_tile", "range": 4},
            [{"type": "teleport_target"}, {"type": "damage"}],
        )


@pytest.mark.parametrize("kind", ["passive", "reaction", "stance"])
def test_displacing_others_is_active_only(kind: str) -> None:
    payload = tele_skill().model_dump(mode="json") | {"kind": kind, "ap_cost": None}
    with pytest.raises(ValueError):
        SkillDef.model_validate(payload)


def test_primitive_shape_restrictions_and_rarity() -> None:
    assert not any("只能搭配形狀" in p for p in _problems(tele_skill()))
    assert not any("只能搭配形狀" in p for p in _problems(pair_skill()))


def test_the_demo_skills_are_valid_and_rare() -> None:
    rules = library().ruleset
    for sid, shape in (("skill_banish", "unit_then_tile"), ("skill_void_swap", "unit_pair")):
        skill = rules.skill_def(sid)
        assert skill.rarity == "rare" and skill.shape.type == shape
    banisher = next(b for b in library().builds.builds if b.id == "build_banisher")
    assert {"skill_banish", "skill_void_swap"} <= set(banisher.hero.skills)


# ---------------------------------------------------------------------------
# teleport_target：選取
# ---------------------------------------------------------------------------


def test_teleport_validates_the_unit_then_the_landing() -> None:
    state = arena(tele_skill(), allies=[(2, 3)], foes=[(3, 1)])
    with pytest.raises(IllegalActionError, match="同時指定 target_id"):
        resolve(state, UseSkill(unit_id=U1, skill_id=TELE, target_id=U2))
    with pytest.raises(IllegalActionError, match="不能傳送自己"):
        tele(state, U1, 1, 3)
    with pytest.raises(IllegalActionError, match="不能指定：direction"):
        resolve(
            state,
            UseSkill(
                unit_id=U1,
                skill_id=TELE,
                target_id=U2,
                target_pos=Pos(x=1, y=1),
                direction="north",
            ),
        )
    with pytest.raises(IllegalActionError, match="不能指定：second_target_id"):
        resolve(
            state,
            UseSkill(
                unit_id=U1,
                skill_id=TELE,
                target_id=U2,
                target_pos=Pos(x=1, y=1),
                second_target_id=U3,
            ),
        )


@pytest.mark.parametrize(
    ("dest", "message"),
    [
        ((3, 1), "已有單位"),  # 落點有單位（敵人）
        ((2, 3), "已有單位"),  # 落點有單位（被傳送者自己的格子）
        ((6, 3), "超出射程"),  # 射程 5：距離 6
        ((4, 4), "不可站立"),  # 木箱擋路（blocks_move）
        ((9, 9), "超出地圖範圍"),
    ],
)
def test_teleport_rejects_bad_landings(dest: tuple[int, int], message: str) -> None:
    state = arena(
        tele_skill(), allies=[(2, 3)], foes=[(3, 1)], objects=[(4, 4, "crate")], terrain=None
    )
    with pytest.raises(IllegalActionError, match=message):
        tele(state, U2, *dest)


def test_teleport_needs_a_line_of_sight_to_the_landing_and_the_unit() -> None:
    state = arena(tele_skill(), allies=[(4, 3)], objects=[(2, 3, "earth_wall")], foes=[(6, 6)])
    with pytest.raises(IllegalActionError, match="視線被阻擋"):
        tele(state, U2, 4, 4)  # 看不到被傳送的單位
    seen = arena(tele_skill(), allies=[(1, 3)], objects=[(2, 3, "earth_wall")], foes=[(6, 6)])
    with pytest.raises(IllegalActionError, match="視線被阻擋"):
        tele(seen, U2, 4, 3)  # 看不到落點


def test_teleport_cannot_target_a_unit_beyond_the_reach() -> None:
    state = arena(tele_skill(3), allies=[(5, 3)], foes=[(6, 6)])
    with pytest.raises(IllegalActionError, match="超出射程"):
        tele(state, U2, 4, 3)


def test_legal_actions_list_every_unit_with_every_legal_landing() -> None:
    state = arena(tele_skill(2), allies=[(2, 3)], foes=[(6, 6)], objects=[(1, 3, "crate")])
    acts = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == TELE]
    assert acts and all(a.target_id == U2 and a.target_pos is not None for a in acts)
    spots = {(a.target_pos.x, a.target_pos.y) for a in acts if a.target_pos is not None}
    assert (1, 3) not in spots  # 木箱
    assert (2, 3) not in spots  # 被傳送者自己的格子
    assert (0, 3) not in spots  # 施放者自己的格子
    assert (0, 2) in spots and (1, 2) in spots and (0, 5) in spots
    keys = [(a.target_id, a.target_pos.y, a.target_pos.x) for a in acts if a.target_pos]
    assert keys == sorted(keys)  # 確定性順序


# ---------------------------------------------------------------------------
# teleport_target：檢定
# ---------------------------------------------------------------------------


def test_teleporting_an_ally_never_rolls_and_always_works() -> None:
    state = arena(tele_skill(), allies=[(2, 3)], foes=[(6, 6)])
    result = tele(state, U2, 3, 1)
    assert not of(result, ManeuverRolled) and not of(result, AttackRolled)
    (moved,) = of(result, UnitMoved)
    assert (moved.unit_id, moved.mode, moved.to_pos) == (U2, "teleported", Pos(x=3, y=1))
    assert result.state.units[U2].xy == (3, 1)


@pytest.mark.parametrize(("natural", "moves"), [(10, False), (11, True)])
def test_an_enemy_resists_with_plus_two_at_the_same_level(natural: int, moves: bool) -> None:
    """同級（修正 0）：d20 + 0 + 熟練 2 − 抵抗 2 ≥ 11，也就是自然骰 ≥ 11 才成功（50%）。"""
    state = arena(tele_skill(), foes=[(2, 3)])
    result = tele(rolled(state, natural), U2, 3, 1)
    (roll,) = of(result, ManeuverRolled)
    assert (roll.maneuver, roll.attacker_id, roll.target_id) == ("teleport", U1, U2)
    assert (roll.natural, roll.modifier, roll.proficiency, roll.resist_bonus) == (natural, 0, 2, 2)
    assert roll.total == natural + 2 - 2 and roll.success is moves
    assert result.state.units[U2].xy == ((3, 1) if moves else (2, 3))
    assert bool(of(result, UnitMoved)) is moves
    assert not of(result, AttackRolled)


@pytest.mark.parametrize(("natural", "moves"), [(18, False), (19, True), (20, True), (1, False)])
def test_a_deadly_landing_is_almost_impossible(natural: int, moves: bool) -> None:
    """落在深淵：目標再加 +8（共 +10），自然 19 與 20 才成功（10%）。"""
    terrain = terrain_with({(4, 3): "x"})
    state = arena(tele_skill(), foes=[(2, 3)], terrain=terrain)
    result = tele(rolled(state, natural), U2, 4, 3)
    (roll,) = of(result, ManeuverRolled)
    assert roll.resist_bonus == 10 and roll.success is moves
    assert result.state.units[U2].alive is not moves  # 掉進深淵就死了


def test_the_success_chances_at_the_same_level_are_60_50_and_10_percent() -> None:
    state = arena(tele_skill(), foes=[(2, 3)])
    caster, foe = state.units[U1], state.units[U2]
    skill = state.ruleset.skill_def(TELE)
    attack = skill_scaling_value(state.ruleset, caster, skill)
    core = state.ruleset.core
    assert (core.teleport_enemy_resist_bonus, core.teleport_lethal_resist_bonus) == (2, 8)
    chance = [contest_chance(state, foe, skill.scaling_attr, attack, b) for b in (0, 2, 10)]
    assert [float(c) for c in chance] == [0.6, 0.5, 0.1]


def test_the_check_scales_with_the_casters_attribute() -> None:
    """施放者的智力比目標高時成功率上升；低很多時只剩自然 20（5%）。"""
    state = arena(tele_skill(), foes=[(2, 3)])
    foe = state.units[U2]
    skill = state.ruleset.skill_def(TELE)
    strong = contest_chance(state, foe, skill.scaling_attr, 40, 10)
    weak = contest_chance(state, foe, skill.scaling_attr, 1, 10)
    assert strong > contest_chance(state, foe, skill.scaling_attr, 16, 10) > weak
    assert float(weak) == 0.05


def test_the_roll_is_deterministic_for_a_fixed_seed() -> None:
    state = arena(tele_skill(), foes=[(2, 3)])
    first = tele(state, U2, 3, 1)
    second = tele(state, U2, 3, 1)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in second.events]


def test_a_fixed_seed_makes_both_a_success_and_a_failure_on_a_normal_tile() -> None:
    """用真的種子（不強制骰子）找到一個成功與一個失敗，之後都是固定結果。"""
    outcomes: dict[bool, int] = {}
    for seed in range(40):
        state = arena(tele_skill(), foes=[(2, 3)])
        state = state.clone()
        state.rng_state = Rng(seed).get_state()
        result = tele(state, U2, 3, 1)
        outcomes.setdefault(of(result, ManeuverRolled)[0].success, seed)
    assert set(outcomes) == {True, False}


# ---------------------------------------------------------------------------
# teleport_target：Boss 與致命地形
# ---------------------------------------------------------------------------


def test_a_boss_cannot_be_sent_into_deadly_terrain() -> None:
    terrain = terrain_with({(4, 3): "x", (4, 4): "~"})
    state = arena(tele_skill(), foes=[(2, 3)], foe_tags=["boss"], terrain=terrain)
    for dest in ((4, 3), (4, 4)):
        with pytest.raises(IllegalActionError, match="Boss，對傳送到致命地形免疫"):
            tele(state, U2, *dest)
    spots = {
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.skill_id == TELE and a.target_pos is not None
    }
    assert (4, 3) not in spots and (4, 4) not in spots and (4, 2) in spots


def test_a_boss_is_checked_normally_on_an_ordinary_tile() -> None:
    state = arena(tele_skill(), foes=[(2, 3)], foe_tags=["boss"])
    ok = tele(rolled(state, 11), U2, 3, 1)
    assert of(ok, ManeuverRolled)[0].resist_bonus == 2 and ok.state.units[U2].xy == (3, 1)
    resisted = tele(rolled(state, 10), U2, 3, 1)
    assert resisted.state.units[U2].xy == (2, 3)


def test_a_non_boss_elite_takes_the_percent_damage_and_is_moved_to_safety() -> None:
    terrain = terrain_with({(4, 3): "~"})
    state = arena(tele_skill(), foes=[(2, 3)], foe_tags=["elite"], terrain=terrain)
    result = tele(rolled(state, 19), U2, 4, 3)
    unit = result.state.units[U2]
    assert unit.alive and unit.xy != (4, 3)
    assert any(d.cause == "deadly_terrain" and d.target_id == U2 for d in of(result, DamageDealt))


def test_an_ordinary_enemy_dies_in_lava_and_an_ally_can_be_sent_there_without_a_roll() -> None:
    terrain = terrain_with({(4, 3): "~"})
    state = arena(tele_skill(), allies=[(2, 2)], foes=[(2, 4)], terrain=terrain)
    killed = tele(rolled(state, 20), U3, 4, 3)
    assert not killed.state.units[U3].alive
    friendly = tele(state, U2, 4, 3)
    assert not of(friendly, ManeuverRolled) and not friendly.state.units[U2].alive


# ---------------------------------------------------------------------------
# teleport_target：落點互動與反應
# ---------------------------------------------------------------------------


def test_the_landing_surface_applies() -> None:
    state = arena(tele_skill(), allies=[(2, 3)], foes=[(6, 6)], surfaces=[(3, 1, "fire")])
    result = tele(state, U2, 3, 1)
    assert [e.unit_id for e in of(result, SurfaceEntered)] == [U2]
    assert any(s.status_id == "burning" for s in result.state.units[U2].statuses)


def test_the_landing_trap_triggers_but_falling_does_not() -> None:
    state = arena(
        tele_skill(),
        allies=[(2, 3)],
        foes=[(6, 6)],
        heights="\n".join(["0000000"] * 3 + ["0030000"] + ["0000000"] * 3),
    )
    state.traps = [
        TrapState(
            owner_id=U3,
            team=Team.ENEMY,
            pos=Pos(x=3, y=1),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U3].attributes.items()),
        )
    ]
    result = tele(state, U2, 3, 1)
    assert [t.unit_id for t in of(result, TrapTriggered)] == [U2]
    assert not of(result, UnitFell)  # 傳送不會墜落（即使從高處到低處）


def test_teleporting_away_does_not_provoke_an_opportunity_attack() -> None:
    state = arena(tele_skill(), allies=[(2, 3)], foes=[(3, 3)], reactive=[0])
    result = tele(state, U2, 2, 1)
    assert not of(result, ReactionTriggered)
    assert result.state.units[U2].xy == (2, 1)


# ---------------------------------------------------------------------------
# swap_any
# ---------------------------------------------------------------------------


def test_swapping_two_allies_never_rolls() -> None:
    state = arena(pair_skill(), allies=[(2, 3), (3, 4)], foes=[(6, 6)])
    result = pair(state, U2, U3)
    assert not of(result, ManeuverRolled) and not of(result, AttackRolled)
    assert result.state.units[U2].xy == (3, 4) and result.state.units[U3].xy == (2, 3)
    assert [m.mode for m in of(result, UnitMoved)] == ["swap", "swap"]


def test_the_caster_does_not_have_to_be_one_of_the_two_and_order_does_not_matter() -> None:
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)])
    a = pair(rolled(state, 15), U3, U2)
    b = pair(rolled(state, 15), U2, U3)
    assert a.state.units[U1].xy == (0, 3)  # 施放者沒動
    assert a.state.units[U2].xy == b.state.units[U2].xy == (3, 4)
    assert a.state.units[U3].xy == b.state.units[U3].xy == (2, 3)


def test_swapping_with_the_caster_works_too() -> None:
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(6, 6)])
    result = pair(state, U1, U2)
    assert result.state.units[U1].xy == (2, 3) and result.state.units[U2].xy == (0, 3)


@pytest.mark.parametrize(("natural", "swaps"), [(8, False), (9, True)])
def test_an_enemy_in_the_pair_rolls_the_ordinary_displacement_check(
    natural: int, swaps: bool
) -> None:
    """一般位移檢定（沒有抵抗加成）：同級自然骰 ≥ 9 成功（60%）。"""
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)])
    result = pair(rolled(state, natural), U2, U3)
    (roll,) = of(result, ManeuverRolled)
    assert (roll.maneuver, roll.target_id, roll.resist_bonus) == ("swap", U3, 0)
    assert roll.success is swaps
    assert (result.state.units[U2].xy == (3, 4)) is swaps


def test_every_enemy_rolls_and_one_resist_fails_the_whole_swap() -> None:
    """兩個敵人各擲一次（依單位 ID）；任一個抵抗成功則整個互換失敗。"""
    state = arena(pair_skill(), foes=[(2, 3), (3, 4)])
    both = pair(with_rolls(state, [(20, 15), (20, 15)]), U2, U3)
    assert [r.success for r in of(both, ManeuverRolled)] == [True, True]
    assert both.state.units[U2].xy == (3, 4) and both.state.units[U3].xy == (2, 3)
    one = pair(with_rolls(state, [(20, 15), (20, 2)]), U2, U3)
    assert [(r.target_id, r.success) for r in of(one, ManeuverRolled)] == [(U2, True), (U3, False)]
    assert one.state.units[U2].xy == (2, 3) and one.state.units[U3].xy == (3, 4)
    assert not of(one, UnitMoved)


def test_swapping_needs_both_tiles_to_be_standable_and_two_distinct_units() -> None:
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)])
    with pytest.raises(IllegalActionError, match="必須不同"):
        pair(state, U2, U2)
    with pytest.raises(IllegalActionError, match="同時指定 target_id 與 second_target_id"):
        resolve(state, UseSkill(unit_id=U1, skill_id=PAIR, target_id=U2))
    with pytest.raises(IllegalActionError, match="不能指定：target_pos"):
        resolve(
            state,
            UseSkill(
                unit_id=U1,
                skill_id=PAIR,
                target_id=U2,
                second_target_id=U3,
                target_pos=Pos(x=1, y=1),
            ),
        )
    broken = state.clone()
    broken.set_tile(2, 3, replace(broken.tile(2, 3), terrain="lava"))
    with pytest.raises(IllegalActionError, match="不能交換位置"):
        pair(broken, U2, U3)


def test_swap_any_needs_sight_and_reach_for_both() -> None:
    state = arena(
        pair_skill(3), allies=[(2, 3)], foes=[(6, 6), (3, 4)], objects=[(1, 3, "earth_wall")]
    )
    with pytest.raises(IllegalActionError, match="視線被阻擋"):
        pair(state, U2, U4)
    far = arena(pair_skill(3), allies=[(2, 3)], foes=[(6, 3)])
    with pytest.raises(IllegalActionError, match="超出射程"):
        pair(far, U2, U3)


def test_legal_actions_list_each_pair_once() -> None:
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)])
    acts = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == PAIR]
    assert [(a.target_id, a.second_target_id) for a in acts] == [(U1, U2), (U1, U3), (U2, U3)]


def test_swapped_units_resolve_their_new_tiles() -> None:
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)], surfaces=[(3, 4, "fire")])
    result = pair(rolled(state, 15), U2, U3)
    entered = of(result, SurfaceEntered)
    assert [e.unit_id for e in entered] == [U2]
    assert any(s.status_id == "burning" for s in result.state.units[U2].statuses)


def test_a_swapped_unit_triggers_a_trap_on_its_new_tile() -> None:
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)])
    state.traps = [
        TrapState(
            owner_id=U3,
            team=Team.ENEMY,
            pos=Pos(x=3, y=4),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U3].attributes.items()),
        )
    ]
    result = pair(state, U2, U1)
    assert of(result, TrapTriggered) == []  # 施放者換到 (2, 3)，沒有陷阱
    swapped = pair(rolled(state, 15), U2, U3)
    assert [t.unit_id for t in of(swapped, TrapTriggered)] == [U2]


def test_a_boss_is_swapped_like_anyone_else_and_never_lands_in_deadly_terrain() -> None:
    """互換要求兩格都能站，所以 Boss 不會被換進致命地形（免疫在這裡是自然成立）；一般格照常檢定。"""
    state = arena(pair_skill(), allies=[(2, 3)], foes=[(3, 4)], foe_tags=["boss"])
    result = pair(rolled(state, 15), U2, U3)
    assert of(result, ManeuverRolled)[0].resist_bonus == 0
    assert result.state.units[U3].xy == (2, 3) and result.state.units[U3].alive


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def test_the_preview_shows_the_success_chance_of_an_ordinary_landing() -> None:
    state = arena(tele_skill(), foes=[(2, 3)])
    p = preview(state, UseSkill(unit_id=U1, skill_id=TELE, target_id=U2, target_pos=Pos(x=3, y=1)))
    (check,) = p.displace_checks
    assert (check.unit_id, check.resist_bonus, check.lethal) == (U2, 2, False)
    assert float(check.chance) == 0.5 and p.displace_chance == check.chance
    assert [(m.kind, m.unit_id, m.path) for m in p.moves] == [("teleport", U2, ((2, 3), (3, 1)))]


def test_the_preview_shows_the_deadly_landing_as_ten_percent() -> None:
    terrain = terrain_with({(4, 3): "x"})
    state = arena(tele_skill(), foes=[(2, 3)], terrain=terrain)
    p = preview(state, UseSkill(unit_id=U1, skill_id=TELE, target_id=U2, target_pos=Pos(x=4, y=3)))
    (check,) = p.displace_checks
    assert check.lethal and check.resist_bonus == 10 and float(check.chance) == 0.1


def test_the_preview_has_no_check_for_allies_and_explains_boss_immunity() -> None:
    state = arena(tele_skill(), allies=[(2, 3)], foes=[(4, 4)], foe_tags=["boss"])
    friendly = preview(
        state, UseSkill(unit_id=U1, skill_id=TELE, target_id=U2, target_pos=Pos(x=3, y=1))
    )
    assert friendly.displace_checks == () and friendly.displace_chance is None
    boss = preview(
        state, UseSkill(unit_id=U1, skill_id=TELE, target_id=U3, target_pos=Pos(x=3, y=1))
    )
    assert any("Boss" in n and "致命地形" in n for n in boss.notes)


def test_the_preview_of_a_pair_multiplies_the_enemy_chances() -> None:
    state = arena(pair_skill(), foes=[(2, 3), (3, 4)])
    p = preview(state, UseSkill(unit_id=U1, skill_id=PAIR, target_id=U2, second_target_id=U3))
    assert [float(c.chance) for c in p.displace_checks] == [0.6, 0.6]
    assert p.displace_chance is not None and float(p.displace_chance) == pytest.approx(0.36)
    assert [m.kind for m in p.moves] == ["swap"]
    friendly = arena(pair_skill(), allies=[(2, 3), (3, 4)], foes=[(6, 6)])
    q = preview(friendly, UseSkill(unit_id=U1, skill_id=PAIR, target_id=U2, second_target_id=U3))
    assert q.displace_checks == () and q.displace_chance is None


def test_the_preview_of_a_swap_skill_shows_the_displacement_check() -> None:
    """3D-2 的 ``swap`` 也改用位移檢定，預覽的成功率就是它。"""
    state = give_turn(
        make_state(
            make_map(FLAT, ally=[(0, 3)], enemy=[(3, 3)]),
            [
                spawn(
                    Team.ALLY, (0, 3), caster_template(["skill_decoy_swap"], base="hero_fighter")
                ),
                spawn(Team.ENEMY, (3, 3), no_reactions(max_hp=200)),
            ],
        ),
        U1,
    )
    p = preview(state, UseSkill(unit_id=U1, skill_id="skill_decoy_swap", target_id=U2))
    assert len(p.displace_checks) == 1 and p.displace_chance == p.displace_checks[0].chance
