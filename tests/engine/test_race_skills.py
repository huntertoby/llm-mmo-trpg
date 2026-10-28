"""種族技（Phase 3R-2，``docs/design/07-角色成長.md`` 7.7）：10 招種族技的結算。

每招一組測試：結算結果與資料（``content/races.yaml``）的數字一致（「卡片＝實戰」：說明文字裡的
數字取自同一份資料）；共通規則（1 AP、每場次數、不佔技能欄）另測。
"""

from __future__ import annotations

import re

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.race_helpers import (
    FLAT7,
    U1,
    U2,
    U3,
    U4,
    act,
    all_races,
    end_turn,
    of,
    race_state,
    use,
)
from trpg.content.races import RaceEffect, RaceSkill
from trpg.engine import BattleState, Move, ResolveResult, legal_actions, resolve
from trpg.engine.actions import Action, Attack, UseRaceSkill
from trpg.engine.effects import ApplyStatusEffect, DamageEffect, PushEffect, run_effects
from trpg.engine.events import (
    AttackIntercepted,
    AttackRolled,
    Collided,
    DamageDealt,
    ObjectExploded,
    ObjectHurled,
    RaceSkillUsed,
    SummonExpired,
    UnitMoved,
)
from trpg.engine.ids import CONCEALED, DECOY_TAG, PRONE, RACE_ADAPT, RACE_STONEWALL
from trpg.engine.state import UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Element, ObjectId, Pos, Surface, Team, UnitId


def _skill(race: str) -> RaceSkill:
    return library().ruleset.race_def(race).skill


def _effect(race: str, kind: str) -> RaceEffect:
    return next(e for e in _skill(race).effects if e.type == kind)


def _numbers(text: str) -> set[int]:
    return {int(n) for n in re.findall(r"\d+", text)}


def _states(state: BattleState, uid: UnitId = U1) -> list[str]:
    return [s.status_id for s in state.units[uid].statuses]


# ---------------------------------------------------------------------------
# 共通規則
# ---------------------------------------------------------------------------


def test_every_race_skill_costs_one_ap_and_none_occupies_a_skill_slot() -> None:
    for race in all_races():
        assert race.skill.ap_cost == 1
        assert race.skill.occupies_skill_slot is False


def test_race_skill_costs_one_ap_and_counts_its_uses() -> None:
    state = race_state("human")
    result = act(state)
    me = result.state.units[U1]
    assert me.ap == state.units[U1].ap - 1
    assert me.skill_uses["race_adapt"] == 1
    assert of(result, RaceSkillUsed)[0].uses_left == 0
    assert me.skills == state.units[U1].skills  # 不佔技能欄


def test_uses_per_battle_limit_is_enforced() -> None:
    state = race_state("human")
    again = give_turn(act(state).state, U1)
    with pytest.raises(IllegalActionError, match="用完"):
        resolve(again, use())
    two = race_state("elf", objects=[(3, 3, "grass")])  # 林隱每場 2 次
    first = give_turn(act(two).state, U1)
    first.units[U1].statuses = []  # 清掉隱蔽狀態，才能再用一次
    second = act(first).state
    assert second.units[U1].skill_uses["race_woodhide"] == 2
    third = give_turn(second, U1)
    third.units[U1].statuses = []
    with pytest.raises(IllegalActionError, match="用完"):
        resolve(third, use())


def test_not_enough_ap_is_illegal() -> None:
    state = race_state("human")
    state.units[U1].ap = 0
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(state, use())


def test_units_without_a_race_have_no_race_skill() -> None:
    state = race_state(None)
    assert not [a for a in legal_actions(state) if isinstance(a, UseRaceSkill)]
    with pytest.raises(IllegalActionError, match="沒有種族技"):
        resolve(state, use())


def test_wrong_selection_fields_are_rejected() -> None:
    with pytest.raises(IllegalActionError, match="不能指定"):
        resolve(race_state("human"), use(direction="east"))
    with pytest.raises(IllegalActionError, match="必須指定"):
        resolve(race_state("dragonkin"), use())


