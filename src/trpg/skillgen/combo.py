"""複合技能的「自己造環境又引爆」檢查（Phase 3F-4a，``docs/design/06-技能.md`` 6.23 共同規則）。

一招複合技能的兩段之間若形成元素或表面連鎖——第一段產生表面或施加狀態，第二段的元素會引爆或改變
它（依 ``content/interactions.yaml`` 與狀態的 ``removed_by_element`` 判斷），或第二段直接消耗
第一段施加的狀態——就是「自己造環境又引爆」。做法（PM 讓實作者擇一）：**不拒絕，預算加價**
``composite_self_combo_permille``（初值 1000‰，點數翻倍），見
:func:`trpg.skillgen.budget.skill_budget`。

只看技能資料裡明寫的東西：第一段的 ``create_surface`` 表面與 ``apply_status`` 狀態（含巢狀的
``then``／賭注分支／擊殺時效果），第二段效果的 ``element``、``create_surface`` 表面與
``consume_status`` 狀態。武器傷害沒寫元素時繼承武器（施放前不知道），不算。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.skills import CONSUME_STATUS, SkillDef

__all__ = ["self_combo_reasons"]


def self_combo_reasons(skill: SkillDef, library: ContentLibrary) -> tuple[str, ...]:
    """複合技能兩段之間的元素／表面連鎖（每一條是一句繁體中文說明，依發現順序、不重複）；不是
    複合技能或沒有連鎖時為空。"""
    follow = skill.followup_skill()
    if follow is None:
        return ()
    first = list(skill.iter_effects())
    second = list(follow.iter_effects())
    surfaces = {e.surface for e in first if e.type == "create_surface" and e.surface is not None}
    statuses = {e.status for e in first if e.type == "apply_status" and e.status is not None}
    elements = {e.element for e in second if e.element is not None}
    created = {e.surface for e in second if e.type == "create_surface" and e.surface is not None}
    reasons: list[str] = []
    for rule in library.ruleset.interactions.rules:
        if rule.trigger == "element" and rule.element in elements:
            hit = rule.surface if rule.target == "surface" else rule.unit_surface
            if hit is not None and hit in surfaces:
                reasons.append(
                    f"第一段產生的表面 {hit.value} 會被第二段的 {rule.element.value} 元素改變"
                    f"（互動 {rule.id}）"
                )
        elif rule.trigger == "surface_created" and rule.surface_created in created:
            if rule.surface is not None and rule.surface in surfaces:
                reasons.append(
                    f"第二段產生的表面 {rule.surface_created.value} 會與第一段的表面 "
                    f"{rule.surface.value} 互動（互動 {rule.id}）"
                )
    status_defs = library.ruleset.statuses.by_id()
    for status in sorted(statuses):
        definition = status_defs.get(status)
        removed = () if definition is None else definition.removed_by_element
        for element in removed:
            if element in elements:
                reasons.append(f"第一段施加的狀態 {status} 會被第二段的 {element.value} 元素解除")
    for effect in second:
        if effect.type == CONSUME_STATUS and effect.status in statuses:
            reasons.append(f"第二段消耗第一段施加的狀態 {effect.status}")
    return tuple(dict.fromkeys(reasons))
