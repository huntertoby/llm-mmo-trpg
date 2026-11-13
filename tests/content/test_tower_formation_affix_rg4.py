"""RG-4：塔盾詞條「護陣」的取得（#163，08 8.11「取得」）。

- 照一般詞條：只會出現在塔盾上（``offhands: [tower_shield]``），預算照詞條規則（武器特性強化類的固定
  點數），稀有起的產生器會抽到；
- 持盾弟子、熔殼甲兵掉的塔盾必帶護陣（``world/loot.yaml`` 的 ``signature_affixes``）。
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.equipment import (
    AffixRoll,
    ItemDef,
    WeaponTraitAffix,
    affix_slot_problems,
    item_problems,
)
from trpg.content.item_budget import affix_budget, affix_points, item_points
from trpg.content.item_gen import generate_item, with_affix
from trpg.shared.rng import Rng
from trpg.world.loot import _with_signature

FORMATION = "affix_trait_tower_formation"
SHIELD_TROOPS = ("sect_shield_disciple", "molten_shell_trooper")


def _gen(seed: int, rarity: str = "rare", level: int = 8) -> ItemDef:
    return generate_item(library(), Rng(seed), "off_hand", rarity, level)  # type: ignore[arg-type]


def test_the_affix_is_a_tower_shield_only_offhand_trait() -> None:
    lib = library()
    affix = lib.affixes[FORMATION]
    assert isinstance(affix, WeaponTraitAffix)
    assert affix.offhands == ("tower_shield",) and affix.slots == ("offhand",)
    assert "護陣" in affix.name_zh and "{" not in affix.name_zh
    tower = lib.items["item_offhand_tower_shield"]
    assert not affix_slot_problems(tower, affix, None, lib.weapons)
    for other in ("item_offhand_round_shield", "item_offhand_tome", "item_offhand_orb"):
        assert affix_slot_problems(lib.items[other], affix, None, lib.weapons)
    # 外觀是塔盾形制、但規則上不是塔盾（沒有 offhand）的物品也掛不上
    bulwark = lib.items["item_g3b_bulwark_shield"]
    assert affix_slot_problems(bulwark, affix, None, lib.weapons)


def test_existing_affixes_serialize_without_the_new_field() -> None:
    lib = library()
    assert "offhands" not in lib.affixes["affix_trait_bow_lob_cover"].model_dump()
    assert lib.affixes[FORMATION].model_dump()["offhands"] == ("tower_shield",)


def test_offhand_traits_need_offhand_slots_and_a_known_param() -> None:
    base = library().affixes[FORMATION].model_dump()
    with pytest.raises(ValidationError):
        WeaponTraitAffix.model_validate({**base, "param": "knockback"})
    with pytest.raises(ValidationError):
        WeaponTraitAffix.model_validate({**base, "slots": ["offhand", "body"]})
    with pytest.raises(ValidationError):
        WeaponTraitAffix.model_validate({**base, "weapons": ["bow"]})


def test_the_generator_only_puts_it_on_tower_shields() -> None:
    """稀有起第 1 條是技能強化（8 點），副手詞條預算要 16 點以上才放得下護陣（物品等級 12 起；第一季
    上限 10 時一般產生器抽不到，見回報的待 PM 決定）。這裡用 15 級驗「抽得到、而且只在塔盾上」。"""
    seen = 0
    for seed in range(300):
        item = _gen(seed, "epic" if seed % 2 else "rare", 15)
        if any(r.affix == FORMATION for r in item.affixes):
            assert item.offhand == "tower_shield"
            seen += 1
    assert seen > 0


def test_the_budget_counts_the_affix_like_any_weapon_trait() -> None:
    lib = library()
    rules = lib.item_gen
    assert rules is not None
    points = affix_points(rules, lib.affixes[FORMATION], None)
    assert points == rules.category_points["weapon_trait"]


def _tower(rarity: str, level: int) -> ItemDef:
    for seed in range(400):
        item = _gen(seed, rarity, level)
        if item.offhand == "tower_shield" and not any(r.affix == FORMATION for r in item.affixes):
            return item
    raise AssertionError("沒抽到塔盾")


@pytest.mark.parametrize("level", [8, 15])
@pytest.mark.parametrize("rarity", ["common", "uncommon", "rare", "epic"])
def test_with_affix_adds_the_formation_within_the_budget(rarity: str, level: int) -> None:
    lib = library()
    rules = lib.item_gen
    assert rules is not None
    item = _tower(rarity, level)
    out = with_affix(lib, item, FORMATION)
    assert out.affixes[-1] == AffixRoll(affix=FORMATION)
    assert len(out.affixes) <= rules.rarity(rarity).max_affixes
    assert item_points(rules, out, lib.affixes) <= affix_budget(rules, level, "offhand")
    assert not item_problems(out, lib.affixes, lib.weapons, lib.ruleset.equipment, lib.offhands)
    if len(out.affixes) > 1:
        assert out.affixes[0] == item.affixes[0]  # 從最後一條往前拿，build 詞條最後才拿
    if level == 15 and rarity in ("rare", "epic"):
        assert len(out.affixes) >= 2  # 預算夠時 build 詞條留著
    assert with_affix(lib, out, FORMATION) == out  # 已經有就不變


def test_with_affix_keeps_the_formation_when_the_budget_is_too_small() -> None:
    """低物品等級（雲嶺 3～4 級）的副手詞條預算放不下護陣：照樣帶（其他詞條拿光；待 PM 決定）。"""
    lib = library()
    rules = lib.item_gen
    assert rules is not None
    budget = affix_budget(rules, 3, "offhand")
    assert budget < affix_points(rules, lib.affixes[FORMATION], None)
    out = with_affix(lib, _tower("rare", 3), FORMATION)
    assert [r.affix for r in out.affixes] == [FORMATION]
    assert out.base_bonus_permille == 0


def test_with_affix_leaves_other_offhands_alone() -> None:
    lib = library()
    for seed in range(40):
        item = _gen(seed)
        if item.offhand != "tower_shield":
            assert with_affix(lib, item, FORMATION) == item


def test_shield_troops_drop_tower_shields_with_the_formation() -> None:
    lib = library()
    rules = lib.world_loot
    assert rules is not None
    for unit in SHIELD_TROOPS:
        assert rules.signature_affix((unit,), "tower_shield") == FORMATION
        assert rules.signature_affix(("bandit", unit), "tower_shield") == FORMATION
        assert rules.signature_affix((unit,), "round_shield") is None
        assert rules.signature_affix((unit,), None) is None
    assert rules.signature_affix(("bandit_shieldbearer",), "tower_shield") is None
    tower = _tower("rare", 8)
    (dropped,) = _with_signature(lib, rules, [tower], ("sect_shield_disciple",))
    assert any(r.affix == FORMATION for r in dropped.affixes)
    (plain,) = _with_signature(lib, rules, [tower], ("bandit",))
    assert plain == tower


def test_the_signature_rows_name_real_enemies_and_points() -> None:
    lib = library()
    rules = lib.world_loot
    assert rules is not None
    budget_floor = Fraction(0)
    for row in rules.signature_affixes:
        for unit in row.units:
            assert "shield_guard" in lib.unit(unit).tags
        assert row.offhand in lib.offhands
        assert affix_points(lib.item_gen, lib.affixes[row.affix], None) > budget_floor  # type: ignore[arg-type]
