"""世界動作與世界事件（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.4）。

動作是玩家（經 API）送進來的意圖，進世界動作日誌（``trpg-wlog/1``）；事件是 :func:`world_step`
套用動作時產生的結果（給 API、說書人與前端看），可由日誌重播得到，不另外存。

5A-4 加上撤退、戰鬥（步驟寫進日誌，重播時重算勝負）、城鎮休息、換技能、傳送。
5A-6 加上成長的動作：配點、重配、閃現、選閃現、溶掉、傳承、立誓、解除誓約。
5B-4 加上任務與好感度：接任務、選任務給的技能、和 NPC 說話、在酒館聽傳聞。
5B-4b 加上放棄、交涉、戰鬥解法（``event_solve``）。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import ID_PATTERN
from trpg.content.world_events import ThreadScope
from trpg.content.world_map import RevealMethod
from trpg.content.world_narration import StoryScene, StoryText
from trpg.content.world_oaths import OATH_TEXT_LIMIT, OathProposal
from trpg.content.world_quests import AffinityRank, QuestKind
from trpg.content.world_situations import (
    PLAYER_TEXT_LIMIT,
    CareItem,
    Outcome,
    SituationProposal,
)
from trpg.engine.actions import Step
from trpg.shared.types import Attribute, Team
from trpg.world.crafting_actions import (
    AffixChangedEvent,
    CraftAction,
    EnhanceAction,
    GearCraftedEvent,
    GearEnhancedEvent,
    GearSalvagedEvent,
    ImbueAction,
    RerollAction,
    SalvageAction,
)
from trpg.world.economy_actions import (
    BuyAction,
    CurrencyGainedEvent,
    EquipAction,
    ItemBoughtEvent,
    ItemEquippedEvent,
    ItemSoldEvent,
    ItemUsedEvent,
    LootAbandonedEvent,
    LootChooseAction,
    LootChosenEvent,
    LootGainedEvent,
    PouchAction,
    PouchChangedEvent,
    PouchUsedEvent,
    SellAction,
    UseItemAction,
)
from trpg.world.encounters import EncounterLineup
from trpg.world.season_events import (
    BountyClaimedEvent,
    BountyMissedEvent,
    DailyGoalDoneEvent,
    SealKeyGainedEvent,
    SeasonBossAction,
    SeasonBossChallengedEvent,
    SeasonBossClearedEvent,
    SeasonBossFailedEvent,
    WorldEventProgressEvent,
    WorldEventResolvedEvent,
    WorldEventStartedEvent,
    WorldEventTargetEvent,
)
from trpg.world.state import EncounterResult, EventTrigger, NextBattleMod, OathState

__all__ = [
    "AcceptQuestAction",
    "AffinityChangedEvent",
    "AllocateAction",
    "AttributesAllocatedEvent",
    "AttributesRespeccedEvent",
    "BattleEndedEvent",
    "BattleStartedEvent",
    "CampAction",
    "CampedEvent",
    "CareResult",
    "CompanionJoinedEvent",
    "CompanionLeftEvent",
    "DefeatedEvent",
    "DissolveAction",
    "EncounterCheckEvent",
    "EncounterEvent",
    "EventCheckEvent",
    "EventLeftEvent",
    "EventResolvedEvent",
    "EventSolveAction",
    "EventSolvedEvent",
    "EventTriggeredEvent",
    "FightAction",
    "FlashAction",
    "FlashOfferedEvent",
    "FlashPickAction",
    "FlashPickedEvent",
    "HireAction",
    "InheritAction",
    "InsightGainedEvent",
    "LeveledUpEvent",
    "LoadoutAction",
    "LoadoutChangedEvent",
    "LocationClearedEvent",
    "LocationRevealedEvent",
    "NarrateAction",
    "NarratedEvent",
    "OathBrokenEvent",
    "OathKeptEvent",
    "OathReleasedEvent",
    "OathSwornEvent",
    "OfferPickAction",
    "OpportunityHintEvent",
    "PartyChangedEvent",
    "PerceptionCheckEvent",
    "QuestCompletedEvent",
    "QuestStartedEvent",
    "QuestStepDoneEvent",
    "ReleaseOathAction",
    "RespecAction",
    "RestAction",
    "RestedEvent",
    "RetreatAction",
    "RetreatedEvent",
    "RumorsHeardEvent",
    "ShadowAiAction",
    "ShadowAiChangedEvent",
    "ShadowLentEvent",
    "ShadowSavedEvent",
    "SituationAction",
    "SituationCheckEvent",
    "SituationResultEvent",
    "SkeletonUnlockedEvent",
    "SkillDissolvedEvent",
    "SkillInheritedEvent",
    "SkillOfferTakenEvent",
    "SkillOfferedEvent",
    "SkillTierChangedEvent",
    "StoryFlagClearedEvent",
    "StorySkillGrantedEvent",
    "SwearOathAction",
    "TalkAction",
    "TalkedEvent",
    "TavernAction",
    "TeleportAction",
    "TeleportedEvent",
    "ThreadAddedEvent",
    "ThreadExpiredEvent",
    "ThreadPushedOutEvent",
    "ThreadSpentEvent",
    "TravelAction",
    "TraveledEvent",
    "WorldAction",
    "WorldEvent",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# 動作
# ---------------------------------------------------------------------------


class TravelAction(_Model):
    """走到相鄰地點（09 9.6.7 #9）；``hasten``＝花補給趕路，降低遇敵機率。"""

    kind: Literal["travel"] = "travel"
    to: str = Field(pattern=ID_PATTERN)
    hasten: bool = False


