"""第二批其他武器（Phase 3I-4，``docs/phases/Phase3I計畫.md``；08 8.11 雙匕首與火器，#46）。

雙匕首（成對、普攻打兩下 1d4，背刺時兩下都吃加成）、霰彈槍（依距離 100／75／50／25%）、手槍
（單手、彈匣 2）、雙手槍（成對、彈匣 2＋2、1 AP 裝滿）。每條規則一組引擎表格測試，另有行為一致
測試：每把新武器的普攻與武器技，實際傷害的屬性加成等於卡片「目前 +N」。
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pydantic import ValidationError

from tests.content.test_equipment_content import _loadout, _rules
from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast, hit_with, of
from tests.engine.test_weapons_24a2 import (
    U1,
    U2,
    armed,
    dice,
    foe,
    gun_state,
    kinds,
    shoot,
    state_of,
    weapon,
)
from trpg.api.gear import gear_catalog
from trpg.content.battle import WeaponDef
from trpg.content.equipment import loadout_problems
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, Reload, legal_actions, resolve
from trpg.engine.ai.simple import choose_action
from trpg.engine.events import AttackRolled, DamageDealt, WeaponReloaded
from trpg.engine.rules.combat import attack_problem
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.state import UnitState
from trpg.roguelite.start import start_weapons
from trpg.shared.bonus_text import plain_text
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Team

NEW_WEAPONS = ("dual_dagger", "shotgun", "pistol", "dual_pistol")


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_the_new_weapons_are_data_with_the_designed_parameters() -> None:
    w = library().weapons
    dd, sg, pi, dp = w["dual_dagger"], w["shotgun"], w["pistol"], w["dual_pistol"]
    assert (dd.weapon_class, dd.range, dd.scaling_attr, dd.paired, dd.strikes) == (
        "melee",
        1,
        "dex",
        True,
        2,
    )
    # BAL-8b 原型專用：雙匕首 1d4 → 1d3
    assert (dd.dice.count, dd.dice.sides, dd.two_handed) == (1, 3, False)
    assert (sg.weapon_class, sg.range, sg.two_handed, sg.magazine, sg.gunshot) == (
        "ranged",
        4,
        True,
        1,
        True,
    )
    assert (pi.range, pi.two_handed, pi.paired, pi.magazine, pi.reload_ap) == (
        5,
        False,
        False,
        2,
        1,
    )
    assert (dp.range, dp.two_handed, dp.paired, dp.magazine, dp.reload_ap) == (5, False, True, 4, 1)
    for gun in (sg, pi, dp):
        assert gun.scaling_attr == "dex" and gun.lob == 0  # 火器是直射
        assert gun.steady is None and not gun.ignore_cover and not gun.armor_pierce_permille
    assert not sg.paired and not any(m.hit for m in sg.range_mod)  # 霰彈槍沒有站定、遠距加成
    assert pi.range_mod == () and dp.range_mod == ()  # 手槍、雙手槍沒有距離修正
    assert [(m.min_distance, m.max_distance, m.damage_permille) for m in sg.range_mod] == [
        (2, 2, 750),
        (3, 3, 500),
        (4, 4, 250),
    ]
    for wid in NEW_WEAPONS:
        look = w[wid].look
        assert look is not None and look.kind == wid and look.form and look.material


def test_the_schema_rejects_inconsistent_parameters() -> None:
    with pytest.raises(ValidationError, match="成對武器"):
        weapon("dual_dagger", two_handed=True)
    with pytest.raises(ValidationError):
        weapon("dual_dagger", strikes=0)
    with pytest.raises(ValidationError):
        weapon("dual_dagger", strikes=4)


def test_trait_and_rule_lines_follow_the_data() -> None:
    core = library().ruleset.core
    dd = weapon("dual_dagger")
    assert dd.trait_lines_zh()[0].startswith("連擊：普攻一次打 2 下")
    assert dd.rule_lines_zh(core)[1].startswith("成對：算一件武器、占用雙手")
    assert any("背刺" in line for line in dd.rule_lines_zh(core))  # 近戰共用的背刺
    assert weapon("dual_dagger", strikes=3).trait_lines_zh()[0].startswith("連擊：普攻一次打 3 下")
    assert not weapon("dual_dagger", strikes=1).trait_lines_zh()  # 一下就沒有連擊行
    lines = weapon("shotgun").trait_lines_zh()
    assert "2 格：傷害 −25%" in lines
    assert "3 格：傷害 −50%" in lines
    assert "4 格：傷害 −75%" in lines
    assert any(line.startswith("彈匣 1 發") for line in lines)
    assert any(line.startswith("彈匣 2 發") for line in weapon("pistol").trait_lines_zh())
    assert weapon("pistol").rule_lines_zh(core)[1].startswith("單手")
    dp = weapon("dual_pistol")
    assert any(line.startswith("彈匣 4 發") for line in dp.trait_lines_zh())
    assert dp.rule_lines_zh(core)[1].startswith("成對")
    assert not any("背刺" in line for line in dp.rule_lines_zh(core))


# ---------------------------------------------------------------------------
# 雙匕首：普攻兩下，背刺時兩下都吃加成
# ---------------------------------------------------------------------------


def _duel(facing: str, w: WeaponDef | None = None, foe_hp: int = 200) -> BattleState:
    """U1 拿雙匕首站在 (3, 2)，U2 在 (2, 2) 朝 ``facing``：朝西時 U1 在它背後，朝東時在正面。"""
    state = state_of(
        [
            armed(Team.ALLY, (3, 2), w or weapon("dual_dagger")),
            foe((2, 2), max_hp=foe_hp, resist={}),
        ]
    )
    state.units[U2].facing = facing  # type: ignore[assignment]
    return state


STRIKE_TABLE = [
    # (說明, 敵人朝向, d20, (期望擲命中次數, 期望傷害次數, 期望背刺值))
    ("正面命中：兩下", "east", 15, (2, 2, 0)),
    ("背後命中：兩下都背刺", "west", 15, (2, 2, 2)),
    ("正面失手：兩下都沒中", "east", 1, (2, 0, 0)),
    ("背後失手：兩下都背刺但沒中", "west", 1, (2, 0, 2)),
]


@pytest.mark.parametrize(("name", "facing", "d20", "counts"), STRIKE_TABLE)
def test_dual_dagger_basic_attack_strikes_twice(
    name: str, facing: str, d20: int, counts: tuple[int, int, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    rolls, damages, backstab = counts
    dice(monkeypatch, d20=d20)
    events = shoot(_duel(facing))
    rolled = kinds(events, AttackRolled)
    dealt = kinds(events, DamageDealt)
    assert len(rolled) == rolls, name
    assert len(dealt) == damages, name
    assert all(r.backstab == backstab for r in rolled), name
    if backstab:  # 背刺：命中 +2、暴擊範圍 +1（兩下各自）
        assert all(r.hit_modifier + r.proficiency + 2 <= r.total for r in rolled if r.natural > 1)
    for d in dealt:
        assert d.rolls and len(d.rolls) in (1, 2)  # 1d4（暴擊時多擲一組）


def test_each_strike_rolls_its_own_attack_and_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    """兩下各自擲命中：第一下命中、第二下失手時只有一筆傷害。"""
    state = _duel("east")  # 先建好戰場（開戰的先攻也擲 d20），再固定骰值
    d20s = iter([15, 1])  # 第一下 d20=15（命中）、第二下 d20=1（失手）
    monkeypatch.setattr(
        "trpg.shared.rng.Rng.roll", lambda self, sides: next(d20s, 1) if sides == 20 else 3
    )
    events = shoot(state)
    rolled = kinds(events, AttackRolled)
    assert [r.hit for r in rolled] == [True, False]
    assert len(kinds(events, DamageDealt)) == 1


def test_dual_dagger_stops_when_the_first_strike_kills(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=15, die=4)
    events = shoot(_duel("east", foe_hp=1))
    assert len(kinds(events, AttackRolled)) == 1
    assert len(kinds(events, DamageDealt)) == 1


def test_changing_strikes_changes_the_number_of_strikes(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch, d20=15)
    for strikes in (1, 2, 3):
        events = shoot(_duel("east", weapon("dual_dagger", strikes=strikes)))
        assert len(kinds(events, AttackRolled)) == strikes
    sword = state_of([armed(Team.ALLY, (3, 2), weapon("one_handed_sword")), foe((2, 2))])
    assert len(kinds(shoot(sword), AttackRolled)) == 1  # 其他武器不連擊


def test_dual_dagger_weapon_skill_hits_only_once() -> None:
    skill = _weapon_skill("melee", 2)
    state = battle(skill, [(4, 3)], caster=(3, 3), base="hero_fighter")
    state.units[U1].weapon = weapon("dual_dagger")
    result = cast(hit_with(state), target_id=U2)
    assert len([e for e in of(result, DamageDealt) if e.source_id == U1]) == 1
    assert len(of(result, AttackRolled)) == 1


# ---------------------------------------------------------------------------
# 霰彈槍：依距離 1／2／3／4 格 ＝ 100／75／50／25%
# ---------------------------------------------------------------------------

SHOTGUN_TABLE = [
    # (距離, 傷害千分比, 命中修正)
    (1, 1000, 0),
    (2, 750, 0),
    (3, 500, 0),
    (4, 250, 0),
]


@pytest.mark.parametrize(("distance", "permille", "hit_mod"), SHOTGUN_TABLE)
@pytest.mark.parametrize("moved", [False, True])
def test_shotgun_damage_falls_with_distance_and_has_no_steady_bonus(
    distance: int, permille: int, hit_mod: int, moved: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(1 + distance, 2), moved=moved, gun=weapon("shotgun"))
    events = shoot(state)
    (roll,) = kinds(events, AttackRolled)
    (dealt,) = kinds(events, DamageDealt)
    assert dealt.multiplier_permille == permille
    assert roll.modifier_bonus == hit_mod  # 站定與移動後都一樣：沒有站定、貼臉懲罰
    assert roll.crit is False


def test_shotgun_damage_really_drops_with_distance(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    amounts = [
        kinds(shoot(gun_state(target_at=(1 + d, 2), gun=weapon("shotgun"))), DamageDealt)[0].amount
        for d in (1, 2, 3, 4)
    ]
    assert amounts == sorted(amounts, reverse=True) and len(set(amounts)) == 4


def test_shotgun_range_is_four_and_changing_the_data_changes_the_falloff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    far = gun_state(target_at=(6, 2), gun=weapon("shotgun"))  # 5 格：射程外
    assert attack_problem(far, far.units[U1], far.units[U2]) is not None
    mods = [{"min_distance": 2, "damage_permille": 900}]
    state = gun_state(target_at=(3, 2), gun=weapon("shotgun", range_mod=mods))
    (dealt,) = kinds(shoot(state), DamageDealt)
    assert dealt.multiplier_permille == 900


def test_shotgun_fires_one_shell_gunshot_and_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(3, 2), gun=weapon("shotgun"))
    assert state.units[U1].ammo == 1
    after = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert after.units[U1].ammo == 0
    assert Reload(unit_id=U1) in legal_actions(after)
    assert not [a for a in legal_actions(after) if isinstance(a, Attack)]
    reloaded = resolve(after, Reload(unit_id=U1))
    assert reloaded.state.units[U1].ammo == 1
    assert reloaded.state.units[U1].ap == after.units[U1].ap - 1


# ---------------------------------------------------------------------------
# 手槍：單手、彈匣 2、沒有任何位置修正
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("distance", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("moved", [False, True])
def test_pistol_has_no_steady_range_or_point_blank_modifiers(
    distance: int, moved: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(1 + distance, 2), moved=moved, gun=weapon("pistol"))
    events = shoot(state)
    (roll,) = kinds(events, AttackRolled)
    (dealt,) = kinds(events, DamageDealt)
    assert roll.modifier_bonus == 0 and dealt.multiplier_permille == 1000


def test_pistol_range_is_five() -> None:
    state = gun_state(target_at=(7, 2), gun=weapon("pistol"))  # 6 格
    assert attack_problem(state, state.units[U1], state.units[U2]) is not None


def test_pistol_holds_two_shots_before_it_needs_a_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(4, 2), gun=weapon("pistol"))
    assert state.units[U1].ammo == 2
    assert not [a for a in legal_actions(state) if isinstance(a, Reload)]
    one = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    assert one.units[U1].ammo == 1
    assert not [a for a in legal_actions(one) if isinstance(a, Reload)]  # 還有子彈不能裝填
    two = resolve(one, Attack(unit_id=U1, target_id=U2)).state
    assert two.units[U1].ammo == 0
    problem = attack_problem(two, two.units[U1], two.units[U2])
    assert problem is not None and "空膛" in problem
    reloaded = resolve(two, Reload(unit_id=U1))
    assert reloaded.state.units[U1].ammo == 2
    (event,) = kinds(reloaded.events, WeaponReloaded)
    assert (event.ammo, event.cost) == (2, 1)


def test_pistol_is_one_handed_and_allows_an_offhand() -> None:
    lib = library()
    pistol = lib.weapons["pistol"]
    assert loadout_problems(_loadout(off_hand="item_offhand_round_shield"), pistol, _rules()) == []


# ---------------------------------------------------------------------------
# 雙手槍：成對、彈匣 2＋2、1 AP 裝滿
# ---------------------------------------------------------------------------


def test_dual_pistol_has_four_shots_and_one_ap_refills_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(4, 2), gun=weapon("dual_pistol"))
    state.units[U1].ap = 9
    assert state.units[U1].ammo == 4
    for left in (3, 2, 1, 0):  # 四發：前兩發用一把，後兩發用另一把
        state = resolve(state, Attack(unit_id=U1, target_id=U2)).state
        assert state.units[U1].ammo == left
    assert not [a for a in legal_actions(state) if isinstance(a, Attack)]
    start_ap = state.units[U1].ap
    reloaded = resolve(state, Reload(unit_id=U1))
    assert reloaded.state.units[U1].ammo == 4  # 一次裝滿
    assert reloaded.state.units[U1].ap == start_ap - 1  # 1 AP
    (event,) = kinds(reloaded.events, WeaponReloaded)
    assert (event.ammo, event.cost) == (4, 1)


def test_dual_pistol_has_no_position_modifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    for distance in (1, 3, 5):
        state = gun_state(target_at=(1 + distance, 2), gun=weapon("dual_pistol"))
        events = shoot(state)
        (roll,) = kinds(events, AttackRolled)
        (dealt,) = kinds(events, DamageDealt)
        assert roll.modifier_bonus == 0 and dealt.multiplier_permille == 1000


def test_dual_pistol_gunshot_reveals_the_shooter() -> None:
    assert weapon("dual_pistol").gunshot and weapon("pistol").gunshot and weapon("shotgun").gunshot


# ---------------------------------------------------------------------------
# 成對武器占雙手；工坊勾選框自動出現
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wid", ["dual_dagger", "dual_pistol"])
def test_paired_weapons_block_the_offhand_even_without_the_paired_item(wid: str) -> None:
    lib = library()
    w = lib.weapons[wid]
    problems = loadout_problems(_loadout(off_hand="item_offhand_round_shield"), w, _rules())
    assert any("成對武器" in p for p in problems)
    with_item = _loadout(main_hand=f"item_{wid}", off_hand="item_offhand_round_shield")
    assert any("成對武器" in p for p in loadout_problems(with_item, w, _rules()))
    assert loadout_problems(_loadout(main_hand=f"item_{wid}"), w, _rules()) == []


@pytest.mark.parametrize("wid", ["one_handed_sword", "pistol", "dagger"])
def test_non_paired_single_handed_weapons_still_take_an_offhand(wid: str) -> None:
    w = library().weapons[wid]
    assert loadout_problems(_loadout(off_hand="item_offhand_round_shield"), w, _rules()) == []


def test_the_workshop_pairable_flag_appears_for_the_paired_weapons() -> None:
    catalog = gear_catalog(library())
    pairable = {w.id for w in catalog.weapons if w.pairable}
    assert pairable == {"dual_dagger", "dual_pistol"}  # 單手劍、匕首、手槍、所有雙手武器都不顯示
    items = {i.id: i for i in catalog.items}
    assert items["item_dual_dagger"].paired and items["item_dual_pistol"].paired
    assert items["item_dual_dagger"].weapon == "dual_dagger"


# ---------------------------------------------------------------------------
# 行為一致：普攻與武器技的骰外加成＝卡片「目前 +N」
# ---------------------------------------------------------------------------

ATTR_TABLE: list[tuple[str, dict[str, int]]] = [
    ("dual_dagger", {"dex": 20}),
    ("dual_dagger", {"dex": 13, "str": 30}),  # 只吃敏捷
    ("shotgun", {"dex": 17}),
    ("shotgun", {"dex": 9}),
    ("pistol", {"dex": 22}),
    ("pistol", {"dex": 11}),
    ("dual_pistol", {"dex": 16}),
    ("dual_pistol", {"dex": 12, "int": 40}),
]

_CURRENT = re.compile(r"目前 \+(\d+)")


def _current(line: str) -> int:
    found = _CURRENT.search(plain_text(line))
    assert found is not None, line
    return int(found.group(1))


def _getter(state: BattleState, unit: UnitState) -> Any:
    return lambda a: effective_attribute(state.ruleset, unit, a)


def _attack_state(weapon_id: str, attrs: dict[str, int]) -> BattleState:
    foe_x = 2 + min(library().weapons[weapon_id].range, 2)  # 霰彈槍也貼近打，避開距離衰減
    return state_of(
        [
            armed(Team.ALLY, (2, 2), weapon(weapon_id), attributes=attrs),
            foe((foe_x, 2), resist={}),
        ]
    )


@pytest.mark.parametrize(("weapon_id", "attrs"), ATTR_TABLE)
def test_basic_attack_damage_matches_the_card_current_bonus(
    weapon_id: str, attrs: dict[str, int], monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    state = _attack_state(weapon_id, attrs)
    unit = state.units[U1]
    line = unit.weapon.attack_formula_zh(state.ruleset.core, _getter(state, unit))
    now = _current(line)
    dealt = [e for e in kinds(shoot(state), DamageDealt) if e.source_id == U1]
    assert len(dealt) == unit.weapon.strikes
    for d in dealt:  # 連擊的每一下都吃同樣的加成
        assert d.scaled_permille // 1000 == now
        if d.scaled_permille % 1000 == 0 and d.multiplier_permille == 1000:
            assert d.amount == sum(d.rolls) + now


def _weapon_skill(weapon_class: str, reach: int) -> SkillDef:
    base = make_skill(
        SID, {"type": "single", "range": reach}, [{"type": "damage"}], category="weapon"
    )
    return SkillDef.model_validate({**base.model_dump(mode="json"), "weapon_req": weapon_class})


def _base_of(w: WeaponDef) -> str:
    """技能的武器大類要求在開戰時就檢查，所以遠程武器用弓手範本開戰、再換成要測的武器。"""
    return "hero_archer" if w.weapon_class == "ranged" else "hero_fighter"


@pytest.mark.parametrize(("weapon_id", "attrs"), ATTR_TABLE)
def test_weapon_skill_damage_matches_the_card_current_bonus(
    weapon_id: str, attrs: dict[str, int]
) -> None:
    w = library().weapons[weapon_id]
    skill = _weapon_skill(w.weapon_class, 2)
    state = battle(skill, [(4, 3)], caster=(3, 3), base=_base_of(w))
    unit = state.units[U1]
    unit.weapon = w
    unit.ammo = w.magazine
    for name, value in attrs.items():
        unit.attributes[Attribute(name)] = value
    lines = skill.formula_lines_zh(state.ruleset.core, unit.weapon, _getter(state, unit))
    damage_line = next(line for line in lines if "目前" in line)
    assert unit.weapon.scaling_names_zh() in damage_line
    result = cast(hit_with(state), target_id=U2)
    (dealt,) = [e for e in of(result, DamageDealt) if e.source_id == U1]
    assert dealt.scaled_permille // 1000 == _current(damage_line)


@pytest.mark.parametrize("weapon_id", ["shotgun", "pistol", "dual_pistol"])
def test_firearm_weapon_skills_spend_a_round_and_need_ammo(weapon_id: str) -> None:
    w = library().weapons[weapon_id]
    skill = _weapon_skill("ranged", 4)
    state = battle(skill, [(4, 3)], caster=(3, 3), base=_base_of(w))
    unit = state.units[U1]
    unit.weapon = w
    unit.ammo = w.magazine
    result = cast(hit_with(state), target_id=U2)
    assert result.state.units[U1].ammo == w.magazine - 1  # 武器技也算開火
    empty = hit_with(state)
    empty.units[U1].ammo = 0
    with pytest.raises(IllegalActionError):
        cast(empty, target_id=U2)


# ---------------------------------------------------------------------------
# AI、開局與模擬 build
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("weapon_id", ["shotgun", "pistol", "dual_pistol"])
def test_simple_ai_reloads_the_empty_new_firearms(
    weapon_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    state = gun_state(target_at=(3, 2), gun=weapon(weapon_id))
    state.units[U1].ammo = 0
    assert choose_action(state) == Reload(unit_id=U1)


def test_the_new_weapons_are_in_the_start_pool_and_have_blank_builds() -> None:
    lib = library()
    pool = set(start_weapons(lib))
    assert set(NEW_WEAPONS) <= pool
    builds = {b.id: b for b in lib.builds.builds}
    for wid in NEW_WEAPONS:
        b = builds[f"build_blank_{wid}"]
        assert b.blank and b.hero.weapon == wid and not b.hero.skills


def test_other_weapons_read_the_effective_attribute() -> None:
    """保險：新武器的縮放屬性都是敏捷（08 武器表），不吃別的屬性。"""
    for wid in NEW_WEAPONS:
        w = library().weapons[wid]
        assert w.scaling_attr is Attribute.DEX and w.secondary_scaling_attr is None
