"""數值工坊：形狀的「沒填參數時」基礎倍率有沒有招用到（HC-W2 裁定 1、HC-6c）。

錐形、十字、環形、連鎖的倍率依參數查表（``shape_budget.<形狀>.by_value`` 等）；只有沒填參數
（或查不到）時才用 ``base_permille``。內建、生成的招都會填參數，所以這幾格常常沒有任何一招用到，
工坊說明要多一句「目前沒有招用到，改了暫時沒效果」。

判斷由資料算：把這格換成另一個數，重算內容庫全部技能（含道具技能）的預算，都和原本相同就算沒有
招用到。只看有查表的形狀（沒有查表的形狀，基礎值就是倍率本身，生成的招一用到就有效）。
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Final

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import BudgetError, BudgetReport, skill_budget

__all__ = ["UNUSED_BASE_NOTE_ZH", "unused_base_note", "unused_shape_bases"]

UNUSED_BASE_NOTE_ZH: Final = "目前沒有招用到，改了暫時沒效果。"
"""HC-W2 裁定 1 的說明句（接在欄位說明後面）。"""

_BASE_PATH: Final = re.compile(r"shape_budget\.(?P<shape>[^.]+)\.base_permille")
_CACHE_SIZE: Final = 4
_cache: dict[int, tuple[ContentLibrary, frozenset[str]]] = {}


def _skills(library: ContentLibrary) -> list[SkillDef]:
    skills = dict(library.skills)
    for skill_id, item in sorted(library.world_economy.item_skills().items()):
        if item.skill is not None:
            skills.setdefault(skill_id, item.skill)
    return [skills[k] for k in sorted(skills)]


def _reports(skills: list[SkillDef], library: ContentLibrary) -> list[BudgetReport | str]:
    out: list[BudgetReport | str] = []
    for skill in skills:
        try:
            out.append(skill_budget(skill, library))
        except BudgetError as error:
            out.append(f"BudgetError: {error}")
    return out


def _compute(library: ContentLibrary) -> frozenset[str]:
    skills = _skills(library)
    before = _reports(skills, library)
    budget = library.budget
    unused: set[str] = set()
    for shape_id, price in sorted(budget.shape_budget.items()):
        if not (price.by_value or price.non_power_by_value or price.solid_by_value):
            continue
        moved = price.model_copy(update={"base_permille": price.base_permille + 1})
        table = {**budget.shape_budget, shape_id: moved}
        changed = replace(library, budget=budget.model_copy(update={"shape_budget": table}))
        if _reports(skills, changed) == before:
            unused.add(shape_id)
    return frozenset(unused)


def unused_shape_bases(library: ContentLibrary) -> frozenset[str]:
    """``base_permille`` 改了也不影響任何一招預算的形狀 ID（只看有查表的形狀）；依內容庫快取。"""
    hit = _cache.get(id(library))
    if hit is not None and hit[0] is library:
        return hit[1]
    found = _compute(library)
    if len(_cache) >= _CACHE_SIZE:
        _cache.clear()
    _cache[id(library)] = (library, found)
    return found


def unused_base_note(path: str, library: ContentLibrary | None) -> str | None:
    """欄位 ``shape_budget.<形狀>.base_permille`` 沒有招用到時的說明句；其他欄位、沒有內容庫時
    ``None``。"""
    found = _BASE_PATH.fullmatch(path)
    if library is None or found is None:
        return None
    return UNUSED_BASE_NOTE_ZH if found.group("shape") in unused_shape_bases(library) else None
