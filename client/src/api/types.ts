// API 型別：由 OpenAPI 產生的 schema.d.ts 取別名；`events` 在 OpenAPI 中是任意 JSON，這裡手寫窄化。
import type { components } from "./schema";

type Schemas = components["schemas"];

export type BattleResponse = Schemas["BattleResponse"];
export type BattleView = Schemas["BattleView"];
export type TileView = Schemas["TileView"];
export type UnitView = Schemas["UnitView"];
export type ChargeView = Schemas["ChargeView"];
export type ObjectView = Schemas["ObjectView"];
export type TrapView = Schemas["TrapView"];
export type ZoneView = Schemas["ZoneView"];
export type RuneView = Schemas["RuneView"];
export type ActivationView = Schemas["ActivationView"];
export type GearSkillView = Schemas["GearSkillView"];
export type GrantedSkillView = Schemas["GrantedSkillView"];
export type StatusView = Schemas["StatusView"];
export type Pending = Schemas["Pending"];
export type Action = Schemas["Action"];
export type MoveAction = Schemas["Move"];
export type AttackAction = Schemas["Attack"];
export type UseSkillAction = Schemas["UseSkill-Output"];
export type UseRaceSkillAction = Schemas["UseRaceSkill"];
export type RaceView = Schemas["RaceView"];
/** 頭目部位（PB-1c）：單位卡上的部位、選部位選單的一列、一個「目標有部位」的動作的選項。 */
export type PartView = Schemas["PartView"];
export type PartOption = Schemas["PartOptionOut"];
export type PartActionOptions = Schemas["PartActionOut"];
export type StepOut = Schemas["StepOut"];
export type Pos = Schemas["Pos"];
export type Team = Schemas["Team"];
export type Surface = Schemas["Surface"];
export type MapSummary = Schemas["MapSummary"];
export type BuildSummary = Schemas["BuildSummary"];
export type SkillCard = Schemas["SkillCard"];
/** 組裝式技能圖示的資料（Phase 3-17；`SkillCard.icon`、`WorkshopCheck.icon`）。 */
export type SkillIconData = Schemas["SkillIcon"];
export type IconSegment = Schemas["IconSegment"];
/** 技能製造與利用的關鍵字（Phase 3-24b1；`SkillCard.keywords`、`WorkshopCheck.keywords`）。 */
export type SkillKeywords = Schemas["SkillCardKeywords"];
export type KeywordRef = Schemas["KeywordRef"];
export type KeywordHint = Schemas["KeywordHint"];
/** 召喚技能卡可展開的「召喚物資訊」（Phase 3-41a；`SkillCard.summons`）。 */
export type SummonInfoCard = Schemas["SummonInfoCard"];
/** 戰場變奏（Phase 3-25b）：技能卡上的一個型態、技能列目前生效的型態、預覽的型態、工坊的各型態預算。 */
export type SkillVariantCard = Schemas["SkillVariantCard"];
export type VariantState = Schemas["VariantStateOut"];
export type PreviewVariant = Schemas["PreviewVariantOut"];
export type VariantBudgetLine = Schemas["VariantLine"];
export type SkillReasons = Schemas["SkillReasons"];
export type HeroCards = Schemas["HeroCards"];
export type SkillStackRef = Schemas["SkillStackRef"];
/** openapi-typescript 把有預設值的欄位標成必填；建立戰鬥時 `max_rounds` 可省略（伺服器預設 30），
 * 技能工坊的 `custom_skills`、`replace_skills` 也可省略（預設空串列，Phase 3F-1）。 */
export type CreateBattleRequest = Omit<
  Schemas["CreateBattleRequest"],
  "max_rounds" | "custom_skills" | "replace_skills" | "equipment"
