"""技能的情境測試（docs/phases/Phase2A計畫.md 5.5 第 5 條）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    ally_mana,
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.skill_helpers import FLAT7, SID, U1, U2, U3, U4, U5, battle, cast, of
from trpg.engine import BattleState, EndTurn, UnitSpawn, UseSkill, legal_actions, resolve
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    Healed,
    ObjectExploded,
    SkillCooldownChanged,
    StatusApplied,
    SurfaceChanged,
)
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Element, Pos, Surface, Team, UnitId

ASHEN = "skill_ashen_oath"


def _content_caster(
    skill_ids: list[str],
    foes: list[tuple[int, int]],
    *,
    base: str = "hero_mage",
    caster: tuple[int, int] = (1, 3),
    allies: list[tuple[int, int]] | None = None,
    objects: tuple[tuple[int, int, str], ...] = (),
    surfaces: tuple[tuple[int, int, str], ...] = (),
) -> BattleState:
    """施放者裝備 ``content/`` 的技能；其他單位沒有反應規則。"""
    allies = allies or []
    m = make_map(FLAT7, ally=[caster, *allies], enemy=foes, objects=objects, surfaces=surfaces)
    spawns = [spawn(Team.ALLY, caster, caster_template(skill_ids, base=base))]
    spawns += [spawn(Team.ALLY, xy, no_reactions("hero_archer")) for xy in allies]
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in foes]
    return give_turn(make_state(m, spawns), U1)


def _use(state: BattleState, skill_id: str, **fields: Any):  # type: ignore[no-untyped-def]
    return resolve(state, UseSkill(unit_id=U1, skill_id=skill_id, **fields))


# ---------------------------------------------------------------------------
# 灰燼誓約 × 油桶；喚潮 × 連鎖閃電；旋風斬 × 火焰武器
# ---------------------------------------------------------------------------


def test_ashen_oath_cone_detonates_an_oil_barrel_and_the_blast_resolves_normally() -> None:
    # 錐形向東：(2,3)；(3,2)(3,3)(3,4)；(4,1…5)。油桶在 (3,3)，敵人在爆炸範圍但不在錐形內的 (2,4)
    state = _content_caster([ASHEN], [(2, 4)], objects=((3, 3, "oil_barrel"),))
    result = _use(state, ASHEN, direction="east")
    assert [e.pos for e in of(result, ObjectExploded)] == [Pos(x=3, y=3)]
    assert not of(result, AttackRolled)  # 敵人不在錐形內，沒有命中骰
    blast = [e for e in of(result, DamageDealt) if e.cause == "explosion"]
    assert [e.target_id for e in blast] == [U2] and blast[0].element is Element.FIRE
    assert result.state.units[U2].hp < state.units[U2].hp
    assert result.state.object_at(3, 3) is None


def test_summon_tide_then_chain_lightning_conducts_through_the_water() -> None:
    state = _content_caster(
        ["skill_summon_tide", "skill_chain_lightning"],
        [(5, 3), (5, 4), (5, 2), (6, 3)],
        base="hero_stormcaller",
    )
    flooded = _use(state, "skill_summon_tide", target_pos=Pos(x=5, y=3)).state
    assert all(flooded.tile(x, y).surface is Surface.WATER for x, y in [(5, 3), (5, 2), (6, 3)])
    turn = with_rolls(give_turn(flooded, U1), [(20, 19)] * 3)
    result = _use(turn, "skill_chain_lightning", target_id=U2)
    chained = {e.target_id for e in of(result, AttackRolled)}
    assert chained == {U2, U3, U4}  # 跳躍 2 次：同距離依單位 ID
    conducted = [e for e in of(result, DamageDealt) if e.cause == "conduct"]
    assert U5 in {e.target_id for e in conducted}  # 沒被連鎖打到、但站在水面上的單位
    assert all(e.element is Element.LIGHTNING for e in conducted)


def test_weapon_skill_with_a_fire_weapon_deals_fire_damage() -> None:
    lib = library()
    fire_sword = lib.weapons["one_handed_sword"].model_copy(update={"element": Element.FIRE})
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3), (3, 4)])
    fighter = caster_template(["skill_whirlwind"], base="hero_fighter")
    spawns = [
        UnitSpawn(template=fighter, weapon=fire_sword, team=Team.ALLY, position=(3, 3)),
        spawn(Team.ENEMY, (4, 3), no_reactions()),
        spawn(Team.ENEMY, (3, 4), no_reactions()),
    ]
    state = give_turn(make_state(m, spawns), U1)
    result = _use(with_rolls(state, [(20, 19)] * 2), "skill_whirlwind")
    damage = of(result, DamageDealt)
    assert len(damage) == 2 and all(e.element is Element.FIRE for e in damage)
    plain = _content_caster(["skill_whirlwind"], [(2, 3)], base="hero_fighter", caster=(1, 3))
    physical = of(_use(with_rolls(plain, [(20, 19)]), "skill_whirlwind"), DamageDealt)
    assert physical and physical[0].element is Element.PHYSICAL


# ---------------------------------------------------------------------------
# 命中：每個敵人各擲一次；地面效果與失手無關
# ---------------------------------------------------------------------------


def test_area_skill_rolls_per_enemy_and_misses_still_create_the_surface() -> None:
    foes = [(2, 3), (3, 2), (3, 4)]  # 都在錐形內
    state = _content_caster([ASHEN], foes)
    # 依單位 ID 擲骰：U2 失手（自然 1）、U3 命中、U4 失手
    rolled = with_rolls(state, [(20, 1), (20, 19), (20, 1)])
    result = _use(rolled, ASHEN, direction="east")
    rolls = of(result, AttackRolled)
    assert [(r.target_id, r.hit) for r in rolls] == [(U2, False), (U3, True), (U4, False)]
    assert all(r.skill_id == ASHEN for r in rolls)
    hurt = {e.target_id for e in of(result, DamageDealt) if e.cause == "attack"}
    assert hurt == {U3}
    cone = {(2, 3), (3, 2), (3, 3), (3, 4), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5)}
    changed = {(c.pos.x, c.pos.y) for c in of(result, SurfaceChanged) if c.after is Surface.FIRE}
    assert changed >= cone


def test_surface_is_created_even_when_every_enemy_misses() -> None:
    state = _content_caster([ASHEN], [(2, 3), (3, 2)])
    result = _use(with_rolls(state, [(20, 1), (20, 1)]), ASHEN, direction="east")
    assert not [e for e in of(result, DamageDealt) if e.cause == "attack"]
    assert result.state.tile(4, 3).surface is Surface.FIRE


# ---------------------------------------------------------------------------
# 友方與表面擁有者
# ---------------------------------------------------------------------------


def test_default_area_damage_never_rolls_against_or_hurts_allies() -> None:
    state = _content_caster([ASHEN], [(3, 4)], allies=[(3, 2)])
    result = _use(with_rolls(state, [(20, 19)]), ASHEN, direction="east")
    assert {r.target_id for r in of(result, AttackRolled)} == {U3}  # 只有敵人（U3）
    ally_damage = [e for e in of(result, DamageDealt) if e.target_id == U2 and e.cause == "attack"]
    assert not ally_damage


def test_a_fire_surface_created_by_a_skill_burns_the_casters_allies() -> None:
    state = _content_caster([ASHEN], [(3, 4)], allies=[(3, 2)])
    result = _use(with_rolls(state, [(20, 19)]), ASHEN, direction="east")
    burned = {e.target_id for e in of(result, StatusApplied) if e.status_id == "burning"}
    assert U2 in burned  # 有害的表面敵我都受影響
    assert result.state.tile(3, 2).surface_team is Team.ALLY


def test_affects_all_rolls_against_and_damages_allies_in_the_area() -> None:
    skill = make_skill(
        SID,
        {"type": "square3", "range": 5},
        [{"type": "damage", "dice": "1d6", "element": "fire", "affects": "all"}],
    )
    state = battle(skill, [(5, 4)], allies=[(5, 2)])
    state = with_rolls(state, [(20, 19)] * 2)
    result = cast(state, target_pos=Pos(x=5, y=3))
    assert {r.target_id for r in of(result, AttackRolled)} == {U2, U3}  # 友方與敵人
    hurt = {e.target_id for e in of(result, DamageDealt) if e.cause == "attack"}
    assert hurt == {U2, U3}
    # 友方也可能失手，失手就不受傷
    missed = cast(with_rolls(state, [(20, 1), (20, 19)]), target_pos=Pos(x=5, y=3))
    assert {e.target_id for e in of(missed, DamageDealt) if e.cause == "attack"} == {U3}


def test_affects_all_never_hits_the_caster_even_when_the_shape_includes_them() -> None:
    """Phase 2A-2 決定 #4：敵我不分只影響其他單位，施放者自己不擲骰、不受傷。"""
    skill = make_skill(
        SID,
        {"type": "allies_in_radius", "radius": 1},
        [{"type": "damage", "dice": "1d6", "element": "fire", "affects": "all"}],
    )
    state = with_rolls(battle(skill, [(4, 3)], allies=[(2, 3)]), [(20, 19)] * 3)
    result = cast(state)
    rolled = {r.target_id for r in of(result, AttackRolled)}
    assert U1 not in rolled and rolled == {U2, U3}  # 友方 U2、敵方 U3
    assert U1 not in {d.target_id for d in of(result, DamageDealt)}
    assert result.state.units[U1].hp == state.units[U1].hp


