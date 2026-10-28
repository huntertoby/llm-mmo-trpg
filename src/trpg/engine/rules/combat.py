"""判定與傷害公式（``docs/phases/Phase1計畫.md`` 4.3、``docs/專案計畫.md`` 5.4、5.1.1）。

全部以整數運算：防禦值以千分比表示（``defense_value_permille``，例如防禦值 16 加上防禦姿態
+25% 為 ``16 × 1250 = 20000``），元素修正以百萬分比（ppm）表示。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.battle import WeaponDef
from trpg.content.library import Ruleset
from trpg.engine.events import AdvantageState
from trpg.engine.gear import gear_defense_permille
from trpg.engine.ids import CONCEALED, DEFENDING, PRONE
from trpg.engine.modifiers import ATTACK, range_delta
from trpg.engine.rules.facing import is_behind
from trpg.engine.rules.forms import form_backstab_crit, form_defense_permille
from trpg.engine.rules.geometry import XY, has_line_of_sight, manhattan
from trpg.engine.rules.perks import attribute_perk
from trpg.engine.rules.statuses import (
    attack_range_cap,
    defense_break_permille,
    effective_attribute,
    forced_target_sources,
    grants_advantage_against,
    has_attack_disadvantage_status,
    prevents_concealment,
    status_attack_bonus,
)
from trpg.engine.rules.weapons import crit_range_cut, weapon_hit_bonus
from trpg.engine.state import BattleState, UnitState
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Element, ObjectId, Surface

__all__ = [
    "PPM",
    "AttackProfile",
    "AttackRoll",
    "Cover",
    "PositionalBonus",
    "advantage_sources",
    "advantage_state",
    "attack_problem",
    "attack_reach",
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
    "positional_bonus",
    "reach_problem",
    "roll_attack",
    "situational_modifier",
    "weapon_profile",
]

PPM = 1_000_000
PERMILLE = 1000
NATURAL_MISS = 1
NATURAL_HIT = 20
HALF_COVER = "half_cover"

# 掩護物的搜尋順序：目標的上、右、下、左（與 geometry.neighbors4 一致）
_COVER_DIRECTIONS: tuple[XY, ...] = ((0, -1), (1, 0), (0, 1), (-1, 0))


def attack_value(unit: UnitState, rules: Ruleset, weapon: WeaponDef | None = None) -> int:
    """攻擊值 ＝ 縮放屬性值（有效屬性） ＋ 武器攻擊加值 ＋ 狀態的攻擊加值（戰意，3-33e1）。
    ``weapon`` 省略時是普攻的武器（``unit.weapon``；形態中為天生武器，Phase 3J-1a）；武器技傳入
    手上的武器。"""
    if weapon is None:
        weapon = unit.weapon
    value = weapon.scaling_value(lambda attr: effective_attribute(rules, unit, attr))
    return value + weapon.attack_bonus + status_attack_bonus(rules, unit)


@dataclass(frozen=True, slots=True)
class AttackProfile:
    """一次命中判定使用的攻擊者參數（普攻取自武器；技能取自技能，Phase 2A）。

    - ``attack_value``：攻擊值（命中修正的分子）。
    - ``melee``：近戰（射程 1）——倒地目標有優勢／遠程有劣勢、濃霧的遠程劣勢。
    - ``height_limited``：近戰與長柄（射程 ≤ ``melee_height_limit_max_range``）——無視半掩護。
    - ``crit_range``：暴擊的最低自然骰值。
    - ``pierce``：穿透（Phase 3C-5b）——無視半掩護（普攻：武器的 ``ignore_cover``）。
    - ``defense_cut_permille``：目標防禦值被穿透的千分比（普攻：武器的 ``armor_pierce_permille``）。
    - ``weapon_attack``：武器自己的攻擊（普攻；Phase 3-24c 起也包含火器的武器技）——站定與距離修正
      （Phase 3-24a2）只套用在這類攻擊。
    - ``ignore_cover``：無視半掩護，但不產生穿透射線（火器武器技的 ``ignore_cover``，3-24c）。
    - ``backstab_crit``：背刺時暴擊範圍再多擴大這麼多（形態天生武器的特性，3J-1b；只有普攻有）。
    """

    attack_value: int
    melee: bool
    height_limited: bool
    crit_range: int
    pierce: bool = False
    defense_cut_permille: int = 0
    weapon_attack: bool = False
    ignore_cover: bool = False
    backstab_crit: int = 0


def weapon_profile(state: BattleState, attacker: UnitState) -> AttackProfile:
    """普攻的參數：取自 ``attacker`` 的武器。"""
    weapon = attacker.weapon
    return AttackProfile(
        attack_value=attack_value(attacker, state.ruleset),
        melee=weapon.is_melee,
        height_limited=weapon.range <= state.ruleset.core.melee_height_limit_max_range,
        crit_range=max(2, weapon.crit_range - crit_range_cut(attacker)),  # 站定狙擊（3-24a2）
        pierce=weapon.ignore_cover,
        defense_cut_permille=weapon.armor_pierce_permille,
        weapon_attack=True,
        backstab_crit=form_backstab_crit(state.ruleset, attacker),
    )


def defense_value_permille(unit: UnitState, rules: Ruleset, cut: int = 0) -> int:
    """防禦值（×1000）＝ (敏捷 ＋ 護甲) × (1 ＋ 防禦姿態加成 − 破甲 − 穿透 ＋ 裝備)。

    基礎防禦值最低視為 1，防禦值至少 1（Phase 3-24a1：破甲 ``defense_break`` 狀態與防禦姿態的
    加成直接相加；Phase 3-24a2：``cut`` 為攻擊者武器的 ``armor_pierce_permille``，同樣直接相減；
    Phase 3G-G1：裝備的防禦加成也直接相加，見 :func:`~trpg.engine.gear.gear_defense_permille`）。
    """
    base = max(1, effective_attribute(rules, unit, Attribute.DEX) + unit.armor_bonus)
    bonus = rules.core.defend_defense_bonus_permille if unit.has_status(DEFENDING) else 0
    bonus -= defense_break_permille(rules, unit) + cut
    bonus += gear_defense_permille(unit)
    bonus += form_defense_permille(rules, unit)  # 形態的防禦加減（Phase 3J-1a，直接相加）
    return max(1, base * (PERMILLE + bonus))


def hit_modifier(
    attacker: UnitState,
    target: UnitState,
    rules: Ruleset,
    profile: AttackProfile | None = None,
) -> int:
    """命中修正 ＝ clamp(round(slope × log2(攻擊值 ÷ 防禦值)), ±cap)，以整數門檻表計算。"""
    value = attack_value(attacker, rules) if profile is None else profile.attack_value
    cut = attacker.weapon.armor_pierce_permille if profile is None else profile.defense_cut_permille
    return rules.hit_table.modifier(value * PERMILLE, defense_value_permille(target, rules, cut))


def situational_modifier(state: BattleState, attacker: UnitState, target: UnitState) -> int:
    """情境修正：高打低 ``+height_hit_bonus``、低打高 ``−height_hit_bonus``（武器的
    ``ignore_height``——弩——沒有這項修正，Phase 3-24a2）。"""
    if attacker.weapon.ignore_height:
        return 0
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
    object_id: ObjectId | None
    """提供掩護的物件；塔盾（Phase 3I-2）的自身掩護沒有物件，為 ``None``。"""
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
    target_height = state.tile(*target_xy).height
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
        cover_height = state.tile(cx, cy).height
        if attacker_height > cover_height + 1:
            continue
        if cover_height + 1 < target_height:
            continue  # 目標站得比掩護物高（站在高台上）：旁邊地面的掩護物擋不到它
        return obj.id, (cx, cy)
    return None


def half_cover(
    state: BattleState,
    attacker: UnitState,
    target: UnitState,
    profile: AttackProfile | None = None,
) -> Cover | None:
    """``attacker`` 攻擊 ``target`` 時，目標是否受到半掩護。

    遠程攻擊（武器射程 > ``melee_height_limit_max_range``）時，目標受到半掩護若且唯若存在格子 C：

    1. C 與目標四方向相鄰；
    2. C 上有未摧毀、帶 ``half_cover`` 標籤的物件；
    3. C 相對於目標的方向向量與「目標指向攻擊者」的向量內積 > 0（C 在目標朝向攻擊者的一側）；
    4. 攻擊者的高度不高於「C 的地形高度 ＋ 1」（物件視為 1 層高；攻擊者高出至少 1 層時無視）；
    5. 目標所在格的高度不高於「C 的地形高度 ＋ 1」（Phase 2A 決定 #1：站在高台上的目標不再被
       旁邊地面的掩護物掩護）。

    近戰（含長柄）與穿透技能（``profile.pierce``）無視半掩護；單位不提供掩護。多個掩護物同時符合時只計一次，來源取上、右、下、
    左順序中的第一個（確定性）。懲罰為 ``half_cover_hit_penalty``（為 0 時視為沒有掩護）。
    """
    limited = is_height_limited(state, attacker) if profile is None else profile.height_limited
    if limited or (
        (profile.pierce or profile.ignore_cover)
        if profile is not None
        else attacker.weapon.ignore_cover
    ):
        return None
    penalty = state.ruleset.core.half_cover_hit_penalty
    if penalty <= 0:
        return None
    found = cover_object_between(state, attacker.xy, target.xy)
    if found is None:
        return _shield_cover(state, attacker, target, penalty)
    oid, pos = found
    obj = state.objects[oid]
    return Cover(
        penalty=penalty,
        object_id=oid,
        kind=obj.kind,
        name_zh=state.ruleset.object_def(obj.kind).name_zh,
        pos=pos,
    )


def _shield_cover(
    state: BattleState, attacker: UnitState, target: UnitState, penalty: int
) -> Cover | None:
    """塔盾的自身半掩護（Phase 3I-2，08 8.11）：目標副手有 ``ranged_cover`` 時，遠程攻擊（呼叫端已
    排除近戰與穿透）命中同半掩護；攻擊者站得比目標高 1 層以上時無視。場上的掩護物已經成立時不會
    走到這裡（兩者不疊加）。"""
    offhand = target.gear.offhand
    if offhand is None or not offhand.ranged_cover:
        return None
    if state.tile(*attacker.xy).height > state.tile(*target.xy).height:
        return None
    return Cover(
        penalty=penalty, object_id=None, kind=offhand.id, name_zh=offhand.name_zh, pos=target.xy
    )


def cover_modifier(state: BattleState, attacker: UnitState, target: UnitState) -> int:
    """半掩護的命中修正（沒有掩護時為 0，有掩護時為負值）。"""
    cover = half_cover(state, attacker, target)
    return 0 if cover is None else -cover.penalty


def is_concealed(state: BattleState, unit: UnitState) -> bool:
    """隱蔽：帶 ``concealed`` 狀態，或站在 ``conceal`` 表面（黑暗）／``conceal`` 物件（草叢）上；
    被揭露（``prevents_concealment``，Phase 3D-8a）的單位一律不算。"""
    if prevents_concealment(state.ruleset, unit):
        return False
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
    state: BattleState,
    attacker: UnitState,
    target: UnitState,
    profile: AttackProfile | None = None,
) -> tuple[bool, bool]:
    """是否存在（優勢來源, 劣勢來源）。

    - 目標倒地：近戰攻擊有優勢、遠程攻擊有劣勢。
    - 目標隱蔽：劣勢。
    - 天氣（濃霧）：遠程攻擊超過 ``ranged_disadvantage_beyond`` 格有劣勢。
    - 攻擊者被嘲諷（``forces_target``）：攻擊嘲諷者以外的單位有劣勢（Phase 2D-1）。
    - 攻擊者恐懼或致盲：任何攻擊都有劣勢；目標被標記：優勢（Phase 2D-2）。
    """
    melee = attacker.weapon.is_melee if profile is None else profile.melee
    advantage = False
    disadvantage = False
    if target.has_status(PRONE):
        if melee:
            advantage = True
        else:
            disadvantage = True
    if is_concealed(state, target):
        disadvantage = True
    taunters = forced_target_sources(state.ruleset, attacker)
    if taunters and target.id not in taunters:
        disadvantage = True
    if has_attack_disadvantage_status(state.ruleset, attacker):  # 恐懼、致盲：任何攻擊都有劣勢
        disadvantage = True
    if grants_advantage_against(state.ruleset, target):  # 被標記
        advantage = True
    weather = state.weather
    if (
        weather is not None
        and weather.ranged_disadvantage_beyond is not None
        and not melee
        and manhattan(attacker.xy, target.xy) > weather.ranged_disadvantage_beyond
    ):
        disadvantage = True
    return advantage, disadvantage


def advantage_state(
    state: BattleState,
    attacker: UnitState,
    target: UnitState,
    profile: AttackProfile | None = None,
) -> AdvantageState:
    """優勢／劣勢：同時存在時互相抵消，不疊加。"""
    return combine_advantage(*advantage_sources(state, attacker, target, profile))


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
    modifier_bonus: int = 0
    """修正規則的命中加值（Phase 3C-2 ``hit_bonus``；已含在 ``total``）。"""
    backstab: int = 0
    """背刺的命中加值（Phase 3D-8d；0 為不是背刺；已含在 ``total``，暴擊範圍另外擴大）。"""
    ambush: int = 0
    """潛行偷襲的命中加值（Phase 3D-8d；0 為沒有隱蔽；已含在 ``total``）。"""


@dataclass(frozen=True, slots=True)
class PositionalBonus:
    """背刺與潛行偷襲（Phase 3D-8d）：命中加值與擴大後的暴擊範圍。"""

    backstab: int
    ambush: int
    crit_range: int

    @property
    def hit(self) -> int:
        return self.backstab + self.ambush


def positional_bonus(
    state: BattleState, attacker: UnitState, target: UnitState, profile: AttackProfile
) -> PositionalBonus:
    """一次命中判定的背刺與潛行偷襲加成。

    - 背刺：近戰攻擊（``profile.melee``）且攻擊者站在目標的背後格（目標朝向的反方向相鄰格）——
      命中 ``+backstab_hit_bonus``、暴擊範圍擴大 ``backstab_crit_range_bonus``。Boss 照常適用。
    - 潛行偷襲：攻擊者帶 ``concealed`` 狀態——命中 ``+ambush_hit_bonus``（攻擊結算完後由呼叫端
      移除隱蔽）。站在黑暗或草叢裡的隱蔽不算（只看狀態）。
    """
    core = state.ruleset.core
    behind = profile.melee and is_behind(attacker.xy, target)
    backstab = core.backstab_hit_bonus if behind else 0
    ambush = core.ambush_hit_bonus if attacker.has_status(CONCEALED) else 0
    crit_range = profile.crit_range - (
        core.backstab_crit_range_bonus + profile.backstab_crit if behind else 0
    )
    return PositionalBonus(backstab, ambush, max(crit_range, 2))


type ForcedOutcome = Literal["miss", "hit", "crit"]
"""預覽用：強制判定結果（``hit`` 為命中但不暴擊）。"""


def roll_attack(  # noqa: PLR0917
    state: BattleState,
    rng: Rng,
    attacker: UnitState,
    target: UnitState,
    forced: ForcedOutcome | None = None,
    profile: AttackProfile | None = None,
    *,
    bonus: int = 0,
) -> AttackRoll:
    """擲命中骰（有優勢或劣勢時擲 2 顆 d20 取高／低）。暴擊需命中且自然骰 ≥ 武器暴擊範圍。

    ``total = 自然骰 ＋ 命中修正 ＋ 熟練 ＋ 情境（高度） ＋ 掩護（半掩護為負值） ＋ bonus ＋ 背刺 ＋
    潛行偷襲``（:func:`positional_bonus`，Phase 3D-8d；背刺另外擴大暴擊範圍）。

    ``forced`` 只供預覽使用：不擲骰，直接採用指定結果。``profile`` 為技能的攻擊參數
    （省略時取自 ``attacker`` 的武器）。``bonus`` 為修正規則的命中加值（3C-2，呼叫端計算）。
    """
    rules = state.ruleset
    if profile is None:
        profile = weapon_profile(state, attacker)
    adv = advantage_state(state, attacker, target, profile)
    modifier = hit_modifier(attacker, target, rules, profile)
    situational = situational_modifier(state, attacker, target)
    cover = half_cover(state, attacker, target, profile)
    cover_mod = 0 if cover is None else -cover.penalty
    proficiency = rules.core.proficiency
    positional = positional_bonus(state, attacker, target, profile)
    if profile.weapon_attack:  # 站定與距離修正（Phase 3-24a2）
        bonus += weapon_hit_bonus(attacker, manhattan(attacker.xy, target.xy))
    bonus += positional.hit + attacker.next_attack_hit  # 形態的進入獎勵（3J-1a；呼叫端用掉）
    crit_range = max(2, positional.crit_range - attacker.next_attack_crit)
    if forced is not None:
        natural = _forced_natural(
            forced,
            modifier + proficiency + situational + cover_mod + bonus,
            crit_range,
            rules,
        )
        rolls: tuple[int, ...] = (natural,)
    elif adv == "none":
        rolls = (rng.d20(),)
        natural = rolls[0]
    else:
        rolls = (rng.d20(), rng.d20())
        natural = max(rolls) if adv == "advantage" else min(rolls)
    total = natural + modifier + proficiency + situational + cover_mod + bonus
    hit = is_hit(natural, total, rules.core.hit_target)
    crit = hit and natural >= crit_range
    if forced is not None:
        hit, crit = forced != "miss", forced == "crit"
    return AttackRoll(
        rolls=rolls,
        advantage=adv,
        natural=natural,
        attack_value=profile.attack_value,
        defense_value_permille=defense_value_permille(target, rules, profile.defense_cut_permille),
        hit_modifier=modifier,
        proficiency=proficiency,
        situational=situational,
        cover=cover_mod,
        cover_object_id=None if cover is None else cover.object_id,
        total=total,
        target_number=rules.core.hit_target,
        hit=hit,
        crit=crit,
        modifier_bonus=bonus - positional.hit - attacker.next_attack_hit,
        backstab=positional.backstab,
        ambush=positional.ambush,
    )


def _forced_natural(forced: ForcedOutcome, bonus: int, crit_range: int, rules: Ruleset) -> int:
    """與強制結果相符的自然骰（只用於事件內容；結果本身由 ``forced`` 決定）。"""
    if forced == "miss":
        return NATURAL_MISS
    if forced == "crit":
        return NATURAL_HIT
    for natural in range(2, crit_range):
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


def attack_reach(state: BattleState, attacker: UnitState, target_xy: XY | None = None) -> int:
    """普攻的射程：武器射程加上修正規則的 ``range_delta``（至少 1；Phase 3C-2）。近戰性質
    （高度差限制、無視半掩護、倒地目標的優勢）仍由武器本身的射程決定。給了 ``target_xy`` 且
    攻擊者站得比那一格高時，再加武器的 ``high_range``（Phase 3-32a，弓的高處射程強化）。"""
    reach = attacker.weapon.range + range_delta(state, attacker, ATTACK)
    if (
        target_xy is not None
        and attacker.weapon.high_range
        and state.tile(*attacker.xy).height > state.tile(*target_xy).height
    ):
        reach += attacker.weapon.high_range
    return max(1, reach)


def reach_problem(state: BattleState, attacker: UnitState, target_xy: XY, what: str) -> str | None:
    """射程、近戰高度差與視線的檢查（目標可以是單位或物件所在的格子）；有彈匣的武器空膛時
    不能開火（Phase 3-24a2）。"""
    if attacker.weapon.magazine > 0 and attacker.ammo <= 0:
        return f"空膛：{attacker.weapon.name_zh}需要先裝填"
    distance = manhattan(attacker.xy, target_xy)
    reach = attack_reach(state, attacker, target_xy)
    if distance > reach:
        return f"目標超出射程：距離 {distance}，射程 {reach}"
    height_problem = melee_height_problem(state, attacker, target_xy)
    if height_problem is not None:
        return height_problem
    if not has_line_of_sight(state, attacker.xy, target_xy, lob=attacker.weapon.lob):
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
    cap = attack_range_cap(state.ruleset, attacker)
    if cap is not None and manhattan(attacker.xy, target.xy) > cap:
        return f"致盲中：只能攻擊 {cap} 格內的目標（距離 {manhattan(attacker.xy, target.xy)}）"
    return concealment_problem(state, attacker, target)


def concealment_problem(state: BattleState, attacker: UnitState, target: UnitState) -> str | None:
    """隱蔽的目標超過一定距離無法選為目標。"""
    if not is_concealed(state, target) or grants_advantage_against(state.ruleset, target):
        return None  # 被標記者不受隱蔽的選取限制
    limit = concealed_max_distance(state) + attribute_perk(
        state.ruleset, attacker, "reveal_range"
    )  # 感知的常駐數值（Phase 3H-1）
    distance = manhattan(attacker.xy, target.xy)
    if distance > limit:
        return f"目標隱蔽中：超過 {limit} 格無法選為目標（距離 {distance}）"
    return None
