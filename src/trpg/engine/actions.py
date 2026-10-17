"""玩家與 AI 提出的動作（pydantic discriminated union，以 ``type`` 區分）。

所有動作都帶 ``unit_id``（行動者），引擎會檢查是否輪到該單位。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from trpg.shared.types import Pos, UnitId

__all__ = [
    "ACTION_ADAPTER",
    "ACTION_LIST_ADAPTER",
    "Action",
    "Attack",
    "Defend",
    "EndTurn",
    "Move",
]


class _ActionBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: UnitId


class Move(_ActionBase):
    """沿 ``path`` 移動（不花 AP）。``path[0]`` 必須是目前位置，之後每一步都相鄰。

    倒地的單位移動前會先站起（消耗一半移動點數）；倒地時 ``path`` 可以只有起點，表示只站起來。
    """

    type: Literal["move"] = "move"
    path: tuple[Pos, ...] = Field(min_length=1)

    @property
    def dest(self) -> Pos:
        return self.path[-1]


class Attack(_ActionBase):
    """以武器普攻 ``target_id``。"""

    type: Literal["attack"] = "attack"
    target_id: UnitId


class Defend(_ActionBase):
    """防禦姿態：防禦值 +25%，到自己的下回合開始。"""

    type: Literal["defend"] = "defend"


class EndTurn(_ActionBase):
    """結束回合。"""

    type: Literal["end_turn"] = "end_turn"


type Action = Annotated[Move | Attack | Defend | EndTurn, Field(discriminator="type")]

ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)
ACTION_LIST_ADAPTER: TypeAdapter[list[Action]] = TypeAdapter(list[Action])
