"""BAL-4c 設定點：每場打贏後回復最大生命的千分比（預設 0 ＝ 行為不變）。"""

from __future__ import annotations

import dataclasses

from tests.engine.helpers import library
from trpg.roguelite.progress import _heal_after_battle


def test_default_is_zero_and_keeps_hp() -> None:
    lib = library()
    assert lib.roguelite.heal_after_battle_permille == 0
    assert _heal_after_battle(lib, 7, 40) == 7


def test_heal_adds_a_share_of_max_hp_and_caps_at_max() -> None:
    lib = library()
    healed = dataclasses.replace(
        lib, roguelite=lib.roguelite.model_copy(update={"heal_after_battle_permille": 200})
    )
    assert _heal_after_battle(healed, 7, 40) == 15  # +8
    assert _heal_after_battle(healed, 37, 40) == 40
    assert _heal_after_battle(healed, 10, 33) == 16  # 6.6 → 6（無條件捨去）
