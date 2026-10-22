"""技能等級的顯示文字（Phase 3-26a，``docs/design/06-技能.md`` 6.28）：技能卡的「Lv.N」、目前加成與
下一級的效果。數值全部來自 ``content/skill_growth.yaml``（``Ruleset.skill_growth``）；5 級小特性依
技能自動擇一（:func:`trpg.engine.skill_levels.level_trait`）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.engine.skill_levels import level_trait

__all__ = ["SkillLevelInfo", "skill_level_info"]

_TRAIT_TEXT = {"area": "範圍 +1", "cooldown": "冷卻 −1 回合"}


class SkillLevelInfo(BaseModel):
    """一個技能在某個等級的顯示資料。只有主動技能有（其他技能的卡片 ``growth`` 為 ``None``）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: int
    max_level: int
    bonus_permille: int
    """目前累計的效果加成（‰）。"""
    current_text: str
    """目前等級的一句話，例如「Lv.4：傷害、治療、護盾 +20%」。"""
    next_level: int | None
    next_text: str | None
    """下一級的一句話，例如「Lv.5：小特性 範圍 +1」；已滿級為 ``None``。"""
    trait: Literal["area", "cooldown"] | None
    """這招的 5 級小特性（範圍 +1 或冷卻 −1）；做不到時 ``None``。"""
    trait_text: str
    """小特性的一句話（沒有時說明原因）。"""
    trait_active: bool
    """目前等級已經到小特性的等級。"""
    cost: int
    """升到下一級要花的技能點。"""
    uses: int = 0
    """這一輪用過的次數（Phase 3-26b；分歧進化的門檻）。"""
    evolve_uses: int = 0
    """升到分歧進化那一級要用過的次數。"""
    evolved_from_zh: str | None = None
    """進化前的技能名稱（已進化的技能）；沒進化為 ``None``。"""
    blocked_text: str | None = None
    """下一級現在升不了的原因（例如用過的次數不夠）；可以升為 ``None``。"""


def _bonus_text(percent: int) -> str:
    return "效果沒有加成" if percent == 0 else f"傷害、治療、護盾 +{percent}%"


def skill_level_info(
    library: ContentLibrary,
    skill: SkillDef,
    level: int,
    *,
    uses: int = 0,
    evolved_from_zh: str | None = None,
    blocked_text: str | None = None,
) -> SkillLevelInfo | None:
    """``skill`` 在 ``level`` 級的顯示資料；不是主動技能
    （不能升級）時 ``None``。``uses`` 是這一輪用過
    的次數、``evolved_from_zh`` 是進化前的名稱（已進化時）、``blocked_text`` 是下一級升不了的原因
    （Phase 3-26b，由呼叫者依一輪的狀態算好）。"""
    if skill.kind != "active":
        return None
    rules = library.ruleset
    growth = rules.skill_growth
    level = max(1, min(growth.max_level, level))
    trait = level_trait(rules, skill)
    trait_text = (
        f"{growth.trait_level} 級小特性：{_TRAIT_TEXT[trait]}"
        if trait is not None
        else f"{growth.trait_level} 級小特性：這招沒有可加的範圍或可減的冷卻"
    )
    current = growth.bonus_permille(level)
    current_text = f"Lv.{level}：{_bonus_text(current // 10)}"
    if level >= growth.trait_level and trait is not None:
        current_text += f"，{_TRAIT_TEXT[trait]}"
    next_level = level + 1 if level < growth.max_level else None
    next_text = None
    if next_level is not None:
        gained = growth.bonus_permille(next_level) - current
        parts = []
        if gained > 0:
            parts.append(f"效果 +{gained // 10}%（共 +{growth.bonus_permille(next_level) // 10}%）")
        if next_level == growth.trait_level:
            parts.append(_TRAIT_TEXT[trait] if trait is not None else "（沒有可用的小特性）")
        if next_level == growth.evolve_level:
            parts.append(
                "只計等級（已進化）"
                if evolved_from_zh is not None
                else f"分歧進化：加深／橋接二選一（用過 {uses}/{growth.evolve_uses} 次）"
            )
        next_text = f"Lv.{next_level}：" + ("、".join(parts) if parts else "只計等級")
    return SkillLevelInfo(
        level=level,
        max_level=growth.max_level,
        bonus_permille=current,
        current_text=current_text,
        next_level=next_level,
        next_text=next_text,
        trait=trait,
        trait_text=trait_text,
        trait_active=level >= growth.trait_level,
        cost=growth.upgrade_cost,
        uses=uses,
        evolve_uses=growth.evolve_uses,
        evolved_from_zh=evolved_from_zh,
        blocked_text=blocked_text,
    )
