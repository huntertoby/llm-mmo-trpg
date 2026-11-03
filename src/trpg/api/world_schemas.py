"""大世界的 API 格式（Phase 5A-5；``/api/world``，``docs/phases/Phase5計畫.md`` 11.3）。

``WorldView`` 是地點圖畫面的整份資料，全部由後端算好（前端不寫規則）。未發現的隱藏地點與連到它的
連線不放進回應。

Phase 5B-5（18.4）：事件卡、情境判定結果、這裡的 NPC、對話、任務日誌、可接的任務、技能三選一、線頭、
酒館傳聞（:mod:`trpg.api.world_story_schemas`）；動作加接任務、選三選一、說話、酒館。

Phase 5A-7（13.2）：成長的世界動作（配點、重配、閃現、選閃現、溶掉、傳承、立誓、解除誓約）；
``WorldView`` 加上一輪格式的主角面板（``hero``，前端重用配點與閃現元件）、待選閃現、成長與誓約的
可用狀態、下一場修正、開場說明、最近一次戰鬥結果。
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from trpg.api.run_schemas import HeroOut, PendingFlashOut
from trpg.api.schemas import BattleResponse
from trpg.api.world_crafting_schemas import CraftingView
from trpg.api.world_economy_schemas import (
    InventoryView,
    PendingLootView,
    ShopView,
    WalletView,
)
from trpg.api.world_party_schemas import MyShadowView, PartyView
from trpg.api.world_story_schemas import (
    DialogLineView,
    EventView,
    NpcHereView,
    PendingOfferView,
    QuestHereView,
    QuestLogView,
    SituationResultView,
    ThreadView,
)
from trpg.narrative.skills import SkillCard
from trpg.shared.rng import MASK64
from trpg.shared.types import Team
from trpg.world.actions import (
    AcceptQuestAction,
    AllocateAction,
    CampAction,
    DissolveAction,
    EventSolveAction,
    FlashAction,
    FlashPickAction,
    HireAction,
    InheritAction,
    LoadoutAction,
    NewsSeenAction,
    OfferPickAction,
    ReleaseOathAction,
    RespecAction,
    RestAction,
    RetreatAction,
    ShadowAiAction,
    SwearOathAction,
    TalkAction,
    TavernAction,
    TeleportAction,
    TravelAction,
)
from trpg.world.crafting_actions import (
    CraftAction,
    EnhanceAction,
    ImbueAction,
    RerollAction,
    SalvageAction,
)
from trpg.world.economy_actions import (
    BuyAction,
    EquipAction,
    LootChooseAction,
    PouchAction,
    SellAction,
    UseItemAction,
)
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.season_events import SeasonBossAction

__all__ = [
    "CreateWorldCharacterRequest",
    "EncounterEnemyView",
    "EncounterView",
    "GrowthView",
    "HereView",
    "HeroStatusView",
    "OathCurrentView",
    "OathParamView",
    "OathTemplateView",
    "OathView",
    "TeleportOption",
    "WorldActionRequest",
    "WorldBattleResponse",
    "WorldCharacterSummary",
    "WorldCharacterView",
    "WorldClockView",
    "WorldLocationView",
    "WorldMapView",
    "WorldView",
]

NAME_MAX = 12


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


type WorldActionRequest = Annotated[
    TravelAction
    | CampAction
    | RetreatAction
    | RestAction
    | LoadoutAction
    | TeleportAction
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
    | NewsSeenAction  # 5F-1b
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
    | LeagueEnterAction  # 5F-4
    | LeagueWithdrawAction
    | SeasonBossAction,  # 5F-3
    Field(discriminator="kind"),
]
"""``POST /api/world/characters/{id}/actions`` 的請求（``fight`` 走開戰端點；``swear_oath`` 只收
``source: "menu"``，代決 5A7-4；情境判定與敘述只能經 ``/situation``、``/chat`` 由伺服器組提議，
5B-5；``event_solve`` 是放棄、交涉、戰鬥解法，5B-5b）。"""


class CreateWorldCharacterRequest(_ApiModel):
    """建立大世界角色（07 7.6 創角）。選項沿用 ``GET /api/runs/start-options``。"""

    name: str = Field(min_length=1, max_length=NAME_MAX)
    """角色名稱（只顯示用；前後空白會去掉）。"""
    weapon: str
    keywords: tuple[str, ...]
    race: str | None = None
    origin: str | None = None
    seed: int | None = Field(default=None, ge=0, le=MASK64)
    """起始技能的種子；省略由伺服器亂數。"""

    @field_validator("name")
    @classmethod
    def _strip(cls, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("名稱不可空白")
        return name


class WorldCharacterSummary(_ApiModel):
    character_id: str
    name: str
    level: int
    region_name_zh: str
    location_name_zh: str


class WorldCharacterView(_ApiModel):
    character_id: str
    name: str
    level: int
    xp: int
    xp_next: int | None
    """下一級的經驗門檻；已到頂為 ``None``。"""
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    supplies: int
    max_supplies: int
    fatigued: bool
    attribute_points: int
    weapon_name_zh: str
    race_name_zh: str | None
    skills: tuple[SkillCard, ...]
    """裝備的技能。"""
    bench: tuple[SkillCard, ...]
    """備用技能（擁有但沒裝上）。"""
    slots_zh: str
    """技能欄位上限的說明。"""
    insight: int = 0
    """還沒花的靈感點（5A-7）。"""
    skill_tier: int = 1
    """角色階級（07 7.6；5A-7）。"""


class WorldLocationView(_ApiModel):
    id: str
    name_zh: str
    kind: str
    kind_zh: str
    level_zh: str | None
    """建議等級（例：``Lv 3～4``）；城鎮與傳送點沒有。"""
    description_zh: str
    x: int
    y: int
    current: bool
    adjacent: bool
    """和目前位置相鄰。"""
    blocked_zh: str | None
    """相鄰但現在不能走過去的原因（例：還沒開放、有遭遇）；可以走時為 ``None``。"""
    cleared: bool
    """已清空（還沒重生，9.6.7 #15）。"""
    hidden: bool
    """隱藏地點（已發現才會出現在回應裡）。"""


