"""效果佇列與處理器註冊表（``docs/phases/Phase1計畫.md`` 3.4）。

- 先入先出；同一時刻產生的多個效果依「來源單位 ID → 目標 ID → 格子座標 (y, x)」排序後入列
  （排序穩定：鍵相同時保留產生順序）。
- 每個效果結算後產生事件；事件經 :mod:`trpg.engine.triggers` 對照表觸發新效果，``depth + 1``。
- ``depth`` 超過 ``max_chain_depth`` 的效果不入列，改產生 ``chain_limit_reached`` 事件。
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence

from trpg.engine import triggers
from trpg.engine.context import Ctx
from trpg.engine.effects.models import Effect, EffectBase
from trpg.engine.events import ChainLimitReached, EventBase
from trpg.shared.errors import TrpgError

__all__ = ["EffectHandler", "execute", "handler_for", "register_effect", "sort_effects"]

type EffectHandler = Callable[[Ctx, EffectBase], list[EventBase]]

_HANDLERS: dict[str, EffectHandler] = {}


def register_effect(kind: str) -> Callable[[EffectHandler], EffectHandler]:
    """註冊效果處理器：``@register_effect("damage")``。同一 ``kind`` 不可重複註冊。"""

    def decorator(handler: EffectHandler) -> EffectHandler:
        if kind in _HANDLERS:
            raise TrpgError(f"效果類型 {kind!r} 已註冊")
        _HANDLERS[kind] = handler
        return handler

    return decorator


def handler_for(kind: str) -> EffectHandler:
    try:
        return _HANDLERS[kind]
    except KeyError:
        raise TrpgError(f"未註冊的效果類型：{kind!r}") from None


def _effect_kind(effect: EffectBase) -> str:
    kind = getattr(effect, "kind", None)
    if not isinstance(kind, str):
        raise TrpgError(f"效果缺少 kind：{effect!r}")
    return kind


def sort_effects[T: EffectBase](effects: Sequence[T]) -> list[T]:
    """依「來源單位 ID → 目標 ID → 格子座標 (y, x)」穩定排序。"""
    return sorted(effects, key=lambda e: (e.source_id or "", e.sort_target(), e.sort_pos()))


def execute(ctx: Ctx, effects: Sequence[Effect] | Sequence[EffectBase]) -> None:
    """把 ``effects`` 排序後入列並結算到佇列清空（含所有觸發的連鎖）。"""
    max_depth = ctx.core.max_chain_depth
    queue: deque[EffectBase] = deque()
    for effect in sort_effects(list(effects)):
        _enqueue(ctx, queue, effect, max_depth)
    while queue:
        effect = queue.popleft()
        produced = handler_for(_effect_kind(effect))(ctx, effect)
        follow_ups: list[EffectBase] = []
        for event in produced:
            follow_ups.extend(triggers.effects_for(ctx, event, effect.depth + 1))
        for follow_up in sort_effects(follow_ups):
            _enqueue(ctx, queue, follow_up, max_depth)


def _enqueue(ctx: Ctx, queue: deque[EffectBase], effect: EffectBase, max_depth: int) -> None:
    if effect.depth > max_depth:
        ctx.emit(ChainLimitReached, effect_kind=_effect_kind(effect), depth=effect.depth)
        return
    queue.append(effect)
