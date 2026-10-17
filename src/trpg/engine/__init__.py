"""純確定性規則引擎：格子、單位、行動、判定、效果佇列與事件。

- 實作階段：Phase 1A 起（戰鬥核心）；Phase 1B 加入環境、反應、預覽與效用 AI。
- 介面（``docs/phases/Phase1計畫.md`` 3.1）::

      start_battle(setup, seed) -> BattleState
      legal_actions(state) -> list[Action]
      resolve(state, action) -> ResolveResult(state, events, pending)

  亂數狀態存放在 ``BattleState.rng_state``；``初始狀態 ＋ 動作列表`` 即可完整重播。
- 依賴限制：不得匯入 ``trpg.llm``、``trpg.narrative``、``trpg.api``、``trpg.roguelite``、
  ``trpg.sim``、``trpg.skillgen``、``trpg.cli``。
- 確定性：禁止呼叫 LLM、讀取時間、使用 ``random`` 模組與 ``uuid4``；亂數只用
  ``trpg.shared.rng.Rng``（由 ``rng_state`` 還原）。

模組：``state``（狀態與序列化）、``actions``、``events``、``setup``、``battle``（API 與動作）、
``turns``（回合流程與勝負）、``rules/``（幾何、移動、判定）、``effects/``（效果佇列）、
``triggers``（事件 → 效果）、``ai/``（簡易 AI）、``runner``（自動對戰與重播）。
"""

from __future__ import annotations

from trpg.engine.actions import Action, Attack, Defend, EndTurn, Move
from trpg.engine.battle import begin_battle, legal_actions, resolve, start_battle
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.setup import BattleSetup, BattleSetupError, UnitSpawn, build_setup
from trpg.engine.state import BattleState, state_from_json, state_to_json

__all__ = [
    "Action",
    "Attack",
    "BattleSetup",
    "BattleSetupError",
    "BattleState",
    "Defend",
    "EndTurn",
    "Move",
    "Pending",
    "ResolveResult",
    "UnitSpawn",
    "begin_battle",
    "build_setup",
    "legal_actions",
    "resolve",
    "start_battle",
    "state_from_json",
    "state_to_json",
]