def test_legal_actions_list_race_skill_and_every_one_resolves() -> None:
    for race in all_races():
        state = race_state(
            race.id, foes=((4, 3), (6, 3)), objects=[(3, 4, "crate"), (3, 3, "grass")]
        )
        listed = [a for a in legal_actions(state) if isinstance(a, UseRaceSkill)]
        for action in listed:
            resolve(state, action)  # 列出的都能結算，不拋例外
        if race.id not in ("elf",):  # 林隱要站在草叢／黑暗（這裡站在草叢物件上，所以也列出）
            assert listed or race.id in ("cyborg",), race.id


# ---------------------------------------------------------------------------
# 人類：應變
# ---------------------------------------------------------------------------


def test_human_adapt_gives_bonus_move_and_no_opportunity_attacks() -> None:
    bonus = _effect("human", "bonus_move").amount
    assert bonus in _numbers(_skill("human").description_zh)
    state = race_state("human", foes=((4, 3),))
    result = act(state)
    me = result.state.units[U1]
    assert me.move_points == state.units[U1].move_points + bonus
    assert RACE_ADAPT in _states(result.state)


def _opportunity_state(race: str | None) -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])

    spawns = [
        spawn(Team.ALLY, (3, 3), no_reactions("hero_fighter", max_hp=999, race=race)),
        spawn(Team.ENEMY, (4, 3), template("bandit", max_hp=999)),  # 保留預設反應（藉機攻擊）
    ]
    return give_turn(make_state(m, spawns), U1)


def test_adapt_prevents_opportunity_attacks_but_normal_movement_does_not() -> None:
    walk = Move(unit_id=U1, path=(Pos(x=3, y=3), Pos(x=2, y=3)))
    plain = resolve(_opportunity_state(None), walk)
    assert of(plain, AttackRolled), "沒有種族時離開相鄰格會被藉機攻擊"
    adapted = _opportunity_state("human")
    adapted = act(adapted).state
    free = resolve(adapted, walk)
    assert not of(free, AttackRolled)
    assert free.state.units[U1].xy == (2, 3)


def test_adapt_wears_off_at_next_own_turn() -> None:
    state = act(race_state("human")).state
    assert RACE_ADAPT in _states(state)
    s = state
    for _ in range(4):  # 走完敵人的回合回到 U1
        if s.active_unit == U1 and s.round > 1:
            break
        s = end_turn(s).state
    assert RACE_ADAPT not in _states(s)


# ---------------------------------------------------------------------------
# 精靈：林隱
# ---------------------------------------------------------------------------


def test_elf_woodhide_conceals_on_grass_or_darkness_only() -> None:
    on_grass = act(race_state("elf", objects=[(3, 3, "grass")])).state
    assert CONCEALED in _states(on_grass)
    in_dark = act(race_state("elf", surfaces=[(3, 3, "darkness")])).state
    assert CONCEALED in _states(in_dark)
    with pytest.raises(IllegalActionError, match="草叢或黑暗"):
        resolve(race_state("elf"), use())


def test_woodhide_is_refused_when_already_concealed() -> None:
    state = act(race_state("elf", objects=[(3, 3, "grass")])).state
    with pytest.raises(IllegalActionError, match="已經在隱蔽"):
        resolve(give_turn(state, U1), use())


# ---------------------------------------------------------------------------
# 狐族：狐火誘餌
# ---------------------------------------------------------------------------


def _decoys(state: BattleState) -> list[UnitState]:
    return [u for u in state.units.values() if u.has_tag(DECOY_TAG) and u.alive]


