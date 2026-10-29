"""技能變奏：``VariantWhen``、``VariantSpec`` 與效果走訪。"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.constants import (
    _MAX_VARIANT_REPLACEMENTS,
    _VARIANT_REPLACEMENTS,
    VARIANT_CONDITIONS,
    VARIANT_TARGET_CONDITIONS,
)
from trpg.content.skills.effects import EffectSpec, ShapeSpec
from trpg.shared.types import Element


class VariantWhen(ContentModel):
    """變奏的條件：四種恰好填一種（PM 決定 #2）。

    - ``caster_surface``：施放者所在格的表面是其中之一（表面 id，必須在 ``surfaces.yaml``）；
    - ``caster_high_ground: true``：施放者所在格比目標點高至少 1 層；
    - ``caster_adjacent_blocker: true``：施放者八方向相鄰的格子有牆壁或 ``blocks_move`` 物件；
    - ``target_surface``：目標點的表面是其中之一。
    """

    caster_surface: tuple[str, ...] | None = None
    caster_high_ground: Literal[True] | None = None
    caster_adjacent_blocker: Literal[True] | None = None
    target_surface: tuple[str, ...] | None = None

    @model_validator(mode="after")
    def _check(self) -> VariantWhen:
        given = [name for name in VARIANT_CONDITIONS if getattr(self, name) is not None]
        if len(given) != 1:
            raise ValueError(
                f"變奏條件 when 必須恰好填一種（{'、'.join(VARIANT_CONDITIONS)}），"
                f"收到 {len(given)} 種"
            )
        for name in ("caster_surface", "target_surface"):
            ids = getattr(self, name)
            if ids is None:
                continue
            if not ids:
                raise ValueError(f"when.{name} 至少要列一種表面")
            bad = [i for i in ids if re.match(ID_PATTERN, i) is None]
            if bad or len(set(ids)) != len(ids):
                raise ValueError(f"when.{name} 必須是不重複的表面 id，收到 {', '.join(ids)}")
        return self

    @property
    def kind(self) -> str:
        """填了哪一種條件。"""
        return next(name for name in VARIANT_CONDITIONS if getattr(self, name) is not None)

    @property
    def target_dependent(self) -> bool:
        """條件依賴目標點（居高、目標格表面）。"""
        return self.kind in VARIANT_TARGET_CONDITIONS

    @property
    def surfaces(self) -> tuple[str, ...]:
        """條件引用的表面 id（沒有時為空）。"""
        return self.caster_surface or self.target_surface or ()


class VariantEffectSwap(ContentModel):
    """``replace_effect``：把第 ``index`` 個效果（從 0 起算）換成 ``effect``。"""

    index: int = Field(ge=0)
    effect: EffectSpec


def walk_effect(effect: EffectSpec) -> Iterator[EffectSpec]:
    """效果本身與巢狀的效果（``then``、``win``／``lose``、``on_kill``、zone 的 ``effects``）。"""
    yield effect
    for group in (effect.then, effect.win, effect.lose, effect.on_kill, effect.effects):
        for sub in group or ():
            yield from walk_effect(sub)


class VariantSpec(ContentModel):
    """技能的一個戰場變奏（Phase 3-25a，06 6.24；PM 決定 #1）：條件 ``when`` 成立時，施放的是把
    替換內容套上去的型態（:meth:`SkillDef.variant_form`）。

    替換內容填 1～2 項：``shape``（整個換掉）、``range_delta``（射程 ±，結果至少 1；形狀要有數字
    射程）、``element``（換掉所有傷害效果的元素）、``add_effect``（加一個附帶效果）、
    ``replace_effect``（換掉一個附帶效果；不可換掉主傷害或唯一的效果）。AP、冷卻、代價、kind 與
    骨架不能改（沒有這些欄位）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    """型態名，例如「水中貫穿」。"""
    when: VariantWhen
    shape: ShapeSpec | None = None
    range_delta: int | None = None
    element: Element | None = None
    add_effect: EffectSpec | None = None
    replace_effect: VariantEffectSwap | None = None

    @model_validator(mode="after")
    def _check(self) -> VariantSpec:
        count = len(self.replacements)
        if not 1 <= count <= _MAX_VARIANT_REPLACEMENTS:
            raise ValueError(
                f"變奏 {self.id} 的替換內容必須填 1～2 項"
                f"（{'、'.join(_VARIANT_REPLACEMENTS)}），收到 {count} 項"
            )
        if self.range_delta == 0:
            raise ValueError(f"變奏 {self.id} 的 range_delta 不可為 0")
        return self

    @property
    def replacements(self) -> tuple[str, ...]:
        """填了的替換欄位（依 :data:`_VARIANT_REPLACEMENTS` 的順序）。"""
        return tuple(name for name in _VARIANT_REPLACEMENTS if getattr(self, name) is not None)
