"""原語 handler 的型別與共用常數（各原語模組匯入；不匯入任何原語模組）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trpg.content.skills import EffectSpec
    from trpg.engine.effects.models import EffectBase
    from trpg.engine.skills.cast import Cast
    from trpg.engine.skills.targeting import ResolvedEffect

__all__ = ["TOUCHING_AFFECTS", "Handler", "no_effects"]

type Handler = Callable[[Cast, ResolvedEffect, EffectSpec], list[EffectBase]]
"""原語 handler：``(施放, 解析後的效果, 效果設定) → 交給效果佇列的效果``。直接結算的原語回傳
空列表。"""

TOUCHING_AFFECTS = ("enemies", "all", "tiles")
"""傷害效果的這些 ``affects`` 也會打到影響格中的可破壞物件，並補上沒被觸及的格子的元素觸及。"""


def no_effects(_cast: Cast, _effect: ResolvedEffect, _spec: EffectSpec) -> list[EffectBase]:
    """在效果的位置不做任何事的原語（在別處結算，見 :mod:`.deferred`）。"""
    return []
