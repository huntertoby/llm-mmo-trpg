"""檢查已填的值是否落在選項之內（Phase 3F-1）：:class:`~trpg.skillgen.option_models.FieldSpec`
的通用比對，給 :func:`trpg.skillgen.options.draft_options` 的 ``problems`` 用（Phase 4 也可以拿來
先過濾 LLM 的輸出）。

只檢查「填了但不在範圍或選項內」：選項（``choice``、``multi_choice``）、整數範圍（含 ``weapon``）、
``count``、骰子格式，並遞迴
檢查被選的選項的 ``params``、``object`` 的子欄位、效果與修正規則的每一項。
沒填的必填欄位不算問題（那是「還沒完成」）。骰子的面數與顆數上限只是建議（組合器的階梯），
不檢查。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from trpg.skillgen.option_models import Choice, FieldSpec

__all__ = ["field_problems"]

_DICE_RE = re.compile(r"^(\d+)d(\d+)$")


def _get(container: Mapping[str, Any], path: str) -> Any:
    value: Any = container
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _choice_of(field: FieldSpec, value: object) -> Choice | None:
    key = value.get("type") if isinstance(value, Mapping) else value
    return next((c for c in field.choices if c.value == key and type(c.value) is type(key)), None)


def _int_problem(field: FieldSpec, value: object, where: str) -> str | None:
    if field.allow_weapon and value == "weapon":
        return None
    if field.type == "count" and value == "all":
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        return f"{where}：{field.name_zh}必須是整數，收到 {value!r}"
    if (field.min is not None and value < field.min) or (
        field.max is not None and value > field.max
    ):
        low = "" if field.min is None else field.min
        high = "" if field.max is None else field.max
        return f"{where}：{field.name_zh}必須在 {low}–{high}，收到 {value}"
    return None


def _parent(where: str) -> str:
    return where.rsplit(".", 1)[0] if "." in where else ""


def _choice_problems(
    field: FieldSpec, value: object, container: Mapping[str, Any], where: str
) -> list[str]:
    """被選的選項的 ``params``：值是物件（形狀、條件、效果）時相對於該物件，否則相對於同一層。"""
    choice = _choice_of(field, value)
    if choice is None:
        shown = value.get("type") if isinstance(value, Mapping) else value
        return [f"{where}：{field.name_zh}「{shown}」不是合法的選項"]
    if isinstance(value, Mapping):
        return field_problems(choice.params, value, where)
    return field_problems(choice.params, container, _parent(where))


def _items_problems(field: FieldSpec, value: object, where: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return [f"{where}：{field.name_zh}必須是列表"]
    out: list[str] = []
    for index, item in enumerate(value):
        here = f"{where}[{index}]"
        if not isinstance(item, Mapping):
            out.append(f"{here}：必須是物件")
        elif field.type in ("modifiers", "variants"):
            out += field_problems(field.fields, item, here)
        else:
            out += _choice_problems(field, item, item, here)
    return out


def _multi_problems(field: FieldSpec, value: object, where: str) -> list[str]:
    values = value if isinstance(value, Sequence) and not isinstance(value, str) else [value]
    allowed = {c.value for c in field.choices}
    return [f"{where}：{field.name_zh}「{v}」不是合法的選項" for v in values if v not in allowed]


def _scalar_problems(field: FieldSpec, value: object, where: str) -> list[str]:
    if field.type == "dice":
        ok = isinstance(value, str) and _DICE_RE.match(value) is not None
        return [] if ok else [f"{where}：{field.name_zh}必須是 NdM 骰子，收到 {value!r}"]
    problem = _int_problem(field, value, where)
    return [] if problem is None else [problem]


def _one(field: FieldSpec, value: object, container: Mapping[str, Any], where: str) -> list[str]:
    kind = field.type
    if kind == "choice":
        return _choice_problems(field, value, container, where)
    if kind in ("int", "count", "dice"):
        return _scalar_problems(field, value, where)
    if kind in ("modifiers", "variants") or (kind == "effects" and field.choices):
        return _items_problems(field, value, where)
    if kind == "multi_choice":
        return _multi_problems(field, value, where)
    if kind == "object" and isinstance(value, Mapping):
        return field_problems(field.fields, value, where)
    return []


def field_problems(
    fields: Sequence[FieldSpec], container: Mapping[str, Any], where: str = ""
) -> list[str]:
    """``container`` 中已填、但不在 ``fields`` 的範圍或選項內的值（中文訊息）。"""
    out: list[str] = []
    for field in fields:
        value = _get(container, field.field)
        if value is None:
            continue
        here = f"{where}.{field.field}" if where else field.field
        out += _one(field, value, container, here)
    return out
