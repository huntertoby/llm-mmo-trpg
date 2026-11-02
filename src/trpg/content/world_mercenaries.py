"""系統傭兵名單（``content/world/mercenaries.yaml``，Phase 5C-1；09 9.6.8 #87、9.6.9 #97、
9.6.11 #117）。

- 一隊 3 人：主角＋最多 ``max_hired`` 名傭兵（#97）；雇用免費、只能在城鎮選（世界動作 ``hire``，
  :mod:`trpg.world.party`）。
- 每名傭兵是固定 build（事先公布、每個人都一樣，#87）：底稿取自 ``content/sim/builds.yaml``
  （#117），戰鬥單位＝底稿的英雄範本換成傭兵的 ID 與暫名；等級與技能階級照主角成長（5A-SIM2）。

跨檔案檢查（底稿存在、不是白板或對照組）在 :mod:`trpg.content.library`。
"""

from __future__ import annotations

from collections import Counter
from typing import Final, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = ["MERCENARY_ROLES", "MIN_PER_ROLE", "MercenaryDef", "MercenaryRole", "MercenaryTable"]

type MercenaryRole = Literal["damage", "guardian", "support", "control"]
"""定位（9.6.8：輸出、守護、輔助、控制）。"""

MERCENARY_ROLES: Final[dict[str, str]] = {
    "damage": "輸出",
    "guardian": "守護",
    "support": "輔助",
    "control": "控制",
}
"""定位 → 中文（依 9.6.8 的順序）。"""

MIN_PER_ROLE: Final = 2
"""每種定位至少幾名（9.6.8「各至少 2 種固定 build」）。"""


class MercenaryDef(ContentModel):
    """一名系統傭兵。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    """暫名（9.6.11 #117），也是戰鬥單位的名字。"""
    title_zh: str = Field(min_length=1)
    """稱號（例：近戰劍客）。"""
    role: MercenaryRole
    build: str = Field(pattern=ID_PATTERN)
    """底稿：``content/sim/builds.yaml`` 的 build ID。"""


class MercenaryTable(ContentModel):
    """``content/world/mercenaries.yaml``。"""

    max_hired: int = Field(default=2, ge=1, le=2)
    """一次最多帶幾名（#97：主角＋最多 2 名隊友）。"""
    mercenaries: tuple[MercenaryDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> MercenaryTable:
        dup = sorted(k for k, n in Counter(m.id for m in self.mercenaries).items() if n > 1)
        if dup:
            raise ValueError(f"傭兵 ID 重複：{', '.join(dup)}")
        counts: Counter[str] = Counter(m.role for m in self.mercenaries)
        short = [MERCENARY_ROLES[r] for r in MERCENARY_ROLES if counts[r] < MIN_PER_ROLE]
        if short:
            raise ValueError(f"每種定位至少 {MIN_PER_ROLE} 名（9.6.8），不足：{'、'.join(short)}")
        return self

    def by_id(self) -> dict[str, MercenaryDef]:
        return {m.id: m for m in self.mercenaries}
