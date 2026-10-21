"""裝備詞條的結算（Phase 3G-G1，``docs/design/08-裝備.md`` 8.21.5.2～8.21.5.3）。

**計算位置**（G2、G3 接在這裡）：

1. 開戰時 :func:`build_gear` 把單位的裝備快照（:class:`~trpg.content.equipment.Loadout`）算成
   :class:`~trpg.engine.gear_state.GearState`：

   - **遞減**（:func:`diminish`）：同一詞條 id 的條目依數值大到小（同值依欄位固定順序）排序，數值類
     權重 ``rules/equipment.yaml`` 的 1000／500／250／0‰；非數值類同 id 只有第一條生效。
     :func:`diminished_total` 把一個數值部分依權重加總後無條件捨去（往 0 的方向）。
   - 第 1 類數值、第 8 類代價型的移動 → ``merged``（:func:`geared_template` 併進單位總屬性；
     移動與單一元素抗性在這裡套硬上限）。
   - 第 2 類條件數值、第 8 類代價型的其他數值 → ``bonuses``（戰鬥中查詢）。

2. 戰鬥中的查詢（**先遞減、再套上限**）：

   - :func:`gear_hit_bonus` → :func:`trpg.engine.modifiers.hit_bonus`（普攻、技能與預覽共用）；
   - :func:`gear_damage_permille` → :func:`trpg.engine.modifiers.damage_permille`（全身傷害加成
     上限 +50% 在這裡截斷）；
   - :func:`gear_defense_permille` → :func:`trpg.engine.rules.combat.defense_value_permille`；
   - :func:`gear_damage_taken_permille` → :func:`trpg.engine.rules.statuses.damage_taken_permille`；
   - :func:`gear_cooldown` → :func:`trpg.engine.skills.targeting.pay_skill_cost`（冷卻下限 1）；
   - :func:`gear_turn_start` → 回合開始（代價型失去 HP，不致死）。

3. 給 G2、G3 的上限函式（已寫好、尚未接上）：:func:`cap_damage_bonus`（技能強化的傷害加成也要算進
   同一個 +50%）、:func:`cap_crit_range`（暴擊範圍最低 18）、:func:`cap_ap_gain`（每回合 AP 回復
   +1）、:func:`cap_move_bonus`、:func:`cap_element_resist`、:func:`cap_cooldown`；觸發連鎖沿用
   ``core.max_trigger_depth``。

這個模組只讀取狀態（:func:`gear_turn_start` 除外）。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import TYPE_CHECKING

from trpg.content.battle import UnitTemplate
from trpg.content.equipment import (
    ConditionalAffix,
    CostAffix,
    EquipmentRules,
    Loadout,
    StatAffix,
)
from trpg.content.library import Ruleset
from trpg.content.skills import ConditionSpec
from trpg.content.slots import SLOT_INDEX
from trpg.engine.events import GearHpLost
from trpg.engine.gear_state import BonusStat, GearAffix, GearBonus, GearItem, GearState
from trpg.engine.ids import CONCEALED
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Attribute, Element

if TYPE_CHECKING:
    from trpg.engine.context import Ctx

__all__ = [
    "EMPTY_GEAR",
    "build_gear",
    "cap_ap_gain",
    "cap_cooldown",
    "cap_crit_range",
    "cap_damage_bonus",
    "cap_element_resist",
    "cap_move_bonus",
    "diminish",
    "diminished_total",
    "gear_cooldown",
    "gear_damage_permille",
    "gear_damage_taken_permille",
    "gear_defense_permille",
    "gear_hit_bonus",
    "gear_turn_start",
    "geared_template",
    "truncate_permille",
]

_PERMILLE = 1000
_MAX_ATTR = 999
EMPTY_GEAR = GearState()

_CONDITIONAL_STAT: dict[str, BonusStat] = {
    "hit": "hit",
    "damage": "damage_permille",
    "defense": "defense_permille",
}


def truncate_permille(total: int) -> int:
    """千分比加總 ÷ 1000，無條件捨去（往 0 的方向：正值向下、負值向上）。"""
    return total // _PERMILLE if total >= 0 else -(-total // _PERMILLE)


# ---------------------------------------------------------------------------
# 遞減
# ---------------------------------------------------------------------------


def diminish(loadout: Loadout, rules: EquipmentRules) -> tuple[GearAffix, ...]:
    """身上的每一條詞條與遞減權重（依詞條 id、再依遞減順序）。

    同 id 依數值由大到小排序（沒有數值的視為 0），同值依欄位固定順序（``main_hand`` → ``ring_2``）；
    數值類（:data:`~trpg.content.equipment.NUMERIC_CATEGORIES`）第 n 條的權重是
    ``rules.weight(n)``，非數值類只有第一條 1000‰、其餘 0。
    """
    groups: dict[str, list[GearAffix]] = {}
    for entry in loadout.items:
        for equipped in entry.affixes:
            groups.setdefault(equipped.affix.id, []).append(
                GearAffix(
                    slot=entry.slot,
                    item_id=entry.item.id,
                    affix=equipped.affix,
                    value=equipped.value,
                    weight_permille=0,
                    rank=0,
                )
            )
    result: list[GearAffix] = []
    for affix_id in sorted(groups):
        ordered = sorted(groups[affix_id], key=lambda g: (-(g.value or 0), SLOT_INDEX[g.slot]))
        for rank, gear in enumerate(ordered):
            first = _PERMILLE if rank == 0 else 0
            weight = rules.weight(rank) if gear.affix.numeric else first
            result.append(replace(gear, weight_permille=weight, rank=rank))
    return tuple(result)


def diminished_total(entries: Iterable[GearAffix], amount: Callable[[GearAffix], int]) -> int:
    """同一詞條 id 的條目中，一個數值部分（``amount`` 取出每條的原始數值）依遞減權重加總，
    再無條件捨去。G2 的技能強化與武器特性強化也用這個函式。"""
    return truncate_permille(sum(amount(e) * e.weight_permille for e in entries))


# ---------------------------------------------------------------------------
# 開戰時：GearState 與併進總屬性
# ---------------------------------------------------------------------------


def _stat_key(affix: StatAffix) -> str:
    if affix.stat == "attribute":
        assert affix.attribute is not None
        return f"attr:{affix.attribute.value}"
    if affix.stat == "element_resist":
        assert affix.element is not None
        return f"resist:{affix.element.value}"
    return affix.stat


def _value(entry: GearAffix) -> int:
    return entry.value or 0


def build_gear(loadout: Loadout, rules: EquipmentRules) -> GearState:
    """開戰時算好單位的裝備狀態（遞減後的加值；移動的上限在這裡截斷，其他上限在使用時套用）。"""
    if not loadout.items:
        return GearState(cooldown_min=rules.caps.cooldown_min)
    affixes = diminish(loadout, rules)
    by_id: dict[str, list[GearAffix]] = {}
    for entry in affixes:
        by_id.setdefault(entry.affix.id, []).append(entry)
    merged: dict[str, int] = {}
    bonuses: list[GearBonus] = []
    for affix_id, entries in by_id.items():
        affix = entries[0].affix
        if isinstance(affix, StatAffix):
            total = diminished_total(entries, _value)
            if affix.stat == "defense":
                bonuses.append(GearBonus(affix_id, "defense_permille", total))
            else:
                key = _stat_key(affix)
                merged[key] = merged.get(key, 0) + total
        elif isinstance(affix, ConditionalAffix):
            total = diminished_total(entries, _value)
            stat = _CONDITIONAL_STAT[affix.effect]
            bonuses.append(GearBonus(affix_id, stat, total, affix.condition, affix.negate))
        elif isinstance(affix, CostAffix):
            weights = sum(e.weight_permille for e in entries)  # 代價型的數值是固定的
            for part in affix.parts:
                total = truncate_permille(part.amount * weights)
                if part.stat == "move":
                    merged["move"] = merged.get("move", 0) + total
                elif total:
                    bonuses.append(GearBonus(affix_id, part.stat, total))
    uncapped = tuple(sorted((k, v) for k, v in merged.items() if v))
    if "move" in merged:
        merged["move"] = cap_move_bonus(rules, merged["move"])
    return GearState(
        items=tuple(GearItem(e.slot, e.item.id, e.item.name_zh) for e in loadout.items),
        affixes=affixes,
        bonuses=tuple(b for b in bonuses if b.amount),
        merged=tuple(sorted((k, v) for k, v in merged.items() if v)),
        uncapped=uncapped,
        cooldown_min=rules.caps.cooldown_min,
    )


def geared_template(template: UnitTemplate, gear: GearState, rules: Ruleset) -> UnitTemplate:
    """把裝備的 ``merged`` 加值併進範本（屬性、基礎最大 HP、個別元素抗性、速度）；沒有加值時回傳
    原範本。最大 HP 之後照常由 ``core.template_max_hp`` 加上體質（裝備的體質也算）。"""
    if not gear.merged:
        return template
    attributes = dict(template.attributes)
    element_mods = dict(template.element_mods)
    max_hp, speed = template.max_hp, template.speed
    for key, amount in gear.merged:
        kind, _, name = key.partition(":")
        if kind == "attr":
            attr = Attribute(name)
            attributes[attr] = max(1, min(_MAX_ATTR, attributes[attr] + amount))
        elif kind == "resist":
            element = Element(name)
            base = -element_mods.get(element, 0)
            element_mods[element] = -cap_element_resist(rules, base, base + amount)
        elif kind == "max_hp":
            max_hp = max(1, max_hp + amount)
        elif kind == "move":
            speed = max(0, speed + amount)
    return template.model_copy(
        update={
            "attributes": attributes,
            "element_mods": element_mods,
            "max_hp": max_hp,
            "speed": speed,
        }
    )


# ---------------------------------------------------------------------------
# 硬上限（8.21.5.3）
# ---------------------------------------------------------------------------


def cap_damage_bonus(rules: Ruleset, total_permille: int) -> int:
    """全身傷害加成（裝備來源合計，‰）上限 ``caps.damage_bonus_permille``；負值不截斷。"""
    return min(total_permille, rules.equipment.caps.damage_bonus_permille)


def cap_move_bonus(rules: EquipmentRules, total: int) -> int:
    """裝備的移動加成合計上限 ``caps.move_bonus``；負值不截斷。"""
    return min(total, rules.caps.move_bonus)


def cap_element_resist(rules: Ruleset, base: int, total: int) -> int:
    """單一元素抗性（‰）：裝備不能把抗性推過 ``caps.element_resist_permille``；範本本身已經更高的
    抗性維持原值（不因穿裝備而下降）。"""
    cap = rules.equipment.caps.element_resist_permille
    if total <= cap:
        return total
    return max(base, cap)


def cap_cooldown(cooldown_min: int, base: int, delta: int) -> int:
    """冷卻 ＝ ``base`` ＋ ``delta``，不低於 ``cooldown_min``；``base`` 本來就低於下限（例如沒有冷卻
    的 0）時不變。"""
    if base < cooldown_min:
        return base
    return max(cooldown_min, base + delta)


def cap_crit_range(rules: Ruleset, crit_range: int) -> int:
    """暴擊範圍（最低自然骰值）不低於 ``caps.crit_range_min``（G2：武器特性與技能強化的暴擊範圍
    加成接上這裡）。"""
    return max(crit_range, rules.equipment.caps.crit_range_min)


def cap_ap_gain(rules: Ruleset, gained_this_round: int, amount: int) -> int:
    """本輪已經由裝備等來源回復 ``gained_this_round`` AP 時，這次最多還能回復多少（每回合合計上限
    ``caps.ap_gain_per_round``；G3 的擊殺回 AP 接上這裡）。"""
    room = rules.equipment.caps.ap_gain_per_round - gained_this_round
    return max(0, min(amount, room))


# ---------------------------------------------------------------------------
# 戰鬥中的查詢
# ---------------------------------------------------------------------------


def _holds(state: BattleState, unit: UnitState, bonus: GearBonus, subject: Subject) -> bool:
    if bonus.condition is None:
        return True
    return condition_met(state, unit, bonus.condition, subject) != bonus.negate


def _self_holds(unit: UnitState, bonus: GearBonus) -> bool:
    """只看持有者自己的條件（:data:`~trpg.content.equipment.SELF_EVALUABLE_CONDITIONS`）。"""
    condition = bonus.condition
    if condition is None:
        return True
    return _self_condition(unit, condition) != bonus.negate


def _self_condition(unit: UnitState, condition: ConditionSpec) -> bool:
    kind = condition.type
    if kind == "moved_this_turn":
        return unit.moved_this_turn
    if kind == "self_hp_below":
        assert condition.permille is not None
        return unit.hp * _PERMILLE < condition.permille * unit.max_hp
    if kind == "self_concealed":
        return unit.has_status(CONCEALED)
    raise ValueError(f"裝備的防禦條件只能看持有者自己：{kind}")


def _sum(state: BattleState, unit: UnitState, stat: BonusStat, subject: Subject) -> int:
    return sum(
        b.amount for b in unit.gear.bonuses if b.stat == stat and _holds(state, unit, b, subject)
    )


def gear_hit_bonus(state: BattleState, unit: UnitState, subject: Subject) -> int:
    """``unit`` 的裝備對 ``subject`` 的命中加值（條件以 ``unit`` 為施放者判斷）。"""
    if not unit.gear.bonuses:
        return 0
    return _sum(state, unit, "hit", subject)


def gear_damage_permille(state: BattleState, unit: UnitState, subject: Subject) -> int:
    """``unit`` 的裝備對 ``subject`` 的傷害加成（‰，加在 1000 上）：條件數值與代價型的傷害加總，
    再套全身傷害加成上限。"""
    if not unit.gear.bonuses:
        return 0
    return cap_damage_bonus(state.ruleset, _sum(state, unit, "damage_permille", subject))


def _self_sum(unit: UnitState, stat: BonusStat) -> int:
    return sum(b.amount for b in unit.gear.bonuses if b.stat == stat and _self_holds(unit, b))


def gear_defense_permille(unit: UnitState) -> int:
    """持有者自己的防禦值加成（‰；可為負，例如 ``affix_cost_swift`` 的 −15%）。"""
    if not unit.gear.bonuses:
        return 0
    return _self_sum(unit, "defense_permille")


def gear_damage_taken_permille(unit: UnitState) -> int:
    """受到的骰值傷害倍率（‰，1000 ＝ 不變；例如 ``affix_cost_glass`` 的 1100），下限 0。"""
    if not unit.gear.bonuses:
        return _PERMILLE
    return max(0, _PERMILLE + _self_sum(unit, "damage_taken_permille"))


def gear_cooldown(unit: UnitState, base: int | None) -> int | None:
    """施放技能時設定的冷卻：``base`` ＋ 裝備的冷卻修正，不低於冷卻下限（:func:`cap_cooldown`）。"""
    if base is None or not unit.gear.bonuses:
        return base
    delta = _self_sum(unit, "cooldown_delta")
    if delta == 0:
        return base
    return cap_cooldown(unit.gear.cooldown_min, base, delta)


def gear_turn_start(ctx: Ctx, unit: UnitState) -> None:
    """回合開始時的裝備效果：代價型的失去 HP（依詞條 id 順序；不會致死，最低剩 1）。"""
    for bonus in unit.gear.bonuses:
        if bonus.stat != "turn_start_hp_loss" or bonus.amount <= 0:
            continue
        amount = min(bonus.amount, unit.hp - 1)
        if amount <= 0:
            continue
        before = unit.hp
        unit.hp -= amount
        ctx.emit(
            GearHpLost,
            unit_id=unit.id,
            affix_id=bonus.affix_id,
            amount=amount,
            hp_before=before,
            hp_after=unit.hp,
        )
