"""掉落規則（Phase 5D-2；``docs/phases/Phase5計畫.md`` 27.2）：雲嶺材料與 ``loot.yaml`` 的檢查。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_loot import LootRules, load_world_loot, loot_problems

MATERIALS = (
    "item_mist_crystal",
    "item_talisman_ash",
    "item_cinnabar",
    "item_green_bamboo",
    "item_wolf_fang",
    "item_thunder_feather",
    "item_living_bone",
    "item_summit_mist_crystal",
    "item_coarse_material",
    "item_fine_material",
    "item_superior_material",
)


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _base() -> dict[str, Any]:
    return {
        "material_permille": 400,
        "generic_by_level": [{"max_level": 3, "item": "item_coarse_material"}],
        "gear": {
            "battle_permille": 150,
            "battle_weights": {"common": 1},
            "elite_epic_permille": 500,
            "max_item_level": 10,
        },
    }


def test_cloud_ridge_loads(library: ContentLibrary) -> None:
    rules = library.world_loot
    assert rules is not None
    items = library.world_economy.items
    for item in MATERIALS:
        assert items[item].kind == "material"
    assert items["item_living_bone"].rare and items["item_summit_mist_crystal"].rare
    assert items["item_fine_material"].grade == "fine"
    loot = rules.region("cloud_ridge")
    assert loot.families["mist_wolf"] == "item_wolf_fang"
    assert loot.elite_affixes["regenerating"] == "item_living_bone"
    assert rules.generic_material(1) == "item_coarse_material"
    assert rules.generic_material(5) == "item_fine_material"
    assert rules.generic_material(12) == "item_superior_material"
    assert rules.sell_price("rare", 4) == 32 and rules.sell_price("legendary", 4) is None
    assert rules.sell_price("rare", None) is None


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (
            {
                "generic_by_level": [
                    {"max_level": 5, "item": "item_a"},
                    {"max_level": 3, "item": "item_b"},
                ]
            },
            "遞增",
        ),
        ({"mercenary_gear": {"slots": ["main_hand"]}}, "主手"),
        ({"gear": {**_base()["gear"], "battle_weights": {"legendary": 1}}}, "傳說"),
        ({"gear": {**_base()["gear"], "battle_weights": {"common": 0}}}, "合計"),
    ],
)
def test_bad_rules(patch: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        LootRules.model_validate({**_base(), **patch})


def test_cross_file_problems(library: ContentLibrary) -> None:
    rules = LootRules.model_validate(
        {
            **_base(),
            "regions": {
                "nowhere": {},
                "cloud_ridge": {
                    "keywords": ["wet", "hidden"],
                    "families": {"ghost": "item_wolf_fang", "mist_wolf": "item_hp_potion_small"},
                    "elite_affixes": {"shiny": "item_nothing"},
                },
            },
        }
    )
    problems = loot_problems(
        rules,
        regions={"cloud_ridge"},
        units=set(library.units),
        affixes={"regenerating"},
        items=library.world_economy.items,
        keywords={"wet", "charged", "concealed"},
    )
    text = "；".join(problems)
    assert "未知的關鍵字 ['hidden']" in text  # 5D-2b：雲嶺的「隱蔽」是 concealed
    assert "nowhere：沒有地點圖" in text
    assert "未知的敵人 ghost" in text
    assert "item_hp_potion_small 不是材料" in text
    assert "未知的精英詞綴 shiny" in text
    assert "item_nothing 不在 world/items.yaml" in text


def test_missing_file_is_none(tmp_path: Path) -> None:
    assert load_world_loot(tmp_path, [], regions=(), units=(), affixes=(), items={}) is None


def test_bandits_drop_scorched_iron_in_every_region(library: ContentLibrary) -> None:
    """5D-2b（19.2.4、20.2）：盜賊在各區都掉焦鐵（護甲、格擋傾向）；區域的家族材料優先。"""
    rules = library.world_loot
    assert rules is not None
    iron = library.world_economy.items["item_scorched_iron"]
    assert iron.kind == "material" and iron.name_zh == "焦鐵" and not iron.rare
    bandits = sorted(u for u in library.units if u.startswith("bandit"))
    assert bandits and set(bandits) <= set(rules.families)
    for region in ("cloud_ridge", "ash_wastes"):
        for unit in bandits:
            assert rules.family_material(region, unit) == "item_scorched_iron"
    assert rules.family_material("cloud_ridge", "mist_wolf") == "item_wolf_fang"
    assert rules.family_material("ash_wastes", "mist_wolf") is None
    crafting = library.world_crafting
    assert crafting is not None
    assert "affix_react_ranged_block" in crafting.materials["item_scorched_iron"].leanings
