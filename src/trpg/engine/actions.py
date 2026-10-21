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
    "Aim",
    "Attack",
    "Decision",
    "Defend",
    "Direction",
    "EndStance",
    "EndTurn",
    "FollowupTarget",
    "Interact",
    "Move",
    "Run",
    "SetReactionMode",
    "Shove",
    "Step",
    "Swap",
    "Trip",
    "UseSkill",
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
    """守護（Phase 3-21a，玩法 #24；內部 ID 仍為 ``defend``）：防禦值 +25%，到自己的下回合開始。

    ``target_id`` 為 ``None`` 時守護自己；給相鄰隊友時，敵人以單體攻擊該隊友、且自己仍與他相鄰
    時，改由自己承受（每輪上限 ``guard_transfers_per_round``，範圍技能不轉移）。
    """

    type: Literal["defend"] = "defend"
    target_id: UnitId | None = None


class Run(_ActionBase):
    """跑步（基本動作，Phase 3-20）：花 ``run_ap_cost`` AP，本回合移動點數 ``+run_move_bonus`` 格；
    每回合限 1 次，定身時不合法。跑步本身不移動。"""

    type: Literal["run"] = "run"


class Swap(_ActionBase):
    """換位（Phase 3-21a）：與相鄰的我方單位（含召喚物）互換位置；朝向不變，不觸發藉機攻擊。"""

    type: Literal["swap"] = "swap"
    target_id: UnitId


class Aim(_ActionBase):
    """瞄準（Phase 3-21a）：本回合下一次需要擲命中的攻擊（普攻或技能）命中 ``+aim_hit_bonus``；
    不疊加，回合結束或用掉即失效。"""

    type: Literal["aim"] = "aim"


class Shove(_ActionBase):
    """推擊（技巧動作）：相鄰敵人，力量對抗；成功時沿「行動者 → 目標」方向推 1 格。"""

    type: Literal["shove"] = "shove"
    target_id: UnitId


class Trip(_ActionBase):
    """絆倒（技巧動作）：相鄰敵人，敏捷對抗；成功時目標倒地。"""

    type: Literal["trip"] = "trip"
    target_id: UnitId


class Interact(_ActionBase):
    """互動：移動相鄰的 ``pushable`` 物件 1 格（只對物件，不能對單位）。

    - ``mode="push"``（預設）：沿「行動者 → 物件」方向推，``side`` 必須為 ``None``；
    - ``mode="shove_aside"``（撥開，Phase 3C-1）：往垂直於「行動者 → 物件」方向的 ``side``
      （``left`` 為逆時針 90°、``right`` 為順時針 90°；畫面上 ``north`` 為 ``y − 1``）移動，
      ``side`` 必填。行動者都不動、花 ``interact_ap_cost``。
    """

    type: Literal["interact"] = "interact"
    object_id: ObjectId
    mode: Literal["push", "shove_aside"] = "push"
    side: Literal["left", "right"] | None = None

    @model_validator(mode="after")
    def _check_side(self) -> Interact:
        if self.mode == "push" and self.side is not None:
            raise ValueError("推（push）不能指定 side")
        if self.mode == "shove_aside" and self.side is None:
            raise ValueError("撥開（shove_aside）必須指定 side（left 或 right）")
        return self


type Direction = Literal["north", "east", "south", "west"]
"""技能的方向（只有東南西北四個；``north`` 為 ``y − 1``）。"""


