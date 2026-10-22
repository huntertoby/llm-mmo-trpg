"""技能成長的參數（``content/skill_growth.yaml``；Phase 3-26a，``docs/design/06-技能.md`` 6.28）。

數值都放資料檔；結算只用整數千分比（‰）。引擎（:mod:`trpg.engine.skill_levels`）與 roguelite
（:mod:`trpg.roguelite.progress`）都讀這份。預設值與資料檔相同，讓不載入完整內容庫的單元測試也能用。
"""

from __future__ import annotations

from itertools import pairwise

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel

__all__ = ["SkillGrowthRules"]

_MIN_LEVEL = 2


class SkillGrowthRules(ContentModel):
    """技能點與技能等級的規則。"""

    max_level: int = Field(default=5, ge=1, le=9)
    points_per_level: int = Field(default=2, ge=0)
    upgrade_cost: int = Field(default=1, ge=1)
    effect_permille: tuple[int, ...] = (0, 100, 100, 200, 200)
    """各等級的累計效果加成（‰），索引 ＋ 1 ＝ 等級；個數 ＝ ``max_level``、第 1 級為 0、不遞減。"""
    trait_level: int = Field(default=5, ge=2)
    trait_area_delta: int = Field(default=1, ge=1, le=2)
    trait_cooldown_delta: int = Field(default=1, ge=1, le=2)
    trait_min_cooldown: int = Field(default=2, ge=2)
    evolve_level: int = Field(default=3, ge=2)

    @model_validator(mode="after")
    def _check(self) -> SkillGrowthRules:
        table = self.effect_permille
        if len(table) != self.max_level:
            raise ValueError(f"effect_permille 必須有 {self.max_level} 個值，收到 {len(table)} 個")
        if table[0] != 0:
            raise ValueError("effect_permille 的第 1 級必須是 0")
        if any(b < a for a, b in pairwise(table)):
            raise ValueError("effect_permille 不可遞減")
        for name in ("trait_level", "evolve_level"):
            if not _MIN_LEVEL <= getattr(self, name) <= self.max_level:
                raise ValueError(f"{name} 必須在 {_MIN_LEVEL} 到 max_level 之間")
        return self

    def bonus_permille(self, level: int) -> int:
        """``level`` 級的累計效果加成（‰）；超出範圍時夾在 1～``max_level``。"""
        return self.effect_permille[max(1, min(self.max_level, level)) - 1]

    def multiplier_permille(self, level: int) -> int:
        """``level`` 級的效果倍率（‰）：1000 ＋ 加成。"""
        return 1000 + self.bonus_permille(level)

    def summary(self) -> str:
        return (
            f"技能等級 1～{self.max_level}，每級 {self.points_per_level} 點，"
            f"升級花 {self.upgrade_cost} 點"
        )
