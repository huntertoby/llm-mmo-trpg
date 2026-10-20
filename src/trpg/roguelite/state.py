"""一輪的狀態（``RunState``）與節點、選擇的資料模型（Phase 3-5a）。

``RunState`` 是一輪進度的唯一真相，**可序列化**（存檔原樣寫入）：

- 主角：目前的單位範本 ``hero``（屬性與技能清單隨升級改變；其餘欄位沿用起始 build 的英雄）、
  等級與經驗、**目前 HP、法力、源力**（戰鬥之間不回復，0.11 G、K）。技能清單就是裝備（主動 ≤ 6、
  被動 ≤ 3、反應 ≤ 1、姿態 ≤ 1，``core.yaml`` 的 ``skill_slots``）；欄位滿時要替換或放棄。
- ``generated_skills``：主角目前裝備的 **生成技能定義**（隨機組合器的產物不在內容庫裡；讀檔與開戰時
  以 ``Ruleset.with_skills`` 加回規則包）。
- ``plan``：開局時以種子排好的每一場（地圖、敵人、戰鬥種子）；存進存檔，所以之後改了抽選方式，
  舊存檔的下一場仍然不變。
- ``node``：目前在等什麼（戰鬥／升級／營火／結束）；升級與重骰的候選 **連同完整技能定義**
  存在節點裡。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import UnitTemplate
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute

__all__ = [
    "BattleNode",
    "BattlePlan",
    "BattleRecord",
    "CampfireNode",
    "Choice",
    "EndedNode",
    "LeaveChoice",
    "LevelUpChoice",
    "LevelUpNode",
    "Node",
    "PickChoice",
    "RerollChoice",
    "RunState",
    "SkillOffer",
]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BattlePlan(_Model):
    """一場戰鬥的安排（開局時決定）。``index`` 從 1 起算；Boss 戰是最後一場。"""

    index: int = Field(ge=1)
    map_id: str
    enemies: tuple[str, ...]
    seed: int = Field(ge=0)
    boss: bool = False


class BattleRecord(_Model):
    """一場戰鬥的結果（歷程）。``state_digest`` 是戰鬥最終狀態 JSON 的 SHA-256（驗證重播一致）。"""

    index: int
    map_id: str
    boss: bool
    won: bool
    end_reason: str | None
    rounds: int
    steps: int
    hp: int
    mana: int
    source: int
    hero_downed: bool
    """主角在戰鬥中倒下（我方仍勝利時以 1 HP 繼續）。"""
    state_digest: str


class SkillOffer(_Model):
    """升級或重骰的技能候選。``off_route`` 是「偏離路線」候選的索引（縮放屬性與當時主角最高屬性
    不同；湊不到時為空）。"""

    reason: Literal["level_up", "reroll"]
    tier: int
    top_attribute: Attribute
    """產生候選時主角的最高屬性（並列時取六屬性順序的第一個）。"""
    candidates: tuple[SkillDef, ...]
    off_route: tuple[int, ...] = ()


class BattleNode(_Model):
    kind: Literal["battle"] = "battle"
    index: int = Field(ge=1)


class LevelUpNode(_Model):
    """升級：分配 ``points`` 屬性點，並從候選選 1 個（可跳過）。"""

    kind: Literal["level_up"] = "level_up"
    level: int
    points: int
    offer: SkillOffer


class CampfireNode(_Model):
    """營火（進入時已回滿 HP、法力並加源力）：可以重骰（得到 ``offer``）或離開。"""

    kind: Literal["campfire"] = "campfire"
    after_battle: int
    rerolls_left: int
    offer: SkillOffer | None = None


class EndedNode(_Model):
    kind: Literal["ended"] = "ended"
    victory: bool


type Node = Annotated[
    BattleNode | LevelUpNode | CampfireNode | EndedNode, Field(discriminator="kind")
]


class LevelUpChoice(_Model):
    """升級的選擇：``attributes`` 分配全部屬性點；``pick`` 為候選索引（``None`` ＝ 跳過）；
    欄位滿時 ``replace`` 指定要換掉的技能 ID。"""

    kind: Literal["level_up"] = "level_up"
    attributes: dict[Attribute, int] = Field(default_factory=dict)
    pick: int | None = None
    replace: str | None = None


class RerollChoice(_Model):
    """營火：重骰（產生一組新的候選）。"""

    kind: Literal["reroll"] = "reroll"


class PickChoice(_Model):
    """營火重骰後：選 1 個候選（``None`` ＝ 放棄），之後離開營火。"""

    kind: Literal["pick"] = "pick"
    pick: int | None = None
    replace: str | None = None


class LeaveChoice(_Model):
    """離開營火（有候選沒選時視為放棄）。"""

    kind: Literal["leave"] = "leave"


type Choice = Annotated[
    LevelUpChoice | RerollChoice | PickChoice | LeaveChoice, Field(discriminator="kind")
]


class RunState(_Model):
    """一輪的進度（見模組說明）。"""

    seed: int = Field(ge=0)
    build_id: str
    hero: UnitTemplate
    level: int = Field(ge=1)
    xp: int = Field(ge=0)
    hp: int = Field(ge=0)
    mana: int = Field(ge=0)
    source: int = Field(ge=0)
    generated_skills: tuple[SkillDef, ...] = ()
    plan: tuple[BattlePlan, ...]
    battles_done: int = 0
    """打完（打贏）的場數，含 Boss。"""
    levels_pending: int = 0
    """還沒處理的升級次數（一場升兩級時依序處理）。"""
    campfires_done: tuple[int, ...] = ()
    offers_made: int = 0
    """已產生的候選組數（衍生候選亂數串流的計數器）。"""
    history: tuple[BattleRecord, ...] = ()
    node: Node

    @property
    def max_hp(self) -> int:
        return self.hero.max_hp

    @property
    def max_mana(self) -> int:
        return self.hero.max_mana

    @property
    def ended(self) -> bool:
        return isinstance(self.node, EndedNode)

    def plan_of(self, index: int) -> BattlePlan:
        return self.plan[index - 1]

    def generated(self, skill_id: str) -> SkillDef | None:
        return next((s for s in self.generated_skills if s.id == skill_id), None)
