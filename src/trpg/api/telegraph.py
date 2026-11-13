"""環境預告的 API 版本（Phase 3-4b 6.8）。

以 **我方看得見的狀態**（:func:`trpg.engine.traps.strip_hidden_traps`）模擬下一次環境回合，所以
敵方的隱藏陷阱不會影響（也不會洩漏在）預告裡；回應不含亂數狀態。隱蔽且看不到資訊的單位，變化項目
不帶 HP、護盾、狀態（:func:`trpg.api.hidden_info.mask_telegraph_changes`，HID-1b）；帶著定時炸彈時
倒數與半徑不送、文字改通用的危險提示（:func:`_bomb_out`，HID-1c）。蓄力強招不是這三項，照 5.7 顯示。
"""

from __future__ import annotations

from trpg.api.hidden_info import hidden_unit_ids, mask_telegraph_changes
from trpg.api.schemas import (
    BombOut,
    BurningOut,
    ChargeOut,
    TelegraphChangeOut,
    TelegraphOut,
    UpcomingEventOut,
)
from trpg.content.library import ContentLibrary
from trpg.engine.environment import TelegraphBomb, TelegraphCharge, telegraph
from trpg.engine.lock_on import lock_blocker
from trpg.engine.state import BattleState
from trpg.engine.traps import strip_hidden_traps
from trpg.narrative.events import xy_text
from trpg.narrative.telegraph import bomb_text, change_text, charge_text, upcoming_text
from trpg.shared.types import Team, UnitId

__all__ = ["telegraph_out"]


def _bomb_out(state: BattleState, bomb: TelegraphBomb, hidden: frozenset[UnitId]) -> BombOut:
    """定時炸彈是狀態（5.1.2 第 7 條）：看不到資訊的攜帶者，倒數與半徑不送。"""
    fields = bomb.model_dump()
    if bomb.unit_id in hidden:
        fields.update(remaining=None, radius=None)
    return BombOut(**fields, text=bomb_text(state, bomb, hidden))


def _lock_blocker(
    state: BattleState, charge: TelegraphCharge, hidden: frozenset[UnitId]
) -> UnitId | None:
    """瞄準預告（RG-3）：現在射出會擋下這一擊的目標隊友（:func:`lock_blocker`）；觀看者看不到資訊的
    單位不送。"""
    if charge.lock_target_id is None:
        return None
    caster = state.units.get(UnitId(charge.unit_id))
    target = state.units.get(charge.lock_target_id)
    if caster is None or target is None or not target.alive:
        return None
    blocker = lock_blocker(state, caster, target)
    if blocker is None or blocker.id in hidden:
        return None
    return blocker.id


def telegraph_out(state: BattleState, library: ContentLibrary, team: Team) -> TelegraphOut:
    def template_name(template_id: str) -> str:
        template = library.units.get(template_id)
        return template_id if template is None else template.name_zh

    forecast = telegraph(strip_hidden_traps(state, team))
    hidden = hidden_unit_ids(state, team)
    burning = []
    for object_id, remaining in forecast.burning:
        obj = state.objects[object_id]
        name = state.ruleset.object_def(obj.kind).name_zh
        burning.append(
            BurningOut(
                object_id=object_id,
                pos=obj.pos,
                remaining=remaining,
                text=f"{name} {xy_text(obj.pos)} 還能燃燒 {remaining} 次環境回合",
            )
        )
    return TelegraphOut(
        round=forecast.round,
        changes=tuple(
            TelegraphChangeOut(
                **masked.model_dump(), text=change_text(state, masked, template_name, hidden)
            )
            for masked in mask_telegraph_changes(forecast.changes, hidden)
        ),
        burning=tuple(burning),
        bombs=tuple(_bomb_out(state, b, hidden) for b in forecast.bombs),
        charges=tuple(
            ChargeOut(
                **c.model_dump(),
                lock_blocker_id=_lock_blocker(state, c, hidden),
                text=charge_text(state, c),
            )
            for c in forecast.charges
        ),
        upcoming=tuple(
            UpcomingEventOut(
                round=e.round,
                kind=e.kind,
                tiles=tuple(e.positions()),
                text=upcoming_text(e, template_name),
            )
            for e in forecast.upcoming
        ),
    )
