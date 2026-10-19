"""召喚物範本（Phase 3D-4a，``docs/design/06-技能.md`` 6.16 B）。

``content/units/summons/<id>.yaml`` 沿用單位範本 schema
（:class:`~trpg.content.battle.UnitTemplate`），必須寫 ``summon: true``。載入時連同武器一起放進
:class:`SummonTable`，再嵌入規則包（:class:`~trpg.content.library.Ruleset` 的 ``summons``），
讓重播不依賴當下的資料檔。
"""

from __future__ import annotations

from fractions import Fraction

from pydantic import Field, model_validator

from trpg.content.battle import UnitTemplate, WeaponDef
from trpg.content.schemas import ContentModel

__all__ = ["SummonDef", "SummonTable", "summon_dpr"]


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
