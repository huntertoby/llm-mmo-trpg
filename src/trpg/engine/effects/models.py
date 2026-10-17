"""效果（effect）的資料模型。

動作展開為效果，放入佇列逐一結算（``docs/專案計畫.md`` 5.9）。每個效果帶 ``depth``：
由動作直接產生的為 0，由事件觸發的為觸發來源的 ``depth + 1``。

新增效果類型（Phase 1B、Phase 2 的原語）：在這裡新增 model 並加入 :data:`Effect`，
再以 :func:`trpg.engine.effects.queue.register_effect` 註冊處理器。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.content.battle import Dice
from trpg.engine.events import DamageCause, MoveMode
from trpg.shared.types import Element, Pos, UnitId

__all__ = [
    "EFFECT_LIST_ADAPTER",
    "ApplyStatusEffect",
    "DamageEffect",
    "Effect",
    "EffectBase",
    "HealEffect",
    "MoveUnitEffect",
    "RemoveStatusEffect",
]


class EffectBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    depth: int = Field(default=0, ge=0)
    source_id: UnitId | None = None

    # 佇列排序用（同一時刻產生的效果依「來源單位 ID → 目標 ID → 格子座標」排序）
    def sort_target(self) -> str:
        return ""

    def sort_pos(self) -> tuple[int, int]:
        return (-1, -1)


class DamageEffect(EffectBase):
    """傷害。

    ``mode``：

    - ``roll``：``(骰子 ＋ flat ＋ scaled_permille ÷ 1000) × 元素修正``，無條件捨去，
      最低 ``min_damage``；``crit`` 時骰子顆數加倍、固定值不加倍。
    - ``percent_max_hp``：最大 HP × ``permille`` ÷ 1000（無條件捨去，最低 ``min_damage``）。
    - ``lethal``：直接把 HP 降為 0（致命地形）。

    ``apply_element_mod=False`` 時不套用元素修正（墜落、致命地形等以最大 HP 比例計算的傷害）。
    """

    kind: Literal["damage"] = "damage"
    target_id: UnitId
    cause: DamageCause = "effect"
    element: Element = Element.PHYSICAL
    mode: Literal["roll", "percent_max_hp", "lethal"] = "roll"
    dice: Dice | None = None
    flat: int = 0
    scaled_permille: int = 0
    crit: bool = False
    permille: int = Field(default=0, ge=0)
    apply_element_mod: bool = True
    min_damage: int = Field(default=1, ge=0)

    def sort_target(self) -> str:
        return self.target_id


class HealEffect(EffectBase):
    """治療：``骰子 ＋ flat``，不超過最大 HP；倒下的單位不能被治療（Phase 1 沒有復活）。"""

    kind: Literal["heal"] = "heal"
    target_id: UnitId
    dice: Dice | None = None
    flat: int = 0

    def sort_target(self) -> str:
        return self.target_id


class MoveUnitEffect(EffectBase):
    """把單位移到 ``dest``。

    - ``walk``：主動移動的一步（合法性已由 ``Move`` 動作檢查；可暫時穿過友方）。
    - ``forced``：強制位移；目的地有其他單位或超出地圖時不移動（``move_blocked``）。
    - ``teleport``：傳送；不觸發墜落。

    ``walk`` 與 ``forced`` 往下落差達門檻時觸發墜落；進入致命地形時觸發致命地形規則。
    """

    kind: Literal["move_unit"] = "move_unit"
    unit_id: UnitId
    dest: tuple[int, int]
    mode: MoveMode = "forced"
    cost: int = 0

    def sort_target(self) -> str:
        return self.unit_id

    def sort_pos(self) -> tuple[int, int]:
        return (self.dest[1], self.dest[0])

    @property
    def dest_pos(self) -> Pos:
        return Pos(x=self.dest[0], y=self.dest[1])


class ApplyStatusEffect(EffectBase):
    """施加狀態；``duration`` 為 ``None`` 時使用狀態定義的預設值。重複施加時刷新持續時間。"""

    kind: Literal["apply_status"] = "apply_status"
    target_id: UnitId
    status_id: str
    duration: int | None = Field(default=None, ge=1)

    def sort_target(self) -> str:
        return self.target_id


class RemoveStatusEffect(EffectBase):
    """移除狀態（不存在時沒有效果）。"""

    kind: Literal["remove_status"] = "remove_status"
    target_id: UnitId
    status_id: str
    reason: Literal["expired", "removed", "stood_up"] = "removed"

    def sort_target(self) -> str:
        return self.target_id


type Effect = Annotated[
    DamageEffect | HealEffect | MoveUnitEffect | ApplyStatusEffect | RemoveStatusEffect,
    Field(discriminator="kind"),
]

EFFECT_LIST_ADAPTER: TypeAdapter[list[Effect]] = TypeAdapter(list[Effect])
