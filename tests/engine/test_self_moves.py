"""自身位移（Phase 3D-2）：``dash``（衝鋒）、``leap``（跳躍）、``swap``（交換位置）。"""

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
)
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import BattleState, ResolveResult, UseSkill, legal_actions, resolve
from trpg.engine.events import (
    Collided,
    DamageDealt,
    EffectFizzled,
    EventBase,
    ReactionTriggered,
    StatusApplied,
    TrapTriggered,
    UnitDashed,
    UnitMoved,
)
from trpg.engine.state import TrapState
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
SID = "skill_t_move"
FLAT = "\n".join(["0000000"] * 7)
CHARGE = "skill_tiger_charge"


def of[E: EventBase](events: Sequence[EventBase] | ResolveResult, kind: type[E]) -> list[E]:
    items = events.events if isinstance(events, ResolveResult) else events
    return [e for e in items if isinstance(e, kind)]


def always(monkeypatch: pytest.MonkeyPatch, die: int = 4) -> None:
    """d20 一律 19（命中、不暴擊、檢定與對抗都很高）、其他骰子一律 ``die``。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(die, sides))


def row(width: int, at: dict[int, str]) -> str:
    return "".join(at.get(x, ".") for x in range(width))


def arena(
    skill: SkillDef | str,
    *,
    caster: tuple[int, int] = (0, 3),
    foes: Sequence[tuple[int, int]] = ((4, 3),),
    allies: Sequence[tuple[int, int]] = (),
    heights: str = FLAT,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    surfaces: Sequence[tuple[int, int, str]] = (),
    reactive: Sequence[int] = (),
    base: str = "hero_fighter",
    extra: Sequence[str] = (),
) -> BattleState:
    """U1 是施放者（我方戰士，裝備 ``skill``）；之後依序是 ``allies``、``foes``（預設不反應、
    HP 200；``reactive`` 列出的敵人保留反應規則）。"""
    sid = skill if isinstance(skill, str) else skill.id
    m = make_map(
        heights,
        terrain,
        ally=[caster, *allies],
        enemy=list(foes),
        objects=objects,
        surfaces=surfaces,
    )
    spawns = [spawn(Team.ALLY, caster, caster_template([sid, *extra], base=base))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    for index, xy in enumerate(foes):
        foe = template("bandit", max_hp=200) if index in reactive else no_reactions(max_hp=200)
        spawns.append(spawn(Team.ENEMY, xy, foe))
    defs = [] if isinstance(skill, str) else [skill]
    return give_turn(make_state(m, spawns, skills=defs), U1)


def use(state: BattleState, skill_id: str, **fields: Any) -> ResolveResult:
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))


def charge_skill(*effects: dict[str, Any], reach: int = 4) -> SkillDef:
    return make_skill(
        SID,
        {"type": "single", "range": reach},
        list(effects),
        category="weapon",
        ap_cost=2,
    )


DASH: dict[str, Any] = {"type": "dash"}
HIT: dict[str, Any] = {"type": "damage", "multiplier_permille": 800}
PUSH2: dict[str, Any] = {"type": "push", "distance": 2}


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


def test_dash_must_be_the_first_effect() -> None:
    with pytest.raises(ValueError, match="dash 必須是技能的第一個效果"):
        charge_skill(HIT, DASH)
    assert charge_skill(DASH, HIT).effects[0].type == "dash"


def test_a_skill_has_at_most_one_self_move() -> None:
    with pytest.raises(ValueError, match="最多一個改變自身位置"):
        charge_skill(DASH, {"type": "swap", "affects": "enemies"})


@pytest.mark.parametrize("kind", ["passive", "reaction", "stance"])
def test_self_moves_are_active_only(kind: str) -> None:
    data = make_skill(SID, {"type": "single", "range": 3}, [DASH, HIT], category="weapon")
    payload = data.model_dump(mode="json") | {"kind": kind, "ap_cost": None}
    with pytest.raises(ValueError):
        SkillDef.model_validate(payload)


def test_primitive_shape_and_affects_restrictions() -> None:
    area = make_skill(SID, {"type": "ring", "radius": 1}, [DASH, HIT], category="weapon")
    assert any("dash 只能搭配形狀 single" in p for p in _problems(area))
    far = make_skill(SID, {"type": "single", "range": 3}, [{"type": "leap"}], category="weapon")
    assert any("leap 只能搭配形狀 ground_tile" in p for p in _problems(far))
    both = make_skill(SID, {"type": "single", "range": 3}, [{"type": "swap", "affects": "all"}])
    assert any("swap 不能搭配 affects: all" in p for p in _problems(both))
    mine = make_skill(SID, {"type": "single", "range": 3}, [{"type": "swap", "affects": "self"}])
    assert any("swap 不能搭配 affects: self" in p for p in _problems(mine))


def test_the_demo_skills_are_valid_and_equipped() -> None:
    rules = library().ruleset
    for sid in (CHARGE, "skill_vault_leap", "skill_decoy_swap", "skill_guard_swap"):
        assert rules.skill_def(sid).rarity == "rare"


# ---------------------------------------------------------------------------
# dash
# ---------------------------------------------------------------------------


def test_dash_runs_to_the_tile_beside_the_target_then_resolves_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(charge_skill(DASH, HIT))
    result = use(state, SID, target_id=U2)
    (dashed,) = of(result, UnitDashed)
    assert (dashed.unit_id, dashed.target_id) == (U1, U2)
    assert [(p.x, p.y) for p in dashed.path] == [(0, 3), (1, 3), (2, 3), (3, 3)]
    moves = of(result, UnitMoved)
    assert [(m.mode, m.to_pos.x, m.cost) for m in moves] == [
        ("dash", 1, 0),
        ("dash", 2, 0),
        ("dash", 3, 0),
    ]
    assert result.state.units[U1].xy == (3, 3)
    assert of(result, DamageDealt)[0].target_id == U2
    assert result.state.units[U1].move_points == state.units[U1].move_points  # 不消耗移動點數


def test_dash_to_an_adjacent_target_does_not_move(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena(charge_skill(DASH, HIT), foes=[(1, 3)])
    result = use(state, SID, target_id=U2)
    assert not of(result, UnitMoved) and result.state.units[U1].xy == (0, 3)
    assert of(result, DamageDealt)


def test_dash_counts_as_moving_this_turn() -> None:
    state = arena(charge_skill(DASH, HIT))
    result = use(state, SID, target_id=U2)
    assert result.state.units[U1].moved_this_turn
    leap = arena(_leap_skill())
    assert not use(leap, SID, target_pos=Pos(x=2, y=3)).state.units[U1].moved_this_turn


def test_dash_is_out_of_range_when_the_path_is_longer_than_the_reach() -> None:
    # 目標在射程內（距離 3、看得到），但低牆擋住直線，繞路的成本超過射程 3
    skill = charge_skill(DASH, HIT, reach=3)
    walls = [(1, 3, "low_wall"), (2, 3, "low_wall")]
    state = arena(skill, caster=(0, 3), foes=[(3, 3)], objects=walls)
    with pytest.raises(IllegalActionError, match="無法衝鋒"):
        use(state, SID, target_id=U2)
    assert not [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]


def test_dash_goes_around_an_obstacle_when_the_reach_allows() -> None:
    state = arena(
        charge_skill(DASH, HIT, reach=5),
        caster=(1, 3),
        foes=[(4, 3)],
        objects=[(2, 3, "low_wall")],
    )
    result = use(state, SID, target_id=U2)
    (dashed,) = of(result, UnitDashed)
    assert len(dashed.path) - 1 <= 5 and (2, 3) not in {(p.x, p.y) for p in dashed.path}
    assert abs(result.state.units[U1].pos.x - 4) + abs(result.state.units[U1].pos.y - 3) == 1


def test_dash_does_not_pass_through_any_unit() -> None:
    # 友方站在唯一的走廊上：衝鋒不能穿過（步行可以穿過友方）
    terrain = "\n".join(
        ["#######", "#######", "#######", ".......", "#######", "#######", "#######"]
    )
    state = arena(charge_skill(DASH, HIT), caster=(0, 3), allies=[(2, 3)], terrain=terrain)
    with pytest.raises(IllegalActionError, match="無法衝鋒"):
        use(state, SID, target_id=U3)


def test_dash_is_unavailable_while_rooted_or_prone() -> None:
    state = arena(charge_skill(DASH, HIT))
    for status in ("root", "prone"):
        stuck = state.clone()
        stuck.units[U1].statuses = [_status(status)]
        with pytest.raises(IllegalActionError):
            use(stuck, SID, target_id=U2)
        assert not [a for a in legal_actions(stuck) if getattr(a, "skill_id", "") == SID]


def _status(status_id: str) -> Any:
    from trpg.engine.state import StatusInstance  # noqa: PLC0415

    return StatusInstance(status_id=status_id, remaining=2, source_id=None)


def test_dashing_away_from_an_adjacent_enemy_triggers_an_opportunity_attack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(
        charge_skill(DASH, HIT),
        caster=(0, 3),
        foes=[(4, 3), (0, 2)],  # U3 在施放者旁邊，會對離開的施放者藉機攻擊
        reactive=[1],
    )
    result = use(state, SID, target_id=U2)
    reactions = of(result, ReactionTriggered)
    assert [r.unit_id for r in reactions] == [U3]
    assert any(d.target_id == U1 for d in of(result, DamageDealt))
    assert result.state.units[U1].xy == (3, 3)


def test_dash_triggers_a_trap_on_the_way_and_a_rooting_trap_stops_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(charge_skill(DASH, HIT, PUSH2))
    state.traps = [
        TrapState(
            owner_id=U2,
            team=Team.ENEMY,
            pos=Pos(x=2, y=3),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U2].attributes.items()),
        )
    ]
    result = use(state, SID, target_id=U2)
    assert [t.unit_id for t in of(result, TrapTriggered)] == [U1]
    assert any(s.status_id == "root" and s.target_id == U1 for s in of(result, StatusApplied))
    assert result.state.units[U1].xy == (2, 3)  # 在陷阱格停下
    # 目標不在相鄰格：後續效果都不結算
    assert [e.reason for e in of(result, EffectFizzled)] == ["dash_blocked"]
    assert not [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert result.state.units[U2].xy == (4, 3)


def test_the_dash_target_must_be_a_unit() -> None:
    state = arena(charge_skill(DASH, HIT), objects=[(2, 3, "crate")])
    obj = next(iter(state.objects))
    with pytest.raises(IllegalActionError, match="必須以單位為目標"):
        use(state, SID, target_object_id=obj)


# ---------------------------------------------------------------------------
# 使用者指定的組合：衝鋒 ＋ 傷害 ＋ 擊退 2 格（撞牆觸發撞擊）
# ---------------------------------------------------------------------------


def test_charge_damage_and_push_into_a_wall_triggers_a_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    terrain = "\n".join(
        [".......", ".......", ".......", row(7, {5: "#"}), ".......", ".......", "......."]
    )
    state = arena(CHARGE, caster=(0, 3), foes=[(4, 3)], terrain=terrain)
    result = use(state, CHARGE, target_id=U2)
    # 1. 衝鋒到敵人面前
    assert result.state.units[U1].xy == (3, 3)
    assert of(result, UnitDashed)
    # 2. 造成傷害，3. 再擊退 2 格：牆就在背後，推不動，少走 2 格 = 2 次撞擊傷害
    kinds = [d.cause for d in of(result, DamageDealt)]
    assert kinds == ["attack", "collision", "collision"]
    (hit,) = of(result, Collided)
    assert (hit.unit_id, hit.obstacle, hit.shortfall, hit.source_id) == (U2, "wall", 2, U1)
    assert result.state.units[U2].xy == (4, 3)
    order = [type(e).__name__ for e in result.events]
    assert order.index("UnitDashed") < order.index("AttackRolled") < order.index("Collided")


def test_charge_pushes_the_target_away_from_the_new_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """推擊的原點是衝鋒之後的位置：目標被推離施放者，而不是離開衝鋒前的位置。"""
    always(monkeypatch)
    state = arena(CHARGE, caster=(1, 1), foes=[(3, 3)])  # 施放者從斜角方向衝過去
    result = use(state, CHARGE, target_id=U2)
    caster = result.state.units[U1].xy
    foe = result.state.units[U2].xy
    assert abs(caster[0] - 3) + abs(caster[1] - 3) == 1
    assert (foe[0] - 3, foe[1] - 3) in {(2, 0), (0, 2), (-2, 0), (0, -2)}
    # 方向與衝鋒最後一步一致：目標在施放者的正前方
    assert (foe[0] - caster[0] == 0) or (foe[1] - caster[1] == 0)


def test_a_blocked_charge_resolves_nothing_after_it(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena(CHARGE, foes=[(4, 3)])
    state.traps = [
        TrapState(
            owner_id=U2,
            team=Team.ENEMY,
            pos=Pos(x=1, y=3),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U2].attributes.items()),
        )
    ]
    result = use(state, CHARGE, target_id=U2)
    assert result.state.units[U1].xy == (1, 3)
    assert [e.reason for e in of(result, EffectFizzled)] == ["dash_blocked"]
    assert not [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert not of(result, Collided)
    assert result.state.units[U2].xy == (4, 3) and result.state.units[U2].hp == 200


def test_the_charge_demo_skill_is_in_the_random_composers_reach() -> None:
    from trpg.skillgen.composer_parts import _composable  # noqa: PLC0415, F401

    rules = library().ruleset
    displace = library().skeletons["displace"]
    assert "dash" in (displace.secondary.primitives or ())
    assert "dash" in (library().skeletons["strike"].secondary.primitives or ())
    assert rules.primitive_def("dash").harmful


# ---------------------------------------------------------------------------
# leap
# ---------------------------------------------------------------------------


def _leap_skill(reach: int = 3) -> SkillDef:
    return make_skill(
        SID,
        {"type": "ground_tile", "range": reach},
        [{"type": "leap"}],
        category="weapon",
    )


def test_leap_jumps_over_units_to_an_empty_tile() -> None:
    state = arena(_leap_skill(), caster=(1, 3), foes=[(2, 3)], allies=[(3, 3)])
    result = use(state, SID, target_pos=Pos(x=4, y=3))
    (moved,) = of(result, UnitMoved)
    assert (moved.mode, moved.to_pos.x) == ("leap", 4)
    assert result.state.units[U1].xy == (4, 3)


def test_leap_does_not_trigger_opportunity_attacks(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena(_leap_skill(), caster=(1, 3), foes=[(1, 2)], reactive=[0])
    result = use(state, SID, target_pos=Pos(x=4, y=3))
    assert not of(result, ReactionTriggered) and not of(result, DamageDealt)
    # 同樣離開相鄰格，走路就會被藉機攻擊
    walked = state.clone()
    from trpg.engine import Move  # noqa: PLC0415

    walk = resolve(walked, Move(unit_id=U1, path=(Pos(x=1, y=3), Pos(x=2, y=3))))
    assert of(walk, ReactionTriggered)


def test_leap_ignores_low_terrain_but_not_pillars_or_walls() -> None:
    skill = _leap_skill(4)
    low = "\n".join(["0000000", "0000000", "0000000", "0010000", "0000000", "0000000", "0000000"])
    ok = arena(skill, caster=(0, 3), foes=[(6, 6)], heights=low)
    assert use(ok, SID, target_pos=Pos(x=3, y=3)).state.units[U1].xy == (3, 3)  # 高 1 層：無視
    high = "\n".join(["0000000", "0000000", "0000000", "0030000", "0000000", "0000000", "0000000"])
    tall = arena(skill, caster=(0, 3), foes=[(6, 6)], heights=high)
    with pytest.raises(IllegalActionError, match="路徑被擋住"):
        use(tall, SID, target_pos=Pos(x=3, y=3))
    pillar = arena(skill, caster=(0, 3), foes=[(6, 6)], objects=[(1, 3, "stone_pillar")])
    with pytest.raises(IllegalActionError, match="路徑被擋住"):
        use(pillar, SID, target_pos=Pos(x=3, y=3))
    wall = "\n".join([".......", ".......", ".......", ".#.....", ".......", ".......", "......."])
    walled = arena(skill, caster=(0, 3), foes=[(6, 6)], terrain=wall)
    with pytest.raises(IllegalActionError, match="路徑被擋住"):
        use(walled, SID, target_pos=Pos(x=2, y=3))


def test_leap_landing_rules() -> None:
    skill = _leap_skill(4)
    state = arena(
        skill,
        caster=(0, 3),
        foes=[(2, 3)],
        terrain="\n".join(
            [".......", ".......", ".......", "...x...", ".......", ".......", "......."]
        ),
    )
    for dest, match in [
        ((2, 3), "已有單位"),  # 落點有單位
        ((3, 3), "不可站立"),  # 深淵
        ((0, 3), "原地"),
        ((6, 3), "超出射程"),
    ]:
        with pytest.raises(IllegalActionError, match=match):
            use(state, SID, target_pos=Pos(x=dest[0], y=dest[1]))
    cliff = "\n".join(["0000000", "0000000", "0000000", "0002000", "0000000", "0000000", "0000000"])
    high = arena(skill, caster=(0, 3), foes=[(6, 6)], heights=cliff)
    with pytest.raises(IllegalActionError, match="高度差過大"):
        use(high, SID, target_pos=Pos(x=3, y=3))
    step = "\n".join(["0000000", "0000000", "0000000", "0001000", "0000000", "0000000", "0000000"])
    up = arena(skill, caster=(0, 3), foes=[(6, 6)], heights=step)
    assert use(up, SID, target_pos=Pos(x=3, y=3)).state.units[U1].xy == (3, 3)


def test_leap_ignores_line_of_sight_but_candidates_exclude_illegal_tiles() -> None:
    skill = _leap_skill(3)
    state = arena(skill, caster=(1, 3), foes=[(6, 6)], objects=[(2, 3, "stone_pillar")])
    cells = {
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.target_pos is not None
    }
    assert (4, 3) not in cells and (1, 3) not in cells  # 石柱擋住直線；不能原地跳
    assert (3, 4) in cells and (1, 5) in cells


def test_leap_lands_in_oil_and_a_trap_triggers_on_landing(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena(_leap_skill(), caster=(0, 3), foes=[(6, 6)], surfaces=[(3, 3, "oil")])
    result = use(state, SID, target_pos=Pos(x=3, y=3))
    assert result.state.tile(3, 3).surface.value == "oil" and result.state.units[U1].xy == (3, 3)
    trapped = arena(_leap_skill(), caster=(0, 3), foes=[(6, 6)])
    trapped.traps = [
        TrapState(
            owner_id=U2,
            team=Team.ENEMY,
            pos=Pos(x=3, y=3),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(trapped.units[U2].attributes.items()),
        )
    ]
    landed = use(trapped, SID, target_pos=Pos(x=3, y=3))
    assert [t.unit_id for t in of(landed, TrapTriggered)] == [U1]


def test_leap_is_unavailable_while_rooted() -> None:
    state = arena(_leap_skill())
    state.units[U1].statuses = [_status("root")]
    with pytest.raises(IllegalActionError):
        use(state, SID, target_pos=Pos(x=2, y=3))


# ---------------------------------------------------------------------------
# swap
# ---------------------------------------------------------------------------


def _swap_skill(affects: str, *extra: dict[str, Any]) -> SkillDef:
    return make_skill(
        SID,
        {"type": "single", "range": 4},
        [{"type": "swap", "affects": affects}, *extra],
        category="weapon",
    )


def test_swap_with_an_ally_always_succeeds_and_does_not_count_as_moving() -> None:
    state = arena(_swap_skill("allies"), caster=(0, 3), allies=[(3, 3)], foes=[(6, 6)])
    result = use(state, SID, target_id=U2)
    moves = of(result, UnitMoved)
    assert [(m.unit_id, m.mode, (m.to_pos.x, m.to_pos.y)) for m in moves] == [
        (U1, "swap", (3, 3)),
        (U2, "swap", (0, 3)),
    ]
    assert result.state.units[U1].xy == (3, 3) and result.state.units[U2].xy == (0, 3)
    assert not result.state.units[U1].moved_this_turn


def test_swap_with_an_enemy_needs_a_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = arena(_swap_skill("enemies"), caster=(0, 3), foes=[(3, 3)])
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 1)  # 自然 1：失手
    missed = use(state, SID, target_id=U2)
    assert not of(missed, UnitMoved) and missed.state.units[U1].xy == (0, 3)
    always(monkeypatch)
    hit = use(state, SID, target_id=U2)
    assert hit.state.units[U1].xy == (3, 3) and hit.state.units[U2].xy == (0, 3)


def test_swap_cannot_target_yourself_and_respects_affects() -> None:
    state = arena(_swap_skill("allies"), caster=(0, 3), allies=[(3, 3)], foes=[(6, 6)])
    with pytest.raises(IllegalActionError, match="不能以自己為目標"):
        use(state, SID, target_id=U1)
    with pytest.raises(IllegalActionError, match="無法對敵方使用"):
        use(state, SID, target_id=U3)


def test_swap_puts_an_enemy_into_the_surface_the_caster_was_standing_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(_swap_skill("enemies"), caster=(0, 3), foes=[(3, 3)], surfaces=[(0, 3, "fire")])
    result = use(state, SID, target_id=U2)
    assert result.state.units[U2].xy == (0, 3)
    entered = [e for e in result.events if type(e).__name__ == "SurfaceEntered"]
    assert [e.unit_id for e in entered if e.pos == Pos(x=0, y=3)][-1] == U2  # type: ignore[attr-defined]


def test_swap_needs_both_tiles_to_be_standable() -> None:
    """交換位置的兩格都要能讓對方站上去（致命或不可站的地形不行）；此處用處理器直接檢查。"""
    from trpg.engine.context import Ctx  # noqa: PLC0415
    from trpg.engine.effects import SwapUnitsEffect, execute  # noqa: PLC0415

    state = arena(_swap_skill("enemies"), caster=(0, 3), foes=[(3, 3)])
    ctx = Ctx(state)
    state.set_tile(0, 3, replace(state.tile(0, 3), terrain="lava"))  # 只為了測試處理器的檢查
    execute(ctx, [SwapUnitsEffect(source_id=U1, unit_id=U1, other_id=U2)])
    assert state.units[U1].xy == (0, 3) and state.units[U2].xy == (3, 3)
    assert [e.reason for e in ctx.events if isinstance(e, EffectFizzled)] == ["swap_blocked"]


def test_swap_lands_the_enemy_on_an_enemy_trap_of_the_casters_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """把敵人換到我方陷阱所在格（施放者原本站的格子）：陷阱觸發。"""
    always(monkeypatch)
    state = arena(_swap_skill("enemies"), caster=(0, 3), foes=[(3, 3)])
    state.traps = [
        TrapState(
            owner_id=U1,
            team=Team.ALLY,
            pos=Pos(x=0, y=3),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U1].attributes.items()),
        )
    ]
    result = use(state, SID, target_id=U2)
    assert [t.unit_id for t in of(result, TrapTriggered)] == [U2]


def test_swap_onto_a_ledge_makes_the_falling_unit_take_fall_damage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    heights = "\n".join(
        ["0000000", "0000000", "0000000", "3000000", "0000000", "0000000", "0000000"]
    )
    # 施放者站在高 3 的台地上（落差 3 ≥ 門檻），與低處的敵人交換：施放者墜落
    state = arena(_swap_skill("enemies"), caster=(0, 3), foes=[(2, 3)], heights=heights)
    result = use(state, SID, target_id=U2)
    falls = [e for e in result.events if type(e).__name__ == "UnitFell"]
    assert [f.unit_id for f in falls] == [U1]  # type: ignore[attr-defined]
    assert result.state.units[U2].xy == (0, 3)


def test_swap_effects_after_it_apply_to_the_swapped_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(_swap_skill("enemies", HIT), caster=(0, 3), foes=[(3, 3)])
    result = use(state, SID, target_id=U2)
    assert result.state.units[U2].xy == (0, 3)
    assert [d.target_id for d in of(result, DamageDealt)] == [U2]


# ---------------------------------------------------------------------------
# 與其他系統的交互：連段條件、on_move 被動、預覽、AI、重播
# ---------------------------------------------------------------------------

MOVED: dict[str, Any] = {"type": "moved_this_turn"}


def _damage_with_condition(condition: dict[str, Any]) -> dict[str, Any]:
    return {"type": "damage", "multiplier_permille": 500, "condition": condition}


def test_a_dash_satisfies_moved_this_turn_but_standing_still_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    follow = _damage_with_condition(MOVED)
    dashing = arena(charge_skill(DASH, follow))
    assert [d.cause for d in of(use(dashing, SID, target_id=U2), DamageDealt)] == ["attack"]
    standing = arena(charge_skill(DASH, follow), foes=[(1, 3)])  # 已經相鄰：沒有移動
    assert not of(use(standing, SID, target_id=U2), DamageDealt)


def test_dash_triggers_on_move_passives_but_leap_and_swap_do_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    dash = arena(charge_skill(DASH, HIT), extra=["skill_fleet_foot"])
    hasted = [s for s in of(use(dash, SID, target_id=U2), StatusApplied) if s.status_id == "hasted"]
    assert [s.target_id for s in hasted] == [U1]
    leap = arena(_leap_skill(), foes=[(6, 6)], extra=["skill_fleet_foot"])
    assert not of(use(leap, SID, target_pos=Pos(x=3, y=3)), StatusApplied)
    swap = arena(_swap_skill("allies"), allies=[(3, 3)], foes=[(6, 6)], extra=["skill_fleet_foot"])
    assert not of(use(swap, SID, target_id=U2), StatusApplied)


def test_the_preview_shows_the_charge_route_the_landing_and_the_collision_damage() -> None:
    from trpg.engine import preview  # noqa: PLC0415

    wall = row(7, {5: "#"})
    terrain = "\n".join([".......", ".......", ".......", wall, ".......", ".......", "......."])
    state = arena(CHARGE, caster=(0, 3), foes=[(4, 3)], terrain=terrain)
    p = preview(state, UseSkill(unit_id=U1, skill_id=CHARGE, target_id=U2))
    (move,) = p.moves
    assert (move.kind, move.unit_id, move.other_id) == ("dash", U1, U2)
    assert move.path == ((0, 3), (1, 3), (2, 3), (3, 3))
    assert p.targets[0].damage is not None and p.targets[0].damage.maximum > 0
    assert [u for u, _, high in p.collisions if u == U2 and high > 0]  # 撞牆的撞擊傷害
    # 衝鋒的每一步不重複列成「移動」
    assert not [o for o in p.certain + p.possible if o.kind == "moved" and o.unit_id == U1]
    assert state.units[U1].xy == (0, 3)  # 預覽沒有改動原本的戰場


def test_the_api_preview_carries_the_moves() -> None:
    from trpg.api.schemas import preview_out  # noqa: PLC0415
    from trpg.engine import preview  # noqa: PLC0415

    state = arena(_leap_skill(), caster=(0, 3), foes=[(6, 6)])
    p = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=3, y=3)))
    out = preview_out(p, (), ())
    assert [(m.kind, m.unit_id, m.path) for m in out.moves] == [("leap", U1, ((0, 3), (3, 3)))]
    swap = arena(_swap_skill("allies"), allies=[(3, 3)], foes=[(6, 6)])
    q = preview_out(preview(swap, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)), (), ())
    assert [(m.kind, m.unit_id, m.other_id) for m in q.moves] == [("swap", U1, U2)]


def test_the_narrative_describes_dashes_leaps_and_swaps() -> None:
    from trpg.narrative.events import describe_event  # noqa: PLC0415

    state = arena(_leap_skill(), caster=(0, 3), foes=[(6, 6)])
    leaped = use(state, SID, target_pos=Pos(x=3, y=3))
    texts = [describe_event(e, leaped.state) for e in leaped.events]
    assert any(t and "跳躍到 (3, 3)" in t for t in texts)
    charge = use(arena(CHARGE), CHARGE, target_id=U2)
    lines = [t for e in charge.events if (t := describe_event(e, charge.state))]
    assert any("衝向" in t and "(0, 3)→(1, 3)→(2, 3)→(3, 3)" in t for t in lines)
    assert not any("移動到" in t and "(1, 3)" in t for t in lines)  # 衝鋒的每一步不逐步顯示
    swap = use(arena(_swap_skill("allies"), allies=[(3, 3)], foes=[(6, 6)]), SID, target_id=U2)
    swapped = (describe_event(e, swap.state) for e in swap.events)
    assert any(t and "交換位置，換到" in t for t in swapped)


def test_a_blocked_charge_is_explained_in_the_log(monkeypatch: pytest.MonkeyPatch) -> None:
    from trpg.narrative.events import describe_event  # noqa: PLC0415

    always(monkeypatch)

    state = arena(CHARGE)
    state.traps = [
        TrapState(
            owner_id=U2,
            team=Team.ENEMY,
            pos=Pos(x=1, y=3),
            skill_id="skill_bear_trap",
            remaining=3,
            attributes=tuple(state.units[U2].attributes.items()),
        )
    ]
    result = use(state, CHARGE, target_id=U2)
    texts = [t for e in result.events if (t := describe_event(e, result.state))]
    assert any("衝鋒被擋下" in t for t in texts)


def test_the_composer_can_draw_displace_with_dash_and_dash_is_always_first() -> None:
    from trpg.skillgen.random_composer import compose_with_stats  # noqa: PLC0415

    found = []
    for seed in range(500):  # 454、476 是已知的 dash＋push＋damage
        composed = compose_with_stats(seed, library=library(), skeleton="displace", rarity="epic")
        if any(e.type == "dash" for e in composed.skill.effects):
            found.append(composed.skill)
    assert found
    assert all(s.effects[0].type == "dash" and s.shape.type == "single" for s in found)
    assert any({"damage", "push"} <= {e.type for e in s.effects} for s in found)
    assert not any(e.type in ("leap", "swap") for s in found for e in s.effects)  # 手寫專用


def _charger_run(map_id: str, seed: int) -> Any:
    from trpg.engine.ai.utility import UtilityAI  # noqa: PLC0415
    from trpg.engine.runner import run_battle  # noqa: PLC0415
    from trpg.engine.setup import build_setup  # noqa: PLC0415
    from trpg.sim.lineup import build_allies, default_lineup  # noqa: PLC0415

    lib, allies = build_allies(library(), ["build_charger"])
    _, enemies = default_lineup(lib, map_id)
    setup = build_setup(lib, map_id, allies, enemies, max_rounds=30)
    return setup, run_battle(setup, seed, UtilityAI(lib.ai_profiles))


@pytest.mark.parametrize(
    ("map_id", "seed"), [("open_plain", 2), ("ruined_fort", 1), ("narrow_halls", 3)]
)
def test_charger_battles_replay_exactly(map_id: str, seed: int) -> None:
    from trpg.engine import state_to_json  # noqa: PLC0415
    from trpg.engine.runner import replay  # noqa: PLC0415

    setup, run = _charger_run(map_id, seed)
    again = replay(setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


def test_the_ai_uses_every_self_move_somewhere() -> None:
    modes: set[str] = set()
    for map_id, seed in [("open_plain", 2), ("ruined_fort", 1)]:
        _, run = _charger_run(map_id, seed)
        modes |= {e.mode for e in run.events if isinstance(e, UnitMoved)}
    assert {"dash", "leap", "swap"} <= modes
