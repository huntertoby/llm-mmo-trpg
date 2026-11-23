"""E6-a2：``CraftRecipe.signature`` 空值不輸出，舊配方碼逐位元不變。

下面的指紋與配方碼是在基準 ``34bb21fa9``（加欄位之前）算出來的，寫死在這裡；新版要算出一樣的值。"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.world.crafting import fingerprint, recipe_code, variant_print
from trpg.world.state import CraftRecipe, RecipeStep

_STEPS = (RecipeStep(index=1), RecipeStep(index=0, affix="affix_attr_dex"))

OLD: list[tuple[dict[str, Any], str, str]] = [
    (
        {
            "slot_type": "neck",
            "rarity": "rare",
            "item_level": 3,
            "affix": "affix_kw_burn_duration",
            "grade": "item_coarse_material",
        },
        "538988a29eeace9845f53eea354a2fcdaab37d1b085feb5b0257970a20acf0ec",
        "87fd1bb79a",
    ),
    (
        {
            "slot_type": "neck",
            "rarity": "rare",
            "item_level": 3,
            "affix": "affix_kw_burn_duration",
            "grade": "item_coarse_material",
            "materials": ("item_mist_crystal",),
        },
        "6fc54c772949725f8979f7995ee5ee6aab9ed27683fc75fdfdaf781ecb93777e",
        "a1db859f0a",
    ),
    (
        {
            "slot_type": "weapon",
            "weapon_class": "melee",
            "rarity": "epic",
            "item_level": 7,
            "affix": "affix_kw_ignite_damage",
            "grade": "item_fine_material",
            "materials": ("item_mist_crystal", "item_talisman_ash"),
        },
        "10971a1aec18a1f5abb248ce66bee153ed9146dc7a9e85ce43f0590f387a93f4",
        "a3cd7fc791",
    ),
    (
        {  # 隱藏配方：affix 是 None
            "slot_type": "body",
            "rarity": "rare",
            "item_level": 6,
            "affix": None,
            "grade": "item_fine_material",
            "materials": ("item_mist_crystal", "item_talisman_ash", "item_thunder_feather"),
        },
        "6f30a997ee77596857b5e17c1a3c19d53075c164403c56256d74f044b9809d8b",
        "95b8239366",
    ),
    (
        {
            "slot_type": "ring",
            "rarity": "epic",
            "item_level": 10,
            "affix": "affix_trig_kill_ap",
            "grade": "item_superior_material",
        },
        "cad66619efb2de63848cab1ceff092a3ec64ee6e39aba663d2472c076c688556",
        "2a5b692246",
    ),
    (
        {
            "slot_type": "offhand",
            "rarity": "rare",
            "item_level": 1,
            "affix": "affix_kw_conceal_damage",
            "grade": "item_coarse_material",
        },
        "b9f459cd9f96403c8beffe3f9153fc29fc8119bdbed0f4b2d5664272300aac28",
        "547341998b",
    ),
]


@pytest.mark.parametrize(("data", "print_", "variant"), OLD)
def test_old_recipe_codes_unchanged(data: dict[str, Any], print_: str, variant: str) -> None:
    recipe = CraftRecipe(**data)
    assert "signature" not in recipe.model_dump(mode="json")
    assert fingerprint(recipe) == print_
    assert recipe_code(fingerprint(recipe)) == print_[:10]
    assert recipe_code(variant_print(print_, _STEPS)) == variant


def test_signature_recipe_round_trips_and_differs() -> None:
    data = dict(OLD[0][0], affix=None)
    recipe = CraftRecipe(**data, signature="action")
    dumped = recipe.model_dump(mode="json")
    assert dumped["signature"] == "action"
    assert CraftRecipe.model_validate(dumped) == recipe
    assert fingerprint(recipe) != fingerprint(CraftRecipe(**data))
