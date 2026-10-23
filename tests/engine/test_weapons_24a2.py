"""武器擴充第一批的遠程（Phase 3-24a2，``docs/phases/Phase3計畫.md`` 25.2）。

每個特性都是 ``content/weapons.yaml`` 武器資料上的參數：弩的穿透一直線 ``pierce_line``、不受高度影響
``ignore_height``；火槍的彈匣 ``magazine``／``reload_ap``、槍聲 ``gunshot``、站定 ``steady``、
直射穿甲 ``ignore_cover``／``armor_pierce_permille``、距離修正 ``range_mod``。每個特性一組測試，其中
都有「資料改參數後行為跟著變」的案例。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_map, make_setup, template
from trpg.content.battle import WeaponDef
from trpg.engine import (
    Aim,
    Attack,
    BattleState,
    EndTurn,
    Move,
    Reload,
    legal_actions,
    resolve,
    start_battle,
)
from trpg.engine.actions import (
    ACTION_ADAPTER,
    BASIC_ACTION_TYPES,
    CHARGE_ACTION_TYPES,
    MANAGEMENT_ACTION_TYPES,
    SUMMON_ACTION_TYPES,
    WEAPON_ACTION_TYPES,
    Action,
)
from trpg.engine.ai.simple import choose_action
from trpg.engine.ai.utility import UtilityAI, _weapon_terms
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    StatusApplied,
    WeaponReloaded,
)
from trpg.engine.preview import preview
from trpg.engine.rules.combat import (
    attack_problem,
    defense_value_permille,
    is_concealed,
    situational_modifier,
)
from trpg.engine.setup import UnitSpawn
from trpg.engine.state import state_from_json, state_to_json
from trpg.engine.weapon_traits import pierce_line_targets
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
FLAT9 = "\n".join(["000000000"] * 5)


def weapon(weapon_id: str, **changes: Any) -> WeaponDef:
    """武器資料的複本，可以覆寫參數（驗證「改資料行為跟著變」）。"""
    data = library().weapons[weapon_id].model_dump(mode="json")
    return WeaponDef.model_validate({**data, **changes})


def armed(
    team: Team,
    pos: tuple[int, int],
    w: WeaponDef,
    base: str = "hero_fighter",
    **overrides: Any,
) -> UnitSpawn:
    overrides.setdefault("reactions", [])
    overrides.setdefault("max_hp", 200)
    overrides.setdefault("skills", [])
    return UnitSpawn(template=template(base, **overrides), weapon=w, team=team, position=pos)


def foe(pos: tuple[int, int], **overrides: Any) -> UnitSpawn:
    return armed(Team.ENEMY, pos, weapon("one_handed_sword"), base="bandit", **overrides)


def state_of(
    spawns: Sequence[UnitSpawn],
    *,
    heights: str = FLAT9,
    terrain: str | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    active: UnitId = U1,
) -> BattleState:
    allies = [s.position for s in spawns if s.team is Team.ALLY and s.position is not None]
    enemies = [s.position for s in spawns if s.team is Team.ENEMY and s.position is not None]
    m = make_map(heights, terrain, ally=allies, enemy=enemies, objects=objects)
    return give_turn(start_battle(make_setup(m, spawns), 0), active)


def dice(monkeypatch: pytest.MonkeyPatch, d20: int = 19, die: int = 3) -> None:
    """d20 一律 ``d20``（19 命中不暴擊、1 失手）、其他骰子一律 ``die``。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: d20 if sides == 20 else min(die, sides))


