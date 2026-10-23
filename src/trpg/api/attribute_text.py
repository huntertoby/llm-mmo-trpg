"""建議屬性與「這個屬性影響你的哪些招」（Phase 3H-3，``docs/design/07-角色成長.md`` 7.2；#44 原則：
說明文字一律由程式依規則與資料產生）。

- :func:`attribute_affects`：每個屬性影響的東西——武器（普攻吃武器的縮放屬性）與技能（縮放屬性與
  第二縮放屬性；武器技看手上武器，3H-6，所以算在武器的屬性上）。
- :func:`attribute_suggestion`：開局建議的主屬性＝起始技能最常用的縮放屬性（沒有技能時為武器的），
  和「自動配點」同一個規則（:func:`trpg.roguelite.start.primary_attribute`）。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from trpg.api.run_schemas import AttributeAffectsOut, AttributeSuggestionOut
from trpg.content.battle import WeaponDef
from trpg.content.skills import SkillDef
from trpg.roguelite.start import primary_attribute
from trpg.shared.types import Attribute

__all__ = ["attribute_affects", "attribute_suggestion"]

_MAX_LISTED = 6


def _weapon_attrs(weapon: WeaponDef | None) -> tuple[Attribute, ...]:
    if weapon is None:
        return ()
    if weapon.secondary_scaling_attr is None:
        return (weapon.scaling_attr,)
    return (weapon.scaling_attr, weapon.secondary_scaling_attr)


def _skill_attrs(skill: SkillDef, weapon: WeaponDef | None) -> tuple[Attribute | None, ...]:
    """技能吃的屬性：武器技看手上武器（3H-6），其他是技能自己的縮放屬性與第二縮放屬性。"""
    if skill.category == "weapon" and weapon is not None:
        return _weapon_attrs(weapon)
    return (skill.scaling_attr, skill.secondary_scaling_attr)


def _weapon_line(weapon: WeaponDef) -> str:
    return f"{weapon.name_zh}的普攻"


def attribute_affects(
    skills: Sequence[SkillDef], weapon: WeaponDef | None
) -> tuple[AttributeAffectsOut, ...]:
    """六屬性各自影響的武器與技能（依六屬性順序；技能依傳入順序）。沒有影響任何東西的屬性
    ``lines_zh`` 為空（前端不顯示）。"""
    out: list[AttributeAffectsOut] = []
    for attr in Attribute:
        lines: list[str] = []
        if weapon is not None and attr in _weapon_attrs(weapon):
            lines.append(_weapon_line(weapon))
        lines.extend(s.name_zh for s in skills if attr in _skill_attrs(s, weapon))
        out.append(AttributeAffectsOut(attr=attr, lines_zh=tuple(lines)))
    return tuple(out)


def _listed(names: Sequence[str]) -> str:
    shown = "、".join(names[:_MAX_LISTED])
    return shown if len(names) <= _MAX_LISTED else f"{shown}等 {len(names)} 招"


def attribute_suggestion(
    skills: Sequence[SkillDef], weapon: WeaponDef | None
) -> AttributeSuggestionOut | None:
    """建議的主屬性與原因（中文，由技能與武器產生）；沒有武器也沒有技能時為 ``None``。"""
    if not skills and weapon is None:
        return None
    fallback = weapon.scaling_attr if weapon is not None else Attribute.STR
    attr = primary_attribute(skills, fallback)
    name = attr.display_name
    users = [s.name_zh for s in skills if attr in _skill_attrs(s, weapon)]
    parts: list[str] = []
    if users:
        parts.append(f"你的起始技能 {_listed(users)} 吃{name}")
    if weapon is not None and attr in _weapon_attrs(weapon):
        parts.append(
            f"{_weapon_line(weapon)}也吃{name}" if users else f"{_weapon_line(weapon)}吃{name}"
        )
    counts = Counter(a for s in skills for a in _skill_attrs(s, weapon)[:1] if a is not None)
    others = [a for a in Attribute if a is not attr and counts[a] > 0]
    if others:
        parts.append(f"其他招吃{'、'.join(a.display_name for a in others)}，可當副屬性")
    return AttributeSuggestionOut(attr=attr, reason_zh="；".join(parts) or f"武器吃{name}")
