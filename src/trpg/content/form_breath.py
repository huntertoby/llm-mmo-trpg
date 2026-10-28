"""蓄力吐息的結算技能（Phase 3J-2，``docs/design/06-技能.md`` 6.30 龍）。

天生武器帶 ``charge`` 的形態（龍），普攻是「選方向開始蓄力」；下一個自己的回合開始時，引擎用這裡
由資料組出的一個 **不登錄的技能** 結算釋放：錐形（大小 ``charge.size``）、一個傷害效果（天生武器的
骰、所選元素；屬性 × 0.3 同普攻，取自核心規則的 ``basic_attack_attr_multiplier_permille``）。
技能的名稱、骰、屬性、元素全部取自 ``content/forms.yaml``，改資料就改吐息，不需要改程式。
"""

from __future__ import annotations

from trpg.content.forms import FormDef
from trpg.content.rules import CoreRules
from trpg.content.skills import EffectSpec, ShapeSpec, SkillDef
from trpg.shared.types import Element

__all__ = ["BREATH_PREFIX", "breath_skill", "breath_skill_id"]

BREATH_PREFIX = "skill_form_breath_"
"""蓄力吐息技能 ID 的前綴（後面接形態 ID）。這些技能不在技能庫裡，只由資料組出。"""


def breath_skill_id(form_id: str) -> str:
    return f"{BREATH_PREFIX}{form_id}"


def breath_skill(form: FormDef, core: CoreRules, element: Element | None) -> SkillDef | None:
    """``form`` 的蓄力吐息（錐形的傷害技能，法術類別）；天生武器不是蓄力武器時為 ``None``。
    ``element`` 是進入時選的元素（固定元素的武器忽略它）。"""
    weapon = form.natural_weapon
    if weapon.charge is None:
        return None
    chosen = weapon.element if weapon.element is not None else element
    first = weapon.attrs[0]
    second = weapon.attrs[1] if len(weapon.attrs) > 1 else None
    damage = EffectSpec(
        type="damage",
        dice=weapon.dice,
        element=chosen,
        attr_permille=core.basic_attack_attr_multiplier_permille,
    )
    return SkillDef(
        id=breath_skill_id(form.id),
        name_zh=weapon.name_zh,
        tier=1,
        rank=1,
        rarity="rare",
        kind="active",
        skeleton="area",
        category="spell",
        weapon_req="any",
        ap_cost=1,
        scaling_attr=first,
        secondary_scaling_attr=second,
        shape=ShapeSpec(type="cone", size=weapon.charge.size),
        effects=(damage,),
    )
