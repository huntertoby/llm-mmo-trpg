"""技能附屬規格：消耗、敘事、來源與觸發。"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.conditions import ConditionSpec
from trpg.content.skills.constants import (
    _MAX_COOLDOWN,
    _PERMILLE,
    ON_CAST_TAG,
    ON_ENTER_SURFACE,
    ON_STATUS_APPLIED,
    SKELETON_IDS,
    DelayedRelease,
    FollowupWhen,
    Origin,
)
from trpg.content.skills.effects import EffectSpec, ShapeSpec
from trpg.shared.types import Surface


class SelfStatusCost(ContentModel):
    """自身狀態代價（Phase 2H-1）：施放結算完之後，施放者自己獲得 ``status``（不擲抵抗）。

    狀態在帶有者回合結束時倒數，所以施放當回合結束就會 −1：``duration`` 限制為 2–3
    （1 等於沒有效果），預算折抵用的「有效回合」＝ ``duration − 1``。允許的狀態與折抵見
    ``content/skill_budget.yaml`` 的 ``allowance.self_status``。
    """

    status: str = Field(pattern=ID_PATTERN)
    duration: int = Field(ge=2, le=3)


class SkillCost(ContentModel):
    """技能代價（``docs/phases/Phase2A計畫.md`` 3.5）。``hp_percent`` 是最大 HP 的千分比（‰）。"""

    mana: int = Field(default=0, ge=0)
    stamina: int = Field(default=0, ge=0)
    """耐力代價（Phase 3H-2，06 6.10）：武器技花耐力、法術技花法力（依類別，``skill_budget.yaml`` 的
    ``cost_resource``；內容庫與產生器檢查）。"""
    cooldown: int | None = Field(default=None, ge=1, le=_MAX_COOLDOWN)
    uses_per_battle: int | None = Field(default=None, ge=1)
    hp_percent: int | None = Field(default=None, ge=1, le=_PERMILLE - 1)
    stacks: int | None = Field(default=None, ge=1)
    """施放前至少要有幾層（Phase 2E-3）：對應技能裡 ``owner: self`` 的 ``consume_stack`` 的層數；
    不足時不可施放。需求本身不消耗層數（消耗由 ``consume_stack`` 負責）。"""
    self_status: SelfStatusCost | None = None
    """施放後施放者自己獲得的狀態（Phase 2H-1）；只有主動技能可以使用。"""
    overdraft: int | None = Field(default=None, ge=1, le=1)
    """透支（Phase 3-50，06 6.5）：施放後自己下一個回合少這麼多 AP（目前一招最多 1 AP，固定折抵見
    ``skill_budget.yaml`` 的 ``allowance.overdraft_permille``）；只有主動技能可以使用。"""
    source: int | None = Field(default=None, ge=1, le=2)
    """花費的源力（Phase 3C-4a，1 或 2）：只有傳說技能可以、而且必須有；源力不足時不能施放。"""
    on_miss: tuple[EffectSpec, ...] = ()
    """失手反噬（Phase 3D-7a，6.17 C）：攻擊沒命中（含自然 1）時對施放者結算的效果（至多 2 個，
    類型見 :data:`BACKLASH_TYPES`，對象只能是施放者自己）；命中則不結算。"""


class FollowupSpec(ContentModel):
    """複合技能的第二段（Phase 3F-3a，``docs/design/06-技能.md`` 6.23）：自己的骨架、形狀、效果與
    條件，照該骨架的規則檢查。``when`` 決定第二段何時、以哪裡為原點結算（:data:`FollowupWhen`）：

    - ``after_move``：施放者真的移動到位移段的落點時，以落點為原點結算；
    - ``after_action``（3F-4a）：第一段結算完、施放者還站著就結算（自身位移，從目前位置選落點）；
    - ``after_gather``（3F-4a）：第一段把敵人拉向聚集點，第二段以聚集點為中心結算；
    - ``on_kill``（3F-4a）：第一段讓敵人倒下才結算（從施放者的位置選目標）；
    - ``on_hit``（3F-4a）：第一段命中敵人才結算（自動對命中的同一個目標）；
    - ``delayed``（3F-4b）：延遲段——施放後施放者身上帶著「蓄力」狀態，``release`` 成立時以施放者
      當下的位置為中心結算（``next_turn``：施放者下回合開始時；``attacked``：到施放者下回合開始
      之前被敵人攻擊時）。"""

    when: FollowupWhen = "after_move"
    skeleton: str
    shape: ShapeSpec
    effects: tuple[EffectSpec, ...] = Field(min_length=1)
    condition: ConditionSpec | None = None
    release: DelayedRelease | None = None
    """延遲段（``when: delayed``，Phase 3F-4b）何時釋放；其他種類必須省略。"""

    @field_validator("skeleton")
    @classmethod
    def _skeleton(cls, value: str) -> str:
        if value not in SKELETON_IDS:
            raise ValueError(f"未知的骨架 {value!r}（可用：{', '.join(SKELETON_IDS)}）")
        return value


class NarrativeDef(ContentModel):
    concept: str = ""
    cast_flavor: str = ""


class Provenance(ContentModel):
    """技能的來源與歸屬（``docs/design/17-未來展望.md`` 17.5）；2A 只存不用。"""

    origin: Origin = "builtin"
    owner_id: str | None = None
    created_by: str | None = None
    parents: tuple[str, ...] = ()
    bound: bool = True
    tradeable: bool = False


class TriggerSpec(ContentModel):
    """被動技能的觸發設定（``docs/phases/Phase2E計畫.md`` 3.2）。

    - ``event``：``content/skill_triggers.yaml`` 的 ID。
    - ``n``：只有 ``every_n_hits`` 使用（2 或 3）。
    - ``target``：效果作用的單位——``self``（持有者）、``other``（該時機的另一方）或
      ``nearest_enemy``（Phase 3W-2b：``max_distance`` 格內離持有者最近的一名存活敵人，同距離
      取單位 ID 小的；範圍內沒有敵人就不觸發、不付代價；任何時機都能用，例如回合開始標記最近的
      敵人）。
    - ``max_per_round``：每輪最多觸發幾次（每輪開始時重設）。
    - ``max_distance``：``target: other`` 時，另一方與持有者的曼哈頓距離上限；``nearest_enemy``
      必填。
    - ``tag``：只有 ``on_cast_tag`` 使用且必填（施放帶這個標籤的技能；Phase 3C-3a）。
    - ``status``：只有 ``on_status_applied`` 使用，可省略（省略＝任何狀態）。
    - ``surface``：只有 ``on_enter_surface`` 使用，可省略（省略＝任何表面；Phase 3C-3b）。
    """

    event: str = Field(pattern=ID_PATTERN)
    n: int | None = None
    tag: str | None = Field(default=None, pattern=ID_PATTERN)
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    surface: Surface | None = None
    target: Literal["self", "other", "nearest_enemy"] = "self"
    max_per_round: int = Field(default=1, ge=1, le=3)
    max_distance: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _check(self) -> TriggerSpec:
        if self.event == "every_n_hits":
            if self.n not in (2, 3):
                raise ValueError(f"every_n_hits 的 n 必須是 2 或 3，收到 {self.n}")
        elif self.n is not None:
            raise ValueError(f"只有 every_n_hits 使用 n，{self.event} 不可填 n")
        if self.max_distance is not None and self.target == "self":
            raise ValueError("max_distance 只能搭配 target: other 或 nearest_enemy")
        if self.target == "nearest_enemy" and self.max_distance is None:
            raise ValueError("target: nearest_enemy 必須填 max_distance（找幾格內最近的敵人）")
        if self.event == ON_CAST_TAG:
            if self.tag is None:
                raise ValueError("on_cast_tag 必須填 tag")
        elif self.tag is not None:
            raise ValueError(f"只有 on_cast_tag 使用 tag，{self.event} 不可填 tag")
        if self.status is not None and self.event != ON_STATUS_APPLIED:
            raise ValueError(f"只有 on_status_applied 使用 status，{self.event} 不可填 status")
        if self.surface is not None and self.event != ON_ENTER_SURFACE:
            raise ValueError(f"只有 on_enter_surface 使用 surface，{self.event} 不可填 surface")
        if self.surface is Surface.NONE:
            raise ValueError("trigger.surface 不可為 none")
        return self
