"""追離頭目遠的敵人（GB-3，T17；``docs/design/19-灰燼荒原與賽季主線.md`` 19.2.3「壓制站遠的人」3）。

行為模式的權重 ``prefer_far_from_leader``（占位；目前只有殼縫餘燼蜥的 ``ember_brood`` 有值）：

- **打誰**（:func:`far_target_extra`，由 ``scoring._preview_score`` 讀）：這次動作打到的敵人裡，
  離自己陣營的頭目（帶 ``boss`` 標籤、存活；有好幾名時取 ID 最小的）最近佔格最遠的那名的距離
  × 權重。
- **往哪走**（:func:`far_from_leader_extra`，位置價值的一項）：從這格現在就打得到的敵人裡，離頭目
  最遠的那名的距離 × 權重——所以移動候選偏向貼近站得遠的人。

軟偏好、不強制：近的敵人照樣打得到，只是分數比較低。沒有頭目或權重為 0 時一律 0。
"""

from __future__ import annotations

from collections.abc import Iterable

from trpg.content.environment import AiWeights
from trpg.engine.ids import BOSS_TAG
from trpg.engine.rules.combat import attack_problem
from trpg.engine.rules.footprint import dist_to
from trpg.engine.state import BattleState, UnitState

__all__ = ["far_from_leader_extra", "far_target_extra", "leader_of"]


def leader_of(state: BattleState, unit: UnitState) -> UnitState | None:
    """``unit`` 陣營的頭目（帶 ``boss`` 標籤、存活、不是自己；依 ID 取第一名）。"""
    for other in state.units_sorted():
        if other.id == unit.id or other.team is not unit.team or not other.alive:
            continue
        if BOSS_TAG in other.tags:
            return other
    return None


def _farthest(leader: UnitState, enemies: Iterable[UnitState]) -> int:
    return max((dist_to(leader, e.xy) for e in enemies), default=0)


def far_target_extra(
    state: BattleState, unit: UnitState, w: AiWeights, victims: Iterable[UnitState]
) -> int:
    """這次動作打到的敵人裡離頭目最遠的距離 × ``prefer_far_from_leader``。"""
    if not w.prefer_far_from_leader:
        return 0
    leader = leader_of(state, unit)
    if leader is None:
        return 0
    foes = [v for v in victims if v.team is not unit.team]
    return w.prefer_far_from_leader * _farthest(leader, foes)


def far_from_leader_extra(
    state: BattleState, unit: UnitState, w: AiWeights, enemies: list[UnitState]
) -> int:
    """位置價值：從 ``unit.xy`` 打得到的敵人裡離頭目最遠的距離 × ``prefer_far_from_leader``。"""
    if not w.prefer_far_from_leader:
        return 0
    leader = leader_of(state, unit)
    if leader is None:
        return 0
    reachable = [e for e in enemies if attack_problem(state, unit, e) is None]
    return w.prefer_far_from_leader * _farthest(leader, reachable)
