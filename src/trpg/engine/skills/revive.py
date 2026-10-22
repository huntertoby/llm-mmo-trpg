"""復活（Phase 3D-8b，``docs/design/06-技能.md`` 6.18 C）。

倒下的單位留在戰鬥狀態（``downed``，保留位置，但不占格子）。``revive`` 讓射程內倒下的友方站起來：

- 站回原位置；原格被占用、不能站立或是致命地形時，站到 ``core.revive_landing_radius`` 格內最近的
  空格（曼哈頓距離相同依 ``(y, x)`` 順序），範圍內都沒有空格就不能施放；
- 以最大 HP 的 ``hp_permille``‰（至少 1）站起來；每個單位每場最多被復活 1 次，召喚物不能被復活；
- 回到先攻順序中原本的名次（先攻值、再比敏捷；平手排在同值者之後），所以不一定馬上行動。倒下時
  已移除的狀態（姿態、以它為來源的嘲諷等）、陷阱、區域與召喚物不會恢復。

選取與可用性檢查（:func:`revive_target_problem`、:func:`revive_candidates`）只讀取狀態；實際結算
:func:`revive_unit` 修改狀態並產生事件。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.engine.events import EventBase, UnitRevived
from trpg.engine.rules.geometry import XY
from trpg.engine.rules.landing import nearest_free
from trpg.engine.rules.statuses import base_attribute
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Attribute, Pos

if TYPE_CHECKING:
    from trpg.engine.context import Ctx

__all__ = [
    "revivable",
    "revive_candidates",
    "revive_landing",
    "revive_target_problem",
    "revive_unit",
]

_PERMILLE = 1000


def revivable(unit: UnitState) -> bool:
    """倒下、可以被復活的單位：已倒下（不是撤離或消失）、不是召喚物、本場還沒被復活過。"""
    return (
        unit.downed
        and not unit.escaped
        and not unit.dismissed
        and not unit.is_summon
        and not unit.revived
    )


def revive_landing(state: BattleState, unit: UnitState) -> XY | None:
    """被復活的單位站的格子：原位置可站就用原位置，否則半徑內最近的空格（曼哈頓距離相同依
    ``(y, x)``）；沒有就是 ``None``。"""
    return nearest_free(state, unit.xy, radius=state.ruleset.core.revive_landing_radius)


def revive_target_problem(state: BattleState, caster: UnitState, target: UnitState) -> str | None:
    """``target`` 不能被 ``caster`` 復活的原因（繁體中文）；可以時為 ``None``（射程與視線另查）。"""
    if target.team is not caster.team:
        return f"只能復活友方：{target.name_zh}"
    if target.is_summon:
        return f"召喚物不能被復活：{target.name_zh}"
    if not target.downed or target.escaped or target.dismissed:
        return f"{target.name_zh} 沒有倒下，不需要復活"
    if target.revived:
        return f"{target.name_zh} 在這場戰鬥已經被復活過一次"
    if revive_landing(state, target) is None:
        return f"{target.name_zh} 周圍沒有可以站起來的空格"
    return None


def revive_candidates(state: BattleState, caster: UnitState) -> list[UnitState]:
    """可以被 ``caster`` 復活的倒下友方（依單位 ID；射程與視線另外檢查）。"""
    return [
        u
        for u in state.units_sorted()
        if u.team is caster.team and u.downed and revive_target_problem(state, caster, u) is None
    ]


def _order_index(state: BattleState, unit: UnitState) -> int:
    """回到先攻順序的位置：第一個名次（先攻值，再比敏捷）嚴格低於自己的單位之前；沒有就排最後。"""
    mine = (unit.initiative, base_attribute(unit, Attribute.DEX))
    for index, uid in enumerate(state.turn_order):
        other = state.units[uid]
        if (other.initiative, base_attribute(other, Attribute.DEX)) < mine:
            return index
    return len(state.turn_order)


def _return_to_order(state: BattleState, unit: UnitState) -> None:
    index = _order_index(state, unit)
    state.turn_order.insert(index, unit.id)
    # 插在目前行動者之前（或正好在它的位置）時，目前位置往後移一格，維持指向同一個單位
    if index < state.turn_pos or (index == state.turn_pos and state.active_unit is not None):
        state.turn_pos += 1


def revive_unit(
    ctx: Ctx, caster: UnitState, target: UnitState, skill_id: str, hp_permille: int
) -> list[EventBase]:
    """復活 ``target``（呼叫端已檢查 :func:`revive_target_problem`）：站起來、回到先攻順序，產生
    ``unit_revived``。選取之後狀態不會變，但仍保險地再檢查一次，不合法就什麼都不做。"""
    state = ctx.state
    landing = revive_landing(state, target) if revivable(target) else None
    if landing is None:
        return []
    from_pos = target.pos
    target.downed = False
    target.revived = True
    target.hp = max(1, target.max_hp * hp_permille // _PERMILLE)
    target.pos = Pos(x=landing[0], y=landing[1])
    _return_to_order(state, target)
    return [
        ctx.emit(
            UnitRevived,
            unit_id=target.id,
            source_id=caster.id,
            skill_id=skill_id,
            hp=target.hp,
            pos=target.pos,
            from_pos=from_pos,
        )
    ]
