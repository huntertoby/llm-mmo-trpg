"""攻擊元素的優先順序（Phase 3I-6，``docs/design/06-技能.md`` 6.10；玩法決定 #52）。

一次攻擊只有一個元素：不疊加、不拆傷害，只改物理傷害的部分。元素來源有四種，由高到低：

1. **臨時附魔**（狀態的 ``attack_element``，由附魔技能施加；同時只會有一個，後施放的覆蓋先施放的）；
2. **普攻附加元素詞條**（只管普攻）；
3. **武器元素詞條**（主手，管普攻與無元素武器技；Phase 3K-1，:func:`weapon_affix_element`
   從主手物品生效中的 ``weapon_element`` 詞條讀出）；
4. **武器本身的元素**（例如法杖）。

- **普攻**：附魔 ＞ 普攻附加 ＞ 武器元素詞條 ＞ 武器本身 ＞ 物理。
- **無元素的武器技**：附魔 ＞ 武器元素詞條 ＞ 武器本身 ＞ 物理（不看普攻附加）。
- **本身已有元素的武器技**：不受任何來源影響。

優先順序本身是純函式 :func:`resolve_attack_element`（表格測試涵蓋全部規則）；其餘函式只負責從單位
身上蒐集來源。關鍵字與元素互動都看這裡算出的最後元素。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from trpg.content.equipment import AttackAffix
from trpg.engine.gear_enhance import gear_attack_element
from trpg.engine.state import UnitState
from trpg.shared.types import Element

if TYPE_CHECKING:
    from trpg.content.library import Ruleset

__all__ = [
    "AttackElementSources",
    "attack_element_sources",
    "effective_attack_element",
    "enchant_element",
    "resolve_attack_element",
    "weapon_affix_element",
]


@dataclass(frozen=True, slots=True)
class AttackElementSources:
    """一個單位的攻擊元素來源（沒有的來源為 ``None``）。"""

    enchant: Element | None = None
    """臨時附魔（狀態 ``attack_element``）。"""
    modifier: Element | None = None
    """修正技能的元素轉換（``add_element``；只在這次施放受修正規則影響時才有）。"""
    basic_affix: Element | None = None
    """普攻附加元素詞條（只管普攻）。"""
    weapon_affix: Element | None = None
    """武器元素詞條（普攻與無元素武器技）。"""
    weapon: Element = Element.PHYSICAL
    """武器本身的元素（物理武器為 ``physical``）。"""


def resolve_attack_element(
    sources: AttackElementSources, *, is_basic: bool, skill_element: Element | None = None
) -> Element:
    """一次攻擊最後生效的元素（純函式；06 6.10，#52 與補充一、二）。

    - 已有元素（不是物理）的武器技：不受任何來源影響。
    - 武器本身的元素（法杖等）**只有臨時附魔能覆寫**；修正技能、普攻附加詞條、武器元素詞條
      只改物理傷害。
    - 普攻：附魔 ＞ 武器本身元素 ＞ 修正技能 ＞ 普攻附加詞條 ＞ 武器元素詞條 ＞ 物理。
    - 無元素武器技：附魔 ＞ 武器本身元素 ＞ 修正技能 ＞ 武器元素詞條 ＞ 物理。
    """
    if skill_element is not None and skill_element is not Element.PHYSICAL:
        return skill_element
    chain = (
        sources.enchant,
        sources.weapon,
        sources.modifier,
        sources.basic_affix if is_basic else None,
        sources.weapon_affix,
    )
    for element in chain:
        if element is not None and element is not Element.PHYSICAL:
            return element
    return Element.PHYSICAL


_MAIN_HAND = "main_hand"


def weapon_affix_element(unit: UnitState, *, held: bool = False) -> Element | None:
    """武器元素詞條的元素（Phase 3K-1，08 8.21.2.4 #52）：主手物品上生效中的第一條
    ``weapon_element`` 普攻附加詞條（同一件最多 1 條，穿戴驗證擋住）；沒有時 ``None``。

    ``held``：看手上的武器（武器技；Phase 3J-1a 形態中普攻改用天生武器，主手詞條只對武器技
    生效）。"""
    gear = unit.form.hand_gear if held and unit.form is not None else unit.gear
    for entry in gear.active_affixes("attack"):
        affix = entry.affix
        if (
            entry.slot == _MAIN_HAND
            and isinstance(affix, AttackAffix)
            and affix.weapon_element is not None
        ):
            return affix.weapon_element
    return None


def enchant_element(rules: Ruleset, unit: UnitState) -> Element | None:
    """單位身上附魔狀態的元素。同時只會有一個（施加時取代舊的）；萬一有多個（資料手動塞入）取
    列表中最後一個。"""
    found: Element | None = None
    for status in unit.statuses:
        element = rules.status_def(status.status_id).attack_element
        if element is not None:
            found = element
    return found


def attack_element_sources(
    rules: Ruleset, unit: UnitState, *, held: bool = False
) -> AttackElementSources:
    """蒐集 ``unit`` 的四種元素來源。``held``：武器技——看手上的武器（Phase 3J-1a：形態中
    ``unit.weapon`` 是天生武器，武器技仍看手上武器與它的詞條）。"""
    weapon = unit.form.hand_weapon if held and unit.form is not None else unit.weapon
    return AttackElementSources(
        enchant=enchant_element(rules, unit),
        basic_affix=gear_attack_element(unit),
        weapon_affix=weapon_affix_element(unit, held=held),
        weapon=weapon.element,
    )


def effective_attack_element(
    rules: Ruleset,
    unit: UnitState,
    *,
    is_basic: bool,
    skill_element: Element | None = None,
) -> Element:
    """``unit`` 這次攻擊最後生效的元素。"""
    return resolve_attack_element(
        attack_element_sources(rules, unit),
        is_basic=is_basic,
        skill_element=skill_element,
    )
