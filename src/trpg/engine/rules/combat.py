"""判定與傷害公式（``docs/phases/Phase1計畫.md`` 4.3、``docs/專案計畫.md`` 5.4、5.1.1）。

全部以整數運算：防禦值以千分比表示（``defense_value_permille``，例如防禦值 16 加上防禦姿態
+25% 為 ``16 × 1250 = 20000``），元素修正以百萬分比（ppm）表示。
"""

from __future__ import annotations

from dataclasses import dataclass

from trpg.content.library import Ruleset
from trpg.engine.events import AdvantageState
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element

__all__ = [
    "PPM",
    "AttackRoll",
    "advantage_sources",
    "advantage_state",
    "attack_problem",
    "attack_value",
    "combine_advantage",
    "defense_value_permille",
    "element_modifier_ppm",
    "hit_modifier",
    "is_height_limited",
    "is_hit",
    "melee_height_problem",
    "reach_problem",
    "roll_attack",
    "situational_modifier",
]

PPM = 1_000_000
PERMILLE = 1000
NATURAL_MISS = 1
NATURAL_HIT = 20
DEFENDING = "defending"
PRONE = "prone"


def attack_value(unit: UnitState) -> int:
    """攻擊值 ＝ 縮放屬性值 ＋ 武器攻擊加值。"""
    return unit.attributes[unit.weapon.scaling_attr] + unit.weapon.attack_bonus


def defense_value_permille(unit: UnitState, rules: Ruleset) -> int:
    """防禦值（×1000）＝ (敏捷 ＋ 護甲) × (1 ＋ 防禦姿態加成)。基礎防禦值最低視為 1。"""
    base = max(1, unit.attributes[Attribute.DEX] + unit.armor_bonus)
    bonus = rules.core.defend_defense_bonus_permille if unit.has_status(DEFENDING) else 0
    return base * (PERMILLE + bonus)


def hit_modifier(attacker: UnitState, target: UnitState, rules: Ruleset) -> int:
    """命中修正 ＝ clamp(round(slope × log2(攻擊值 ÷ 防禦值)), ±cap)，以整數門檻表計算。"""
    return rules.hit_table.modifier(
        attack_value(attacker) * PERMILLE, defense_value_permille(target, rules)
    )


def situational_modifier(state: BattleState, attacker: UnitState, target: UnitState) -> int:
    """情境修正：高打低 ``+height_hit_bonus``、低打高 ``−height_hit_bonus``。"""
    bonus = state.ruleset.core.height_hit_bonus
    ha = state.tile(*attacker.xy).height
    ht = state.tile(*target.xy).height
    if ha > ht:
        return bonus
    if ha < ht:
        return -bonus
    return 0


def advantage_sources(attacker: UnitState, target: UnitState) -> tuple[bool, bool]:
    """是否存在（優勢來源, 劣勢來源）。

    Phase 1A 的來源：目標倒地時，近戰攻擊有優勢、遠程攻擊有劣勢（1B 加入隱蔽、天氣等）。
    """
    advantage = False
    disadvantage = False
    if target.has_status(PRONE):
        if attacker.weapon.is_melee:
            advantage = True
        else:
            disadvantage = True
    return advantage, disadvantage


def advantage_state(attacker: UnitState, target: UnitState) -> AdvantageState:
    """優勢／劣勢：同時存在時互相抵消，不疊加。"""
    return combine_advantage(*advantage_sources(attacker, target))


def combine_advantage(advantage: bool, disadvantage: bool) -> AdvantageState:
    """多個來源只看「有沒有」：優勢與劣勢同時存在時抵消為一般擲骰。"""
    if advantage and not disadvantage:
        return "advantage"
    if disadvantage and not advantage:
        return "disadvantage"
    return "none"


def is_hit(natural: int, total: int, target_number: int) -> bool:
    """自然 1 必定失手、自然 20 必定命中，其餘看 ``total ≥ target_number``。"""
    if natural == NATURAL_MISS:
        return False
    if natural == NATURAL_HIT:
        return True
    return total >= target_number