class WorldMapView(_ApiModel):
    region: str
    name_zh: str
    level_zh: str
    locations: tuple[WorldLocationView, ...]
    edges: tuple[tuple[str, str], ...]


class TeleportOption(_ApiModel):
    region: str
    name_zh: str


class HereView(_ApiModel):
    location: str
    name_zh: str
    kind_zh: str
    description_zh: str
    can_rest: bool
    can_loadout: bool
    camp_problem_zh: str | None
    """不能紮營的原因；可以紮營時為 ``None``。"""
    camped: bool
    """正在這裡紮營（營火）。"""
    teleports: tuple[TeleportOption, ...]
    hasten_cost: int
    camp_cost: int
    can_tavern: bool = False
    """城鎮的酒館（本週傳聞，9.6.7 #1；5B-5；``event_solve`` 是放棄、交涉、戰鬥解法，5B-5b）。"""


class HeroStatusView(_ApiModel):
    """開場掛在主角身上的狀態（5A-6／5A-6b：不擲抵抗、最多 2 回合）。"""

    id: str
    name_zh: str
    description_zh: str
    beneficial: bool
    rounds: int | None
    """持續回合（``None`` ＝ 不倒數）。"""


class EncounterEnemyView(_ApiModel):
    name_zh: str
    elite: bool
    affix_zh: str | None
    third: bool = False
    """第三方（Phase 5B-M3 三方混戰：和我方、敵方都敵對）。"""


class EncounterView(_ApiModel):
    location: str
    location_name_zh: str
    enemy_level: int
    map_name_zh: str
    weather_zh: str
    day_phase_zh: str
    enemies: tuple[EncounterEnemyView, ...]
    retreat_to_zh: str
    fatigued: bool
    """開場帶疲憊（HP 打折，9.6.9 #98）。"""
    hero_hp: int
    """主角開場 HP。"""
    in_battle: bool
    reinforcements: int = 0
    """這場的增援人數（已在 ``enemies`` 裡，排在最後；5A-6）。"""
    first_team: Team | None = None
    """先手的陣營（只影響第 1 輪，5A-6b）；``None`` ＝ 照先攻。"""
    hero_statuses: tuple[HeroStatusView, ...] = ()
    opening_zh: tuple[str, ...] = ()
    """開場說明（先手、開場狀態、增援）的句子；戰鬥畫面開場也顯示（5A-7）。"""
    allies_zh: str = ""
    """我方的說明（例「主角（開場 HP 30）＋青鋒、回春」；5C-1）。"""


class WorldClockView(_ApiModel):
    time_zh: str
    """遊戲內時刻 ``HH:MM``。"""
    day_phase: Literal["day", "night"]
    day_phase_zh: str
    weather_zh: str


class GrowthView(_ApiModel):
    """成長服務的可用狀態（5A-7；規則照 ``trpg.world.growth``）。"""

    insight: int
    skill_tier: int
    at_service: bool
    """在城鎮或營火（閃現、重閃、溶掉、傳承、重配、立誓的地點）。"""
    service_zh: str
    """地點限制的說明。"""
    can_allocate: bool
    """可以分配屬性點（有點數、沒有遭遇、不在戰鬥、沒有待選閃現）。"""
    can_spend: bool
    """可以花靈感與重配（城鎮或營火、沒有遭遇、不在戰鬥、沒有待選閃現）。"""
    blocked_zh: str | None
    """不能花點的原因；可以時為 ``None``。"""
    pending: bool
    """有待選的閃現（選之前其他動作都不行）。"""


