"""召喚（Phase 3D-4a，``docs/design/06-技能.md`` 6.16 B）。

- 召喚物由 ``summon`` 原語在 ``ground_tile`` 選的空格產生（範本在規則包的 ``summons``，
  ``content/units/summons/``），屬於召喚者陣營，``owner_id`` 記錄召喚者，由效用 AI 控制。
- **行動順序**：插在先攻順序中召喚者之後（同一召喚者已有的召喚物之後），不擲先攻；召喚者在
  自己的回合施放時，召喚物這一輪就緊接著行動。
- **持續**：``summon_expires_round`` ＝ 施放輪 ＋ ``duration``；召喚者在那一輪（或之後）的回合結束
  時消失（:func:`expire_summons`），所以召喚物恰好行動 ``duration`` 次（召喚者被跳過回合也照常
  倒數）。召喚者倒下或撤離時一併消失（:mod:`trpg.engine.lifecycle`）。
- **上限**：同一召喚者同時存在的召喚物超過 ``summon_limit_per_owner`` 時，最舊的先消失。
- 召喚物沒有源力、不取用源泉、不計入勝負條件、不能撤離（各自的規則模組檢查 ``is_summon``）。
- **圖騰**（Phase 3D-4b，範本的 ``totem``）：沒有 AP（不移動、不攻擊），自己的回合開始時讓範圍內的
  友方獲得狀態（:func:`pulse_totem`）。
- 消失的召喚物保留在 ``units`` 中（``dismissed``），事件與紀錄仍可引用它的名字。
"""

from __future__ import annotations

from trpg.content.battle import TotemSpec
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect
from trpg.engine.events import EffectFizzled, EventBase, TotemPulsed, UnitSummoned
from trpg.engine.lifecycle import dismiss_summon, make_unit, summons_of
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.skills.targeting import summon_site_problem
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Pos, UnitId

__all__ = ["expire_summons", "pulse_totem", "summon_unit", "totem_of"]


def _order_index(state: BattleState, owner_id: UnitId) -> int:
    """新召喚物在先攻順序中的位置：召喚者之後、同一召喚者已有的召喚物之後。"""
    order = state.turn_order
    if owner_id not in order:
        return len(order)
    index = order.index(owner_id) + 1
    while index < len(order) and state.units[order[index]].owner_id == owner_id:
        index += 1
    return index


def _insert_in_order(state: BattleState, uid: UnitId, index: int) -> None:
    state.turn_order.insert(index, uid)
    # 插在目前位置之前（或正好插在行動者的位置）時，目前位置往後移一格，維持指向同一個單位
    if index < state.turn_pos or (index == state.turn_pos and state.active_unit is not None):
        state.turn_pos += 1


def summon_unit(  # noqa: PLR0917
    ctx: Ctx,
    owner: UnitState,
    template_id: str,
    xy: XY,
    duration: int,
    skill_id: str,
    *,
    order_index: int | None = None,
    orphan: bool = False,
) -> list[EventBase]:
    """``owner`` 在 ``xy`` 召喚 ``template_id``，持續 ``duration`` 輪。位置不合法或範本不存在時
    發出 ``effect_fizzled``；超過上限時先讓最舊的召喚物消失。

    ``order_index``／``orphan``（Phase 3D-6，``on_downed_spawn``）：召喚者已倒下，分身排在指定的
    先攻位置，``unit_summoned`` 標記 ``orphan``（到期改在環境回合處理）。"""
    state = ctx.state
    try:
        summon = state.ruleset.summon_def(template_id)
    except KeyError:
        pos = Pos(x=xy[0], y=xy[1])
        return [ctx.emit(EffectFizzled, effect_kind="summon", pos=pos, reason="unknown_summon")]
    if summon_site_problem(state, xy) is not None:
        pos = Pos(x=xy[0], y=xy[1])
        return [ctx.emit(EffectFizzled, effect_kind="summon", pos=pos, reason="summon_blocked")]
    events: list[EventBase] = []
    existing = summons_of(ctx, owner.id)
    limit = ctx.core.summon_limit_per_owner
    while len(existing) >= limit:
        events += dismiss_summon(ctx, existing.pop(0), "limit")
    uid = UnitId(f"unit_{len(state.units) + 1:04d}")
    same = sum(1 for u in state.units.values() if u.template_id == template_id)
    unit = make_unit(
        uid,
        template=summon.template,
        weapon=summon.weapon,
        team=owner.team,
        pos=Pos(x=xy[0], y=xy[1]),
        name=f"{summon.template.name_zh}{same + 1}",
        rules=state.ruleset,
    )
    unit.owner_id = owner.id
    unit.summon_expires_round = state.round + duration
    unit.initiative = owner.initiative  # 不擲先攻：顯示用，順序由插入位置決定
    state.units[uid] = unit
    index = _order_index(state, owner.id) if order_index is None else order_index
    _insert_in_order(state, uid, index)
    events.append(
        ctx.emit(
            UnitSummoned,
            unit_id=uid,
            owner_id=owner.id,
            template_id=template_id,
            team=owner.team,
            pos=unit.pos,
            skill_id=skill_id,
            expires_round=unit.summon_expires_round,
            order_index=index,
            orphan=orphan,
        )
    )
    return events


def expire_summons(ctx: Ctx, owner: UnitState) -> list[EventBase]:
    """召喚者的回合結束：到期（``summon_expires_round`` ≤ 目前輪數）的召喚物消失。"""
    events: list[EventBase] = []
    for summon in summons_of(ctx, owner.id):
        expires = summon.summon_expires_round
        if expires is not None and expires <= ctx.state.round:
            events += dismiss_summon(ctx, summon, "expired")
    return events


def totem_of(state: BattleState, unit: UnitState) -> TotemSpec | None:
    """``unit`` 是圖騰時回傳它的光環規格，否則 ``None``。"""
    if not unit.is_summon:
        return None
    try:
        return state.ruleset.summon_def(unit.template_id).template.totem
    except KeyError:
        return None


def totem_targets(state: BattleState, totem: UnitState, spec: TotemSpec) -> list[UnitState]:
    """光環範圍內的友方（含圖騰所在格的距離 0；不含圖騰自己與其他圖騰），依單位 ID 排序。"""
    return [
        u
        for u in state.units_sorted()
        if u.alive
        and u.team is totem.team
        and u.id != totem.id
        and totem_of(state, u) is None
        and manhattan(u.xy, totem.xy) <= spec.radius
    ]


def pulse_totem(ctx: Ctx, totem: UnitState) -> None:
    """圖騰的回合開始：範圍內的友方獲得（或刷新）光環狀態；範圍內沒有友方時不發事件。"""
    spec = totem_of(ctx.state, totem)
    if spec is None:
        return
    targets = totem_targets(ctx.state, totem, spec)
    if not targets:
        return
    ctx.emit(
        TotemPulsed,
        unit_id=totem.id,
        status_id=spec.status,
        duration=spec.duration,
        radius=spec.radius,
        targets=[u.id for u in targets],
    )
    execute(
        ctx,
        [
            ApplyStatusEffect(
                target_id=u.id, status_id=spec.status, duration=spec.duration, source_id=totem.id
            )
            for u in targets
        ],
    )
