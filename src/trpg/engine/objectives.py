"""勝利與失敗條件（``docs/專案計畫.md`` 5.8；``docs/phases/Phase1計畫.md`` 6.1-10）。

- ``eliminate``：擊倒所有敵人即勝。
- ``escape``：我方存活單位在 ``rounds`` 輪內全部抵達出口格即勝（抵達者離開戰場）；第 ``rounds``
  輪結束時仍有我方單位留在戰場上即敗（``escape_failed``）。
- ``defend``：守住守點 ``rounds`` 輪即勝（``defended``）；某輪結束（環境回合之後）時有敵方單位
  站在守點格上即敗（``point_lost``）。
- 任何模式：我方全滅（且沒有人撤離）即敗；敵方全滅即勝（``eliminate``）。

:func:`check_battle_end` 在每次結算後與回合交接時檢查；:func:`check_round_end` 在每輪的
環境回合之後檢查。
"""

from __future__ import annotations

from trpg.engine.context import Ctx
from trpg.engine.events import BattleEnded, EndReason
from trpg.shared.types import Team

__all__ = ["check_battle_end", "check_round_end", "end_battle"]


def end_battle(ctx: Ctx, winner: Team | None, reason: EndReason) -> None:
    state = ctx.state
    state.ended = True
    state.winner = winner
    state.end_reason = reason
    state.active_unit = None
    ctx.emit(BattleEnded, winner=winner, reason=reason)


def check_battle_end(ctx: Ctx) -> bool:
    """隨時成立的結束條件（全滅、全員撤離）。回傳戰鬥是否已結束。"""
    state = ctx.state
    if state.ended:
        return True
    living = state.living_units()
    allies = [u for u in living if u.team is Team.ALLY]
    enemies = [u for u in living if u.team is Team.ENEMY]
    escaped = any(u.escaped for u in state.units.values() if u.team is Team.ALLY)
    if allies and enemies:
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
        if any(u.team is Team.ENEMY and u.xy in tiles for u in state.living_units()):
            end_battle(ctx, Team.ENEMY, "point_lost")
            return True
        if state.round >= objective.rounds:
            end_battle(ctx, Team.ALLY, "defended")
            return True
    return False
