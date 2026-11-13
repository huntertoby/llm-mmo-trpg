"""頭目部位的事件（PB-1a，``docs/design/05-戰鬥.md`` 5.12.2；:mod:`trpg.engine.part_breaks`）。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from trpg.engine.events.base import EventBase
from trpg.shared.types import UnitId


class PartDamaged(EventBase):
    """打中部位（緊接在那一次的 ``damage_dealt`` 之後）：部位扣掉頭目實際扣掉的 HP（R2）。"""

    type: Literal["part_damaged"] = "part_damaged"
    target_id: UnitId
    part_id: str
    name_zh: str
    amount: int
    hp_before: int
    hp_after: int


class PartBroken(EventBase):
    """部位破了（整場只一次）。``effects`` 是破壞效果的種類（依 ``on_break`` 的順序）；破的那一下
    頭目倒下時照發，但不結算效果（``applied: false``，T8）。``text_zh`` 是範本的
    ``break_text_zh``（沒寫為 ``None``）。"""

    type: Literal["part_broken"] = "part_broken"
    target_id: UnitId
    part_id: str
    name_zh: str
    effects: tuple[str, ...]
    applied: bool = True
    text_zh: str | None = None
    source_id: UnitId | None = None
    """打破它的單位（那一下傷害的來源）。"""


class SkillSealed(EventBase):
    """部位破壞封住了一招（``seal_skill``）：換技能組也不解除。``rounds``（GB-1c，T14）有值時是
    限時封招：從這一輪起封這麼多輪；永久封住時為 ``None``、不輸出。"""

    type: Literal["skill_sealed"] = "skill_sealed"
    unit_id: UnitId
    skill_id: str
    part_id: str
    rounds: int | None = Field(default=None, exclude_if=lambda v: v is None)


class PartStatDown(EventBase):
    """部位破壞的能力下降（``stat_down``）：``amount`` 是這一項的數值（格、點或‰），``total`` 是
    累計之後的值（``damage_dealt`` 是相乘後的倍率‰）。"""

    type: Literal["part_stat_down"] = "part_stat_down"
    unit_id: UnitId
    part_id: str
    stat: str
    amount: int
    total: int
