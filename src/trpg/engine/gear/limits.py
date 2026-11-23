"""裝備效果的名額（E6-b1，``docs/design/08-裝備.md`` 8.27、8.30 第 4、5、10 點，#180）。

建立單位時（:func:`trpg.engine.lifecycle.make_unit`），在 :func:`~trpg.engine.gear.core.build_gear`
的遞減之後套用：

- **改寫規則同時 1 個**（``caps.rule_affixes``）：生效中的第 11 類詞條依詞條 id 分組，超過名額的
  標灰（``weight_permille`` 設 0、``limited_by="rule"``）。誰留下：玩家勾選的（``Loadout.chosen``）
  優先，其次照欄位固定順序（主手 → 戒指 2），再依詞條 id。

標灰一律只把權重設 0：授予的技能、反應、規則改變都只看生效中的詞條，自然不生效。

這個模組是確定性的純函式（需要順序時一律排序）。
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import replace

from trpg.content.equipment import Loadout, chosen_key
from trpg.content.library import Ruleset
from trpg.content.slots import SLOT_INDEX
from trpg.engine.gear.state import GearAffix, GearState, LimitReason

__all__ = ["limit_gear", "limit_priority"]


def limit_priority(entry: GearAffix, chosen: Collection[str]) -> tuple[int, int, str, int]:
    """名額的先後（越小越先）：勾選的優先，其次欄位固定順序，再依詞條 id、同 id 的順序。"""
    picked = 0 if chosen_key(entry.slot, entry.affix.id) in chosen else 1
    return (picked, SLOT_INDEX[entry.slot], entry.affix.id, entry.rank)


def _grey(gear: GearState, losers: Collection[int], reason: LimitReason) -> GearState:
    """把 ``gear.affixes`` 第 ``losers`` 條標灰。"""
    if not losers:
        return gear
    affixes = tuple(
        replace(a, weight_permille=0, limited_by=reason) if i in losers else a
        for i, a in enumerate(gear.affixes)
    )
    return replace(gear, affixes=affixes)


def _limit_rules(gear: GearState, chosen: Collection[str], cap: int) -> GearState:
    """改寫規則：生效中的不同詞條 id 最多 ``cap`` 個，其他標灰（``rule``）。"""
    active = [(i, a) for i, a in enumerate(gear.affixes) if a.active and a.affix.category == "rule"]
    best: dict[str, tuple[int, int, str, int]] = {}
    for _, entry in active:
        key = limit_priority(entry, chosen)
        best[entry.affix.id] = min(best.get(entry.affix.id, key), key)
    kept = set(sorted(best, key=lambda affix_id: best[affix_id])[:cap])
    return _grey(gear, {i for i, a in active if a.affix.id not in kept}, "rule")


def limit_gear(gear: GearState, loadout: Loadout, rules: Ruleset) -> GearState:
    """套用改寫規則的名額（見模組說明）。沒有要標灰的時候原樣回傳。"""
    if not gear.affixes:
        return gear
    chosen = frozenset(loadout.chosen)
    return _limit_rules(gear, chosen, rules.equipment.caps.rule_affixes)
