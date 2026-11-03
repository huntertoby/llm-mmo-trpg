"""背包的格數與加減物品（Phase 5D-R1，集中 economy、crafting、loot、gear 與 API 檢視原本各寫一份的
算法）。

- **格數**（:func:`slots_used`）：每種物品 ceil(個數 ÷ 疊數)（代決 5D1-2），背包裡的裝備每件 1 格
  （5D-2）。
- **容量**（:func:`room_problem`、:func:`check_room`、:func:`slots_over`）：上限是經濟規則的
  ``bag_slots``。**內容庫沒有經濟規則（``world/economy.yaml``）時背包沒有格數上限**（5D-R1 統一：
  打造、分解、掉落、換裝原本就如此；經濟動作本身沒有規則時已先拒絕，所以行為不變）。
- **加減物品**（:func:`add_items`、:func:`remove_items`）：回傳依物品 ID 排序的新字典，個數 0 的
  拿掉。
- **移除裝備**（:func:`remove_gear`）：從背包拿掉裝備，連同 5D-3 的改動紀錄（``gear_mods``）。

純函式：不讀時間、不呼叫 LLM、沒有亂數。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from trpg.content.library import ContentLibrary
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState

__all__ = [
    "add_items",
    "bag_capacity",
    "check_room",
    "remove_gear",
    "remove_items",
    "room_problem",
    "slots_over",
    "slots_used",
]


def bag_capacity(library: ContentLibrary) -> int | None:
    """背包格數上限；沒有經濟規則時為 ``None``（沒有上限）。"""
    rules = library.world_economy.rules
    return None if rules is None else rules.bag_slots


def _stack(library: ContentLibrary, item: str) -> int:
    rules = library.world_economy.rules
    found = library.world_economy.items.get(item)
    if rules is None or found is None:
        return 1
    return rules.stack_max[found.kind]


def slots_used(library: ContentLibrary, bag: Mapping[str, int], gear: int = 0) -> int:
    """背包用掉的格數：每種物品 ceil(個數 ÷ 疊數)，再加 ``gear`` 件裝備（每件 1 格）。
    沒有經濟規則時每種物品算 1 格。"""
    if library.world_economy.rules is None:
        return len(bag) + gear
    return sum(-(-count // _stack(library, item)) for item, count in bag.items()) + gear


def slots_over(library: ContentLibrary, bag: Mapping[str, int], gear: int = 0) -> int:
    """超出上限的格數（沒超出、或沒有上限時為 0）。"""
    cap = bag_capacity(library)
    return 0 if cap is None else max(0, slots_used(library, bag, gear) - cap)


def room_problem(library: ContentLibrary, bag: Mapping[str, int], gear: int = 0) -> str | None:
    """放不下的原因（「背包放不下（需要 N 格，只有 M 格）」）；放得下或沒有上限時為 ``None``。"""
    cap = bag_capacity(library)
    if cap is None:
        return None
    used = slots_used(library, bag, gear)
    if used > cap:
        return f"背包放不下（需要 {used} 格，只有 {cap} 格）"
    return None


def check_room(library: ContentLibrary, bag: Mapping[str, int], gear: int = 0) -> None:
    """放不下就拋 :class:`WorldActionError`（見 :func:`room_problem`）。"""
    problem = room_problem(library, bag, gear)
    if problem is not None:
        raise WorldActionError(problem)


def add_items(counts: Mapping[str, int], items: Mapping[str, int]) -> dict[str, int]:
    """加上物品（個數要是正的）；回傳依 ID 排序的新字典。"""
    updated = dict(counts)
    for item, count in items.items():
        updated[item] = updated.get(item, 0) + count
    return dict(sorted(updated.items()))


def remove_items(counts: Mapping[str, int], items: Mapping[str, int]) -> dict[str, int]:
    """拿掉物品；不夠就拋 :class:`WorldActionError`（「材料不夠：ID（要 N，有 M）」）。回傳依 ID
    排序的新字典，個數 0 的拿掉。"""
    updated = dict(counts)
    for item, count in items.items():
        have = updated.get(item, 0)
        if have < count:
            raise WorldActionError(f"材料不夠：{item}（要 {count}，有 {have}）")
        if have == count:
            del updated[item]
        else:
            updated[item] = have - count
    return dict(sorted(updated.items()))


def remove_gear(char: CharacterState, ids: Iterable[str]) -> CharacterState:
    """從背包拿掉這些 ID 的裝備（各拿第一件），連同它們的改動紀錄（``gear_mods``）；背包裡沒有就
    拋 :class:`WorldActionError`。"""
    gear = list(char.gear)
    removed: list[str] = []
    for gear_id in ids:
        piece = next((g for g in gear if g.id == gear_id), None)
        if piece is None:
            raise WorldActionError(f"背包裡沒有這件裝備：{gear_id}")
        gear.remove(piece)
        removed.append(gear_id)
    mods = {k: v for k, v in char.gear_mods.items() if k not in removed}
    return char.model_copy(update={"gear": tuple(gear), "gear_mods": mods})