class CampAction(_Model):
    """在目前地點紮營＝營火（09 9.6.11 #114）。"""

    kind: Literal["camp"] = "camp"


class RetreatAction(_Model):
    """看了陣容不打，退回出發地點（09 9.6.6：不開戰、不扣任何東西）。"""

    kind: Literal["retreat"] = "retreat"


class FightAction(_Model):
    """打這場遭遇：``steps`` 是整場戰鬥的步驟（動作與決定，同 ``BattleLog.actions``），套用後戰鬥
    必須已結束。重播時用同一份設定與種子重算勝負（第 2.4 節）。"""

    kind: Literal["fight"] = "fight"
    steps: tuple[Step, ...]


class RestAction(_Model):
    """在城鎮休息：HP、法力、耐力回滿，補給補到初值（09 9.6.7 #2、#11）。"""

    kind: Literal["rest"] = "rest"


class LoadoutAction(_Model):
    """換技能（城鎮或營火；07 7.6）：新的裝備清單，沒裝上的進備用。"""

    kind: Literal["loadout"] = "loadout"
    skills: tuple[str, ...]


class TeleportAction(_Model):
    """傳送到另一區的小鎮（09 9.6.2「城鎮之間用傳送點」）：從城鎮到去過的小鎮，或從傳送點到它通往
    的區域。"""

    kind: Literal["teleport"] = "teleport"
    region: str = Field(pattern=ID_PATTERN)


class SituationAction(_Model):
    """對目前的事件做情境判定（Phase 5B-2；09 9.6.4）。

    ``proposal`` 是 LLM（或降級）提議、已經過 pydantic 驗證；引擎另外檢查合法性。提議、來源、
    prompt 版本與玩家原文都隨動作進世界動作日誌，重播照紀錄、不再呼叫 LLM（10 第 10 節）。
    ``player_text``：給 LLM 時包在 ``<player_input>``；引擎只拿它核對用心清單的關鍵詞（完全字串
    包含，5C-3d），不解讀內容。
    """

    kind: Literal["situation"] = "situation"
    template: str = Field(pattern=ID_PATTERN)
    player_text: str = Field(default="", max_length=PLAYER_TEXT_LIMIT)
    proposal: SituationProposal
    source: Literal["llm", "fallback"] = "fallback"
    """``llm``＝LLM 的提議；``fallback``＝模型不可用或提議一直不合法時的降級提議。"""
    prompt_version: str | None = Field(default=None, max_length=64)


class NarrateAction(_Model):
    """說書人的一段敘述（Phase 5B-3；09 9.6.7 #3、#6、#7）。

    ``story`` 是 LLM（或降級模板）的輸出、已經過 pydantic 驗證；引擎另外核對引用（NPC、地點、線頭
    存在且角色看得到）與禁止文字。敘述、來源、prompt 版本與玩家原文都隨動作進世界動作日誌，重播照
    紀錄、不呼叫 LLM（10 第 10 節）。只有 ``event`` 會改狀態（在候選內換骨架）。
    """

    kind: Literal["narrate"] = "narrate"
    scene: StoryScene
    template: str | None = Field(default=None, pattern=ID_PATTERN)
    """``situation``／``outcome``：情境模板。"""
    outcome: Outcome | None = None
    """``outcome``：判定結果（外層從 ``situation_check`` 事件帶入）。"""
    npc: str | None = Field(default=None, pattern=ID_PATTERN)
    """``chat``：聊天的 NPC。"""
    player_text: str = Field(default="", max_length=PLAYER_TEXT_LIMIT)
    """``chat``：玩家說的話（只是紀錄；給 LLM 時包在 ``<player_input>``）。"""
    story: StoryText
    source: Literal["llm", "fallback"] = "fallback"
    prompt_version: str | None = Field(default=None, max_length=64)