def test_fox_decoy_is_placed_within_range_and_only_one_exists() -> None:
    reach = _effect("fox", "decoy").range
    assert reach in _numbers(_skill("fox").description_zh)
    state = race_state("fox")
    result = act(state, pos=(4, 3))
    (decoy,) = _decoys(result.state)
    assert decoy.xy == (4, 3) and decoy.team is Team.ALLY
    with pytest.raises(IllegalActionError, match="射程"):
        resolve(state, use(pos=(3 + reach + 1, 3)))
    again = give_turn(result.state, U1)
    again.units[U1].skill_uses.clear()
    replaced = resolve(again, use(pos=(2, 3)))
    assert [u.xy for u in _decoys(replaced.state)] == [(2, 3)]
    assert any(e.reason == "limit" for e in of(replaced, SummonExpired))


def test_decoy_cannot_be_placed_on_a_unit_or_wall() -> None:
    state = race_state("fox", foes=((4, 3),))
    with pytest.raises(IllegalActionError, match="已經有單位"):
        resolve(state, use(pos=(4, 3)))


def _enemy_attack_after_decoy(seed: int) -> ResolveResult:
    state = race_state("fox", foes=((4, 3),), foe_attrs={"str": 18, "dex": 18})
    state = act(state, pos=(2, 3)).state
    state.seed = seed

    state.rng_state = Rng(seed).get_state()
    return resolve(give_turn(state, U2), Attack(unit_id=U2, target_id=U1))


def test_decoy_takes_the_next_single_target_hit() -> None:
    seen_hit = False
    for seed in range(40):
        result = _enemy_attack_after_decoy(seed)
        rolled = of(result, AttackRolled)
        if not rolled[0].hit:
            assert not of(result, AttackIntercepted)
            continue
        seen_hit = True
        (intercepted,) = of(result, AttackIntercepted)
        assert intercepted.target_id == U1
        assert result.state.units[U1].hp == result.state.units[U1].max_hp
        assert not _decoys(result.state)  # 誘餌用掉就消失
        assert any(e.reason == "decoy_hit" for e in of(result, SummonExpired))
        assert not of(result, DamageDealt)
    assert seen_hit


def test_decoy_is_spent_after_one_interception() -> None:
    for seed in range(40):
        result = _enemy_attack_after_decoy(seed)
        if not of(result, AttackRolled)[0].hit:
            continue
        again = give_turn(result.state, U2)
        for _ in range(40):  # 第二次命中時不會再被攔
            second = resolve(again, Attack(unit_id=U2, target_id=U1))
            assert not of(second, AttackIntercepted)
            if of(second, DamageDealt):
                return
            again = give_turn(second.state, U2)
    pytest.fail("找不到命中的種子")


# ---------------------------------------------------------------------------
# 龍裔：龍息震退
# ---------------------------------------------------------------------------


def test_dragon_breath_pushes_targets_in_cone_without_damage() -> None:
    distance = _effect("dragonkin", "push").distance
    assert distance in _numbers(_skill("dragonkin").description_zh)
    state = race_state("dragonkin", foes=((4, 3), (5, 3), (3, 6)))
    result = act(state, direction="east")
    assert result.state.units[U2].xy == (4 + distance, 3)
    assert result.state.units[U3].xy == (5 + distance, 3)
    assert result.state.units[U4].xy == (3, 6)  # 錐形外不動
    assert not of(result, DamageDealt) and not of(result, Collided)


def test_dragon_breath_blocked_push_is_not_a_collision() -> None:
    state = race_state("dragonkin", foes=((4, 3),), terrain="\n".join([".....#."] * 7))
    result = act(state, direction="east")
    assert result.state.units[U2].xy == (4, 3)  # 後面是牆：推不動
    assert not of(result, Collided) and not of(result, DamageDealt)


def test_dragon_breath_needs_someone_in_the_cone() -> None:
    with pytest.raises(IllegalActionError, match="沒有可以推開"):
        resolve(race_state("dragonkin", foes=((6, 6),)), use(direction="east"))


# ---------------------------------------------------------------------------
# 矮人：穩若磐石
# ---------------------------------------------------------------------------


