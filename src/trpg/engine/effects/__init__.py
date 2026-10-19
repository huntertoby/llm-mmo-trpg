"""效果佇列與效果類型。

- :mod:`~trpg.engine.effects.models`：效果的資料模型（``Effect`` union）。
- :mod:`~trpg.engine.effects.queue`：佇列、處理器註冊表（``register_effect``）。
- :mod:`~trpg.engine.effects.handlers`：單位效果的處理器（匯入本套件時自動註冊）。
- :mod:`~trpg.engine.effects.world`：Phase 1B 的環境效果處理器（物件、表面、地形、推擊、產生單位）。
- 互動表的觸發函式在 :mod:`trpg.engine.interactions`（同樣在匯入本套件時註冊）。

:func:`run_effects` 是給測試用的內部 API：直接把效果放進佇列執行，不需要技能系統。
"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.engine import interactions as _interactions
from trpg.engine.context import Ctx
from trpg.engine.effects import handlers as _handlers
from trpg.engine.effects import world as _world
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    ChangeTileEffect,
    CleanseEffect,
    CreateObstacleEffect,
    CreateSurfaceEffect,
    DamageEffect,
    DamageObjectEffect,
    DestroyObjectEffect,
    Effect,
    EffectBase,
    ElementTouchEffect,
    ExplodeEffect,
    HealEffect,
    HurlObjectEffect,
    IgniteObjectEffect,
    LowerTerrainEffect,
    MoveUnitEffect,
    PushEffect,
    RaiseTerrainEffect,
    RemoveStatusEffect,
    ShieldEffect,
    SpawnUnitEffect,
    SwapUnitsEffect,
)
from trpg.engine.effects.queue import execute, register_effect
from trpg.engine.results import ResolveResult
from trpg.engine.state import BattleState

__all__ = [
    "ApplyStatusEffect",
    "ChangeTileEffect",
    "CleanseEffect",
    "CreateObstacleEffect",
    "CreateSurfaceEffect",
    "DamageEffect",
    "DamageObjectEffect",
    "DestroyObjectEffect",
    "Effect",
    "EffectBase",
    "ElementTouchEffect",
    "ExplodeEffect",
    "HealEffect",
    "HurlObjectEffect",
    "IgniteObjectEffect",
    "LowerTerrainEffect",
    "MoveUnitEffect",
    "PushEffect",
    "RaiseTerrainEffect",
    "RemoveStatusEffect",
    "ShieldEffect",
    "SpawnUnitEffect",
    "SwapUnitsEffect",
    "execute",
    "register_effect",
    "run_effects",
]

del _handlers, _interactions, _world  # 只為了註冊處理器與觸發函式


def run_effects(state: BattleState, effects: Sequence[EffectBase]) -> ResolveResult:
    """在 ``state`` 的複本上結算 ``effects``（含連鎖），回傳新狀態與事件；不修改 ``state``。

    結算後檢查勝負；若行動者在過程中倒下，會接著開始下一位的回合（與 ``resolve`` 相同）。
    """
    # 延遲匯入：turns 依賴本套件（execute），頂層匯入會形成循環。
    from trpg.engine.turns import finish_resolution  # noqa: PLC0415

    ctx = Ctx(state.clone())
    execute(ctx, effects)
    return finish_resolution(ctx)