class AllocateAction(_Model):
    """分配未分配的屬性點（07 7.2；5A-6）：屬性 → 加幾點，總數 ≤ ``attribute_points``。"""

    kind: Literal["allocate"] = "allocate"
    attributes: dict[Attribute, int]


class RespecAction(_Model):
    """免費重配屬性點（07 7.2「營火可以免費重配」；城鎮與營火；5A-6）。"""

    kind: Literal["respec"] = "respec"


class FlashAction(_Model):
    """閃現或重閃出題（06 6.34.3；城鎮與營火；5A-6）。欄位同 roguelite ``FlashChoice``：``slot``
    為 ``None`` ＝ 閃現下一次，否則重閃第 ``slot`` 次；``category`` 指定類別（多花 1 點）。"""

    kind: Literal["flash"] = "flash"
    skill: str
    slot: int | None = Field(default=None, ge=0)
    category: str | None = None


class FlashPickAction(_Model):
    """選閃現的第 ``pick`` 個選項（同 roguelite ``FlashPickChoice``）。"""

    kind: Literal["flash_pick"] = "flash_pick"
    pick: int = Field(ge=0)
    unequip: str | None = None


class DissolveAction(_Model):
    """溶掉一招（06 6.34.3 #71；城鎮與營火）：退回花在它身上的點的一半。"""

    kind: Literal["dissolve"] = "dissolve"
    skill: str


class InheritAction(_Model):
    """傳承（06 6.34.9 第 4 點；城鎮與營火）：同 roguelite ``InheritChoice``。"""

    kind: Literal["inherit"] = "inherit"
    skill: str
    source: str
    records: tuple[int, ...] = Field(min_length=1, max_length=2)


class SwearOathAction(_Model):
    """立誓（06 6.26、09 9.6.10 #106；城鎮與營火，同時 1 個）。``proposal`` 是 LLM 或選單提議、
    已經過 pydantic 驗證的模板與參數；引擎另外檢查合法性。誓言原文只是紀錄（給 LLM 時包在
    ``<player_input>``），重播照紀錄、不呼叫 LLM。"""

    kind: Literal["swear_oath"] = "swear_oath"
    proposal: OathProposal
    player_text: str = Field(default="", max_length=OATH_TEXT_LIMIT)
    source: Literal["llm", "menu"] = "menu"
    prompt_version: str | None = Field(default=None, max_length=64)


class ReleaseOathAction(_Model):
    """解除誓約（#106：解除後現實 1 天內不能再立）。"""

    kind: Literal["release_oath"] = "release_oath"


class AcceptQuestAction(_Model):
    """接任務（Phase 5B-4；09 9.6.3）：在給任務的 NPC 所在地點、``start`` 條件成立。"""

    kind: Literal["accept_quest"] = "accept_quest"
    quest: str = Field(pattern=ID_PATTERN)


class OfferPickAction(_Model):
    """選任務給的技能三選一（07 7.6）：``pick`` 為 ``None`` ＝ 跳過；``replace`` 是要換掉的技能
    （只在城鎮與營火）。"""

    kind: Literal["offer_pick"] = "offer_pick"
    pick: int | None = Field(default=None, ge=0)
    replace: str | None = None


class TalkAction(_Model):
    """和所在地點的 NPC 說話（9.6.7 #3）：引擎依好感度列出能給的內容（只換資訊）。"""

    kind: Literal["talk"] = "talk"
    npc: str = Field(pattern=ID_PATTERN)


class TavernAction(_Model):
    """在城鎮的酒館聽本週傳聞（9.6.7 #1）。"""

    kind: Literal["tavern"] = "tavern"


class EventSolveAction(_Model):
    """用放棄、交涉或戰鬥解法處理身上的事件（Phase 5B-4b；9.6.7 #6）。``solution`` 是骨架
    ``solutions`` 的索引；``use_thread`` 是交涉時拿來抵掉付出的線頭（例：用人情代替青竹節）。"""

    kind: Literal["event_solve"] = "event_solve"
    solution: int = Field(ge=0)
    use_thread: str | None = Field(default=None, pattern=ID_PATTERN)


