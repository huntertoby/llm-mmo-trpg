"""判定與傷害公式（``docs/phases/Phase1計畫.md`` 4.3、``docs/專案計畫.md`` 5.4、5.1.1）。

全部以整數運算：防禦值以千分比表示（``defense_value_permille``，例如防禦值 16 加上防禦姿態
+25% 為 ``16 × 1250 = 20000``），元素修正以百萬分比（ppm）表示。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.library import Ruleset
from trpg.engine.events import AdvantageState
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element, ObjectId, Surface

__all__ = [
    "PPM",
    "AttackRoll",
    "Cover",
    "advantage_sources",
    "advantage_state",
    "attack_problem",
    "attack_value",
    "combine_advantage",
    "concealed_max_distance",
    "concealment_problem",
    "cover_modifier",
    "cover_object_between",
    "defense_value_permille",
    "element_modifier_ppm",
    "half_cover",
    "hit_modifier",
    "is_concealed",
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
CONCEALED = "concealed"
HALF_COVER = "half_cover"

# 掩護物的搜尋順序：目標的上、右、下、左（與 geometry.neighbors4 一致）
_COVER_DIRECTIONS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


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


@dataclass(frozen=True, slots=True)
class Cover:
    """半掩護（``docs/phases/Phase1C計畫.md`` 3.2）：命中 ``−penalty``，來源為 ``object_id``。"""

    penalty: int
    object_id: ObjectId
    kind: str
    name_zh: str
    pos: XY


def cover_object_between(
    state: BattleState, attacker_xy: XY, target_xy: XY
) -> tuple[ObjectId, XY] | None:
    """幾何部分的半掩護判定：從 ``attacker_xy`` 看向 ``target_xy`` 時提供掩護的物件與其格子。

    不看武器（呼叫端負責「近戰無視」）；條件見 :func:`half_cover`。
    """
    tx, ty = target_xy
    wx, wy = attacker_xy[0] - tx, attacker_xy[1] - ty
    attacker_height = state.tile(*attacker_xy).height
    for dx, dy in _COVER_DIRECTIONS:
        if dx * wx + dy * wy <= 0:
            continue
        cx, cy = tx + dx, ty + dy
        if not state.in_bounds(cx, cy):
            continue
        oid = state.tile(cx, cy).object_id
        if oid is None:
            continue
        obj = state.objects[oid]
        if HALF_COVER not in state.ruleset.object_def(obj.kind).tags:
            continue
        if attacker_height > state.tile(cx, cy).height + 1:
            continue
        return obj.id, (cx, cy)
    return None


def half_cover(state: BattleState, attacker: UnitState, target: UnitState) -> Cover | None:
    """``attacker`` 攻擊 ``target`` 時，目標是否受到半掩護。

    遠程攻擊（武器射程 > ``melee_height_limit_max_range``）時，目標受到半掩護若且唯若存在格子 C：

    1. C 與目標四方向相鄰；
    2. C 上有未摧毀、帶 ``half_cover`` 標籤的物件；
    3. C 相對於目標的方向向量與「目標指向攻擊者」的向量內積 > 0（C 在目標朝向攻擊者的一側）；
    4. 攻擊者的高度不高於「C 的地形高度 ＋ 1」（物件視為 1 層高；攻擊者高出至少 1 層時無視）。

    近戰（含長柄）無視半掩護；單位不提供掩護。多個掩護物同時符合時只計一次，來源取上、右、下、
    左順序中的第一個（確定性）。懲罰為 ``half_cover_hit_penalty``（為 0 時視為沒有掩護）。
    """
    if is_height_limited(state, attacker):
        return None
    penalty = state.ruleset.core.half_cover_hit_penalty
    if penalty <= 0:
        return None
    found = cover_object_between(state, attacker.xy, target.xy)
    if found is None:
        return None
    oid, pos = found
    obj = state.objects[oid]
    return Cover(
        penalty=penalty,
        object_id=oid,
        kind=obj.kind,
        name_zh=state.ruleset.object_def(obj.kind).name_zh,
        pos=pos,
    )


def cover_modifier(state: BattleState, attacker: UnitState, target: UnitState) -> int:
    """半掩護的命中修正（沒有掩護時為 0，有掩護時為負值）。"""
    cover = half_cover(state, attacker, target)
    return 0 if cover is None else -cover.penalty


def is_concealed(state: BattleState, unit: UnitState) -> bool:
    """隱蔽：帶 ``concealed`` 狀態，或站在 ``conceal`` 表面（黑暗）／``conceal`` 物件（草叢）上。"""
    if unit.has_status(CONCEALED):
        return True
    tile = state.tile(*unit.xy)
    if tile.surface is not Surface.NONE and state.ruleset.surface_def(tile.surface).conceal:
        return True
    return tile.object_id is not None and state.object_has_tag(*unit.xy, "conceal")


def concealed_max_distance(state: BattleState) -> int:
    """隱蔽的目標可被攻擊的最遠距離（夜晚由天氣覆寫）。"""
    weather = state.weather
    if weather is not None and weather.concealed_ranged_max_distance is not None:
        return weather.concealed_ranged_max_distance
    return state.ruleset.core.concealed_ranged_max_distance


def advantage_sources(
    state: BattleState, attacker: UnitState, target: UnitState
) -> tuple[bool, bool]:
    """是否存在（優勢來源, 劣勢來源）。

    - 目標倒地：近戰攻擊有優勢、遠程攻擊有劣勢。
    - 目標隱蔽：劣勢。
    - 天氣（濃霧）：遠程攻擊超過 ``ranged_disadvantage_beyond`` 格有劣勢。
    """
    advantage = False
    disadvantage = False
    if target.has_status(PRONE):
        if attacker.weapon.is_melee:
            advantage = True
        else:
            disadvantage = True
    if is_concealed(state, target):
        disadvantage = True
    weather = state.weather
    if (
        weather is not None
        and weather.ranged_disadvantage_beyond is not None
        and not attacker.weapon.is_melee
        and manhattan(attacker.xy, target.xy) > weather.ranged_disadvantage_beyond
    ):
        disadvantage = True
    return advantage, disadvantage


def advantage_state(state: BattleState, attacker: UnitState, target: UnitState) -> AdvantageState:
    """優勢／劣勢：同時存在時互相抵消，不疊加。"""
    return combine_advantage(*advantage_sources(state, attacker, target))


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
    cover: int
    cover_object_id: ObjectId | None
    total: int
    target_number: int
    hit: bool
    crit: bool


type ForcedOutcome = Literal["miss", "hit", "crit"]
"""預覽用：強制判定結果（``hit`` 為命中但不暴擊）。"""


def roll_attack(
    state: BattleState,
    rng: Rng,
    attacker: UnitState,
    target: UnitState,
    forced: ForcedOutcome | None = None,
) -> AttackRoll:
    """擲命中骰（有優勢或劣勢時擲 2 顆 d20 取高／低）。暴擊需命中且自然骰 ≥ 武器暴擊範圍。

    ``total = 自然骰 ＋ 命中修正 ＋ 熟練 ＋ 情境（高度） ＋ 掩護（半掩護為負值）``。

    ``forced`` 只供預覽使用：不擲骰，直接採用指定結果。
    """
    rules = state.ruleset
    adv = advantage_state(state, attacker, target)
    modifier = hit_modifier(attacker, target, rules)
    situational = situational_modifier(state, attacker, target)
    cover = half_cover(state, attacker, target)
    cover_mod = 0 if cover is None else -cover.penalty
    proficiency = rules.core.proficiency
    if forced is not None:
        bonus = modifier + proficiency + situational + cover_mod
        natural = _forced_natural(forced, bonus, attacker, rules)
        rolls: tuple[int, ...] = (natural,)
    elif adv == "none":
        rolls = (rng.d20(),)
        natural = rolls[0]
    else:
        rolls = (rng.d20(), rng.d20())
        natural = max(rolls) if adv == "advantage" else min(rolls)
    total = natural + modifier + proficiency + situational + cover_mod
    hit = is_hit(natural, total, rules.core.hit_target)
    crit = hit and natural >= attacker.weapon.crit_range
    if forced is not None:
        hit, crit = forced != "miss", forced == "crit"
    return AttackRoll(
        rolls=rolls,
        advantage=adv,
        natural=natural,
        attack_value=attack_value(attacker),
        defense_value_permille=defense_value_permille(target, rules),
        hit_modifier=modifier,
        proficiency=proficiency,
        situational=situational,
        cover=cover_mod,
        cover_object_id=None if cover is None else cover.object_id,
        total=total,
        target_number=rules.core.hit_target,
        hit=hit,
        crit=crit,
    )


def _forced_natural(forced: ForcedOutcome, bonus: int, attacker: UnitState, rules: Ruleset) -> int:
    """與強制結果相符的自然骰（只用於事件內容；結果本身由 ``forced`` 決定）。"""
    if forced == "miss":
        return NATURAL_MISS
    if forced == "crit":
        return NATURAL_HIT
    for natural in range(2, attacker.weapon.crit_range):
        if is_hit(natural, natural + bonus, rules.core.hit_target):
            return natural
    return NATURAL_HIT


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
    if not target.alive:
        return f"目標已不在戰場上：{target.name_zh}"
    if target.id == attacker.id:
        return "不能攻擊自己"
    if target.team is attacker.team:
        return f"不能攻擊友方單位：{target.name_zh}"
    problem = reach_problem(state, attacker, target.xy, target.name_zh)
    if problem is not None:
        return problem
    return concealment_problem(state, attacker, target)


def concealment_problem(state: BattleState, attacker: UnitState, target: UnitState) -> str | None:
    """隱蔽的目標超過一定距離無法選為目標。"""
    if not is_concealed(state, target):
        return None
    limit = concealed_max_distance(state)
    distance = manhattan(attacker.xy, target.xy)
    if distance > limit:
        return f"目標隱蔽中：超過 {limit} 格無法選為目標（距離 {distance}）"
    return None
