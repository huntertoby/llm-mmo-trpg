"""裝備詞條第 3、4、5 類的結算（Phase 3G-G2，``docs/design/08-裝備.md`` 8.21.2.3～8.21.2.5）。

- **第 3 類 技能強化（關鍵字）**：詞條用關鍵字選取技能——「製造」或「利用」該關鍵字的技能（推導表
  ``content/skill_keywords.yaml``；推導函式 ``trpg.content.keyword_derive.derive_keywords``，結果依
  技能 ID 快取在規則包上），改變它的狀態持續回合（:func:`gear_status_duration`）、傷害
  （:func:`gear_keyword_damage_permille`，和其他傷害加成一起受全身 +50% 上限，見
  :func:`trpg.engine.modifiers.damage_permille`）或範圍（:func:`gear_area_delta`，受形狀最大值也就是
  6.6 的範圍上限約束）。``include_attack`` 的詞條也套用在普攻上：普攻的關鍵字由它的元素與命中附帶
  的狀態推導（:func:`attack_keywords`）。
- **第 4 類 普攻附加**：普攻帶元素（:func:`gear_attack_element`，只改物理傷害）、命中後附帶狀態
  （:func:`gear_on_hit_statuses`）。
- **第 5 類 武器特性強化**：改單位那把武器的資料參數（:func:`geared_weapon`，開戰時算一次）。參數
  路徑是 ``WeaponDef`` 的整數欄位（``knockback``）、巢狀欄位（``armor_break.rounds``、
  ``steady.hit``），或特例 ``range_mod.penalty``（距離修正裡的懲罰部分乘上倍率）；``delta`` 加減、
  ``scale_permille`` 倍率。暴擊範圍不低於 ``caps.crit_range_min``。

所有數字都先經過 :func:`~trpg.engine.gear.diminished_total` 的遞減（同 id 100／50／25／0%）。這個
模組只讀狀態（:func:`geared_weapon` 回傳新的武器資料）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from trpg.content.battle import WeaponDef
from trpg.content.equipment import (
    AttackAffix,
    EquipmentRules,
    KeywordAffix,
    WeaponTraitAffix,
)
from trpg.content.keyword_derive import Facts, SkillKeywords
from trpg.content.skills import EffectSpec, SkillDef
from trpg.content.weapon_params import set_weapon_param
from trpg.engine.gear import diminished_total
from trpg.engine.gear_state import GearAffix, GearState
from trpg.engine.rune_queries import has_own_rune
from trpg.shared.types import Element

if TYPE_CHECKING:
    from trpg.engine.modifiers import Use
    from trpg.engine.skills.conditions import Subject
    from trpg.engine.state import BattleState, UnitState

__all__ = [
    "attack_element",
    "attack_keywords",
    "gear_area_delta",
    "gear_attack_element",
    "gear_keyword_damage_permille",
    "gear_on_hit_statuses",
    "gear_rune_read_permille",
    "gear_status_duration",
    "geared_weapon",
    "rune_affixes",
    "spend_gear_rune_read",
    "strike_affixes",
]

_PERMILLE = 1000


def _groups(gear: GearState, category: str) -> dict[str, list[GearAffix]]:
    """生效中的某類詞條，依詞條 id 分組（id 由小到大）。"""
    found: dict[str, list[GearAffix]] = {}
    for entry in gear.active_affixes(category):
        found.setdefault(entry.affix.id, []).append(entry)
    return found


# ---------------------------------------------------------------------------
# 第 4 類 普攻附加
# ---------------------------------------------------------------------------


def gear_attack_element(unit: UnitState) -> Element | None:
    """普攻附加的元素（第一條 ``add_element`` 的普攻附加詞條）；沒有時 ``None``。"""
    if not unit.gear.affixes:
        return None
    for entries in _groups(unit.gear, "attack").values():
        affix = entries[0].affix
        assert isinstance(affix, AttackAffix)
        if affix.add_element is not None:
            return affix.add_element
    return None


def attack_element(unit: UnitState) -> Element:
    """普攻的元素：武器本身的元素，物理武器則看普攻附加（不含修正技能的 ``add_element``）。"""
    base = unit.weapon.element
    if base is not Element.PHYSICAL:
        return base
    return gear_attack_element(unit) or Element.PHYSICAL


def _on_hit_entries(unit: UnitState) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for entries in _groups(unit.gear, "attack").values():
        affix = entries[0].affix
        assert isinstance(affix, AttackAffix)
        if affix.on_hit_status is not None:
            assert affix.status_duration is not None
            found.append((affix.on_hit_status, affix.status_duration))
    return found


def gear_on_hit_statuses(state: BattleState, unit: UnitState) -> list[tuple[str, int]]:
    """普攻命中後要附帶的狀態與持續回合（狀態 ID、回合；持續回合已含技能強化的「+N 回合」）。"""
    if not unit.gear.affixes:
        return []
    return [
        (status, rounds + gear_status_duration(state, unit, None, True, status))
        for status, rounds in _on_hit_entries(unit)
    ]


def rune_affixes(unit: UnitState, rune: str) -> list[GearAffix]:
    """生效中的普攻符文詞條（Phase 3-31；``rune`` 為 ``read``／``detonate``／``inscribe``，
    依詞條 id 排序）。"""
    if not unit.gear.affixes:
        return []
    found: list[GearAffix] = []
    for entries in _groups(unit.gear, "attack").values():
        affix = entries[0].affix
        assert isinstance(affix, AttackAffix)
        if affix.rune == rune:
            found.append(entries[0])
    return found


def strike_affixes(unit: UnitState, strike: str) -> list[GearAffix]:
    """生效中的普攻流詞條（Phase 3-32a；``strike`` 為 ``combo``／``cleave``，依詞條 id 排序）。"""
    if not unit.gear.affixes:
        return []
    found: list[GearAffix] = []
    for entries in _groups(unit.gear, "attack").values():
        affix = entries[0].affix
        assert isinstance(affix, AttackAffix)
        if affix.strike == strike:
            found.append(entries[0])
    return found


def _read_ready(state: BattleState, unit: UnitState, subject: Subject) -> list[GearAffix]:
    """可以生效的讀取符文詞條：本回合還沒用過，且目標格上有自己的符文。"""
    entries = rune_affixes(unit, "read")
    if not entries or not has_own_rune(state, unit.id, subject.xy):
        return []
    return [e for e in entries if unit.gear_turn_counts.get(e.affix.id, 0) < 1]


def gear_rune_read_permille(state: BattleState, unit: UnitState, use: Use, subject: Subject) -> int:
    """普攻讀取符文的傷害加成（‰，Phase 3-31）：打到站在自己符文上的敵人時 +N‰，每條詞條每回合
    1 次（用完由 :func:`spend_gear_rune_read` 記錄）。還沒套全身傷害加成上限。"""
    if use.action != "attack":
        return 0
    return sum(e.value or 0 for e in _read_ready(state, unit, subject))


def spend_gear_rune_read(state: BattleState, unit: UnitState, subject: Subject) -> None:
    """記下本回合用掉的讀取符文加傷（與 :func:`gear_rune_read_permille` 同一個 ``subject``）。"""
    for entry in _read_ready(state, unit, subject):
        key = entry.affix.id
        unit.gear_turn_counts[key] = unit.gear_turn_counts.get(key, 0) + 1


# ---------------------------------------------------------------------------
# 第 3 類 技能強化（關鍵字）
# ---------------------------------------------------------------------------


def attack_keywords(state: BattleState, unit: UnitState) -> SkillKeywords:
    """普攻製造與利用的關鍵字：由普攻的元素傷害與命中附帶的狀態推導（和技能同一份推導表）。"""
    from trpg.engine.attack_element import (  # noqa: PLC0415  # 避免循環匯入
        effective_attack_element,
    )

    element = effective_attack_element(state.ruleset, unit, is_basic=True)
    statuses = tuple(status for status, _ in _on_hit_entries(unit))
    effects = [EffectSpec.model_construct(type="apply_status", status=s) for s in statuses]
    if element is not Element.PHYSICAL:
        effects.append(EffectSpec.model_construct(type="damage", element=element))
    return state.ruleset.facts_keywords(
        ("attack", element.value, statuses), Facts(effects=tuple(effects))
    )


def _selected(
    state: BattleState,
    unit: UnitState,
    affix: KeywordAffix,
    skill: SkillDef | None,
    is_attack: bool,
) -> bool:
    """技能強化詞條有沒有選中這次動作（技能：製造或利用該關鍵字；普攻：詞條 ``include_attack`` 且
    普攻本身製造或利用該關鍵字）。"""
    if skill is not None:
        keywords = state.ruleset.skill_keywords(skill)
    elif is_attack and affix.include_attack:
        keywords = attack_keywords(state, unit)
    else:
        return False
    wanted = keywords.makes if affix.direction == "create" else keywords.uses
    return affix.keyword in wanted


def _amount(entry: GearAffix) -> int:
    if entry.value is not None:
        return entry.value
    affix = entry.affix
    assert isinstance(affix, KeywordAffix) and affix.amount is not None
    return affix.amount


def _keyword_total(
    state: BattleState,
    unit: UnitState,
    skill: SkillDef | None,
    is_attack: bool,
    change: str,
    *,
    status: str | None = None,
) -> int:
    if not unit.gear.affixes or (skill is None and not is_attack):
        return 0
    total = 0
    for entries in _groups(unit.gear, "keyword").values():
        affix = entries[0].affix
        assert isinstance(affix, KeywordAffix)
        if affix.change != change or (status is not None and affix.status != status):
            continue
        if _selected(state, unit, affix, skill, is_attack):
            total += diminished_total(entries, _amount)
    return total


def gear_status_duration(
    state: BattleState, unit: UnitState, skill: SkillDef | None, is_attack: bool, status: str
) -> int:
    """這次動作施加 ``status`` 時，裝備多給的持續回合（「你施加的燃燒 +1 回合」）。"""
    return _keyword_total(state, unit, skill, is_attack, "status_duration", status=status)


def gear_keyword_damage_permille(
    state: BattleState, unit: UnitState, skill: SkillDef | None, is_attack: bool
) -> int:
    """這次動作的技能強化傷害加成（‰；「利用倒地的技能傷害 +N%」）。還沒套全身傷害加成上限。"""
    return _keyword_total(state, unit, skill, is_attack, "damage_permille")


def gear_area_delta(state: BattleState, unit: UnitState, skill: SkillDef) -> int:
    """技能的範圍加成（「製造帶電的技能範圍 +1」；實際長大多少由形狀的最大值約束）。"""
    return _keyword_total(state, unit, skill, False, "area_delta")


# ---------------------------------------------------------------------------
# 第 5 類 武器特性強化
# ---------------------------------------------------------------------------


def _fixed(amount: int) -> Callable[[GearAffix], int]:
    return lambda _entry: amount


def _trait_changes(
    unit_gear: GearState, weapon_id: str
) -> list[tuple[str, int | None, int | None]]:
    """對這把武器生效的武器特性強化：``(參數, 加減, 倍率‰)``（同 id 已遞減加總）。"""
    changes: list[tuple[str, int | None, int | None]] = []
    for entries in _groups(unit_gear, "weapon_trait").values():
        affix = entries[0].affix
        assert isinstance(affix, WeaponTraitAffix)
        if weapon_id not in affix.weapons:
            continue
        if affix.delta is not None:
            changes.append((affix.param, diminished_total(entries, _fixed(affix.delta)), None))
        else:
            assert affix.scale_permille is not None
            cut = diminished_total(entries, _fixed(_PERMILLE - affix.scale_permille))
            changes.append((affix.param, None, max(0, _PERMILLE - cut)))
    return changes


def _cap_crit(data: dict[str, Any], original: WeaponDef, crit_range_min: int) -> None:
    """暴擊範圍不低於 ``crit_range_min``（武器本來就更低的不動）；站定的暴擊範圍擴大也一併限制。"""
    floor = min(original.crit_range, crit_range_min)
    data["crit_range"] = max(data["crit_range"], floor)
    steady = data.get("steady")
    if steady is not None:
        original_cut = original.steady.crit_range if original.steady is not None else 0
        room = max(original_cut, data["crit_range"] - crit_range_min)
        steady["crit_range"] = min(steady["crit_range"], room)


def geared_weapon(weapon: WeaponDef, gear: GearState, rules: EquipmentRules) -> WeaponDef:
    """套用武器特性強化詞條後的武器資料；沒有適用的詞條時回傳原物件。

    改完之後重新通過 ``WeaponDef`` 驗證（載入時已檢查詞條數值的範圍都合法，所以這裡不會失敗；萬一
    失敗就維持原武器）。
    """
    if not gear.affixes:
        return weapon
    changes = _trait_changes(gear, weapon.id)
    if not changes:
        return weapon
    data = weapon.model_dump()
    for param, delta, factor in changes:
        set_weapon_param(data, param, delta, factor)
    _cap_crit(data, weapon, rules.caps.crit_range_min)
    try:
        return WeaponDef.model_validate(data)
    except ValidationError:
        return weapon
