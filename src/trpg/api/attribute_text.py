"""建議屬性與「這個屬性影響你的哪些招」（Phase 3H-3，``docs/design/07-角色成長.md`` 7.2；#44 原則：
說明文字一律由程式依規則與資料產生）。

- :func:`attribute_affects`：每個屬性影響的東西——武器（普攻吃武器的縮放屬性）與技能（縮放屬性與
  第二縮放屬性；武器技看手上武器，3H-6，所以算在武器的屬性上）。
- :func:`attribute_suggestion`：開局建議的主屬性＝起始技能最常用的縮放屬性（沒有技能時為武器的），
  和「自動配點」同一個規則（:func:`trpg.roguelite.start.primary_attribute`）。
- :func:`route_hint`：關鍵字與屬性不搭的提示（BAL-19g，06 6.27.3，#110）：選的關鍵字大多只有法術
  （或只有武器技）、而最高屬性對不上時提示。只提示、不擋。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Literal

from trpg.api.run_schemas import AttributeAffectsOut, AttributeSuggestionOut, RouteHintOut
from trpg.content.battle import WeaponDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, weapon_problem
from trpg.roguelite.start import primary_attribute
from trpg.shared.types import Attribute
from trpg.skillgen.candidates import follows_attr
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.validate import minimum_tier

__all__ = ["attribute_affects", "attribute_suggestion", "keyword_supply", "route_hint"]

_MIND = (Attribute.INT, Attribute.WIS, Attribute.WIL)
_EARLY_TIER = 2
"""前兩次升級用到的角色階級上限（候選池的「早期」範圍）。"""

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
        return (*_weapon_attrs(weapon), skill.secondary_scaling_attr)  # 3I-3：武器技的心智第二屬性
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


def keyword_supply(
    library: ContentLibrary, weapon: WeaponDef, keywords: Sequence[str]
) -> tuple[SkillDef, ...]:
    """選的關鍵字前期拿得到的技能（BAL-19g）：手寫技能裡 1 階、非傳說、不是形態技、角色
    :data:`_EARLY_TIER` 階以內可用、這把武器能用、（專屬規則）帶任一個選的關鍵字；依 ID 排序、
    不重複。"""
    wanted = set(keywords)
    held = {weapon.id: weapon.name_zh}
    found: list[SkillDef] = []
    for skill_id in sorted(library.skills):
        skill = library.skills[skill_id]
        if skill.tier != 1 or skill.rarity == "legendary" or skill.form_id is not None:
            continue
        if weapon_problem(skill, weapon.weapon_class, held) is not None:
            continue
        if not wanted & set(derive_keywords(skill, library.keywords, exclusive_only=True).all()):
            continue
        if minimum_tier(skill, library) <= _EARLY_TIER:
            found.append(skill)
    return tuple(found)


def _attr_list(attrs: Sequence[Attribute]) -> str:
    names = "、".join(a.display_name for a in attrs)
    return f"心智屬性（{names}）" if all(a in _MIND for a in attrs) else names


def route_hint(
    library: ContentLibrary, weapon: WeaponDef | None, keywords: Sequence[str]
) -> RouteHintOut | None:
    """關鍵字與屬性不搭的提示（BAL-19g，06 6.27.3，#110）。

    依選的關鍵字前期拿得到的技能（:func:`keyword_supply`）算每個屬性有幾招跟主路線
    （:func:`~trpg.skillgen.candidates.follows_attr`，武器技看武器）：至少一半跟上的屬性是
    ``fits``（都不到一半時取最多的）。前端在配點後的最高屬性不在 ``fits`` 時顯示 ``text_zh``；
    只提示、不擋。跟上 ``fits`` 的技能裡法術不少於武器技算「多半是法術」，否則「多半是武器技」；
    法器拿不到武器技，所以法器的另一個建議是「選其他關鍵字」。沒有武器、沒選關鍵字或湊不到技能
    時為 ``None``。"""
    if weapon is None or not keywords:
        return None
    supply = keyword_supply(library, weapon, keywords)
    if not supply:
        return None
    weapon_attrs = _weapon_attrs(weapon)
    follow = {a: sum(follows_attr(s, a, weapon_attrs) for s in supply) for a in Attribute}
    fits = tuple(a for a in Attribute if 2 * follow[a] >= len(supply))
    if not fits:
        best = max(follow.values())
        fits = tuple(a for a in Attribute if follow[a] == best and best > 0)
    if not fits:
        return None
    on_route = [s for s in supply if any(follows_attr(s, a, weapon_attrs) for a in fits)]
    spells = sum(1 for s in on_route if s.category != "weapon")
    lean: Literal["spell", "weapon"] = "spell" if 2 * spells >= len(on_route) else "weapon"
    if lean == "weapon":
        other = "有法術的關鍵字"
    else:
        other = "其他關鍵字" if weapon.weapon_class == "focus" else "有武器技的關鍵字"
    kind = "法術" if lean == "spell" else "武器技"
    text = f"你選的關鍵字多半是{kind}，建議配一些點到{_attr_list(fits)}，或選{other}"
    return RouteHintOut(lean=lean, fits=fits, text_zh=text)
