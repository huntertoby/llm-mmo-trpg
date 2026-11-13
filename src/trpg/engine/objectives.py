"""勝利與失敗條件（``docs/專案計畫.md`` 5.8；``docs/phases/Phase1計畫.md`` 6.1-10）。

- ``eliminate``：擊倒所有敵人即勝。
- ``escape``：我方存活單位在 ``rounds`` 輪內全部抵達出口格即勝（抵達者離開戰場）；第 ``rounds``
  輪結束時仍有我方單位留在戰場上即敗（``escape_failed``）。
- ``defend``：守住守點 ``rounds`` 輪即勝（``defended``）；某輪結束（環境回合之後）時有敵方單位
  站在守點格上即敗（``point_lost``）。
- 任何模式：我方全滅（且沒有人撤離）即敗；敵人全滅即勝（``eliminate``）。
- 「敵人」＝ 和我方敵對的單位：敵方＋第三方（Phase 5B-M3 三方混戰，代決 5BM3-3）。敵方被第三方
  打光、第三方還在時繼續打；守點被第三方占也算失守；敗北時勝方一律記 ``enemy``（代決 5BM3-4）。
- 召喚物（Phase 3D-4a）不計入任何勝負條件：全滅判定不看它們，敵方召喚物站在守點上也不算失守。
- ``eliminate`` 帶 ``leader_retreat``（Boss 戰，BAL-16a，05 5.8，#86）：敵方頭目（``boss`` 標籤、
  非召喚物）全部倒下時，其餘敵人（含第三方）撤退，我方直接勝利（``leader_defeated``）。撤退的敵人不算倒下
  （不給擊殺、不掉落）。

:func:`check_battle_end` 在每次結算後與回合交接時檢查；:func:`check_round_end` 在每輪的
環境回合之後檢查。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import BattleEnded, EndReason, GuardsRetreated
from trpg.engine.forms import leave_all_forms
from trpg.engine.ids import BOSS_TAG
from trpg.engine.rules.footprint import touches
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Team

__all__ = ["check_battle_end", "check_round_end", "end_battle"]


def end_battle(ctx: Ctx, winner: Team | None, reason: EndReason) -> None:
    state = ctx.state
    state.ended = True
    state.winner = winner
    state.end_reason = reason
    state.active_unit = None
    leave_all_forms(ctx, "battle_end")  # 戰鬥結束解除形態（Phase 3J-1a）
    ctx.emit(BattleEnded, winner=winner, reason=reason)


def check_battle_end(ctx: Ctx) -> bool:
    """隨時成立的結束條件（全滅、全員撤離）。回傳戰鬥是否已結束。"""
    state = ctx.state
    if state.ended:
        return True
    living = [u for u in state.living_units() if not u.is_summon]  # 召喚物不計入（Phase 3D-4a）
    allies = [u for u in living if u.team is Team.ALLY]
    enemies = [u for u in living if u.team is not Team.ALLY]  # 敵方＋第三方（5B-M3）
    escaped = any(u.escaped for u in state.units.values() if u.team is Team.ALLY)
    if allies and enemies:
        leaders = _fallen_leaders(state)
        if leaders:
            ctx.emit(
                GuardsRetreated,
                leader_ids=tuple(u.id for u in leaders),
                unit_ids=tuple(u.id for u in sorted(enemies, key=lambda u: u.id)),
            )
            end_battle(ctx, Team.ALLY, "leader_defeated")
            return True
        return False
    if not allies and escaped:
        end_battle(ctx, Team.ALLY, "escaped")
    elif not enemies and (allies or escaped):
        end_battle(ctx, Team.ALLY, "eliminate")
    elif not allies and enemies:
        end_battle(ctx, Team.ENEMY, "eliminate")
    else:
        end_battle(ctx, None, "eliminate")
    return True


def _fallen_leaders(state: BattleState) -> list[UnitState]:
    """Boss 戰（``leader_retreat``）：場上曾有敵方頭目且全部已倒下時，回傳這些頭目；否則空列表。"""
    if not state.objective.leader_retreat:
        return []
    leaders = [
        u
        for u in state.units_sorted()
        if u.team is Team.ENEMY and not u.is_summon and u.has_tag(BOSS_TAG)
    ]
    return [] if any(u.alive for u in leaders) else leaders


def check_round_end(ctx: Ctx) -> bool:
    """每輪結束（環境回合之後）的勝利條件判定。回傳戰鬥是否已結束。"""
    if check_battle_end(ctx):
        return True
    state = ctx.state
    objective = state.objective
    if objective.kind == "escape":
        assert objective.rounds is not None
        if state.round >= objective.rounds:
            end_battle(ctx, Team.ENEMY, "escape_failed")
            return True
    elif objective.kind == "defend":
        assert objective.rounds is not None
        tiles = set(objective.tiles)
        if any(
            u.team is not Team.ALLY and not u.is_summon and touches(u, tiles)
            for u in state.living_units()
        ):
            end_battle(ctx, Team.ENEMY, "point_lost")
            return True
        if state.round >= objective.rounds:
            end_battle(ctx, Team.ALLY, "defended")
            return True
    return False
