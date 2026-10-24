"""隨機組合器的武器親和（Phase 3I-5，06 6.10 #50）。

組合器組好技能之後（亂數串流不變），依主角手上的裝備把 **一個已有的、掛在附帶效果上的常見條件**
換成「手持某種武器時」：條件倍率相同（常見 0.85），預算不變，只是那個附帶效果變成「拿著那種武器
才有」。不加新效果、不動核心效果（核心效果沒有武器就不能用），也不改關鍵字：

- 只換第 2 個以後的效果（索引 ≥ 1）上、嚴苛度為 ``common`` 的條件；
- 抽籤用技能 ID 決定的確定性亂數（機率 ``composer.condition.affinity_permille``），沒給手上裝備
  或沒抽中時原樣回傳；
- 換完之後必須通過驗證器、關鍵字不變，否則原樣回傳。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.library import ContentLibrary, gear_class_problem
from trpg.content.skills import WIELDING_WEAPON, ConditionSpec, SkillDef, rarity_rank
from trpg.shared.rng import Rng, fnv1a64
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.validate import validate_skill

__all__ = ["grant_affinity"]


def _usable_gear(skill: SkillDef, held: Mapping[str, str], library: ContentLibrary) -> list[str]:
    return [
        g
        for g in sorted(held)
        if gear_class_problem(skill.weapon_req, g, library.weapons, library.offhands) is None
    ]


def _bonus_indexes(skill: SkillDef, library: ContentLibrary) -> list[int]:
    conditions = library.ruleset.conditions.by_id()
    return [
        i
        for i, effect in enumerate(skill.effects)
        if i >= 1
        and effect.condition is not None
        and effect.condition.type != WIELDING_WEAPON
        and conditions[effect.condition.type].harshness == "common"
    ]


def grant_affinity(
    skill: SkillDef, held: Mapping[str, str] | None, library: ContentLibrary
) -> SkillDef:
    """見模組說明。"""
    wielding = library.ruleset.conditions.by_id().get(WIELDING_WEAPON)
    if (
        not held
        or wielding is None
        or skill.kind != "active"
        or rarity_rank(skill.rarity) < rarity_rank(wielding.min_rarity)
    ):
        return skill
    roll = Rng(fnv1a64(skill.id.encode())).fork("composer.affinity")
    if not roll.chance_permille(library.composer.condition.affinity_permille):
        return skill
    gear = _usable_gear(skill, held, library)
    indexes = _bonus_indexes(skill, library)
    if not gear or not indexes:
        return skill
    index, weapon = roll.choice(indexes), roll.choice(gear)
    effects = list(skill.effects)
    condition = ConditionSpec(type=WIELDING_WEAPON, weapon=weapon)
    effects[index] = effects[index].model_copy(update={"condition": condition})
    changed = skill.model_copy(update={"effects": tuple(effects)})
    keywords = library.keywords
    if derive_keywords(changed, keywords).all() != derive_keywords(skill, keywords).all():
        return skill
    return skill if validate_skill(changed, library) else changed
