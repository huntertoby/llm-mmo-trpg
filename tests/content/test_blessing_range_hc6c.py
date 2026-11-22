"""HC-6c（X10-3d 裁定 6）：武器特性「祝禱」的骰子寫成範圍，照現有骰子範圍的顯示規則（X10-3b／3d）：
骰面 × ``quantity_scale``、固定值疊進範圍、連接號「–」，長說明下一行「擲 NdM，每點 ×10」。"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.content.battle import WeaponDef
from trpg.content.library import load_library
from trpg.shared.range_text import dice_note, range_text, span


def _scepter(**blessing: Any) -> WeaponDef:
    data = load_library().weapons["scepter"].model_dump(mode="json")
    return WeaponDef.model_validate({**data, "blessing": blessing})


def test_flat_only_unchanged() -> None:
    """現有的權杖只有固定值：字和改前逐字相同。"""
    core = load_library().ruleset.core
    scepter = load_library().weapons["scepter"]
    assert scepter.trait_lines_zh(core) == ("祝禱：普攻命中時，最近的隊友回復 30 HP",)
    assert scepter.trait_lines_zh() == ("祝禱：普攻命中時，最近的隊友回復 30 HP",)


def test_dice_written_as_range() -> None:
    core = load_library().ruleset.core
    scale = core.quantity_scale
    lines = _scepter(dice="1d6").trait_lines_zh(core)
    low, high = span(1, 6, scale)
    assert lines == (
        f"祝禱：普攻命中時，最近的隊友回復 {range_text(low, high)} HP",
        dice_note(1, 6, scale),
    )
    assert "1d6 HP" not in "".join(lines)
    if scale == 10:  # 現在的量尺：照 X10-3d 的例子
        assert lines == ("祝禱：普攻命中時，最近的隊友回復 10–60 HP", "擲 1d6，每點 ×10")


def test_flat_stacks_into_range_and_preview_has_no_dice_line() -> None:
    core = load_library().ruleset.core
    scale = core.quantity_scale
    low, high = span(2, 4, scale, 5)
    weapon = _scepter(dice="2d4", flat=5)
    assert weapon.trait_lines_zh(core)[0] == f"祝禱：普攻命中時，最近的隊友回復 {low}–{high} HP"
    assert weapon.trait_lines_zh(core, on_hit_only=True) == (
        f"祝禱：普攻命中時，最近的隊友回復 {low}–{high} HP",
    )


def test_dice_without_core_is_an_error() -> None:
    with pytest.raises(ValueError, match="core"):
        _scepter(dice="1d6").trait_lines_zh()
