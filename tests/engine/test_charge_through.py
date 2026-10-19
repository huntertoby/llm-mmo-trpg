"""直線衝撞（Phase 3D-2c）：``charge_through`` 選終點格、沿直線衝過去，沿途每個敵人各擲一次命中。"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
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
from trpg.engine import BattleState, Move, ResolveResult, UseSkill, legal_actions, resolve
from trpg.engine.events import (
    AttackRolled,
    Collided,
    DamageDealt,
    EventBase,
    ManeuverRolled,
    ReactionTriggered,
    StatusApplied,
    SurfaceEntered,
    TrapTriggered,
    UnitCharged,
    UnitMoved,
)
from trpg.engine.preview import preview
from trpg.engine.state import StatusInstance, TrapState
from trpg.narrative.events import describe_event
from trpg.narrative.skills import effect_summary
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3 = (UnitId(f"unit_000{i}") for i in range(1, 4))
SID = "skill_t_charge"
FLAT = "\n".join(["0000000"] * 7)
BULL = "skill_bull_rush"
PRONE_HIT: dict[str, Any] = {"type": "charge_through", "dice": "2d6", "on_hit": "knock_prone"}
ASIDE_HIT: dict[str, Any] = {"type": "charge_through", "dice": "2d6", "on_hit": "push_aside"}


def of[E: EventBase](result: ResolveResult, kind: type[E]) -> list[E]:
    return [e for e in result.events if isinstance(e, kind)]


_ROLLS: dict[str, Any] = {"armed": False, "queue": []}


def d20s(monkeypatch: pytest.MonkeyPatch, *rolls: int, die: int = 4) -> None:
    """d20 依序給 ``rolls``（用完之後一律 19：命中、對抗成功）、其他骰子一律 ``die``。序列從
    :func:`go` 開始才計算（建立戰鬥時的先攻不吃掉它）。"""
    _ROLLS["armed"], _ROLLS["queue"] = False, list(rolls)

    def fake(_self: Rng, sides: int) -> int:
        if sides != 20:
            return min(die, sides)
        queue = _ROLLS["queue"]
        return queue.pop(0) if _ROLLS["armed"] and queue else 19

    monkeypatch.setattr(Rng, "roll", fake)


def skill(*effects: dict[str, Any], reach: int = 6) -> SkillDef:
    return make_skill(
        SID, {"type": "ground_tile", "range": reach}, list(effects), category="weapon", ap_cost=2
    )


def terrain_of(cells: dict[tuple[int, int], str]) -> str:
    rows = [["."] * 7 for _ in range(7)]
    for (x, y), ch in cells.items():
        rows[y][x] = ch
    return "\n".join("".join(r) for r in rows)


def arena(
    sk: SkillDef | str,
    *,
    caster: tuple[int, int] = (0, 3),
    foes: Sequence[tuple[int, int]] = (),
    allies: Sequence[tuple[int, int]] = (),
    heights: str = FLAT,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    surfaces: Sequence[tuple[int, int, str]] = (),
    reactive: Sequence[int] = (),
    foe_hp: int = 200,
) -> BattleState:
    """U1 是施放者（我方戰士，裝備 ``sk``）；之後依序是 ``allies``、``foes``（預設不反應；
    ``reactive`` 列出的敵人保留反應規則）。"""
    sid = sk if isinstance(sk, str) else sk.id
    foes = foes or [(6, 6)]  # 戰鬥至少要有兩個單位：預設一個站在角落的敵人，不在任何衝撞線上
    m = make_map(
        heights,
        terrain,
        ally=[caster, *allies],
        enemy=list(foes),
        objects=objects,
        surfaces=surfaces,
    )
    spawns = [spawn(Team.ALLY, caster, caster_template([sid], base="hero_fighter"))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    for index, xy in enumerate(foes):
        foe = (
            template("bandit", max_hp=foe_hp) if index in reactive else no_reactions(max_hp=foe_hp)
        )
        spawns.append(spawn(Team.ENEMY, xy, foe))
    defs = [] if isinstance(sk, str) else [sk]
    return give_turn(make_state(m, spawns, skills=defs), U1)


def go(state: BattleState, sid: str, end: tuple[int, int]) -> ResolveResult:
    _ROLLS["armed"] = True
    return resolve(state, UseSkill(unit_id=U1, skill_id=sid, target_pos=Pos(x=end[0], y=end[1])))


def path_of(result: ResolveResult) -> list[tuple[int, int]]:
    (charged,) = of(result, UnitCharged)
    return [(p.x, p.y) for p in charged.path]


def ends(state: BattleState, sid: str = SID) -> list[tuple[int, int]]:
    return [
        (a.target_pos.x, a.target_pos.y)
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.skill_id == sid and a.target_pos is not None
    ]


def problems(sk: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        sk,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


# ---------------------------------------------------------------------------
# schema 與資料
# ---------------------------------------------------------------------------


def test_charge_through_must_be_the_first_effect() -> None:
    with pytest.raises(ValueError, match="charge_through 必須是技能的第一個效果"):
        skill({"type": "heal", "dice": "1d4", "affects": "self"}, PRONE_HIT)


def test_the_other_effects_must_be_self_only() -> None:
    with pytest.raises(ValueError, match="明寫 affects: self"):
        skill(PRONE_HIT, {"type": "apply_status", "status": "slowed", "duration": 2})
    ok = skill(PRONE_HIT, {"type": "apply_status", "status": "empowered", "affects": "self"})
    assert len(ok.effects) == 2


def test_charge_through_needs_the_ground_tile_shape_and_the_parameters() -> None:
    with pytest.raises(ValueError, match="形狀必須是 ground_tile"):
        make_skill(SID, {"type": "single", "range": 4}, [PRONE_HIT], category="weapon")
    no_hit = skill({"type": "charge_through", "dice": "2d6"})
    assert any("缺少必要參數 on_hit" in p for p in problems(no_hit))
    no_dice = skill({"type": "charge_through", "on_hit": "push_aside"})
    assert any("缺少必要參數 dice" in p for p in problems(no_dice))
    with pytest.raises(ValueError):
        skill({"type": "charge_through", "dice": "2d6", "on_hit": "burn"})


def test_it_is_an_active_only_self_move_and_at_most_one() -> None:
    data = skill(PRONE_HIT).model_dump(mode="json") | {"kind": "passive", "ap_cost": None}
    with pytest.raises(ValueError):
        SkillDef.model_validate(data)
    with pytest.raises(ValueError, match="最多一個改變自身位置"):
        skill(PRONE_HIT, {"type": "leap"})


def test_the_demo_skill_is_valid_rare_and_equipped_in_build_charger() -> None:
    lib = library()
    bull = lib.ruleset.skill_def(BULL)
    assert bull.rarity == "rare" and bull.effects[0].type == "charge_through"
    assert bull.name_zh == "蠻牛衝陣"
    assert BULL in lib.builds.by_id()["build_charger"].hero.skills
    assert lib.ruleset.skill_def("skill_battering_ram").name_zh == "破城衝撞"  # 3C-3a 的同名技能


# ---------------------------------------------------------------------------
# 選取：直線、終點須空、擋住停下
# ---------------------------------------------------------------------------


def test_only_straight_lines_within_the_reach_are_legal() -> None:
    state = arena(skill(PRONE_HIT, reach=3), caster=(3, 3))
    expect = {
        (3 + dx * i, 3 + dy * i) for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)) for i in (1, 2, 3)
    }
    assert set(ends(state)) == expect
    for bad in ((4, 4), (5, 4), (3, 3), (3, 7)):  # 斜向、不在線上、原地、地圖外
        with pytest.raises(IllegalActionError):
            go(state, SID, bad)
    far = arena(skill(PRONE_HIT, reach=3), caster=(0, 3))
    with pytest.raises(IllegalActionError, match="超出射程"):
        go(far, SID, (4, 3))


def test_the_end_tile_must_be_empty_and_standable() -> None:
    state = arena(skill(PRONE_HIT), foes=[(3, 3)], terrain=terrain_of({(5, 3): "#"}))
    with pytest.raises(IllegalActionError, match="終點必須是空格"):
        go(state, SID, (3, 3))
    with pytest.raises(IllegalActionError, match="不可站立"):
        go(state, SID, (5, 3))
    assert (3, 3) not in ends(state) and (5, 3) not in ends(state)
    assert (4, 3) in ends(state)


def test_a_wall_stops_the_charge_before_it(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), terrain=terrain_of({(3, 3): "#"}))
    result = go(state, SID, (5, 3))  # 終點是空地，但牆擋在路上
    assert path_of(result) == [(0, 3), (1, 3), (2, 3)]
    assert result.state.units[U1].xy == (2, 3)
    assert [(m.mode, m.to_pos.x) for m in of(result, UnitMoved)] == [("dash", 1), ("dash", 2)]


def test_a_blocking_object_stops_it_too() -> None:
    state = arena(skill(PRONE_HIT), objects=[(2, 3, "crate")])
    assert go(state, SID, (5, 3)).state.units[U1].xy == (1, 3)


def test_a_too_high_step_stops_the_charge() -> None:
    heights = "\n".join(["0003000"] * 7)
    result = go(arena(skill(PRONE_HIT), heights=heights), SID, (5, 3))
    assert result.state.units[U1].xy == (2, 3)


def test_it_cannot_be_cast_when_it_cannot_stop_anywhere() -> None:
    state = arena(skill(PRONE_HIT), terrain=terrain_of({(1, 3): "#"}))
    with pytest.raises(IllegalActionError, match="停不下來"):
        go(state, SID, (4, 3))
    assert (4, 3) not in ends(state)


def test_it_never_stops_on_a_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """牆前最後一個空格被敵人占住：停點退回到更前面的空格（敵人被穿過、不阻擋）。"""
    d20s(monkeypatch, 1)  # 這一擊失手
    state = arena(skill(PRONE_HIT), foes=[(2, 3)], terrain=terrain_of({(3, 3): "#"}))
    result = go(state, SID, (5, 3))
    assert result.state.units[U1].xy == (1, 3)
    assert path_of(result) == [(0, 3), (1, 3)]
    assert [r.target_id for r in of(result, AttackRolled)] == []  # 沒有走到敵人身旁就停了


def test_it_cannot_be_cast_while_rooted_or_prone() -> None:
    state = arena(skill(PRONE_HIT))
    for status in ("root", "prone"):
        stuck = state.clone()
        stuck.units[U1].statuses = [StatusInstance(status_id=status, remaining=2, source_id=None)]
        with pytest.raises(IllegalActionError):
            go(stuck, SID, (3, 3))
        assert not ends(stuck)


# ---------------------------------------------------------------------------
# 結算：沿途的敵人
# ---------------------------------------------------------------------------


def test_every_enemy_on_the_way_rolls_once_in_path_order(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    # U2 站得遠、U3 站得近：命中依路徑順序（先 U3 再 U2），不是依單位 ID
    state = arena(skill(PRONE_HIT), foes=[(4, 3), (2, 3)])
    result = go(state, SID, (6, 3))
    assert [r.target_id for r in of(result, AttackRolled)] == [U3, U2]
    assert [(d.target_id, d.cause) for d in of(result, DamageDealt)] == [
        (U3, "attack"),
        (U2, "attack"),
    ]
    assert result.state.units[U1].xy == (6, 3)
    assert path_of(result)[-1] == (6, 3)


def test_hits_and_misses_are_rolled_separately(monkeypatch: pytest.MonkeyPatch) -> None:
    # U3（近）命中 → 擊倒對抗（19 成功）→ U2（遠）自然 1 失手
    d20s(monkeypatch, 19, 19, 1)
    state = arena(skill(PRONE_HIT), foes=[(4, 3), (2, 3)])
    result = go(state, SID, (6, 3))
    rolls = {r.target_id: r.hit for r in of(result, AttackRolled)}
    assert rolls == {U3: True, U2: False}
    assert [d.target_id for d in of(result, DamageDealt)] == [U3]
    assert result.state.units[U3].has_status("prone")
    assert not result.state.units[U2].has_status("prone")
    assert result.state.units[U2].hp == 200
    assert result.state.units[U1].xy == (6, 3)  # 失手也照樣穿過去


def test_a_hit_deals_the_dice_physical_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch, die=5)
    state = arena(skill(PRONE_HIT), foes=[(2, 3)])
    result = go(state, SID, (4, 3))
    (dealt,) = of(result, DamageDealt)
    assert dealt.element.value == "physical" and dealt.cause == "attack"
    assert result.state.units[U2].hp == 200 - dealt.amount
    assert dealt.amount >= 10  # 2d6 的兩顆都是 5（不加屬性）


def test_knock_prone_rolls_a_contest_and_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch, 19, 1)  # 命中，但擊倒的對抗自然 1 失敗
    state = arena(skill(PRONE_HIT), foes=[(2, 3)])
    result = go(state, SID, (4, 3))
    (contest,) = of(result, ManeuverRolled)
    assert contest.maneuver == "knock_prone" and not contest.success
    assert not result.state.units[U2].has_status("prone")
    assert [d.cause for d in of(result, DamageDealt)] == ["attack"]


def test_allies_yield_and_are_not_affected(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), allies=[(2, 3)], foes=[(4, 3)])
    ally = state.units[U2]
    result = go(state, SID, (6, 3))
    assert [r.target_id for r in of(result, AttackRolled)] == [U3]
    assert result.state.units[U2].hp == ally.hp and result.state.units[U2].xy == (2, 3)
    assert not result.state.units[U2].statuses
    assert result.state.units[U1].xy == (6, 3)


def test_an_enemy_who_falls_leaves_the_tile_open(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch, die=6)
    state = arena(skill(PRONE_HIT), foes=[(2, 3)], foe_hp=1)
    result = go(state, SID, (4, 3))
    assert [m.to_pos.x for m in of(result, UnitMoved) if m.unit_id == U1] == [1, 2, 3, 4]
    assert result.state.units[U1].xy == (4, 3)


def test_the_charge_does_not_provoke_opportunity_attacks(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), foes=[(0, 2), (4, 3)], reactive=[0])
    result = go(state, SID, (6, 3))
    assert not of(result, ReactionTriggered)
    assert all(d.target_id != U1 for d in of(result, DamageDealt))
    # 對照：同一個起點用走的離開相鄰格，藉機攻擊會被觸發
    walked = resolve(state, Move(unit_id=U1, path=(Pos(x=0, y=3), Pos(x=1, y=3))))
    assert of(walked, ReactionTriggered)


def test_charging_counts_as_moving_this_turn() -> None:
    state = arena(skill(PRONE_HIT), foes=[(3, 3)])
    assert not state.units[U1].moved_this_turn
    assert go(state, SID, (5, 3)).state.units[U1].moved_this_turn


def test_other_effects_apply_to_the_caster(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    buff = {"type": "apply_status", "status": "empowered", "duration": 2, "affects": "self"}
    result = go(arena(skill(PRONE_HIT, buff), foes=[(2, 3)]), SID, (4, 3))
    assert result.state.units[U1].has_status("empowered")


# ---------------------------------------------------------------------------
# push_aside
# ---------------------------------------------------------------------------


def test_push_aside_moves_the_hit_enemy_to_the_left_side_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d20s(monkeypatch)
    result = go(arena(skill(ASIDE_HIT), foes=[(2, 3)]), SID, (5, 3))
    # 向東衝：左手邊是北（y − 1）
    assert result.state.units[U2].xy == (2, 2)
    assert result.state.units[U1].xy == (5, 3)
    assert not of(result, Collided)


def test_push_aside_picks_the_right_side_when_the_left_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d20s(monkeypatch)
    state = arena(skill(ASIDE_HIT), foes=[(2, 3)], terrain=terrain_of({(2, 2): "#"}))
    assert go(state, SID, (5, 3)).state.units[U2].xy == (2, 4)
    crowded = arena(skill(ASIDE_HIT), foes=[(2, 3)], allies=[(2, 2)])  # 左邊站著隊友
    assert go(crowded, SID, (5, 3)).state.units[U3].xy == (2, 4)


def test_push_aside_into_a_wall_triggers_a_collision(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    walls = terrain_of({(2, 2): "#", (2, 4): "#"})
    result = go(arena(skill(ASIDE_HIT), foes=[(2, 3)], terrain=walls), SID, (5, 3))
    (hit,) = of(result, Collided)
    assert (hit.unit_id, hit.obstacle, hit.shortfall, hit.source_id) == (U2, "wall", 1, U1)
    assert [d.cause for d in of(result, DamageDealt)] == ["attack", "collision"]
    assert result.state.units[U2].xy == (2, 3)  # 推不動，還站在路徑上
    assert result.state.units[U1].xy == (5, 3)  # 施放者照樣穿過去


def test_push_aside_direction_follows_the_travel_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    south = arena(skill(ASIDE_HIT), caster=(3, 0), foes=[(3, 2)])
    # 向南衝（y 增加）：左手邊是東（x + 1）
    assert go(south, SID, (3, 5)).state.units[U2].xy == (4, 2)
    west = arena(skill(ASIDE_HIT), caster=(6, 3), foes=[(4, 3)])
    assert go(west, SID, (1, 3)).state.units[U2].xy == (4, 4)


# ---------------------------------------------------------------------------
# 落點互動
# ---------------------------------------------------------------------------


def test_a_trap_on_the_way_triggers_and_a_rooting_trap_stops_the_charge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), foes=[(4, 3)])
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
    result = go(state, SID, (6, 3))
    assert [t.unit_id for t in of(result, TrapTriggered)] == [U1]
    assert any(s.status_id == "root" and s.target_id == U1 for s in of(result, StatusApplied))
    assert result.state.units[U1].xy == (2, 3)  # 在陷阱格被定身停下
    assert not of(result, AttackRolled)  # 還沒走到敵人身邊


def test_the_surface_on_the_end_tile_applies() -> None:
    state = arena(skill(PRONE_HIT), surfaces=[(3, 3, "fire")])
    result = go(state, SID, (3, 3))
    assert [(e.unit_id, e.surface.value) for e in of(result, SurfaceEntered)] == [(U1, "fire")]


def test_the_charge_event_records_the_chosen_end_and_the_real_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), terrain=terrain_of({(3, 3): "#"}))
    (charged,) = of(go(state, SID, (5, 3)), UnitCharged)
    assert (charged.target.x, charged.target.y) == (5, 3)
    assert (charged.path[-1].x, charged.path[-1].y) == (2, 3)


# ---------------------------------------------------------------------------
# 示範技能
# ---------------------------------------------------------------------------


def test_bull_rush_runs_through_two_enemies_and_knocks_them_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d20s(monkeypatch, die=3)
    state = arena(BULL, foes=[(1, 3), (3, 3)])
    result = go(state, BULL, (4, 3))
    assert [r.target_id for r in of(result, AttackRolled)] == [U2, U3]
    assert result.state.units[U2].has_status("prone") and result.state.units[U3].has_status("prone")
    assert result.state.units[U1].xy == (4, 3)


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def test_the_preview_lists_the_route_and_each_enemy_with_the_hit_chance_at_that_spot() -> None:
    state = arena(skill(PRONE_HIT), foes=[(4, 3), (2, 3)])
    result = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=6, y=3)))
    (move,) = result.moves
    assert move.kind == "charge" and move.other_id is None
    assert move.path == ((0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3))
    assert [t.unit_id for t in result.targets] == [U2, U3]
    assert all(t.hit_chance == Fraction(3, 5) for t in result.targets)
    assert all(t.knock_chance is not None for t in result.targets)


def test_the_preview_hit_chance_uses_the_tile_the_caster_passes_from() -> None:
    """敵人站在高台上，施放者沿坡爬上去、與敵人同高時出手：預覽的命中率要用那一格計算（從起點算
    會有高度差的懲罰，與實際擲骰的位置不符）。"""
    heights = "\n".join(["0012200"] * 7)
    state = arena(skill(PRONE_HIT), foes=[(4, 3)], heights=heights)
    flat = arena(skill(PRONE_HIT), foes=[(4, 3)])
    spot = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=6, y=3))
    assert preview(state, spot).targets[0].hit_chance == preview(flat, spot).targets[0].hit_chance


def test_previewing_a_prone_target_describes_the_single_forced_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """倒地的目標讓攻擊有優勢，預覽事件卻只有一顆強制骰：紀錄文字不能因此出錯（3D-2c 修正）。"""
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), foes=[(2, 3)])
    state.units[U2].statuses = [StatusInstance(status_id="prone", remaining=2, source_id=None)]
    result = preview(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=4, y=3)))
    rolled = [e for e in result.max_events if isinstance(e, AttackRolled)]
    assert rolled and rolled[0].advantage == "advantage" and len(rolled[0].rolls) == 1
    assert "d20=" in (describe_event(rolled[0], result.max_state) or "")


# ---------------------------------------------------------------------------
# 紀錄文字與組合器
# ---------------------------------------------------------------------------


def test_the_log_describes_the_charge_and_a_blocked_end(monkeypatch: pytest.MonkeyPatch) -> None:
    d20s(monkeypatch)
    state = arena(skill(PRONE_HIT), terrain=terrain_of({(3, 3): "#"}))
    result = go(state, SID, (5, 3))
    (charged,) = of(result, UnitCharged)
    text = describe_event(charged, result.state) or ""
    assert "直線衝撞：(0, 3)→(1, 3)→(2, 3)" in text and "被擋住，停在 (2, 3)" in text
    clear = go(arena(skill(PRONE_HIT)), SID, (3, 3))
    assert "被擋住" not in (describe_event(of(clear, UnitCharged)[0], state) or "")


def test_the_skill_text_explains_both_on_hit_effects() -> None:
    lib = library()
    sk_prone, sk_aside = skill(PRONE_HIT), skill(ASIDE_HIT)
    prone = effect_summary(lib, sk_prone, sk_prone.effects[0])
    aside = effect_summary(lib, sk_aside, sk_aside.effects[0])
    assert "擊倒" in prone and "沿途每個敵人各擲命中" in prone and "2d6" in prone
    assert "推到路徑旁" in aside


def test_the_random_composer_never_draws_charge_through() -> None:
    """只給手寫技能：組合器用的原語清單不含 ``charge_through``。"""
    from trpg.skillgen.composer_parts import _HAND_WRITTEN_PRIMITIVES  # noqa: PLC0415

    assert "charge_through" in _HAND_WRITTEN_PRIMITIVES
