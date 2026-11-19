"""組合器技能的吸血版本（SK-5 第 2 項；玩法交接 4.1.34 第 10 點 SK-4 後補，07 7.6 第 2 點
「照標籤專門做候選」）。

:func:`add_lifesteal`：組合器組好的技能，照 SK-4 的吸血配方（``composer_parts._lifesteal_damage``）
在第一個對敵的傷害效果（沒有聖光雙效、還沒有吸血）附上 ``structure.lifesteal_amount_permille``，
再用組合器同一套旋鈕重調強度（:func:`~trpg.skillgen.composer_tuning.tune`，預算窗照舊），最後過
驗證器。只做 ``structure.lifesteal_skeletons`` 的骨架（打擊、範圍）的主動技；做不出來回傳 ``None``。
不新增效果、不改骨架；亂數只來自呼叫端給的 ``rng``。

許願池（:mod:`trpg.skillgen.wish_pick`）在願望的效果同時有「傷害」和「治療」時用它。
"""

from __future__ import annotations

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, default_affects
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.evolution import effect_strength_knobs
from trpg.skillgen.flash_ops import base_draft
from trpg.skillgen.memo import by_id
from trpg.skillgen.validate import validate_skill

__all__ = ["add_lifesteal", "lifesteal_ready"]


def lifesteal_ready(library: ContentLibrary, skill: SkillDef) -> bool:
    """``skill`` 是吸血配方做得到的結構：主動技、骨架在 ``structure.lifesteal_skeletons``、不是
    陷阱或複合技、有一個對敵的傷害（沒有聖光雙效）、還沒有吸血。"""
    if (
        skill.kind != "active"
        or skill.skeleton not in library.composer.structure.lifesteal_skeletons
        or skill.trap is not None
        or skill.followup is not None
    ):
        return False
    return _first_enemy_damage(library, skill) is not None


def _first_enemy_damage(library: ContentLibrary, skill: SkillDef) -> int | None:
    primitive = by_id(library.ruleset.primitives)["damage"]
    for index, effect in enumerate(skill.effects):
        if effect.type != "damage" or effect.split_heal:
            continue
        if (effect.affects or default_affects(primitive)) != "enemies":
            continue
        return None if effect.lifesteal_permille is not None else index
    return None


def add_lifesteal(library: ContentLibrary, skill: SkillDef, rng: Rng) -> SkillDef | None:
    """``skill`` 的吸血版本（見模組說明）；結構不合（:func:`lifesteal_ready`）或重調後不合格時
    ``None``。"""
    if not lifesteal_ready(library, skill):
        return None
    index = _first_enemy_damage(library, skill)
    if index is None:
        return None
    base, effects = base_draft(skill)
    effects[index]["lifesteal_permille"] = library.composer.structure.lifesteal_amount_permille
    knobs = effect_strength_knobs(skill.category, effects, library)
    try:
        if not tune(rng, library, base, effects, knobs):
            return None
        made = SkillDef.model_validate({**base, "effects": effects})
    except (ValidationError, BudgetError):
        return None
    return None if validate_skill(made, library) else made
