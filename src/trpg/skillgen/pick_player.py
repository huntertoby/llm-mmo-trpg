"""挑選模式打分用的玩家狀態摘要（Phase PK-1；提案第 4 節、7.2 節）。

只放引擎已記錄、確定性的資料：手上的技能（協同看它們製造／利用的關鍵字）、行為紀錄（動作 → 次數）、
主角屬性與手上武器的縮放屬性（屬性路線）。獨立成小模組（之後接一輪或大世界的出題時，呼叫端只要組這個
摘要，不必匯入候選池）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute

__all__ = ["PickPlayer"]


@dataclass(frozen=True, slots=True)
class PickPlayer:
    """玩家狀態摘要。全部欄位可空：空的摘要只剩多樣性在排序。"""

    held_skills: tuple[SkillDef, ...] = ()
    """手上的技能（裝備＋備用）。"""
    behavior: Mapping[str, int] = field(default_factory=dict)
    """用過的動作類型 → 次數（``RunState.behavior``）。"""
    hero_attributes: Mapping[Attribute, int] = field(default_factory=dict)
    """主角目前的六屬性；空＝不看屬性路線。"""
    weapon_attrs: tuple[Attribute, ...] = ()
    """手上武器的縮放屬性（武器技看手上武器，3H-7）。"""
