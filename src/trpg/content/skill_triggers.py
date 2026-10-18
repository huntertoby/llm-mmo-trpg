"""技能觸發時機的資料 schema（``content/skill_triggers.yaml``；Phase 2E-1 3.1）。

被動技能（``kind: passive``）在「某件事發生時」自動生效；這個資料表定義有哪些時機、是否有
「另一方」單位、預算係數與最低稀有度。引擎（``trpg.engine.skill_triggers``）對照 ``id`` 收集事件。

只定義 schema；``trpg.content`` 不得匯入引擎。
"""

from __future__ import annotations

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillRarity

__all__ = [
    "EVERY_N_HITS",
    "REQUIRED_TRIGGERS",
    "SkillTriggerDef",
    "SkillTriggerTable",
]

EVERY_N_HITS = "every_n_hits"
"""唯一帶參數 ``n`` 的時機。"""

REQUIRED_TRIGGERS: tuple[str, ...] = (
    "on_hit",
    "on_crit",
    "on_natural_20",
    "on_kill",
    "on_damaged",
    "on_turn_start",
    "on_turn_end",
    "on_move",
    EVERY_N_HITS,
)
"""引擎實作的觸發時機，資料檔必須全部定義、不可多出引擎沒有的。"""


class SkillTriggerDef(ContentModel):
    """一種觸發時機。

    - ``has_other``：這個時機是否有「另一方」單位（``trigger.target: other`` 才能使用）。
    - ``budget_coefficient_permille``：被動技能的預算係數（取代主動技能的 AP 係數）。
      ``every_n_hits`` 依 ``n`` 查 ``budget_by_n_permille``。
    - ``min_rarity``：使用這個時機的最低稀有度。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    has_other: bool
    budget_coefficient_permille: int | None = Field(default=None, ge=1)
    budget_by_n_permille: dict[int, int] | None = None
    min_rarity: SkillRarity = "epic"

    @model_validator(mode="after")
    def _check(self) -> SkillTriggerDef:
        if self.id == EVERY_N_HITS:
            table = self.budget_by_n_permille
            if table is None or sorted(table) != [2, 3] or any(v < 1 for v in table.values()):
                raise ValueError("every_n_hits 必須以 budget_by_n_permille 給 n=2、3 的係數")
            if self.budget_coefficient_permille is not None:
                raise ValueError("every_n_hits 的係數依 n 查表，不可填 budget_coefficient_permille")
        else:
            if self.budget_coefficient_permille is None:
                raise ValueError(f"觸發時機 {self.id} 必須填 budget_coefficient_permille")
            if self.budget_by_n_permille is not None:
                raise ValueError(f"觸發時機 {self.id} 不可填 budget_by_n_permille")
        return self

    def coefficient_permille(self, n: int | None) -> int:
        """預算係數（‰）；``every_n_hits`` 依 ``n`` 查表（``n`` 不合法時回傳最小的係數）。"""
        if self.budget_by_n_permille is not None:
            table = self.budget_by_n_permille
            return table[n] if n in table else min(table.values())
        assert self.budget_coefficient_permille is not None
        return self.budget_coefficient_permille

    def summary(self) -> str:
        return self.name_zh


class SkillTriggerTable(ContentModel):
    """``content/skill_triggers.yaml``。"""

    triggers: tuple[SkillTriggerDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> SkillTriggerTable:
        ids = [t.id for t in self.triggers]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            raise ValueError(f"重複的觸發時機 ID：{', '.join(dup)}")
        missing = [i for i in REQUIRED_TRIGGERS if i not in ids]
        if missing:
            raise ValueError(f"缺少引擎實作的觸發時機：{', '.join(missing)}")
        unknown = sorted(set(ids) - set(REQUIRED_TRIGGERS))
        if unknown:
            raise ValueError(f"引擎尚未實作的觸發時機：{', '.join(unknown)}")
        return self

    def by_id(self) -> dict[str, SkillTriggerDef]:
        return {t.id: t for t in self.triggers}

    def summary(self) -> str:
        return f"{len(self.triggers)} 種觸發時機"
