"""營火的免費屬性重配（Phase 3H-3，``docs/design/07-角色成長.md`` 7.2「重配」）。

和營火換技能同一個畫面、同一個精神：

- ``RunState.attribute_spent``：玩家分配出去的屬性點（開局的自由配點＋每次升級的配點＋重配後再分配的
  點數）；範本的基礎屬性（``base_attribute``）不在內。
- :func:`respec_attributes`：營火免費——分配出去的點數全部退回 ``RunState.attribute_points``，屬性
  回到基礎；之後用 :func:`allocate_attributes` 重新分配（不推進節點，營火、戰前都可以分配）。
- 純函式（``RunState`` 進、``RunState`` 出），存檔是 ``RunState`` 的欄位，所以存檔與重播一致；
  最大 HP 隨體質的同步調整由 :mod:`trpg.roguelite.progress` 的包裝處理（和升級配點一樣）。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.state import RunState
from trpg.shared.types import Attribute

__all__ = ["allocate_attributes", "merge_spent", "respec_attributes", "spent_total"]


def spent_total(run: RunState) -> int:
    """目前分配出去（可以重配退回）的屬性點總數。"""
    return sum(run.attribute_spent.values())


def merge_spent(
    spent: Mapping[Attribute, int], allocation: Mapping[Attribute, int]
) -> dict[Attribute, int]:
    """把 ``allocation`` 併進已分配的屬性點（只留 > 0 的項目，依六屬性順序存入，序列化確定）。"""
    return {
        a: spent.get(a, 0) + allocation.get(a, 0)
        for a in Attribute
        if spent.get(a, 0) + allocation.get(a, 0) > 0
    }


def respec_attributes(run: RunState) -> RunState:
    """全部分配出去的屬性點退回（屬性回到基礎），沒有分配過時不變。"""
    spent = run.attribute_spent
    if not spent:
        return run
    attributes = {a: run.hero.attributes[a] - spent.get(a, 0) for a in Attribute}
    hero = run.hero.model_copy(update={"attributes": attributes})
    return run.model_copy(
        update={
            "hero": hero,
            "attribute_points": run.attribute_points + spent_total(run),
            "attribute_spent": {},
        }
    )


def allocate_attributes(run: RunState, allocation: Mapping[Attribute, int]) -> RunState:
    """把未分配的屬性點（``attribute_points``）分配出去。每項不可為負；總數不可超過未分配的點數
    （可以只分一部分，剩下的之後再分）。不合法時拋出 :class:`ChoiceError`（狀態不變）。"""
    negative = [a.display_name for a, v in allocation.items() if v < 0]
    if negative:
        raise ChoiceError(f"配點不可為負：{'、'.join(negative)}")
    total = sum(allocation.values())
    if total <= 0:
        raise ChoiceError("沒有要分配的屬性點")
    if total > run.attribute_points:
        raise ChoiceError(f"屬性點不足：要分配 {total} 點，只有 {run.attribute_points} 點")
    attributes = {a: run.hero.attributes[a] + allocation.get(a, 0) for a in Attribute}
    return run.model_copy(
        update={
            "hero": run.hero.model_copy(update={"attributes": attributes}),
            "attribute_points": run.attribute_points - total,
            "attribute_spent": merge_spent(run.attribute_spent, allocation),
        }
    )
