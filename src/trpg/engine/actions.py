"""玩家與 AI 提出的動作（pydantic discriminated union，以 ``type`` 區分）。

所有動作都帶 ``unit_id``（行動者），引擎會檢查是否輪到該單位。

:class:`Decision` 不是動作，而是對暫停中的 ``prompt`` 反應的回答（以 ``resume`` 送出）；
戰鬥紀錄中的步驟（:data:`Step`）是動作或決定。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from trpg.shared.types import ObjectId, Pos, UnitId

__all__ = [
    "ACTION_ADAPTER",
    "ACTION_LIST_ADAPTER",
    "STEP_ADAPTER",
    "STEP_LIST_ADAPTER",
    "Action",
    "Attack",
    "Decision",
    "Defend",
    "EndTurn",
    "Interact",
    "Move",
    "Shove",
    "Step",
    "Trip",
]


class _ActionBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: UnitId


class Move(_ActionBase):
    """沿 ``path`` 移動（不花 AP）。``path[0]`` 必須是目前位置，之後每一步都相鄰。

    倒地的單位移動前會先站起（消耗一半移動點數）；倒地時 ``path`` 可以只有起點，表示只站起來。
    途中滑倒（冰面）、倒下或撤離時停止。
    """

    type: Literal["move"] = "move"
    path: tuple[Pos, ...] = Field(min_length=1)

    @property
    def dest(self) -> Pos:
        return self.path[-1]


class Attack(_ActionBase):
    """以武器普攻單位 ``target_id`` 或物件 ``target_object_id``（恰好給一個）。

    攻擊物件一律命中（不擲命中骰、不暴擊），物件必須帶 ``breakable``。
    """

    type: Literal["attack"] = "attack"
    target_id: UnitId | None = None
    target_object_id: ObjectId | None = None

    @model_validator(mode="after")
    def _one_target(self) -> Attack:
        if (self.target_id is None) == (self.target_object_id is None):
            raise ValueError("Attack 必須恰好指定 target_id 或 target_object_id 其中之一")
        return self


class Defend(_ActionBase):
    """防禦姿態：防禦值 +25%，到自己的下回合開始。"""

    type: Literal["defend"] = "defend"


class Shove(_ActionBase):
    """推擊（技巧動作）：相鄰敵人，力量對抗；成功時沿「行動者 → 目標」方向推 1 格。"""

    type: Literal["shove"] = "shove"
    target_id: UnitId


class Trip(_ActionBase):
    """絆倒（技巧動作）：相鄰敵人，敏捷對抗；成功時目標倒地。"""

    type: Literal["trip"] = "trip"
    target_id: UnitId


class Interact(_ActionBase):
    """互動：推動相鄰的 ``pushable`` 物件 1 格（沿「行動者 → 物件」方向）。"""

    type: Literal["interact"] = "interact"
    object_id: ObjectId
    mode: Literal["push"] = "push"


class EndTurn(_ActionBase):
    """結束回合。"""

    type: Literal["end_turn"] = "end_turn"


type Action = Annotated[
    Move | Attack | Defend | Shove | Trip | Interact | EndTurn, Field(discriminator="type")
]

ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)
ACTION_LIST_ADAPTER: TypeAdapter[list[Action]] = TypeAdapter(list[Action])


class Decision(BaseModel):
    """對 ``prompt`` 反應的回答：``unit_id`` 為被詢問的反應者，``accept`` 是否使用反應。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["decision"] = "decision"
    unit_id: UnitId
    accept: bool


type Step = Annotated[
    Move | Attack | Defend | Shove | Trip | Interact | EndTurn | Decision,
    Field(discriminator="type"),
]
"""戰鬥紀錄中的一步：動作（``resolve``）或決定（``resume``）。"""

STEP_ADAPTER: TypeAdapter[Step] = TypeAdapter(Step)
STEP_LIST_ADAPTER: TypeAdapter[list[Step]] = TypeAdapter(list[Step])