> & {
  max_rounds?: number;
  custom_skills?: Record<string, unknown>[];
  replace_skills?: string[];
  /** 裝備測試（Phase 3G-G4）：欄位 → 物品 id 或自訂物品。 */
  equipment?: Record<string, GearChoice>;
};
// 技能工坊（Phase 3F）
export type StepId = Schemas["StepId"];
export type FieldSpec = Schemas["FieldSpec"];
export type FieldType = Schemas["FieldType"];
export type Choice = Schemas["Choice"];
export type StepOptions = Schemas["StepOptions"];
export type DraftOptions = Schemas["DraftOptions"];
export type WorkshopCheck = Schemas["WorkshopCheck"];
export type WorkshopProblem = Schemas["Problem"];
export type BudgetSummary = Schemas["BudgetSummary"];
export type BudgetLine = Schemas["BudgetLine"];
export type WorkshopArena = Schemas["WorkshopArena"];
export type ArenaOpponents = Schemas["ArenaOpponents"];
export type WorkshopRandom = Schemas["WorkshopRandom"];
export type WorkshopRandomRequest = Schemas["WorkshopRandomRequest"];
export type WorkshopExport = Schemas["WorkshopExport"];
export type WorkshopWeapon = Schemas["WorkshopWeapon"];
export type SkillRarity = Schemas["SkillRarity"];
export type Glossary = Schemas["Glossary"];
export type GlossaryEntry = Schemas["GlossaryEntry"];
export type StatusLook = Schemas["StatusLook"];
export type WeaponLookEntry = Schemas["WeaponLookEntry"];
export type WeaponRangeEntry = Schemas["WeaponRangeEntry"];
export type DollLook = Schemas["DollLook"];
/** 玩家自己選的外觀（6R-2，#137；只在畫面）。 */
export type LookChoice = Schemas["LookChoice"];
export type PreviewOut = Schemas["PreviewOut"];
export type PathPreviewOut = Schemas["PathPreviewOut"];
export type PathPreviewRequest = Schemas["PathPreviewRequest"];
export type UseSkill = Schemas["UseSkill-Output"];
export type Direction = Schemas["Direction"];
export type Awaiting = BattleResponse["awaiting"];
export type FollowupTarget = Schemas["FollowupTarget"];
export type FollowupOption = Schemas["FollowupOptionOut"];
export type ChargeOut = Schemas["ChargeOut"];
export type ReactionRuleView = Schemas["ReactionRuleView"];
export type ReactionMode = ReactionRuleView["mode"];
export type SetReactionModeAction = Schemas["SetReactionMode"];
/** 召喚物操控（Phase 3-33c）：切換模式（0 AP）、指揮（1 AP）與指揮時可選的終點和目標。 */
export type SetSummonModeAction = Schemas["SetSummonMode"];
export type CommandSummonAction = Schemas["CommandSummon"];
export type CommandOptions = Schemas["CommandOptionsOut"];
export type CommandOption = Schemas["CommandOptionOut"];
/** 灌注技能（Phase 3-33d）：動作、技能選單與預覽中的灌注範圍。 */
export type InfuseSkillAction = Schemas["InfuseSkill"];
export type InfuseOptions = Schemas["InfuseOptionsOut"];
export type InfuseSkillOption = Schemas["InfuseSkillOptionOut"];
export type InfusionPreview = Schemas["InfusionPreviewOut"];
export type InteractOption = Schemas["InteractOptionOut"];
export type RunOption = Schemas["RunOptionOut"];
export type TelegraphOut = Schemas["TelegraphOut"];
export type TelegraphChange = Schemas["TelegraphChangeOut"];
export type OrderSet = Schemas["OrderSet"];
export type TacticalOrder = Schemas["TacticalOrder"];
export type IgnoredOrder = Schemas["IgnoredOrder"];

/** 所有事件共有的欄位（`text` 只在有中文描述時存在）。 */
export interface EventBase {
  seq: number;
  round: number;
  type: string;
  text?: string;
  [key: string]: unknown;
}

export type MoveMode = "walk" | "forced" | "teleport" | "teleported" | "dash" | "leap" | "swap" | "shadowstep" | "slide";
export type Facing = UnitView["facing"];

export interface UnitMovedEvent extends EventBase {
  type: "unit_moved";
  unit_id: string;
  from_pos: Pos;
  to_pos: Pos;
  mode: MoveMode;
  cost: number;
}

/** `StepOut.events` 的元素 → 窄化的事件（只認得前端需要的型別，其他保持 `EventBase`）。 */
export function asEvent(raw: Record<string, unknown>): EventBase {
  return raw as EventBase;
}

