"""關鍵字推導與技能池（Phase 3-24b1，``docs/design/06-技能.md`` 6.27.1、6.27.2）。

技能「製造」或「利用」哪些關鍵字，由原語、條件、觸發自動推導（推導表
``content/skill_keywords.yaml``），不由人填寫。這裡的函式都是純函式：只讀技能與推導表，沒有亂數、沒有時間。

**技能池**：每個關鍵字一個池，技能依「製造或利用某關鍵字」自動歸池（一招可同時在多個池）。創角與候選
產生器（3-24b2）從池裡抽技能；``pool_skills`` 預設只列「可當起始技能」的：1 階、普通或稀有、主動技。
遊戲不定義流派：這裡沒有任何主題分類，只有關鍵字。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from trpg.content.keyword_derive import (
    Facts,
    SkillKeywords,
    derive_from_facts,
    derive_keywords,
    modifier_effects,
    skill_condition_specs,
    skill_effect_specs,
    walk_effect,
)
from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordDef, KeywordTable
from trpg.content.skills import (
    ConditionSpec,
    EffectSpec,
    ModifierSpec,
    ShapeSpec,
    SkillDef,
    TriggerSpec,
)

__all__ = [
    "SkillKeywords",
    "derive_draft_keywords",
    "derive_keywords",
    "is_starter_skill",
    "keyword_pools",
    "pool_skills",
    "skill_condition_specs",
    "skill_effect_specs",
    "skills_without_keywords",
]

_STARTER_RARITIES = ("common", "rare")


def _parsed[T: BaseModel](model: type[T], raw: object) -> T | None:
    try:
        return model.model_validate(raw)
    except ValidationError:
        return None


def _parsed_list[T: BaseModel](model: type[T], raw: object) -> list[T]:
    items = raw if isinstance(raw, list | tuple) else ()
    return [found for item in items if (found := _parsed(model, item)) is not None]


def derive_draft_keywords(draft: Mapping[str, Any], table: KeywordTable) -> SkillKeywords:
    """組到一半的技能草稿（工坊的 JSON）製造與利用的關鍵字：逐一解析能解析的部分
    （效果、條件、觸發、形狀、修正規則），解析不了的略過，所以草稿每多一步就多顯示一點。"""
    effects = _parsed_list(EffectSpec, draft.get("effects"))
    followup = draft.get("followup")
    if isinstance(followup, Mapping):
        effects += _parsed_list(EffectSpec, followup.get("effects"))
    expanded = [sub for effect in effects for sub in walk_effect(effect)]
    modifiers = _parsed_list(ModifierSpec, draft.get("modifiers"))
    for rule in modifiers:
        expanded.extend(modifier_effects(rule))
    conditions = [c for c in (_parsed(ConditionSpec, draft.get("condition")),) if c is not None]
    conditions += [e.condition for e in expanded if e.condition is not None]
    conditions += [r.condition for r in modifiers if r.condition is not None]
    shape = _parsed(ShapeSpec, draft.get("shape"))
    facts = Facts(
        effects=tuple(expanded),
        conditions=tuple(conditions),
        trigger=_parsed(TriggerSpec, draft.get("trigger")),
        shape=None if shape is None else shape.type,
        modifiers=tuple(modifiers),
        weapon_req=_text(draft.get("weapon_req")),
        category=_text(draft.get("category")),
    )
    return derive_from_facts(facts, table)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def skills_without_keywords(skills: Iterable[SkillDef], table: KeywordTable) -> list[SkillDef]:
    """沒有任何關鍵字的技能（驗收：每招技能至少製造或利用一個關鍵字）。"""
    return [s for s in skills if not derive_keywords(s, table)]


# ---------------------------------------------------------------------------
# 技能池
# ---------------------------------------------------------------------------


def is_starter_skill(skill: SkillDef) -> bool:
    """可當起始技能（創角與候選產生器的來源）：1 階、普通或稀有、主動技。"""
    return skill.tier == 1 and skill.rarity in _STARTER_RARITIES and skill.kind == "active"


def keyword_pools(
    library: ContentLibrary, *, starter_only: bool = False
) -> dict[str, tuple[str, ...]]:
    """每個關鍵字的技能池：關鍵字 ID → 技能 ID（排序）。``starter_only`` 只列可當起始技能的。"""
    table = library.keywords
    pools: dict[str, list[str]] = {k.id: [] for k in table.keywords}
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        if starter_only and not is_starter_skill(skill):
            continue
        for keyword_id in derive_keywords(skill, table).all():
            pools[keyword_id].append(skill_id)
    return {k: tuple(v) for k, v in pools.items()}


def pool_skills(
    library: ContentLibrary, keyword_id: str, *, starter_only: bool = True
) -> tuple[SkillDef, ...]:
    """``keyword_id`` 技能池裡的技能（依 ID 排序；預設只列可當起始技能的）。"""
    ids = keyword_pools(library, starter_only=starter_only)[keyword_id]
    return tuple(library.skills[i] for i in ids)


def keyword_def(library: ContentLibrary, keyword_id: str) -> KeywordDef:
    """關鍵字的定義（不存在時 ``KeyError``）。"""
    return library.keywords.by_id()[keyword_id]
