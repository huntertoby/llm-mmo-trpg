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
from trpg.content.skills.conditions import ConditionSpec

if TYPE_CHECKING:
    from trpg.content.skills.effects import EffectSpec
    from trpg.content.skills.modifiers import ModifierSpec
    from trpg.content.skills.skill import SkillDef

__all__ = ["ModifierLimits", "SkillLimits", "skill_limit_problems"]


class ModifierLimits(ContentModel):
    """``skill_limits.modifier_bounds``：修正規則（``kind: modifier``）改變幅度的規則型上下限
    （HC-4b2 從 ``skills/modifiers.py`` 的 ``ModifierChange`` 與 ``skills/constants.py`` 搬來，
    值照搬；Phase 3C 4.1）。``ModifierChange`` 只留另一側的界線與純護欄。"""

    damage_permille_min: int = Field(ge=-1000, le=-1)
    """``damage_permille`` 的下限（‰；上限 +1000 是 ‰ 護欄，留在 schema）。"""
    heal_permille_min: int = Field(ge=-1000, le=-1)
    """``heal_permille`` 的下限（‰；上限 +1000 同上）。"""
    hit_bonus_max: int = Field(ge=1, le=20)
    """``hit_bonus`` 的絕對值上限（命中 −此值～＋此值）。"""
    cooldown_delta_max: int = Field(ge=1, le=20)
    """``cooldown_delta`` 一次最多縮短幾回合（−1～−此值）。"""
    push_distance_delta_max: int = Field(ge=1, le=10)
    """``push_distance_delta`` 的上限（格；結果另外截斷在 ``core.max_displace_distance``，
    不能比它大）。"""
    range_delta_max: int = Field(ge=1, le=10)
    """``range_delta`` 的上限（格；下限 −1 留在 schema）。"""
    summon_duration_delta_max: int = Field(ge=1, le=10)
    """``summon_duration_delta`` 的上限（輪）。"""
    max_add_tags: int = Field(ge=1, le=10)
    """``add_tags`` 最多幾個標籤。"""
    max_on_hit_effects: int = Field(ge=1, le=10)
    """``on_hit_effects`` 最多幾個效果。"""
    on_hit_max_displace: int = Field(ge=1, le=10)
    """命中後效果的推擊、拉扯距離上限（格；不能比 ``core.max_displace_distance`` 大，
    HC-4b 裁定 3）。"""


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
    max_rank: int = Field(ge=1, le=10)
    """``SkillDef.rank`` 的上限（HC-4d，原本是 schema 的 ``le=5``）。"""
    min_self_status_duration: int = Field(ge=1, le=10)
    max_self_status_duration: int = Field(ge=1, le=10)
    """自身狀態代價（``cost.self_status``）的回合範圍（Phase 2H-1：2～3，1 等於沒有效果；
    HC-4d）。"""
    max_source_cost: int = Field(ge=1, le=10)
    """傳說技能 ``cost.source`` 的上限（Phase 3C-4a：1 或 2；HC-4d）。"""
    max_stance_upkeep: int = Field(ge=0, le=10)
    """姿態維持費（``stance_upkeep``）的點數上限（6.34.4；HC-4d）。"""
    max_any_of: int = Field(ge=1, le=10)
    """條件的 ``any_of`` 最多再幾個（Phase 3W-2b；HC-4d）。"""
    every_n_hits: tuple[int, ...] = Field(min_length=1)
    """``every_n_hits`` 的 ``n`` 只能是這些值（HC-4d）；``skill_triggers.yaml`` 的
    ``budget_by_n_permille`` 要剛好有這些鍵（``Ruleset`` 層檢查）。"""
    min_beside_power_permille: int = Field(ge=1, le=1000)
    """召喚到身邊（TF-1）縮小版的最低強度（‰；上限 1000 是 ‰ 護欄；HC-4d）。"""
    max_overload_backlash: int = Field(ge=1, le=10)
    """層數超載（``stacks.yaml`` 的 ``overload.backlash``）最多幾個反噬效果（Phase 3D-7b；HC-4d，
    ``Ruleset`` 層檢查）。"""
    modifier_bounds: ModifierLimits
    """修正規則改變幅度的上下限（HC-4b2）。"""


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
    for index, rule in enumerate(skill.modifiers):
        problems += _modifier_problems(f"modifiers[{index}]", rule, limits.modifier_bounds)
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
    return problems + _cost_problems(skill, limits) + _primitive_problems(skill, limits)


