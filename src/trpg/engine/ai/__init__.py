"""敵我雙方的自動決策。

- :mod:`~trpg.engine.ai.simple`：Phase 1A 的簡易 AI（走向最近的敵人並攻擊）。
- Phase 1B 會加入以 ``preview`` 評分的效用 AI 與行為模式。

AI 只讀取狀態並回傳一個 :class:`~trpg.engine.actions.Action`；是否合法仍由 ``resolve`` 檢查。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.engine.actions import Action
from trpg.engine.state import BattleState

__all__ = ["Policy"]

type Policy = Callable[[BattleState], Action]
"""決策函式：給定狀態（輪到的行動者為 ``state.active``），回傳一個動作。"""
