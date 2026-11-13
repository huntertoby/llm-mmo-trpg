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
from trpg.api.skill_cards import SkillCard
from trpg.api.world_crafting_schemas import CraftingView
from trpg.api.world_economy_schemas import (
    InventoryView,
    PendingLootView,
    ShopView,
    WalletView,
)
from trpg.api.world_field_schemas import FieldHeroView, FieldView
from trpg.api.world_mail_schemas import MailBadgeView
from trpg.api.world_party_schemas import MyShadowView, PartyIntroView, PartyView
from trpg.api.world_range_schemas import RangeView, WorkshopView
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
from trpg.api.world_wish_schemas import WishView
from trpg.content.battle import LookChoice
from trpg.shared.rng import MASK64
from trpg.shared.types import Attribute, Team
from trpg.world.actions import (
    AcceptQuestAction,
    AllocateAction,
    CampAction,
    ChangeLookAction,
    ChangeRaceAction,
    DissolveAction,
    DuelChoiceAction,
    EventSolveAction,
    FlashAction,
    FlashPickAction,
    HintSeenAction,
    HintsOffAction,
    HintsResetAction,
    HireAction,
    InheritAction,
    LoadoutAction,
    NewsSeenAction,
    OfferPickAction,
    OpeningClassAction,
    OpeningConfirmAction,
    OpeningReselectAction,
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
    WishAction,
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
from trpg.world.field_actions import (
    SneakAction,
    UseFieldObjectAction,
    UseTeleportStoneAction,
    WalkAction,
)
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.season_events import SeasonBossAction

__all__ = [
    "AtlasRegionView",
    "AtlasView",
    "AttributeNoteView",
    "CreateWorldCharacterRequest",
    "EncounterEnemyView",
    "EncounterView",
    "GrowthView",
    "HereView",
    "HeroStatusView",
    "HintsStateView",
    "LevelUpView",
    "OathCurrentView",
    "OathParamView",
    "OathTemplateView",
    "OathView",
    "RegionStoneView",
    "TeleportOption",
    "WorldActionRequest",
    "WorldBattleResponse",
    "WorldCharacterSummary",
    "WorldCharacterView",
    "WorldClockView",
    "WorldDevBattleResponse",
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
    | DuelChoiceAction  # RG-2
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
    | HintSeenAction  # 6F-4
    | HintsOffAction
    | HintsResetAction
    | ChangeRaceAction  # 6R-1（#138 本季免費換種族）
    | ChangeLookAction  # 6R-2（#137 主城免費改外觀）
    | OpeningConfirmAction  # TR-1（#134 主城工坊靶場的「確定出發」）
    | OpeningClassAction  # OB-1（#150 靶場選大類）
    | OpeningReselectAction  # OB-3（#150 4 級前的免費重選）
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
    | SeasonBossAction  # 5F-3
    | WalkAction  # 6B-2
    | UseTeleportStoneAction
    | SneakAction  # 6C-5
    | UseFieldObjectAction
    | WishAction,  # WP-2（#88 許願池）
    Field(discriminator="kind"),
]
"""``POST /api/world/characters/{id}/actions`` 的請求（``fight`` 走開戰端點；``swear_oath`` 只收
``source: "menu"``，代決 5A7-4；情境判定與敘述只能經 ``/situation``、``/chat`` 由伺服器組提議，
5B-5；``event_solve`` 是放棄、交涉、戰鬥解法，5B-5b）。"""


class CreateWorldCharacterRequest(_ApiModel):
    """建立大世界角色（07 7.6 創角）。選項沿用 ``GET /api/runs/start-options``。"""

    name: str = Field(min_length=1, max_length=NAME_MAX)
    """角色名稱（只顯示用；前後空白會去掉）。"""
    weapon: str | None = None
    keywords: tuple[str, ...] | None = None
    """TR-1（#134）：正式流程兩個都省略——角色停在主城工坊靶場（未完成開局），武器與 2 個關鍵字
    在那裡試用後選（``opening_class``）。兩個都給＝建角就選好（舊流程，OB-1 起只留開發模式，
    正式模式 403，:meth:`dev_fields`）；只給一個 422。"""
    race: str | None = None
    origin: str | None = None
    seed: int | None = Field(default=None, ge=0, le=MASK64)
    """起始技能的種子；省略由伺服器亂數（TR-1：未完成開局時存在角色身上，確定出發用它）。"""
    look: LookChoice | None = None
    """（6R-2，#137）建角時選的外觀：只有選項代碼，要在種族的 ``look_options`` 內（不合法 422）；
    省略＝種族預設。只在畫面，不影響數值。"""
    legacy_character: str | None = Field(default=None, max_length=32)
    """（5F-5）沿用這個上季角色（``GET /api/world/legacy``）的外觀：名字與紙娃娃（名字取代
    ``name``）。種族不算外觀（5F-5c）：``race`` 省略＝帶上季的，給了就照新選；種族改了時
    紙娃娃跟著種族的部件改回預設。等級、技能、裝備照新角色。不是自己帳號的 404。"""

    def dev_fields(self) -> list[str]:
        """有填的開發用欄位（OB-1，#150：舊流程建角只留開發模式）。"""
        used = {"weapon": self.weapon is not None, "keywords": self.keywords is not None}
        return [name for name, on in used.items() if on]

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
    hero_look: FieldHeroView | None = None
    """（QK-2b）角色清單的 Q 版頭像：紙娃娃外觀（同實地地圖主角的 ``FieldHeroView``；純顯示）。"""
    origin_realm: str | None = None
    """（QK-2b）出身的區域 ID（``origins.yaml`` 的 ``realm``；頭像框色）；沒有出身為 ``None``。"""


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
    weapon_blocked: tuple[str, ...] = ()
    """主手是別大類時暫時不能用的技能 ID（戰鬥裡不出現；換回同大類就恢復，6T-1b、08 8.13 #135）。"""
    weapon_blocked_zh: str | None = None
    """同上的一句說明：「主手是遠程武器：〈招名〉暫時不能用」；沒有時 ``None``。"""
    race: str | None = None
    """種族 ID（6R-1；``races.yaml``，名稱見 ``race_name_zh``）。"""
    free_race_change: bool = False
    """（6R-1，#138）這一季還能免費換一次種族（動作 ``change_race``，在主城）。"""
    free_race_change_zh: str | None = None
    """現在不能換的原因（例：「只有在主城能換種族」）；能換時 ``None``。"""
    look: LookChoice | None = None
    """（6R-2，#137）目前自己選的外觀；``None``＝種族預設。"""
    look_change_zh: str | None = None
    """現在不能改外觀的原因（例：「只有在主城能改外觀」）；能改時 ``None``（動作
    ``change_look``）。"""
    hero_look: FieldHeroView | None = None
    """（QK-2b）HUD 主角卡的 Q 版頭像：紙娃娃外觀（同 ``FieldHeroView``；純顯示）。"""
    origin_realm: str | None = None
    """（QK-2b）出身的區域 ID（頭像框色）；沒有出身為 ``None``。"""


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
    fog: Literal["visited", "silhouette", "fog"] = "visited"
    """區域圖的戰爭迷霧（21.1；6C-6）：``visited``＝去過（彩色、名字、建議等級、清空狀態）；
    ``silhouette``＝和去過的相連但沒去過（灰色剪影、「？？？」與建議等級）；``fog``＝更遠，被霧蓋住。"""
    quest_marks: tuple[str, ...] = ()
    """進行中的任務，目前這一步要到這裡（到達或在這裡打贏；任務名稱，依任務 ID；6C-6）。"""
    footprints: tuple[str, ...] = ()
    """去過這裡的朋友（其他角色）的名字（6C-5；依角色 ID，最多 3 位；霧裡的地點不給）。"""


class RegionStoneView(_ApiModel):
    """區域圖上的傳送石（21.2；6C-6）。只列在去過或剪影的地點上（霧裡的不給）。"""

    id: str
    location: str
    """傳送石所在的地點 ID。"""
    unlocked: bool
    here: bool
    """現在出發的那一顆（站在上面，或所在城鎮的那一顆）。"""


class WorldMapView(_ApiModel):
    region: str
    name_zh: str
    level_zh: str
    locations: tuple[WorldLocationView, ...]
    edges: tuple[tuple[str, str], ...]
    stones: tuple[RegionStoneView, ...] = ()
    """這一區的傳送石（依 ID；6C-6）。"""
    can_teleport: bool = False
    """現在能從區域圖點已解鎖的傳送石傳過去（站在傳送石上或在城鎮裡、沒有遭遇或戰鬥；21.1）。"""
    teleport_problem_zh: str | None = None
    """不能從圖上傳送的原因（``can_teleport`` 時為 ``None``）。"""
    art_url: str | None = None
    """區域插畫的路徑（還沒有插畫＝``None``，畫面用節點圖當底圖；6C-6）。"""
    hub: bool = False
    """主城這類樞紐（內容的 ``hub: true``；6D-R2）：沒有區域圖，開地圖直接開大世界圖。"""


class AtlasRegionView(_ApiModel):
    """大世界圖上的一區（6D-5；21.1）。"""

    region: str
    name_zh: str
    status: Literal["open", "locked", "later"]
    """``open``＝已開放（彩色）；``locked``＝灰色剪影＋解鎖條件；``later``＝「之後的賽季」。"""
    condition_zh: str | None = None
    town: str | None = None
    town_name_zh: str | None = None
    current: bool = False
    """自己在這一區（主城：在主城裡）。"""
    can_teleport: bool = False
    """現在能點這一區的城鎮直接傳送（送 ``teleport``）。"""
    free: bool = False
    """這一區是第一次免費傳送的新手區（RT-5，#125、21 21.5）：角色在主城、還沒到過那一區的小鎮
    （:func:`trpg.world.atlas.free_first_teleport`）。傳送鈕寫「免費」；到過之後就是 ``False``。"""


class AtlasView(_ApiModel):
    """大世界圖（6D-5；21.1、9.6.5）：五區漂浮的界域與中央的主城浮島。只能看；站在傳送石上或在城鎮裡
    打開時，可以點已開放區的城鎮傳送。"""

    regions: tuple[AtlasRegionView, ...]
    """``regions.yaml`` 的順序。"""
    capital: AtlasRegionView
    can_teleport: bool = False
    teleport_problem_zh: str | None = None
    art_url: str | None = None
    """大世界圖插畫（還沒有＝``None``，畫面用程式畫的浮島）。"""
    maps: tuple[WorldMapView, ...] = ()
    """已開放、但不是所在區的區域圖（點大世界圖上的那一區進去看；只能看）。"""


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


type EnemyRank = Literal["normal", "elite", "boss"]
"""遇敵卡的階級標記（UI-E3b，純顯示）：``boss``＝範本帶 ``boss`` 標籤；``elite``＝精英範本或套了
精英詞綴；其餘 ``normal``。"""


class EncounterEnemyView(_ApiModel):
    name_zh: str
    elite: bool
    affix_zh: str | None
    third: bool = False
    """第三方（Phase 5B-M3 三方混戰：和我方、敵方都敵對）。"""
    rank: EnemyRank = "normal"
    """階級標記（UI-E3b）：前端畫精英、頭目金環用；不影響規則與重播。"""
    look: FieldHeroView | None = None
    """這一名的紙娃娃外觀（UI-E3b；格式同實地地圖人物的 ``FieldHeroView``：``doll_look`` 含異形的
    ``creature``、頭目的 ``rarity``、精英詞綴的 ``affixes``）；純顯示。"""


class BattlefieldRectView(_ApiModel):
    """就地開打切出的戰場在實地地圖上的範圍（Phase 6C-2；格子座標）：畫面用 6B-6 的 ``frameCamera``
    框住它。"""

    field_map: str
    x: int
    y: int
    width: int
    height: int


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
    battlefield: BattlefieldRectView | None = None
    """就地開打切出的戰場（6C-2）；``None``＝用地點原本的戰鬥地圖模板。"""
    battlefield_fallback_zh: str | None = None
    """碰到地圖上的敵人卻改用模板的原因（6C-2，例「站位放不下」）。"""
    duel: Literal["offered", "accepted", "declined"] | None = None
    """精英單挑（RG-2，#162）：``offered``＝排最前的精英要求一對一（送 ``duel_choice``；還沒選就
    開打＝拒絕），``accepted``＝一對一（``enemies`` 只有精英本人、我方只有主角），``declined``＝照
    原本全隊打。兩邊獎勵一樣。``None``＝沒有提出單挑。"""
    duel_zh: str | None = None
    """單挑的說明句（例「狂暴的霧狼要求一對一：接受＝只有你和牠，拒絕＝照原本全隊打；兩邊獎勵一樣」）。"""


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
    can_flash: bool
    """可以閃現、重閃（``can_spend`` 成立，而且沒有被 #150 第 6 點擋住：開局還沒結束的角色 4 級前
    不能閃現）。溶掉、傳承、重配另外看 ``can_spend``。"""
    flash_blocked_zh: str | None
    """被 #150 第 6 點擋住時的原因（「4 級前不能閃現」）；其他時候 ``None``（地點等原因看
    ``blocked_zh``）。"""
    starter_note_zh: str | None = None
    """入門期（還沒正式選定）接在 ``service_zh`` 那一行後面的話（OB-6，玩法 PM「OB-5b 後補定」）；
    其他時候 ``None``。"""


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


class OpeningLineView(_ApiModel):
    """開場的一句話（6F-2，#125）。"""

    speaker_zh: str
    text_zh: str


class GuideView(_ApiModel):
    """新手指引（6F-2，筆記 U2、#125）：任務追蹤器沒有任務時顯示的那一行。"""

    text_zh: str
    """例「到霧渡鎮找渡婆婆」。"""
    how_zh: str | None = None
    """怎麼去（例「站上中央廣場的傳送陣……」）。"""
    opening: tuple[OpeningLineView, ...] = ()
    """在主城、還沒到過新手區時的開場（說書人＋守印人）；其他時候空。"""


class AttributeNoteView(_ApiModel):
    """配點教學裡一個屬性的說明（#133；滑過時顯示，第 1 行「你的技能：…」由畫面從
    ``hero.attribute_affects`` 帶入）。"""

    attr: Attribute
    text_zh: str


class LessonView(_ApiModel):
    """教學（6F-2，#132；6F-4，#133）：``allocate``＝升到 2 級後葛蘭先教配點、``flash``＝第一次
    閃現、``reflash``＝升到 3 級後改教重閃。每種每個角色只跳一次（看過記在角色的 ``hints_seen``：
    ``lesson:<種類>``）、可以略過。"""

    kind: Literal["allocate", "flash", "reflash", "choose"]
    """``choose``（OB-5，#150 第 3 點）：入門期打完新手前兩步、人在導師的城鎮或主城——畫面打開
    「正式選定」整頁（資料在 ``WorldView.opening.choice``）；不記看過，選定前每次到都會出。"""
    lines: tuple[OpeningLineView, ...]
    skills_zh: tuple[str, ...] = ()
    """建議的招（``flash``：戰鬥中用過、還沒閃過的；``reflash``：閃過的）。"""
    points: int = 0
    """``allocate``：這次要分配的屬性點（升級給的、還沒分的）。"""
    start_points: int = 0
    """``allocate``：開局已照推薦配好的點數（規則 ``roguelite.yaml`` 的
    ``start_free_points``；6F-4b，
    守則 4：畫面不寫死）。教學顯示「共 ``start_points`` ＋ ``points`` 點」。"""
    recommended: dict[Attribute, int] = Field(default_factory=dict)
    """``allocate``：推薦配法（07 7.2：升級的點給兩招中目前比較低的屬性；同屬性全給它）。"""
    recommended_zh: str = ""
    done_zh: str | None = None
    """``allocate``：配完之後導師說的話（接第一次閃現）。"""
    skip_zh: str | None = None
    """``allocate``：按「之後再說」時導師說的話。"""
    notes: tuple[AttributeNoteView, ...] = ()
    """``allocate``：六個屬性的白話說明（滑過時）。"""
    respec: bool = False
    """``allocate``（OB-3，#150）：點數已經全部照推薦配好（走新開局流程、正式選定之後），教學要
    先重配（``respec``）再自己分配；``points`` 是重配後能分的全部點數，``start_points`` 為 0。
    略過記 ``lesson:allocate_skip``、上完記 ``lesson:allocate``（分開記）。"""
    reminder: bool = False
    """``allocate``（OB-3）：略過之後第一次進城鎮或營火的再提示（只出這一次；出過記
    ``lesson:allocate_again``，照做完記 ``lesson:allocate``）。"""
    reselect_reminder: tuple[OpeningLineView, ...] = ()
    """``allocate``、``respec``（OB-6 Q2）：收尾彈窗的第二段——導師提醒 4 級前可以免費重選一次；
    只在還有重選資格時有（:func:`trpg.world.opening_reselect.reselect_window_problem`），其他時候空。"""


class LevelUpView(_ApiModel):
    """升級畫面（6F-4 C2）：等級比 ``level_seen`` 高時出；看過用 ``hint_seen`` 的 ``level`` 記。"""

    level: int
    text_zh: str
    """例「升到 2 級：屬性點 +2、靈感 +1。回霧渡鎮找導師堂的葛蘭，學怎麼配點。」"""


class HintsStateView(_ApiModel):
    """提示與教學的紀錄（6F-4，6F-2b：記在角色身上）。"""

    seen: tuple[str, ...] = ()
    off: bool = False


class BattleHintView(_ApiModel):
    """戰鬥短提示（6F-2，#99）：畫面照 ``trigger`` 判斷戰況，每種每個角色只出一次、可以關。"""

    id: str
    trigger: Literal[
        "battle_start",
        "enemy_on_water",
        "water_present",
        "reaction",
        "ice_present",
        "trap_present",
        "lethal_terrain",
        "pushed",
    ]
    text_zh: str
    terrains: tuple[str, ...] = ()
    """``lethal_terrain`` 的致命地形 ID（``terrain.yaml`` 的 ``deadly``）；其他觸發空。"""


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
    field: FieldView | None = None
    """目前的實地地圖與自己的位置（Phase 6B-2；所在地點沒有實地地圖＝``None``，照舊用
    ``travel``）。"""
    atlas: AtlasView | None = None
    """大世界圖（Phase 6D-5；M 在區域圖上再按一次）。"""
    guide: GuideView | None = None
    """新手指引（6F-2）：還沒到過新手區，或到了還沒接新手任務時有；其他時候 ``None``。"""
    battle_hints: tuple[BattleHintView, ...] = ()
    """戰鬥中（``battle_id`` 有值）這場可能出現的短提示（6F-2，#99）；其他時候空。"""
    lesson: LessonView | None = None
    """教學（6F-2，#132；6F-4，#133 配點教學排在第一次閃現之前）；條件不符時 ``None``。"""
    level_up: LevelUpView | None = None
    """升級畫面（6F-4 C2）；沒有新升的等級時 ``None``。"""
    hints: HintsStateView = Field(default_factory=HintsStateView)
    """提示與教學的紀錄（6F-4）。"""
    mail: MailBadgeView | None = None
    """所在區域的郵差與有信時的「✉」（6T-1a；郵寄面板另用 ``GET …/mail``）。沒有郵差為 ``None``。"""
    opening: RangeView | None = None
    """未完成開局（TR-1，#134）：角色停在主城工坊靶場時的資料（畫面顯示靶場、不顯示地圖）；已完成
    為 ``None``。"""
    limits: dict[str, str] = Field(default_factory=dict)
    """開局還沒結束時不開放的系統 → 原因（OB-5，#150 第 7、9 點；
    :func:`trpg.world.opening.opening_limits`）：面板照它把按鈕標成不可用並說明原因。鍵：``race``、
    ``flash``、``loadout``、``hire``、``league``、``season_boss``、``oath``、``main_hand``、``smith``、
    ``dissolve``。已完成開局＝空。"""
    workshop: WorkshopView | None = None
    """主城工坊師傅的選單（PR-2a，#147）：人在主城、內容有靶場與師傅選單時才有；其他 ``None``。"""
    party_intro: PartyIntroView | None = None
    """還沒播的隊友加入台詞（OB-7，#154；:func:`trpg.api.world_party_intro.party_intro`）：開局還沒
    結束時，賽倫在確定出發後、阿岳在新手第 1 步打完後各一段；戰鬥中、沒有時 ``None``。"""
    wish: WishView | None = None
    """主城許願池的面板資料（WP-2，#88；:func:`trpg.api.world_wish_view.wish_view`）：人在主城才有。"""


class WorldBattleResponse(_ApiModel):
    world: WorldView
    battle: BattleResponse


class WorldDevBattleResponse(_ApiModel):
    """開發用 Boss 戰入口（6F-3，``POST …/dev-boss``）：不回寫世界的一場戰鬥（既有戰鬥畫面）。"""

    title_zh: str
    battle: BattleResponse
