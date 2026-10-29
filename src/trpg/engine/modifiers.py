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

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from trpg.content.skills import (
    SHAPE_CHANGES,
    BasicAction,
    ModifierSpec,
    ShapeSpec,
    SkillDef,
    default_affects,
)
from trpg.engine.actions import UseSkill
from trpg.engine.activations import is_active
from trpg.engine.attack_element import (
    attack_element_sources,
    resolve_attack_element,
)
from trpg.engine.gear.core import cap_damage_bonus, gear_damage_parts, gear_hit_bonus
from trpg.engine.gear.enhance import (
    gear_area_delta,
    gear_keyword_damage_permille,
    gear_rune_read_permille,
    gear_status_duration,
    spend_gear_rune_read,
)
from trpg.engine.rules.forms import form_heal_permille, held_weapon, natural_damage_permille
from trpg.engine.skill_levels import grow_shape, leveled_skill
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import BattleState, UnitState
from trpg.engine.variants import target_point, varied_skill
from trpg.shared.types import Element

__all__ = [
    "ATTACK",
    "CHANGE_HANDLERS",
    "INTERACT",
    "SHOVE",
    "TRIP",
    "ActiveRule",
    "Use",
    "acting_skill",
    "ap_cost",
    "cooldown_delta",
    "damage_element",
    "damage_permille",
    "displace_distance",
    "displace_split",
    "effective_tags",
    "empty_active_slots",
    "form_entry_permille",
    "form_upkeep_permille",
    "grants_pierce",
    "heal_permille",
    "hit_bonus",
    "is_attack_skill",
    "offhand_spell_permille",
    "on_hit_rules",
    "range_delta",
    "reap_permille",
    "rule_limit_key",
    "rule_limit_reached",
    "shaped_skill",
    "skill_has_fire",
    "skill_is_fiery",
    "skill_use",
    "spend_attack_limits",
    "status_duration_bonus",
    "summon_attack_dice",
    "summon_damage_permille",
    "summon_duration_delta",
    "summon_hp_permille",
    "summon_limit_delta",
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
    """``unit`` 的全部修正規則（依技能 ID、再依規則索引）。修正型傳說（Phase 3D-6，
    ``activation``）只在啟動後生效。"""
    rules = state.ruleset
    if not rules.has_modifier(unit.skills):
        return ()
    found: list[ActiveRule] = []
    for skill_id in sorted(unit.skills):
        skill = rules.skill_def(skill_id)
        if skill.is_modifier and (not skill.is_activatable or is_active(unit, skill_id)):
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
    if target.weapon_skills and use.skill.category == "weapon":
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


def _applicable_active(
    state: BattleState, unit: UnitState, use: Use, change: str
) -> Iterator[ActiveRule]:
    """``unit`` 套用在 ``use`` 上、``change`` 種類的規則（未檢查條件）。"""
    rules = unit_rules(state, unit)
    if not rules:
        return
    tags = effective_tags(state, unit, use.skill) if use.skill is not None else ()
    for active in rules:
        rule = active.rule
        if getattr(rule.change, change) is not None and _matches(state, rule, use, tags):
            yield active


def _applicable(
    state: BattleState, unit: UnitState, use: Use, change: str
) -> Iterator[ModifierSpec]:
    """:func:`_applicable_active` 的規則本身。"""
    for active in _applicable_active(state, unit, use, change):
        yield active.rule


def rule_limit_key(skill_id: str, index: int) -> str:
    """修正規則 ``per_turn_limit`` 的計數鍵（存在 ``UnitState.gear_turn_counts``，自己回合開始時
    清除；Phase 3-31）。"""
    return f"rule:{skill_id}:{index}"


def rule_limit_reached(unit: UnitState, active: ActiveRule) -> bool:
    """規則帶 ``per_turn_limit`` 且本回合已用完。"""
    limit = active.rule.per_turn_limit
    return (
        limit is not None
        and unit.gear_turn_counts.get(rule_limit_key(active.skill.id, active.index), 0) >= limit
    )


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
    """對 ``subject`` 的命中修正（``hit_bonus`` 加總，再加上裝備的命中加值，Phase 3G-G1）。"""
    return _sum_for(state, unit, use, "hit_bonus", subject) + gear_hit_bonus(state, unit, subject)


def empty_active_slots(state: BattleState, unit: UnitState) -> int:
    """主動技能欄的空格數（Phase 3-32a，普攻精通）：``core.skill_slots.active`` 減去單位裝備的
    主動技能數（裝備授予的常駐技能、暫時獲得的技能不算；下限 0）。結算當下由技能欄推算，不存
    狀態。"""
    rules = state.ruleset
    used = sum(1 for skill_id in unit.skills if rules.skill_def(skill_id).slot_kind == "active")
    return max(0, rules.core.skill_slots.active - used)


def _rule_amount(state: BattleState, unit: UnitState, active: ActiveRule, change: str) -> int:
    """規則的改變量；帶 ``empty_slots_cap`` 的傷害加成依空格數（最多 cap 格）乘上去。"""
    amount: int = getattr(active.rule.change, change)
    cap = active.rule.empty_slots_cap
    if cap is None:
        return amount
    return amount * min(cap, empty_active_slots(state, unit))


def _split_for(
    state: BattleState, unit: UnitState, use: Use, change: str, subject: Subject
) -> tuple[int, int]:
    """:func:`_sum_for` 分成 ``(正的加總, 負的加總)``（本回合次數已用完的規則不計）。"""
    gain = loss = 0
    for active in _applicable_active(state, unit, use, change):
        if rule_limit_reached(unit, active):
            continue
        if condition_met(state, unit, active.rule.condition, subject):
            amount = _rule_amount(state, unit, active, change)
            if amount > 0:
                gain += amount
            else:
                loss += amount
    return gain, loss


def summon_damage_bonus(state: BattleState, unit: UnitState, use: Use, subject: Subject) -> int:
    """召喚物自己的傷害加成（‰；Phase 3-33b，6.29.1）：召喚當下快照的成長加成，**計入施放者全身
    +50% 上限**——施放者自己的正向傷害加成（修正規則、裝備、技能強化）先占用上限，召喚物的加成
    只能用掉剩下的空間（召喚者已不在場時視為 0）。不是召喚物、或沒有加成時為 0。"""
    if unit.owner_id is None or unit.summon_bonus_permille <= 0:
        return 0
    owner = state.units.get(unit.owner_id)
    used = 0
    if owner is not None:
        gain, _ = _split_for(state, owner, use, "damage_permille", subject)
        gear_gain, _ = gear_damage_parts(state, owner, subject)
        keyword = gear_keyword_damage_permille(state, owner, use.skill, use.action == "attack")
        used = gain + gear_gain + keyword
    room = max(0, state.ruleset.equipment.caps.damage_bonus_permille - used)
    return min(unit.summon_bonus_permille, room)


def reap_permille(unit: UnitState, use: Use, subject: Subject) -> int:
    """武器的收割（Phase 3I-1，08 8.11，鐮刀）：普攻或武器技、目標 **當下** HP ≤ 最大 HP 的
    ``hp_permille``‰ 時的傷害加成（‰）；其他情況 0。和其他正向加成一起套全身 +50% 上限。"""
    reap = (
        unit.weapon if use.action == "attack" else held_weapon(unit)
    ).reap  # 武器技看手上武器（3J-1a）
    target = subject.unit
    if reap is None or target is None or not target.alive or target.max_hp <= 0:
        return 0
    weapon_use = use.action == "attack" or (
        use.skill is not None and use.skill.category == "weapon"
    )
    if not weapon_use or target.hp * _PERMILLE > reap.hp_permille * target.max_hp:
        return 0
    return reap.damage_permille


def offhand_spell_permille(unit: UnitState, use: Use) -> int:
    """副手的法術增幅（Phase 3I-2，08 8.11，法書）：施放者的法術技（``category: spell``）傷害加成
    （‰）；普攻、武器技與其他技能為 0。和其他正向加成一起套全身 +50% 上限。"""
    offhand = unit.gear.offhand
    if offhand is None or use.skill is None or use.skill.category != "spell":
        return 0
    return offhand.spell_damage_permille


def damage_permille(state: BattleState, unit: UnitState, use: Use, subject: Subject) -> int:
    """對 ``subject`` 的傷害倍率（‰）：1000 ＋ 傷害加成 ＋ 減益，下限 0。

    傷害加成是 **所有來源合計**（Phase 3G-G2，08 8.21.5.3）：修正規則的 ``damage_permille``、裝備的
    條件數值與代價型（3G-G1）、裝備的技能強化（3G-G2）的正值加總後，套全身傷害加成上限（+50%）；
    負值（減益）不受上限限制，直接相加。
    """
    gain, loss = _split_for(state, unit, use, "damage_permille", subject)
    gear_gain, gear_loss = gear_damage_parts(state, unit, subject)
    keyword = gear_keyword_damage_permille(state, unit, use.skill, use.action == "attack")
    rune = gear_rune_read_permille(state, unit, use, subject)  # 普攻讀取符文（3-31）
    summon = summon_damage_bonus(state, unit, use, subject)  # 召喚物成長的加成（3-33b）
    reap = reap_permille(unit, use, subject)  # 鐮刀的收割（3I-1）
    book = offhand_spell_permille(unit, use)  # 法書的法術增幅（3I-2）
    natural = natural_damage_permille(state.ruleset, unit) if use.action == "attack" else 0
    capped = cap_damage_bonus(
        state.ruleset, gain + gear_gain + keyword + rune + summon + reap + book + natural
    )
    total = max(0, _PERMILLE + capped + loss + gear_loss)
    # 數量型分歧進化（3-33f2）：每隻只有一般的 power_permille ‰ 傷害
    power = unit.summon_power_permille
    return total if power >= _PERMILLE else total * power // _PERMILLE


def spend_attack_limits(state: BattleState, unit: UnitState, use: Use, subject: Subject) -> None:
    """普攻的傷害真的結算時，記下本回合用掉的「每回合 1 次」加傷（Phase 3-31）。

    帶 ``per_turn_limit`` 的修正規則（傷害‰）與普攻的讀取符文詞條，條件成立且次數還沒用完的才
    計一次。必須在 :func:`damage_permille` 之後、同一個 ``subject`` 呼叫。"""
    for active in _applicable_active(state, unit, use, "damage_permille"):
        if active.rule.per_turn_limit is None or rule_limit_reached(unit, active):
            continue
        if condition_met(state, unit, active.rule.condition, subject):
            key = rule_limit_key(active.skill.id, active.index)
            unit.gear_turn_counts[key] = unit.gear_turn_counts.get(key, 0) + 1
    if use.action == "attack":
        spend_gear_rune_read(state, unit, subject)


def status_duration_bonus(state: BattleState, unit: UnitState, use: Use, status: str) -> int:
    """裝備的技能強化讓這次動作施加的 ``status`` 多持續幾回合（Phase 3G-G2）。"""
    return gear_status_duration(state, unit, use.skill, use.action == "attack", status)


def heal_permille(state: BattleState, unit: UnitState, use: Use) -> int:
    """你的治療量倍率（‰）：1000 ＋ ``heal_permille`` 加總，下限 0（Phase 3-24b1；技能的治療與聖光
    雙效的治療，不含狀態與表面的回合開始治療、吸血）。"""
    form = form_heal_permille(state.ruleset, unit)  # 形態的治療加成（Phase 3J-1a）
    return max(0, _PERMILLE + _sum_self(state, unit, use, "heal_permille") + form)


def summon_hp_permille(state: BattleState, unit: UnitState, use: Use) -> int:
    """你召喚的召喚物最大 HP 倍率（‰）：1000 ＋ ``summon_hp_permille`` 加總（召喚時結算）。"""
    return _PERMILLE + _sum_self(state, unit, use, "summon_hp_permille")


def summon_attack_dice(state: BattleState, unit: UnitState, use: Use) -> int:
    """你召喚的召喚物攻擊傷害骰多出的顆數（``summon_attack_dice`` 加總；召喚時結算）。"""
    return _sum_self(state, unit, use, "summon_attack_dice")


def _sum_unit(state: BattleState, unit: UnitState, change: str) -> int:
    """持有者全部修正規則裡 ``change`` 種類的改變量加總（不看 ``applies_to``，條件看持有者）。"""
    return sum(
        getattr(active.rule.change, change)
        for active in unit_rules(state, unit)
        if getattr(active.rule.change, change) is not None and _self_holds(state, unit, active.rule)
    )


def form_upkeep_permille(state: BattleState, unit: UnitState) -> int:
    """形態維持費的倍率改變（‰；``form_upkeep_permille`` 加總，不低於 −1000；化形專精，3J-3）。"""
    return max(-_PERMILLE, _sum_unit(state, unit, "form_upkeep_permille"))


def form_entry_permille(state: BattleState, unit: UnitState) -> int:
    """形態進入獎勵的數值倍率改變（‰；``form_entry_permille`` 加總；化形專精，3J-3）。"""
    return _sum_unit(state, unit, "form_entry_permille")


def summon_limit_delta(state: BattleState, unit: UnitState, use: Use) -> int:
    """你同時存在的召喚物上限的修正量（``summon_limit_delta`` 加總；召喚專精，3-33f1）。"""
    return _sum_self(state, unit, use, "summon_limit_delta")


def summon_duration_delta(state: BattleState, unit: UnitState, use: Use) -> int:
    """你召喚的召喚物多持續幾輪（``summon_duration_delta`` 加總；召喚時結算，3-33f1）。"""
    return _sum_self(state, unit, use, "summon_duration_delta")


def summon_damage_permille(state: BattleState, unit: UnitState, use: Use) -> int:
    """你召喚的召喚物傷害加成（‰；``summon_damage_permille`` 加總；召喚時快照，3-33f1）。"""
    return _sum_self(state, unit, use, "summon_damage_permille")


def damage_element(state: BattleState, unit: UnitState, use: Use, base: Element) -> Element:
    """傷害的元素：物理傷害改為第一條成立的 ``add_element``；已有元素的不覆寫。

    普攻（Phase 3I-6）依 :func:`trpg.engine.attack_element.resolve_attack_element` 的優先順序
    （附魔 ＞ 武器本身元素 ＞ 修正技能 ＞ 普攻附加詞條 ＞ 武器元素詞條；06 6.10 #52 補充二；
    ``base`` 被忽略）。
    """
    if use.action == "attack":
        sources = attack_element_sources(state.ruleset, unit)
        sources = replace(sources, modifier=_added_element(state, unit, use))
        return resolve_attack_element(sources, is_basic=True)
    if base is not Element.PHYSICAL:
        return base
    added = _added_element(state, unit, use)
    return base if added is None else added


def _added_element(state: BattleState, unit: UnitState, use: Use) -> Element | None:
    """第一條成立的修正規則 ``add_element``；沒有為 ``None``。"""
    for rule in _applicable(state, unit, use, "add_element"):
        if _self_holds(state, unit, rule):
            assert rule.change.add_element is not None
            return rule.change.add_element
    return None


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


def skill_has_fire(skill: SkillDef) -> bool:
    """技能本身帶火：標籤有 ``fire``，或有元素為火的效果（不看修正規則）。"""
    return "fire" in skill.tags or any(e.element is Element.FIRE for e in skill.effects)


def skill_is_fiery(state: BattleState, unit: UnitState, skill: SkillDef) -> bool:
    """``unit`` 施放 ``skill`` 時帶火元素（Phase 3D-3，投擲的爆炸物是否引爆用）：技能本身帶火、
    修正規則加上 ``fire`` 標籤，或修正規則讓物理傷害變成火元素（``add_element``）。"""
    if skill_has_fire(skill) or "fire" in effective_tags(state, unit, skill):
        return True
    return damage_element(state, unit, skill_use(skill), Element.PHYSICAL) is Element.FIRE


# ---------------------------------------------------------------------------
# 技能變形（Phase 3D-3）：範圍 +1、形狀轉換、施放者也算在內
# ---------------------------------------------------------------------------


def acting_skill(
    state: BattleState, unit: UnitState, skill_id: str, action: UseSkill | None = None
) -> SkillDef:
    """``unit`` 施放 ``skill_id`` 時實際使用的技能：基礎 → 戰場變奏（Phase 3-25a，依 ``action``
    的目標點選型態；沒給 ``action`` 時是基礎型態）→ 技能等級 → 修正（:func:`shaped_skill`）。"""
    skill = state.ruleset.skill_def(skill_id)
    if action is not None and skill.variants:
        skill = varied_skill(state, unit, skill, target_point(state, action))[0]
    return shaped_skill(state, unit, skill)


def shaped_skill(state: BattleState, unit: UnitState, skill: SkillDef) -> SkillDef:
    """套用持有者的變形規則（``shape_to``、``area_delta``、``allow_self_target``）後的技能。

    變形在選目標之前決定（條件只能是 ``self_hp_below``），所以合法動作（``legal_actions``）、預覽、
    網頁的目標選取與實際結算都用這個技能，彼此一致。只有主動技能會變形；沒有成立的規則時回傳原技能
    （同一個物件）。技能的 ID、標籤、效果與代價不變，所以其他修正規則照常套用。

    順序：先依技能 ID、規則索引依序套用 ``shape_to``（每條至多轉一次，可以接續轉，例如
    單體 → 直線 → 錐形），再把每條 ``area_delta`` 的 +1 加上去，最後看 ``allow_self_target``。
    """
    skill = leveled_skill(state.ruleset, unit, skill)  # 技能等級的 5 級小特性（Phase 3-26a）
    if skill.kind != "active" or not (state.ruleset.has_modifier(unit.skills) or unit.gear.affixes):
        return skill
    if skill.followup is not None:  # 複合技能（Phase 3F-3a）的兩段形狀不變形（保守做法）
        return skill
    rules = _shape_rules(state, unit, skill) if state.ruleset.has_modifier(unit.skills) else []
    gear_area = gear_area_delta(state, unit, skill)  # 裝備的技能強化（3G-G2）
    if not rules and not gear_area:
        return skill
    shape = skill.shape
    for rule in rules:
        if rule.change.shape_to is not None:
            shape = _convert(state, unit, skill, shape, rule.change.shape_to)
    for rule in rules:
        if rule.change.area_delta is not None:
            shape = _grow(state, shape, rule.change.area_delta)
    if gear_area:
        shape = _grow(state, shape, gear_area)
    include = skill.include_caster or (
        any(r.change.allow_self_target for r in rules) and _helps_allies(state, skill)
    )
    if shape == skill.shape and include == skill.include_caster:
        return skill
    return skill.model_copy(update={"shape": shape, "include_caster": include})


def _shape_rules(state: BattleState, unit: UnitState, skill: SkillDef) -> list[ModifierSpec]:
    use = skill_use(skill)
    tags = effective_tags(state, unit, skill)
    return [
        active.rule
        for active in unit_rules(state, unit)
        if active.rule.change.kind in SHAPE_CHANGES
        and _matches(state, active.rule, use, tags)
        and _self_holds(state, unit, active.rule)
    ]


def _convert(
    state: BattleState, unit: UnitState, skill: SkillDef, shape: ShapeSpec, target: str
) -> ShapeSpec:
    """``shape`` 轉成 ``target``：不在轉換表、效果原語不支援新形狀（或有陷阱）時維持原樣。"""
    rules = state.ruleset
    conversion = next(
        (c for c in rules.shapes.conversions if c.from_shape == shape.type and c.to == target),
        None,
    )
    if conversion is None or skill.trap is not None:
        return shape
    for effect in skill.effects:
        allowed = rules.primitive_def(effect.type).allowed_shapes
        if allowed is not None and target not in allowed:
            return shape
    params = rules.shape_def(target).params
    values: dict[str, int] = dict(conversion.params)
    for name in conversion.keep:
        raw = getattr(shape, name)
        if raw == "weapon":
            raw = held_weapon(unit).range
        if not isinstance(raw, int):
            return shape
        spec = params[name]
        values[name] = max(spec.min, min(spec.max, raw))
    return ShapeSpec(type=target, **values)


def _grow(state: BattleState, shape: ShapeSpec, delta: int) -> ShapeSpec:
    """``shape`` 的第一個可增加的大小參數（``size``、``radius``）加 ``delta``（不超過最大值）。"""
    return grow_shape(state.ruleset, shape, delta)


def _helps_allies(state: BattleState, skill: SkillDef) -> bool:
    """技能有對友方生效的效果（治療、護盾、增益），``allow_self_target`` 才有意義。"""
    rules = state.ruleset
    return any(
        (e.affects or default_affects(rules.primitive_def(e.type))) == "allies"
        for e in skill.effects
    )


CHANGE_HANDLERS: Mapping[str, Callable[..., object]] = MappingProxyType(
    {
        "damage_permille": damage_permille,
        "hit_bonus": hit_bonus,
        "cooldown_delta": cooldown_delta,
        "push_distance_delta": displace_split,
        "ap_delta": ap_cost,
        "range_delta": range_delta,
        "add_element": damage_element,
        "add_tags": effective_tags,
        "on_hit_effects": on_hit_rules,
        "grant_pierce": grants_pierce,
        "area_delta": shaped_skill,
        "shape_to": shaped_skill,
        "allow_self_target": shaped_skill,
        "heal_permille": heal_permille,
        "summon_hp_permille": summon_hp_permille,
        "summon_attack_dice": summon_attack_dice,
        "summon_limit_delta": summon_limit_delta,
        "summon_duration_delta": summon_duration_delta,
        "summon_damage_permille": summon_damage_permille,
        "form_upkeep_permille": form_upkeep_permille,
        "form_entry_permille": form_entry_permille,
    }
)
"""每種修正規則改變（``content/modifier_changes.yaml``）由哪個查詢函式套用（Phase 3T-1 的宣告表；
:mod:`trpg.primitive_coverage` 載入時檢查每種都有）。新增一種改變要寫查詢函式並加進這裡。"""
