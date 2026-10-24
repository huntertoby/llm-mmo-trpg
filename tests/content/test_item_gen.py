"""Phase 3K-1：物品產生器與物品預算（08 8.22、8.22.1、8.21.2.4 #52；07 7.1）。

行為一致測試（規格第 4 節）：大量種子抽樣——部位與稀有度分布符合權重、主手全部同大類、每件都通過
物品預算與穿戴驗證、同物品等級各稀有度預算相同（表格）。另外驗證確定性、屬性偏好、武器元素詞條、
傳說、普通物品的基礎加成，以及驗證器本身會擋下不合規的物品。
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction

import pytest

from tests.engine.helpers import library
from trpg.content.equipment import (
    AffixRoll,
    AttackAffix,
    ItemDef,
    StatAffix,
    item_problems,
    loadout_problems,
    resolve_loadout,
)
from trpg.content.item_budget import (
    RARITIES,
    ItemGenRules,
    affix_budget,
    affix_points,
    item_budget,
    item_budget_problems,
    slot_budget,
    total_budget,
)
from trpg.content.item_gen import ItemGenError, generate_item, roll_rarity
from trpg.content.slots import SLOT_TYPES, SlotType
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element

GENERATED = ("common", "uncommon", "rare", "epic")
LEVELS = range(1, 7)  # roguelite 一輪的物品等級＝主角等級 1～6（8.22.1 第 1 點）
WEAPON_CLASSES = ("melee", "ranged", "focus")


def rules() -> ItemGenRules:
    found = library().item_gen
    assert found is not None
    return found


def _gen(seed: int, slot: str, rarity: str, level: int, **kw: object) -> ItemDef:
    return generate_item(library(), Rng(seed), slot, rarity, level, **kw)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 預算表（8.22、8.22.1 第 1～3 點）
# ---------------------------------------------------------------------------


def test_total_budget_interpolates_and_floors() -> None:
    r = rules()
    assert [total_budget(r, lv) for lv in range(1, 11)] == [
        100, 125, 150, 175, 200, 230, 260, 290, 320, 350,
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("level", "slot_type", "slot", "affix"),
    [
        (1, "weapon", 30, 12),
        (1, "body", 20, 8),
        (1, "offhand", 10, 4),
        (1, "head", 8, 4),
        (1, "neck", 8, 8),
        (1, "ring", 4, 4),
        (5, "weapon", 60, 24),
        (5, "hands", 16, 8),
        (6, "weapon", 69, 27),
        (6, "body", 46, 18),
        (6, "feet", 18, 9),
        (6, "ring", 9, 9),
        (10, "weapon", 105, 42),
    ],
)
def test_slot_and_affix_budget_table(
    level: int, slot_type: SlotType, slot: int, affix: int
) -> None:
    assert slot_budget(rules(), level, slot_type) == slot
    assert affix_budget(rules(), level, slot_type) == affix


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("slot_type", SLOT_TYPES)
def test_every_rarity_gets_the_same_budget(level: int, slot_type: SlotType) -> None:
    """稀有度不加強度（08 8.5）：同物品等級、同部位，四種稀有度的預算相同。"""
    budgets = set()
    for rarity in GENERATED:
        item = _gen(level * 31 + 7, slot_type, rarity, level)
        found = item_budget(rules(), item, library().affixes)
        assert found is not None
        budgets.add(found.budget)
    assert budgets == {affix_budget(rules(), level, slot_type)}


# ---------------------------------------------------------------------------
# 詞條點數（8.22.1 第 4 點）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("affix_id", "value", "points"),
    [
        ("affix_attr_str", 1, Fraction(3)),
        ("affix_attr_wil", 4, Fraction(12)),
        ("affix_max_hp", 4, Fraction(3)),
        ("affix_max_hp", 16, Fraction(12)),
        ("affix_resist_fire", 50, Fraction(3)),
        ("affix_resist_fire", 150, Fraction(9)),
        ("affix_cond_still_defense", 200, Fraction(30) * Fraction(6, 10)),
        ("affix_cond_height_hit", 1, Fraction(8) * Fraction(35, 100)),
        ("affix_kw_prone_damage", 150, Fraction(8)),
        ("affix_attack_lightning", None, Fraction(10)),
        ("affix_attack_shadow", None, Fraction(10)),
        ("affix_weapon_fire", None, Fraction(15)),
        ("affix_trait_axe_sunder", None, Fraction(8)),
        ("affix_trig_kill_ap", None, Fraction(12) * Fraction(7, 10)),
        ("affix_charge_static", None, Fraction(12)),
        ("affix_act_grapple", None, Fraction(20)),
        ("affix_react_guard_ally", None, Fraction(15)),
        ("affix_rule_fire_mends", None, Fraction(40)),
        ("affix_cost_glass", None, Fraction(30 - 15)),
        ("affix_cost_swift", None, Fraction(4)),  # 24 − 22.5 → 至少 4
    ],
)
def test_affix_points(affix_id: str, value: int | None, points: Fraction) -> None:
    assert affix_points(rules(), library().affixes[affix_id], value) == points


# ---------------------------------------------------------------------------
# 大量種子抽樣
# ---------------------------------------------------------------------------


def _wear_problems(item: ItemDef) -> list[str]:
    """把物品放進對應欄位穿上（主手外用單手劍當主手武器），回傳穿戴驗證的問題。"""
    lib = library()
    slot = {"weapon": "main_hand", "offhand": "off_hand", "ring": "ring_1"}.get(
        item.slot_type, item.slot_type
    )
    loadout = resolve_loadout({slot: item.id}, {item.id: item}, lib.affixes)
    weapon = lib.weapons[item.weapon or "one_handed_sword"]
    return loadout_problems(loadout, weapon, lib.ruleset.equipment)


def _sample() -> list[tuple[ItemDef, str | None]]:
    """6 個等級 × 8 種部位 × 四種稀有度 × 6 個種子；主手輪流限定三個大類。"""
    out: list[tuple[ItemDef, str | None]] = []
    for level in LEVELS:
        for s_index, slot_type in enumerate(SLOT_TYPES):
            for r_index, rarity in enumerate(GENERATED):
                for seed in range(6):
                    cls = None
                    if slot_type == "weapon":
                        cls = WEAPON_CLASSES[(seed + r_index) % 3]
                    key = ((level * 17 + s_index) * 13 + r_index) * 101 + seed
                    item = _gen(key, slot_type, rarity, level, weapon_class=cls)
                    out.append((item, cls))
    return out


SAMPLE: list[tuple[ItemDef, str | None]] = []


def sample() -> list[tuple[ItemDef, str | None]]:
    if not SAMPLE:
        SAMPLE.extend(_sample())
    return SAMPLE


def test_every_sampled_item_passes_budget_item_and_wear_checks() -> None:
    lib = library()
    for item, _ in sample():
        assert item_budget_problems(rules(), item, lib.affixes) == [], item
        problems = item_problems(
            item, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands
        )
        assert problems == [], item
        assert _wear_problems(item) == [], item


def test_main_hand_weapons_all_match_the_requested_class() -> None:
    lib = library()
    weapons = [(i, c) for i, c in sample() if i.slot_type == "weapon"]
    assert weapons
    for item, cls in weapons:
        assert item.weapon is not None
        weapon = lib.weapons[item.weapon]
        assert weapon.weapon_class == cls
        assert not weapon.summon_only
        assert item.paired == weapon.paired


def test_new_weapons_and_offhands_are_used_as_bases() -> None:
    """3I-1、3I-3、3I-4 的新武器與 3I-2 的副手都能當底材。"""
    lib = library()
    weapons = {
        _gen(seed, "weapon", "rare", 3).weapon for seed in range(400)
    }  # fmt: skip
    expected = {w.id for w in lib.weapons.values() if not w.summon_only}
    assert weapons == expected
    for new in ("fist", "scythe", "whip", "arcane_blade", "dual_dagger", "shotgun", "pistol"):
        assert new in weapons
    offhands = {_gen(seed, "off_hand", "uncommon", 3).offhand for seed in range(80)}
    assert offhands == set(lib.offhands)
    shields = [_gen(seed, "offhand", "common", 2) for seed in range(40)]
    assert all(
        ("shield" in i.tags) == (i.offhand in ("round_shield", "tower_shield")) for i in shields
    )


def test_affix_count_and_categories_follow_rarity() -> None:
    lib = library()
    for item, _ in sample():
        rule = rules().rarities[item.rarity or ""]
        assert len(item.affixes) <= rule.max_affixes
        cats = [lib.affixes[r.affix].category for r in item.affixes]
        assert "action" not in cats and "reaction" not in cats and "rule" not in cats
        if item.rarity == "common":
            assert len(item.affixes) <= 1
            if not item.affixes:
                assert item.base_bonus_permille > 0
        else:
            assert item.affixes
            assert item.base_bonus_permille == 0


def test_rare_and_epic_weapons_carry_one_keyword_affix_when_it_fits() -> None:
    lib = library()
    keyword_counts: Counter[int] = Counter()
    for item, _ in sample():
        if item.rarity in ("rare", "epic") and item.slot_type == "weapon":
            kws = [r for r in item.affixes if lib.affixes[r.affix].category == "keyword"]
            keyword_counts[len(kws)] += 1
    assert set(keyword_counts) == {1}  # 主手預算夠放 8 點的技能強化，每件恰好 1 條


def test_rarity_weights_match_content() -> None:
    """稀有度依 40／25／20／13／2 抽（07 7.1；使用者 2026-10-24），10000 次抽樣誤差在 ±1.5% 內。"""
    rng = Rng(2026)
    n = 10_000
    counts = Counter(roll_rarity(library(), rng) for _ in range(n))
    weights = rules().rarity_weights
    total = sum(weights.values())
    assert set(counts) <= set(RARITIES)
    assert weights == {"common": 40, "uncommon": 25, "rare": 20, "epic": 13, "legendary": 2}
    for rarity, weight in weights.items():
        assert abs(counts[rarity] / n - weight / total) < 0.015, (rarity, counts)


def test_slot_distribution_with_rolled_rarity() -> None:
    """依部位均勻抽、稀有度依權重抽時，每種部位都出現、件件通過預算（3K-2 的三選一照這個用法）。"""
    lib = library()
    rng = Rng(77)
    slots: Counter[str] = Counter()
    for index in range(400):
        slot = SLOT_TYPES[rng.randint(0, len(SLOT_TYPES) - 1)]
        rarity = roll_rarity(lib, rng)
        item = generate_item(lib, rng.fork(f"gear/{index}"), slot, rarity, 1 + index % 6)
        slots[item.slot_type] += 1
        assert item.slot_type == slot
        assert item_budget_problems(rules(), item, lib.affixes) == []
    assert set(slots) == set(SLOT_TYPES)
    assert min(slots.values()) > 400 / len(SLOT_TYPES) * 0.6


# ---------------------------------------------------------------------------
# 確定性
# ---------------------------------------------------------------------------


def test_same_seed_same_item_and_different_seeds_differ() -> None:
    for slot in ("weapon", "body", "ring"):
        first = _gen(123, slot, "epic", 4)
        assert _gen(123, slot, "epic", 4) == first
    items = {_gen(seed, "weapon", "rare", 4).model_dump_json() for seed in range(20)}
    assert len(items) > 10


def test_generator_only_uses_the_given_rng() -> None:
    rng_a, rng_b = Rng(9), Rng(9)
    a = [generate_item(library(), rng_a, "neck", "rare", 3) for _ in range(5)]
    b = [generate_item(library(), rng_b, "neck", "rare", 3) for _ in range(5)]
    assert a == b
    assert rng_a.get_state() == rng_b.get_state()


# ---------------------------------------------------------------------------
# 武器上的屬性偏好（3K-1 規格）與武器元素詞條（#52）
# ---------------------------------------------------------------------------


def _attribute_share(weapon_class: str, weapon_ids: set[str]) -> Counter[str]:
    lib = library()
    counts: Counter[str] = Counter()
    for seed in range(3000):
        item = _gen(seed, "weapon", "uncommon", 3, weapon_class=weapon_class)
        if item.weapon not in weapon_ids:
            continue
        for roll in item.affixes:
            affix = lib.affixes[roll.affix]
            if isinstance(affix, StatAffix) and affix.attribute is not None:
                counts[affix.attribute.value] += 1
    return counts


def test_single_attribute_weapons_prefer_their_scaling_attribute() -> None:
    lib = library()
    single = {
        w.id
        for w in lib.weapons.values()
        if not w.summon_only and w.weapon_class == "ranged" and w.secondary_scaling_attr is None
    }
    counts = _attribute_share("ranged", single)  # 遠程全是敏捷
    total = sum(counts.values())
    assert total > 300
    assert abs(counts["dex"] / total - 0.5) < 0.07
    for attr in Attribute:
        if attr is not Attribute.DEX:
            assert abs(counts[attr.value] / total - 0.1) < 0.05


def test_dual_attribute_weapons_split_the_preference() -> None:
    counts = _attribute_share("melee", {"hammer"})  # 體質／力量
    total = sum(counts.values())
    assert total > 60
    assert abs(counts["con"] / total - 0.25) < 0.12
    assert abs(counts["str"] / total - 0.25) < 0.12
    others = sum(counts[a] for a in ("dex", "int", "wis", "wil"))
    assert abs(others / total - 0.5) < 0.15


def test_weapon_element_affixes_appear_but_never_on_elemental_weapons() -> None:
    lib = library()
    seen: set[Element] = set()
    for seed in range(1500):
        item = _gen(seed, "weapon", "epic", 6)
        weapon = lib.weapons[item.weapon or ""]
        elements = [
            a.weapon_element
            for r in item.affixes
            if isinstance(a := lib.affixes[r.affix], AttackAffix) and a.weapon_element is not None
        ]
        assert len(elements) <= 1
        if weapon.element is not Element.PHYSICAL:  # 法杖、權杖
            assert not elements
            defs = [lib.affixes[r.affix] for r in item.affixes]
            assert not any(isinstance(a, AttackAffix) and a.add_element is not None for a in defs)
        seen.update(e for e in elements if e is not None)
    assert len(seen) >= 6


def test_staffs_never_get_a_weapon_element_from_validation() -> None:
    lib = library()
    staff = ItemDef(
        id="item_t_staff",
        name_zh="測試法杖",
        slot_type="weapon",
        weapon="fire_staff",
        affixes=(AffixRoll(affix="affix_weapon_ice"),),
    )
    problems = item_problems(staff, lib.affixes, lib.weapons, lib.ruleset.equipment)
    assert any("不能掛武器元素詞條" in p for p in problems)


# ---------------------------------------------------------------------------
# 傳說與普通
# ---------------------------------------------------------------------------


def test_legendary_picks_an_existing_legendary_item_or_falls_back_to_epic() -> None:
    lib = library()
    neck = _gen(1, "neck", "legendary", 3)
    assert neck.legendary and neck.id in lib.items
    ring = _gen(1, "ring", "legendary", 3)  # 沒有傳說戒指 → 史詩
    assert ring.rarity == "epic" and not ring.legendary
    assert item_budget_problems(rules(), ring, lib.affixes) == []


def test_common_items_without_affixes_convert_the_budget_to_base_bonus() -> None:
    commons = [_gen(seed, "body", "common", 6) for seed in range(60)]
    bare = [i for i in commons if not i.affixes]
    assert bare
    for item in bare:
        assert item.base_bonus_permille == 18 // 3 * 20  # 詞條預算 18 → 6 × 2% ＝ 12%


# ---------------------------------------------------------------------------
# 驗證器會擋下不合規的物品
# ---------------------------------------------------------------------------


def _item(rolls: list[tuple[str, int | None]], **kw: object) -> ItemDef:
    data: dict[str, object] = {
        "id": "item_t_budget",
        "name_zh": "測試",
        "slot_type": "weapon",
        "weapon": "one_handed_sword",
        "rarity": "rare",
        "item_level": 1,
        "affixes": [{"affix": a, "value": v} for a, v in rolls],
    }
    data.update(kw)
    return ItemDef.model_validate(data)


def test_budget_validator_rejects_bad_items() -> None:
    lib, r = library(), rules()
    ok = _item([("affix_kw_prone_damage", 150), ("affix_attr_str", 1)])  # 8 + 3 ＝ 11／12
    assert item_budget_problems(r, ok, lib.affixes) == []
    over = _item([("affix_kw_prone_damage", 150), ("affix_attr_str", 2)])  # 14 > 12
    assert any("不在預算" in p for p in item_budget_problems(r, over, lib.affixes))
    under = _item([("affix_attr_str", 2)])  # 6 < 8.4
    assert any("不在預算" in p for p in item_budget_problems(r, under, lib.affixes))
    keywords = _item(
        [("affix_kw_prone_damage", 60), ("affix_kw_burn_duration", None)], item_level=6
    )
    assert any("build 詞條" in p for p in item_budget_problems(r, keywords, lib.affixes))
    common_kw = _item([("affix_kw_prone_damage", 150)], rarity="common")
    assert any("不能有 keyword" in p for p in item_budget_problems(r, common_kw, lib.affixes))
    base_on_rare = _item([("affix_attr_str", 3)], base_bonus_permille=20, item_level=1)
    assert any("基礎加成" in p for p in item_budget_problems(r, base_on_rare, lib.affixes))
    triggers = _item(
        [("affix_trig_every3_prone", None), ("affix_trig_kill_ap", None)],
        item_level=4,
        rarity="epic",
    )
    assert any("觸發詞條每件最多 1 條" in p for p in item_budget_problems(r, triggers, lib.affixes))
    no_level = _item([("affix_attr_str", 3)], item_level=None)
    assert any("沒有物品等級" in p for p in item_budget_problems(r, no_level, lib.affixes))


def test_generator_rejects_bad_arguments() -> None:
    with pytest.raises(ItemGenError):
        _gen(1, "weapon", "rare", 0)
    with pytest.raises(ItemGenError):
        _gen(1, "tail", "rare", 1)
