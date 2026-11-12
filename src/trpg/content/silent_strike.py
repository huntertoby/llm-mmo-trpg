"""「無聲」的來源檢查（BS-1，#157，``docs/design/06-技能.md`` 6.21.1 C）。

修正規則 ``silent_strike``（無聲）只能來自 **隱蔽關鍵字的技能**：

- 修正技能（被動常駐）直接帶 ``silent_strike``；
- 主動技能用 ``grant_skill`` 暫時給一個「只有無聲」的修正技能（:func:`is_silent_grant`）。

「隱蔽關鍵字的技能」＝ 技能要帶隱蔽關鍵字，**可以同時帶別的關鍵字**（BS-3，06 6.21.1「BS-1 後的
細節」第 2 點：毒＋隱蔽、火＋隱蔽的刺客招都可以）。``silent_strike`` 與「給無聲」本身在
``skill_keywords.yaml`` 推導成隱蔽，所以判斷時先把無聲本身拿掉，看技能其餘部分的專屬關鍵字：

- 沒有任何專屬關鍵字（技能的主題就只有無聲，例：無聲步、影纏）→ 通過；
- 有專屬關鍵字而且包含 ``concealed`` → 通過（毒＋隱蔽、火＋隱蔽）；
- 有專屬關鍵字但沒有 ``concealed``（只有毒、只有火）→ 擋。

不能做成裝備詞條或武器特性：詞條沒有修正規則欄位；「授予動作」詞條給的主動技能若會給無聲，
由 :func:`carries_silent` 在詞條檢查擋下（``gear_checks``，不分技能主題一律擋）。

內容載入（``trpg.content.library.load``）與技能驗證器（``trpg.skillgen.validate``，含 LLM 提議、
工坊、白板）共用 :func:`silent_strike_problems`。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from trpg.content.keyword_derive import Facts, derive_from_facts, facts_of
from trpg.content.skill_keywords import KeywordTable
from trpg.content.skills import GRANT_SKILL, EffectSpec, SkillDef, has_silent_rule

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


def _without_silence(facts: Facts, skills: Mapping[str, SkillDef]) -> Facts:
    """拿掉無聲本身的事實：``silent_strike`` 修正規則與給出帶無聲技能的 ``grant_skill`` 效果。"""

    def gives_silence(effect: EffectSpec) -> bool:
        if effect.type != GRANT_SKILL or effect.skill is None:
            return False
        granted = skills.get(effect.skill)
        return granted is not None and has_silent_rule(granted)

    return replace(
        facts,
        effects=tuple(e for e in facts.effects if not gives_silence(e)),
        modifiers=tuple(r for r in facts.modifiers if not r.change.silent_strike),
    )


def silent_strike_problems(
    skill: SkillDef, skills: Mapping[str, SkillDef], keywords: KeywordTable
) -> list[str]:
    """無聲放錯地方的問題（空串列＝沒問題或沒帶無聲）。``skills`` 是 ``grant_skill`` 查找的
    技能表。"""
    if not carries_silent(skill, skills):
        return []
    rest = _without_silence(facts_of(skill), skills)
    found = derive_from_facts(rest, keywords, exclusive_only=True).all()
    if not found or CONCEALED_KEYWORD in found:
        return []
    names = {k.id: k.name_zh for k in keywords.keywords}
    return [
        "無聲（silent_strike）只能放在帶隱蔽關鍵字的技能（被動常駐，或主動技能給幾回合；"
        "可以同時帶別的關鍵字），這個技能除了無聲以外的專屬關鍵字是："
        + "、".join(names.get(k, k) for k in found)
        + "，沒有隱蔽"
    ]
