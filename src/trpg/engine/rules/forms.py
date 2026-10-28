"""形態的查詢（Phase 3J-1a，``docs/design/06-技能.md`` 6.30）：純函式，只讀狀態。

進入、離開、維持費等狀態轉換在 :mod:`trpg.engine.forms`；這裡是規則計算會用到的形態效果
（防禦、移動、受傷倍率、治療加成、高度差當平地、天生武器的傷害加成）與「手上的武器」。
"""

from __future__ import annotations

from trpg.content.battle import WeaponDef
from trpg.content.forms import CHOSEN, FormDef
from trpg.content.library import Ruleset
from trpg.engine.state import UnitState
from trpg.shared.types import Element

__all__ = [
    "active_form",
    "form_defense_permille",
    "form_element_problem",
    "form_flat_height",
    "form_heal_permille",
    "form_move_delta",
    "form_problem",
    "form_taken_permille",
    "held_weapon",
    "natural_damage_permille",
]

PERMILLE = 1000


def active_form(rules: Ruleset, unit: UnitState) -> FormDef | None:
    """``unit`` 目前的形態定義；不在形態中為 ``None``。"""
    return None if unit.form is None else rules.form_def(unit.form.form_id)


def held_weapon(unit: UnitState) -> WeaponDef:
    """手上的武器：形態中是進入前的武器（``unit.weapon`` 是天生武器），否則就是 ``unit.weapon``。
    武器技、技能的武器需求與射程、「手持某種武器」條件都看它（6.30：武器技仍看手上武器）。"""
    return unit.weapon if unit.form is None else unit.form.hand_weapon


def form_defense_permille(rules: Ruleset, unit: UnitState) -> int:
    """形態的防禦值加成（‰，可為負）；不在形態中為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.effects.defense_permille


def form_move_delta(rules: Ruleset, unit: UnitState) -> int:
    """形態的每回合移動點數加減；不在形態中為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.effects.move


def form_taken_permille(rules: Ruleset, unit: UnitState, element: Element | None) -> int:
    """形態對 ``element`` 傷害的受傷倍率（‰，多條相乘、無條件捨去）；沒有時為 1000。``chosen``
    指進入時選的元素。"""
    form = active_form(rules, unit)
    if form is None or element is None or unit.form is None:
        return PERMILLE
    chosen = unit.form.element
    value = PERMILLE
    for mod in form.effects.damage_taken:
        target = chosen if mod.element == CHOSEN else mod.element
        if target is element:
            value = value * mod.permille // PERMILLE
    return value


def form_heal_permille(rules: Ruleset, unit: UnitState) -> int:
    """形態給你施放的治療的加成（‰）；不在形態中為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.effects.heal_permille


def form_flat_height(rules: Ruleset, unit: UnitState) -> int:
    """形態中上坡高度差在這個層數以內當平地走；不在形態中為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.effects.flat_height


def natural_damage_permille(rules: Ruleset, unit: UnitState) -> int:
    """天生武器造成的傷害加成（‰；只套在形態中的普攻）；不在形態中為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.natural_weapon.damage_permille


def form_problem(unit: UnitState, form_id: str) -> str | None:
    """不能進入 ``form_id`` 的原因：已經在這個形態中，或該形態冷卻中；可以時為 ``None``。"""
    if unit.form is not None and unit.form.form_id == form_id:
        return "已經在這個形態中"
    remaining = unit.form_cooldowns.get(form_id, 0)
    if remaining > 0:
        return f"形態冷卻中：還要 {remaining} 回合"
    return None


def form_element_problem(form: FormDef, element: Element | None) -> str | None:
    """``use_skill`` 的 ``form_element`` 是否合法：只有元素可選的形態可以帶，而且要在清單內。"""
    if element is None:
        return None
    if not form.element_choices:
        return f"{form.name_zh}沒有可選的元素，不能指定 form_element"
    if element not in form.element_choices:
        names = "、".join(e.display_name for e in form.element_choices)
        return f"{form.name_zh}只能選這些元素：{names}"
    return None
