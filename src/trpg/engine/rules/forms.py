"""形態的查詢（Phase 3J-1a，``docs/design/06-技能.md`` 6.30）：純函式，只讀狀態。

進入、離開、維持費等狀態轉換在 :mod:`trpg.engine.forms`；這裡是規則計算會用到的形態效果
（防禦、移動、受傷倍率、治療加成、高度差當平地、天生武器的傷害加成）與「手上的武器」。
"""

from __future__ import annotations

from trpg.content.battle import WeaponDef
from trpg.content.form_breath import breath_skill
from trpg.content.forms import CHOSEN, FormDef, NaturalCharge
from trpg.content.library import Ruleset
from trpg.content.skills import SkillDef
from trpg.engine.actions import Direction
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Element

__all__ = [
    "active_form",
    "breath_of",
    "charge_direction",
    "form_backstab_crit",
    "form_collision_permille",
    "form_defense_permille",
    "form_element_problem",
    "form_flat_height",
    "form_heal_permille",
    "form_move_delta",
    "form_problem",
    "form_taken_permille",
    "held_weapon",
    "is_spell_for_silence",
    "natural_bleed",
    "natural_charge",
    "natural_damage_permille",
]

PERMILLE = 1000


def active_form(rules: Ruleset, unit: UnitState) -> FormDef | None:
    """``unit`` 目前的形態定義；不在形態中為 ``None``。"""
    return None if unit.form is None else rules.form_def(unit.form.form_id)


def natural_charge(rules: Ruleset, unit: UnitState) -> NaturalCharge | None:
    """形態的天生武器若是蓄力武器（龍的吐息；3J-2）回傳它的定向蓄力資料，否則 ``None``。"""
    form = active_form(rules, unit)
    return None if form is None else form.natural_weapon.charge


def breath_of(rules: Ruleset, unit: UnitState) -> SkillDef | None:
    """``unit`` 目前形態的蓄力吐息技能（由形態資料組出，不登錄；見
    :mod:`trpg.content.form_breath`）；不在形態中或天生武器不是蓄力武器時為 ``None``。"""
    form = active_form(rules, unit)
    if form is None or unit.form is None:
        return None
    return breath_skill(form, rules.core, unit.form.element)


def charge_direction(unit: UnitState, xy: tuple[int, int]) -> Direction:
    """朝 ``xy`` 的方向（四方向）：取較大的軸向，相等時取上下（北／南）；同格時為北。"""
    dx, dy = xy[0] - unit.xy[0], xy[1] - unit.xy[1]
    if abs(dx) > abs(dy):
        return "east" if dx > 0 else "west"
    return "south" if dy > 0 else "north"


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


def form_backstab_crit(rules: Ruleset, unit: UnitState) -> int:
    """天生武器特性：背刺時普攻暴擊範圍再多擴大幾點（貓 1）；不在形態中為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.natural_weapon.traits.backstab_crit


def natural_bleed(rules: Ruleset, unit: UnitState) -> int:
    """天生武器特性：普攻命中施加流血的回合數（狼人 1）；沒有時為 0。"""
    form = active_form(rules, unit)
    return 0 if form is None else form.natural_weapon.traits.bleed


def form_collision_permille(state: BattleState, unit: UnitState) -> int:
    """進入獎勵的「本回合撞擊傷害 +N‰」（巨人 +500）：進入的那一輪、輪到自己行動時有效；回傳
    撞擊傷害倍率（‰，沒有加成為 1000）。"""
    form = active_form(state.ruleset, unit)
    if form is None or unit.form is None or state.active_unit != unit.id:
        return PERMILLE
    if unit.form.entered_round != state.round:
        return PERMILLE
    return PERMILLE + form.entry.collision_permille


def is_spell_for_silence(rules: Ruleset, skill: SkillDef) -> bool:
    """沉默擋不擋這個技能：一般技能看 ``category``；進入形態的技能看形態類別——心智形態算法術
    （沉默時不能用）、物理形態不算（沉默擋不住；6.30 實作細節 5）。"""
    form_id = skill.form_id
    if form_id is None:
        return skill.category == "spell"
    return rules.form_def(form_id).category == "mental"


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
