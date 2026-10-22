"""關鍵字推導的核心（純函式；Phase 3-24b1，``docs/design/06-技能.md`` 6.27.1）。

技能「製造」或「利用」哪些關鍵字，由原語、條件、觸發自動推導（推導表
``content/skill_keywords.yaml``）。只讀技能與推導表，沒有亂數、沒有時間。

放在 ``trpg.content``（而不是 ``trpg.skillgen``）是因為 Phase 3G-G2 的裝備詞條「技能強化」要在
戰鬥引擎裡依關鍵字選取技能，而 ``trpg.engine`` 不得匯入 ``trpg.skillgen``；
``trpg.skillgen.keywords`` 重新匯出這裡的名稱，其餘（技能池、草稿推導）仍在那邊。
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from trpg.content.skill_keywords import KeywordRule, KeywordTable
from trpg.content.skills import (
    ConditionSpec,
    EffectSpec,
    ModifierSpec,
    SkillDef,
    TriggerSpec,
    walk_effect,
)

__all__ = [
    "Facts",
    "SkillKeywords",
    "derive_from_facts",
    "derive_keywords",
    "modifier_effects",
    "skill_condition_specs",
    "skill_effect_specs",
    "walk_effect",
]


@dataclass(frozen=True, slots=True)
class SkillKeywords:
    """一個技能製造與利用的關鍵字 ID（依推導表的順序）。"""

    makes: tuple[str, ...] = ()
    uses: tuple[str, ...] = ()
    variant: tuple[str, ...] = ()
    """只由戰場變奏型態帶來的關鍵字（Phase 3-25a；``variant: true``，技能卡標「（特定地形）」）。
    它們也列在 ``makes``／``uses`` 裡。"""

    def all(self) -> tuple[str, ...]:
        """製造或利用的關鍵字（依推導表的順序，不重複）。"""
        return tuple(dict.fromkeys((*self.makes, *self.uses)))

    def __bool__(self) -> bool:
        return bool(self.makes or self.uses)


# ---------------------------------------------------------------------------
# 從技能收集「來源」
# ---------------------------------------------------------------------------


def modifier_effects(rule: ModifierSpec) -> Iterator[EffectSpec]:
    for effect in rule.change.on_hit_effects or ():
        yield from walk_effect(effect)


def skill_effect_specs(skill: SkillDef) -> tuple[EffectSpec, ...]:
    """技能所有層級的效果（含 ``then``、賭注分支、擊殺時效果、區域效果、複合第二段與修正規則的
    命中後效果）。"""
    return tuple(skill.iter_effects(include_followup=True, include_modifiers=True))


def skill_condition_specs(skill: SkillDef) -> tuple[ConditionSpec, ...]:
    """技能所有層級的條件（技能、效果、複合第二段與修正規則）。"""
    return facts_of(skill).conditions


@dataclass(frozen=True, slots=True)
class Facts:
    """推導用的事實：技能（或組到一半的草稿）上的效果、條件、觸發、形狀與修正規則。"""

    effects: tuple[EffectSpec, ...] = ()
    conditions: tuple[ConditionSpec, ...] = ()
    trigger: TriggerSpec | None = None
    shape: str | None = None
    modifiers: tuple[ModifierSpec, ...] = ()
    weapon_req: str | None = None
    category: str | None = None


def facts_of(skill: SkillDef) -> Facts:
    effects = skill_effect_specs(skill)
    conditions: list[ConditionSpec] = []
    if skill.condition is not None:
        conditions.append(skill.condition)
    if skill.followup is not None and skill.followup.condition is not None:
        conditions.append(skill.followup.condition)
    conditions.extend(e.condition for e in effects if e.condition is not None)
    conditions.extend(r.condition for r in skill.modifiers if r.condition is not None)
    return Facts(
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


def _rule_matches(rule: KeywordRule, facts: Facts) -> bool:
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


def derive_from_facts(
    facts: Facts, table: KeywordTable, *, exclusive_only: bool = False
) -> SkillKeywords:
    makes: list[str] = []
    uses: list[str] = []

    def hit(rules: Iterable[KeywordRule]) -> bool:
        return any(
            _rule_matches(rule, facts)
            for rule in rules
            if not exclusive_only or rule.grade == "exclusive"
        )

    for keyword in table.keywords:
        if hit(keyword.makes):
            makes.append(keyword.id)
        if hit(keyword.uses):
            uses.append(keyword.id)
    return SkillKeywords(tuple(makes), tuple(uses))


def derive_keywords(
    skill: SkillDef, table: KeywordTable, *, exclusive_only: bool = False
) -> SkillKeywords:
    """``skill`` 製造與利用的關鍵字（純函式；依 ``table`` 的順序）。``exclusive_only`` 只看專屬規則
    （``grade: exclusive``；開局技能池與候選產生器用，Phase 3-24b2 PM 決定）。

    帶戰場變奏的技能（Phase 3-25a，PM 決定 #8）看所有型態的聯集；只由變奏型態帶來的關鍵字另外
    列在 ``variant``。``exclusive_only``（開局技能池與候選產生器）只看基礎型態：只在特定地形才
    成立的關鍵字不讓技能進入該關鍵字的池（保守做法，見 Phase 3-25a 報告）。"""
    base = derive_from_facts(facts_of(skill), table, exclusive_only=exclusive_only)
    if not skill.variants or exclusive_only:
        return base
    found = [base]
    found += [
        derive_from_facts(facts_of(skill.variant_form(v.id)), table, exclusive_only=exclusive_only)
        for v in skill.variants
    ]
    makes = {k for f in found for k in f.makes}
    uses = {k for f in found for k in f.uses}
    own = set(base.all())
    order = [k.id for k in table.keywords]
    return SkillKeywords(
        makes=tuple(k for k in order if k in makes),
        uses=tuple(k for k in order if k in uses),
        variant=tuple(k for k in order if (k in makes or k in uses) and k not in own),
    )
