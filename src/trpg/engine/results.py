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
    mana: int
    max_mana: int


class BattleResult(BaseModel):
    """一場戰鬥的結果：勝負與每個我方單位的剩餘狀況（依單位 ID 排序）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ended: bool
    winner: Team | None
    end_reason: str | None
    round: int
    allies: tuple[AllyResult, ...]

    def ally(self, unit_id: str) -> AllyResult | None:
        """單位 ID 為 ``unit_id`` 的我方單位的結果（沒有為 ``None``）。"""
        for ally in self.allies:
            if ally.unit_id == unit_id:
                return ally
        return None

    def source_of(self, unit_id: str) -> int | None:
        """單位 ``unit_id`` 的剩餘源力（不是我方單位為 ``None``）。"""
        found = self.ally(unit_id)
        return None if found is None else found.source

    def hp_of(self, unit_id: str) -> int | None:
        """單位 ``unit_id`` 的剩餘 HP（不是我方單位為 ``None``）。"""
        found = self.ally(unit_id)
        return None if found is None else found.hp

    def mana_of(self, unit_id: str) -> int | None:
        """單位 ``unit_id`` 的剩餘法力（不是我方單位為 ``None``）。"""
        found = self.ally(unit_id)
        return None if found is None else found.mana

    def ally_of_template(self, template_id: str) -> AllyResult | None:
        """範本為 ``template_id`` 的我方單位的結果（便利函式；沒有為 ``None``）。

        同一範本有兩個以上的我方單位時拋出 :class:`ValueError`（請改用單位 ID 查）。
        """
        found = [a for a in self.allies if a.template_id == template_id]
        if len(found) > 1:
            ids = "、".join(a.unit_id for a in found)
            raise ValueError(
                f"範本 {template_id} 有 {len(found)} 個我方單位（{ids}），請以單位 ID 查詢"
            )
        return found[0] if found else None

    def source_of_template(self, template_id: str) -> int | None:
        """範本為 ``template_id`` 的唯一我方單位的剩餘源力（沒有為 ``None``；兩個以上拋出
        :class:`ValueError`）。"""
        found = self.ally_of_template(template_id)
        return None if found is None else found.source


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
            mana=u.mana,
            max_mana=u.max_mana,
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
