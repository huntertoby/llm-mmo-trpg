"""環境回合、地圖事件、勝利條件、Boss 階段與天氣事件。"""

from __future__ import annotations

from typing import Literal

from trpg.engine.events.base import EventBase
from trpg.shared.types import Pos, Team, UnitId

# ---------------------------------------------------------------------------
# Phase 1B：環境回合、地圖事件、勝利條件
# ---------------------------------------------------------------------------


class EnvironmentStarted(EventBase):
    type: Literal["environment_started"] = "environment_started"


class EnvironmentEnded(EventBase):
    type: Literal["environment_ended"] = "environment_ended"


class MapEventTriggered(EventBase):
    type: Literal["map_event_triggered"] = "map_event_triggered"
    index: int
    kind: Literal["spawn_units", "terrain_change"]


class UnitSpawned(EventBase):
    type: Literal["unit_spawned"] = "unit_spawned"
    unit_id: UnitId
    template_id: str
    team: Team
    pos: Pos


class UnitEscaped(EventBase):
    """單位抵達出口，離開戰場。"""

    type: Literal["unit_escaped"] = "unit_escaped"
    unit_id: UnitId
    pos: Pos


# ---------------------------------------------------------------------------
# Phase 5F-2：Boss 階段、天氣
# ---------------------------------------------------------------------------


class BossPhaseChanged(EventBase):
    """Boss 進入新階段（Phase 5F-2，:mod:`trpg.engine.boss_phases`）：``phase`` 是 1 起算的新階段
    序號（開場階段為 1，所以第一次轉換是 2）；``trigger``／``permille``／``condition_zh`` 是這個
    階段的觸發條件；``hp``／``max_hp`` 是觸發當下。之後依序是移除狀態、換技能組與行為模式、
    施加狀態、改天氣、改格子、召喚的事件。"""

    type: Literal["boss_phase_changed"] = "boss_phase_changed"
    unit_id: UnitId
    phase: int
    total: int
    phase_id: str
    name_zh: str
    text_zh: str | None = None
    trigger: Literal["hp_below", "tag_down", "round_at"] = "hp_below"
    """觸發種類（Phase 5F-3 起）。"""
    permille: int | None = None
    """``hp_below`` 的 HP 門檻（‰）；其他種類為 ``None``。"""
    condition_zh: str = ""
    """觸發條件的中文（例「HP 60% 以下」「「源晶柱」倒下 3 名」「第 15 輪起」）。"""
    hp: int
    max_hp: int
    skills: tuple[str, ...] | None = None
    """換成的技能組（``None``＝不變）。"""


class WeatherChanged(EventBase):
    """戰鬥中天氣改變（Phase 5F-2：Boss 階段）。``before``／``after`` 是天氣 ID（``None``＝
    晴朗）。"""

    type: Literal["weather_changed"] = "weather_changed"
    before: str | None
    after: str | None
    after_name_zh: str
    cause: Literal["boss_phase"] = "boss_phase"
    source_id: UnitId | None = None
