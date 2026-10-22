"""一輪的狀態（``RunState``）與節點、選擇的資料模型（Phase 3-5a）。

``RunState`` 是一輪進度的唯一真相，**可序列化**（存檔原樣寫入）：

- 開局（Phase 3-24b2）：``start``＝起始武器 ＋ 選的關鍵字（與開發者起始包 ID）；``build_id`` 只在以
  回歸範本（``content/sim/builds.yaml``）開局時有值（開發與測試用，玩家介面不提供）。
- ``behavior``：主角在這一輪用過的動作類型與次數（候選產生器的行為紀錄）。
- 主角：目前的單位範本 ``hero``（屬性與技能清單隨升級改變；其餘欄位沿用開局時的主角）、
  等級與經驗、**目前 HP、法力、源力**（戰鬥之間不回復，0.11 G、K）。技能清單就是裝備（主動 ≤ 6、
  被動 ≤ 3、反應 ≤ 1、姿態 ≤ 1，``core.yaml`` 的 ``skill_slots``）；欄位滿時要替換或放棄。
- 技能成長（Phase 3-26a）：``skill_points`` 未花的技能點、``skill_levels`` 技能等級、``bench``
  備用技能（卸下的技能，等級保留）；規則在 ``content/skill_growth.yaml``，邏輯在
  ``trpg.roguelite.growth``。
- 分歧進化（Phase 3-26b）：``skill_usage`` 每招的用法統計、``evolutions`` 進化紀錄（進化後的技能
  定義也放在 ``generated_skills``）；
  邏輯在 ``trpg.roguelite.growth`` 與 ``trpg.skillgen.evolution``。
- ``generated_skills``：主角目前裝備與備用的 **生成技能定義**（隨機組合器的產物不在內容庫裡；讀檔與
  開戰時以 ``Ruleset.with_skills`` 加回規則包）。
- ``plan``：開局時以種子排好的每一場（地圖、敵人、戰鬥種子）；存進存檔，所以之後改了抽選方式，
  舊存檔的下一場仍然不變。
- ``node``：目前在等什麼（戰鬥／升級／營火／結束）；升級與重骰的候選 **連同完整技能定義**
  存在節點裡。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import UnitTemplate
from trpg.content.rules import CoreRules
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "BattleNode",
    "BattlePlan",
    "BattleRecord",
    "CampfireNode",
    "Choice",
    "EndedNode",
    "EvolutionRecord",
    "LeaveChoice",
    "LevelUpChoice",
    "LevelUpNode",
    "LoadoutChoice",
    "Node",
    "OfferTag",
    "PickChoice",
    "RerollChoice",
    "RespecChoice",
    "RunStart",
    "RunState",
    "SkillOffer",
    "SpendChoice",
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
    objective: Literal["eliminate", "escape", "defend"] = "eliminate"
    """本場的勝利條件種類（Phase 3-22）；撤離與守點的格子、輪數取自地圖的 ``alt_objectives``。"""


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


class RunStart(_Model):
    """一輪的開局（Phase 3-24b2，06 6.27.3）：自選的起始武器與關鍵字；``dev_pack`` 是開發者起始包
    ID（一般開局為 ``None``）。"""

    weapon: str
    keywords: tuple[str, ...] = ()
    dev_pack: str | None = None


class OfferTag(_Model):
    """候選的標示（Phase 3-24b2，候選產生器）：``kind`` 加深／橋接／新方向、它帶的關鍵字、來源，
    ``fallback`` 表示定義做不到而退回（例：只持有 1 個關鍵字時的橋接）。"""

    kind: Literal["deepen", "bridge", "new"]
    keywords: tuple[str, ...]
    source: Literal["pool", "composer"]
    fallback: bool = False


class SkillOffer(_Model):
    """升級或重骰的技能候選。``off_route`` 是「偏離路線」候選的索引（縮放屬性與當時主角最高屬性
    不同；湊不到時為空）。``tags`` 與 ``candidates`` 一一對應（Phase 3-24b2 起）。"""

    reason: Literal["level_up", "reroll"]
    tier: int
    top_attribute: Attribute
    """產生候選時主角的最高屬性（並列時取六屬性順序的第一個）。"""
    candidates: tuple[SkillDef, ...]
    off_route: tuple[int, ...] = ()
    tags: tuple[OfferTag, ...] = ()


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


class EvolutionRecord(_Model):
    """一次分歧進化（Phase 3-26b）：進化前的技能 ID、分支（加深／橋接）、模板、帶的關鍵字，
    ``fallback`` 表示橋接做不出來、改用第二個加深模板。進化後的技能定義在 ``generated_skills``。"""

    base_id: str
    branch: Literal["deepen", "bridge"]
    template: str
    keyword: str | None = None
    fallback: bool = False


class LevelUpChoice(_Model):
    """升級的選擇：``attributes`` 分配全部屬性點；``pick`` 為候選索引（``None`` ＝ 跳過）；
    欄位滿時 ``replace`` 指定要換掉的技能 ID。"""

    kind: Literal["level_up"] = "level_up"
    attributes: dict[Attribute, int] = Field(default_factory=dict)
    pick: int | None = None
    replace: str | None = None
    levels: dict[str, int] = Field(default_factory=dict)
    """選完候選之後順便花技能點（Phase 3-26a；同 ``SpendChoice.levels``，空 ＝ 先不花）。"""
    evolve: dict[str, int] = Field(default_factory=dict)
    """升到 3 級時選的進化分支（Phase 3-26b；同 ``SpendChoice.evolve``）。"""


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


class SpendChoice(_Model):
    """花技能點升級（Phase 3-26a）：``levels`` 是技能 ID → 升到的等級（只能升、不能降；每升 1 級花
    ``skill_growth.upgrade_cost`` 點）。升級、營火與下一場戰鬥之前都可以送；不推進節點。"""

    kind: Literal["spend"] = "spend"
    levels: dict[str, int] = Field(default_factory=dict)
    evolve: dict[str, int] = Field(default_factory=dict)
    """分歧進化（Phase 3-26b）：技能 ID → 選的分支索引（0 或 1，
    對應 ``evolution_options`` 的順序）。
    升到 ``skill_growth.evolve_level``（含以上）而且還沒進化過的技能必須選；進化後技能換成進化後的
    定義（新的 ID），等級跟著過去。"""


class RespecChoice(_Model):
    """營火：免費重配（Phase 3-26a）——全部技能退回 1 級，花掉的點數退回，之後再用 ``spend`` 重新
    分配。不推進節點。"""

    kind: Literal["respec"] = "respec"


class LoadoutChoice(_Model):
    """營火：換裝（Phase 3-26a）——``skills`` 是新的裝備清單（必須是目前裝備與備用技能的子集，符合
    欄位上限）；沒裝上的進備用，技能等級保留。不推進節點。"""

    kind: Literal["loadout"] = "loadout"
    skills: tuple[str, ...]


type Choice = Annotated[
    LevelUpChoice
    | RerollChoice
    | PickChoice
    | LeaveChoice
    | SpendChoice
    | RespecChoice
    | LoadoutChoice,
    Field(discriminator="kind"),
]


class RunState(_Model):
    """一輪的進度（見模組說明）。"""

    seed: int = Field(ge=0)
    build_id: str | None = None
    """以回歸範本開局時的 build ID（開發與測試用）；一般開局為 ``None``。"""
    start: RunStart | None = None
    """一般開局與開發者起始包的選擇（Phase 3-24b2）；以回歸範本開局時為 ``None``。"""
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
    behavior: dict[str, int] = Field(default_factory=dict)
    """主角用過的動作類型 → 次數（每場戰後累加；候選產生器的行為紀錄，Phase 3-24b2）。"""
    skill_points: int = Field(default=0, ge=0)
    """還沒花掉的技能點（Phase 3-26a；每升 1 級 ``skill_growth.points_per_level`` 點）。"""
    skill_levels: dict[str, int] = Field(default_factory=dict)
    """技能等級（Phase 3-26a）：技能 ID → 等級（2～``max_level``，1 級不列）。技能點跟著技能走：
    卸下（進備用）後等級保留。依 ID 排序存入，所以序列化確定。"""
    bench: tuple[str, ...] = ()
    """備用技能 ID（Phase 3-26a）：被替換或在營火卸下的技能，等級保留，可在營火換回；定義在
    ``generated_skills``（生成技能）或內容庫。"""
    skill_usage: dict[str, SkillUsage] = Field(default_factory=dict)
    """每招技能在這一輪的用法統計（Phase 3-26b；戰後由事件重播累加，``trpg.skillgen.usage``）：
    技能 ID → 統計，依 ID 排序。進化的門檻與兩支的推導都讀它。"""
    evolutions: dict[str, EvolutionRecord] = Field(default_factory=dict)
    """分歧進化（Phase 3-26b）：進化後的技能 ID → 紀錄。進化結果跟著技能走（卸下、重配都保留）。"""
    node: Node

    def max_hp_in(self, core: CoreRules) -> int:
        """最大 HP ＝ 基礎 ＋（體質 − 10）× 3 ＋ 基礎 × 50‰ ×（等級 − 1）（係數在 ``core.yaml``；
        基礎是 ``hero.max_hp``，不隨升級與配點改變）。"""
        return core.run_max_hp(self.hero.max_hp, self.hero.attributes[Attribute.CON], self.level)

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
