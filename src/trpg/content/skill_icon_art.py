"""Q 版技能圖示的推導表（Phase QI-2a；資料檔 ``content/skill_icon_art.yaml``）。

技能 → 主圖畫哪個道具、怎麼出手、效果記號與染色。推導規則在
:mod:`trpg.narrative.skill_icon_art`；這裡只是規則查的表（美術參考實作
``docs/art/sample/tools/qskills_derive.py`` 的同名常數，逐筆照抄、順序不變）。

只影響圖示：不嵌入規則包、不進引擎。表由美術 PM 維護（06 6.36）。

代碼是封閉集合（拼錯直接報錯）：出手 :data:`ICON_MOTIONS`、記號 :data:`ICON_ACTS`（另可寫
``terrain``，載入後換成 ``surface``＋染色 ``stone``）、染色 :data:`ICON_TINTS`。跨檔參照（狀態、
原語、表面、召喚物、武器 ID）不在這裡擋：參考表裡可以有目前內容沒有的 ID（由測試列出）。
"""

from __future__ import annotations

import re
from typing import Any, Literal, get_args

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel, duplicates

__all__ = [
    "ICON_ACTS",
    "ICON_MOTIONS",
    "ICON_TINTS",
    "ActionRow",
    "IconAct",
    "IconArtTable",
    "IconMotion",
    "IconTint",
    "KeyTint",
    "ShapeMotion",
    "SummonGroup",
    "TagProp",
    "WeaponLook",
    "WordRow",
]

type IconMotion = Literal[
    "swing", "thrust", "sweep", "spin", "shot", "area", "chain", "place", "aura"
]
"""出手 9 種（``qIconsSkills.js`` 的 ``MOTION``）。"""

type IconAct = Literal[
    "modify",
    "builder",
    "transform",
    "summon",
    "detonate",
    "trap",
    "step",
    "dash",
    "pull",
    "push",
    "knockdown",
    "heal",
    "shield",
    "dot",
    "bind",
    "slow",
    "mark",
    "curse",
    "buff",
    "surface",
    "finisher",
    "combo",
    "hit",
]
"""效果記號 23 種（``qIconsSkills.js`` 的 ``ACT``，不含舊代碼 ``terrain``）。"""

type IconTint = Literal[
    "fire",
    "ice",
    "lightning",
    "poison",
    "holy",
    "shadow",
    "wind",
    "earth",
    "water",
    "arcane",
    "blood",
    "steel",
    "impact",
    "stone",
]
"""染色 13 種＋``stone``（``qIconsSkills.js`` 的 ``TINT``）。"""

ICON_MOTIONS: tuple[str, ...] = get_args(IconMotion.__value__)
ICON_ACTS: tuple[str, ...] = get_args(IconAct.__value__)
ICON_TINTS: tuple[str, ...] = get_args(IconTint.__value__)

_ID = r"^[a-z][a-z0-9_]*$"
_LOOK = r"^[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_]*)?$"
_PROP = r"^(?:none|(?:w|el|summon|form):[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_]*)?)$"
"""道具代碼：``none`` 或 ``前綴:種類[/形制]``，前綴只有 ``w``、``el``、``summon``、``form``。"""


class WeaponLook(ContentModel):
    """``wielding_weapon`` 的武器 id → 道具種類／形制。"""

    weapon: str = Field(pattern=_ID)
    look: str = Field(pattern=_LOOK)


class WordRow(ContentModel):
    """名稱關鍵字：``name_zh`` 含其中一個字 → 武器種類。"""

    words: tuple[str, ...] = Field(min_length=1)
    kind: str = Field(pattern=_ID)


class SummonGroup(ContentModel):
    """召喚物（``unit`` 去掉 ``summon_``）→ 道具組。"""

    unit: str = Field(pattern=_ID)
    group: str = Field(pattern=_ID)


class TagProp(ContentModel):
    """修正技 ``applies_to.skill_tags`` 的標籤 → 道具。"""

    tag: str = Field(pattern=_ID)
    prop: str = Field(pattern=_PROP)


class KeyTint(ContentModel):
    """某個代碼（召喚物、狀態、條件、表面、修正鍵）→ 染色。"""

    key: str = Field(pattern=_ID)
    tint: IconTint


