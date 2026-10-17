"""純確定性規則引擎：格子、單位、行動、判定、效果佇列與事件。

- 實作階段：Phase 1A 起（戰鬥核心）；Phase 1B 加入環境、反應、預覽與效用 AI。
- 介面（``docs/phases/Phase1計畫.md`` 3.1）::

      start_battle(setup, seed) -> BattleState
      legal_actions(state) -> list[Action]
      resolve(state, action) -> ResolveResult(state, events, pending)
      resume(state, decision) -> ResolveResult          # prompt 反應的暫停點
      preview(state, action) -> Preview                 # 預覽（dry run）
      telegraph(state) -> Telegraph                     # 環境下一輪預告

  亂數狀態存放在 ``BattleState.rng_state``；``初始狀態 ＋ 動作列表`` 即可完整重播。
- 依賴限制：不得匯入 ``trpg.llm``、``trpg.narrative``、``trpg.api``、``trpg.roguelite``、
  ``trpg.sim``、``trpg.skillgen``、``trpg.cli``。
- 確定性：禁止呼叫 LLM、讀取時間、使用 ``random`` 模組與 ``uuid4``；亂數只用
  ``trpg.shared.rng.Rng``（由 ``rng_state`` 還原）。

模組：``state``（狀態與序列化）、``actions``、``events``、``setup``、``battle``（API 與動作）、
``turns``（回合流程與勝負）、``rules/``（幾何、移動、判定）、``effects/``（效果佇列）、
``triggers``（事件 → 效果）、``interactions``（元素 × 標籤互動表）、``reactions``（反應與暫停點）、
``environment``（環境回合、預告、天氣、地圖事件）、``objectives``（勝利條件）、``preview``（預覽）、
``ai/``（簡易 AI、效用 AI）、``runner``（自動對戰與重播）。
"""

from __future__ import annotations

from trpg.engine.actions import (
    Action,
    Attack,
    Decision,
    Defend,
    EndTurn,
    Interact,
    Move,
    Shove,
    Step,
    Trip,
)
from trpg.engine.battle import begin_battle, legal_actions, resolve, resume, start_battle
from trpg.engine.environment import Telegraph, telegraph
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.setup import (
    BattleSetup,
    BattleSetupError,
    UnitSpawn,
    build_setup,
    deploy_allies,
    deployment_tiles,
)
from trpg.engine.state import BattleState, state_from_json, state_to_json

__all__ = [
    "Action",
    "Attack",
    "BattleSetup",
    "BattleSetupError",
    "BattleState",
    "Decision",
    "Defend",
    "EndTurn",
    "Interact",
    "Move",
    "Pending",
    "ResolveResult",
    "Shove",
    "Step",
    "Telegraph",
    "Trip",
    "UnitSpawn",
    "begin_battle",
    "build_setup",
    "deploy_allies",
    "deployment_tiles",
    "legal_actions",
    "resolve",
    "resume",
    "start_battle",
    "state_from_json",
    "state_to_json",
    "telegraph",
]
