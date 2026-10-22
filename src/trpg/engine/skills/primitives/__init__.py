"""效果原語的登錄表（Phase 3E-2b）：原語 ID → handler。

每個 ``content/skill_primitives.yaml`` 的原語在這裡恰好有一個 handler（``(施放, 解析後的效果,
效果設定) → 效果列表``，見 :data:`~trpg.engine.skills.primitives.base.Handler`）。
:meth:`trpg.engine.skills.cast.Cast.build` 只查這張表，沒有預設分支：表裡沒有的原語會拋出
``KeyError``；載入內容時 :func:`trpg.primitive_coverage.check_primitive_coverage` 先檢查
YAML 的每個原語都有登錄（另外也檢查預算、AI 估值、敘事、預覽）。

模組：``numeric``（傷害、治療、護盾、淨化）、``displacement``（位移與場景物件）、``statuses``
（狀態與層數）、``rule_rewrites``（改寫規則型與資源）、``summoning``（召喚與放置）、``terrain``
（地形）、``deferred``（在別的時間點結算或不在效果位置展開的原語）。
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from trpg.engine.skills.primitives import (
    deferred,
    displacement,
    numeric,
    rule_rewrites,
    statuses,
    summoning,
    terrain,
)
from trpg.engine.skills.primitives.base import Handler

__all__ = ["PRIMITIVE_HANDLERS", "Handler", "primitive_handler"]


def _merge(*tables: Mapping[str, Handler]) -> Mapping[str, Handler]:
    merged: dict[str, Handler] = {}
    for table in tables:
        for kind, handler in table.items():
            if kind in merged:
                raise ValueError(f"原語 {kind} 登錄了兩個 handler")
            merged[kind] = handler
    return MappingProxyType(dict(sorted(merged.items())))


PRIMITIVE_HANDLERS: Mapping[str, Handler] = _merge(
    numeric.HANDLERS,
    displacement.HANDLERS,
    statuses.HANDLERS,
    rule_rewrites.HANDLERS,
    summoning.HANDLERS,
    terrain.HANDLERS,
    deferred.HANDLERS,
)
"""原語 ID → handler（依 ID 排序、唯讀）。"""


def primitive_handler(kind: str) -> Handler:
    """原語 ``kind`` 的 handler；沒有登錄時拋出 ``KeyError``（不會靜默略過）。"""
    try:
        return PRIMITIVE_HANDLERS[kind]
    except KeyError:
        raise KeyError(f"原語 {kind} 沒有解譯器 handler（trpg.engine.skills.primitives）") from None