def _end_turns_until(state: BattleState, uids: set[UnitId]) -> list[Healed]:
    """一路結束回合，直到 ``uids`` 都至少開始過一次回合；回傳期間的治療事件。"""
    healed: list[Healed] = []
    started: set[UnitId] = set()
    for _ in range(12):
        assert state.active_unit is not None
        result = resolve(state, EndTurn(unit_id=state.active_unit))
        healed += of(result, Healed)
        state = result.state
        started.add(state.active_unit) if state.active_unit else None
        if uids <= started:
            return healed
    raise AssertionError("回合沒有輪到所有單位")


def test_a_holy_surface_made_by_a_skill_only_heals_the_casters_team() -> None:
    skill = make_skill(
        SID,
        {"type": "cross", "range": 4},
        [{"type": "create_surface", "surface": "holy", "duration": 3}],
    )
    state = battle(skill, [(5, 3)], allies=[(4, 3)])  # 友方 U2 與敵人 U3 都在十字內
    state.units[U2].hp = 10
    state.units[U3].hp = 10
    after = cast(state, target_pos=Pos(x=5, y=3)).state
    assert after.tile(5, 3).surface_team is Team.ALLY
    assert after.tile(4, 3).surface is Surface.HOLY
    healed = _end_turns_until(after, {U1, U2, U3})
    assert U2 in {e.target_id for e in healed}  # 友方被治療
    assert U3 not in {e.target_id for e in healed}  # 敵人站在同一種表面上卻不受益


