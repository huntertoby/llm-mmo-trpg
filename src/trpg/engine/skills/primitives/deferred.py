"""在效果的位置不展開、或由施放流程在別的時間點結算的原語。

- ``dash``、``shadowstep``：一律最先結算（:meth:`~trpg.engine.skills.cast.Cast.dash`、
  :meth:`~trpg.engine.skills.cast.Cast.shadowstep`）。
- ``consume_stack``：命中判定之後、第一個效果之前消耗（``Cast.consume_stacks``）。
- ``gamble``：命中判定之後擲骰（``Cast.roll_gamble``）；在效果列表的位置（最後一個）結算擲出的分支。
- ``intercept``：反應機制（:mod:`trpg.engine.reactions`）。
- ``place_trap``：施放時放置陷阱（:func:`trpg.engine.traps.place_trap`），其餘效果等觸發時結算。
- ``rule_change``：常駐類傳說，施放＝啟動（:mod:`trpg.engine.activations`）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.engine.skills.primitives.base import Handler, no_effects

if TYPE_CHECKING:
    from trpg.content.skills import EffectSpec
    from trpg.engine.effects.models import EffectBase
    from trpg.engine.skills.cast import Cast
    from trpg.engine.skills.targeting import ResolvedEffect

__all__ = ["HANDLERS"]


def gamble(cast: Cast, _effect: ResolvedEffect, _spec: EffectSpec) -> list[EffectBase]:
    """``gamble`` 在效果列表的位置（最後一個）：結算擲出的分支（擲骰見 ``Cast.roll_gamble``）。"""
    cast.resolve_branch(cast.gamble_branch)
    return []


HANDLERS: dict[str, Handler] = {
    "dash": no_effects,
    "shadowstep": no_effects,
    "consume_stack": no_effects,
    "intercept": no_effects,
    "place_trap": no_effects,
    "rule_change": no_effects,
    "gamble": gamble,
}