@dataclass(frozen=True, slots=True)
class AttackRoll:
    rolls: tuple[int, ...]
    advantage: AdvantageState
    natural: int
    attack_value: int
    defense_value_permille: int
    hit_modifier: int
    proficiency: int
    situational: int
    total: int
    target_number: int
    hit: bool
    crit: bool


def roll_attack(state: BattleState, rng: Rng, attacker: UnitState, target: UnitState) -> AttackRoll:
    """擲命中骰（有優勢或劣勢時擲 2 顆 d20 取高／低）。暴擊需命中且自然骰 ≥ 武器暴擊範圍。"""
    rules = state.ruleset
    adv = advantage_state(attacker, target)
    if adv == "none":
        rolls: tuple[int, ...] = (rng.d20(),)
        natural = rolls[0]
    else:
        rolls = (rng.d20(), rng.d20())
        natural = max(rolls) if adv == "advantage" else min(rolls)
    modifier = hit_modifier(attacker, target, rules)
    situational = situational_modifier(state, attacker, target)
    proficiency = rules.core.proficiency
    total = natural + modifier + proficiency + situational
    hit = is_hit(natural, total, rules.core.hit_target)
    crit = hit and natural >= attacker.weapon.crit_range
    return AttackRoll(
        rolls=rolls,
        advantage=adv,
        natural=natural,
        attack_value=attack_value(attacker),
        defense_value_permille=defense_value_permille(target, rules),
        hit_modifier=modifier,
        proficiency=proficiency,
        situational=situational,
        total=total,
        target_number=rules.core.hit_target,
        hit=hit,
        crit=crit,
    )


def element_modifier_ppm(unit: UnitState, element: Element, rules: Ruleset) -> int:
    """元素修正（ppm）＝ (1000 − 分組抗性‰) × (1000 + 個別弱點／抗性‰)，下限 ``floor × 1000``。"""
    group = unit.resist.get(element.resist_group, 0)
    individual = unit.element_mods.get(element, 0)
    value = (PERMILLE - group) * (PERMILLE + individual)
    floor = rules.core.element_mod_floor_permille * PERMILLE
    return max(value, floor)


def is_height_limited(state: BattleState, unit: UnitState) -> bool:
    """近戰與長柄武器（射程 ≤ ``melee_height_limit_max_range``）受高度差限制。"""
    return unit.weapon.range <= state.ruleset.core.melee_height_limit_max_range


def melee_height_problem(state: BattleState, attacker: UnitState, target_xy: XY) -> str | None:
    """近戰攻擊的高度差超過 ``melee_height_limit`` 時的原因；沒有問題時回傳 ``None``。"""
    if not is_height_limited(state, attacker):
        return None
    limit = state.ruleset.core.melee_height_limit
    diff = abs(state.tile(*attacker.xy).height - state.tile(*target_xy).height)
    if diff > limit:
        return f"高度差過大，無法近戰：相差 {diff} 層（上限 {limit} 層）"
    return None


def reach_problem(state: BattleState, attacker: UnitState, target_xy: XY, what: str) -> str | None:
    """射程、近戰高度差與視線的檢查（目標可以是單位或物件所在的格子）。"""
    distance = manhattan(attacker.xy, target_xy)
    if distance > attacker.weapon.range:
        return f"目標超出射程：距離 {distance}，射程 {attacker.weapon.range}"
    height_problem = melee_height_problem(state, attacker, target_xy)
    if height_problem is not None:
        return height_problem
    if not has_line_of_sight(state, attacker.xy, target_xy):
        return f"視線被阻擋：{attacker.name_zh} 看不到 {what}"
    return None


def attack_problem(state: BattleState, attacker: UnitState, target: UnitState) -> str | None:
    """不能攻擊的原因（繁體中文）；可以攻擊時回傳 ``None``（不檢查 AP）。"""
    if target.downed:
        return f"目標已倒下：{target.name_zh}"
    if target.id == attacker.id:
        return "不能攻擊自己"
    if target.team is attacker.team:
        return f"不能攻擊友方單位：{target.name_zh}"
    return reach_problem(state, attacker, target.xy, target.name_zh)
