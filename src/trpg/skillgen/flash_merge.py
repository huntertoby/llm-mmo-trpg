"""提議的選項與資料補位選項的合併（Phase 3W-7）。

來源（LLM 提議或重播）先提議一批變化，``make_offer`` 把其中合格的選項放前面，
不夠的數量用資料順序的選項補滿；不指定類別時至少涵蓋 ``min_categories`` 類（做得到時）：提議全擠在
同一類時，從後面換成補位選項裡別的類別。純函式，不依賴 :mod:`trpg.skillgen.flash`。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from trpg.skillgen.flash_state import Variation

__all__ = ["merge_options"]


class _HasVariation(Protocol):
    @property
    def variation(self) -> Variation: ...


def _categories[T: _HasVariation](options: Sequence[T]) -> set[str]:
    return {o.variation.category for o in options}


def merge_options[T: _HasVariation](
    proposed: Sequence[T], filler: Sequence[T], count: int, *, min_categories: int = 1
) -> list[T]:
    """提議的放前面、補位的接在後面，最多 ``count`` 個，變化不重複。沒有提議時原樣回傳補位。"""
    if not proposed:
        return list(filler)[:count]
    out: list[T] = []
    keys: set[str] = set()
    for option in [*proposed[:count], *filler]:
        key = option.variation.key()
        if len(out) < count and key not in keys:
            keys.add(key)
            out.append(option)
    proposed_keys = {o.variation.key() for o in proposed}
    spare = [o for o in filler if o.variation.key() not in keys]
    for option in spare:
        if len(_categories(out)) >= min_categories:
            break
        if option.variation.category in _categories(out):
            continue
        # 換掉最後一個「類別重複」的提議（補位選項本身不換）
        slot = next(
            (
                i
                for i in range(len(out) - 1, -1, -1)
                if out[i].variation.key() in proposed_keys
                and sum(x.variation.category == out[i].variation.category for x in out) > 1
            ),
            None,
        )
        if slot is None:
            break
        out[slot] = option
    return out
