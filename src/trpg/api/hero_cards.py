"""戰鬥中主角的技能卡（Phase 3-41c）：附施放者當下的實際值。

`GET /api/skills/{id}` 的卡片是純算式、召喚物資訊是 1 級基準值；戰鬥中的技能列改用這裡的卡片：
傷害算法附「目前」加成（有效屬性，含狀態加值）與武器骰、召喚物資訊用
:func:`trpg.engine.summons.core.summon_stats`（和引擎生成召喚物同一組函式）。只讀取狀態、不推進戰鬥。
只回傳有算式或召喚物的技能（其餘的卡片和基本版一樣）。
"""

from __future__ import annotations

from trpg.api.schemas import HeroCards
from trpg.content.library import ContentLibrary
from trpg.content.skills import EffectSpec, SkillDef
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons.core import SummonStats, summon_stats
from trpg.narrative.skills import CardOwner, SkillCard, skill_card
from trpg.shared.types import Attribute, Team, UnitId

__all__ = ["hero_cards", "unit_card_owner"]


def unit_card_owner(state: BattleState, unit: UnitState, skill: SkillDef) -> CardOwner:
    """``unit`` 持有 ``skill`` 時的卡片持有者資料（有效屬性、武器、召喚物實際值）。"""

    def get(attr: Attribute) -> int:
        return effective_attribute(state.ruleset, unit, attr)

    def stats_for(spec: EffectSpec) -> SummonStats | None:
        if spec.unit is None:
            return None
        try:
            return summon_stats(state, unit, spec.unit, skill.id, spec)
        except KeyError:
            return None

    return CardOwner(weapon=unit.weapon, attr_get=get, summon_stats=stats_for)


def hero_cards(state: BattleState, library: ContentLibrary, unit_id: UnitId) -> HeroCards:
    """``unit_id`` 持有的技能中有算式或召喚物的卡片（實際值）。單位不存在時為空。"""
    unit = state.units.get(unit_id)
    cards: dict[str, SkillCard] = {}
    if unit is None:
        return HeroCards(cards=cards)
    for skill_id in sorted(unit.all_skills):
        try:
            skill = state.ruleset.skill_def(skill_id)
        except KeyError:
            continue
        owner = unit_card_owner(state, unit, skill)
        card = skill_card(library, skill, owner=owner, ally=unit.team is Team.ALLY)
        if card.formula_lines or card.summons:
            cards[skill_id] = card
    return HeroCards(cards=cards)