export function isUnitMoved(e: EventBase): e is UnitMovedEvent {
  return e.type === "unit_moved";
}

/** 打中頭目部位（PB-1a 事件；頭目資訊被隱藏時 `hp_before`／`hp_after` 為 null，PB-1c）。 */
export interface PartDamagedEvent extends EventBase {
  type: "part_damaged";
  target_id: string;
  part_id: string;
  name_zh: string;
  amount: number;
  hp_before: number | null;
  hp_after: number | null;
}

/** 頭目部位破了（整場一次；`applied` false＝破的那一下頭目也倒下、不施效果）。 */
export interface PartBrokenEvent extends EventBase {
  type: "part_broken";
  target_id: string;
  part_id: string;
  name_zh: string;
  effects: string[];
  applied?: boolean;
  text_zh?: string | null;
  source_id?: string | null;
}

/** 部位破壞封住了一招。 */
export interface SkillSealedEvent extends EventBase {
  type: "skill_sealed";
  unit_id: string;
  skill_id: string;
  part_id: string;
}

export function isPartDamaged(e: EventBase): e is PartDamagedEvent {
  return e.type === "part_damaged" && typeof e["target_id"] === "string" && typeof e["part_id"] === "string";
}

export function isPartBroken(e: EventBase): e is PartBrokenEvent {
  return e.type === "part_broken" && typeof e["target_id"] === "string" && typeof e["name_zh"] === "string";
}

export function isSkillSealed(e: EventBase): e is SkillSealedEvent {
  return e.type === "skill_sealed" && typeof e["unit_id"] === "string" && typeof e["skill_id"] === "string";
}
// roguelite 一輪（Phase 3-5c-1）
export type RunResponse = Schemas["RunResponse"];
export type RunBattleResponse = Schemas["RunBattleResponse"];
export type RunHero = Schemas["HeroOut"];
export type RunNode = Schemas["NodeOut"];
export type RunOffer = Schemas["OfferOut"];
// 戰後裝備三選一與背包（Phase 3K-2）
export type GearCandidate = Schemas["GearCandidateOut"];
export type GearOffer = Schemas["GearOfferOut"];
export type HeroGearSlot = Schemas["HeroGearSlotOut"];
export type RunPlan = Schemas["BattlePlanOut"];
export type RunRecord = Schemas["BattleRecord"];
export type RunSaveOut = Schemas["SaveOut"];
export type RunSaveSummary = Schemas["SaveSummary"];
export type RunRules = Schemas["RunRules"];
// 新開局（Phase 3-24b2）：起始武器 ＋ 2 個關鍵字；開發者起始包只在 ?dev=1 顯示
export type StartOptions = Schemas["StartOptions"];
export type RaceOption = Schemas["RaceOption"];
export type OriginOption = Schemas["OriginOption"];
export type StartWeaponOption = Schemas["StartWeaponOption"];
export type StartPreview = Schemas["StartPreview"];
export type StartResources = Schemas["StartResourcesOut"];
export type AllocationPreview = Schemas["AllocationPreviewOut"];
export type StartKeywordOption = Schemas["StartKeywordOption"];
export type DevPack = Schemas["DevPackOut"];
export type OfferTag = Schemas["OfferTagOut"];
/** 一輪的 LLM 生成統計（Phase 4-L6b）。 */
export type LlmStats = Schemas["LlmStatsOut"];
// 靈感點與閃現（Phase 3W-5；畫面 3W-6）
export type FlashRules = Schemas["FlashRulesOut"];
export type SkillFlash = Schemas["SkillFlashOut"];
export type PendingFlash = Schemas["PendingFlashOut"];
export type FlashPreview = Schemas["FlashPreviewOut"];
export type FlashOption = Schemas["FlashOptionOut"];
export type FlashCategory = Schemas["FlashCategoryOut"];
export type BattleHistory = Schemas["BattleHistory"];
export type AttributeId = Schemas["Attribute"];
// 建議屬性與「這個屬性影響你的哪些招」（Phase 3H-3）
export type AttributeAffects = Schemas["AttributeAffectsOut"];
export type AttributeSuggestion = Schemas["AttributeSuggestionOut"];
/** 創角時關鍵字與屬性不搭的提示（BAL-19g）。 */
export type RouteHint = Schemas["RouteHintOut"];
/** 起始兩招的觸發關係（#129，6F-4）：「火球製造點燃 → 電爆利用點燃」。 */
export type StartLink = Schemas["StartLinkOut"];
/** `POST /api/runs/{id}/choice` 的請求（工坊另有同名的 `Choice`，所以加前綴）。 */
export type RunChoice =
  | Schemas["LevelUpChoice"]
  | Schemas["CompletePickChoice"]
  | Schemas["LeaveChoice"]
  | Schemas["FlashChoice"]
  | Schemas["FlashPickChoice"]
  | Schemas["DissolveChoice"]
  | Schemas["InheritChoice"]
  | Schemas["RespecAttributesChoice"]
  | Schemas["AllocateChoice"]
  | Schemas["LoadoutChoice"]
  | Schemas["GearPickChoice"]
  | Schemas["EquipChoice"];
