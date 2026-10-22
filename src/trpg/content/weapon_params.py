"""武器資料參數的修改（Phase 3G-G2；裝備的「武器特性強化」詞條與載入時的檢查共用）。

參數路徑是 ``WeaponDef.model_dump()`` 的整數欄位（``knockback``）、巢狀欄位
（``armor_break.rounds``、``steady.hit``），或特例 ``range_mod.penalty``
（距離修正裡的懲罰部分乘上倍率）；開關欄位（``ignore_cover``）``delta`` 為正即開啟。純函式、
確定性。
"""

from __future__ import annotations

from typing import Any

__all__ = ["scale_penalties", "set_weapon_param", "truncate_permille"]

_PERMILLE = 1000


def truncate_permille(total: int) -> int:
    """千分比加總 ÷ 1000，無條件捨去（往 0 的方向）。"""
    return total // _PERMILLE if total >= 0 else -(-total // _PERMILLE)


def scale_penalties(entries: list[dict[str, Any]], factor: int) -> list[dict[str, Any]]:
    """距離修正裡的懲罰（命中為負、傷害低於 1000‰）乘上 ``factor``‰；加成不變。沒有任何修正的
    條目移除。"""
    result: list[dict[str, Any]] = []
    for entry in entries:
        hit, damage = entry["hit"], entry["damage_permille"]
        if hit < 0:
            hit = truncate_permille(hit * factor)
        if damage < _PERMILLE:
            damage = _PERMILLE - truncate_permille((_PERMILLE - damage) * factor)
        if hit != 0 or damage != _PERMILLE:
            result.append({**entry, "hit": hit, "damage_permille": damage})
    return result


def _turn_on(holder: dict[str, Any], key: str, delta: int | None) -> bool:
    if delta is None or delta <= 0:
        return False
    holder[key] = True
    return True


def set_weapon_param(
    data: dict[str, Any], param: str, delta: int | None, factor: int | None
) -> bool:
    """依參數路徑改武器資料（``model_dump`` 的字典）；路徑不存在（例如武器沒有該特性）時不動作。"""
    head, _, tail = param.partition(".")
    if param == "range_mod.penalty":
        if factor is None or not data.get("range_mod"):
            return False
        data["range_mod"] = scale_penalties(data["range_mod"], factor)
        return True
    holder: Any = data if not tail else data.get(head)
    key = tail or head
    value = holder.get(key) if isinstance(holder, dict) else None
    if isinstance(value, bool):  # 開關參數（例如 ignore_cover）：``delta`` 為正 ＝ 開啟
        return _turn_on(holder, key, delta)
    if not isinstance(value, int):
        return False
    if delta is not None:
        holder[key] = value + delta
    elif factor is not None:
        holder[key] = truncate_permille(value * factor)
    else:
        return False
    return True
