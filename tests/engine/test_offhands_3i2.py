"""副手（Phase 3I-2，``docs/phases/Phase3I計畫.md``；08 8.11 副手表，玩法決定 #46）。

圓盾（力量／體質取較高；格擋反應強化依縮放屬性）、塔盾（體質；遠程攻擊打你時命中同半掩護、
攻擊者高 1 層以上無視；移動 −1）、法書（智力；法術技傷害 +10%，計入全身 +50% 上限）、法器珠
（智力／意志取較高；法術技施放距離 +1，不加範圍、射程為自身的不受影響）。

行為一致測試（流程改善 B）：塔盾掩護、法書加成、法器珠射程、圓盾格擋各一組引擎表格測試；
卡片（``OffhandDef.trait_lines_zh``、單位檢視）顯示的數值與實際結算一致。
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast, hit_with, of
from tests.engine.test_weapons_24a1 import U1, U2, armed, dice, hit, kinds, state_of, weapon
from trpg.content.battle import OffhandDef
from trpg.content.equipment import Loadout, loadout_problems, resolve_loadout
from trpg.engine import BattleState, UseSkill, resolve
from trpg.engine.events import AttackRolled, DamageDealt
from trpg.engine.gear import cap_damage_bonus
from trpg.engine.gear_state import GearBonus
from trpg.engine.modifiers import ATTACK, damage_permille, skill_use
from trpg.engine.rules.statuses import effective_attribute, move_points_for_turn
from trpg.engine.setup import UnitSpawn
from trpg.engine.skills.conditions import Subject
from trpg.engine.skills.targeting import compute_area, shape_reach
from trpg.engine.view import project_for
from trpg.roguelite.start import ChoiceError, check_test_equipment
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Attribute, Pos, Team

SHIELD_ITEM = {
    "round_shield": "item_offhand_round_shield",
    "tower_shield": "item_offhand_tower_shield",
    "tome": "item_offhand_tome",
    "orb": "item_offhand_orb",
}


def offhand(offhand_id: str, **changes: Any) -> OffhandDef:
    """副手資料的複本，可以覆寫參數（驗證「改資料行為跟著變」）。"""
    data = library().offhands[offhand_id].model_dump(mode="json")
    return OffhandDef.model_validate({**data, **changes})


def loadout_of(offhand_id: str) -> Loadout:
    lib = library()
    return resolve_loadout({"off_hand": SHIELD_ITEM[offhand_id]}, lib.items, lib.affixes)


def holding(spawn: UnitSpawn, offhand_id: str) -> UnitSpawn:
    """單位的副手換成 ``offhand_id``（走完整的 裝備快照 → build_gear 路徑）。"""
    return spawn.model_copy(update={"equipment": loadout_of(offhand_id)})


def give_offhand(state: BattleState, unit_id: str, offhand_id: str) -> None:
    """直接把副手寫進單位的裝備狀態（改資料參數的測試用）。"""
    unit = state.units[unit_id]
    unit.gear = dataclasses.replace(unit.gear, offhand=library().offhands[offhand_id])


# ---------------------------------------------------------------------------
# 資料、schema、裝備欄相容性
# ---------------------------------------------------------------------------


def test_offhands_are_data_with_the_designed_parameters() -> None:
    o = library().offhands
    assert set(o) == {"round_shield", "tower_shield", "tome", "orb"}
    rs, ts, tome, orb = o["round_shield"], o["tower_shield"], o["tome"], o["orb"]
    assert (rs.scaling_attr, rs.secondary_scaling_attr, rs.attr_mode) == ("str", "con", "max")
    assert rs.block_bonus is not None
    assert (ts.scaling_attr, ts.secondary_scaling_attr) == ("con", None)
    assert (ts.ranged_cover, ts.move_penalty) == (True, 1)
    assert (tome.scaling_attr, tome.spell_damage_permille) == ("int", 100)
    assert (orb.scaling_attr, orb.secondary_scaling_attr, orb.attr_mode) == ("int", "wil", "max")
    assert orb.spell_range_bonus == 1


def test_the_schema_applies_the_dual_attribute_rule_to_offhands() -> None:
    with pytest.raises(ValidationError, match="attr_mode"):
        offhand("round_shield", attr_mode="mean")
    with pytest.raises(ValidationError, match="attr_mode"):
        offhand("orb", attr_mode="mean")
    with pytest.raises(ValidationError, match="secondary_scaling_attr"):
        offhand("orb", secondary_scaling_attr="int")


def test_offhand_items_embed_their_definition_into_the_equipment_snapshot() -> None:
    lib = library()
    for offhand_id, item_id in SHIELD_ITEM.items():
        item = lib.items[item_id]
        assert item.slot_type == "offhand" and item.offhand == offhand_id
        assert item.offhand_def == lib.offhands[offhand_id]
    # 舊的副手物品（沒有 offhand）沒有基礎特性
    assert lib.items["item_test_shield"].offhand_def is None


def test_only_offhand_items_may_name_an_offhand() -> None:
    lib = library()
    data = lib.items["item_test_sword"].model_dump(mode="json")
    with pytest.raises(ValidationError, match="offhand"):
        type(lib.items["item_test_sword"]).model_validate({**data, "offhand": "tome"})


@pytest.mark.parametrize("offhand_id", sorted(SHIELD_ITEM))
@pytest.mark.parametrize(
    ("main", "legal"),
    [
        ("one_handed_sword", True),
        ("scepter", True),  # 單手法器
        ("whip", True),
        ("hammer", False),  # 雙手
        ("fist", False),
        ("fire_staff", False),
    ],
)
def test_two_handed_weapons_cannot_hold_an_offhand(offhand_id: str, main: str, legal: bool) -> None:
    lib = library()
    problems = loadout_problems(loadout_of(offhand_id), lib.weapons[main], lib.ruleset.equipment)
    assert (problems == []) is legal, problems


def test_a_second_weapon_is_not_an_offhand() -> None:
    lib = library()
    bad = resolve_loadout({"off_hand": "item_test_sword"}, lib.items, lib.affixes)
    problems = loadout_problems(bad, lib.weapons["one_handed_sword"], lib.ruleset.equipment)
    assert any("副手不能放第二把武器" in p for p in problems)


def test_test_mode_can_pick_each_offhand() -> None:
    """測試模式挑的裝備（開局的 ``test_equipment``）走 ``check_test_equipment``：合法就過。"""
    lib = library()
    for item_id in SHIELD_ITEM.values():
        check_test_equipment(lib, "one_handed_sword", {"off_hand": item_id})
    with pytest.raises(ChoiceError, match="副手被占用"):
        check_test_equipment(lib, "hammer", {"off_hand": SHIELD_ITEM["tome"]})


# ---------------------------------------------------------------------------
# 塔盾：遠程掩護（命中 −2，同半掩護）、移動 −1
# ---------------------------------------------------------------------------

FLAT = "\n".join(["0000000"] * 5)
ATTACKER_HIGH = "\n".join(["0000000", "0000000", "0010000", "0000000", "0000000"])
TARGET_HIGH = "\n".join(["0000000", "0000000", "0000100", "0000000", "0000000"])

COVER_TABLE = [
    # (說明, 攻擊者武器, 地形高度, 目標副手, 場上掩護物, 期望的掩護修正)
    ("遠程打塔盾", "bow", FLAT, "tower_shield", False, -2),
    ("遠程打沒有塔盾的人", "bow", FLAT, None, False, 0),
    ("遠程打圓盾（沒有掩護特性）", "bow", FLAT, "round_shield", False, 0),
    ("近戰打塔盾", "one_handed_sword", FLAT, "tower_shield", False, 0),
    ("長柄（矛）打塔盾", "spear", FLAT, "tower_shield", False, 0),
    ("攻擊者高 1 層", "bow", ATTACKER_HIGH, "tower_shield", False, 0),
    ("攻擊者低 1 層", "bow", TARGET_HIGH, "tower_shield", False, -2),
    ("無視掩護的火槍", "longgun", FLAT, "tower_shield", False, 0),
    ("塔盾加場上掩護物不疊加", "bow", FLAT, "tower_shield", True, -2),
    ("只有場上掩護物", "bow", FLAT, None, True, -2),
]


@pytest.mark.parametrize("row", COVER_TABLE, ids=[row[0] for row in COVER_TABLE])
def test_tower_shield_cover_table(row: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch) -> None:
    label, attacker, heights, held, crate, expected = row
    dice(monkeypatch)
    distance = min(3, weapon(attacker).range)
    target = armed(Team.ALLY, (2 + distance, 2), weapon("one_handed_sword"))
    if held is not None:
        target = holding(target, held)
    # 目標旁邊、朝向攻擊者一側的掩護物
    objects = [(2 + distance - 1, 2, "crate")] if crate else []
    state = state_of(
        [armed(Team.ENEMY, (2, 2), weapon(attacker), base="bandit"), target],
        heights=heights,
        objects=objects,
    )
    (rolled,) = kinds(hit(state), AttackRolled)
    assert rolled.cover == expected, label


def test_tower_shield_cover_matches_the_card_and_follows_the_rule_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """卡片的數字取自 ``core.half_cover_hit_penalty``，實際扣的也是它。"""
    dice(monkeypatch)
    state = state_of(
        [
            armed(Team.ENEMY, (2, 2), weapon("bow"), base="bandit"),
            holding(armed(Team.ALLY, (5, 2), weapon("one_handed_sword")), "tower_shield"),
        ]
    )
    core = state.ruleset.core
    card = library().offhands["tower_shield"].trait_lines_zh(core)
    assert any(f"命中 −{core.half_cover_hit_penalty}（同半掩護" in line for line in card)
    (rolled,) = kinds(hit(state), AttackRolled)
    assert rolled.cover == -core.half_cover_hit_penalty
    assert rolled.cover_object_id is None  # 不是場上的物件


def test_tower_shield_slows_the_holder_by_one() -> None:
    plain = state_of(
        [
            armed(Team.ENEMY, (2, 2), weapon("bow"), base="bandit"),
            armed(Team.ALLY, (5, 2), weapon("one_handed_sword")),
        ]
    )
    shielded = state_of(
        [
            armed(Team.ENEMY, (2, 2), weapon("bow"), base="bandit"),
            holding(armed(Team.ALLY, (5, 2), weapon("one_handed_sword")), "tower_shield"),
        ]
    )
    base = move_points_for_turn(plain.ruleset, plain.units[U2])
    assert move_points_for_turn(shielded.ruleset, shielded.units[U2]) == base - 1
    assert shielded.units[U2].speed == plain.units[U2].speed - 1
    # 其他副手不減速
    for offhand_id in ("round_shield", "tome", "orb"):
        other = state_of(
            [
                armed(Team.ENEMY, (2, 2), weapon("bow"), base="bandit"),
                holding(armed(Team.ALLY, (5, 2), weapon("one_handed_sword")), offhand_id),
            ]
        )
        assert other.units[U2].speed == plain.units[U2].speed
    line = next(x for x in library().offhands["tower_shield"].trait_lines_zh(plain.ruleset.core))
    assert line.startswith("縮放屬性：體質")


def test_tower_shield_move_penalty_follows_the_data() -> None:
    state = state_of(
        [
            armed(Team.ENEMY, (2, 2), weapon("bow"), base="bandit"),
            armed(Team.ALLY, (5, 2), weapon("one_handed_sword")),
        ]
    )
    for penalty in (1, 2):
        item = library().items[SHIELD_ITEM["tower_shield"]]
        item = item.model_copy(
            update={"offhand_def": offhand("tower_shield", move_penalty=penalty)}
        )
        lib = library()
        loadout = resolve_loadout({"off_hand": item.id}, {**lib.items, item.id: item}, lib.affixes)
        spawn = armed(Team.ALLY, (5, 2), weapon("one_handed_sword")).model_copy(
            update={"equipment": loadout}
        )
        shielded = state_of([armed(Team.ENEMY, (2, 2), weapon("bow"), base="bandit"), spawn])
        assert shielded.units[U2].speed == state.units[U2].speed - penalty


# ---------------------------------------------------------------------------
# 法書：法術技傷害 +10%，計入全身 +50% 上限
# ---------------------------------------------------------------------------


def _mage_state() -> BattleState:
    return state_of(
        [
            armed(Team.ALLY, (2, 2), weapon("fire_staff"), base="hero_mage"),
            armed(Team.ENEMY, (4, 2), weapon("one_handed_sword"), base="bandit"),
        ]
    )


def _effects(category: str) -> list[dict[str, Any]]:
    if category == "weapon":  # 武器技的傷害骰來自武器
        return [{"type": "damage"}]
    return [{"type": "damage", "dice": "1d4", "element": "fire"}]


def _use(category: str) -> Any:
    shape = {"type": "single", "range": 3}
    return skill_use(make_skill(SID, shape, _effects(category), category=category))


TOME_TABLE = [
    # (說明, 使用, 期望倍率‰)
    ("法術技", "spell", 1100),
    ("武器技", "weapon", 1000),
    ("普攻", "attack", 1000),
]


@pytest.mark.parametrize("row", TOME_TABLE, ids=[row[0] for row in TOME_TABLE])
def test_tome_raises_spell_skill_damage_only(row: tuple[str, str, int]) -> None:
    _label, kind, expected = row
    state = _mage_state()
    give_offhand(state, U1, "tome")
    unit, foe = state.units[U1], state.units[U2]
    use = ATTACK if kind == "attack" else _use(kind)
    assert damage_permille(state, unit, use, Subject(foe, foe.xy)) == expected
    plain = _mage_state()
    assert damage_permille(plain, plain.units[U1], use, Subject(foe, foe.xy)) == 1000


def test_tome_bonus_follows_the_data_and_the_card() -> None:
    state = _mage_state()
    unit, foe = state.units[U1], state.units[U2]
    for permille in (100, 250):
        unit.gear = dataclasses.replace(
            unit.gear, offhand=offhand("tome", spell_damage_permille=permille)
        )
        assert damage_permille(state, unit, _use("spell"), Subject(foe, foe.xy)) == 1000 + permille
        card = unit.gear.offhand.trait_lines_zh(state.ruleset.core)  # type: ignore[union-attr]
        assert f"法術技傷害 +{permille / 10:g}%" in card[1]


def test_tome_bonus_counts_toward_the_whole_body_cap() -> None:
    """法書的 +10% 和其他來源一起套 +50% 上限（裝備代價型 +20% ×2 遞減、再加法書）。"""
    state = _mage_state()
    caps = state.ruleset.equipment.caps.damage_bonus_permille
    unit, foe = state.units[U1], state.units[U2]
    give_offhand(state, U1, "tome")
    other = 480  # 其他來源的加成：再加 100 就超過 500 上限
    bonus = GearBonus("affix_cost_glass", "damage_permille", other)
    unit.gear = dataclasses.replace(unit.gear, bonuses=(*unit.gear.bonuses, bonus))
    total = damage_permille(state, unit, _use("spell"), Subject(foe, foe.xy))
    assert total == 1000 + cap_damage_bonus(state.ruleset, other + 100) == 1000 + caps


def test_tome_damage_shows_up_in_real_spell_damage() -> None:
    """實際施放：法書讓法術技的傷害乘 1.1（無條件捨去）。"""
    skill = make_skill(
        SID, {"type": "single", "range": 3}, [{"type": "damage", "dice": "1d4", "element": "fire"}]
    )
    plain = battle(skill, [(5, 3)])
    booked = battle(skill, [(5, 3)])
    give_offhand(booked, U1, "tome")
    a = [
        e
        for e in of(cast(hit_with(plain, [(4, 4)]), target_id=U2), DamageDealt)
        if e.source_id == U1
    ]
    b = [
        e
        for e in of(cast(hit_with(booked, [(4, 4)]), target_id=U2), DamageDealt)
        if e.source_id == U1
    ]
    assert len(a) == len(b) == 1
    assert b[0].scaled_permille == a[0].scaled_permille  # 縮放加成不變
    assert (a[0].multiplier_permille, b[0].multiplier_permille) == (1000, 1100)
    assert b[0].amount >= a[0].amount


# ---------------------------------------------------------------------------
# 法器珠：法術技施放距離 +1（不加範圍大小、射程為自身的不受影響）
# ---------------------------------------------------------------------------

DMG = [{"type": "damage", "dice": "1d4", "element": "fire"}]
REACH_TABLE: list[tuple[str, dict[str, Any], str, int, int]] = [
    # (說明, 形狀, 類別, 沒有法器珠的射程, 有法器珠的射程)
    ("單體法術", {"type": "single", "range": 3}, "spell", 3, 4),
    ("連鎖法術", {"type": "chain", "range": 4, "jumps": 2, "jump_range": 2}, "spell", 4, 5),
    ("十字（落點）法術", {"type": "cross", "range": 3}, "spell", 3, 4),
    ("以自身為中心的十字（射程 0）", {"type": "cross", "range": 0}, "spell", 0, 0),
    ("射程為自身（self）", {"type": "self"}, "spell", 0, 0),
    ("武器技不受影響", {"type": "single", "range": 3}, "weapon", 3, 3),
]


@pytest.mark.parametrize("row", REACH_TABLE, ids=[row[0] for row in REACH_TABLE])
def test_orb_extends_spell_cast_distance_table(row: tuple[Any, ...]) -> None:
    _label, shape, category, plain_reach, orb_reach = row
    skill = make_skill(SID, shape, _effects(category), category=category)
    base = "hero_fighter" if category == "weapon" else "hero_mage"
    plain = battle(skill, [(6, 3)], base=base)
    orbed = battle(skill, [(6, 3)], base=base)
    give_offhand(orbed, U1, "orb")
    assert shape_reach(plain, skill, plain.units[U1]) == plain_reach
    assert shape_reach(orbed, skill, orbed.units[U1]) == orb_reach


def test_orb_lets_a_spell_reach_one_tile_further_and_keeps_the_area_size() -> None:
    skill = make_skill(SID, {"type": "single", "range": 3}, DMG)
    far = (6, 3)  # 距離 4（地圖寬 7）
    plain = battle(skill, [far], caster=(2, 3))
    with pytest.raises(IllegalActionError):
        resolve(plain, cast_action(plain))
    orbed = battle(skill, [far], caster=(2, 3))
    give_offhand(orbed, U1, "orb")
    assert of(cast(hit_with(orbed), target_id=U2), DamageDealt)
    # 範圍大小不變（十字的範圍格數與沒有法器珠時一樣）
    cross = make_skill(SID, {"type": "cross", "range": 3}, DMG)
    a, b = battle(cross, [(5, 3)]), battle(cross, [(5, 3)])
    give_offhand(b, U1, "orb")
    ta = project_tiles(a, cross, (5, 3))
    tb = project_tiles(b, cross, (5, 3))
    assert ta == tb and len(ta) == 5


def cast_action(state: BattleState) -> Any:
    return UseSkill(unit_id=U1, skill_id=SID, target_id=U2)


def project_tiles(state: BattleState, skill: Any, xy: tuple[int, int]) -> list[Any]:
    action = UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=xy[0], y=xy[1]))
    return list(compute_area(state, state.units[U1], skill, action).tiles)


def test_orb_bonus_follows_the_data_and_the_card() -> None:
    skill = make_skill(SID, {"type": "single", "range": 3}, DMG)
    state = battle(skill, [(6, 3)])
    unit = state.units[U1]
    for bonus in (1, 2):
        unit.gear = dataclasses.replace(unit.gear, offhand=offhand("orb", spell_range_bonus=bonus))
        assert shape_reach(state, skill, unit) == 3 + bonus
        card = unit.gear.offhand.trait_lines_zh(state.ruleset.core)  # type: ignore[union-attr]
        assert f"法術技施放距離 +{bonus}" in card[1]


# ---------------------------------------------------------------------------
# 圓盾：格擋反應強化（依縮放屬性：力量／體質取較高）
# ---------------------------------------------------------------------------

BLOCK_TABLE = [
    # (力量, 體質, 期望多減傷‰)  每點 5‰，最多 100‰
    (10, 10, 50),
    (14, 8, 70),  # 取較高：力量
    (6, 12, 60),  # 取較高：體質
    (20, 5, 100),  # 到上限
    (30, 30, 100),
]
_PCT = re.compile(r"目前 \+([\d.]+)%")


def _block_state(attrs: dict[str, int], held: str | None = "round_shield") -> BattleState:
    target = armed(Team.ALLY, (3, 2), weapon("one_handed_sword"), attributes=attrs, reactions=None)
    if held is not None:
        target = holding(target, held)
    return state_of([armed(Team.ENEMY, (2, 2), weapon("one_handed_sword"), base="bandit"), target])


@pytest.mark.parametrize(("strength", "con", "extra"), BLOCK_TABLE)
def test_round_shield_strengthens_block_by_the_scaling_attribute(
    strength: int, con: int, extra: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch)
    attrs = {"str": strength, "con": con}
    state = _block_state(attrs)
    (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.target_id == U2]
    assert dealt.block_permille == 1000 - 500 - extra
    # 沒有圓盾：只有格擋反應本身的減半
    plain = _block_state(attrs, held=None)
    (base,) = [e for e in kinds(hit(plain), DamageDealt) if e.target_id == U2]
    assert base.block_permille == 500
    assert dealt.amount <= base.amount
    # 卡片的「目前 +N%」＝ 實際多減傷
    unit = state.units[U2]
    card = unit.gear.offhand.trait_lines_zh(  # type: ignore[union-attr]
        state.ruleset.core, lambda a: effective_attribute(state.ruleset, unit, a)
    )
    shown = next(_PCT.search(line) for line in card if "目前" in line)
    assert shown is not None and float(shown.group(1)) * 10 == extra


def test_the_unit_view_card_lines_match_the_data() -> None:
    state = _block_state({"str": 14, "con": 8})
    view = next(u for u in project_for(state, Team.ALLY).units if u.id == U2)
    assert view.offhand_name_zh == "圓盾"
    assert view.offhand_traits_zh[0] == "縮放屬性：力量／體質（取較高）"
    assert "目前 +7%" in view.offhand_traits_zh[1]
    plain = _block_state({}, held=None)
    bare = next(u for u in project_for(plain, Team.ALLY).units if u.id == U2)
    assert (bare.offhand_name_zh, bare.offhand_traits_zh) == ("", ())


def test_round_shield_only_strengthens_the_block_reaction(monkeypatch: pytest.MonkeyPatch) -> None:
    """沒有格擋反應（反應規則關掉）時圓盾不減傷；其他副手不強化格擋。"""
    dice(monkeypatch)
    for held in ("tower_shield", "tome", "orb"):
        state = _block_state({"str": 20, "con": 20}, held=held)
        (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.target_id == U2]
        assert dealt.block_permille == 500, held
    state = _block_state({"str": 20, "con": 20})
    unit = state.units[U2]
    unit.reactions = tuple(r.model_copy(update={"mode": "off"}) for r in unit.reactions)
    (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.target_id == U2]
    assert dealt.block_permille == 1000


def test_block_bonus_follows_the_data(monkeypatch: pytest.MonkeyPatch) -> None:
    dice(monkeypatch)
    state = _block_state({"str": 10, "con": 10})
    unit = state.units[U2]
    unit.gear = dataclasses.replace(
        unit.gear,
        offhand=offhand("round_shield", block_bonus={"permille_per_point": 10, "max_permille": 80}),
    )
    (dealt,) = [e for e in kinds(hit(state), DamageDealt) if e.target_id == U2]
    assert dealt.block_permille == 1000 - 500 - 80  # 10 點 × 10‰ ＝ 100，被上限 80 截斷
    assert any("最多 8%" in line for line in unit.gear.offhand.trait_lines_zh(state.ruleset.core))  # type: ignore[union-attr]


def test_loadout_attribute_helpers_exist() -> None:
    """``Attribute`` 的物理／心智分類（雙屬性規則用）涵蓋六屬性。"""
    assert {a for a in Attribute if a.is_physical} == {Attribute.STR, Attribute.DEX, Attribute.CON}
