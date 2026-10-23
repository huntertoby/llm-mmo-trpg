"""技能縮放屬性的允許範圍（Phase 3H-1；``docs/design/06-技能.md`` 6.10、``07-角色成長.md`` 7.2）。

- **武器技**（``category: weapon``）：**看手上武器的屬性**（3H-6，玩法決定 #45）——引擎不讀技能
  自己的 ``scaling_attr``。內建技能的欄位只當顯示提示，必須是某把同武器大類（``weapon_req``）、
  可裝備的武器的縮放屬性（含第二縮放屬性）；產生器（隨機組合器、LLM 提議、工坊）一律設為
  ``weapon_class_attrs`` 的武器大類主屬性。
- **法術技**（``category: spell``）：依主題，由 :class:`ScalingTheme` 依 **先後順序** 比對，第一個
  符合的主題決定屬性（智力＝元素傷害與互動；感知＝治療、護盾、輔助、偵測與標記；意志＝召喚、獻祭、
  詛咒、心智控制、暗影）；都不符合的（物理、裝備動作等）屬於身體類，允許 ``body_attrs``。
- ``combos``：組合主題（玩法 PM 2026-10-23，06 6.10）：法術同時符合組合裡的每個主題時，可以看其中
  任一個主題的屬性（例：元素＋意志主題＝智力或意志）；產生技能時取主角較高的那個。純元素仍只看智力。
- ``overrides``：個別技能的例外（要寫理由）。

規則是資料（``content/skill_scaling.yaml``），內建技能的檢查與之後的隨機組合器、LLM 提議（3H-3）
共用同一份。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, WeaponDef
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute

__all__ = [
    "ScalingOverride",
    "ScalingTheme",
    "SkillScalingRules",
    "ThemeCombo",
    "scaling_problems",
    "weapon_attrs",
    "weapon_class_mismatches",
]


class ScalingTheme(ContentModel):
    """一個法術主題：技能的標籤或效果類型符合任一個條件、且沒有 ``tags_none`` 的標籤時成立。"""

    id: str = Field(pattern=ID_PATTERN)
    attr: Attribute
    label_zh: str = Field(min_length=1)
    tags_any: tuple[str, ...] = ()
    tags_none: tuple[str, ...] = ()
    effect_types_any: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ScalingTheme:
        if not self.tags_any and not self.effect_types_any:
            raise ValueError(f"主題 {self.id}：tags_any 與 effect_types_any 至少要有一個")
        return self

    def matches(self, tags: frozenset[str], effect_types: frozenset[str]) -> bool:
        if tags & set(self.tags_none):
            return False
        return bool(tags & set(self.tags_any) or effect_types & set(self.effect_types_any))


class ThemeCombo(ContentModel):
    """組合主題：技能同時符合 ``themes`` 的每一個時，允許這些主題的屬性任選其一。"""

    themes: tuple[str, ...] = Field(min_length=2)
    reason_zh: str = Field(min_length=1)


class ScalingOverride(ContentModel):
    """個別技能的例外：這招允許的屬性（取代主題推導），並寫明理由。"""

    skill: str = Field(pattern=ID_PATTERN)
    attrs: tuple[Attribute, ...] = Field(min_length=1)
    reason_zh: str = Field(min_length=1)


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
            unknown = sorted(set(combo.themes) - known)
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

    def spell_theme(self, skill: SkillDef) -> ScalingTheme | None:
        """法術技的主題（依先後順序第一個符合的）；沒有時為 ``None``（身體類）。"""
        tags = frozenset(skill.tags)
        types = frozenset(str(getattr(e, "type", "")) for e in skill.effects)
        return next((t for t in self.spell_themes if t.matches(tags, types)), None)

    def allowed_attrs(
        self, skill: SkillDef, weapons: Mapping[str, WeaponDef] | Iterable[WeaponDef]
    ) -> frozenset[Attribute]:
        """這招技能可以用的縮放屬性集合（主屬性；雙屬性技能的第二屬性另外檢查同一集合）。"""
        override = next((o for o in self.overrides if o.skill == skill.id), None)
        if override is not None:
            return frozenset(override.attrs)
        if skill.category == "weapon":
            return weapon_attrs(skill.weapon_req, weapons)
        theme = self.spell_theme(skill)
        if theme is None:
            return frozenset(self.body_attrs)
        tags = frozenset(skill.tags)
        types = frozenset(str(getattr(e, "type", "")) for e in skill.effects)
        matched = {t.id: t for t in self.spell_themes if t.matches(tags, types)}
        allowed = {theme.attr}
        for combo in self.combos:
            if all(tid in matched for tid in combo.themes):
                allowed |= {matched[tid].attr for tid in combo.themes}
        return frozenset(allowed)

    def primary_attr(
        self, skill: SkillDef, weapons: Mapping[str, WeaponDef] | Iterable[WeaponDef]
    ) -> Attribute:
        """內建技能該指定的縮放屬性（法術依主題；沒有主題或武器技時取現值若合法，否則固定順序第一個）。"""
        allowed = self.allowed_attrs(skill, weapons)
        if skill.scaling_attr in allowed:
            return skill.scaling_attr
        return min(allowed, key=list(Attribute).index)


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
    引擎不再使用這個欄位（武器技看手上武器），只當顯示提示；清單供報告與測試用。"""
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
        allowed = rules.allowed_attrs(skill, weapons)
        used = [skill.scaling_attr]
        if skill.secondary_scaling_attr is not None:
            used.append(skill.secondary_scaling_attr)
        bad = [a for a in used if a not in allowed]
        if bad:
            names = "、".join(a.value for a in sorted(allowed, key=list(Attribute).index))
            problems.append(
                f"技能 {sid}：縮放屬性 {'、'.join(a.value for a in bad)} 不在允許範圍（{names}）"
            )
    return problems
