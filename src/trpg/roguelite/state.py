"""一輪的狀態（``RunState``）與節點、選擇的資料模型（Phase 3-5a）。

``RunState`` 是一輪進度的唯一真相，**可序列化**（存檔原樣寫入）：

- 開局（Phase 3-24b2）：``start``＝起始武器 ＋ 選的關鍵字（與開發者起始包 ID）；``build_id`` 只在以
  回歸範本（``content/sim/builds.yaml``）開局時有值（開發與測試用，玩家介面不提供）。
- ``behavior``：主角在這一輪用過的動作類型與次數（候選產生器的行為紀錄）。
- 主角：目前的單位範本 ``hero``（屬性與技能清單隨升級改變；其餘欄位沿用開局時的主角）、
  等級與經驗、**目前 HP、法力、耐力（3H-2）、源力**（戰鬥之間不回復，0.11 G、K）。技能清單就是
  裝備（主動 ≤ 6、被動 ≤ 3、反應 ≤ 1、姿態 ≤ 1，``core.yaml`` 的 ``skill_slots``）；欄位滿時要
  替換或放棄。
- 靈感點與閃現（Phase 3W-5，06 6.34）：``insight`` 未花的靈感點（每打贏一場 1 點）、``flash`` 每招
  技能的閃現狀態（變化歷程、先上場用過、花掉的點數；以 **目前的技能 ID** 為鍵，沒有記錄＝剛取得）、
  ``flash_bases`` 閃現前的原本技能定義（推出閃現後技能的起點）、``pending_flash`` 已付點、還沒選的
  閃現選項；``bench`` 備用技能（卸下的技能，閃現狀態保留）。邏輯在 ``trpg.roguelite.flashes``。
- ``skill_usage``：每招的用法統計（Phase 3-26b；閃現選項的排序讀它）。
- ``skill_tier``（Phase 3W-9）：主角技能目前用的階級（＝角色階級；升階時重配，見
  ``trpg.roguelite.retier``）。
- ``generated_skills``：主角目前裝備與備用的 **生成技能定義**（隨機組合器的產物不在內容庫裡；讀檔與
  開戰時以 ``Ruleset.with_skills`` 加回規則包）。
- ``plan``：開局時以種子排好的每一場（地圖、敵人、戰鬥種子）；存進存檔，所以之後改了抽選方式，
  舊存檔的下一場仍然不變。
- ``node``：目前在等什麼（戰鬥／裝備三選一／升級／完整技能三選一／營火／結束）；升級與完整技能的
  候選 **連同完整技能定義** 存在節點裡。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import UnitTemplate
from trpg.content.equipment import ItemDef
from trpg.content.rules import CoreRules
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute
from trpg.skillgen.flash_offer import FlashOffer
from trpg.skillgen.flash_state import SkillFlash, Variation
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "AllocateChoice",
    "BattleNode",
    "BattlePlan",
    "BattleRecord",
    "CampfireNode",
    "Choice",
    "CompleteOfferNode",
    "CompletePickChoice",
    "DissolveChoice",
    "EndedNode",
    "EquipChoice",
    "FlashChoice",
    "FlashLlmName",
    "FlashLlmRecord",
    "FlashPickChoice",
    "GearOfferNode",
    "GearPickChoice",
    "InheritChoice",
    "LeaveChoice",
    "LevelUpChoice",
    "LevelUpNode",
    "LlmRecord",
    "LoadoutChoice",
    "Node",
    "OfferTag",
    "PendingFlash",
    "RespecAttributesChoice",
    "RunStart",
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
    stamina: int | None = None
    """戰後的耐力（Phase 3H-2）；舊存檔沒有此欄位。"""
    """主角在戰鬥中倒下（我方仍勝利時以 1 HP 繼續）。"""
    state_digest: str


class RunStart(_Model):
    """一輪的開局（Phase 3-24b2，06 6.27.3）：自選的起始武器與關鍵字；``dev_pack`` 是開發者起始包
    ID（一般開局為 ``None``）。"""

    weapon: str
    keywords: tuple[str, ...] = ()
    dev_pack: str | None = None


class LlmRecord(_Model):
    """一次 LLM 提議的紀錄（Phase 4-L6）：題目（關鍵字、稀有度、核心原語、選單種子、主題）、
    嘗試次數、
    是否成功、錯誤代碼與失敗原因。``ok`` 為假表示候選改走組合器或技能池（退回）。重播與讀檔直接用
    存下來的候選，不再呼叫 LLM。"""

    offer: int = 0
    """第幾組候選（``RunState.offers_made`` 當時的值）。"""
    kind: Literal["deepen", "bridge", "new"] = "deepen"
    keywords: tuple[str, ...] = ()
    rarity: str = "common"
    core_primitive: str | None = None
    menu_seed: int | None = None
    theme: str | None = None
    attempts: int = 0
    ok: bool = False
    codes: tuple[str, ...] = ()
    reason: str | None = None
    name_source: Literal["llm", "fallback"] | None = None
    """命名與敘事（4-L7）的來源；舊存檔與沒有命名步驟為 ``None``。"""
    name_attempts: int = 0
    name_codes: tuple[str, ...] = ()
    prompt_version: str | None = None
    """提議 prompt 的版本號（``trpg.llm`` 的 ``PROMPT_VERSION``；4-L8）；沒有請 LLM 為 ``None``。"""
    naming_prompt_version: str | None = None
    """命名 prompt 的版本號（``NAMING_PROMPT_VERSION``；4-L8）；沒有命名步驟為 ``None``。"""


class OfferTag(_Model):
    """候選的標示（Phase 3-24b2，候選產生器）：``kind`` 加深／橋接／新方向、它帶的關鍵字、來源，
    ``fallback`` 表示定義做不到而退回（例：只持有 1 個關鍵字時的橋接）。``llm``（Phase 4-L6）是這個
    候選請過 LLM 的紀錄（來源為 ``llm`` 表示成功；失敗時來源是退回後的組合器或技能池）。"""

    kind: Literal["deepen", "bridge", "new"]
    keywords: tuple[str, ...]
    source: Literal["pool", "composer", "llm"]
    fallback: bool = False
    llm: LlmRecord | None = None


class SkillOffer(_Model):
    """升級（白板）或完整技能三選一（Phase 3W-5）的技能候選。``off_route`` 是「偏離路線」候選的
    索引（縮放屬性與當時主角最高屬性不同；湊不到時為空）。``tags`` 與 ``candidates`` 一一對應
    （Phase 3-24b2 起）。"""

    reason: Literal["level_up", "complete"]
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
    """升級：分配 ``points`` 屬性點，並從候選選 1 個（可跳過）。``tier_up`` 表示這次升級讓角色升階
    （3W-9 重配每招；3W-5 起給前端顯示升階提示「可以重閃第 3 格轉型」用）。"""

    kind: Literal["level_up"] = "level_up"
    level: int
    points: int
    offer: SkillOffer
    tier_up: bool = False


class CompleteOfferNode(_Model):
    """完整技能三選一（Phase 3W-5，06 6.34.6、07 7.1）：一輪中段與 Boss 前各一次（``roguelite.yaml``
    的 ``complete_skill_after``）。候選已是完整技能的強度（視為已閃 3 次、預算上限 +120‰），選 1 個
    或跳過；之後才是營火。"""

    kind: Literal["complete_offer"] = "complete_offer"
    after_battle: int
    offer: SkillOffer


class GearOfferNode(_Model):
    """戰後裝備三選一（Phase 3K-2，07 7.1）：``candidates`` 是 3 件產生的裝備（連同完整定義，
    部位不重複）；選 1 件直接換上（換下的進背包）或跳過，之後才是升級。"""

    kind: Literal["gear_offer"] = "gear_offer"
    after_battle: int
    candidates: tuple[ItemDef, ...]


class CampfireNode(_Model):
    """營火（進入時已回滿 HP、法力並加源力）：可以閃現、重閃、溶掉、傳承、換技能與裝備、重配屬性，
    之後離開（Phase 3W-5 起沒有重骰候選）。"""

    kind: Literal["campfire"] = "campfire"
    after_battle: int


class EndedNode(_Model):
    kind: Literal["ended"] = "ended"
    victory: bool


type Node = Annotated[
    BattleNode | GearOfferNode | LevelUpNode | CompleteOfferNode | CampfireNode | EndedNode,
    Field(discriminator="kind"),
]


class PendingFlash(_Model):
    """已付點、還沒選的閃現（或重閃）選項（Phase 3W-5）：``skill`` 是目前的技能 ID，``offer`` 連同
    套用後的技能定義存下來（選擇時不重抽、不重算，重播不呼叫 LLM）。"""

    skill: str
    offer: FlashOffer


class FlashLlmName(_Model):
    """閃現選項命名（4-L7）的紀錄（``trpg.llm.flash_propose.FlashNameRecord`` 的同形欄位）。"""

    template: str
    source: Literal["llm", "fallback"]
    attempts: int
    codes: tuple[str, ...] = ()
    naming_prompt_version: str = ""
    consistency_retries: int = 0
    """因敘事一致性或世界觀詞檢查（4-L11）不過而重試的次數（舊紀錄沒有＝0）。"""


class FlashLlmRecord(_Model):
    """一次閃現變化提議的紀錄（Phase 3W-5 接 3W-7；``trpg.llm.flash_propose.FlashProposalRecord``
    的同形欄位，``trpg.roguelite`` 不得匯入 ``trpg.llm`` 所以另外定義）。``seconds`` 只供報表，比對
    一輪的紀錄時排除（:func:`trpg.roguelite.flashes.comparable_run`）。"""

    tag: str
    prompt_version: str = ""
    source: Literal["llm", "partial", "template"] = "template"
    wanted: int = 0
    attempts: int = 0
    codes: tuple[tuple[str, ...], ...] = ()
    accepted: tuple[Variation, ...] = ()
    rejected: tuple[str, ...] = ()
    reason: str | None = None
    seconds: float = 0.0
    names: tuple[FlashLlmName, ...] = ()


class LevelUpChoice(_Model):
    """升級的選擇：``attributes`` 分配全部屬性點；``pick`` 為候選索引（``None`` ＝ 跳過）；
    欄位滿時 ``replace`` 指定要換掉的技能 ID。"""

    kind: Literal["level_up"] = "level_up"
    attributes: dict[Attribute, int] = Field(default_factory=dict)
    pick: int | None = None
    replace: str | None = None


class CompletePickChoice(_Model):
    """完整技能三選一的選擇（Phase 3W-5）：``pick`` 為候選索引（``None`` ＝ 跳過）；欄位滿時
    ``replace`` 指定要換掉的技能 ID（換下的進備用）。"""

    kind: Literal["complete_pick"] = "complete_pick"
    pick: int | None = None
    replace: str | None = None


class GearPickChoice(_Model):
    """戰後裝備三選一：``pick`` 為候選索引（``None`` ＝ 跳過）。"""

    kind: Literal["gear_pick"] = "gear_pick"
    pick: int | None = None


class EquipChoice(_Model):
    """營火換裝（Phase 3K-2）：把背包裡的 ``item_id`` 換上；``slot`` 省略時依物品種類決定（戒指有
    兩個欄位時，先放空的、都有裝備時換掉較弱的）。換下的進背包。不推進節點。"""

    kind: Literal["equip"] = "equip"
    item_id: str
    slot: str | None = None


class LeaveChoice(_Model):
    """離開營火（有候選沒選時視為放棄）。"""

    kind: Literal["leave"] = "leave"


class FlashChoice(_Model):
    """閃現或重閃（Phase 3W-5，06 6.34.3）：付點出題，選項存進 ``RunState.pending_flash``，接著要用
    ``flash_pick`` 選一個。

    - ``skill``：學會的技能（裝備中或備用）的目前 ID。
    - ``slot``：``None`` ＝ 閃現（下一次）；否則重閃第 ``slot`` 次的變化（完整技能為 0，換調整欄）。
      重閃只在營火；閃現在戰鬥之間都可以（戰鬥中不行）。
    - ``category``：``None`` ＝ 不指定（1 點出 4 個）；指定類別 2 點出 3 個（只出該類；第 3 次另附
      「轉型」保底）。0 個合法變化的類別會被拒絕（沒有扣點）。"""

    kind: Literal["flash"] = "flash"
    skill: str
    slot: int | None = Field(default=None, ge=0)
    category: str | None = None


class FlashPickChoice(_Model):
    """選閃現的第 ``pick`` 個選項（點數在出題時已付，不能放棄）。轉型讓技能換到另一種已滿的欄位時，
    ``unequip`` 指定要卸下到備用的技能（必須是那一欄目前裝備的技能）。不推進節點。"""

    kind: Literal["flash_pick"] = "flash_pick"
    pick: int = Field(ge=0)
    unequip: str | None = None


class DissolveChoice(_Model):
    """溶掉一招學會的技能（Phase 3W-5，#71）：技能消失，退回花在它身上的靈感點的一半（無條件捨去）。
    只在營火；欄位空出（可以用 ``loadout`` 從備用補上）。不推進節點。"""

    kind: Literal["dissolve"] = "dissolve"
    skill: str


class InheritChoice(_Model):
    """傳承（Phase 3W-5，#72，06 6.34.9 第 4 點）：還沒閃過的白板 ``skill`` 帶走舊技能 ``source`` 的
    最多 2 個小變化（``records`` 是舊技能變化歷程的「第幾次」，依序變成新技能的第 1、2 次）。舊技能
    消失、不退點；完整技能不能接受；變化必須對新技能合法。只在營火（和溶掉二選一）。不推進節點。"""

    kind: Literal["inherit"] = "inherit"
    skill: str
    source: str
    records: tuple[int, ...] = Field(min_length=1, max_length=2)


class RespecAttributesChoice(_Model):
    """營火：免費重配屬性點（Phase 3H-3）——分配出去的屬性點全部退回（屬性回到基礎），之後再用
    ``allocate`` 重新分配。免費、不推進節點。"""

    kind: Literal["respec_attributes"] = "respec_attributes"


class AllocateChoice(_Model):
    """分配未分配的屬性點（Phase 3H-3；重配之後用）：``attributes`` 是屬性 → 加幾點，總數不可超過
    ``RunState.attribute_points``。營火、戰前都可以送；不推進節點。"""

    kind: Literal["allocate"] = "allocate"
    attributes: dict[Attribute, int] = Field(default_factory=dict)


class LoadoutChoice(_Model):
    """營火：換裝（Phase 3-26a）——``skills`` 是新的裝備清單（必須是目前裝備與備用技能的子集，符合
    欄位上限）；沒裝上的進備用，閃現狀態保留。不推進節點。"""

    kind: Literal["loadout"] = "loadout"
    skills: tuple[str, ...]


type Choice = Annotated[
    LevelUpChoice
    | CompletePickChoice
    | LeaveChoice
    | FlashChoice
    | FlashPickChoice
    | DissolveChoice
    | InheritChoice
    | RespecAttributesChoice
    | AllocateChoice
    | LoadoutChoice
    | GearPickChoice
    | EquipChoice,
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
    origin: str | None = None
    """出身（Phase 3R-3a，``content/origins.yaml`` 的 ID）；不影響戰鬥（只決定預設外觀、開場劇情鍵、
    NPC 態度）。舊存檔沒有此欄位＝無出身。種族存在 ``hero.race``。"""
    level: int = Field(ge=1)
    xp: int = Field(ge=0)
    hp: int = Field(ge=0)
    mana: int = Field(ge=0)
    stamina: int | None = Field(default=None, ge=0)
    """目前耐力（Phase 3H-2：武器技與格擋共用；和法力一樣戰鬥之間不回復，營火回滿）。``None`` ＝ 滿
    （舊存檔沒有此欄位；讀檔時以上限計，見 :meth:`stamina_in`）。"""
    source: int = Field(ge=0)
    generated_skills: tuple[SkillDef, ...] = ()
    skill_tier: int | None = Field(default=None, ge=1)
    """主角的技能目前照哪一階的預算配數值（Phase 3W-9，06 6.34.9：技能的預算用角色階級）。和角色
    階級不同時，下一個戰鬥之間的節點（升級）把每招照新階級重配（``trpg.roguelite.retier``）。
    ``None`` ＝ 舊存檔（``/10`` 以前），讀檔或下一個節點時照角色階級重配一次。"""
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
    insight: int = Field(default=0, ge=0)
    """還沒花掉的靈感點（Phase 3W-5，06 6.34.2；每打贏一場 ``flash_templates.yaml`` 的
    ``insight_per_win`` 點，可以存、不設上限）。"""
    flash: dict[str, SkillFlash] = Field(default_factory=dict)
    """每招學會的技能的閃現狀態（Phase 3W-5）：**目前的技能 ID** → 狀態（``base_id`` 是閃現前的
    原本技能）。沒有記錄 ＝ 剛取得（沒有變化、還沒用過）。依 ID 排序存入。"""
    flash_bases: tuple[SkillDef, ...] = ()
    """閃現過的生成技能的原本定義（Phase 3W-5；內容庫的手寫技能不存）。閃現後的技能由原本的技能依
    變化歷程推出（``trpg.skillgen.flash_derive.derive_skill``）。依 ID 排序。"""
    pending_flash: PendingFlash | None = None
    """已付點、還沒選的閃現選項（Phase 3W-5）；有它時只能送 ``flash_pick``。"""
    complete_offers_done: tuple[int, ...] = ()
    """已出過完整技能三選一的場次（Phase 3W-5）。"""
    flash_llm_log: tuple[FlashLlmRecord, ...] = ()
    """閃現選項請 LLM 提議的紀錄（Phase 3W-5 接 3W-7；``llm`` 開著而且外層裝了來源時才有）。"""
    bench: tuple[str, ...] = ()
    """備用技能 ID（Phase 3-26a）：被替換或在營火卸下的技能，閃現狀態保留，可在營火換回；定義在
    ``generated_skills``（生成技能）或內容庫。"""
    skill_usage: dict[str, SkillUsage] = Field(default_factory=dict)
    """每招技能在這一輪的用法統計（Phase 3-26b；戰後由事件重播累加，``trpg.skillgen.usage``）：
    技能 ID → 統計，依 ID 排序。閃現選項依它排序。"""
    attribute_points: int = Field(default=0, ge=0)
    """還沒分配的屬性點（Phase 3H-3；營火重配退回的點數，用 ``allocate`` 分配）。"""
    attribute_spent: dict[Attribute, int] = Field(default_factory=dict)
    """分配出去（營火重配時退回）的屬性點（Phase 3H-3）：開局自由配點＋升級配點＋重配後再分配的點
    數，依六屬性順序存入。舊存檔沒有此欄位時為空（重配只退之後分配的點數）。"""
    equipment: dict[str, ItemDef] = Field(default_factory=dict)
    """目前穿戴的裝備（Phase 3K-2）：欄位 → 物品（連同完整定義；產生器的物品不在內容庫裡）。**非空時
    就是全身裝備**（第一次換裝時把範本或測試模式的裝備一併搬進來）；空 ＝ 用範本（或測試模式）的
    裝備。舊存檔沒有此欄位時為空。"""
    backpack: tuple[ItemDef, ...] = ()
    """背包（Phase 3K-2）：換下與沒穿上的裝備，一輪內不限數量；營火可以換回。"""
    node: Node
    llm: bool = False
    """LLM 生成開關（Phase 4-L6）：打開時候選產生器請 LLM 提議技能（需要呼叫端裝上提議器，見
    ``trpg.roguelite.llm_hook``）；關閉時行為與以往完全相同。舊存檔沒有此欄位＝關閉。"""
    llm_uses: dict[str, int] = Field(default_factory=dict)
    """run 內配額（Phase 4-L6）：原語 → 已出現在這一輪候選中的次數（核心原語抽籤的權重折減）。"""
    llm_log: tuple[LlmRecord, ...] = ()
    """這一輪每次請 LLM 提議的紀錄（Phase 4-L6；退回率統計與 ``trpg run show`` 讀它）。"""
    test_mode: bool = False
    """測試模式（Phase 3-39）：每場戰鬥結束後 HP、法力回滿，並可在開局挑裝備。**只存在這一輪的設定
    裡**，不進模擬、不計入任何統計；舊存檔沒有此欄位時為 ``False``。"""
    test_equipment: dict[str, str] = Field(default_factory=dict)
    """測試模式開局挑的裝備（Phase 3-39）：欄位 → 物品 ID；非空時取代主角範本的裝備。只有
    ``test_mode`` 時才可非空。"""

    def max_hp_in(self, core: CoreRules) -> int:
        """最大 HP ＝ 基礎 ＋（體質 − 10）× 3 ＋ 基礎 × 50‰ ×（等級 − 1）（係數在 ``core.yaml``；
        基礎是 ``hero.max_hp``，不隨升級與配點改變）。"""
        return core.run_max_hp(self.hero.max_hp, self.hero.attributes[Attribute.CON], self.level)

    def max_mana_in(self, core: CoreRules) -> int:
        """法力上限 ＝ 基礎（``hero.max_mana``，依武器大類）＋ 屬性加成（Phase 3H-2，
        ``core.yaml`` 的 ``resources``；不含裝備詞條，戰鬥中的上限另含裝備的屬性）。"""
        return core.resources.max_for("mana", self.hero.max_mana, self.hero.attributes)

    def max_stamina_in(self, core: CoreRules) -> int:
        """耐力上限 ＝ 基礎（``hero.stamina``，省略時 ``default_stamina``）＋ 屬性加成
        （Phase 3H-2）。"""
        base = core.template_stamina(self.hero)
        return core.resources.max_for("stamina", base, self.hero.attributes)

    def stamina_in(self, core: CoreRules) -> int:
        """目前耐力（``stamina`` 為 ``None`` 時 ＝ 上限）。"""
        return self.max_stamina_in(core) if self.stamina is None else self.stamina

    @property
    def ended(self) -> bool:
        return isinstance(self.node, EndedNode)

    @property
    def llm_fallbacks(self) -> int:
        """LLM 提議失敗而退回的次數（Phase 4-L6）。"""
        return sum(1 for r in self.llm_log if not r.ok)

    def plan_of(self, index: int) -> BattlePlan:
        return self.plan[index - 1]

    def generated(self, skill_id: str) -> SkillDef | None:
        return next((s for s in self.generated_skills if s.id == skill_id), None)