def test_a_map_placed_holy_surface_is_neutral_and_heals_both_teams() -> None:
    skill = make_skill(
        SID, {"type": "self"}, [{"type": "apply_status", "status": "concealed", "affects": "self"}]
    )
    state = battle(skill, [(5, 3)], allies=[(4, 3)], surfaces=((5, 3, "holy"), (4, 3, "holy")))
    state.units[U2].hp = 10
    state.units[U3].hp = 10
    healed = _end_turns_until(state, {U1, U2, U3})
    assert {U2, U3} <= {e.target_id for e in healed}


# ---------------------------------------------------------------------------
# 代價：法力、冷卻、次數、HP
# ---------------------------------------------------------------------------

BOLT = {"type": "damage", "dice": "1d4", "element": "fire"}


def _bolt(**cost: Any):  # type: ignore[no-untyped-def]
    return make_skill(SID, {"type": "single", "range": 5}, [BOLT], cost=cost or {"mana": 0})


def _unavailable(state: BattleState, fragment: str) -> None:
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    assert action not in legal_actions(state)
    assert not [a for a in legal_actions(state) if isinstance(a, UseSkill)]
    with pytest.raises(IllegalActionError, match=fragment):
        resolve(state, action)


def test_not_enough_mana_makes_the_skill_illegal() -> None:
    state = battle(_bolt(mana=10), [(5, 3)])
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    assert action in legal_actions(state)
    need = ally_mana(10)  # 我方付打折後的費用（BAL-4c）
    state.units[U1].mana = need - 1
    _unavailable(state, "法力不足")
    state.units[U1].mana = need
    assert action in legal_actions(state)
    assert resolve(state, action).state.units[U1].mana == 0


