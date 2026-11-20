"""技能結構的規則型上下限（HC-4b：從 ``constants.py`` 搬到 ``rules/core.yaml`` 的
``skill_limits``）。

這些上限是遊戲規則（設計文件寫成規則、內容／產生器／LLM 提議都要遵守），所以數字寫在內容檔，
``SkillDef`` 讀不到規則包，改在 ``Ruleset`` 層檢查（:func:`skill_limit_problems`）：載入內容庫
（``library/skill_checks.py``）、技能驗證器（``skillgen/validate.py`` 的 ``cap.limits``）與技能
工坊的草稿檢查（``skillgen/draft_check.py``，當成 schema 錯誤）都呼叫它。``SkillDef`` 自己只留
下限（至少 1 個效果、AP 至少 1……）與純護欄。推擊、拉扯的距離上限是原語表
（``skill_primitives.yaml``）的參數範圍，不在這裡。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from pydantic import Field

from trpg.content.schemas import ContentModel

if TYPE_CHECKING:
    from trpg.content.skills.effects import EffectSpec
    from trpg.content.skills.skill import SkillDef

__all__ = ["SkillLimits", "skill_limit_problems"]


class SkillLimits(ContentModel):
    """``rules/core.yaml`` 的 ``skill_limits``：技能結構的規則型上限（HC-4b，值照搬原本的常數）。"""

    tiers: int = Field(ge=1, le=10)
    """技能（＝角色）階級數：``tier`` 只能是 1～此值；``tier_budget`` 的鍵要剛好是 1～此值。"""
    max_ap_cost: int = Field(ge=1, le=9)
    """主動技能 ``ap_cost`` 的上限（1～此值；帶預支的是 0）；``skill_budget.yaml`` 的
    ``ap_coefficient_permille`` 的鍵要剛好是 1～此值。"""
    max_effects: int = Field(ge=1, le=20)
    """一個技能（複合技能兩段合計）最多幾個效果原語。"""
    max_cooldown: int = Field(ge=1, le=20)
    """``cost.cooldown`` 的上限（回合）。"""
    min_crit_range: int = Field(ge=2, le=20)
    """技能 ``crit_range`` 的下限（6.17 B）。"""
    max_grant_duration: int = Field(ge=1, le=20)
    """``grant_skill`` 的 ``duration`` 上限（輪，6.20）。"""
    max_summon_count: int = Field(ge=1, le=10)
    """一次召喚的數量：1 或此值（3-33f2 數量型分歧進化）。"""
    max_on_kill_effects: int = Field(ge=1, le=10)
    """``on_kill`` 的效果個數上限。"""
    max_refund_ap: int = Field(ge=1, le=10)
    """``on_kill`` 的 ``refund_ap`` 一次最多返還的 AP。"""
    max_zone_effects: int = Field(ge=1, le=10)
    """持續區域（``zone``）的子效果個數上限。"""
    max_branch_effects: int = Field(ge=1, le=10)
    """賭注分支（``win``／``lose``）與失手反噬（``cost.on_miss``）的效果個數上限。"""
    max_consume_then: int = Field(ge=1, le=10)
    """``consume_status`` 的 ``then`` 效果個數上限。"""
    max_cooldown_restore: int = Field(ge=1, le=10)
    """``restore_resource`` 的 ``resource: cooldown`` 一次最多縮短的回合。"""
    max_modifiers: int = Field(ge=1, le=10)
    """修正技能（``kind: modifier``）的規則數上限。"""
    max_mastery_modifiers: int = Field(ge=1, le=10)
    """專精（帶 ``exclusive_group`` 的修正技能）的規則數上限。"""
    max_variant_replacements: int = Field(ge=1, le=5)
    """一個戰場變奏最多填幾項替換內容。"""


_NESTED = ("then", "win", "lose", "on_kill", "effects")


def _walk(at: str, effect: EffectSpec) -> Iterator[tuple[str, EffectSpec]]:
    """效果本身與巢狀的效果，附完整路徑（同 ``SkillDef._check_effect`` 的寫法）。"""
    yield at, effect
    for group in _NESTED:
        for index, sub in enumerate(getattr(effect, group) or ()):
            yield from _walk(f"{at}.{group}[{index}]", sub)


def _all_effects(skill: SkillDef) -> Iterator[tuple[str, EffectSpec]]:
    for index, effect in enumerate(skill.effects):
        yield from _walk(f"effects[{index}]", effect)
    for index, effect in enumerate(skill.cost.on_miss):
        yield from _walk(f"cost.on_miss[{index}]", effect)


def skill_limit_problems(
    skill: SkillDef, limits: SkillLimits, *, count_effects: bool = True
) -> list[str]:
    """``skill`` 超出 ``limits`` 的地方（空串列為通過）：技能本身、複合技能的第二段
    （``followup.``）與每個變奏型態（``variants.<id>.``）。

    第二段與變奏型態沿用本技能的階級、代價，同一句不重報。``count_effects=False`` 時不看效果原語數
    （技能驗證器另有 ``cap.effects``，兩段合計）。"""
    problems = _segment_problems(skill, limits, count_effects=count_effects)
    follow = skill.followup_skill()
    if follow is not None:
        segment = _segment_problems(follow, limits, count_effects=count_effects)
        problems += [
            f"followup.{p}" for p in segment if p not in problems
        ]  # 沿用的階級、代價不重報
    for variant in skill.variants:
        form = _segment_problems(
            skill.variant_form(variant.id), limits, count_effects=count_effects
        )
        problems += [f"variants.{variant.id}.{p}" for p in form if p not in problems]
    return problems


def _segment_problems(skill: SkillDef, limits: SkillLimits, *, count_effects: bool) -> list[str]:
    problems = _top_problems(skill, limits, count_effects=count_effects)
    problems += _branch_problems(skill, limits)
    for at, effect in _all_effects(skill):
        problems += _effect_problems(at, effect, limits)
    for variant in skill.variants:
        count = len(variant.replacements)
        if count > limits.max_variant_replacements:
            problems.append(
                f"variants.{variant.id}：替換內容最多填 {limits.max_variant_replacements} 項，"
                f"收到 {count} 項"
            )
    return problems


def _top_problems(skill: SkillDef, limits: SkillLimits, *, count_effects: bool) -> list[str]:
    problems: list[str] = []
    if skill.tier > limits.tiers:
        problems.append(f"tier：技能階級只能是 1 到 {limits.tiers}，收到 {skill.tier}")
    if (
        skill.kind == "active"
        and not skill.borrows_ap
        and (skill.ap_cost or 0) > limits.max_ap_cost
    ):
        problems.append(
            f"主動技能的 ap_cost 必須是 1 到 {limits.max_ap_cost}，收到 {skill.ap_cost}"
        )
    if skill.kind == "modifier":
        limit = (
            limits.max_modifiers if skill.exclusive_group is None else limits.max_mastery_modifiers
        )
        if len(skill.modifiers) > limit:
            count = len(skill.modifiers)
            problems.append(f"修正技能的 modifiers 必須有 1 到 {limit} 條，收到 {count} 條")
    elif count_effects and len(skill.effects) > limits.max_effects:
        count = len(skill.effects)
        problems.append(f"效果原語必須有 1 到 {limits.max_effects} 個，收到 {count} 個")
    if count_effects and skill.followup is not None:
        total = len(skill.effects) + len(skill.followup.effects)
        if total > limits.max_effects:
            problems.append(f"複合技能兩段合計最多 {limits.max_effects} 個效果，收到 {total} 個")
    cooldown = skill.cost.cooldown
    if cooldown is not None and cooldown > limits.max_cooldown:
        problems.append(f"cost.cooldown：冷卻最多 {limits.max_cooldown} 回合，收到 {cooldown}")
    if skill.crit_range is not None and skill.crit_range < limits.min_crit_range:
        problems.append(f"crit_range：最小是 {limits.min_crit_range}，收到 {skill.crit_range}")
    return problems + _primitive_problems(skill, limits)


def _primitive_problems(skill: SkillDef, limits: SkillLimits) -> list[str]:
    """只看第一個召喚、暫時獲得技能、持續區域（同 ``SkillDef`` 的檢查；最多一個是原語表的規則）。"""
    problems: list[str] = []
    by_type: dict[str, EffectSpec] = {}
    for effect in skill.effects:
        by_type.setdefault(effect.type, effect)
    summon = by_type.get("summon")
    if summon is not None:
        count = summon.count or 1
        if count not in (1, limits.max_summon_count):
            problems.append(f"summon 的 count 只能是 1 或 {limits.max_summon_count}，收到 {count}")
    grant = by_type.get("grant_skill")
    if grant is not None and (grant.duration or 0) > limits.max_grant_duration:
        problems.append(
            f"grant_skill 的 duration 最多 {limits.max_grant_duration}，收到 {grant.duration}"
        )
    zone = by_type.get("zone")
    if zone is not None and len(zone.effects or ()) > limits.max_zone_effects:
        where = "effects[0]（zone）"
        problems.append(f"{where}：effects 必須有 1 到 {limits.max_zone_effects} 個效果")
    return problems


def _branch_problems(skill: SkillDef, limits: SkillLimits) -> list[str]:
    """賭注分支與失手反噬的效果數。"""
    branches = [("cost.on_miss", skill.cost.on_miss)]
    for index, effect in enumerate(skill.effects):
        if effect.type == "gamble":
            where = f"effects[{index}]（gamble）"
            branches += [
                (f"{where}.{name}", getattr(effect, name) or ()) for name in ("win", "lose")
            ]
    limit = limits.max_branch_effects
    return [
        f"{where}：必須有 1 到 {limit} 個效果，收到 {len(branch)}"
        for where, branch in branches
        if len(branch) > limit
    ]


def _effect_problems(at: str, effect: EffectSpec, limits: SkillLimits) -> list[str]:
    where = f"{at}（{effect.type}）"
    problems: list[str] = []
    if effect.on_kill is not None and len(effect.on_kill) > limits.max_on_kill_effects:
        problems.append(f"{where}：on_kill 必須有 1 到 {limits.max_on_kill_effects} 個效果")
    if effect.type == "refund_ap" and (effect.amount or 0) > limits.max_refund_ap:
        problems.append(f"{where}：必須填 amount（1–{limits.max_refund_ap}）")
    if effect.type == "consume_status" and len(effect.then or ()) > limits.max_consume_then:
        count = len(effect.then or ())
        problems.append(f"{where}：then 必須有 1 到 {limits.max_consume_then} 個效果，收到 {count}")
    restores_cooldown = effect.type == "restore_resource" and effect.resource == "cooldown"
    if restores_cooldown and (effect.amount or 1) > limits.max_cooldown_restore:
        problems.append(f"{where}：冷卻最多縮短 {limits.max_cooldown_restore} 回合")
    return problems