class FollowupTarget(BaseModel):
    """複合技能動作段的選取（Phase 3F-3a）：依動作段形狀的 ``targeting`` 給對應欄位——
    ``direction``（直線、錐形）、``target_id``／``target_object_id``（單體）；以落點為中心的形狀
    （十字、方陣、環）都不給（``target_pos`` 省略時為落點，給了也必須是落點）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_id: UnitId | None = None
    target_object_id: ObjectId | None = None
    target_pos: Pos | None = None
    direction: Direction | None = None


class UseSkill(_ActionBase):
    """使用技能（Phase 2A）。依形狀的 ``targeting`` 只允許對應的欄位：

    - ``unit``（單體、連鎖）：``target_id`` 或 ``target_object_id`` 恰好一個；
    - ``tile``（十字、方陣、指定格）：``target_pos``；
    - ``direction``（直線、錐形）：``direction``；
    - ``object_tile``（投擲物件）：``target_object_id`` 與 ``target_pos``；
    - ``unit_tile``（傳送他人，Phase 3D-2b）：``target_id``（被傳送的單位）與 ``target_pos``
      （落點）；
    - ``unit_pair``（任意兩者互換，Phase 3D-2b）：``target_id`` 與 ``second_target_id``（兩個不同的
      單位，順序不拘）；
    - ``self``／``none``（自身、環形、範圍光環）：都不給。

    複合技能（Phase 3F-3a）：上面的欄位是位移段的選取，``followup_target`` 是動作段的選取。

    是否合法（欄位是否對應形狀、射程、視線、代價）由引擎檢查，不合法時拋出
    :class:`~trpg.shared.errors.IllegalActionError`。

    ``copy_cast``（Phase 3C-4b）：``copy_skill`` 技能複製的技能的選取（``skill_id`` 必須是目前
    可複製的技能，``unit_id`` 是同一個施放者，目標欄位依該技能的形狀）。玩家省略它時結算暫停，由
    :class:`Decision` 補上；AI 與戰鬥紀錄直接給出。其他技能不能帶 ``copy_cast``。
    """

    type: Literal["use_skill"] = "use_skill"
    skill_id: str
    target_id: UnitId | None = None
    target_object_id: ObjectId | None = None
    target_pos: Pos | None = None
    direction: Direction | None = None
    second_target_id: UnitId | None = None
    copy_cast: UseSkill | None = None
    followup_target: FollowupTarget | None = None
    """複合技能第二段的選取：「位移 → 動作」（Phase 3F-3a）以位移段的落點為原點；「動作 → 位移」
    「擊殺 → 接下一段」（Phase 3F-4a）從施放者第一段結算後的位置選（玩家省略時結算到第二段暫停，由
    :class:`Decision` 補上）；「聚集 → 範圍打擊」「命中 → 加碼段」由引擎決定，不能帶。其他技能
    不能帶。"""


class EndStance(_ActionBase):
    """取消目前的姿態（Phase 2E-2）：只能在自己的回合，免費（不花 AP）。"""

    type: Literal["end_stance"] = "end_stance"


class SetReactionMode(_ActionBase):
    """設定自己身上某條反應規則的模式（Phase 3-4b）：``auto`` 自動、``prompt`` 詢問、``off`` 關閉。

    不花 AP、不結束回合，只能在自己的回合使用，只能改自己身上已有的規則（``reaction`` 為反應 ID
    或反應技 ID；同一個反應的所有規則一併改）。**不列入** ``legal_actions``（AI 不使用），由
    :func:`trpg.engine.battle.reaction_mode_problem` 判斷合法。
    """

    type: Literal["set_reaction_mode"] = "set_reaction_mode"
    reaction: str
    mode: Literal["auto", "prompt", "off"]


class EndTurn(_ActionBase):
    """結束回合。"""

    type: Literal["end_turn"] = "end_turn"


type Action = Annotated[
    Move
    | Attack
    | UseSkill
    | Defend
    | Run
    | Swap
    | Aim
    | Shove
    | Trip
    | Interact
    | EndStance
    | SetReactionMode
    | EndTurn,
    Field(discriminator="type"),
]

ACTION_ADAPTER: TypeAdapter[Action] = TypeAdapter(Action)
ACTION_LIST_ADAPTER: TypeAdapter[list[Action]] = TypeAdapter(list[Action])


class Decision(BaseModel):
    """對暫停中的結算的回答：``unit_id`` 為被詢問者。

    - ``prompt`` 反應：``accept`` 是否使用反應；
    - ``copy_skill``（Phase 3C-4b）：``accept`` 為真時 ``copy_cast`` 必須給出複製技能的選取，為假則
      放棄施放（不付任何代價）；
    - ``followup``（Phase 3F-4a）：``accept`` 為真時 ``followup_target`` 必須給出複合技能第二段的
      選取，為假則放棄第二段（第一段已經結算）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["decision"] = "decision"
    unit_id: UnitId
    accept: bool
    copy_cast: UseSkill | None = None
    followup_target: FollowupTarget | None = None


type Step = Annotated[
    Move
    | Attack
    | UseSkill
    | Defend
    | Run
    | Swap
    | Aim
    | Shove
    | Trip
    | Interact
    | EndStance
    | SetReactionMode
    | EndTurn
    | Decision,
    Field(discriminator="type"),
]
"""戰鬥紀錄中的一步：動作（``resolve``）或決定（``resume``）。"""

STEP_ADAPTER: TypeAdapter[Step] = TypeAdapter(Step)
STEP_LIST_ADAPTER: TypeAdapter[list[Step]] = TypeAdapter(list[Step])