class OathParamView(_ApiModel):
    id: str
    kind: Literal["choice", "int"]
    choices: tuple[str, ...] = ()
    min: int = 0
    max: int = 0
    name_zh: str = ""
    """參數的中文名（例「元素」；5C-3）。"""
    choice_names_zh: dict[str, str] = {}
    """``choice`` 每個值的中文名（5C-3）。"""


class OathTemplateView(_ApiModel):
    id: str
    name_zh: str
    difficulty: Literal["easy", "medium", "hard"]
    difficulty_zh: str
    params: tuple[OathParamView, ...] = ()
    description_zh: str = ""
    bonus_zh: str = ""
    """加成（例「〔誓約之力・中〕：造成的攻擊傷害 +10%」；有 ``difficulty_by`` 時列出各檔）。"""
    judge_zh: str = ""
    """判定時機（「戰鬥中判定：違反時立刻移除加成」／「戰鬥結束時判定」）。"""


class OathCurrentView(_ApiModel):
    template: str
    name_zh: str
    difficulty_zh: str
    params_zh: str
    """參數的文字（例「元素：火焰」）；沒有參數時空字串。"""
    sworn_at: int
    bonus_zh: str = ""
    """這個誓約的加成（5C-3）。"""
    judge_zh: str = ""


class OathView(_ApiModel):
    """誓約（06 6.26、09 9.6.10 #106；模板內容在 5C-3）。"""

    available: bool
    """內容庫有誓約模板（``world/oaths.yaml``）。"""
    unavailable_zh: str | None
    """沒有模板時的說明（「尚未開放」）。"""
    current: OathCurrentView | None
    cooldown_until: int
    cooldown_zh: str | None
    """解除後還要多久才能再立；沒有冷卻時為 ``None``。"""
    can_swear: bool
    swear_problem_zh: str | None
    can_release: bool
    templates: tuple[OathTemplateView, ...] = ()
    penalty_zh: str = ""
    """違反的後果（#27；例「違反：本場加成移除＋〔破誓〕2 回合，下一場恢復」）。"""
    slot_zh: str = ""
    """「誓約佔 1 格被動欄位」（06 6.26）。"""


class WorldView(_ApiModel):
    character: WorldCharacterView
    map: WorldMapView
    here: HereView
    encounter: EncounterView | None
    clock: WorldClockView
    events: tuple[str, ...]
    """這次請求的世界事件（中文句子）。"""
    battle_id: str | None
    hero: HeroOut
    """一輪格式的主角面板（屬性、靈感、每招的閃現狀態；5A-7，前端重用配點與閃現元件）。"""
    pending_flash: PendingFlashOut | None = None
    """待選閃現（5A-7）。"""
    growth: GrowthView
    oath: OathView
    next_battle_zh: tuple[str, ...] = ()
    """角色身上的下一場修正（每筆一句；5A-7）。"""
    last_battle_zh: str | None = None
    last_loot_zh: str | None = None
    """最近一次戰鬥的掉落（Phase 5D-2，例「掉落：霧晶 ×1、稀有短劍（1 級）。」）。"""
    pending_loot: PendingLootView | None = None
    """背包滿了、等戰後結算選要丟哪件（Phase 5D-2b；沒有為 ``None``）。"""
    """最近一次戰鬥結果的一句話（5A-5 待決 1；沒打過為 ``None``）。"""
    event: EventView | None = None
    """事件卡（5B-5；``event_solve`` 是放棄、交涉、戰鬥解法，5B-5b）。"""
    situation_result: SituationResultView | None = None
    """這次請求的情境判定明細與結果敘述。"""
    npcs_here: tuple[NpcHereView, ...] = ()
    dialog: tuple[DialogLineView, ...] = ()
    """這次請求的 NPC 回話與聊到的內容（前端自己保留紀錄，代決 5B5-8）。"""
    quests: tuple[QuestLogView, ...] = ()
    """任務日誌。"""
    quests_here: tuple[QuestHereView, ...] = ()
    pending_offer: PendingOfferView | None = None
    threads: tuple[ThreadView, ...] = ()
    rumors: tuple[str, ...] = ()
    """這次請求在酒館聽到的本週傳聞。"""
    party: PartyView | None = None
    """隊伍與系統傭兵（5C-1）、可借的影子（5C-2）。"""
    my_shadow: MyShadowView | None = None
    """自己的影子與被借用的戰報（5C-2）。"""
    wallet: WalletView | None = None
    """金幣與任務幣（5D-1；沒有經濟資料時為 ``None``）。"""
    inventory: InventoryView | None = None
    """背包與腰包（5D-1）。"""
    shop: ShopView | None = None
    """角色所在地點的店（5D-1；沒有店為 ``None``）。"""
    crafting: CraftingView | None = None
    """角色所在地點的鐵匠與附魔台（5D-3；沒有設施為 ``None``）。"""


class WorldBattleResponse(_ApiModel):
    world: WorldView
    battle: BattleResponse
