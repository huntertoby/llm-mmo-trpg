"""形狀的範圍成長（修正規則的 ``area_delta``、閃現的範圍變化共用；Phase 3-26a 起，3W-5b 從
已移除的技能等級模組搬來）。這個模組只讀資料。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.skills import ShapeSpec

if TYPE_CHECKING:
    from trpg.content.library import Ruleset

__all__ = ["grow_shape"]

_GROWABLE = ("size", "radius")
"""範圍 +1 能加的形狀參數（``cross``、``square3`` 只有 ``range``，大小固定）。"""


def grow_shape(rules: Ruleset, shape: ShapeSpec, delta: int) -> ShapeSpec:
    """``shape`` 的第一個可增加的大小參數（``size``、``radius``）加 ``delta``（不超過最大值）。"""
    params = rules.shape_def(shape.type).params
    for name in _GROWABLE:
        value = getattr(shape, name)
        if name in params and isinstance(value, int):
            return shape.model_copy(update={name: min(value + delta, params[name].max)})
    return shape
