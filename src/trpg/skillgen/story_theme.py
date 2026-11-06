"""劇情技能換元素（Phase 6L-2；07 7.6「LLM 只依玩家的關鍵字換元素、名稱、描述」）。

純函式，給世界引擎與 API 層（LLM 提議）共用：

- :func:`story_elements`：可以換的元素選單——玩家持有的關鍵字（只看專屬規則）裡，
  ``skill_keywords.yaml`` 有「``effect: damage`` ＋ ``element``」製造規則的元素（例：點燃 →
  火焰、帶電 → 雷電）。依關鍵字的持有數由多到少、同數依推導表順序；不重複。
- :func:`retheme`：把技能 **頂層的傷害效果** 與技能的主題元素換成 ``element``，標籤裡的元素名稱
  也換掉；其他欄位（形狀、骰子、費用、冷卻、骨架）都不動。換完後預算分數必須和原本
  **完全相同**、驗證器的問題數不增加，否則回傳 ``None``（呼叫者照用原本的技能）。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.validate import validate_skill

__all__ = ["damage_elements", "retheme", "story_elements"]


def damage_elements(skill: SkillDef) -> tuple[str, ...]:
    """技能頂層傷害效果的元素（依效果順序、不重複）。"""
    found = [
        Element(e.element).value
        for e in skill.effects
        if e.type == "damage" and e.element is not None
    ]
    return tuple(dict.fromkeys(found))


def story_elements(library: ContentLibrary, keyword_counts: Mapping[str, int]) -> tuple[str, ...]:
    """玩家的關鍵字對得到的傷害元素（見模組說明）。"""
    order = {k: i for i, k in enumerate(library.keywords.ids())}
    ranked = sorted(
        (k for k, n in keyword_counts.items() if n > 0 and k in order),
        key=lambda k: (-keyword_counts[k], order[k]),
    )
    by_id = {k.id: k for k in library.keywords.keywords}
    out: list[str] = []
    for keyword in ranked:
        for rule in by_id[keyword].makes:
            if rule.effect == "damage" and rule.element is not None and rule.grade == "exclusive":
                out.append(Element(rule.element).value)
    return tuple(dict.fromkeys(out))


def retheme(library: ContentLibrary, skill: SkillDef, element: str) -> SkillDef | None:
    """``skill`` 換成 ``element`` 的版本（見模組說明）；沒有可換的傷害效果、元素相同或預算變了時
    ``None``。"""
    old = damage_elements(skill)
    if not old or old == (element,):
        return None
    elements = {e.id for e in library.elements.elements}
    if element not in elements:
        return None
    swap = set(old)
    effects = tuple(
        e.model_copy(update={"element": Element(element)})
        if e.type == "damage" and e.element in swap
        else e
        for e in skill.effects
    )
    element_ids = elements
    tag = Element(element).value
    tags = tuple(dict.fromkeys(tag if t in element_ids else t for t in skill.tags))
    update: dict[str, object] = {"effects": effects, "tags": tags}
    if skill.element is not None:
        update["element"] = Element(element)
    new = skill.model_copy(update=update)
    try:
        same = skill_budget(new, library).total == skill_budget(skill, library).total
    except BudgetError:
        return None
    if not same:
        return None
    if len(validate_skill(new, library)) > len(validate_skill(skill, library)):
        return None
    return new