def _cost_problems(skill: SkillDef, limits: SkillLimits) -> list[str]:
    """等階、自身狀態代價、源力、姿態維持費、條件「或」與每 N 次命中（HC-4d，原本是 schema 的
    上下限；訊息的數字從規則組字）。"""
    problems: list[str] = []
    if skill.rank > limits.max_rank:
        problems.append(f"rank：最大是 {limits.max_rank}，收到 {skill.rank}")
    self_status = skill.cost.self_status
    low, high = limits.min_self_status_duration, limits.max_self_status_duration
    if self_status is not None and not low <= self_status.duration <= high:
        problems.append(
            f"cost.self_status.duration：必須是 {low}～{high}，收到 {self_status.duration}"
        )
    source = skill.cost.source
    if source is not None and source > limits.max_source_cost:
        problems.append(f"cost.source：源力最多 {limits.max_source_cost}，收到 {source}")
    if skill.stance_upkeep > limits.max_stance_upkeep:
        top = limits.max_stance_upkeep
        problems.append(f"stance_upkeep：維持費最多 {top} 點，收到 {skill.stance_upkeep}")
    for at, condition in _conditions(skill):
        count = len(condition.any_of or ())
        if count > limits.max_any_of:
            problems.append(f"{at}.any_of：最多 {limits.max_any_of} 個條件，收到 {count}")
    trigger = skill.trigger
    if trigger is not None and trigger.event == "every_n_hits":
        allowed = limits.every_n_hits
        if trigger.n not in allowed:
            shown = " 或 ".join(str(n) for n in allowed)
            problems.append(f"trigger.n：every_n_hits 的 n 必須是 {shown}，收到 {trigger.n}")
    return problems


def _conditions(skill: SkillDef) -> Iterator[tuple[str, ConditionSpec]]:
    """技能本身、修正規則與每個效果（含巢狀）的條件（第二段與變奏型態另外當成一段檢查）。"""
    if skill.condition is not None:
        yield "condition", skill.condition
    for index, rule in enumerate(skill.modifiers):
        if rule.condition is not None:
            yield f"modifiers[{index}].condition", rule.condition
    for at, effect in _all_effects(skill):
        if effect.condition is not None:
            yield f"{at}.condition", effect.condition


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


def _modifier_problems(at: str, rule: ModifierSpec, limits: ModifierLimits) -> list[str]:
    """一條修正規則的改變超出幅度（HC-4b2；訊息同原本 schema 的字句，數字從規則組字）。"""
    change = rule.change
    kind = change.kind
    value = getattr(change, kind)
    where = f"{at}.change.{kind}"
    bounds: dict[str, tuple[int | None, int | None]] = {
        "damage_permille": (limits.damage_permille_min, None),
        "heal_permille": (limits.heal_permille_min, None),
        "hit_bonus": (-limits.hit_bonus_max, limits.hit_bonus_max),
        "cooldown_delta": (-limits.cooldown_delta_max, None),
        "push_distance_delta": (None, limits.push_distance_delta_max),
        "range_delta": (None, limits.range_delta_max),
        "summon_duration_delta": (None, limits.summon_duration_delta_max),
    }
    problems: list[str] = []
    if kind in bounds:
        low, high = bounds[kind]
        if (low is not None and value < low) or (high is not None and value > high):
            shown_low = "" if low is None else f"最小 {low}"
            shown_high = "" if high is None else f"最大 {high}"
            span = "、".join(s for s in (shown_low, shown_high) if s)
            problems.append(f"{where}：{span}，收到 {value}")
    elif kind == "add_tags" and len(value) > limits.max_add_tags:
        problems.append(f"{where}：必須有 1 到 {limits.max_add_tags} 個標籤，收到 {len(value)} 個")
    elif kind == "on_hit_effects":
        problems += _on_hit_problems(where, value, limits)
    return problems


def _on_hit_problems(
    where: str, effects: tuple[EffectSpec, ...], limits: ModifierLimits
) -> list[str]:
    problems: list[str] = []
    if len(effects) > limits.max_on_hit_effects:
        problems.append(
            f"{where}：必須有 1 到 {limits.max_on_hit_effects} 個效果，收到 {len(effects)} 個"
        )
    top = limits.on_hit_max_displace
    for index, effect in enumerate(effects):
        if effect.type in ("push", "pull") and (effect.distance or 0) > top:
            problems.append(
                f"{where}[{index}]：推擊與拉扯的距離必須是 1 到 {top} 格，收到 {effect.distance}"
            )
    return problems


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
    power = effect.power_permille
    low = limits.min_beside_power_permille
    if effect.type == "summon_beside" and power is not None and power < low:
        problems.append(
            f"{where}：summon_beside 的 power_permille 必須在 {low}～1000（縮小版召喚物）"
        )
    return problems