def test_not_enough_ap_makes_the_skill_illegal() -> None:
    skill = make_skill(SID, {"type": "single", "range": 5}, [BOLT], ap_cost=2)
    state = battle(skill, [(5, 3)])
    state.units[U1].ap = 1
    _unavailable(state, "AP 不足")


def test_uses_per_battle_runs_out() -> None:
    state = battle(_bolt(mana=1, uses_per_battle=1), [(5, 3)])
    after = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).state
    after = give_turn(after, U1)
    _unavailable(after, "已用完")


def test_hp_cost_must_leave_the_caster_standing() -> None:
    state = battle(_bolt(hp_percent=300), [(5, 3)])  # 最大 HP 的 30%，無條件進位
    caster = state.units[U1]
    cost = -(-caster.max_hp * 300 // 1000)
    caster.hp = cost
    _unavailable(state, "HP 不足")
    caster.hp = cost + 1
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2))
    assert result.state.units[U1].hp == 1


def test_cooldown_two_skips_exactly_one_own_turn() -> None:
    state = battle(_bolt(mana=1, cooldown=2), [(5, 3)])
    state = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_id=U2)).state
    assert state.units[U1].cooldowns == {SID: 2}
    action = UseSkill(unit_id=U1, skill_id=SID, target_id=U2)
    seen: list[tuple[int, bool]] = []
    cooldown_events: list[int] = []
    for _ in range(12):
        assert state.active_unit is not None
        result = resolve(state, EndTurn(unit_id=state.active_unit))
        state = result.state
        cooldown_events += [e.remaining for e in of(result, SkillCooldownChanged)]
        if state.active_unit == U1 and not state.ended:
            seen.append((state.round, action in legal_actions(state)))
            if len(seen) == 2:
                break
            state = give_turn(state, U1)  # 保持 AP，不改冷卻
    assert seen == [(2, False), (3, True)]  # 第 1 輪用、第 2 輪不可用、第 3 輪可用
    assert cooldown_events == [1, 0]
    assert state.units[U1].mana == 98  # 法力不回復


def test_loadout_incompatible_with_the_weapon_is_rejected_at_battle_start() -> None:
    from trpg.engine.setup import BattleSetupError  # noqa: PLC0415

    mage = library().unit("hero_mage")
    bad = mage.model_copy(update={"skills": ("skill_piercing_shot",)})  # 需要遠程武器
    m = make_map(FLAT7, ally=[(0, 0)], enemy=[(6, 6)])
    with pytest.raises(BattleSetupError, match="需要遠程武器"):
        make_state(m, [spawn(Team.ALLY, (0, 0), bad), spawn(Team.ENEMY, (6, 6), no_reactions())])


def test_illegal_skill_actions_have_chinese_reasons_and_leave_state_untouched() -> None:
    state = battle(_bolt(mana=1), [(5, 3)])
    other = UseSkill(unit_id=U1, skill_id="skill_nope", target_id=U2)
    with pytest.raises(IllegalActionError, match="找不到技能"):
        resolve(state, other)
    other_skill = make_skill("skill_t_other", {"type": "self"}, [BOLT])
    with pytest.raises(IllegalActionError, match="沒有裝備技能"):
        resolve(
            battle(other_skill, [(5, 3)]),
            UseSkill(unit_id=U1, skill_id="skill_ashen_oath", direction="east"),
        )
    with pytest.raises(IllegalActionError, match="目標超出射程"):
        resolve(
            battle(_bolt(mana=1), [(6, 6)]),
            UseSkill(unit_id=U1, skill_id=SID, target_id=U2),
        )
