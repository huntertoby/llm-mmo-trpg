"""大世界隊伍與系統傭兵的 API 格式（Phase 5C-1；``docs/phases/Phase5計畫.md`` 22.6）。

全部由後端算好（前端不寫規則）：隊伍成員、能不能雇用與理由、傭兵名單（定位、主題、技能概要）。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["MercenaryView", "PartyMemberView", "PartyView"]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PartyMemberView(_ApiModel):
    """隊伍的一名成員（主角、傭兵或標準隊友）。"""

    name_zh: str
    title_zh: str
    """主角＝「主角」；傭兵＝稱號＋定位（例「盾衛・守護」）；標準隊友＝「標準隊友」。"""
    level: int
    """開戰時的等級（傭兵與標準隊友照主角等級成長，5A-SIM2）。"""
    mercenary: str | None = None
    """傭兵 ID（主角與標準隊友為 ``None``）。"""


class MercenaryView(_ApiModel):
    """名單上的一名系統傭兵（每個人都一樣，9.6.8）。"""

    id: str
    name_zh: str
    title_zh: str
    role: str
    role_zh: str
    theme_zh: str
    """底稿 build 的主題說明（打法、有利與不利的地形）。"""
    skills_zh: tuple[str, ...]
    """技能概要：底稿技能的中文名（依底稿順序；開戰時照主角等級升階）。"""
    hired: bool


class PartyView(_ApiModel):
    """目前的隊伍與雇用（09 9.6.9 #97：主角＋最多 2 名；免費、出城前在城鎮選好、野外不能換）。"""

    members: tuple[PartyMemberView, ...]
    max_hired: int
    can_hire: bool
    hire_problem_zh: str | None
    """不能換傭兵的理由（例「出城前在城鎮選好，野外不能換」）；可以時為 ``None``。"""
    mercenaries: tuple[MercenaryView, ...] = ()
    """傭兵名單（名單順序）。"""