def test_stonewall_blocks_push_pull_and_knockdown_for_its_duration() -> None:
    duration = _effect("dwarf", "immovable").duration
    state = act(race_state("dwarf")).state
    me = state.units[U1]
    assert RACE_STONEWALL in _states(state)
    assert next(s for s in me.statuses if s.status_id == RACE_STONEWALL).remaining == duration
    pushed = run_effects(
        state, [PushEffect(target_id=U1, direction=(1, 0), distance=2, source_id=U2)]
    )
    assert pushed.state.units[U1].xy == (3, 3)
    pulled = run_effects(
        state, [PushEffect(target_id=U1, direction=(-1, 0), distance=2, source_id=U2, pull=True)]
    )
    assert pulled.state.units[U1].xy == (3, 3)
    prone = run_effects(state, [ApplyStatusEffect(target_id=U1, status_id=PRONE, source_id=U2)])
    assert PRONE not in _states(prone.state)


def test_stonewall_expires_after_its_duration() -> None:
    state = act(race_state("dwarf")).state
    s = state
    turns = 0
    while RACE_STONEWALL in _states(s) and turns < 12:
        s = end_turn(s).state
        turns += 1
    assert RACE_STONEWALL not in _states(s)
    # 自己的兩個回合結束後消失（施放那個回合算第一個）
    assert s.round >= 2


# ---------------------------------------------------------------------------
# 晶能義體人：過充
# ---------------------------------------------------------------------------


def test_overcharge_restores_chosen_resource_by_the_data_amount() -> None:
    amount = _effect("cyborg", "restore_choice").amount
    assert amount in _numbers(_skill("cyborg").description_zh)
    state = race_state("cyborg")
    me = state.units[U1]
    me.stamina, me.mana, me.max_mana = 0, 0, 50
    stamina = act(state, choice="stamina").state.units[U1]
    assert (stamina.stamina, stamina.mana) == (amount, 0)
    mana = act(state, choice="mana").state.units[U1]
    assert (mana.stamina, mana.mana) == (0, amount)


def test_overcharge_never_exceeds_max_and_needs_a_deficit() -> None:
    state = race_state("cyborg")
    me = state.units[U1]
    me.max_stamina, me.stamina = 20, 15
    assert act(state, choice="stamina").state.units[U1].stamina == 20
    me.stamina = me.max_stamina
    with pytest.raises(IllegalActionError, match="滿的"):
        resolve(state, use(choice="stamina"))
    with pytest.raises(IllegalActionError, match="必須指定"):
        resolve(state, use())


# ---------------------------------------------------------------------------
# 獸人：蠻力投擲
# ---------------------------------------------------------------------------


def _object_id(state: BattleState, x: int, y: int) -> ObjectId:
    oid = state.tile(x, y).object_id
    assert oid is not None
    return oid


def test_brute_throw_moves_an_object_without_damage() -> None:
    reach = _effect("orc", "hurl_object").range
    assert reach in _numbers(_skill("orc").description_zh)
    state = race_state("orc", foes=((6, 6),), objects=[(4, 3, "crate")])
    oid = _object_id(state, 4, 3)
    result = act(state, target_object_id=oid, pos=(5, 3))
    (hurled,) = of(result, ObjectHurled)
    assert hurled.outcome in ("placed", "shattered")
    assert not of(result, DamageDealt)


def test_brute_throw_respects_range_and_pushable_only() -> None:
    state = race_state("orc", foes=((6, 6),), objects=[(0, 3, "crate"), (4, 3, "stone_pillar")])
    far = _object_id(state, 0, 3)
    with pytest.raises(IllegalActionError, match="超出投擲距離"):
        resolve(state, use(target_object_id=far, pos=(3, 5)))
    pillar = _object_id(state, 4, 3)
    with pytest.raises(IllegalActionError, match="無法投擲"):
        resolve(state, use(target_object_id=pillar, pos=(3, 5)))


