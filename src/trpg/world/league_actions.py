"""影子循環賽的世界動作與事件（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.4）。

放在獨立模組，由 :mod:`trpg.world.actions` 併進 ``WorldAction``／``WorldEvent`` 聯集（不匯入
``actions``，避免循環）。規則在 :mod:`trpg.world.league`。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.shared.types import Attribute

__all__ = [
    "LeagueEnterAction",
    "LeagueEnteredEvent",
    "LeagueWithdrawAction",
    "LeagueWithdrawnEvent",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LeagueEnterAction(_Model):
    """在城鎮用目前的 build 報名影子循環賽（9.7；每個帳號 1 個角色，#100）；同一個角色再送＝更新。
    ``ai`` 是 AI 打法（``ai_choices``；``None``＝自己影子的預設打法）。"""

    kind: Literal["league_enter"] = "league_enter"
    ai: str | None = Field(default=None, pattern=ID_PATTERN)
    allocation: dict[Attribute, int] | None = None
    """（5F-4b，#32）循環賽用的屬性點重新分配：拉到等級上限後「全部可配的點」（已分配的＋未分配的
    ＋升到上限多出的）怎麼配，總和必須剛好等於可配點數；``None``＝照開局自動配點補新增的點。
    只影響循環賽，不改角色本身。"""


class LeagueWithdrawAction(_Model):
    """取消循環賽報名（截止前）。"""

    kind: Literal["league_withdraw"] = "league_withdraw"


class LeagueEnteredEvent(_Model):
    kind: Literal["league_entered"] = "league_entered"
    ai: str | None = None
    """報名的 AI 打法（``None``＝預設）。"""
    updated: bool = False
    """這個角色本來就報名了（更新快照與打法）。"""


class LeagueWithdrawnEvent(_Model):
    kind: Literal["league_withdrawn"] = "league_withdrawn"
