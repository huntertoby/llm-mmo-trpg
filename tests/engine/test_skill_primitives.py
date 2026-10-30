"""技能效果原語（docs/phases/Phase2A計畫.md 3.4、5.5 第 4 條）：每個原語至少一個測試。"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import ally_mana, library, make_skill, no_reactions, with_rolls
from tests.engine.skill_helpers import SID, U1, U2, U3, battle, cast, hit_with, of
from trpg.engine import ResolveResult, UseSkill, legal_actions, resolve
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    Healed,
    ManeuverRolled,
    ObjectCreated,
    ObjectDestroyed,
    PushResisted,
    ReactionTriggered,
    SkillUsed,
    StatusApplied,
    SurfaceChanged,
    TerrainChanged,
    UnitMoved,
)
from trpg.shared.types import Attribute, Pos, Surface, Team, UnitId

FIRE: dict[str, Any] = {"type": "damage", "dice": "2d6", "element": "fire"}
SINGLE5: dict[str, Any] = {"type": "single", "range": 5}


# ---------------------------------------------------------------------------
# damage
# ---------------------------------------------------------------------------


def test_spell_damage_uses_dice_plus_attribute_and_the_hit_roll() -> None:
    skill = make_skill(SID, SINGLE5, [FIRE], cost={"mana": 7})
    state = hit_with(battle(skill, [(5, 3)]), [(6, 3), (6, 4)])
    result = cast(state, target_id=U2)
    (roll,) = of(result, AttackRolled)
    assert (roll.attacker_id, roll.target_id, roll.skill_id, roll.hit) == (U1, U2, SID, True)
    (dmg,) = of(result, DamageDealt)
    assert dmg.rolls == (3, 4) and dmg.element.value == "fire" and dmg.cause == "attack"
    mage_int = state.units[U1].attributes["int"]  # type: ignore[index]
    assert dmg.amount == (7 * 1000 + mage_int * 500) // 1000  # 骰值 + 智力 × 0.5
    assert result.state.units[U2].hp == state.units[U2].hp - dmg.amount
    caster = result.state.units[U1]
    paid = ally_mana(7)  # 我方付打折後的費用（BAL-4c）
    assert (caster.ap, caster.mana) == (state.units[U1].ap - 1, 99 - paid)
    (used,) = of(result, SkillUsed)
    assert (used.skill_id, used.ap, used.mana, used.mana_after) == (SID, 1, paid, 99 - paid)


def test_a_miss_deals_no_damage_but_still_costs() -> None:
    skill = make_skill(SID, SINGLE5, [FIRE], cost={"mana": 7})
    result = cast(with_rolls(battle(skill, [(5, 3)]), [(20, 1)]), target_id=U2)
    assert not of(result, AttackRolled)[0].hit
    assert not of(result, DamageDealt)
    assert result.state.units[U1].mana == 99 - ally_mana(7)


def test_critical_hit_doubles_the_dice_count() -> None:
    skill = make_skill(SID, SINGLE5, [FIRE])
    state = with_rolls(battle(skill, [(5, 3)]), [(20, 20), (6, 1), (6, 2), (6, 3), (6, 4)])
    (dmg,) = of(cast(state, target_id=U2), DamageDealt)
    assert dmg.crit and dmg.rolls == (1, 2, 3, 4)


def test_weapon_skill_damage_uses_the_weapon_dice_and_multiplier() -> None:
    skill = make_skill(
        SID,
        {"type": "single", "range": "weapon"},
        [{"type": "damage", "multiplier_permille": 1500}],
        category="weapon",
        ap_cost=2,
    )
    state = hit_with(battle(skill, [(4, 3)], base="hero_fighter"), [(8, 4)])
    weapon = state.units[U1].weapon
    (dmg,) = of(cast(state, target_id=U2), DamageDealt)
    strength = state.units[U1].attributes["str"]  # type: ignore[index]
    raw = (sum(dmg.rolls) + weapon.flat) * 1000 + strength * 300
    assert dmg.amount == raw * 1500 // 1_000_000 and dmg.element == weapon.element


# ---------------------------------------------------------------------------
# heal
# ---------------------------------------------------------------------------


def test_heal_restores_hp_of_allies_without_a_hit_roll() -> None:
    skill = make_skill(
        SID, {"type": "allies_in_radius", "radius": 2}, [{"type": "heal", "dice": "1d6"}]
    )
    state = battle(skill, [(6, 6)], allies=[(4, 3)])
    state.units[U2].hp = 10
    state.units[U1].hp = 20
    result = cast(state)
    assert not of(result, AttackRolled)
    healed = {e.target_id: e for e in of(result, Healed)}
    assert set(healed) == {U1, U2}  # 友方預設為對象，施放者在形狀內
    attr = state.units[U1].attributes["int"]  # type: ignore[index]
    for event in healed.values():
        assert event.amount == (sum(event.rolls) * 1000 + attr * 500) // 1000
    assert result.state.units[U2].hp == 10 + healed[U2].amount
    assert result.state.units[U3].hp == state.units[U3].hp  # 敵人不被治療


# ---------------------------------------------------------------------------
# push／pull
# ---------------------------------------------------------------------------

PUSH2: list[dict[str, Any]] = [
    {"type": "damage", "dice": "1d4", "element": "fire"},
    {"type": "push", "distance": 2},
]


def _moved(result: ResolveResult, uid: UnitId) -> list[UnitMoved]:
    return [e for e in of(result, UnitMoved) if e.unit_id == uid and e.mode == "forced"]


def test_push_moves_the_target_away_from_the_caster() -> None:
    skill = make_skill(SID, SINGLE5, PUSH2)
    result = cast(hit_with(battle(skill, [(4, 3)]), [(4, 1)]), target_id=U2)
    assert (result.state.units[U2].pos.x, result.state.units[U2].pos.y) == (6, 3)
    assert len(_moved(result, U2)) >= 1


def test_push_blocked_by_an_obstacle_stops_on_the_previous_tile() -> None:
    skill = make_skill(SID, SINGLE5, PUSH2)
    state = hit_with(battle(skill, [(4, 3)], objects=((6, 3, "stone_pillar"),)), [(4, 1)])
    result = cast(state, target_id=U2)
    assert (result.state.units[U2].pos.x, result.state.units[U2].pos.y) == (5, 3)
    blocked = battle(skill, [(4, 3)], objects=((5, 3, "stone_pillar"),))
    again = cast(hit_with(blocked, [(4, 1)]), target_id=U2)
    assert (again.state.units[U2].pos.x, again.state.units[U2].pos.y) == (4, 3)


def test_steadfast_halves_push_and_zero_distance_is_still_legal() -> None:
    skill = make_skill(
        SID,
        SINGLE5,
        [{"type": "damage", "dice": "1d4", "element": "fire"}, {"type": "push", "distance": 1}],
    )
    boss = no_reactions("bandit_boss")
    state = hit_with(battle(skill, [(4, 3, boss)]), [(4, 1)])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    assert action in legal_actions(state)  # 推 0 格也合法
    result = resolve(state, action)
    assert (result.state.units[U2].pos.x, result.state.units[U2].pos.y) == (4, 3)
    (resisted,) = of(result, PushResisted)
    assert (resisted.requested, resisted.distance) == (1, 0)
    assert of(result, DamageDealt)  # 傷害照常


def test_push_from_a_center_shape_pushes_away_from_the_center() -> None:
    skill = make_skill(
        SID,
        {"type": "cross", "range": 4},
        [{"type": "push", "distance": 1}],
    )
    state = battle(skill, [(5, 2), (5, 4)])
    result = cast(with_rolls(state, [(20, 19), (20, 19)]), target_pos=Pos(x=5, y=3))
    assert (result.state.units[U2].pos.x, result.state.units[U2].pos.y) == (5, 1)
    assert (result.state.units[U3].pos.x, result.state.units[U3].pos.y) == (5, 5)


def test_pull_moves_the_target_toward_the_caster_and_stops_in_front_of_them() -> None:
    skill = make_skill(
        SID,
        SINGLE5,
        [{"type": "damage", "dice": "1d4", "element": "fire"}, {"type": "pull", "distance": 2}],
    )
    result = cast(hit_with(battle(skill, [(6, 3)]), [(4, 1)]), target_id=U2)
    assert (result.state.units[U2].pos.x, result.state.units[U2].pos.y) == (4, 3)
    adjacent = cast(hit_with(battle(skill, [(4, 3)]), [(4, 1)]), target_id=U2)
    assert (adjacent.state.units[U2].pos.x, adjacent.state.units[U2].pos.y) == (4, 3)


# ---------------------------------------------------------------------------
# knock_prone／teleport／apply_status
# ---------------------------------------------------------------------------


def test_knock_prone_uses_a_contest_and_only_succeeds_on_a_win() -> None:
    skill = make_skill(
        SID,
        SINGLE5,
        [{"type": "damage", "dice": "1d4", "element": "fire"}, {"type": "knock_prone"}],
    )
    won = cast(hit_with(battle(skill, [(4, 3)]), [(4, 1), (20, 20)]), target_id=U2)
    (roll,) = of(won, ManeuverRolled)
    assert (roll.maneuver, roll.skill_id, roll.success) == ("knock_prone", SID, True)
    assert won.state.units[U2].has_status("prone")
    lost = cast(hit_with(battle(skill, [(4, 3)]), [(4, 1), (20, 1)]), target_id=U2)
    assert not of(lost, ManeuverRolled)[0].success
    assert not lost.state.units[U2].has_status("prone")


def test_teleport_moves_the_caster_without_provoking_reactions() -> None:
    skill = make_skill(
        SID, {"type": "ground_tile", "range": 3}, [{"type": "teleport"}], weapon_req="any"
    )
    guard = library().unit("bandit")  # 有藉機攻擊的敵人，緊鄰施放者
    state = battle(skill, [(4, 3, guard)])
    result = cast(state, target_pos=Pos(x=1, y=3))
    assert (result.state.units[U1].pos.x, result.state.units[U1].pos.y) == (1, 3)
    assert [e.mode for e in of(result, UnitMoved)] == ["teleport"]
    assert not of(result, ReactionTriggered)
    occupied = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=4, y=3))
    assert occupied not in legal_actions(state)  # 目標格有單位


def test_teleport_into_an_effect_tile_triggers_the_surface() -> None:
    skill = make_skill(SID, {"type": "ground_tile", "range": 3}, [{"type": "teleport"}])
    state = battle(skill, surfaces=((1, 3, "fire"),))
    result = cast(state, target_pos=Pos(x=1, y=3))
    assert any(e.status_id == "burning" for e in of(result, StatusApplied))  # 進入火焰表面


def test_apply_status_defaults_to_enemies_and_respects_affects_self() -> None:
    foe = make_skill(
        SID, {"type": "single", "range": 5}, [{"type": "apply_status", "status": "burning"}]
    )
    result = cast(hit_with(battle(foe, [(5, 3)])), target_id=U2)
    assert result.state.units[U2].has_status("burning")
    me = make_skill(
        SID,
        {"type": "self"},
        [{"type": "apply_status", "status": "concealed", "duration": 2, "affects": "self"}],
    )
    own = cast(battle(me, [(6, 6)]))
    assert own.state.units[U1].has_status("concealed")
    assert not of(own, AttackRolled)


# ---------------------------------------------------------------------------
# 地形類：create_surface／destroy_object／create_obstacle／raise／lower
# ---------------------------------------------------------------------------


def test_create_surface_records_the_caster_team_and_duration() -> None:
    skill = make_skill(
        SID,
        {"type": "cross", "range": 4},
        [{"type": "create_surface", "surface": "oil", "duration": 3}],
    )
    state = battle(skill)
    state.units[U1].attributes[Attribute.INT] = (
        13  # 智力 14 起表面 +1 回合（3H-1），這裡量原本的持續回合
    )
    result = cast(state, target_pos=Pos(x=2, y=2))
    tiles = {(c.pos.x, c.pos.y) for c in of(result, SurfaceChanged)}
    assert tiles == {(2, 2), (2, 1), (2, 3), (1, 2), (3, 2)}
    tile = result.state.tile(2, 2)
    assert tile.surface is Surface.OIL and tile.surface_team is Team.ALLY
    assert tile.surface_remaining == 3


def test_destroy_object_removes_breakable_objects_in_the_area() -> None:
    skill = make_skill(SID, {"type": "square3", "range": 4}, [{"type": "destroy_object"}])
    state = battle(skill, objects=((2, 2, "crate"), (3, 2, "earth_wall"), (1, 1, "oil_barrel")))
    result = cast(state, target_pos=Pos(x=2, y=2))
    destroyed = {e.object_id for e in of(result, ObjectDestroyed)}
    assert destroyed >= {"obj_0001", "obj_0002"}
    assert result.state.object_at(2, 2) is None and result.state.object_at(3, 2) is None


def test_create_obstacle_fills_only_empty_tiles() -> None:
    skill = make_skill(
        SID, {"type": "cross", "range": 4}, [{"type": "create_obstacle", "object": "crate"}]
    )
    state = battle(skill, [(2, 1)], objects=((1, 2, "low_wall"),))
    result = cast(state, target_pos=Pos(x=2, y=2))
    created = {(c.pos.x, c.pos.y) for c in of(result, ObjectCreated)}
    assert created == {(2, 2), (2, 3), (3, 2)}  # (2, 1) 有單位、(1, 2) 已有物件


def test_raise_and_lower_terrain_change_height_within_bounds() -> None:
    up = make_skill(
        SID, {"type": "ground_tile", "range": 4}, [{"type": "raise_terrain", "amount": 1}]
    )
    state = battle(up, heights="\n".join(["0000000"] * 3 + ["0010000"] + ["0000000"] * 3))
    raised = cast(state, target_pos=Pos(x=2, y=3))
    (change,) = of(raised, TerrainChanged)
    assert (change.height_before, change.height_after) == (1, 2)
    down = make_skill(
        SID, {"type": "ground_tile", "range": 4}, [{"type": "lower_terrain", "amount": 1}]
    )
    lowered = cast(
        battle(down, heights="\n".join(["0000000"] * 3 + ["0010000"] + ["0000000"] * 3)),
        target_pos=Pos(x=2, y=3),
    )
    assert lowered.state.tile(2, 3).height == 0
    floor = cast(battle(down), target_pos=Pos(x=2, y=2))
    assert floor.state.tile(2, 2).height == 0  # 不會低於 0
