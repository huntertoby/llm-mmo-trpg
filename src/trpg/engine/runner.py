"""自動對戰與重播（CLI 與之後的模擬器共用的驅動迴圈）。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast

from pydantic import BaseModel, ConfigDict

from trpg.engine.actions import Action, EndTurn
from trpg.engine.ai import Policy
from trpg.engine.ai.simple import choose_action
from trpg.engine.battle import begin_battle, has_only_end_turn, resolve
from trpg.engine.events import Event, EventBase
from trpg.engine.results import ResolveResult
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.shared.errors import TrpgError

__all__ = [
    "LOG_FORMAT",
    "BattleLog",
    "BattleRun",
    "replay",
    "run_battle",
]

LOG_FORMAT = "trpg-battle-log/1"
DEFAULT_MAX_ACTIONS = 20_000

type StepCallback = Callable[[Action | None, ResolveResult], None]


class BattleRun:
    """一場自動對戰的結果：最終狀態、動作列表、全部事件（含開場事件）。"""

    __slots__ = ("actions", "events", "seed", "setup", "state")

    def __init__(
        self,
        setup: BattleSetup,
        seed: int,
        state: BattleState,
        actions: list[Action],
        events: list[EventBase],
    ) -> None:
        self.setup = setup
        self.seed = seed
        self.state = state
        self.actions = actions
        self.events = events

    def to_log(self) -> BattleLog:
        return BattleLog(
            format=LOG_FORMAT,
            seed=self.seed,
            setup=self.setup,
            actions=self.actions,
            events=cast("list[Event]", self.events),
            final_state=self.state,
        )


class BattleLog(BaseModel):
    """``trpg battle --log-json`` 的輸出格式。"""

    model_config = ConfigDict(extra="forbid")

    format: str
    seed: int
    setup: BattleSetup
    actions: list[Action]
    events: list[Event]
    final_state: BattleState


def run_battle(
    setup: BattleSetup,
    seed: int,
    policy: Policy = choose_action,
    *,
    on_step: StepCallback | None = None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
) -> BattleRun:
    """雙方都由 ``policy`` 決策，跑到戰鬥結束。

    ``legal_actions`` 只剩 ``EndTurn`` 時（:func:`has_only_end_turn`）自動結束回合，不詢問
    policy。``on_step`` 在開場與每個動作結算後呼叫（開場時 action 為 ``None``）。超過
    ``max_actions`` 個動作仍未結束時拋出錯誤（設定 ``max_rounds`` 可保證結束）。
    """
    result = begin_battle(setup, seed)
    if on_step is not None:
        on_step(None, result)
    state = result.state
    events: list[EventBase] = list(result.events)
    actions: list[Action] = []
    while not state.ended:
        if len(actions) >= max_actions:
            raise TrpgError(f"超過 {max_actions} 個動作仍未結束戰鬥")
        if has_only_end_turn(state):
            assert state.active_unit is not None
            action: Action = EndTurn(unit_id=state.active_unit)
        else:
            action = policy(state)
        result = resolve(state, action)
        if on_step is not None:
            on_step(action, result)
        state = result.state
        actions.append(action)
        events.extend(result.events)
    return BattleRun(setup, seed, state, actions, events)


def replay(setup: BattleSetup, seed: int, actions: Sequence[Action]) -> BattleRun:
    """以 ``初始狀態 ＋ 動作列表`` 重播。"""
    result = begin_battle(setup, seed)
    state = result.state
    events: list[EventBase] = list(result.events)
    for action in actions:
        result = resolve(state, action)
        state = result.state
        events.extend(result.events)
    return BattleRun(setup, seed, state, list(actions), events)