def kinds[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def shoot(state: BattleState, target: UnitId = U2) -> list[EventBase]:
    return resolve(state, Attack(unit_id=U1, target_id=target)).events


def gun_state(
    target_at: tuple[int, int] = (6, 2),
    *,
    moved: bool = False,
    objects: Sequence[tuple[int, int, str]] = (),
    gun: WeaponDef | None = None,
    heights: str = FLAT9,
) -> BattleState:
    state = state_of(
        [armed(Team.ALLY, (1, 2), gun or weapon("longgun")), foe(target_at)],
        objects=objects,
        heights=heights,
    )
    state.units[U1].moved_this_turn = moved
    return state


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_new_weapons_are_data_with_the_specified_parameters() -> None:
    w = library().weapons
    cb, lg = w["crossbow"], w["longgun"]
    assert (cb.weapon_class, cb.range, cb.two_handed, cb.scaling_attr) == ("ranged", 6, True, "dex")
    assert cb.pierce_line > 0 and cb.ignore_height and cb.magazine == 0 and cb.lob == 0
    assert (lg.weapon_class, lg.range, lg.two_handed, lg.scaling_attr) == ("ranged", 8, True, "dex")
    assert (lg.magazine, lg.reload_ap, lg.lob) == (1, 1, 0)
    assert lg.gunshot and lg.ignore_cover and lg.armor_pierce_permille == 250
    assert lg.steady is not None and (lg.steady.hit, lg.steady.crit_range) == (2, 2)
    spans = {(m.min_distance, m.max_distance): (m.hit, m.damage_permille) for m in lg.range_mod}
    assert spans == {(1, 1): (-2, 500), (4, None): (0, 1250)}
    # 舊武器維持預設（沒有任何遠程特性）
    bow = w["bow"]
    assert bow.pierce_line == 0 and not bow.ignore_height and bow.magazine == 0
    assert bow.steady is None and bow.range_mod == () and bow.armor_pierce_permille == 0


def test_weapon_schema_rejects_inconsistent_parameters() -> None:
    base = library().weapons["longgun"].model_dump(mode="json")
    with pytest.raises(ValidationError, match="直射"):
        WeaponDef.model_validate({**base, "lob": 1})  # 有彈匣的武器不能拋射
    with pytest.raises(ValidationError, match="steady"):
        WeaponDef.model_validate({**base, "steady": {"hit": 0, "crit_range": 0}})
    with pytest.raises(ValidationError, match="range_mod"):
        WeaponDef.model_validate({**base, "range_mod": [{"min_distance": 2}]})  # 沒有任何修正
    with pytest.raises(ValidationError, match="max_distance"):
        WeaponDef.model_validate(
            {**base, "range_mod": [{"min_distance": 3, "max_distance": 2, "hit": 1}]}
        )
    with pytest.raises(ValidationError):
        WeaponDef.model_validate({**base, "armor_pierce_permille": 1001})


def test_trait_text_follows_the_parameters() -> None:
    lines = weapon("longgun").trait_lines_zh()
    assert any("彈匣 1 發" in line and "1 AP" in line for line in lines)
    assert "槍聲：開火會解除自己的隱蔽" in lines
    assert "站定狙擊：本回合未移動時開火，命中 +2、暴擊範圍 +2" in lines
    assert "直射穿甲：無視半掩護、穿透 25% 防禦" in lines
    assert "貼臉（相鄰）：命中 −2、傷害 −50%" in lines
    assert "4 格以上：傷害 +25%" in lines
    edited = weapon(
        "longgun",
        magazine=2,
        reload_ap=2,
        armor_pierce_permille=400,
        steady={"hit": 3, "crit_range": 1},
        range_mod=[{"min_distance": 5, "max_distance": 7, "damage_permille": 1500}],
    ).trait_lines_zh()
    assert any("彈匣 2 發" in line and "2 AP" in line for line in edited)
    assert "直射穿甲：無視半掩護、穿透 40% 防禦" in edited
    assert "站定狙擊：本回合未移動時開火，命中 +3、暴擊範圍 +1" in edited
    assert "5～7 格：傷害 +50%" in edited
    assert any("穿透" in line for line in weapon("crossbow").trait_lines_zh())
    assert "不受高度影響：命中沒有高低差修正" in weapon("crossbow").trait_lines_zh()
    assert weapon("crossbow").trait_lines_zh() != weapon("bow").trait_lines_zh()


# ---------------------------------------------------------------------------
# 弩：穿透一直線
# ---------------------------------------------------------------------------


def line_state(count: int = 3, **changes: Any) -> BattleState:
    """主角在 (1,2)，敵人在同一橫線 (3,2)、(4,2)、(5,2)…"""
    spawns = [armed(Team.ALLY, (1, 2), weapon("crossbow", **changes))]
    spawns += [foe((3 + i, 2)) for i in range(count)]
    return state_of(spawns)


def test_crossbow_bolt_pierces_every_enemy_on_the_line_each_with_its_own_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    events = shoot(line_state(3))
    rolled = kinds(events, AttackRolled)
    assert [e.target_id for e in rolled] == [U2, U3, U4]
    assert all(e.attacker_id == U1 and e.hit for e in rolled)
    assert {e.target_id for e in kinds(events, DamageDealt)} == {U2, U3, U4}


def test_pierce_stops_at_the_weapon_range() -> None:
    state = line_state(4)  # 敵人在 x=3,4,5,6；主角 x=1，射程 6 → 最遠 x=7
    assert [u.id for u in pierce_line_targets(state, state.units[U1], state.units[U2])] == [
        U3,
        UnitId("unit_0004"),
        UnitId("unit_0005"),
    ]
    short = line_state(4, range=4)  # 射程 4 → 只到 x=5
    assert [u.id for u in pierce_line_targets(short, short.units[U1], short.units[U2])] == [
        U3,
        UnitId("unit_0004"),
    ]


def test_pierce_ignores_allies_and_units_off_the_line() -> None:
    spawns = [
        armed(Team.ALLY, (1, 2), weapon("crossbow")),
        armed(Team.ALLY, (2, 2), weapon("one_handed_sword")),  # 友方站在線上：不被打到
        foe((3, 2)),
        foe((4, 2)),
        foe((4, 3)),  # 不在這條線上
    ]
    state = state_of(spawns)
    targets = pierce_line_targets(state, state.units[U1], state.units[UnitId("unit_0003")])
    assert [u.id for u in targets] == [UnitId("unit_0004")]


def test_pierce_follows_a_diagonal_line_within_range() -> None:
    spawns = [armed(Team.ALLY, (1, 1), weapon("crossbow")), foe((3, 2)), foe((5, 3)), foe((7, 4))]
    state = state_of(spawns)
    behind = pierce_line_targets(state, state.units[U1], state.units[U2])
    assert [u.id for u in behind] == [UnitId("unit_0003")]  # (7,4) 距離 9，超出射程 6


def test_pierce_stops_at_a_wall_that_blocks_sight() -> None:
    spawns = [armed(Team.ALLY, (1, 2), weapon("crossbow")), foe((3, 2)), foe((5, 2))]
    open_state = state_of(spawns)
    assert len(pierce_line_targets(open_state, open_state.units[U1], open_state.units[U2])) == 1
    wall_at = "\n".join("....#...." if y == 2 else "........." for y in range(5))
    blocked = state_of(spawns, terrain=wall_at)
    assert pierce_line_targets(blocked, blocked.units[U1], blocked.units[U2]) == []


def test_changing_pierce_line_changes_how_many_enemies_are_pierced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    assert [e.target_id for e in kinds(shoot(line_state(3, pierce_line=0)), AttackRolled)] == [U2]
    assert [e.target_id for e in kinds(shoot(line_state(3, pierce_line=1)), AttackRolled)] == [
        U2,
        U3,
    ]


def test_bow_does_not_pierce(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    spawns = [armed(Team.ALLY, (1, 2), weapon("bow")), foe((3, 2)), foe((4, 2))]
    assert [e.target_id for e in kinds(shoot(state_of(spawns)), AttackRolled)] == [U2]


def test_crossbow_is_unaffected_by_height_and_the_data_decides() -> None:
    heights = "\n".join(["000000000", "000000000", "010000000", "000000000", "000000000"])
    low = state_of([armed(Team.ALLY, (1, 2), weapon("crossbow")), foe((4, 2))], heights=heights)
    up = state_of([armed(Team.ALLY, (1, 2), weapon("bow")), foe((4, 2))], heights=heights)
    bonus = low.ruleset.core.height_hit_bonus
    assert situational_modifier(up, up.units[U1], up.units[U2]) == bonus  # 弓：高打低
    assert situational_modifier(low, low.units[U1], low.units[U2]) == 0  # 弩：不受影響
    # 資料改參數：弩去掉 ignore_height 就受高度影響；弓加上就不受影響
    changed = state_of(
        [armed(Team.ALLY, (1, 2), weapon("crossbow", ignore_height=False)), foe((4, 2))],
        heights=heights,
    )
    assert situational_modifier(changed, changed.units[U1], changed.units[U2]) == bonus
    plain = state_of(
        [armed(Team.ALLY, (1, 2), weapon("bow", ignore_height=True)), foe((4, 2))],
        heights=heights,
    )
    assert situational_modifier(plain, plain.units[U1], plain.units[U2]) == 0


def test_crossbow_needs_no_reload_and_has_no_magazine(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = line_state(1)
    assert state.units[U1].ammo == 0
    assert not [a for a in legal_actions(state) if isinstance(a, Reload)]
    after = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert after.units[U1].ammo == 0
    assert attack_problem(after, after.units[U1], after.units[U2]) is None


# ---------------------------------------------------------------------------
# 火槍：彈匣與裝填
# ---------------------------------------------------------------------------


def test_longgun_starts_loaded_and_the_shot_empties_the_magazine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = gun_state()
    assert state.units[U1].ammo == 1
    assert not [a for a in legal_actions(state) if isinstance(a, Reload)]  # 滿膛時沒有裝填
    after = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert after.units[U1].ammo == 0
    problem = attack_problem(after, after.units[U1], after.units[U2])
    assert problem is not None and "空膛" in problem
    with pytest.raises(IllegalActionError, match="空膛"):
        resolve(after, Attack(unit_id=U1, target_id=U2))
    assert not [a for a in legal_actions(after) if isinstance(a, Attack)]


def test_reload_appears_only_when_empty_costs_ap_and_refills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = resolve(gun_state(), Attack(unit_id=U1, target_id=U2)).state
    assert Reload(unit_id=U1) in legal_actions(state)
    ap = state.units[U1].ap
    result = resolve(state, Reload(unit_id=U1))
    (event,) = kinds(result.events, WeaponReloaded)
    assert (event.unit_id, event.ammo, event.cost) == (U1, 1, 1)
    assert result.state.units[U1].ap == ap - 1 and result.state.units[U1].ammo == 1
    assert attack_problem(result.state, result.state.units[U1], result.state.units[U2]) is None
    assert not [a for a in legal_actions(result.state) if isinstance(a, Reload)]
    with pytest.raises(IllegalActionError, match="還沒空"):
        resolve(result.state, Reload(unit_id=U1))


def test_reload_needs_enough_ap(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = resolve(gun_state(), Attack(unit_id=U1, target_id=U2)).state
    state.units[U1].ap = 0
    assert not [a for a in legal_actions(state) if isinstance(a, Reload)]
    with pytest.raises(IllegalActionError, match="AP 不足"):
        resolve(state, Reload(unit_id=U1))


def test_reload_is_illegal_for_weapons_without_a_magazine() -> None:
    state = line_state(1)
    with pytest.raises(IllegalActionError, match="不用裝填"):
        resolve(state, Reload(unit_id=U1))


def test_magazine_and_reload_cost_come_from_the_data(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(gun=weapon("longgun", magazine=2, reload_ap=2))
    assert state.units[U1].ammo == 2
    once = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert once.units[U1].ammo == 1 and attack_problem(once, once.units[U1], once.units[U2]) is None
    twice = resolve(once, Attack(unit_id=U1, target_id=U2)).state
    assert twice.units[U1].ammo == 0
    twice.units[U1].ap = 2
    reloaded = resolve(twice, Reload(unit_id=U1))
    assert reloaded.state.units[U1].ammo == 2 and reloaded.state.units[U1].ap == 0
    assert kinds(reloaded.events, WeaponReloaded)[0].cost == 2
    assert preview(twice, Reload(unit_id=U1)).ap_cost == 2


def test_ammo_survives_the_state_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = resolve(gun_state(), Attack(unit_id=U1, target_id=U2)).state
    assert state.units[U1].ammo == 0
    assert state_from_json(state_to_json(state)).units[U1].ammo == 0
    assert state.clone().units[U1].ammo == 0


def test_attacking_an_object_also_spends_a_round(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(objects=[(4, 2, "crate")], target_at=(8, 4))
    crate = next(o for o in state.objects.values() if o.kind == "crate")
    after = resolve(state, Attack(unit_id=U1, target_object_id=crate.id)).state
    assert after.units[U1].ammo == 0


# ---------------------------------------------------------------------------
# 火槍：直射、槍聲
# ---------------------------------------------------------------------------


def test_longgun_is_direct_fire_and_cannot_lob_over_an_object() -> None:
    wall = [(4, 2, "stone_pillar")]
    rifle = gun_state(objects=wall)
    problem = attack_problem(rifle, rifle.units[U1], rifle.units[U2])
    assert problem is not None and "視線" in problem
    bow = state_of([armed(Team.ALLY, (1, 2), weapon("bow")), foe((6, 2))], objects=wall)
    assert attack_problem(bow, bow.units[U1], bow.units[U2]) is None  # 弓可以拋射越過


def test_gunshot_reveals_a_shooter_hiding_in_the_grass(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(objects=[(1, 2, "grass")])
    assert is_concealed(state, state.units[U1])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not is_concealed(result.state, result.state.units[U1])
    assert [e.status_id for e in kinds(result.events, StatusApplied)] == ["revealed"]
    # 資料改參數：沒有槍聲的火槍開火後仍藏在草叢裡
    quiet = gun_state(objects=[(1, 2, "grass")], gun=weapon("longgun", gunshot=False))
    still = resolve(quiet, Attack(unit_id=U1, target_id=U2)).state
    assert is_concealed(still, still.units[U1])


def test_gunshot_does_nothing_when_not_concealed(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    assert not kinds(shoot(gun_state()), StatusApplied)


# ---------------------------------------------------------------------------
# 火槍：站定狙擊
# ---------------------------------------------------------------------------


def test_steady_shot_gets_the_hit_bonus_and_wider_crit_range_when_not_moved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch, d20=18)  # 18：站定（暴擊範圍 18 起）暴擊，否則只是命中
    steady = shoot(gun_state(target_at=(3, 2)))  # 距離 2：沒有距離修正
    (roll,) = kinds(steady, AttackRolled)
    assert roll.modifier_bonus == 2 and roll.crit
    moved = shoot(gun_state(target_at=(3, 2), moved=True))
    (roll2,) = kinds(moved, AttackRolled)
    assert roll2.modifier_bonus == 0 and roll2.hit and not roll2.crit


def test_a_real_move_clears_the_steady_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(4, 2))
    state.units[U1].move_points = 3
    path = (Pos(x=1, y=2), Pos(x=1, y=3))
    after = resolve(state, Move(unit_id=U1, path=path)).state
    assert after.units[U1].moved_this_turn
    (roll,) = kinds(resolve(after, Attack(unit_id=U1, target_id=U2)).events, AttackRolled)
    assert roll.modifier_bonus == 0


def test_steady_stacks_with_aim(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(3, 2))
    state.units[U1].ap = 3
    aimed = resolve(state, Aim(unit_id=U1)).state
    (roll,) = kinds(resolve(aimed, Attack(unit_id=U1, target_id=U2)).events, AttackRolled)
    assert roll.modifier_bonus == 2 + state.ruleset.core.aim_hit_bonus


def test_changing_the_steady_parameters_changes_the_bonus(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=17)
    gun = weapon("longgun", steady={"hit": 5, "crit_range": 3})  # 暴擊範圍 17 起
    (roll,) = kinds(shoot(gun_state(target_at=(3, 2), gun=gun)), AttackRolled)
    assert roll.modifier_bonus == 5 and roll.crit
    none = weapon("longgun", steady=None)
    (roll2,) = kinds(shoot(gun_state(target_at=(3, 2), gun=none)), AttackRolled)
    assert roll2.modifier_bonus == 0 and not roll2.crit


def test_preview_hit_chance_reflects_steady_and_point_blank() -> None:
    steady = preview(gun_state(target_at=(3, 2)), Attack(unit_id=U1, target_id=U2)).hit_chance
    moved = preview(
        gun_state(target_at=(3, 2), moved=True), Attack(unit_id=U1, target_id=U2)
    ).hit_chance
    adjacent = preview(
        gun_state(target_at=(2, 2), moved=True), Attack(unit_id=U1, target_id=U2)
    ).hit_chance
    assert steady is not None and moved is not None and adjacent is not None
    assert steady > moved > adjacent


# ---------------------------------------------------------------------------
# 火槍：直射穿甲
# ---------------------------------------------------------------------------


def test_longgun_ignores_half_cover_and_a_bow_does_not(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    cover = [(5, 2, "crate")]  # 在目標 (6,2) 前面一格：半掩護
    (rifle,) = kinds(shoot(gun_state(objects=cover)), AttackRolled)
    assert rifle.cover == 0 and rifle.cover_object_id is None
    bow_state = state_of(
        [armed(Team.ALLY, (1, 2), weapon("bow", lob=0)), foe((6, 2))], objects=cover
    )
    (bow,) = kinds(shoot(bow_state), AttackRolled)
    assert bow.cover == -2
    # 資料改參數：火槍不再 ignore_cover 就吃半掩護
    soft = gun_state(objects=cover, gun=weapon("longgun", ignore_cover=False))
    (roll,) = kinds(shoot(soft), AttackRolled)
    assert roll.cover == -2


def test_longgun_pierces_a_quarter_of_the_targets_defense(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state()
    base = defense_value_permille(state.units[U2], state.ruleset)
    (roll,) = kinds(shoot(state), AttackRolled)
    assert roll.defense_value_permille == base * 750 // 1000
    other = gun_state(gun=weapon("longgun", armor_pierce_permille=500))
    (roll2,) = kinds(shoot(other), AttackRolled)
    assert roll2.defense_value_permille == base * 500 // 1000
    none = gun_state(gun=weapon("longgun", armor_pierce_permille=0))
    (roll3,) = kinds(shoot(none), AttackRolled)
    assert roll3.defense_value_permille == base


def test_armor_pierce_stacks_additively_with_armor_break() -> None:
    state = gun_state()
    target = state.units[U2]
    base = defense_value_permille(target, state.ruleset)
    assert defense_value_permille(target, state.ruleset, 250) == base * 750 // 1000
    assert defense_value_permille(target, state.ruleset, 100000) >= 1  # 至少 1


# ---------------------------------------------------------------------------
# 火槍：貼臉懲罰與遠距加成
# ---------------------------------------------------------------------------


def multiplier_at(
    distance: int, monkeypatch: pytest.MonkeyPatch, **changes: Any
) -> tuple[int, int]:
    dice(monkeypatch)
    state = gun_state(target_at=(1 + distance, 2), moved=True, gun=weapon("longgun", **changes))
    events = shoot(state)
    (roll,) = kinds(events, AttackRolled)
    (damage,) = kinds(events, DamageDealt)
    return roll.modifier_bonus, damage.multiplier_permille


def test_point_blank_is_penalized_and_far_shots_hit_harder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert multiplier_at(1, monkeypatch) == (-2, 500)  # 貼臉：命中 −2、傷害 −50%
    assert multiplier_at(2, monkeypatch) == (0, 1000)
    assert multiplier_at(3, monkeypatch) == (0, 1000)
    assert multiplier_at(4, monkeypatch) == (0, 1250)  # 4 格以上：傷害 +25%
    assert multiplier_at(7, monkeypatch) == (0, 1250)


def test_point_blank_damage_is_really_lower(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    near = kinds(shoot(gun_state(target_at=(2, 2), moved=True)), DamageDealt)[0].amount
    mid = kinds(shoot(gun_state(target_at=(3, 2), moved=True)), DamageDealt)[0].amount
    far = kinds(shoot(gun_state(target_at=(6, 2), moved=True)), DamageDealt)[0].amount
    assert near < mid < far


def test_changing_range_mod_changes_the_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    mods = [{"min_distance": 2, "max_distance": 3, "hit": 3, "damage_permille": 2000}]
    assert multiplier_at(2, monkeypatch, range_mod=mods) == (3, 2000)
    assert multiplier_at(1, monkeypatch, range_mod=mods) == (0, 1000)  # 貼臉不再有懲罰
    assert multiplier_at(5, monkeypatch, range_mod=[]) == (0, 1000)


def test_range_mod_does_not_touch_other_weapons(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = state_of([armed(Team.ALLY, (1, 2), weapon("bow")), foe((2, 2))])
    (roll,) = kinds(shoot(state), AttackRolled)
    (damage,) = kinds(shoot(state), DamageDealt)
    assert roll.modifier_bonus == 0 and damage.multiplier_permille == 1000


# ---------------------------------------------------------------------------
# AI 與基本動作上限
# ---------------------------------------------------------------------------


def test_simple_ai_reloads_an_empty_gun(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = resolve(gun_state(), Attack(unit_id=U1, target_id=U2)).state
    assert choose_action(state) == Reload(unit_id=U1)
    loaded = resolve(state, Reload(unit_id=U1)).state
    assert choose_action(loaded) == Attack(unit_id=U1, target_id=U2)


def test_utility_ai_reloads_when_empty_and_shoots_standing_still(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    ai = UtilityAI(library().ai_profiles)
    state = gun_state(target_at=(6, 2))
    assert ai(state) == Attack(unit_id=U1, target_id=U2)  # 站定直接開火，不先走位
    empty = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    empty.units[U1].ap = 2
    assert ai(empty) == Reload(unit_id=U1)


def test_ai_line_up_prefers_a_position_that_lines_up_several_enemies() -> None:
    ai = library().ai_profiles
    w = next(p for p in ai.profiles if p.id == "archer").weights
    assert w.line_up > 0
    spawns = [armed(Team.ALLY, (1, 2), weapon("crossbow")), foe((3, 2)), foe((4, 2)), foe((4, 4))]
    lined = state_of(spawns)
    enemies = [u for u in lined.living_units() if u.team is Team.ENEMY]
    here = _weapon_terms(lined, lined.units[U1], w, enemies)
    off = state_of(spawns)
    off.units[U1].pos = Pos(x=1, y=1)  # 斜著看：不再一線穿過兩名敵人
    there = _weapon_terms(off, off.units[U1], w, enemies)
    assert here > there
    assert _weapon_terms(lined, lined.units[U1], w.model_copy(update={"line_up": 0}), enemies) == 0


def test_basic_action_cap_stays_at_ten_and_reload_is_a_weapon_action() -> None:
    assert len(BASIC_ACTION_TYPES) == len(set(BASIC_ACTION_TYPES)) <= 10
    assert WEAPON_ACTION_TYPES == ("reload",) and "reload" not in BASIC_ACTION_TYPES
    # 每一種動作都歸類：基本動作、武器動作、管理操作，或技能
    union = get_args(get_args(Action.__value__)[0])
    types = {a.model_fields["type"].default for a in union}
    classified = {
        *BASIC_ACTION_TYPES,
        *WEAPON_ACTION_TYPES,
        *CHARGE_ACTION_TYPES,
        *MANAGEMENT_ACTION_TYPES,
        *SUMMON_ACTION_TYPES,
        "use_skill",
    }
    assert types == classified
    # 加上武器動作的總數（含裝填）也有上限，避免之後無限長
    assert len(BASIC_ACTION_TYPES) + len(WEAPON_ACTION_TYPES) <= 11
    assert ACTION_ADAPTER.validate_python({"type": "reload", "unit_id": U1}) == Reload(unit_id=U1)


def test_reload_never_shows_up_for_other_weapons() -> None:
    for wid in ("one_handed_sword", "bow", "crossbow", "fire_staff"):
        state = state_of([armed(Team.ALLY, (1, 2), weapon(wid)), foe((6, 2))])
        assert not [a for a in legal_actions(state) if isinstance(a, Reload)], wid
        assert EndTurn(unit_id=U1) in legal_actions(state)


def test_blank_heroes_for_the_new_weapons_exist() -> None:
    builds = {b.id: b for b in library().builds.builds}
    assert builds["build_blank_crossbow"].hero.weapon == "crossbow"
    assert builds["build_blank_longgun"].hero.weapon == "longgun"
    assert builds["build_blank_crossbow"].blank and builds["build_blank_longgun"].blank
    assert not builds["build_blank_longgun"].hero.skills


def test_weapon_rule_lines_show_grip_and_shared_backstab() -> None:
    """武器卡的共用規則（Phase 3-41b，清單 7.2、7.3）：握法、近戰共用的背刺（數字取自 core）。"""
    lib = library()
    core = lib.ruleset.core
    gun = lib.weapons["longgun"]
    assert gun.name_zh == "火槍"
    assert gun.rule_lines_zh(core)[0].startswith("雙手")
    assert not any("背刺" in line for line in gun.rule_lines_zh(core))  # 遠程武器沒有背刺
    dagger = lib.weapons["dagger"]
    assert dagger.rule_lines_zh(core)[0].startswith("單手")
    backstab = next(line for line in dagger.rule_lines_zh(core) if "背刺" in line)
    assert f"命中 +{core.backstab_hit_bonus}" in backstab
    bigger = core.model_copy(update={"backstab_hit_bonus": 5})
    assert "命中 +5" in "".join(dagger.rule_lines_zh(bigger))
