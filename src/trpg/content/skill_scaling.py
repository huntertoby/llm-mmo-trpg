"""技能縮放屬性的允許範圍（Phase 3H-1、3H-7；``docs/design/06-技能.md`` 6.10、``07`` 7.2）。

- **武器技**（``category: weapon``）：**看手上武器的屬性**（3H-6，玩法決定 #45）——引擎不讀技能
  自己的 ``scaling_attr``。內建技能的欄位只當顯示提示，必須是某把同武器大類（``weapon_req``）、
  可裝備的武器的縮放屬性；產生器（隨機組合器、LLM 提議、工坊）一律設為 ``weapon_class_attrs`` 的
  武器大類主屬性。武器技 **不帶第二屬性**（3H-7；魔劍士方案 A 決定前）。
- **法術技**（``category: spell``）：依主題，**主題由效果推導**（3H-7，玩法 PM 2026-10-24）：
  依序看技能的效果（主要效果在前；複合技能接著看第二段），第一個帶有主題訊號的效果是 **主要
  效果**——訊號是效果的原語（``effect_types_any``）、元素（``elements_any``）、表面
  （``surfaces_any``）或狀態（``statuses_any``；``consume_status`` 的 ``then`` 一起看）。
  召喚物 **自帶** 的元素或灌注（召喚物武器）不算技能的元素主題（玩法 PM 2026-10-24）。
  主要效果符合的主題中，``spell_themes`` 順序第一個決定主屬性；同一個效果也符合組合主題的另一個
  主題時，可以看其中任一個。附帶效果一般不算；只有組合主題的 ``anywhere`` 主題（元素）可以由
  其他效果補上，例：聖水的主要效果是神聖傷害（感知），造水表面補上元素 → 感知或智力。
  **標籤只當輔助**：只有每個效果都沒有主題訊號時（物理傷害、拉扯、障礙、修正規則、規則改變…），才
  依標籤（``tags_any``／``tags_none``）判斷；標籤不能改掉效果推導出的主題。都不符合的屬於身體類，
  允許 ``body_attrs``。
- ``combos``：組合主題（玩法 PM 2026-10-23，06 6.10）。
- ``overrides``：個別技能的例外（要寫理由）；也適用於由它進化而來的技能（``provenance.parents``
  或 ``<id>_evo_`` 開頭的 ID）。

**允許範圍有順序**（:meth:`SkillScalingRules.scaling_range`）：主題的屬性在前、組合主題的另一個
屬性在後；身體類依 ``body_attrs``；例外依列出的順序。沒有主角屬性時（工坊、隨機組合器）取範圍
裡第一個（玩法 PM 2026-10-24 第 5 題）。

規則是資料（``content/skill_scaling.yaml``）；內建技能的載入檢查、驗證器（``scaling.range``）、
隨機組合器、候選、LLM 提議與工坊共用同一份。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, WeaponDef
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute, Element

__all__ = [
    "ScalingBasis",
    "ScalingFacts",
    "ScalingOverride",
    "ScalingTheme",
    "SkillScalingRules",
    "ThemeCombo",
    "scaling_problems",
    "weapon_attrs",
    "weapon_class_mismatches",
]


def _get(effect: Any, name: str) -> Any:
    """效果的欄位：:class:`~trpg.content.skills.EffectSpec` 或工坊草稿的 dict 都可以。"""
    if isinstance(effect, Mapping):
        return effect.get(name)
    return getattr(effect, name, None)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def _seq(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return tuple(value)
    return ()


@dataclass(frozen=True, slots=True)
class ScalingFacts:
    """判斷縮放範圍需要的技能資料（技能或工坊草稿都能轉成這個）。``effects`` 依序是技能本身的
    效果與複合技能第二段的效果。"""

    skill_id: str
    category: str
    weapon_req: str
    tags: frozenset[str]
    effects: tuple[Any, ...]
    parents: tuple[str, ...] = ()

    @classmethod
    def of_skill(cls, skill: SkillDef) -> ScalingFacts:
        followup = () if skill.followup is None else tuple(skill.followup.effects)
        return cls(
            skill_id=skill.id,
            category=skill.category,
            weapon_req=skill.weapon_req,
            tags=frozenset(skill.tags),
            effects=(*skill.effects, *followup),
            parents=tuple(skill.provenance.parents),
        )

    @classmethod
    def of_draft(cls, draft: Mapping[str, Any]) -> ScalingFacts:
        """工坊草稿（缺欄位時視為空）。"""
        followup = draft.get("followup")
        more = _seq(followup.get("effects")) if isinstance(followup, Mapping) else ()
        provenance = draft.get("provenance")
        parents = _seq(provenance.get("parents")) if isinstance(provenance, Mapping) else ()
        return cls(
            skill_id=str(draft.get("id") or ""),
            category=str(draft.get("category") or ""),
            weapon_req=str(draft.get("weapon_req") or ""),
            tags=frozenset(str(t) for t in _seq(draft.get("tags"))),
            effects=(*_seq(draft.get("effects")), *more),
            parents=tuple(str(p) for p in parents),
        )


class ScalingTheme(ContentModel):
    """一個法術主題。效果訊號（原語、元素、表面、狀態）決定主題；標籤（``tags_any``，且沒有
    ``tags_none``）只在每個效果都沒有訊號時才看。"""

    id: str = Field(pattern=ID_PATTERN)
    attr: Attribute
    label_zh: str = Field(min_length=1)
    tags_any: tuple[str, ...] = ()
    tags_none: tuple[str, ...] = ()
    effect_types_any: tuple[str, ...] = ()
    elements_any: tuple[Element, ...] = ()
    surfaces_any: tuple[str, ...] = ()
    statuses_any: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ScalingTheme:
        signals = (
            self.tags_any,
            self.effect_types_any,
            self.elements_any,
            self.surfaces_any,
            self.statuses_any,
        )
        if not any(signals):
            raise ValueError(f"主題 {self.id}：至少要有一種效果訊號或標籤")
        return self

    def matches_tags(self, tags: frozenset[str]) -> bool:
        """輔助：標籤符合（沒有任何效果訊號時才用）。"""
        if tags & set(self.tags_none):
            return False
        return bool(tags & set(self.tags_any))

    def matches_effect(self, effect: Any) -> bool:
        """一個效果（含 ``consume_status`` 的 ``then``）帶有這個主題的訊號。召喚物自帶的元素
        不算（``summon`` 效果本身沒有 ``element``）。"""
        if _text(_get(effect, "type")) in self.effect_types_any:
            return True
        element = _text(_get(effect, "element"))
        if element is not None and element in {e.value for e in self.elements_any}:
            return True
        if _text(_get(effect, "surface")) in self.surfaces_any:
            return True
        if _text(_get(effect, "status")) in self.statuses_any:
            return True
        return any(self.matches_effect(e) for e in _seq(_get(effect, "then")))


class ThemeCombo(ContentModel):
    """組合主題：主要效果同時符合 ``themes`` 的每一個時（只有標籤可看時則是標籤都符合），允許
    這些主題的屬性任選其一。``anywhere`` 裡的主題也可以由技能的其他效果符合（例：元素表面）。"""

    themes: tuple[str, ...] = Field(min_length=2)
    anywhere: tuple[str, ...] = ()
    reason_zh: str = Field(min_length=1)


class ScalingOverride(ContentModel):
    """個別技能的例外：這招允許的屬性（取代主題推導），並寫明理由。"""

    skill: str = Field(pattern=ID_PATTERN)
    attrs: tuple[Attribute, ...] = Field(min_length=1)
    reason_zh: str = Field(min_length=1)

    def applies(self, facts: ScalingFacts) -> bool:
        """這招本身，或由它進化而來的技能。"""
        return (
            facts.skill_id == self.skill
            or facts.skill_id.startswith(f"{self.skill}_evo_")
            or self.skill in facts.parents
        )


@dataclass(frozen=True, slots=True)
class ScalingBasis:
    """允許範圍與它的由來（給驗證器與工坊寫中文原因）。

    ``source``：``override``（例外）、``weapon``（武器技）、``effect``（主要效果推導）、
    ``tags``（沒有效果訊號，看標籤）、``body``（身體類）。``effect_index`` 是主要效果在
    :attr:`ScalingFacts.effects` 的位置；``themes`` 是決定範圍的主題 ID（依主題順序）。"""

    attrs: tuple[Attribute, ...]
    source: str
    themes: tuple[str, ...] = ()
    effect_index: int | None = None
    reason_zh: str = ""


class SkillScalingRules(ContentModel):
    """``content/skill_scaling.yaml``。"""

    spell_themes: tuple[ScalingTheme, ...] = Field(min_length=1)
    body_attrs: tuple[Attribute, ...] = Field(min_length=1)
    """沒有任何法術主題的法術技（物理、裝備動作等）允許的屬性。"""
    weapon_class_attrs: Mapping[str, Attribute] = Field(
        default_factory=lambda: {"melee": Attribute.STR, "ranged": Attribute.DEX}
    )
    """武器技的武器大類主屬性（3H-6）：產生器與驗證器給武器技的 ``scaling_attr``。"""
    combos: tuple[ThemeCombo, ...] = ()
    overrides: tuple[ScalingOverride, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> SkillScalingRules:
        if "melee" not in self.weapon_class_attrs:
            raise ValueError("weapon_class_attrs 必須有 melee（未列出的大類取近戰的）")
        known = {t.id for t in self.spell_themes}
        for combo in self.combos:
            unknown = sorted((set(combo.themes) | set(combo.anywhere)) - known)
            if unknown:
                raise ValueError(f"組合主題引用了未知的主題：{', '.join(unknown)}")
        for label, ids in (
            ("主題", [t.id for t in self.spell_themes]),
            ("例外", [o.skill for o in self.overrides]),
        ):
            dup = sorted(k for k, n in Counter(ids).items() if n > 1)
            if dup:
                raise ValueError(f"縮放屬性{label}重複：{', '.join(dup)}")
        return self

    def weapon_class_attr(self, weapon_req: str) -> Attribute:
        """武器技所需武器大類的主屬性（3H-6）；``any`` 與未列出的大類取近戰的。"""
        return self.weapon_class_attrs.get(weapon_req, self.weapon_class_attrs["melee"])

    def theme(self, theme_id: str) -> ScalingTheme:
        return next(t for t in self.spell_themes if t.id == theme_id)

    def _themed(
        self, matched: Sequence[ScalingTheme], elsewhere: frozenset[str] = frozenset()
    ) -> tuple[Attribute, ...]:
        """符合的主題（依主題順序）→ 範圍：第一個主題的屬性，加上組合主題的其他屬性。
        ``elsewhere`` 是其他效果符合的主題，只補組合主題的 ``anywhere``。"""
        ids = {t.id for t in matched}
        out = [matched[0].attr]
        for combo in self.combos:
            have = ids | (elsewhere & set(combo.anywhere))
            if matched[0].id in combo.themes and all(tid in have for tid in combo.themes):
                out += [self.theme(tid).attr for tid in combo.themes]
        return tuple(dict.fromkeys(out))

    def _main_effect(self, facts: ScalingFacts) -> tuple[int, list[ScalingTheme]] | None:
        for index, effect in enumerate(facts.effects):
            matched = [t for t in self.spell_themes if t.matches_effect(effect)]
            if matched:
                return index, matched
        return None

    def basis(
        self,
        skill: SkillDef | ScalingFacts,
        weapons: Mapping[str, WeaponDef] | Iterable[WeaponDef],
    ) -> ScalingBasis:
        """允許範圍（有順序）與由來；見模組說明。"""
        facts = skill if isinstance(skill, ScalingFacts) else ScalingFacts.of_skill(skill)
        override = next((o for o in self.overrides if o.applies(facts)), None)
        if override is not None:
            return ScalingBasis(override.attrs, "override", reason_zh=override.reason_zh)
        if facts.category == "weapon":
            first = self.weapon_class_attr(facts.weapon_req)
            rest = sorted(weapon_attrs(facts.weapon_req, weapons), key=list(Attribute).index)
            return ScalingBasis(tuple(dict.fromkeys([first, *rest])), "weapon")
        main = self._main_effect(facts)
        if main is not None:
            index, matched = main
            elsewhere = frozenset(
                t.id
                for i, effect in enumerate(facts.effects)
                if i != index
                for t in self.spell_themes
                if t.matches_effect(effect)
            )
            return ScalingBasis(
                self._themed(matched, elsewhere), "effect", tuple(t.id for t in matched), index
            )
        tagged = [t for t in self.spell_themes if t.matches_tags(facts.tags)]
        if tagged:
            return ScalingBasis(self._themed(tagged), "tags", tuple(t.id for t in tagged))
        return ScalingBasis(tuple(self.body_attrs), "body")

    def scaling_range(
        self,
        skill: SkillDef | ScalingFacts,
        weapons: Mapping[str, WeaponDef] | Iterable[WeaponDef],
    ) -> tuple[Attribute, ...]:
        """允許的縮放屬性（有順序：沒有主角屬性時取第一個）。"""
        return self.basis(skill, weapons).attrs

    def spell_theme(self, skill: SkillDef | ScalingFacts) -> ScalingTheme | None:
        """法術技的主題（主要效果推導；沒有效果訊號時看標籤）；身體類或例外為 ``None``。"""
        basis = self.basis(skill, ())
        if basis.source not in ("effect", "tags"):
            return None
        return self.theme(basis.themes[0])

    def allowed_attrs(
        self,
        skill: SkillDef | ScalingFacts,
        weapons: Mapping[str, WeaponDef] | Iterable[WeaponDef],
    ) -> frozenset[Attribute]:
        """這招技能可以用的縮放屬性集合（主屬性與法術技的第二屬性都限在這裡）。"""
        return frozenset(self.scaling_range(skill, weapons))


def weapon_attrs(
    weapon_req: str, weapons: Mapping[str, WeaponDef] | Iterable[WeaponDef]
) -> frozenset[Attribute]:
    """某武器需求（``melee``／``ranged``／``focus``／``any``）的武器技可用的屬性：
    玩家可裝備的武器（不含召喚物專用）的縮放屬性與第二縮放屬性。"""
    pool = weapons.values() if isinstance(weapons, Mapping) else weapons
    out: set[Attribute] = set()
    for w in pool:
        if w.summon_only or (weapon_req not in ("any", w.weapon_class)):
            continue
        out.add(w.scaling_attr)
        if w.secondary_scaling_attr is not None:
            out.add(w.secondary_scaling_attr)
    return frozenset(out)


def weapon_class_mismatches(rules: SkillScalingRules, skills: Mapping[str, SkillDef]) -> list[str]:
    """內建武器技中，``scaling_attr`` 或第二屬性和武器大類主屬性不一致的技能 ID（排序）。
    引擎不使用這個欄位（武器技看手上武器），只當顯示提示；清單供報告與測試用。"""
    return sorted(
        s.id
        for s in skills.values()
        if s.category == "weapon"
        and (
            s.scaling_attr != rules.weapon_class_attr(s.weapon_req)
            or s.secondary_scaling_attr is not None
        )
    )


def scaling_problems(
    rules: SkillScalingRules,
    skills: Mapping[str, SkillDef],
    weapons: Mapping[str, WeaponDef],
) -> list[str]:
    """內建技能的縮放屬性（含第二屬性）是否都在允許範圍內；回傳問題清單。"""
    problems: list[str] = []
    for req, attr in rules.weapon_class_attrs.items():
        if attr not in weapon_attrs(req, weapons):
            problems.append(f"武器大類 {req} 的主屬性 {attr.value} 不是該大類任何武器的縮放屬性")
    known = set(skills)
    problems += [
        f"例外引用了未知的技能：{o.skill}" for o in rules.overrides if o.skill not in known
    ]
    for sid in sorted(skills):
        skill = skills[sid]
        allowed = rules.scaling_range(skill, weapons)
        used = [skill.scaling_attr]
        if skill.secondary_scaling_attr is not None:
            used.append(skill.secondary_scaling_attr)
        bad = [a for a in used if a not in allowed]
        if bad:
            names = "、".join(a.value for a in allowed)
            problems.append(
                f"技能 {sid}：縮放屬性 {'、'.join(a.value for a in bad)} 不在允許範圍（{names}）"
            )
        if skill.category == "weapon" and skill.secondary_scaling_attr is not None:
            problems.append(f"技能 {sid}：武器技不帶第二縮放屬性（看手上武器）")
    return problems
