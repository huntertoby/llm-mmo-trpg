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

from trpg.shared.types import Attribute
from trpg.skillgen.option_models import Choice, FieldSpec

__all__ = ["field_problems"]

_DICE_RE = re.compile(r"^(\d+)d(\d+)$")

# 玩家看到的位置用中文（3-48，玩法決定 #44：不露欄位名或代號）
_LIST_NAME_ZH = {"effects": "效果", "modifiers": "修正規則", "variants": "變奏"}
_PART_ZH = {"followup": "第二段", "shape": "形狀", "cost": "費用"}
_INDEX_RE = re.compile(r"^(\w+)\[(\d+)\]$")
_ATTR_ZH = {a.value: a.display_name for a in Attribute}
_MAX_LISTED = 6


def _place(where: str) -> str:
    """欄位路徑 → 中文位置前綴（含結尾冒號）；欄位本身的名稱已在訊息裡，所以最後一段若不是
    列表項目就略過。例：``effects[1].distance`` → 「第 2 個效果：」；頂層欄位 → 空字串。"""
    parts = where.split(".") if where else []
    if parts and _INDEX_RE.match(parts[-1]) is None:
        parts = parts[:-1]
    out: list[str] = []
    for part in parts:
        m = _INDEX_RE.match(part)
        if m is not None:
            out.append(f"第 {int(m.group(2)) + 1} 個{_LIST_NAME_ZH.get(m.group(1), '項目')}")
        elif part in _PART_ZH:
            out.append(_PART_ZH[part])
    return "的".join(out) + "：" if out else ""


def _shown_zh(value: object) -> str:
    """值的中文名（屬性）；不認得的代號不顯示給玩家。"""
    text = value.get("type") if isinstance(value, Mapping) else value
    zh = _ATTR_ZH.get(text) if isinstance(text, str) else None
    return "" if zh is None else f"「{zh}」"


def _not_allowed(field: FieldSpec, value: object, where: str) -> str:
    names = [c.name_zh for c in field.choices]
    listed = "、".join(names[:_MAX_LISTED]) + ("等" if len(names) > _MAX_LISTED else "")
    head = f"{_place(where)}{field.name_zh}{_shown_zh(value)}不在可選範圍內"
    if field.field == "scaling_attr" and field.description_zh:
        return f"{head}。{field.description_zh}"
    return f"{head}（可選：{listed}）" if names else head


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
        return f"{_place(where)}{field.name_zh}必須是整數"
    if (field.min is not None and value < field.min) or (
        field.max is not None and value > field.max
    ):
        low = "" if field.min is None else field.min
        high = "" if field.max is None else field.max
        return f"{_place(where)}{field.name_zh}必須在 {low}–{high}，收到 {value}"
    return None


def _parent(where: str) -> str:
    return where.rsplit(".", 1)[0] if "." in where else ""


def _choice_problems(
    field: FieldSpec, value: object, container: Mapping[str, Any], where: str
) -> list[str]:
    """被選的選項的 ``params``：值是物件（形狀、條件、效果）時相對於該物件，否則相對於同一層。"""
    choice = _choice_of(field, value)
    if choice is None:
        return [_not_allowed(field, value, where)]
    if isinstance(value, Mapping):
        return field_problems(choice.params, value, where)
    return field_problems(choice.params, container, _parent(where))


def _items_problems(field: FieldSpec, value: object, where: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return [f"{_place(where)}{field.name_zh}必須是列表"]
    out: list[str] = []
    for index, item in enumerate(value):
        here = f"{where}[{index}]"
        if not isinstance(item, Mapping):
            out.append(f"{_place(here)}內容格式不對")
        elif field.type in ("modifiers", "variants"):
            out += field_problems(field.fields, item, here)
        else:
            out += _choice_problems(field, item, item, here)
    return out


def _multi_problems(field: FieldSpec, value: object, where: str) -> list[str]:
    values = value if isinstance(value, Sequence) and not isinstance(value, str) else [value]
    allowed = {c.value for c in field.choices}
    return [_not_allowed(field, v, where) for v in values if v not in allowed]


def _scalar_problems(field: FieldSpec, value: object, where: str) -> list[str]:
    if field.type == "dice":
        ok = isinstance(value, str) and _DICE_RE.match(value) is not None
        return [] if ok else [f"{_place(where)}{field.name_zh}必須是骰子寫法（例：2d6）"]
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
        if value is None or field.locked:  # 鎖定欄位的值由規則決定（3H-6），不算玩家填錯
            continue
        here = f"{where}.{field.field}" if where else field.field
        out += _one(field, value, container, here)
    return out