def test_thrown_oil_barrel_still_explodes_on_fire() -> None:
    """蠻力投擲不加傷害，但物件規則照舊：油桶落在火焰上照樣爆炸（爆炸傷害是物件的，不是種族技的）。"""
    state = race_state(
        "orc", foes=((6, 6),), objects=[(4, 3, "oil_barrel")], surfaces=[(5, 3, "fire")]
    )
    oid = _object_id(state, 4, 3)
    result = act(state, target_object_id=oid, pos=(5, 3))
    assert of(result, ObjectExploded)


# ---------------------------------------------------------------------------
# 角魔：炎印
# ---------------------------------------------------------------------------


def test_ember_mark_creates_fire_under_the_caster() -> None:
    effect = _effect("fiend", "create_surface")
    state = race_state("fiend")
    result = act(state)
    tile = result.state.tile(3, 3)
    assert tile.surface is Surface.FIRE
    assert tile.surface_remaining == effect.duration
    assert not of(result, DamageDealt)


# ---------------------------------------------------------------------------
# 鱗族：潮息
# ---------------------------------------------------------------------------


def test_tide_breath_creates_water_in_a_3x3_within_range() -> None:
    reach = _skill("scalefolk").shape.range
    assert reach in _numbers(_skill("scalefolk").description_zh)
    state = race_state("scalefolk", foes=((6, 6),))
    result = act(state, pos=(5, 3))
    for x in range(4, 7):
        for y in range(2, 5):
            assert result.state.tile(x, y).surface is Surface.WATER, (x, y)
    assert result.state.tile(3, 3).surface is Surface.NONE
    with pytest.raises(IllegalActionError, match="射程"):
        resolve(state, use(pos=(6, 3)))  # 距離 3 > 2


# ---------------------------------------------------------------------------
# 海民：拋錨
# ---------------------------------------------------------------------------


def test_anchor_haul_pulls_an_enemy_closer_by_the_data_distance() -> None:
    effect = _effect("seafolk", "pull")
    assert effect.distance in _numbers(_skill("seafolk").description_zh)
    state = race_state("seafolk", foes=((7, 3),), heights="\n".join(["00000000"] * 7))
    result = act(state, target_id=U2)
    assert result.state.units[U2].xy == (7 - effect.distance, 3)
    assert not of(result, DamageDealt)


def test_anchor_haul_stops_when_blocked_and_never_collides() -> None:
    # 敵人 (6,3)；被拉的路上 (4,3) 站著我方友軍：拉 2 格只能走 1 格，且不吃撞擊傷害
    state = race_state("seafolk", foes=((6, 3),), allies=((4, 3),))
    result = act(state, target_id=U3)
    assert result.state.units[U3].xy == (5, 3)
    assert not of(result, Collided) and not of(result, DamageDealt)
    assert len(of(result, UnitMoved)) == 1


def test_anchor_haul_range_and_target_rules() -> None:
    far = race_state("seafolk", foes=((6, 6),))
    with pytest.raises(IllegalActionError, match="射程"):
        resolve(far, use(target_id=U2))
    with pytest.raises(IllegalActionError, match="只能拉敵人"):
        resolve(race_state("seafolk", allies=((5, 3),)), use(target_id=U2))


def test_pushed_damage_spec_is_never_used_by_race_skills() -> None:
    """防最佳解原則 1：種族技的任何結算都不加傷害（以所有種族技各打一次的事件驗證）。"""
    for race in all_races():
        state = race_state(race.id, foes=((4, 3), (5, 3)), objects=[(3, 4, "crate")])
        actions: list[Action] = [a for a in legal_actions(state) if isinstance(a, UseRaceSkill)]
        for action in actions[:6]:
            result = resolve(state, action)
            assert not [
                e for e in result.events if isinstance(e, DamageDealt) and e.cause != "explosion"
            ], race.id


def test_damage_effect_import_is_used() -> None:
    state = race_state("human")
    r = run_effects(
        state, [DamageEffect(target_id=U1, element=Element.FIRE, flat=10, source_id=U2)]
    )
    assert of(r, DamageDealt)
