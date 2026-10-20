"""進行中的戰鬥（Phase 3-5a）：``setup ＋ seed ＋ 步驟 ＋ 指令``，可存可重播。

``setup`` 不存進存檔：它是 ``battle_setup(內容庫, RunState)`` 的結果（地圖、隊友、敵人來自內容庫與
``RunState.plan``，主角來自 ``RunState``，生成技能以 ``Ruleset.with_skills`` 加回規則包），而戰鬥
進行中 ``RunState`` 不會改變（戰後才寫回）。讀檔時重建 ``setup``、以
:func:`trpg.engine.runner.apply_step` 依序重播步驟，再以 ``CommandedAI.restore_orders`` 還原隊友
指令，得到與存檔當下逐位元相同的狀態。
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.library import ContentLibrary
from trpg.engine.actions import Step
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.orders import OrderRecord
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.runner import advance, apply_step
from trpg.engine.setup import BattleSetup
from trpg.engine.state import BattleState
from trpg.roguelite.errors import SaveFormatError
from trpg.roguelite.progress import battle_setup, hero_unit_id
from trpg.roguelite.state import BattleNode, RunState
from trpg.shared.errors import TrpgError
from trpg.shared.types import UnitId

__all__ = ["ActiveBattle", "SavedBattle", "battle_seed"]


class SavedBattle(BaseModel):
    """存檔中的進行中戰鬥：第幾場、種子、步驟（動作或決定，與 ``BattleLog.actions`` 同格式）、
    隊友指令紀錄（與 ``BattleLog.orders`` 同格式）。"""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    seed: int = Field(ge=0)
    steps: list[Step] = []
    orders: list[OrderRecord] = []


def battle_seed(run: RunState) -> int:
    assert isinstance(run.node, BattleNode)
    return run.plan_of(run.node.index).seed


class ActiveBattle:
    """一場進行中的戰鬥（AI 代打用；網頁 API 用 ``BattleSession``，存的內容相同）。"""

    def __init__(self, library: ContentLibrary, run: RunState) -> None:
        if not isinstance(run.node, BattleNode):
            raise TrpgError("目前不是戰鬥節點")
        self.index = run.node.index
        self.seed = battle_seed(run)
        self.setup: BattleSetup = battle_setup(library, run)
        opening = begin_battle(self.setup, self.seed)
        self.state: BattleState = opening.state
        self.pending: Pending | None = opening.pending
        self.steps: list[Step] = []
        self.policy = CommandedAI(UtilityAI(library.ai_profiles), {})
        """所有單位（含主角）共用的效用 AI；沒有指揮官。"""
        self.hero_id: UnitId = hero_unit_id(self.state)

    def apply(self, step: Step) -> ResolveResult:
        result = apply_step(self.state, step)
        self.state = result.state
        self.pending = result.pending
        self.steps.append(step)
        return result

    @classmethod
    def restore(cls, library: ContentLibrary, run: RunState, saved: SavedBattle) -> ActiveBattle:
        """以存檔的步驟重播；與目前節點不符或重播失敗時拋出 :class:`SaveFormatError`。"""
        battle = cls(library, run)
        if (saved.index, saved.seed) != (battle.index, battle.seed):
            raise SaveFormatError(
                f"存檔的戰鬥（第 {saved.index} 場，種子 {saved.seed}）與一輪進度"
                f"（第 {battle.index} 場，種子 {battle.seed}）不符"
            )
        for number, step in enumerate(saved.steps, start=1):
            try:
                battle.apply(step)
            except TrpgError as exc:
                raise SaveFormatError(f"存檔的第 {number} 步無法重播：{exc}") from exc
        battle.policy.restore_orders(saved.orders)
        return battle

    def to_saved(self) -> SavedBattle:
        return SavedBattle(
            index=self.index,
            seed=self.seed,
            steps=list(self.steps),
            orders=list(self.policy.order_log),
        )

    def auto(self, stop: Callable[[ActiveBattle], bool] | None = None) -> None:
        """AI 代打到戰鬥結束，或 ``stop(self)`` 為真（每一步之前檢查）。"""

        def on_step(step: Step | None, result: ResolveResult) -> None:
            assert step is not None
            self.state = result.state
            self.pending = result.pending
            self.steps.append(step)

        advance(
            self.state,
            self.pending,
            self.policy,
            on_step=on_step,
            stop=None if stop is None else (lambda _s, _p: stop(self)),
        )
