"""召喚專用詞條與繼承普攻附加的結算（Phase 3-33f2，``docs/design/06-技能.md`` 6.29.6、
``docs/design/08-裝備.md`` 8.21.5.3）。

- **技能強化類**（第 3 類，``keyword: summon``）：``cooldown_delta`` 召喚技能冷卻 −1（製造召喚物的
  技能；冷卻最低 1）、``duration_delta`` 召喚物持續 +1 輪、``sacrifice_permille`` 利用召喚物的獻祭
  （``sacrifice_summon``）傷害與治療 +N‰（傷害加成計入全身 +50% 上限）。皆先遞減（同 id 依
  100／50／25／0%）再套硬上限。
- **繼承普攻附加**（第 4 類 ``summon_inherit``）：召喚物的裝備狀態只放施放者 1 條可繼承的普攻附加
  （普攻元素、命中附帶狀態、連擊、分裂；符文不繼承），依詞條 ID 取第一條。
- **召喚物倒下時**（第 6 類觸發 ``on_summon_downed``）：見 :mod:`trpg.engine.gear_triggers`。
"""

from __future__ import annotations

from trpg.content.equipment import AttackAffix, KeywordAffix
from trpg.content.skills import SUMMON, SkillDef
from trpg.engine.gear import cap_cooldown, cap_damage_bonus, diminished_total
from trpg.engine.gear_state import GearAffix, GearState
from trpg.engine.state import BattleState, UnitState

__all__ = [
    "gear_sacrifice_permille",
    "gear_summon_cooldown",
    "gear_summon_duration",
    "inherit_attack_gear",
]

_PERMILLE = 1000


def _inheritable(affix: AttackAffix) -> bool:
    """可以被召喚物繼承的普攻附加：元素、命中附帶狀態、連擊與分裂（符文要靠施放者自己的符文，
    召喚物沒有，所以不繼承；繼承詞條本身也不傳）。"""
    return not affix.summon_inherit and affix.rune is None


def inherit_attack_gear(owner: UnitState, current: GearState) -> GearState:
    """施放者身上有生效的「召喚物繼承普攻附加」詞條時，回傳只含 1 條繼承來的普攻附加的裝備狀態
    （依詞條 ID 取第一條可繼承的）；否則維持 ``current``。"""
    attacks = owner.gear.active_affixes("attack")
    if not any(isinstance(g.affix, AttackAffix) and g.affix.summon_inherit for g in attacks):
        return current
    for gear in attacks:
        affix = gear.affix
        if isinstance(affix, AttackAffix) and _inheritable(affix):
            inherited = GearAffix(
                slot=gear.slot,
                item_id=gear.item_id,
                affix=affix,
                value=gear.value,
                weight_permille=_PERMILLE,
                rank=0,
            )
            return GearState(affixes=(inherited,), cooldown_min=owner.gear.cooldown_min)
    return current


def _summon_entries(unit: UnitState, change: str, direction: str) -> list[list[GearAffix]]:
    """生效中、改變種類為 ``change``、選取 ``keyword: summon`` 的技能強化詞條，依詞條 ID 分組。"""
    groups: dict[str, list[GearAffix]] = {}
    for entry in unit.gear.active_affixes("keyword"):
        affix = entry.affix
        if (
            isinstance(affix, KeywordAffix)
            and affix.keyword == SUMMON
            and affix.change == change
            and affix.direction == direction
        ):
            groups.setdefault(affix.id, []).append(entry)
    return [groups[k] for k in sorted(groups)]


def _amount(entry: GearAffix) -> int:
    if entry.value is not None:
        return entry.value
    affix = entry.affix
    assert isinstance(affix, KeywordAffix) and affix.amount is not None
    return affix.amount


def _total(unit: UnitState, change: str, direction: str) -> int:
    if not unit.gear.affixes:
        return 0
    return sum(diminished_total(g, _amount) for g in _summon_entries(unit, change, direction))


def gear_summon_cooldown(unit: UnitState, skill: SkillDef, base: int | None) -> int | None:
    """召喚技能（有 ``summon`` 效果）施放時設定的冷卻：``base`` ＋ 召喚冷卻詞條（遞減後，通常是
    −1），不低於冷卻下限。"""
    if base is None or not unit.gear.affixes or not any(e.type == SUMMON for e in skill.effects):
        return base
    delta = _total(unit, "cooldown_delta", "create")
    return base if delta == 0 else cap_cooldown(unit.gear.cooldown_min, base, delta)


def gear_summon_duration(unit: UnitState) -> int:
    """召喚物持續多出的輪數（召喚物持續 +N 輪詞條，遞減後）。"""
    return max(0, _total(unit, "duration_delta", "create"))


def gear_sacrifice_permille(state: BattleState, unit: UnitState) -> int:
    """獻祭（``sacrifice_summon``）的傷害與治療加成（‰，遞減後）。獻祭的傷害加成計入全身 +50% 上限
    （:func:`~trpg.engine.gear.cap_damage_bonus`）；治療用同一個數字。"""
    total = _total(unit, "sacrifice_permille", "exploit")
    return max(0, cap_damage_bonus(state.ruleset, total))
