"""裝備效果的名額（E6-b1，``docs/design/08-裝備.md`` 8.27、8.30 第 4、5、10 點，#180）。

建立單位時（:func:`trpg.engine.lifecycle.make_unit`），在 :func:`~trpg.engine.gear.core.build_gear`
的遞減之後依序套用：

1. **改寫規則同時 1 個**（``caps.rule_affixes``）：生效中的第 11 類詞條依詞條 id 分組，超過名額的
   標灰（``limited_by="rule"``）。
2. **招牌同時 3 個**（``caps.signature_active``）：生效中、標了 ``signature`` 的詞條，超過名額的標灰
   （``limited_by="signature"``）。怎麼算名額：

   - 裝備給的技能（第 9 類：新動作、新反應、行為改寫）照 8.28 疊加，每份各佔 1 個（遞減時每份都
     生效）；地形規則、改寫規則、第 10 類反應同 id 只生效 1 條（遞減時第 2 條起權重 0），只佔 1 個。
   - 整條完全沒效果的不佔名額（8.30 第 10 點）：遞減、改寫規則名額標灰的；和種族或其他裝備完全
     重複的地形規則（8.29 E2 第 1 點，所以要知道種族）；普攻變形拿著不能套用的武器、或過不了預算
     閘門（8.29 E5 第 3 點）。只對部分技能沒效果的照佔。
   - 不佔名額的判斷會隨其他詞條標灰而變（例：蓋過另一條地形規則的那條被標灰，被蓋過的那條就有效果
     了），所以一次只標灰 1 條、重算到不超過名額為止。

誰留下：玩家勾選的（``Loadout.chosen``）優先，其次照欄位固定順序（主手 → 戒指 2），再依詞條 id
（:func:`limit_priority`）。玩家以外的單位沒有勾選，就是照欄位順序。

標灰一律只把權重設 0：授予的技能、反應、規則改變、地形規則都只看生效中的詞條，自然不生效。

這個模組是確定性的純函式（需要順序時一律排序）。
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import replace

from trpg.content.battle import WeaponDef
from trpg.content.equipment import ActionAffix, Loadout, chosen_key
from trpg.content.library import Ruleset
from trpg.content.slots import SLOT_INDEX
from trpg.engine.attack_shapes import suits_line
from trpg.engine.gear.state import GearAffix, GearState, LimitReason
from trpg.engine.reshape_gate import ATTACK_TARGET, BLOCKED, gate_permille
from trpg.engine.rules.unit_rules import classify_sources, gear_rule_sources, gear_strength

__all__ = ["limit_gear", "limit_priority", "whole_no_effect"]

type Priority = tuple[int, int, str, int]


def limit_priority(entry: GearAffix, chosen: Collection[str]) -> Priority:
    """名額的先後（越小越先）：勾選的優先，其次欄位固定順序，再依詞條 id、同 id 的順序。"""
    picked = 0 if chosen_key(entry.slot, entry.affix.id) in chosen else 1
    return (picked, SLOT_INDEX[entry.slot], entry.affix.id, entry.rank)


def _grey(gear: GearState, losers: Collection[int], reason: LimitReason) -> GearState:
    """把 ``gear.affixes`` 第 ``losers`` 條標灰。"""
    if not losers:
        return gear
    affixes = tuple(
        replace(a, weight_permille=0, limited_by=reason) if i in losers else a
        for i, a in enumerate(gear.affixes)
    )
    return replace(gear, affixes=affixes)


def _limit_rules(gear: GearState, chosen: Collection[str], cap: int) -> GearState:
    """改寫規則：生效中的不同詞條 id 最多 ``cap`` 個，其他標灰（``rule``）。"""
    active = [(i, a) for i, a in enumerate(gear.affixes) if a.active and a.affix.category == "rule"]
    best: dict[str, Priority] = {}
    for _, entry in active:
        key = limit_priority(entry, chosen)
        best[entry.affix.id] = min(best.get(entry.affix.id, key), key)
    kept = set(sorted(best, key=lambda affix_id: best[affix_id])[:cap])
    return _grey(gear, {i for i, a in active if a.affix.id not in kept}, "rule")


def _shape_problem(rules: Ruleset, entry: GearAffix, weapon: WeaponDef) -> bool:
    """授予的修正技是普攻變形，而且這把武器不能套用、或過不了預算閘門（整條沒效果；同
    :func:`trpg.engine.attack_shapes.skill_problem_zh` 的前半）。"""
    affix = entry.affix
    if not isinstance(affix, ActionAffix):
        return False
    skill = rules.skill_def(affix.skill)
    if not any(rule.change.attack_shape is not None for rule in skill.modifiers):
        return False
    return not suits_line(weapon) or gate_permille(rules, affix.skill, ATTACK_TARGET) == BLOCKED


def whole_no_effect(
    rules: Ruleset, gear: GearState, race: str | None, weapon: WeaponDef
) -> frozenset[int]:
    """``gear.affixes`` 裡生效中、但整條完全沒效果的詞條（索引）：和種族或其他裝備完全重複的地形
    規則，以及不能套用的普攻變形。"""
    found: set[int] = set()
    index = {id(a): i for i, a in enumerate(gear.affixes)}
    if gear.active_affixes("terrain"):
        overlaps = classify_sources(
            gear_rule_sources(rules, race, gear), gear_strength(rules, gear)
        )
        found |= {
            index[id(o.source.gear)]
            for o in overlaps
            if o.source.gear is not None and o.covered and o.full
        }
    found |= {
        i
        for i, a in enumerate(gear.affixes)
        if a.active and a.affix.category == "action" and _shape_problem(rules, a, weapon)
    }
    return frozenset(found)


def _limit_signatures(
    gear: GearState,
    chosen: Collection[str],
    rules: Ruleset,
    race: str | None,
    weapon: WeaponDef,
) -> GearState:
    """招牌：佔名額的最多 ``caps.signature_active`` 個；超過時從最後面一次標灰 1 條
    （``signature``），重算到不超過為止。"""
    cap = rules.equipment.caps.signature_active
    while True:
        signatures = [
            i for i, a in enumerate(gear.affixes) if a.active and a.affix.signature is not None
        ]
        if len(signatures) <= cap:
            return gear
        free = whole_no_effect(rules, gear, race, weapon)
        counted = [i for i in signatures if i not in free]
        if len(counted) <= cap:
            return gear
        loser = max(counted, key=lambda i: limit_priority(gear.affixes[i], chosen))
        gear = _grey(gear, {loser}, "signature")


def limit_gear(
    gear: GearState,
    loadout: Loadout,
    rules: Ruleset,
    *,
    race: str | None,
    weapon: WeaponDef,
) -> GearState:
    """套用改寫規則與招牌的名額（見模組說明）。``race``、``weapon``：單位的種族與手上的武器（判斷
    整條沒效果用）。沒有要標灰的時候原樣回傳。"""
    if not gear.affixes:
        return gear
    chosen = frozenset(loadout.chosen)
    gear = _limit_rules(gear, chosen, rules.equipment.caps.rule_affixes)
    return _limit_signatures(gear, chosen, rules, race, weapon)
