"""環境預告的 API 版本（Phase 3-4b 6.8）。

以 **我方看得見的狀態**（:func:`trpg.engine.traps.strip_hidden_traps`）模擬下一次環境回合，所以
敵方的隱藏陷阱不會影響（也不會洩漏在）預告裡；回應不含亂數狀態。
"""

from __future__ import annotations

from trpg.api.schemas import (
    BombOut,
    BurningOut,
    TelegraphChangeOut,
    TelegraphOut,
    UpcomingEventOut,
)
from trpg.content.library import ContentLibrary
from trpg.engine.environment import telegraph
from trpg.engine.state import BattleState
from trpg.engine.traps import strip_hidden_traps
from trpg.narrative.events import xy_text
from trpg.narrative.telegraph import bomb_text, change_text, upcoming_text
from trpg.shared.types import Team

__all__ = ["telegraph_out"]


def telegraph_out(state: BattleState, library: ContentLibrary, team: Team) -> TelegraphOut:
    def template_name(template_id: str) -> str:
        template = library.units.get(template_id)
        return template_id if template is None else template.name_zh

    forecast = telegraph(strip_hidden_traps(state, team))
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
            TelegraphChangeOut(**c.model_dump(), text=change_text(state, c, template_name))
            for c in forecast.changes
        ),
        burning=tuple(burning),
        bombs=tuple(BombOut(**b.model_dump(), text=bomb_text(state, b)) for b in forecast.bombs),
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
