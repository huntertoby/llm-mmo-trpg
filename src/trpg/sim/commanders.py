"""腳本指揮官（Phase 2C-2；``docs/phases/Phase2C計畫.md`` 4.4）。

確定性、只讀狀態的 :data:`~trpg.engine.ai.commanded.Commander`，供模擬與 CLI 使用；LLM 指揮官
（Phase 3）接同一個介面。:data:`COMMANDER_FACTORIES` 的每個值每場戰鬥新建一個指揮官（有些需要
記住戰鬥開始時的資訊），所以 :class:`CommandedPolicyFactory` 只存 ID，可以 pickle
（``--jobs > 1``）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import AiProfileTable
from trpg.engine.ai import Policy
from trpg.engine.ai.commanded import CommandedAI, Commander, OrderObserver
from trpg.engine.ai.orders import (
    FocusTarget,
    HoldPosition,
    OrderSet,
    Protect,
    TacticalOrder,
    UseEnvironment,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.rules.combat import is_concealed
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Team, UnitId

__all__ = [
    "COMMANDER_FACTORIES",
    "COMMANDER_IDS",
    "CommandedPolicyFactory",
    "FocusLowestHp",
    "HoldStart",
    "ProtectWeakest",
    "UseEnv",
    "build_commanded_ai",
    "describe_commander",
]


def _visible_enemies(state: BattleState, team: Team) -> list[UnitState]:
    """該陣營「看得見」的敵人：存活且未隱蔽（目前還沒有完整的視野過濾，Phase 3）。"""
    return [u for u in state.living_units() if u.team is not team and not is_concealed(state, u)]


class FocusLowestHp:
    """``focus_lowest_hp``：集火 HP 最低的可見敵人（平手依 ID）。"""

    def __call__(self, state: BattleState, team: Team) -> OrderSet | None:
        foes = _visible_enemies(state, team)
        if not foes:
            return OrderSet()
        target = min(foes, key=lambda u: (u.hp, u.id))
        return OrderSet(team_orders=(FocusTarget(target=target.id),))


class ProtectWeakest:
    """``protect_weakest``：全隊保護 HP 比例最低的友方（平手依 ID；隊伍只有一人時沒有指令）。"""

    def __call__(self, state: BattleState, team: Team) -> OrderSet | None:
        allies = [u for u in state.living_units() if u.team is team]
        if len(allies) < 2:  # noqa: PLR2004
            return OrderSet()
        ward = min(allies, key=lambda u: (Fraction(u.hp, u.max_hp), u.id))
        return OrderSet(team_orders=(Protect(ward=ward.id),))


class HoldStart:
    """``hold_start``：每個單位守在自己的起始格（radius 1）。起始格是第一次看到該單位時的位置
    （每場新建一個，所以記得的是這場戰鬥的起點）。"""

    def __init__(self) -> None:
        self._starts: dict[UnitId, tuple[int, int]] = {}

    def __call__(self, state: BattleState, team: Team) -> OrderSet | None:
        for u in state.living_units():
            if u.team is team:
                self._starts.setdefault(u.id, u.xy)
        orders: dict[UnitId, tuple[TacticalOrder, ...]] = {
            uid: (HoldPosition(at=xy, radius=1),)
            for uid, xy in sorted(self._starts.items())
            if state.units[uid].alive
        }
        return OrderSet(unit_orders=orders)


class UseEnv:
    """``use_env``：全隊 ``use_environment``。"""

    def __call__(self, state: BattleState, team: Team) -> OrderSet | None:
        return OrderSet(team_orders=(UseEnvironment(),))


COMMANDER_FACTORIES: dict[str, Callable[[], Commander]] = {
    "focus_lowest_hp": FocusLowestHp,
    "protect_weakest": ProtectWeakest,
    "hold_start": HoldStart,
    "use_env": UseEnv,
}
"""指揮官 ID → 每場戰鬥新建指揮官的工廠（模組層級的類別，可 pickle）。"""

COMMANDER_IDS: tuple[str, ...] = tuple(sorted(COMMANDER_FACTORIES))

_DESCRIPTIONS = {
    "focus_lowest_hp": "集火 HP 最低的可見敵人",
    "protect_weakest": "全隊保護 HP 比例最低的友方",
    "hold_start": "每個單位守在自己的起始格",
    "use_env": "全隊優先利用環境",
}


def describe_commander(commander_id: str) -> str:
    return _DESCRIPTIONS[commander_id]


def build_commanded_ai(
    profiles: AiProfileTable,
    *,
    ally: str | None = None,
    enemy: str | None = None,
    on_order: OrderObserver | None = None,
) -> CommandedAI:
    """新建一個效用 AI ＋ 指定指揮官的 :class:`CommandedAI`（ID 見 :data:`COMMANDER_IDS`）。"""
    commanders: dict[Team, Commander] = {}
    for team, commander_id in ((Team.ALLY, ally), (Team.ENEMY, enemy)):
        if commander_id is not None:
            commanders[team] = COMMANDER_FACTORIES[commander_id]()
    return CommandedAI(UtilityAI(profiles), commanders, on_order=on_order)


@dataclass(frozen=True)
class CommandedPolicyFactory:
    """每場戰鬥新建 :class:`CommandedAI`（可 pickle；``BatchSpec.policy_factory`` 用）。"""

    profiles: AiProfileTable
    ally: str | None = None
    enemy: str | None = None

    def __post_init__(self) -> None:
        for commander_id in (self.ally, self.enemy):
            if commander_id is not None and commander_id not in COMMANDER_FACTORIES:
                raise ValueError(
                    f"未知的指揮官：{commander_id}（可用：{', '.join(COMMANDER_IDS)}）"
                )

    def __call__(self) -> Policy:
        return build_commanded_ai(self.profiles, ally=self.ally, enemy=self.enemy)