class HireAction(_Model):
    """在城鎮雇用系統傭兵（Phase 5C-1；09 9.6.9 #97：免費、出城前選好、野外不能換）：整組換成
    ``mercenaries``（依出場順序；空＝不帶傭兵）。"""

    kind: Literal["hire"] = "hire"
    mercenaries: tuple[str, ...] = Field(default=(), max_length=8)
    shadows: tuple[str, ...] = Field(default=(), max_length=8)
    """借用的影子（影子主人的角色 ID；Phase 5C-2）。和傭兵合計不超過 ``max_hired``。"""
    ai: dict[str, str] = Field(default_factory=dict, max_length=8)
    """成員（傭兵 ID 或影子主人 ID）→ AI 打法（``ai_choices``；沒有＝預設；5C-2 玩法 PM 定 ④）。"""


class ShadowAiAction(_Model):
    """在城鎮設定自己影子的預設打法（Phase 5C-2；#102）；``None``＝範本的預設。"""

    kind: Literal["shadow_ai"] = "shadow_ai"
    profile: str | None = Field(default=None, pattern=ID_PATTERN)


type WorldAction = Annotated[
    TravelAction
    | CampAction
    | RetreatAction
    | FightAction
    | RestAction
    | LoadoutAction
    | TeleportAction
    | SituationAction
    | NarrateAction
    | AllocateAction
    | RespecAction
    | FlashAction
    | FlashPickAction
    | DissolveAction
    | InheritAction
    | SwearOathAction
    | ReleaseOathAction
    | AcceptQuestAction
    | OfferPickAction
    | TalkAction
    | TavernAction
    | EventSolveAction
    | HireAction
    | ShadowAiAction
    | BuyAction  # 5D-1
    | SellAction
    | PouchAction
    | UseItemAction
    | EquipAction  # 5D-2
    | LootChooseAction  # 5D-2b
    | CraftAction  # 5D-3
    | EnhanceAction
    | RerollAction
    | ImbueAction
    | SalvageAction
    | SeasonBossAction,  # 5F-3
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# 事件
# ---------------------------------------------------------------------------


class TraveledEvent(_Model):
    kind: Literal["traveled"] = "traveled"
    from_location: str
    to: str
    hasten: bool
    supplies_spent: int


class EncounterCheckEvent(_Model):
    """遇敵擲骰：``roll``（0～999）< ``chance_permille`` 即遇敵。"""

    kind: Literal["encounter_check"] = "encounter_check"
    location: str
    chance_permille: int
    roll: int
    encountered: bool


class EncounterEvent(_Model):
    kind: Literal["encounter"] = "encounter"
    result: EncounterResult


class PerceptionCheckEvent(_Model):
    """隱藏地點的感知判定：d20 ＋ ``modifier`` ≥ ``dc`` 即成功（#112）。"""

    kind: Literal["perception_check"] = "perception_check"
    location: str
    roll: int
    modifier: int
    dc: int
    success: bool


class LocationRevealedEvent(_Model):
    kind: Literal["location_revealed"] = "location_revealed"
    location: str
    method: RevealMethod


class EventCheckEvent(_Model):
    """事件擲骰（Phase 5B-1）：``roll``（0～999）< ``chance_permille`` 且這一步沒遇敵、有合格骨架
    才觸發。``steps`` 是含這一步、距離上次事件的步數。"""

    kind: Literal["event_check"] = "event_check"
    location: str
    steps: int
    chance_permille: int
    roll: int
    triggered: bool


class EventTriggeredEvent(_Model):
    kind: Literal["event_triggered"] = "event_triggered"
    trigger: EventTrigger


class EventLeftEvent(_Model):
    """離開地點時沒處理的事件作罷（Phase 5B-1 代決 5B1-4）。``guaranteed``（5D-2b）：作罷的是保底
    觸發的那次（句子用保底的「誰」）；預設 ``False``，舊日誌照讀。"""

    kind: Literal["event_left"] = "event_left"
    skeleton: str
    location: str
    guaranteed: bool = False


class CareResult(_Model):
    """用心清單一筆的核對結果（核對不到「不算」，不是錯誤）。"""

    item: CareItem
    fact: str
    counted: bool
    reason_zh: str = ""
    """不算的原因（算的時候空字串）。"""


class SituationCheckEvent(_Model):
    """情境判定的擲骰明細（Phase 5B-2）。總值 ＝ ``roll`` ＋ 屬性修正 ＋ 用心加值 ＋ 種族加值。"""

    kind: Literal["situation_check"] = "situation_check"
    template: str
    skeleton: str
    attribute: Attribute
    method: str
    base_dc: int
    dc_shift: int
    dc: int
    dice: tuple[int, int]
    """一律擲兩顆 d20（亂數消耗固定）。"""
    mode: Literal["normal", "advantage", "disadvantage"]
    roll: int
    """採用的骰值（一般＝第一顆、優勢取高、劣勢取低）。"""
    attribute_mod: int
    care: tuple[CareResult, ...]
    care_bonus: int
    dropped: tuple[str, ...] = ()
    """因為玩家原文沒提到關鍵詞而拿掉的事實編號（5C-3d；也在 ``care`` 裡標「不算」）。"""
    race_bonus: int
    total: int
    outcome: Outcome
    source: Literal["llm", "fallback"]


class SituationResultEvent(_Model):
    """情境判定的獎懲（照模板的表與預算；Phase 5B-2）。"""

    kind: Literal["situation_result"] = "situation_result"
    template: str
    outcome: Outcome
    xp: int
    supplies_delta: int
    """補給的淨變化（含用心清單 ③ 拿出來的補給）。"""
    hp_lost: int
    next_battle: tuple[NextBattleMod, ...]
    """這次新增的下一場戰鬥修正。"""


class ThreadAddedEvent(_Model):
    kind: Literal["thread_added"] = "thread_added"
    thread: str
    scope: ThreadScope
    expires_at: int


class ThreadPushedOutEvent(_Model):
    """線頭滿了，最舊的被擠掉（提前結束）。"""

    kind: Literal["thread_pushed_out"] = "thread_pushed_out"
    thread: str
    scope: ThreadScope


class EventResolvedEvent(_Model):
    """事件以某個解法結束（Phase 5B-2：情境判定；5B-4b：放棄＝``abandoned``、交涉、戰鬥）。"""

    kind: Literal["event_resolved"] = "event_resolved"
    skeleton: str
    location: str
    solution: int
    """骨架 ``solutions`` 的索引。"""
    outcome: Outcome | Literal["abandoned"]


class EventSolvedEvent(_Model):
    """選了放棄、交涉、戰鬥或機遇解法（Phase 5B-4b、5B-4c）：付了多少補給、用掉哪條線頭；戰鬥解法
    之後接 ``encounter``，打完才 ``event_resolved``；機遇之後接 ``skill_offered``（``tier_bonus``＝
    這組候選高幾階，07 7.6）。"""

    kind: Literal["event_solved"] = "event_solved"
    skeleton: str
    solution: int
    solution_kind: Literal["combat", "parley", "abandon", "opportunity"]
    supplies_spent: int = 0
    thread_spent: str | None = None
    tier_bonus: int = 0


class ThreadSpentEvent(_Model):
    """線頭被用掉（Phase 5B-4b：交涉時拿人情抵付出）。"""

    kind: Literal["thread_spent"] = "thread_spent"
    thread: str


class ThreadExpiredEvent(_Model):
    """有到期結局的線頭到期（Phase 5B-4b；18.4「線頭到期例」）：給了旗標 ``flag``。"""

    kind: Literal["thread_expired"] = "thread_expired"
    thread: str
    scope: ThreadScope
    flag: str
    until: int | None = None
    """限時的世界旗標到這個時間失效（Phase 5B-4c）；``None``＝永久。"""


class StoryFlagClearedEvent(_Model):
    """劇情旗標移除（Phase 5B-4b：打贏線頭到期結局的變化陣容）。"""

    kind: Literal["story_flag_cleared"] = "story_flag_cleared"
    flag: str


class SkeletonUnlockedEvent(_Model):
    """信賴的 NPC 說出祕密，解鎖一個事件骨架（Phase 5B-4b；18.7.7）。"""

    kind: Literal["skeleton_unlocked"] = "skeleton_unlocked"
    skeleton: str
    npc: str


class NarratedEvent(_Model):
    """說書人的敘述（Phase 5B-3）：給前端顯示與之後的記憶。``skeleton`` 是敘述後的骨架。"""

    kind: Literal["narrated"] = "narrated"
    scene: StoryScene
    skeleton: str | None = None
    template: str | None = None
    outcome: Outcome | None = None
    npc: str | None = None
    story: StoryText
    source: Literal["llm", "fallback"]


class CampedEvent(_Model):
    kind: Literal["camped"] = "camped"
    location: str
    supplies_left: int
    hp: int
    mana: int


class RetreatedEvent(_Model):
    kind: Literal["retreated"] = "retreated"
    from_location: str
    to: str


class BattleStartedEvent(_Model):
    """開戰：地圖（已換皮成 ``region``）、敵方陣容與等級、天氣、主角開場 HP。"""

    kind: Literal["battle_started"] = "battle_started"
    location: str
    battle_map: str
    region: str
    lineup: EncounterLineup
    """敵方陣容（5A-6 起含情境判定的增援，增援排在最後）。"""
    enemy_level: int
    weather: str
    hero_hp: int
    fatigued: bool
    reinforcements: int = 0
    """這場的增援人數（5A-6）。"""
    first_team: Team | None = None
    """先手的陣營（5A-6：暗門我方先手、增援滿 4 名敵人先手；``None`` ＝ 照先攻）。"""
    hero_statuses: tuple[str, ...] = ()
    """開場掛在主角身上的狀態（5A-6：情境判定給的 buff／debuff）。"""
    mercenaries: tuple[str, ...] = ()
    """這場帶的系統傭兵（5C-1）。"""
    shadows: tuple[str, ...] = ()
    """這場帶的影子（主人的角色 ID；5C-2）。傭兵與影子都沒有＝獨行。"""
    companions: tuple[str, ...] = ()
    """這場帶的劇情夥伴（5C-3）。"""
    oath: str | None = None
    """這場帶的誓約模板（5C-3；``None``＝沒有誓約）。"""


class BattleEndedEvent(_Model):
    kind: Literal["battle_ended"] = "battle_ended"
    won: bool
    end_reason: str | None
    rounds: int
    hp: int
    mana: int
    xp_gained: int
    level: int
    skills_used: tuple[str, ...] = ()
    """這場主角用過的技能 ID（排序；Phase 5B-4b 導師任務鏈的條件）。"""


class LeveledUpEvent(_Model):
    kind: Literal["leveled_up"] = "leveled_up"
    level: int
    attribute_points: int
    """升到這級後未分配的屬性點總數。"""
    insight: int = 0
    """升到這級後未花的靈感點總數（5A-6）。"""
    skill_tier: int = 1
    """這個等級的角色階級（07 7.6；5A-6）。"""


class DefeatedEvent(_Model):
    """全滅（9.6.9 #98）：回小鎮、HP 回滿、下一場疲憊。"""

    kind: Literal["defeated"] = "defeated"
    location: str
    hp: int


class LocationClearedEvent(_Model):
    kind: Literal["location_cleared"] = "location_cleared"
    location: str
    respawn_at: int


class RestedEvent(_Model):
    kind: Literal["rested"] = "rested"
    location: str
    hp: int
    mana: int
    supplies: int


class LoadoutChangedEvent(_Model):
    kind: Literal["loadout_changed"] = "loadout_changed"
    skills: tuple[str, ...]
    bench: tuple[str, ...]


class TeleportedEvent(_Model):
    kind: Literal["teleported"] = "teleported"
    region: str
    location: str


class InsightGainedEvent(_Model):
    """得到靈感點（06 6.34.2；5A-6）：``source`` 例 ``elite:<種類>``。升級給的寫在
    ``leveled_up``。"""

    kind: Literal["insight_gained"] = "insight_gained"
    source: str
    amount: int
    insight: int


class SkillTierChangedEvent(_Model):
    """角色升階，主角技能照新階級重配（06 6.34.9；5A-6）。"""

    kind: Literal["skill_tier_changed"] = "skill_tier_changed"
    from_tier: int | None
    to_tier: int
    skills: tuple[str, ...]
    bench: tuple[str, ...]


class AttributesAllocatedEvent(_Model):
    kind: Literal["attributes_allocated"] = "attributes_allocated"
    attributes: dict[Attribute, int]
    attribute_points: int
    """分配後還剩的點數。"""


class AttributesRespeccedEvent(_Model):
    kind: Literal["attributes_respecced"] = "attributes_respecced"
    attribute_points: int
    """退回後未分配的點數。"""


class FlashOfferedEvent(_Model):
    """閃現或重閃出題（點數已付）。"""

    kind: Literal["flash_offered"] = "flash_offered"
    skill: str
    slot: int | None
    category: str | None
    cost: int
    options: int
    insight: int


class FlashPickedEvent(_Model):
    kind: Literal["flash_picked"] = "flash_picked"
    skill: str
    """選之前的技能 ID。"""
    new_skill: str
    pick: int
    slot: int | None = None
    """重閃的欄位；``None``＝閃現（Phase 5B-4b 導師任務鏈分辨閃現與重閃）。"""


class SkillDissolvedEvent(_Model):
    kind: Literal["skill_dissolved"] = "skill_dissolved"
    skill: str
    refund: int
    insight: int


class SkillInheritedEvent(_Model):
    kind: Literal["skill_inherited"] = "skill_inherited"
    skill: str
    source: str
    records: tuple[int, ...]
    new_skill: str


class OathSwornEvent(_Model):
    kind: Literal["oath_sworn"] = "oath_sworn"
    oath: OathState


class OathReleasedEvent(_Model):
    kind: Literal["oath_released"] = "oath_released"
    template: str
    cooldown_until: int


class QuestStartedEvent(_Model):
    kind: Literal["quest_started"] = "quest_started"
    quest: str
    quest_kind: QuestKind


class QuestStepDoneEvent(_Model):
    """完成任務的一步（Phase 5B-4）：``index`` 從 1 起；經驗與靈感已加上。"""

    kind: Literal["quest_step_done"] = "quest_step_done"
    quest: str
    step: str
    index: int
    xp: int = 0
    insight: int = 0
    flags: tuple[str, ...] = ()


class QuestCompletedEvent(_Model):
    kind: Literal["quest_completed"] = "quest_completed"
    quest: str


class SkillOfferedEvent(_Model):
    """任務或機遇給的技能三選一（候選存在角色的 ``pending_offers``；``source`` 見
    :class:`~trpg.world.state.PendingOffer`）。"""

    kind: Literal["skill_offered"] = "skill_offered"
    quest: str
    step: str
    reason: Literal["level_up", "complete"]
    candidates: tuple[str, ...]
    source: Literal["quest", "opportunity"] = "quest"


class SkillOfferTakenEvent(_Model):
    """選了任務給的技能（``skill`` 為 ``None`` ＝ 跳過）；``placed`` 是裝上或放進備用。"""

    kind: Literal["skill_offer_taken"] = "skill_offer_taken"
    quest: str
    step: str
    skill: str | None
    placed: Literal["equipped", "bench", "skipped"]
    source: Literal["quest", "opportunity"] = "quest"


class StorySkillGrantedEvent(_Model):
    """主線給的劇情技能（07 7.6；完整技能、放進備用）。"""

    kind: Literal["story_skill_granted"] = "story_skill_granted"
    quest: str
    step: str
    skill: str


class AffinityChangedEvent(_Model):
    """NPC 好感度變化（9.6.7 #5、#116）。``source`` 例 ``event:<骨架>``、``quest:<任務>``。"""

    kind: Literal["affinity_changed"] = "affinity_changed"
    npc: str
    delta: int
    value: int
    from_rank: AffinityRank
    rank: AffinityRank
    source: str


class TalkedEvent(_Model):
    """和 NPC 說話（9.6.7 #3）：依好感度能給的內容 ID 與可接的隱藏任務。"""

    kind: Literal["talked"] = "talked"
    npc: str
    affinity: int
    rank: AffinityRank
    entries: tuple[str, ...]
    quests_available: tuple[str, ...] = ()


class RumorsHeardEvent(_Model):
    """酒館的本週傳聞（9.6.7 #1）。"""

    kind: Literal["rumors_heard"] = "rumors_heard"
    week: int
    rumors: tuple[str, ...]


class OpportunityHintEvent(_Model):
    """還沒遇過機遇的角色在提示地點聽到的一句（5B-4e；``SocialTable.opportunity_hints``）。不改狀態。"""

    kind: Literal["opportunity_hint"] = "opportunity_hint"
    location: str
    text_zh: str


class PartyChangedEvent(_Model):
    """隊伍的傭兵換了（5C-1）。"""

    kind: Literal["party_changed"] = "party_changed"
    mercenaries: tuple[str, ...]
    shadows: tuple[str, ...] = ()
    """借用的影子（主人的角色 ID；5C-2）。"""
    shadow_names: tuple[str, ...] = ()
    """影子的名字（同 ``shadows`` 順序；顯示用）。"""
    ai: dict[str, str] = Field(default_factory=dict)


class ShadowSavedEvent(_Model):
    """在城鎮整備，自動存成影子（5C-2；#102）。"""

    kind: Literal["shadow_saved"] = "shadow_saved"
    level: int


class ShadowAiChangedEvent(_Model):
    """自己影子的預設打法換了（5C-2）。"""

    kind: Literal["shadow_ai_changed"] = "shadow_ai_changed"
    profile: str | None


class ShadowLentEvent(_Model):
    """借來的影子今天第一次被借用：主人得到任務幣與一則戰報（5C-2；#102）。"""

    kind: Literal["shadow_lent"] = "shadow_lent"
    owner: str
    coins: int


class OathBrokenEvent(_Model):
    """這場戰鬥違反了誓約（5C-3；06 6.26）：``at_end`` 為假＝戰鬥中違反（加成移除、破誓 2 回合）；
    真＝戰鬥結束時才判定沒達到（只記錄）。``check`` 是判定種類。誓約本身不解除，下一場恢復。"""

    kind: Literal["oath_broken"] = "oath_broken"
    template: str
    check: str
    at_end: bool = False


class OathKeptEvent(_Model):
    """這場戰鬥守住了誓約（5C-3）。"""

    kind: Literal["oath_kept"] = "oath_kept"
    template: str


class CompanionJoinedEvent(_Model):
    """劇情夥伴加入隊伍（5C-3，#97）；``replaced``：替下的成員（傭兵或影子主人 ID）。"""

    kind: Literal["companion_joined"] = "companion_joined"
    companion: str
    quest: str
    replaced: str | None = None
    replaced_name: str | None = None


class CompanionLeftEvent(_Model):
    """劇情夥伴離隊（任務結束，5C-3）；``restored``：還原回隊伍的成員，沒有＝不還原。"""

    kind: Literal["companion_left"] = "companion_left"
    companion: str
    restored: str | None = None
    restored_name: str | None = None


type WorldEvent = Annotated[
    TraveledEvent
    | EncounterCheckEvent
    | EncounterEvent
    | PerceptionCheckEvent
    | LocationRevealedEvent
    | CampedEvent
    | RetreatedEvent
    | BattleStartedEvent
    | BattleEndedEvent
    | LeveledUpEvent
    | DefeatedEvent
    | LocationClearedEvent
    | RestedEvent
    | LoadoutChangedEvent
    | TeleportedEvent
    | EventCheckEvent
    | EventTriggeredEvent
    | EventLeftEvent
    | SituationCheckEvent
    | SituationResultEvent
    | ThreadAddedEvent
    | ThreadPushedOutEvent
    | EventResolvedEvent
    | NarratedEvent
    | InsightGainedEvent
    | SkillTierChangedEvent
    | AttributesAllocatedEvent
    | AttributesRespeccedEvent
    | FlashOfferedEvent
    | FlashPickedEvent
    | SkillDissolvedEvent
    | SkillInheritedEvent
    | OathSwornEvent
    | OathReleasedEvent
    | QuestStartedEvent
    | QuestStepDoneEvent
    | QuestCompletedEvent
    | SkillOfferedEvent
    | SkillOfferTakenEvent
    | StorySkillGrantedEvent
    | AffinityChangedEvent
    | TalkedEvent
    | RumorsHeardEvent
    | OpportunityHintEvent
    | EventSolvedEvent
    | ThreadSpentEvent
    | ThreadExpiredEvent
    | StoryFlagClearedEvent
    | SkeletonUnlockedEvent
    | PartyChangedEvent
    | ShadowSavedEvent
    | ShadowAiChangedEvent
    | ShadowLentEvent
    | OathBrokenEvent
    | OathKeptEvent
    | CompanionJoinedEvent
    | CompanionLeftEvent
    | ItemBoughtEvent  # 5D-1
    | ItemSoldEvent
    | PouchChangedEvent
    | ItemUsedEvent
    | PouchUsedEvent
    | CurrencyGainedEvent
    | LootGainedEvent  # 5D-2
    | ItemEquippedEvent
    | LootChosenEvent  # 5D-2b
    | LootAbandonedEvent
    | GearCraftedEvent  # 5D-3
    | GearEnhancedEvent
    | AffixChangedEvent
    | GearSalvagedEvent
    | WorldEventStartedEvent  # 5F-1
    | WorldEventTargetEvent
    | WorldEventProgressEvent
    | WorldEventResolvedEvent
    | BountyClaimedEvent
    | BountyMissedEvent
    | DailyGoalDoneEvent
    | SealKeyGainedEvent  # 5F-3
    | SeasonBossChallengedEvent
    | SeasonBossClearedEvent
    | SeasonBossFailedEvent,
    Field(discriminator="kind"),
]
