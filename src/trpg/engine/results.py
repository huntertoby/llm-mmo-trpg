"""引擎 API 的回傳型別。"""

from __future__ import annotations

from typing import Literal, NamedTuple

from pydantic import BaseModel, ConfigDict

from trpg.engine.events import EventBase
from trpg.engine.state import BattleState
from trpg.shared.types import Team, UnitId

__all__ = ["AllyResult", "BattleResult", "Pending", "ResolveResult", "battle_result"]


class Pending(BaseModel):
    """結算暫停、等待玩家決定（``prompt`` 反應，或 ``copy_skill`` 選目標）。

    以 ``resume(state, Decision(unit_id=..., accept=...))`` 繼續；``kind == "copy_skill"`` 時
    ``Decision.copy_cast`` 給出複製技能的選取（Phase 3C-4b）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["reaction", "copy_skill"]
    unit_id: UnitId
    reaction: str = ""
    trigger_unit_id: UnitId | None = None
    skill_id: str | None = None
    """以反應技回應時為該技能 ID；一般（內建）反應規則為 ``None``；``copy_skill`` 暫停時為施放
    的 ``copy_skill`` 技能 ID。"""
    copy_skill_id: str | None = None
    """``copy_skill`` 暫停時：要複製的技能 ID（玩家要為它選目標）。"""
    trigger_event_seq: int | None = None
    """引發這次詢問的事件 ``seq``（格擋類為擊中判定 ``attack_rolled``、反應技為造成傷害的
    ``damage_dealt`` 或攻擊判定；``enemy_leaves_adjacent`` 的移動事件尚未發出，為 ``None``）。"""
    stamina_cost: int = 0
    """接受時要付出的耐力（內建反應）。"""
    mana_cost: int = 0
    """接受時要付出的法力（反應技）。"""
    hp_cost_permille: int = 0
    """接受時要付出的最大 HP 千分比（反應技的 ``hp_percent``）。"""


class ResolveResult(NamedTuple):
    state: BattleState
    events: list[EventBase]
    pending: Pending | None = None


class AllyResult(BaseModel):
    """戰鬥結束時一個我方單位的狀況（Phase 3C-4a；Phase 3-5 把 ``source`` 寫回一輪存檔）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: UnitId
    template_id: str
    hp: int
    max_hp: int
    downed: bool
    escaped: bool
    source: int
    """剩餘源力（0～``source_max``）。"""


class BattleResult(BaseModel):
    """一場戰鬥的結果：勝負與每個我方單位的剩餘狀況（依單位 ID 排序）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ended: bool
    winner: Team | None
    end_reason: str | None
    round: int
    allies: tuple[AllyResult, ...]

    def source_of(self, template_id: str) -> int | None:
        """範本為 ``template_id`` 的第一個我方單位的剩餘源力（沒有為 ``None``）。"""
        for ally in self.allies:
            if ally.template_id == template_id:
                return ally.source
        return None


def battle_result(state: BattleState) -> BattleResult:
    """``state`` 的戰鬥結果（戰鬥尚未結束時 ``ended`` 為 ``False``，數值是目前的狀況）。"""
    allies = tuple(
        AllyResult(
            unit_id=u.id,
            template_id=u.template_id,
            hp=u.hp,
            max_hp=u.max_hp,
            downed=u.downed,
            escaped=u.escaped,
            source=u.source,
        )
        for u in state.units_sorted()
        if u.team is Team.ALLY and not u.is_summon  # 召喚物不帶出戰鬥（Phase 3D-4a）
    )
    return BattleResult(
        ended=state.ended,
        winner=state.winner,
        end_reason=state.end_reason,
        round=state.round,
        allies=allies,
    )
