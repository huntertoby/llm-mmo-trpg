"""修正規則（Phase 3C-2，``docs/phases/Phase3C計畫.md`` 4、``docs/design/06-技能.md``
6.14.1、6.14.3）。

修正技能（``kind: modifier``）不能施放，而是持續改變 **持有者自己** 的動作：普攻（含藉機攻擊）、
推擊、絆倒、互動與施放的技能（主動、姿態、反應技）。被動觸發與陷阱觸發的效果不算「你的動作」，
不受修正（也避免命中後效果再被修正而遞迴）。

一次動作由 :class:`Use` 描述（基本動作或技能）。每個查詢函式都依 **技能 ID 排序、再依規則索引**
走過持有者的修正規則（:func:`unit_rules`），數值類（傷害‰、命中、距離、AP、射程、冷卻）全部加總後
套用一次，結果取整數；元素取第一條符合的規則。

條件（``condition``）沿用技能條件：``self_hp_below`` 看持有者，其他看 ``subject``
（這次動作的目標）。

這個模組只讀取狀態，不修改。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from trpg.content.skills import BasicAction, ModifierSpec, SkillDef, default_affects
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Element

__all__ = [
    "ATTACK",
    "INTERACT",
    "SHOVE",
    "TRIP",
    "ActiveRule",
    "Use",
    "ap_cost",
    "cooldown_delta",
    "damage_element",
    "damage_permille",
    "displace_distance",
    "displace_split",
    "effective_tags",
    "grants_pierce",
    "hit_bonus",
    "is_attack_skill",
    "on_hit_rules",
    "range_delta",
    "skill_use",
    "unit_rules",
]

_PERMILLE = 1000
_HOSTILE = ("enemies", "all")


@dataclass(frozen=True, slots=True)
class Use:
    """被修正的一次動作：基本動作（``action``）或技能（``skill``），兩者恰好一個。"""

    action: BasicAction | None = None
    skill: SkillDef | None = None


ATTACK = Use(action="attack")
SHOVE = Use(action="shove")
TRIP = Use(action="trip")
INTERACT = Use(action="interact")


def skill_use(skill: SkillDef) -> Use:
    return Use(skill=skill)


@dataclass(frozen=True, slots=True)
class ActiveRule:
    """持有者身上的一條修正規則：來源技能、規則索引與規則本身。"""

    skill: SkillDef
    index: int
    rule: ModifierSpec


def unit_rules(state: BattleState, unit: UnitState) -> tuple[ActiveRule, ...]:
    """``unit`` 的全部修正規則（依技能 ID、再依規則索引）。"""
    rules = state.ruleset
    if not rules.has_modifier(unit.skills):
        return ()
    found: list[ActiveRule] = []
    for skill_id in sorted(unit.skills):
        skill = rules.skill_def(skill_id)
        if skill.is_modifier:
            found.extend(ActiveRule(skill, i, rule) for i, rule in enumerate(skill.modifiers))
    return tuple(found)


def is_attack_skill(state: BattleState, skill: SkillDef) -> bool:
    """「攻擊技能」（``all_attacks`` 的對象）：有對敵方（``enemies``／``all``）的傷害效果。"""
    rules = state.ruleset
    return any(
        e.type == "damage"
        and (e.affects or default_affects(rules.primitive_def(e.type))) in _HOSTILE
        for e in skill.effects
    )


def _matches(state: BattleState, rule: ModifierSpec, use: Use, tags: Iterable[str]) -> bool:
    target = rule.applies_to
    if use.skill is None:
        assert use.action is not None
        return use.action in target.actions or (target.all_attacks and use.action == "attack")
    if target.all_skills:
        return True
    if target.all_attacks and is_attack_skill(state, use.skill):
        return True
    return bool(set(target.skill_tags) & set(tags))


def _self_holds(state: BattleState, unit: UnitState, rule: ModifierSpec) -> bool:
    return condition_met(state, unit, rule.condition, Subject(unit, unit.xy))


def effective_tags(state: BattleState, unit: UnitState, skill: SkillDef) -> tuple[str, ...]:
    """技能的實際標籤：原本的標籤，再加上 ``add_tags`` 規則（以原本的標籤比對對象，只做一層，
    不會因為加上的標籤再觸發其他 ``add_tags``）給的標籤；依加入順序、不重複。"""
    tags = list(skill.tags)
    use = skill_use(skill)
    for active in unit_rules(state, unit):
        rule = active.rule
        added = rule.change.add_tags
        if not added or not _matches(state, rule, use, skill.tags):
            continue
        if _self_holds(state, unit, rule):
            tags += [t for t in added if t not in tags]
    return tuple(tags)


def _applicable(
    state: BattleState, unit: UnitState, use: Use, change: str
) -> Iterator[ModifierSpec]:
    """``unit`` 套用在 ``use`` 上、``change`` 種類的規則（未檢查條件）。"""
    rules = unit_rules(state, unit)
    if not rules:
        return
    tags = effective_tags(state, unit, use.skill) if use.skill is not None else ()
    for active in rules:
        rule = active.rule
        if getattr(rule.change, change) is not None and _matches(state, rule, use, tags):
            yield rule


def _sum_self(state: BattleState, unit: UnitState, use: Use, change: str) -> int:
    return sum(
        getattr(rule.change, change)
        for rule in _applicable(state, unit, use, change)
        if _self_holds(state, unit, rule)
    )


def _sum_for(state: BattleState, unit: UnitState, use: Use, change: str, subject: Subject) -> int:
    return sum(
        getattr(rule.change, change)
        for rule in _applicable(state, unit, use, change)
        if condition_met(state, unit, rule.condition, subject)
    )


def ap_cost(state: BattleState, unit: UnitState, use: Use, base: int) -> int:
    """修正後的 AP 成本：``base`` 加上 ``ap_delta``，至少 1；不花 AP 的（反應技、被動）不變。"""
    if base <= 0:
        return base
    return max(1, base + _sum_self(state, unit, use, "ap_delta"))


def range_delta(state: BattleState, unit: UnitState, use: Use) -> int:
    """射程的修正量（``range_delta`` 加總；呼叫端負責「結果至少 1」）。"""
    return _sum_self(state, unit, use, "range_delta")


def hit_bonus(state: BattleState, unit: UnitState, use: Use, subject: Subject) -> int:
    """對 ``subject`` 的命中修正（``hit_bonus`` 加總）。"""
    return _sum_for(state, unit, use, "hit_bonus", subject)


def damage_permille(state: BattleState, unit: UnitState, use: Use, subject: Subject) -> int:
    """對 ``subject`` 的傷害倍率（‰）：1000 ＋ ``damage_permille`` 加總，下限 0。"""
    return max(0, _PERMILLE + _sum_for(state, unit, use, "damage_permille", subject))


def damage_element(state: BattleState, unit: UnitState, use: Use, base: Element) -> Element:
    """傷害的元素：物理傷害改為第一條成立的 ``add_element``；已有元素的不覆寫。"""
    if base is not Element.PHYSICAL:
        return base
    for rule in _applicable(state, unit, use, "add_element"):
        if _self_holds(state, unit, rule):
            assert rule.change.add_element is not None
            return rule.change.add_element
    return base


def grants_pierce(state: BattleState, unit: UnitState, use: Use) -> bool:
    """有沒有成立的 ``grant_pierce`` 規則讓這個技能獲得穿透（Phase 3C-5b；是否真的有效由
    :func:`trpg.engine.skills.targeting.pierce_active` 依形狀與武器判斷）。"""
    return any(
        _self_holds(state, unit, rule) for rule in _applicable(state, unit, use, "grant_pierce")
    )


def displace_split(
    state: BattleState, unit: UnitState, use: Use, subject: Subject, base: int
) -> tuple[int, int]:
    """推擊／拉扯的 ``(距離, 額外撞擊次數)``：``base`` 加上 ``push_distance_delta``，距離截斷在
    ``max_displace_distance``，超過的每 1 格改為一次撞擊傷害（Phase 3C-3a；推完之後結算，就算
    沒有撞到東西也算）。``base`` 本身已超過上限時距離不變。"""
    delta = _sum_for(state, unit, use, "push_distance_delta", subject)
    if delta <= 0:
        return base, 0
    total = base + delta
    distance = max(base, min(total, state.ruleset.core.max_displace_distance))
    return distance, total - distance


def displace_distance(
    state: BattleState, unit: UnitState, use: Use, subject: Subject, base: int
) -> int:
    """:func:`displace_split` 的距離部分。"""
    return displace_split(state, unit, use, subject, base)[0]


def cooldown_delta(
    state: BattleState, unit: UnitState, use: Use, subjects: Iterable[Subject]
) -> int:
    """命中後的冷卻修正：每條規則在「被命中的目標中至少一個」符合條件時計入（加總，≤ 0）。"""
    hit = list(subjects)
    if not hit:
        return 0
    total = 0
    for rule in _applicable(state, unit, use, "cooldown_delta"):
        if any(condition_met(state, unit, rule.condition, s) for s in hit):
            assert rule.change.cooldown_delta is not None
            total += rule.change.cooldown_delta
    return total


def on_hit_rules(state: BattleState, unit: UnitState, use: Use) -> list[ActiveRule]:
    """套用在 ``use`` 上、有命中後效果的規則（依技能 ID、規則索引；條件由觸發結算時判斷）。"""
    rules = unit_rules(state, unit)
    if not rules:
        return []
    tags = effective_tags(state, unit, use.skill) if use.skill is not None else ()
    return [
        a
        for a in rules
        if a.rule.change.on_hit_effects is not None and _matches(state, a.rule, use, tags)
    ]
