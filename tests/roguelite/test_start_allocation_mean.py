"""開局自動配點：取平均的雙屬性武器 2＋2（玩法 PM 2026-10-24，3I-1 待決 #6）。"""

from __future__ import annotations

import pytest

from trpg.content.library import load_library
from trpg.roguelite.start import default_allocation
from trpg.shared.types import Attribute


@pytest.mark.parametrize(
    ("weapon", "main", "expected"),
    [
        ("scythe", Attribute.WIL, {Attribute.WIL: 2, Attribute.STR: 2}),  # 取平均
        ("whip", Attribute.DEX, {Attribute.DEX: 2, Attribute.WIS: 2}),  # 取平均
        ("fist", Attribute.CON, {Attribute.CON: 4}),  # 取較高：全點主屬性
        ("hammer", Attribute.CON, {Attribute.CON: 4}),  # 取較高
        ("one_handed_sword", Attribute.STR, {Attribute.STR: 4}),  # 單一屬性
        ("scythe", Attribute.INT, {Attribute.INT: 4}),  # 技能主導、不是武器主屬性：照舊
    ],
)
def test_default_allocation_splits_only_for_mean_weapons(
    weapon: str, main: Attribute, expected: dict[Attribute, int]
) -> None:
    lib = load_library()
    assert default_allocation(main, lib.weapons[weapon], 4) == expected


def test_odd_points_give_the_extra_point_to_the_main_attribute() -> None:
    lib = load_library()
    assert default_allocation(Attribute.WIL, lib.weapons["scythe"], 5) == {
        Attribute.WIL: 3,
        Attribute.STR: 2,
    }
