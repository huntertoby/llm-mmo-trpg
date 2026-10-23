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
from trpg.content.rules import CoreRules
from trpg.content.schemas import ContentModel

__all__ = [
    "SummonDef",
    "SummonLookEntry",
    "SummonLookTable",
    "SummonTable",
    "load_summon_looks",
    "summon_dpr",
    "summon_scaled_hp",
    "summon_spec_hp",
]

_PERMILLE = 1000


def summon_scaled_hp(
    core: CoreRules,
    template: UnitTemplate,
    base_max_hp: int,
    *,
    growth_hp: int = 0,
    owner_hp_permille: int = _PERMILLE,
    infusion_hp_permille: int = 0,
) -> int:
    """召喚物的最大 HP（Phase 3-33f1 的定位係數式；3-41a 抽成共用函式，引擎生成與技能卡顯示同一個
    算法）：``(範本 HP ＋ 成長) × 定位係數‰`` → × 召喚者修正規則的 HP 倍率‰ → × (1 ＋ 灌注的 HP
    加成‰)，每一步無條件捨去。分歧進化的 HP 另見 :func:`summon_spec_hp`。

    ``base_max_hp`` 是範本建立出的單位的最大 HP（:meth:`CoreRules.template_max_hp`，含體質）。"""
    role = core.summon_role_hp_permille.get(template.role or "", _PERMILLE)
    hp = (base_max_hp + growth_hp) * role // _PERMILLE
    hp = hp * owner_hp_permille // _PERMILLE
    return hp * (_PERMILLE + infusion_hp_permille) // _PERMILLE


def summon_spec_hp(max_hp: int, *, max_hp_permille: int | None, power_permille: int | None) -> int:
    """召喚技能分歧進化（Phase 3-33f2）對最大 HP 的調整：加深 ``max_hp_permille``（＋‰），數量型
    ``power_permille``（每隻只有這麼多‰，至少 1）。"""
    if max_hp_permille:
        max_hp = max_hp * (_PERMILLE + max_hp_permille) // _PERMILLE
    if power_permille is not None:
        max_hp = max(1, max_hp * power_permille // _PERMILLE)
    return max_hp


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


def summon_dpr(summon: SummonDef, *, flat: int = 0, bonus_permille: int = 0) -> Fraction:
    """召喚物每輪的預估傷害（最簡單的近似，預算與 AI 共用）：武器骰平均 ＋ 固定傷害，
    每輪一次攻擊、不計命中率與屬性。``flat``／``bonus_permille`` 是施放者成長的普攻固定傷害與
    傷害加成（‰；Phase 3-33c，AI 估值用）。"""
    if summon.template.inert:  # 不行動的召喚物（土牆）沒有攻擊
        return Fraction(0)
    dice = summon.weapon.dice
    base = Fraction(dice.count * (dice.sides + 1), 2) + summon.weapon.flat + flat
    return base * (1000 + bonus_permille) / 1000


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
