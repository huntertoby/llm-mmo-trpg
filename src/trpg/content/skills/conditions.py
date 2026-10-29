"""條件的 schema 與文字化：``ConditionDef``、``ConditionTable``、``ConditionSpec``。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.forms import FormCategory
from trpg.content.schemas import ContentModel
from trpg.content.skill_tags import UNKNOWN_TAG_TEXT
from trpg.content.skills.constants import (
    _PLAIN_CONDITION_TEXT,
    FORM_CATEGORY_TEXT,
    REQUIRED_CONDITIONS,
    _unique,
)
from trpg.content.skills.primitives import ConditionDef
from trpg.shared.types import Element, Surface, rune_name


class ConditionTable(ContentModel):
    """``content/skill_conditions.yaml``。"""

    conditions: tuple[ConditionDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> ConditionTable:
        _unique((c.id for c in self.conditions), "條件")
        ids = {c.id for c in self.conditions}
        missing = [c for c in REQUIRED_CONDITIONS if c not in ids]
        if missing:
            raise ValueError(f"缺少引擎實作的條件：{', '.join(missing)}")
        unknown = sorted(ids - set(REQUIRED_CONDITIONS))
        if unknown:
            raise ValueError(f"引擎尚未實作的條件：{', '.join(unknown)}")
        return self

    def by_id(self) -> dict[str, ConditionDef]:
        return {c.id: c for c in self.conditions}

    def summary(self) -> str:
        return f"{len(self.conditions)} 種條件"


class ConditionSpec(ContentModel):
    """技能或效果上的條件：``type`` 加上該條件的參數（範圍見 ``skill_conditions.yaml``）。"""

    type: str = Field(pattern=ID_PATTERN)
    permille: int | None = None
    surface: Surface | None = None
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    """``cast_tag_this_turn`` 專用（Phase 3D-1）：本回合施放過的技能標籤；``on_own_rune`` 的符文標籤
    篩選（Phase 3-23）。"""
    element: Element | None = None
    """``on_own_rune`` 專用（Phase 3-23）：符文元素篩選（省略＝任何符文）。"""
    weapon: str | None = Field(default=None, pattern=ID_PATTERN)
    """``wielding_weapon`` 專用（Phase 3I-5，6.10 #50）：要手持的武器或副手 ID
    （``weapons.yaml``、``offhands.yaml``）。"""
    form_category: FormCategory | None = None
    """``in_form`` 專用（Phase 3J-3，6.30）：限定形態類別（物理／心智）；省略＝任何形態。"""
    any_of: tuple[ConditionSpec, ...] | None = Field(default=None, min_length=1, max_length=2)
    """真正的「或」（Phase 3W-2b）：``type`` 的條件成立，**或** ``any_of`` 裡任何一個成立（最多再
    2 個，不可再巢狀）。預算用其中最寬鬆的倍率，最低稀有度取最高的那個；只有技能與修正規則的條件
    可以用（裝備詞條的條件不行）。"""

    @model_validator(mode="after")
    def _check_any_of(self) -> ConditionSpec:
        if self.any_of is not None and any(c.any_of is not None for c in self.any_of):
            raise ValueError("any_of 裡的條件不能再有 any_of")
        return self

    def alternatives(self) -> tuple[ConditionSpec, ...]:
        """所有「或」的分支（本條件自己去掉 ``any_of`` 當第一個，其後是 ``any_of``）。"""
        if self.any_of is None:
            return (self,)
        return (self.model_copy(update={"any_of": None}), *self.any_of)

    def param_values(self) -> dict[str, Any]:
        """已填寫的參數（依名稱排序）。"""
        names = ("element", "form_category", "permille", "status", "surface", "tag", "weapon")
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}


def _rune_condition_text(
    condition: ConditionSpec, tag_runes: Mapping[str, str] | None = None
) -> str:
    """``on_own_rune`` 的一句話（Phase 3-23）：可帶元素或標籤篩選。"""
    if condition.element is None and condition.tag is None:
        return "目標站在自己的符文上"
    return f"目標站在自己的{rune_name(condition.element, condition.tag, tag_runes)}上"


def _unknown_tag(_tag: str) -> str:
    return UNKNOWN_TAG_TEXT


def condition_text(
    condition: ConditionSpec,
    *,
    status_name: Callable[[str], str] = str,
    surface_name: Callable[[Surface], str] = lambda surface: surface.value,
    tag_name: Callable[[str], str] = _unknown_tag,
    tag_runes: Mapping[str, str] | None = None,
    weapon_name: Callable[[str], str] = str,
) -> str:
    """條件的一句話（繁體中文），例如「目標血量低於 40%」。有 ``any_of`` 時用「，或」連接。"""
    return "，或".join(
        _single_condition_text(
            part,
            status_name=status_name,
            surface_name=surface_name,
            tag_name=tag_name,
            tag_runes=tag_runes,
            weapon_name=weapon_name,
        )
        for part in condition.alternatives()
    )


def _single_condition_text(
    condition: ConditionSpec,
    *,
    status_name: Callable[[str], str],
    surface_name: Callable[[Surface], str],
    tag_name: Callable[[str], str],
    tag_runes: Mapping[str, str] | None,
    weapon_name: Callable[[str], str],
) -> str:
    kind = condition.type
    if kind in ("target_hp_below", "self_hp_below") and condition.permille is not None:
        who = "目標" if kind == "target_hp_below" else "自身"
        return f"{who}血量低於 {condition.permille / 10:g}%"
    if kind == "height_advantage":
        return "居高臨下"
    if kind == "target_on_surface" and condition.surface is not None:
        return f"目標站在「{surface_name(condition.surface)}」表面上"
    if kind == "target_has_status" and condition.status is not None:
        return f"目標帶有狀態「{status_name(condition.status)}」"
    if kind == "cast_tag_this_turn" and condition.tag is not None:
        return f"本回合已施放過帶「{tag_name(condition.tag)}」標籤的技能"
    plain = _PLAIN_CONDITION_TEXT.get(kind)
    if kind == "in_form" and condition.form_category is not None:
        plain = f"你在{FORM_CATEGORY_TEXT[condition.form_category]}形態中"
    if plain is None and kind == "on_own_rune":
        plain = _rune_condition_text(condition, tag_runes)
    if plain is None and kind == "wielding_weapon" and condition.weapon is not None:
        plain = f"手持{weapon_name(condition.weapon)}時"  # 3I-5
    if plain is None and kind == "wielding_weapon":
        plain = "手持指定的武器時"  # 3-55：沒帶武器 ID 時也不露出英文代號
    return plain or kind