class ActionRow(ContentModel):
    """效果原語的一組 → 記號；``tint`` 有值時固定用這個染色（只有 ``terrain`` 換算來的那列）。"""

    effects: tuple[str, ...] = Field(min_length=1)
    act: IconAct
    tint: IconTint | None = None

    @model_validator(mode="before")
    @classmethod
    def _terrain(cls, data: Any) -> Any:
        """舊代碼 ``terrain`` → ``surface``＋``stone``（需求 3.3 第 15～20 列；參考實作同）。"""
        if isinstance(data, dict) and data.get("act") == "terrain":
            return {**data, "act": "surface", "tint": data.get("tint") or "stone"}
        return data


class ShapeMotion(ContentModel):
    """形狀 → 出手；``shape`` 為 ``None`` ＝ 技能沒有形狀。"""

    shape: str | None = Field(default=None, pattern=_ID)
    motion: IconMotion


def _dup(label: str, values: list[str]) -> list[str]:
    found = duplicates(values)
    return [f"{label} 重複：{', '.join(found)}"] if found else []


class IconArtTable(ContentModel):
    """``content/skill_icon_art.yaml``。"""

    weapon_look: tuple[WeaponLook, ...] = ()
    melee_words: tuple[WordRow, ...] = ()
    ranged_words: tuple[WordRow, ...] = ()
    thrust_props: tuple[str, ...] = ()
    ranged_kinds: tuple[str, ...] = ()
    summon_group: tuple[SummonGroup, ...] = ()
    summon_tint: tuple[KeyTint, ...] = ()
    mod_tag_prop: tuple[TagProp, ...] = ()
    mod_tint: tuple[KeyTint, ...] = ()
    dot: tuple[KeyTint, ...] = ()
    bind: tuple[KeyTint, ...] = ()
    curse: tuple[KeyTint, ...] = ()
    status_tint: tuple[KeyTint, ...] = ()
    cond_tint: tuple[KeyTint, ...] = ()
    surface_tint: tuple[KeyTint, ...] = ()
    effect_action: tuple[ActionRow, ...] = ()
    late_action: tuple[ActionRow, ...] = ()
    shape_motion: tuple[ShapeMotion, ...] = ()
    needs_prop: tuple[IconAct, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> IconArtTable:
        problems = [
            f"thrust_props 的 {p!r} 不是武器道具（w:種類）"
            for p in self.thrust_props
            if not p.startswith("w:") or not _matches(_LOOK, p[2:])
        ]
        problems += [
            f"ranged_kinds 的 {k!r} 不是種類代碼" for k in self.ranged_kinds if not _matches(_ID, k)
        ]
        problems += _dup("weapon_look 的 weapon", [r.weapon for r in self.weapon_look])
        for label, rows in (("melee_words", self.melee_words), ("ranged_words", self.ranged_words)):
            problems += _dup(f"{label} 的字", [w for r in rows for w in r.words])
        problems += _dup("thrust_props", list(self.thrust_props))
        problems += _dup("ranged_kinds", list(self.ranged_kinds))
        problems += _dup("summon_group 的 unit", [r.unit for r in self.summon_group])
        problems += _dup("mod_tag_prop 的 tag", [r.tag for r in self.mod_tag_prop])
        for label, tints in self._tint_tables():
            problems += _dup(f"{label} 的 key", [r.key for r in tints])
        problems += _dup(
            "狀態分類（dot／bind／curse）", [r.key for r in (*self.dot, *self.bind, *self.curse)]
        )
        actions = (*self.effect_action, *self.late_action)
        problems += _dup(
            "effect_action／late_action 的原語", [e for r in actions for e in r.effects]
        )
        problems += _dup("shape_motion 的 shape", [str(r.shape) for r in self.shape_motion])
        problems += _dup("needs_prop", list(self.needs_prop))
        if problems:
            raise ValueError("；".join(problems))
        return self

    def _tint_tables(self) -> tuple[tuple[str, tuple[KeyTint, ...]], ...]:
        return (
            ("summon_tint", self.summon_tint),
            ("mod_tint", self.mod_tint),
            ("dot", self.dot),
            ("bind", self.bind),
            ("curse", self.curse),
            ("status_tint", self.status_tint),
            ("cond_tint", self.cond_tint),
            ("surface_tint", self.surface_tint),
        )

    def summary(self) -> str:
        actions = len(self.effect_action) + len(self.late_action)
        return f"技能圖示推導表：{actions} 組效果記號、{len(self.shape_motion)} 種形狀出手"


def _matches(pattern: str, value: str) -> bool:
    return re.fullmatch(pattern, value) is not None
