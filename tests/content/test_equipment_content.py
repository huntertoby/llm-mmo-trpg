"""裝備內容（Phase 3G-G1）：詞條白名單 31 條、11 類 schema、物品、欄位與占用規則、代價型上限。"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from tests.engine.helpers import library
from trpg.content.equipment import (
    AFFIX_CATEGORIES,
    AffixDef,
    AffixTable,
    EquipmentRules,
    ItemDef,
    Loadout,
    affix_text,
    item_problems,
    loadout_problems,
    resolve_loadout,
)
from trpg.content.slots import SLOT_TYPE_OF, SLOTS

AFFIX = TypeAdapter[AffixDef](AffixDef)

# docs/design/08-裝備.md 8.24 的 31 條（類別 → id）
WHITELIST: dict[str, tuple[str, ...]] = {
    "stat": ("affix_attr_str", "affix_max_hp", "affix_resist_fire"),
    "conditional": (
        "affix_cond_height_hit",
        "affix_cond_still_defense",
        "affix_cond_low_hp_damage",
    ),
    "keyword": ("affix_kw_burn_duration", "affix_kw_prone_damage", "affix_kw_shock_area"),
    "attack": ("affix_attack_lightning", "affix_attack_mark"),
    "weapon_trait": (
        "affix_trait_hammer_knockback",
        "affix_trait_longgun_pointblank",
        "affix_trait_axe_sunder",
    ),
    "trigger": ("affix_trig_every3_prone", "affix_trig_kill_ap", "affix_trig_thorns_burn"),
    "charge": ("affix_charge_static", "affix_charge_fury"),
    "cost": ("affix_cost_glass", "affix_cost_blood", "affix_cost_swift"),
    "action": ("affix_act_grapple", "affix_act_smoke", "affix_act_shield_wall"),
    "reaction": (
        "affix_react_ranged_block",
        "affix_react_guard_ally",
        "affix_react_double_overwatch",
    ),
    "rule": ("affix_rule_fire_mends", "affix_rule_move_any_object", "affix_rule_bleeding_wake"),
}


def _rules() -> EquipmentRules:
    return library().ruleset.equipment


def _loadout(**slots: str) -> Loadout:
    lib = library()
    return resolve_loadout(slots, lib.items, lib.affixes)


# ---------------------------------------------------------------------------
# 白名單
# ---------------------------------------------------------------------------


def test_whitelist_has_all_31_affixes_in_11_categories() -> None:
    affixes = library().affixes
    assert len(affixes) == 31
    by_category: dict[str, set[str]] = {}
    for affix in affixes.values():
        by_category.setdefault(affix.category, set()).add(affix.id)
    assert {c: set(ids) for c, ids in WHITELIST.items()} == by_category
    assert set(by_category) == set(AFFIX_CATEGORIES)


@pytest.mark.parametrize("affix_id", [a for ids in WHITELIST.values() for a in ids])
def test_every_whitelist_affix_round_trips_through_schema(affix_id: str) -> None:
    affix = library().affixes[affix_id]
    again = AFFIX.validate_python(AFFIX.dump_python(affix, mode="json"))
    assert again == affix
    value = None if affix.value is None else affix.value.max
    assert "{n}" not in affix_text(affix, value)


def test_categories_are_discriminated() -> None:
    with pytest.raises(ValidationError):
        AFFIX.validate_python(
            {"id": "affix_x", "category": "nope", "name_zh": "x", "slots": ["ring"]}
        )
    with pytest.raises(ValidationError):  # 數值類必須有 value
        AFFIX.validate_python(
            {
                "id": "affix_x",
                "category": "stat",
                "name_zh": "力量",
                "slots": ["ring"],
                "stat": "attribute",
                "attribute": "str",
            }
        )


def test_defense_conditions_must_be_self_evaluable() -> None:
    data: dict[str, Any] = {
        "id": "affix_x",
        "category": "conditional",
        "name_zh": "防禦 +{n}",
        "slots": ["body"],
        "effect": "defense",
        "condition": {"type": "height_advantage"},
        "value": {"min": 100, "max": 100},
        "value_unit": "permille",
    }
    with pytest.raises(ValidationError, match="防禦類條件數值"):
        AFFIX.validate_python(data)


def test_cost_affix_sides_must_point_the_right_way() -> None:
    data: dict[str, Any] = {
        "id": "affix_x",
        "category": "cost",
        "name_zh": "x",
        "slots": ["ring"],
        "upside": [{"stat": "damage_taken_permille", "amount": 100}],
        "downside": [{"stat": "move", "amount": -1}],
    }
    with pytest.raises(ValidationError, match="upside"):
        AFFIX.validate_python(data)


def test_rule_affix_must_be_legendary_only() -> None:
    data = {
        "id": "affix_x",
        "category": "rule",
        "name_zh": "x",
        "slots": ["ring"],
        "rule": "fire_mends_allies",
    }
    with pytest.raises(ValidationError, match="legendary_only"):
        AFFIX.validate_python(data)


def test_duplicate_affix_ids_rejected() -> None:
    affix = library().affixes["affix_max_hp"]
    with pytest.raises(ValidationError, match="重複"):
        AffixTable(affixes=(affix, affix))


# ---------------------------------------------------------------------------
# 物品
# ---------------------------------------------------------------------------


def test_test_items_cover_every_slot_with_1_to_3_affixes() -> None:
    items = library().items.values()
    kinds = Counter(i.slot_type for i in items)
    assert set(kinds) == set(SLOT_TYPE_OF.values())
    assert kinds["ring"] >= 2  # 兩個戒指欄需要兩枚不同的戒指
    assert all(1 <= len(i.affixes) <= 3 for i in items)
    implemented = {"stat", "conditional", "cost"}  # G1 的測試物品只掛已結算的類別
    lib = library()
    assert {lib.affixes[r.affix].category for i in items for r in i.affixes} <= implemented


def _item(**data: Any) -> ItemDef:
    return ItemDef.model_validate({"id": "item_x", "name_zh": "測試", **data})


def test_item_problems_detect_slot_value_and_unknown_affix() -> None:
    lib = library()

    def problems(item: ItemDef) -> list[str]:
        return item_problems(item, lib.affixes, lib.weapons, _rules())

    assert problems(_item(slot_type="ring", affixes=[{"affix": "affix_max_hp", "value": 8}])) == []
    assert problems(_item(slot_type="ring", affixes=[{"affix": "affix_nope"}]))
    # 火焰抗性不能出現在武器上
    bad_slot = _item(
        slot_type="weapon",
        weapon="axe",
        affixes=[{"affix": "affix_resist_fire", "value": 100}],
    )
    assert any("不能出現在" in p for p in problems(bad_slot))
    out_of_range = _item(slot_type="ring", affixes=[{"affix": "affix_max_hp", "value": 99}])
    assert any("超出範圍" in p for p in problems(out_of_range))
    missing_value = _item(slot_type="ring", affixes=[{"affix": "affix_max_hp"}])
    assert any("需要 value" in p for p in problems(missing_value))
    # 限定武器、限盾、傳說、法杖已有元素
    hammer_only = _item(
        slot_type="weapon", weapon="axe", affixes=[{"affix": "affix_trait_hammer_knockback"}]
    )
    assert any("hammer" in p for p in problems(hammer_only))
    no_shield = _item(slot_type="offhand", affixes=[{"affix": "affix_act_shield_wall"}])
    assert any("shield" in p for p in problems(no_shield))
    body_ok = _item(slot_type="body", affixes=[{"affix": "affix_react_ranged_block"}])
    assert problems(body_ok) == []  # 「副（限盾）、身」：身體不限盾
    not_legendary = _item(slot_type="ring", affixes=[{"affix": "affix_rule_fire_mends"}])
    assert any("傳說" in p for p in problems(not_legendary))
    staff = _item(
        slot_type="weapon", weapon="fire_staff", affixes=[{"affix": "affix_attack_lightning"}]
    )
    assert any("已有元素" in p for p in problems(staff))
    too_many = _item(
        slot_type="ring",
        affixes=[
            {"affix": "affix_max_hp", "value": 4},
            {"affix": "affix_attr_str", "value": 1},
            {"affix": "affix_resist_fire", "value": 50},
            {"affix": "affix_cost_glass"},
            {"affix": "affix_cost_blood"},
        ],
    )
    assert any("最多 4 條" in p for p in problems(too_many))


def test_item_cannot_repeat_an_affix() -> None:
    with pytest.raises(ValidationError, match="重複"):
        _item(
            slot_type="ring",
            affixes=[{"affix": "affix_max_hp", "value": 4}, {"affix": "affix_max_hp", "value": 8}],
        )


def test_weapon_items_need_a_weapon() -> None:
    with pytest.raises(ValidationError, match="weapon"):
        _item(slot_type="weapon")
    with pytest.raises(ValidationError, match="weapon"):
        _item(slot_type="ring", weapon="axe")


# ---------------------------------------------------------------------------
# 欄位與占用
# ---------------------------------------------------------------------------


def test_slot_list_and_types() -> None:
    assert SLOTS == (
        "main_hand",
        "off_hand",
        "head",
        "body",
        "hands",
        "feet",
        "neck",
        "ring_1",
        "ring_2",
    )
    assert SLOT_TYPE_OF["ring_1"] == SLOT_TYPE_OF["ring_2"] == "ring"


def test_full_loadout_is_legal() -> None:
    lib = library()
    loadout = lib.loadout_of(lib.unit("gear_tester"))
    assert [e.slot for e in loadout.items] == list(SLOTS)
    assert loadout_problems(loadout, lib.weapons["one_handed_sword"], _rules()) == []


def test_slot_type_must_match() -> None:
    lib = library()
    loadout = _loadout(head="item_test_boots")
    problems = loadout_problems(loadout, lib.weapons["one_handed_sword"], _rules())
    assert any("頭只能放頭類物品" in p for p in problems)


def test_off_hand_cannot_hold_a_second_weapon() -> None:
    lib = library()
    loadout = _loadout(main_hand="item_test_sword", off_hand="item_test_sword")
    problems = loadout_problems(loadout, lib.weapons["one_handed_sword"], _rules())
    assert any("副手不能放第二把武器" in p for p in problems)


def test_two_handed_weapon_occupies_off_hand() -> None:
    lib = library()
    hammer = lib.weapons["hammer"]
    assert hammer.two_handed
    ok = _loadout(main_hand="item_test_hammer")
    assert loadout_problems(ok, hammer, _rules()) == []
    blocked = _loadout(main_hand="item_test_hammer", off_hand="item_test_shield")
    assert any("雙手武器" in p for p in loadout_problems(blocked, hammer, _rules()))
    # 沒有主手物品（舊資料的 weapon 就是主手）也一樣：雙手武器占用副手
    bare = _loadout(off_hand="item_test_shield")
    assert any("副手被占用" in p for p in loadout_problems(bare, hammer, _rules()))
    assert loadout_problems(bare, lib.weapons["one_handed_sword"], _rules()) == []


def test_paired_weapon_occupies_off_hand() -> None:
    lib = library()
    dagger = lib.weapons["dagger"]
    assert not dagger.two_handed
    blocked = _loadout(main_hand="item_test_twin_daggers", off_hand="item_test_shield")
    assert any("成對武器" in p for p in loadout_problems(blocked, dagger, _rules()))


def test_same_ring_cannot_be_worn_twice() -> None:
    lib = library()
    loadout = _loadout(ring_1="item_test_ring_str", ring_2="item_test_ring_str")
    problems = loadout_problems(loadout, lib.weapons["one_handed_sword"], _rules())
    assert any("同一枚戒指" in p for p in problems)


def test_main_hand_item_must_match_unit_weapon() -> None:
    lib = library()
    loadout = _loadout(main_hand="item_test_hammer")
    problems = loadout_problems(loadout, lib.weapons["one_handed_sword"], _rules())
    assert any("必須和單位的武器" in p for p in problems)


def test_more_than_two_cost_affixes_fail() -> None:
    lib = library()
    # 戰錘（玻璃）、項鍊（血契）、焰紋戒（玻璃）＝ 3 條代價型
    loadout = _loadout(
        main_hand="item_test_hammer", neck="item_test_amulet", ring_1="item_test_ring_fire"
    )
    problems = loadout_problems(loadout, lib.weapons["hammer"], _rules())
    assert any("代價型詞條全身最多 2 條（目前 3 條）" in p for p in problems)
    two = _loadout(main_hand="item_test_hammer", neck="item_test_amulet")
    assert loadout_problems(two, lib.weapons["hammer"], _rules()) == []


def test_unknown_slot_or_item_rejected() -> None:
    lib = library()
    with pytest.raises(ValueError, match="未知的物品"):
        resolve_loadout({"head": "item_nope"}, lib.items, lib.affixes)
    with pytest.raises(ValueError, match="未知的裝備欄位"):
        resolve_loadout({"tail": "item_test_helm"}, lib.items, lib.affixes)


def test_equipment_rules_from_yaml() -> None:
    rules = _rules()
    assert rules.diminishing_permille == (1000, 500, 250)
    assert [rules.weight(i) for i in range(5)] == [1000, 500, 250, 0, 0]
    caps = rules.caps
    assert (caps.damage_bonus_permille, caps.element_resist_permille) == (500, 500)
    assert (caps.ap_gain_per_round, caps.cooldown_min, caps.crit_range_min) == (1, 1, 18)
    assert (caps.move_bonus, caps.cost_affixes, caps.damage_reduction_permille) == (2, 2, 750)
    core = library().ruleset.core
    assert caps.damage_reduction_permille == 1000 - core.element_mod_floor_permille


def test_diminishing_weights_must_start_at_1000_and_not_grow() -> None:
    with pytest.raises(ValidationError):
        EquipmentRules(diminishing_permille=(500, 250))
    with pytest.raises(ValidationError):
        EquipmentRules(diminishing_permille=(1000, 250, 500))
