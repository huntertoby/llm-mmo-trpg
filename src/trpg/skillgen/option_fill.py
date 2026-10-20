"""以選項的最小值填出一個值（Phase 3F-1）：:func:`trpg.skillgen.options.draft_options` 用來「試組」
候選的效果原語，看 schema 能不能接受（不能接受的原語不列出）。

``choice`` 取第一個可選值（:func:`variants` 另外列出第一個 ``choice`` 參數的每個值）、``int`` 取
``min``（沒有時 1）、骰子取最少顆數與第一種面數、``bool`` 取 ``true``、文字取 ``x``。巢狀的效果列表
（``effects``、``modifiers``）無法自動填，回傳 ``None``。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from trpg.skillgen.option_models import Choice, FieldSpec

__all__ = ["fill_choice", "fill_fields", "variants"]

_OBJECT_CHOICES = frozenset({"shape", "condition"})
"""值本身是物件（``{"type": …, 參數…}``）的 ``choice`` 欄位；其他 ``choice`` 的參數填在同一層。"""


def _scalar(field: FieldSpec) -> object:
    if field.type in ("int", "count"):
        return field.min if field.min is not None else 1
    if field.type == "dice":
        sides = field.dice_sides[0] if field.dice_sides else 6
        return f"{field.min or 1}d{sides}"
    if field.type == "bool":
        return True
    if field.type == "tags":
        return ["x"]
    return "x"


def _choice_value(field: FieldSpec, choice: Choice) -> dict[str, Any] | None:
    """``choice`` 欄位選 ``choice`` 時要寫進同一層的內容；無法自動填時為 ``None``。"""
    if field.type == "multi_choice":
        return {field.field: [choice.value]}
    if field.field in _OBJECT_CHOICES:
        sub = fill_choice(choice)
        return None if sub is None else {field.field: sub}
    params = fill_fields(choice.params)
    return None if params is None else {field.field: choice.value, **params}


def _fill_one(field: FieldSpec, out: dict[str, Any], pick: Choice | None = None) -> bool:
    value: dict[str, Any] | None
    if field.type in ("effects", "modifiers"):
        value = None
    elif field.type == "object":
        sub = fill_fields(field.fields)
        value = None if sub is None else {field.field: sub}
    elif field.type in ("choice", "multi_choice"):
        choice = pick or (field.choices[0] if field.choices else None)
        value = None if choice is None else _choice_value(field, choice)
    else:
        value = {field.field: _scalar(field)}
    if value is None:
        return False
    out.update(value)
    return True


def fill_fields(
    fields: Sequence[FieldSpec], picks: dict[str, Choice] | None = None
) -> dict[str, Any] | None:
    """必填欄位的最小值（``picks`` 指定個別 ``choice`` 欄位的值）；有無法自動填的必填欄位時回傳
    ``None``。"""
    out: dict[str, Any] = {}
    for field in fields:
        if field.required and not _fill_one(field, out, (picks or {}).get(field.field)):
            return None
    return out


def fill_choice(choice: Choice, picks: dict[str, Choice] | None = None) -> dict[str, Any] | None:
    """``{"type": 值, 必填參數…}``（形狀、條件、效果原語）；無法自動填時回傳 ``None``。"""
    params = fill_fields(choice.params, picks)
    return None if params is None else {"type": choice.value, **params}


def variants(choice: Choice) -> list[dict[str, Any]]:
    """``choice`` 的幾種最小填法：第一個必填的 ``choice`` 參數取每一個值（例：瞬步的落點
    ``choose``／``behind``）；無法自動填時為空串列。"""
    first = next((p for p in choice.params if p.required and p.type == "choice"), None)
    picks: list[dict[str, Choice]] = [{}]
    if first is not None:
        picks = [{first.field: c} for c in first.choices]
    out = [fill_choice(choice, p) for p in picks]
    return [v for v in out if v is not None]
