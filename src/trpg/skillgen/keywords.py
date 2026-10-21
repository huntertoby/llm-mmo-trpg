"""關鍵字推導與技能池（Phase 3-24b1，``docs/design/06-技能.md`` 6.27.1、6.27.2）。

技能「製造」或「利用」哪些關鍵字，由原語、條件、觸發自動推導（推導表
``content/skill_keywords.yaml``），不由人填寫。這裡的函式都是純函式：只讀技能與推導表，沒有亂數、沒有時間。

**技能池**：每個關鍵字一個池，技能依「製造或利用某關鍵字」自動歸池（一招可同時在多個池）。創角與候選
產生器（3-24b2）從池裡抽技能；``pool_skills`` 預設只列「可當起始技能」的：1 階、普通或稀有、主動技。
遊戲不定義流派：這裡沒有任何主題分類，只有關鍵字。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skill_keywords import KeywordDef, KeywordRule, KeywordTable
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
    "skills_without_keywords",
]

_STARTER_RARITIES = ("common", "rare")


@dataclass(frozen=True, slots=True)
class SkillKeywords:
    """一個技能製造與利用的關鍵字 ID（依推導表的順序）。"""

    makes: tuple[str, ...] = ()
    uses: tuple[str, ...] = ()

    def all(self) -> tuple[str, ...]:
        """製造或利用的關鍵字（依推導表的順序，不重複）。"""
        return tuple(dict.fromkeys((*self.makes, *self.uses)))

    def __bool__(self) -> bool:
        return bool(self.makes or self.uses)


# ---------------------------------------------------------------------------
# 從技能收集「來源」
# ---------------------------------------------------------------------------


def _walk_effect(effect: EffectSpec) -> Iterator[EffectSpec]:
    yield effect
    for group in (effect.then, effect.win, effect.lose, effect.on_kill, effect.effects):
        for sub in group or ():
            yield from _walk_effect(sub)


def _modifier_effects(rule: ModifierSpec) -> Iterator[EffectSpec]:
    for effect in rule.change.on_hit_effects or ():
        yield from _walk_effect(effect)


def skill_effect_specs(skill: SkillDef) -> tuple[EffectSpec, ...]:
    """技能所有層級的效果（含 ``then``、賭注分支、擊殺時效果、區域效果、複合第二段與修正規則的
    命中後效果）。"""
    found: list[EffectSpec] = []
    for effect in skill.effects:
        found.extend(_walk_effect(effect))
    if skill.followup is not None:
        for effect in skill.followup.effects:
            found.extend(_walk_effect(effect))
    for rule in skill.modifiers:
        found.extend(_modifier_effects(rule))
    return tuple(found)


def skill_condition_specs(skill: SkillDef) -> tuple[ConditionSpec, ...]:
    """技能所有層級的條件（技能、效果、複合第二段與修正規則）。"""
    return _facts_of(skill).conditions


@dataclass(frozen=True, slots=True)
class _Facts:
    """推導用的事實：技能（或組到一半的草稿）上的效果、條件、觸發、形狀與修正規則。"""

    effects: tuple[EffectSpec, ...] = ()
    conditions: tuple[ConditionSpec, ...] = ()
    trigger: TriggerSpec | None = None
    shape: str | None = None
    modifiers: tuple[ModifierSpec, ...] = ()
    weapon_req: str | None = None
    category: str | None = None


def _facts_of(skill: SkillDef) -> _Facts:
    effects = skill_effect_specs(skill)
    conditions: list[ConditionSpec] = []
    if skill.condition is not None:
        conditions.append(skill.condition)
    if skill.followup is not None and skill.followup.condition is not None:
        conditions.append(skill.followup.condition)
    conditions.extend(e.condition for e in effects if e.condition is not None)
    conditions.extend(r.condition for r in skill.modifiers if r.condition is not None)
    return _Facts(
        effects=effects,
        conditions=tuple(conditions),
        trigger=skill.trigger,
        shape=skill.shape.type,
        modifiers=skill.modifiers,
        weapon_req=skill.weapon_req,
        category=skill.category,
    )


def _params_match(rule: KeywordRule, source: object) -> bool:
    """規則的每個參數都等於來源的同名欄位（修正規則的 ``add_element`` 以 ``element`` 比對）。"""
    return all(
        _same(getattr(source, name, None) or getattr(source, f"add_{name}", None), value)
        for name, value in rule.params().items()
    )


def _same(actual: object, expected: str) -> bool:
    if actual is None:
        return False
    return str(getattr(actual, "value", actual)) == expected


def _rule_matches(rule: KeywordRule, facts: _Facts) -> bool:
    if any(getattr(facts, name) != value for name, value in rule.filters().items()):
        return False
    kind, wanted = rule.source, rule.source_id
    if kind == "effect":
        return any(e.type == wanted and _params_match(rule, e) for e in facts.effects)
    if kind == "condition":
        return any(c.type == wanted and _params_match(rule, c) for c in facts.conditions)
    if kind == "trigger":
        trig = facts.trigger
        return trig is not None and trig.event == wanted and _params_match(rule, trig)
    if kind == "shape":
        return facts.shape == wanted
    return any(_change_matches(rule, r) for r in facts.modifiers)


def _change_matches(rule: KeywordRule, modifier: ModifierSpec) -> bool:
    """修正規則的改變種類與參數相符；``applies_to`` 參數看修正規則的套用對象旗標。"""
    if modifier.change.kind != rule.source_id:
        return False
    applies = rule.applies_to
    if applies is not None and not getattr(modifier.applies_to, applies):
        return False
    if rule.unconditional and modifier.condition is not None:
        return False
    plain = rule.model_copy(update={"applies_to": None, "unconditional": None})
    return _params_match(plain, modifier.change)


def _derive(facts: _Facts, table: KeywordTable) -> SkillKeywords:
    makes: list[str] = []
    uses: list[str] = []
    for keyword in table.keywords:
        if any(_rule_matches(rule, facts) for rule in keyword.makes):
            makes.append(keyword.id)
        if any(_rule_matches(rule, facts) for rule in keyword.uses):
            uses.append(keyword.id)
    return SkillKeywords(tuple(makes), tuple(uses))


def derive_keywords(skill: SkillDef, table: KeywordTable) -> SkillKeywords:
    """``skill`` 製造與利用的關鍵字（純函式；依 ``table`` 的順序）。"""
    return _derive(_facts_of(skill), table)


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
    expanded = [sub for effect in effects for sub in _walk_effect(effect)]
    modifiers = _parsed_list(ModifierSpec, draft.get("modifiers"))
    for rule in modifiers:
        expanded.extend(_modifier_effects(rule))
    conditions = [c for c in (_parsed(ConditionSpec, draft.get("condition")),) if c is not None]
    conditions += [e.condition for e in expanded if e.condition is not None]
    conditions += [r.condition for r in modifiers if r.condition is not None]
    shape = _parsed(ShapeSpec, draft.get("shape"))
    facts = _Facts(
        effects=tuple(expanded),
        conditions=tuple(conditions),
        trigger=_parsed(TriggerSpec, draft.get("trigger")),
        shape=None if shape is None else shape.type,
        modifiers=tuple(modifiers),
        weapon_req=_text(draft.get("weapon_req")),
        category=_text(draft.get("category")),
    )
    return _derive(facts, table)


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
