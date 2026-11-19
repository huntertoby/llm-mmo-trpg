"""組合器的雙元素完整技能（WC-2 第 1 項；#167，07 7.6「許願池：願望驅動」第 1 點、06 6.34.9
「第二元素 2 階開放」）。

:func:`add_second_element`：組合器組好的技能（已經帶一個元素、有傷害效果）在第一個傷害效果後面多一段
另一個元素的傷害（同閃現「第二元素」的寫法：法術技用骰子、武器技用倍率），再用組合器同一套旋鈕重調
強度（:func:`~trpg.skillgen.composer_tuning.tune`，預算窗照舊），最後過驗證器（含第二元素的角色階級
門檻）。做不出來回傳 ``None``。結構不另外加新原語、不改骨架；亂數只來自呼叫端給的 ``rng``。

許願池（:mod:`trpg.skillgen.wish_pick`）在願望有兩個元素、角色已到第二元素的階級時用它。
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, damage_elements
from trpg.content.skills.constants import MAX_EFFECTS
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.evolution import effect_strength_knobs
from trpg.skillgen.flash_ops import base_draft
from trpg.skillgen.validate import validate_skill

__all__ = ["add_second_element", "second_element_tier"]

_KINDS = frozenset({"active", "passive", "reaction"})
_FIRST_DICE = "1d4"
_FIRST_MULTIPLIER = 300


def second_element_tier(library: ContentLibrary) -> int:
    """第二元素開放的角色階級（``skill_budget.yaml`` 的 ``min_character_tier.second_element``）。"""
    return library.budget.min_character_tier.second_element


def _new_damage(skill: SkillDef, source: dict[str, Any], element: str) -> dict[str, Any]:
    """新增的傷害效果（數值之後由旋鈕調，從最弱開始）。"""
    effect: dict[str, Any] = {"type": "damage", "element": element}
    if "affects" in source:
        effect["affects"] = source["affects"]
    if skill.category == "spell" or "dice" in source:
        effect["dice"] = _FIRST_DICE
    else:
        effect["multiplier_permille"] = _FIRST_MULTIPLIER
    return effect


def add_second_element(
    library: ContentLibrary, skill: SkillDef, element: str, rng: Rng
) -> SkillDef | None:
    """``skill`` 多一段 ``element`` 的傷害（見模組說明）；``element`` 不能是物理、不能是技能已經有的
    元素；技能要有元素、有傷害效果、效果數沒滿、不是陷阱或複合技，角色階級（技能的 ``tier``）要到
    第二元素的階級。"""
    have = {e.value for e in damage_elements(skill)}
    if (
        element == Element.PHYSICAL.value
        or element in have
        or not have
        or skill.kind not in _KINDS
        or skill.trap is not None
        or skill.followup is not None
        or skill.tier < second_element_tier(library)
        or len(skill.effects) >= MAX_EFFECTS
    ):
        return None
    base, effects = base_draft(skill)
    index = next((i for i, e in enumerate(effects) if e["type"] == "damage"), None)
    if index is None:
        return None
    effects.insert(index + 1, _new_damage(skill, effects[index], element))
    knobs = effect_strength_knobs(skill.category, effects, library)
    try:
        if not tune(rng, library, base, effects, knobs):
            return None
        made = SkillDef.model_validate({**base, "effects": effects})
    except (ValidationError, BudgetError):
        return None
    return None if validate_skill(made, library) else made