/** 開新一輪：`weapon` ＋ `keywords`（一般開局）或 `dev_pack`（開發者起始包）；`attributes` 省略時伺服器把開局點數全部點在武器的縮放屬性。 */
export type CreateRunRequest = Omit<Schemas["CreateRunRequest"], "attributes" | "test_mode" | "test_equipment" | "llm"> & {
  /** LLM 生成開關（4-L6b）：升級技能候選請本機模型提議；省略 ＝ 關閉。連不到模型時伺服器把這一輪當作關閉並在回應提示。 */
  llm?: boolean;
  attributes?: Partial<Record<AttributeId, number>>;
  /** 測試模式（3-39）：戰後 HP、法力回滿；省略 ＝ 正式模式。 */
  test_mode?: boolean;
  /** 測試模式挑的裝備（欄位 → 物品 ID）。 */
  test_equipment?: Record<string, string>;
};
// 裝備測試（Phase 3G-G4）
export type GearCatalog = Schemas["GearCatalog"];
export type GearSlotInfo = Schemas["GearSlotInfo"];
export type GearItemInfo = Schemas["GearItemInfo"];
export type GearAffixInfo = Schemas["GearAffixInfo"];
/** 裝備上的一條詞條（含 `active`／`duplicate_of`，3-32a）。 */
export type AffixLineView = Schemas["AffixLineView"];
export type GearOffhandInfo = Schemas["GearOffhandInfo"];
export type GearWeaponInfo = Schemas["GearWeaponInfo"];
export type GearChoice = Schemas["GearChoice"];
export type GearCustomItem = Schemas["GearCustomItem"];
export type GearCheck = Schemas["GearCheck"];
export type GearCheckRequest = Schemas["GearCheckRequest"];
/** 英雄面板的一行裝備加成（實際值、截斷前的值、每條詞條的貢獻）。 */
export type GearTotalView = Schemas["GearTotalView"];
// 帳號與登入（Phase 5E-1）
export type AuthStatus = Schemas["AuthStatus"];
export type AccountView = Schemas["AccountView"];
export type LoginResponse = Schemas["LoginResponse"];
// 大世界（Phase 5A-5）
export type WorldView = Schemas["WorldView"];
/** 戰鬥短提示（6F-2，#99）與新手指引（#125）。 */
export type BattleHint = Schemas["BattleHintView"];
export type WorldGuide = Schemas["GuideView"];
/** 開場的一句話（RT-5：說書人那句放插圖卡、主城上站著的人那句變成頭上的泡泡）。 */
export type WorldOpeningLine = Schemas["OpeningLineView"];
/** 閃現教學（6F-2，#132）。 */
export type WorldLesson = Schemas["LessonView"];
/** 升級畫面（6F-4 C2）與提示紀錄（6F-4：記在角色身上）。 */
export type WorldLevelUp = Schemas["LevelUpView"];
export type WorldHints = Schemas["HintsStateView"];
/** 實地地圖（Phase 6B-2／6B-3）。 */
export type FieldView = Schemas["FieldView"];
/** 主角（或影子）的紙娃娃外觀（實地地圖、角色清單與 HUD 主角卡的 Q 版頭像，QK-2b）。 */
export type FieldHeroView = Schemas["FieldHeroView"];
/** 實地地圖的靜態地形（6C-R3；依 `hash` 快取）。 */
export type FieldTilesView = Schemas["FieldTilesView"];
export type WorldCharacterView = Schemas["WorldCharacterView"];
export type WorldCharacterSummary = Schemas["WorldCharacterSummary"];
export type WorldLocationView = Schemas["WorldLocationView"];
export type WorldMapView = Schemas["WorldMapView"];
/** 大世界圖（Phase 6D-5）。 */
export type AtlasView = Schemas["AtlasView"];
export type AtlasRegionView = Schemas["AtlasRegionView"];
export type WorldEncounterView = Schemas["EncounterView"];
export type WorldHereView = Schemas["HereView"];
export type WorldBattleResponse = Schemas["WorldBattleResponse"];
export type CreateWorldCharacterRequest = Schemas["CreateWorldCharacterRequest"];
/** TR-1（#134）：主城工坊靶場（未完成開局時 `WorldView.opening`）與沙盒試打。 */
export type RangeView = Schemas["RangeView"];
export type RangeTrialResponse = Schemas["RangeTrialResponse"];
export type RangeRecommendResponse = Schemas["RangeRecommendResponse"];
/** 世界動作（`fight` 走開戰端點）；`hasten` 省略 ＝ 不趕路。 */
export type WorldAction =
  | (Omit<Schemas["TravelAction"], "hasten"> & { hasten?: boolean })
  | Schemas["CampAction"]
  | Schemas["RetreatAction"]
  | Schemas["RestAction"]
  | Schemas["LoadoutAction"]
  | Schemas["TeleportAction"]
  // 5A-7：成長的世界動作
  | Schemas["AllocateAction"]
  | Schemas["RespecAction"]
  | Schemas["FlashAction"]
  | Schemas["FlashPickAction"]
  | Schemas["DissolveAction"]
  | Schemas["InheritAction"]
  | (Omit<Schemas["SwearOathAction"], "source" | "prompt_version" | "player_text"> & { player_text?: string })
  | Schemas["ReleaseOathAction"]
  // 5B-5：任務、三選一、說話、酒館（情境判定與聊天走自己的端點）
  | Schemas["AcceptQuestAction"]
  | (Omit<Schemas["OfferPickAction"], "pick" | "replace"> & { pick?: number | null; replace?: string | null })
  | Schemas["TalkAction"]
  | Schemas["TavernAction"]
  // 5B-5b：放棄、交涉、戰鬥解法
  | (Omit<Schemas["EventSolveAction"], "use_thread"> & { use_thread?: string | null })
  // 5C-1：雇用系統傭兵（整組換掉）；5C-2：借影子、打法、自己影子的預設打法
  | (Omit<Schemas["HireAction"], "shadows" | "ai"> & { shadows?: string[]; ai?: Record<string, string> })
  | (Omit<Schemas["ShadowAiAction"], "profile"> & { profile?: string | null })
  | Schemas["NewsSeenAction"]
  // 6F-4：提示與教學的紀錄（記在角色身上；戰鬥中也能送）
  | (Omit<Schemas["HintSeenAction"], "ids" | "level"> & { ids?: string[]; level?: number | null })
  | (Omit<Schemas["HintsOffAction"], "off"> & { off?: boolean })
  | Schemas["HintsResetAction"]
  // 6R-1（#138）：這一季的免費換種族（在主城）
  | Schemas["ChangeRaceAction"]
  | Schemas["ChangeLookAction"] // 6R-2（#137）主城免費改外觀
  | Schemas["OpeningClassAction"] // OB-5（#150 第 1 點）：選大類的「確定出發」
  | Schemas["OpeningConfirmAction"] // TR-1（#134）主城工坊靶場的「確定出發」
  | Schemas["OpeningReselectAction"] // OB-6（#150 第 5 點）：4 級前的免費重選
  // 5D-1：商店買賣、整理腰包、野外用道具（`count` 省略＝1）
  | (Omit<Schemas["BuyAction"], "count"> & { count?: number })
  | (Omit<Schemas["SellAction"], "count"> & { count?: number })
  | (Omit<Schemas["PouchAction"], "items"> & { items: Record<string, number> })
  | Schemas["UseItemAction"]
  | Schemas["EquipAction"]
  // 5D-2b：背包滿了，戰後結算選要丟哪件
  | (Omit<Schemas["LootChooseAction"], "drop_gear"> & { drop_gear?: string[] })
  // 5D-3：鐵匠（打造、強化、分解）與附魔台（重骰、指定）
  | (Pick<Schemas["CraftAction"], "kind" | "station"> & Partial<Omit<Schemas["CraftAction"], "kind" | "station">>)
  | Schemas["EnhanceAction"]
  | Schemas["RerollAction"]
  | Schemas["ImbueAction"]
  | Schemas["SalvageAction"]
  // 5F-4：影子循環賽的報名與取消
  | (Omit<Schemas["LeagueEnterAction"], "ai"> & { ai?: string | null })
  | Schemas["LeagueWithdrawAction"]
  // 5F-3：挑戰賽季 Boss（扣帳號今天的 1 次，之後照一般遭遇開戰）
  | Schemas["SeasonBossAction"]
  // 6B-2：實地地圖走路、傳送石
  | Schemas["WalkAction"]
  | Schemas["UseTeleportStoneAction"]
  // 6C-5：潛行、點情境物件
  | Schemas["SneakAction"]
  | Schemas["UseFieldObjectAction"];
