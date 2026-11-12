"""「無聲」的來源檢查（BS-1，#157，``docs/design/06-技能.md`` 6.21.1 C）。

修正規則 ``silent_strike``（無聲）只能來自 **隱蔽關鍵字的技能**：

- 修正技能（被動常駐）直接帶 ``silent_strike``；
- 主動技能用 ``grant_skill`` 暫時給一個「只有無聲」的修正技能（:func:`is_silent_grant`）。

「隱蔽關鍵字的技能」＝ 技能的專屬關鍵字（``skill_keywords.yaml`` 的 exclusive 規則）恰好只有
``concealed``（``silent_strike`` 與「給無聲」本身就推導成隱蔽，所以這條等於「除了無聲以外，技能沒有
其他主題的專屬關鍵字」）。不能做成裝備詞條或武器特性：詞條沒有修正規則欄位；「授予動作」詞條給的
主動技能若會給無聲，由 :func:`carries_silent` 在詞條檢查擋下（``gear_checks``）。

內容載入（``trpg.content.library.load``）與技能驗證器（``trpg.skillgen.validate``，含 LLM 提議、
工坊、白板）共用 :func:`silent_strike_problems`。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.keyword_derive import derive_from_facts, facts_of
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skills import GRANT_SKILL, SkillDef, has_silent_rule

__all__ = [
    "CONCEALED_KEYWORD",
    "carries_silent",
    "grants_silent",
    "silent_strike_problems",
]

CONCEALED_KEYWORD = "concealed"


def grants_silent(skill: SkillDef, skills: Mapping[str, SkillDef]) -> bool:
    """``skill`` 有 ``grant_skill`` 效果（含複合第二段）給出帶無聲的技能。"""
    for effect in skill.iter_effects(include_followup=True):
        if effect.type != GRANT_SKILL or effect.skill is None:
            continue
        granted = skills.get(effect.skill)
        if granted is not None and has_silent_rule(granted):
            return True
    return False


def carries_silent(skill: SkillDef, skills: Mapping[str, SkillDef]) -> bool:
    """``skill`` 會讓持有者獲得無聲：自己帶 ``silent_strike`` 修正規則，或用 ``grant_skill``
    給出。"""
    return has_silent_rule(skill) or grants_silent(skill, skills)


def silent_strike_problems(
    skill: SkillDef, skills: Mapping[str, SkillDef], keywords: KeywordTable
) -> list[str]:
    """無聲放錯地方的問題（空串列＝沒問題或沒帶無聲）。``skills`` 是 ``grant_skill`` 查找的
    技能表。"""
    if not carries_silent(skill, skills):
        return []
    found = derive_from_facts(facts_of(skill), keywords, exclusive_only=True).all()
    if found == (CONCEALED_KEYWORD,):
        return []
    others = "、".join(k for k in found if k != CONCEALED_KEYWORD) or "沒有隱蔽"
    return [
        "無聲（silent_strike）只能放在隱蔽關鍵字的技能（被動常駐，或主動技能給幾回合），"
        f"這個技能的專屬關鍵字是：{others}"
    ]
