"""召喚物範本（Phase 3D-4a，``docs/design/06-技能.md`` 6.16 B）。

``content/units/summons/<id>.yaml`` 沿用單位範本 schema
（:class:`~trpg.content.battle.UnitTemplate`），必須寫 ``summon: true``。載入時連同武器一起放進
:class:`SummonTable`，再嵌入規則包（:class:`~trpg.content.library.Ruleset` 的 ``summons``），
讓重播不依賴當下的資料檔。
"""

from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, SummonLook, UnitTemplate, WeaponDef
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel

__all__ = [
    "SummonDef",
    "SummonLookEntry",
    "SummonLookTable",
    "SummonTable",
    "load_summon_looks",
    "summon_dpr",
]


class SummonDef(ContentModel):
    """一種召喚物：單位範本與它的武器。"""

    template: UnitTemplate
    weapon: WeaponDef

    @property
    def id(self) -> str:
        return self.template.id


class SummonTable(ContentModel):
    """全部召喚物範本（依 ID 排序）。"""

    summons: tuple[SummonDef, ...] = Field(default=())

    @model_validator(mode="after")
    def _check(self) -> SummonTable:
        ids = [s.id for s in self.summons]
        if len(set(ids)) != len(ids):
            raise ValueError("召喚物範本 ID 重複")
        bad = [s.id for s in self.summons if not s.template.summon]
        if bad:
            raise ValueError(f"召喚物範本必須寫 summon: true：{', '.join(bad)}")
        return self

    def by_id(self) -> dict[str, SummonDef]:
        return {s.id: s for s in self.summons}


def summon_dpr(summon: SummonDef) -> Fraction:
    """召喚物每輪的預估傷害（最簡單的近似，預算與 AI 共用）：武器骰平均 ＋ 固定傷害，
    每輪一次攻擊、不計命中率與屬性。"""
    dice = summon.weapon.dice
    return Fraction(dice.count * (dice.sides + 1), 2) + summon.weapon.flat


class SummonLookEntry(SummonLook):
    """外觀表的一列：外觀欄位加中文名。"""

    zh: str = Field(min_length=1)


class SummonLookTable(ContentModel):
    """``content/summon_looks.yaml``（Phase 3-33h1）：17 種召喚物的外觀表（不進規則包）。"""

    looks: dict[str, SummonLookEntry]

    @model_validator(mode="after")
    def _ids(self) -> SummonLookTable:
        bad = [i for i in self.looks if re.match(ID_PATTERN, i) is None]
        if bad:
            raise ValueError(f"外觀表的召喚物 ID 格式錯誤：{', '.join(bad)}")
        return self


def load_summon_looks(root: Path) -> SummonLookTable:
    """讀取 ``<root>/summon_looks.yaml``（找不到檔案時是 ``ContentError``）。"""
    return load_content_file(root / "summon_looks.yaml", SummonLookTable)