export type WorldGrowthView = Schemas["GrowthView"];
export type WorldOathView = Schemas["OathView"];
export type WorldOathTemplate = Schemas["OathTemplateView"];
// 大世界事件與任務（Phase 5B-5）
export type WorldEventView = Schemas["EventView"];
export type WorldEventSolution = Schemas["EventSolutionView"];
export type WorldSituationView = Schemas["SituationView"];
export type WorldCiteFact = Schemas["CiteFactView"];
export type WorldSituationResult = Schemas["SituationResultView"];
export type WorldStory = Schemas["StoryView"];
export type WorldNpcHere = Schemas["NpcHereView"];
// NPC 頭像（6C-7；`docs/art/NPC頭像.md`）
export type NpcPortrait = Schemas["NpcPortrait"];
export type FieldFigure = Schemas["FieldFigure"];
export type WorldDialogLine = Schemas["DialogLineView"];
export type WorldQuestLog = Schemas["QuestLogView"];
export type WorldQuestHere = Schemas["QuestHereView"];
export type WorldPendingOffer = Schemas["PendingOfferView"];
export type WorldThread = Schemas["ThreadView"];
export type WorldLlmView = Schemas["WorldLlmView"];
/** 6L-2：LLM 入口的預先生成等待（按閃現、選機遇解法之前）。 */
export type PregenWaitRequest = Schemas["PregenWaitRequest"];
export type PregenWaitOut = Schemas["PregenWaitOut"];
/** 地點留言板（5E-3，#105）：所在地點的留言（最新 20 則）與其他角色的足跡。 */
export type LocationBoard = Schemas["LocationBoard"];
export type NoteView = Schemas["NoteView"];
/** 城鎮公告板（5F-1）：賽季第幾天、今日目標、懸賞板、世界事件全服進度、已清空的地點。 */
export type SeasonBoardView = Schemas["SeasonBoardView"];
export type BoardGoalView = Schemas["BoardGoalView"];
export type BoardBountyView = Schemas["BoardBountyView"];
export type BoardWorldEventView = Schemas["BoardWorldEventView"];
/** 賽季 Boss（5F-3）：封印、鑰匙、帳號今天剩幾次、首殺、評分榜。 */
export type BoardSeasonBossView = Schemas["BoardSeasonBossView"];
export type BoardBossEntryView = Schemas["BoardBossEntryView"];
/** 「你不在的時候」摘要（5F-1b）：上次看過之後的世界事件成敗、懸賞歸屬、新開放的區域。 */
export type AbsenceView = Schemas["AbsenceView"];
export type AbsenceItemView = Schemas["AbsenceItemView"];
/** 影子循環賽（5F-4）：報名、排行榜、場次與重播。 */
export type LeagueView = Schemas["LeagueView"];
export type LeagueStandingView = Schemas["LeagueStandingView"];
export type LeagueMatchView = Schemas["LeagueMatchView"];
export type LeagueReplayResponse = Schemas["LeagueReplayResponse"];
/** 開發用 Boss 戰入口（6F-3）：不回寫世界的一場戰鬥。 */
export type WorldDevBattleResponse = Schemas["WorldDevBattleResponse"];
/** 編年史、上季角色與季末重置（5F-5）。 */
export type ChronicleView = Schemas["ChronicleView"];
export type ChronicleSeasonView = Schemas["ChronicleSeasonView"];
export type LegacyHeroView = Schemas["LegacyHeroView"];
export type SeasonResetRequest = Schemas["SeasonResetRequest"];
export type SeasonResetReport = Schemas["SeasonResetReport"];
export type ResetLine = Schemas["ResetLine"];
// 隊伍與系統傭兵（Phase 5C-1）
export type WorldPartyView = Schemas["PartyView"];
export type WorldPartyMember = Schemas["PartyMemberView"];
export type WorldMercenary = Schemas["MercenaryView"];
// 朋友的影子（Phase 5C-2）
export type WorldShadow = Schemas["ShadowView"];
export type WorldAiChoice = Schemas["AiChoiceView"];
export type WorldMyShadow = Schemas["MyShadowView"];
// 貨幣、背包、腰包與商店（Phase 5D-1）
export type WorldWallet = Schemas["WalletView"];
export type WorldInventory = Schemas["InventoryView"];
export type WorldBagItem = Schemas["BagItemView"];
// 郵寄（Phase 6T-1a 伺服器、6T-1b 面板）
export type MailView = Schemas["MailView"];
export type MailLetter = Schemas["LetterView"];
export type MailLetterItem = Schemas["LetterItemView"];
export type MailRecipient = Schemas["MailRecipientView"];
export type MailQuote = Schemas["MailQuoteView"];
export type MailSend = Schemas["MailSendAction"];
export type MailActionResponse = Schemas["MailActionResponse"];
export type MailBadge = Schemas["MailBadgeView"];
export type MailPostman = Schemas["PostmanView"];
export type WorldShop = Schemas["ShopView"];
export type WorldShopItem = Schemas["ShopItemView"];
export type WorldPendingLoot = Schemas["PendingLootView"];
// 鐵匠與附魔台（Phase 5D-3）
export type WorldCrafting = Schemas["CraftingView"];
export type WorldCraftGear = Schemas["CraftGearView"];
export type WorldCraftMaterial = Schemas["CraftMaterialView"];
export type WorldRecipe = Schemas["RecipeView"];
// 數值工坊（Phase NW-1a 後端、NW-1b 畫面；前綴 /api/tuning，只在 dev_mode 且 TRPG_TUNING=1 時存在）
export type TuningStatus = Schemas["TuningStatus"];
export type TuningObjectSummary = Schemas["TuningObjectSummary"];
export type TuningObjectDetail = Schemas["TuningObjectDetail"];
export type TuningFieldView = Schemas["TuningFieldView"];
export type TuningChangeIn = Schemas["TuningChangeIn"];
export type TuningChangeView = Schemas["TuningChangeView"];
export type TuningDraftView = Schemas["TuningDraftView"];
export type TuningCheckResult = Schemas["TuningCheckResult"];
export type TuningFieldError = Schemas["TuningFieldError"];
export type TuningDiff = Schemas["TuningDiff"];
export type TuningDiffRow = Schemas["TuningDiffRow"];
export type TuningApplyResult = Schemas["TuningApplyResult"];
export type TuningHistoryEntry = Schemas["TuningHistoryEntry"];
export type TuningSimOptions = Schemas["TuningSimOptions"];
export type TuningSimRequest = Schemas["TuningSimRequest"];
export type TuningSimJob = Schemas["TuningSimJob"];
export type TuningSimResult = Schemas["TuningSimResult"];
export type TuningSimSide = Schemas["TuningSimSide"];
export type TuningSimPhase = Schemas["TuningSimPhase"];
