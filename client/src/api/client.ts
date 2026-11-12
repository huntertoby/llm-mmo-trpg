// fetch 包裝：所有請求走相對路徑 /api（開發時由 Vite proxy 轉到 127.0.0.1:8000）。
// 5E-1：登入後每個請求帶 `Authorization: Bearer <token>`；收到 401 時清掉 token 並發出 AUTH_EXPIRED_EVENT。
import { AUTH_EXPIRED_EVENT, authHeaders, needsLogin, readToken, writeToken } from "../auth/auth";
import { hydrateField } from "../world/fieldTiles";
import type {
  AuthStatus,
  LoginResponse,
  Action,
  BattleHistory,
  BattleResponse,
  BuildSummary,
  CommandOptions,
  CreateBattleRequest,
  CreateRunRequest,
  DevPack,
  DraftOptions,
  FollowupTarget,
  GearCatalog,
  GearCheck,
  GearCheckRequest,
  Glossary,
  InfuseOptions,
  MapSummary,
  OrderSet,
  HeroCards,
  PreviewOut,
  PathPreviewOut,
  PathPreviewRequest,
  RunBattleResponse,
  RunChoice,
  RunResponse,
  RunRules,
  RangeRecommendResponse,
  RangeTrialResponse,
  RunSaveOut,
  RunSaveSummary,
  SkillCard,
  SkillReasons,
  StartOptions,
  StartPreview,
  StartResources,
  AllocationPreview,
  FlashPreview,
  UseSkill,
  WorkshopArena,
  WorkshopCheck,
  WorkshopExport,
  WorkshopWeapon,
  WorkshopRandom,
  WorkshopRandomRequest,
  CreateWorldCharacterRequest,
  WorldAction,
  WorldBattleResponse,
  WorldCharacterSummary,
  WorldLlmView,
  PregenWaitRequest,
  PregenWaitOut,
  LeagueReplayResponse,
  WorldDevBattleResponse,
  LeagueView,
  LocationBoard,
  SeasonBoardView,
  AbsenceView,
  ChronicleView,
  LegacyHeroView,
  SeasonResetRequest,
  SeasonResetReport,
  WorldView,
  FieldTilesView,
  TuningApplyIn,
  TuningApplyResult,
  TuningBudgetResult,
  TuningChangeIn,
  TuningCheckResult,
  TuningDiff,
  TuningDraftView,
  TuningGroupIn,
  TuningGroupPreset,
  TuningGroupPreview,
  TuningHistoryEntry,
  TuningLadders,
  TuningRatioBaseline,
  TuningRatioPlan,
  TuningRatioPlanIn,
  TuningSkillRatio,
  TuningObjectDetail,
  TuningObjectSummary,
  TuningSimJob,
  TuningSimOptions,
  TuningSimRequest,
  TuningStatus,
  MailActionResponse,
  MailQuote,
  MailRecipient,
  MailSend,
  MailView,
} from "./types";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

/** 錯誤回應的 `detail` → 一行中文訊息（pydantic 驗證錯誤的 `detail` 是列表）。 */
export function detailText(status: number, body: unknown): string {
  if (body !== null && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d !== null && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
        .join("；");
    }
  }
  return `伺服器錯誤（HTTP ${status}）`;
}

/** `quiet`：背景請求（首頁的存檔列表）收到 401 不導到登入畫面（5D-R2）。 */
async function request<T>(method: string, path: string, body?: unknown, quiet = false): Promise<T> {
  const token = readToken();
  const init: RequestInit = { method, headers: authHeaders(token) };
  if (body !== undefined) {
    init.headers = { ...authHeaders(token), "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(0, "無法連線到伺服器（請確認 `trpg serve` 正在執行）");
  }
  const text = await res.text();
  let data: unknown = null;
  if (text !== "") {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!quiet && needsLogin(res.status, path)) {
    // 5D-R2：沒帶 token 的 401（開發模式關、還沒登入）也導到登入畫面
    if (token !== null) writeToken(null);
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  if (!res.ok) throw new ApiError(res.status, detailText(res.status, data));
  return data as T;
}

/** 實地地圖的靜態地形（6C-R3；`fieldTiles.ts` 依雜湊快取）。6D-R1：經角色取（只給看得到的圖）。 */
const fetchFieldTiles = (characterId: string, mapId: string, hash: string) =>
  request<FieldTilesView>(
    "GET",
    `/world/characters/${encodeURIComponent(characterId)}/fields/${encodeURIComponent(mapId)}?h=${encodeURIComponent(hash)}`,
  );

/** 取不到靜態地形時的退路：請伺服器直接帶地形（6D-R1）。 */
const fetchWorldWithTiles = (characterId: string) =>
  request<WorldView>("GET", `/world/characters/${encodeURIComponent(characterId)}?with_tiles=1`);

/** 世界畫面補上地形（6C-R3）。 */
const hydrate = (view: WorldView) => hydrateField(view, fetchFieldTiles, fetchWorldWithTiles);

/** 回傳世界畫面的請求：`field` 沒帶地形時補上（6C-R3）。 */
async function worldRequest(method: string, path: string, body?: unknown): Promise<WorldView> {
  return hydrate(await request<WorldView>(method, path, body));
}

/** 開發用 Boss 戰入口的其他查詢參數（QK-9b）。 */
export interface DevBattleMore {
  region?: string;
  facing?: string;
  opening?: string;
}

/** `DevBattleMore` → 查詢字串（沒給的不帶；順序固定）。 */
export function devMoreQuery(more: DevBattleMore): string {
  return (["region", "facing", "opening"] as const)
    .filter((k) => more[k] !== undefined && more[k] !== "")
    .map((k) => `&${k}=${encodeURIComponent(more[k]!)}`)
    .join("");
}

export const api = {
  maps: () => request<MapSummary[]>("GET", "/maps"),
  builds: () => request<BuildSummary[]>("GET", "/builds"),
  /** 技能卡片；帶 `battleId` 時也查該場戰鬥內的自訂技能（工坊試玩、一輪生成技能）。 */
  skill: (id: string, battleId?: string) =>
    request<SkillCard>(
      "GET",
      `/skills/${encodeURIComponent(id)}${battleId === undefined ? "" : `?battle_id=${encodeURIComponent(battleId)}`}`,
    ),
  /** 主角灰掉的技能 → 引擎的拒絕理由（Phase 3-5c-2）。 */
  skillReasons: (battleId: string) => request<SkillReasons>("GET", `/battles/${battleId}/skill-reasons`),
  /** 主角的技能卡（附施放者當下的實際值：傷害算法的目前加成、召喚物資訊；Phase 3-41c）。 */
  heroCards: (battleId: string) => request<HeroCards>("GET", `/battles/${battleId}/hero-cards`),
  /** 指揮主角的一隻召喚物時可選的終點與目標（Phase 3-33c）。 */
  commandOptions: (battleId: string, summonId: string) =>
    request<CommandOptions>("GET", `/battles/${battleId}/summons/${encodeURIComponent(summonId)}/command-options`),
  /** 灌注技能給主角的一隻召喚物時的技能選單（不能灌注的附中文原因；Phase 3-33d）。 */
  infuseOptions: (battleId: string, summonId: string) =>
    request<InfuseOptions>("GET", `/battles/${battleId}/summons/${encodeURIComponent(summonId)}/infuse-options`),
  glossary: () => request<Glossary>("GET", "/glossary"),
  createBattle: (body: CreateBattleRequest) => request<BattleResponse>("POST", "/battles", body),
  battle: (id: string) => request<BattleResponse>("GET", `/battles/${id}`),
  /** 到目前為止戰鬥發生過的事件（重新整理或讀檔回到戰鬥時還原戰鬥紀錄；Phase 3-6）。 */
  battleHistory: (id: string) => request<BattleHistory>("GET", `/battles/${id}/history`),
  act: (id: string, action: Action) => request<BattleResponse>("POST", `/battles/${id}/actions`, action),
  preview: (id: string, action: Action) =>
    request<PreviewOut>("POST", `/battles/${id}/preview`, action),
  /** 選移動時的路徑預覽（6A-4b）：每格的表面、陷阱、預估事件與停點；不擲骰、不改狀態。 */
  pathPreview: (id: string, body: PathPreviewRequest) =>
    request<PathPreviewOut>("POST", `/battles/${id}/path-preview`, body),
  /** 設定我方隊友的戰術指令（空集合 ＝ 取消）；不推進戰鬥，`steps` 為空。 */
  setOrders: (id: string, orders: OrderSet) =>
    request<BattleResponse>("PUT", `/battles/${id}/orders`, orders),
  /** 回答暫停中的結算：反應詢問（`accept`），或複製技能的選目標（`copyCast` 為選取，`accept: false` 放棄）。 */
  /** 技能工坊（Phase 3F-1）：skill 是組到一半（或完整）的技能定義。 */
  workshopArena: () => request<WorkshopArena>("GET", "/workshop/arena"),
  /** `weapon`（選填）：主角目前手上武器的 ID，武器技的縮放屬性會顯示手上武器（Phase 3-48b）。 */
  workshopWeapons: () => request<WorkshopWeapon[]>("GET", "/workshop/weapons"),
  workshopOptions: (skill: Record<string, unknown>, weapon?: string) =>
    request<DraftOptions>("POST", "/workshop/options", weapon === undefined ? { skill } : { skill, weapon }),
  workshopCheck: (skill: Record<string, unknown>, weapon?: string) =>
    request<WorkshopCheck>("POST", "/workshop/check", weapon === undefined ? { skill } : { skill, weapon }),
  workshopRandom: (body: WorkshopRandomRequest) =>
    request<WorkshopRandom>("POST", "/workshop/random", body),
  /** 匯出 YAML；`allowIllegal`（開發者模式）才能匯出不合法的技能。 */
  workshopExport: (skill: Record<string, unknown>, allowIllegal = false) =>
    request<WorkshopExport>("POST", "/workshop/export", { skill, allow_illegal: allowIllegal }),
  /** 數值工坊（Phase NW-1b；端點 NW-1a，前綴 /api/tuning）。沒開開關時端點不存在（404）。 */
  tuningStatus: () => request<TuningStatus>("GET", "/tuning/status", undefined, true),
  tuningObjects: (kind: "unit" | "skill" | "ai" = "unit") => request<TuningObjectSummary[]>("GET", `/tuning/objects?kind=${kind}`),
  tuningObject: (kind: string, id: string) =>
    request<TuningObjectDetail>("GET", `/tuning/objects/${encodeURIComponent(kind)}/${encodeURIComponent(id)}`),
  tuningDraft: (name: string) => request<TuningDraftView>("GET", `/tuning/drafts/${encodeURIComponent(name)}`),
  tuningPutDraft: (name: string, changes: TuningChangeIn[]) =>
    request<TuningDraftView>("PUT", `/tuning/drafts/${encodeURIComponent(name)}`, { changes }),
  tuningDeleteDraft: (name: string) => request<null>("DELETE", `/tuning/drafts/${encodeURIComponent(name)}`),
  /** 驗證；給了 `changes` 就驗它（不必先存）。 */
  tuningCheck: (name: string, changes?: TuningChangeIn[]) =>
    request<TuningCheckResult>("POST", `/tuning/drafts/${encodeURIComponent(name)}/check`, changes === undefined ? undefined : { changes }),
  tuningDiff: (name: string) => request<TuningDiff>("GET", `/tuning/drafts/${encodeURIComponent(name)}/diff`),
  tuningApply: (name: string, confirm?: TuningApplyIn) =>
    request<TuningApplyResult>("POST", `/tuning/drafts/${encodeURIComponent(name)}/apply`, confirm),
  /** NW-2b：技能的即時預算、分組預覽、常用預設組、骰子與倍率階梯（端點 NW-2a）。 */
  tuningBudget: (skillId: string, changes: TuningChangeIn[]) =>
    request<TuningBudgetResult>("POST", `/tuning/skills/${encodeURIComponent(skillId)}/budget`, { changes }),
  tuningGroupPreview: (body: TuningGroupIn) => request<TuningGroupPreview>("POST", "/tuning/skills/group-preview", body),
  tuningPresets: () => request<TuningGroupPreset[]>("GET", "/tuning/skills/presets"),
  tuningLadders: () => request<TuningLadders>("GET", "/tuning/skills/ladders"),
  /** NW-2c：1 階比值（技能表單的比值區、比值工作的規模、匯入基準）。 */
  tuningSkillRatio: (skillId: string) => request<TuningSkillRatio>("GET", `/tuning/skills/${encodeURIComponent(skillId)}/ratio`),
  tuningRatioPlan: (body: TuningRatioPlanIn) => request<TuningRatioPlan>("POST", "/tuning/skills/ratio-plan", body),
  tuningRatioBaseline: () => request<TuningRatioBaseline | null>("GET", "/tuning/skills/ratio-baseline"),
  tuningImportRatioBaseline: (data: unknown) => request<TuningRatioBaseline>("POST", "/tuning/skills/ratio-baseline", data),
  tuningRevert: (name: string, commit: string) =>
    request<TuningDraftView>("POST", `/tuning/drafts/${encodeURIComponent(name)}/revert/${encodeURIComponent(commit)}`),
  tuningHistory: () => request<TuningHistoryEntry[]>("GET", "/tuning/history?limit=20"),
  tuningSimOptions: () => request<TuningSimOptions>("GET", "/tuning/sims/options"),
  tuningStartSim: (body: TuningSimRequest) => request<TuningSimJob>("POST", "/tuning/sims", body),
  tuningSim: (jobId: string) => request<TuningSimJob>("GET", `/tuning/sims/${encodeURIComponent(jobId)}`),
  tuningCancelSim: (jobId: string) => request<TuningSimJob>("DELETE", `/tuning/sims/${encodeURIComponent(jobId)}`),
  /** 裝備測試（Phase 3G-G4）：選單與穿戴檢查。 */
  gearCatalog: () => request<GearCatalog>("GET", "/gear/catalog"),
  gearCheck: (body: GearCheckRequest) => request<GearCheck>("POST", "/gear/check", body),
  /** roguelite 一輪（Phase 3-5c-1）。 */
  createRun: (body: CreateRunRequest) => request<RunResponse>("POST", "/runs", body),
  /** 開局規則（配點數）；Phase 3-6。 */
  runRules: () => request<RunRules>("GET", "/runs/rules"),
  /** 新開局（Phase 3-24b2）：可選的武器與關鍵字、各關鍵字的起始技能預覽、開發者起始包。 */
  startOptions: () => request<StartOptions>("GET", "/runs/start-options"),
  startPreview: (weapon: string, seed: number, keywords: string[]) =>
    request<StartPreview>("POST", "/runs/start-preview", { weapon, seed, keywords }),
  /** 開局畫面的資源預覽（Phase 3-41c）：選了武器、配了點之後的最大 HP、法力、耐力（後端算）。 */
  startResources: (weapon: string, attributes: Record<string, number>) =>
    request<StartResources>("POST", "/runs/start-resources", { weapon, attributes }),
  /** 升級配點與營火重配的資源預覽（Phase 3H-5）：配點後的最大 HP、法力、耐力變化（後端算）。 */
  allocationPreview: (runId: string, attributes: Record<string, number>) =>
    request<AllocationPreview>("POST", `/runs/${encodeURIComponent(runId)}/allocation-preview`, { attributes }),
  devPacks: () => request<DevPack[]>("GET", "/runs/dev-packs"),
  /** 開發用（3U-3）：AI 代打到指定的戰後畫面；伺服器要帶 `TRPG_DEV_ROUTES=1`，否則 404。 */
  devAdvance: (runId: string, to: string, insight = 0) =>
    request<RunResponse>("POST", `/runs/${encodeURIComponent(runId)}/dev-advance?to=${encodeURIComponent(to)}${insight > 0 ? `&insight=${insight}` : ""}`),
  runSaves: () => request<RunSaveSummary[]>("GET", "/runs/saves", undefined, true),
  loadRun: (runId: string) => request<RunResponse>("POST", "/runs/load", { run_id: runId }),
  run: (runId: string) => request<RunResponse>("GET", `/runs/${encodeURIComponent(runId)}`),
  runBattle: (runId: string) =>
    request<RunBattleResponse>("POST", `/runs/${encodeURIComponent(runId)}/battle`),
  /** 閃現或重閃之前的預覽（3W-5）：能不能閃、價格、每類合法變化數量；不扣點。 */
  flashPreview: (runId: string, skill: string, slot: number | null) =>
    request<FlashPreview>("POST", `/runs/${encodeURIComponent(runId)}/flash-preview`, { skill, slot }),
  runChoice: (runId: string, choice: RunChoice) =>
    request<RunResponse>("POST", `/runs/${encodeURIComponent(runId)}/choice`, choice),
  saveRun: (runId: string) =>
    request<RunSaveOut>("POST", `/runs/${encodeURIComponent(runId)}/save`),
  /** 大世界（Phase 5A-5）：角色列表、建立、地點圖畫面、世界動作、開戰。 */
  /** 帳號與登入（5E-1）：開發模式與目前 token 的帳號。 */
  authStatus: () => request<AuthStatus>("GET", "/auth/status"),
  login: (username: string, password: string) => request<LoginResponse>("POST", "/auth/login", { username, password }),
  logout: () => request<null>("POST", "/auth/logout"),
  worldCharacters: () => request<WorldCharacterSummary[]>("GET", "/world/characters"),
  /** 首頁「繼續」用的背景讀取（UI-E1b）：同一個端點，收到 401 不導到登入畫面。 */
  worldCharactersQuiet: () => request<WorldCharacterSummary[]>("GET", "/world/characters", undefined, true),
  createWorldCharacter: (body: CreateWorldCharacterRequest) => worldRequest("POST", "/world/characters", body),
  world: (characterId: string) => worldRequest("GET", `/world/characters/${encodeURIComponent(characterId)}`),
  worldAct: (characterId: string, action: WorldAction) =>
    worldRequest("POST", `/world/characters/${encodeURIComponent(characterId)}/actions`, action),
  /** TR-1（#134）：主城工坊靶場的沙盒試打（不寫世界日誌、不回寫角色；`keywords` 空＝示範招）。 */
  worldRangeTrial: (characterId: string, weapon: string, keywords: string[]) =>
    request<RangeTrialResponse>("POST", `/world/characters/${encodeURIComponent(characterId)}/range/trial`, { weapon, keywords }),
  /** PR-2（#147）：主城工坊師傅的「靶場試玩」——自己的技能與裝備打木樁（測試模式沙盒；不能開時 422，原因＝師傅選單上那句）。 */
  worldRangePractice: (characterId: string) =>
    request<RangeTrialResponse>("POST", `/world/characters/${encodeURIComponent(characterId)}/range/practice`),
  /** PR-2：離開靶場時刪掉這個角色目前的試打（開局試打或靶場試玩；沒有也成功）。 */
  worldRangeTrialClose: (characterId: string) =>
    request<null>("DELETE", `/world/characters/${encodeURIComponent(characterId)}/range/trial`),
  /** OB-3／OB-5（#150 第 4 點）：照玩家當下選的那把武器查推薦的關鍵字（0～2 個；不能選定也不能重選時 422）。 */
  worldRangeRecommend: (characterId: string, weapon: string) =>
    request<RangeRecommendResponse>("GET", `/world/characters/${encodeURIComponent(characterId)}/range/recommend?weapon=${encodeURIComponent(weapon)}`),
  worldBattle: (characterId: string) =>
    request<WorldBattleResponse>("POST", `/world/characters/${encodeURIComponent(characterId)}/battle`).then(
      async (r) => ({ ...r, world: await hydrate(r.world) }),
    ),
  /** 大世界的閃現與配點預覽（5A-7；同一輪的預覽，不扣點）。 */
  worldFlashPreview: (characterId: string, skill: string, slot: number | null) =>
    request<FlashPreview>("POST", `/world/characters/${encodeURIComponent(characterId)}/flash-preview`, { skill, slot }),
  worldAllocationPreview: (characterId: string, attributes: Record<string, number>) =>
    request<AllocationPreview>("POST", `/world/characters/${encodeURIComponent(characterId)}/allocation-preview`, { attributes }),
  /** 大世界事件（5B-5）：打開情境判定、送出回答（第一次送出即定案；文字是純資料，後端包進 <player_input>）、和 NPC 聊天。 */
  worldSituation: (characterId: string, template: string) =>
    worldRequest("POST", `/world/characters/${encodeURIComponent(characterId)}/situation`, { template }),
  worldAnswer: (characterId: string, template: string, text: string, cite: string[]) =>
    worldRequest("POST", `/world/characters/${encodeURIComponent(characterId)}/situation/answer`, { template, text, cite }),
  worldChat: (characterId: string, npc: string, text: string) =>
    worldRequest("POST", `/world/characters/${encodeURIComponent(characterId)}/chat`, { npc, text }),
  /** 大世界自己的 LLM 開關（預設跟著伺服器設定；`null` 回到預設）。 */
  worldLlm: () => request<WorldLlmView>("GET", "/world/llm"),
  /** 6L-2：LLM 的版本好了沒（伺服器最多等 10 秒；前端顯示等待提示、可取消＝不送動作）。 */
  worldPregenWait: (characterId: string, body: PregenWaitRequest) =>
    request<PregenWaitOut>("POST", `/world/characters/${encodeURIComponent(characterId)}/pregen/wait`, body),
  setWorldLlm: (enabled: boolean | null) => request<WorldLlmView>("POST", "/world/llm", { enabled }),
  /** 地點留言與足跡（5E-3，#105）：留言是純資料，不送進 LLM。 */
  worldNotes: (characterId: string) =>
    request<LocationBoard>("GET", `/world/characters/${encodeURIComponent(characterId)}/notes`),
  postWorldNote: (characterId: string, text: string) =>
    request<LocationBoard>("POST", `/world/characters/${encodeURIComponent(characterId)}/notes`, { text }),
  /** 作者刪自己的留言（5E-3b）；回更新後的留言板。 */
  deleteOwnWorldNote: (characterId: string, noteId: string) =>
    request<LocationBoard>(
      "DELETE",
      `/world/characters/${encodeURIComponent(characterId)}/notes/${encodeURIComponent(noteId)}`,
    ),
  /** 郵寄（6T-1b 面板；伺服器 6T-1a）：面板、寄給誰、寄件前檢查（不寫日誌）、寄出、領取、退回寄件人。 */
  worldMail: (characterId: string) => request<MailView>("GET", `/world/characters/${encodeURIComponent(characterId)}/mail`),
  mailRecipients: (characterId: string) =>
    request<MailRecipient[]>("GET", `/world/characters/${encodeURIComponent(characterId)}/mail/recipients`),
  mailQuote: (characterId: string, body: MailSend) =>
    request<MailQuote>("POST", `/world/characters/${encodeURIComponent(characterId)}/mail/quote`, body),
  mailSend: (characterId: string, body: MailSend) =>
    request<MailActionResponse>("POST", `/world/characters/${encodeURIComponent(characterId)}/mail/send`, body),
  mailClaim: (characterId: string, letter: string) =>
    request<MailActionResponse>("POST", `/world/characters/${encodeURIComponent(characterId)}/mail/${encodeURIComponent(letter)}/claim`),
  mailRefuse: (characterId: string, letter: string) =>
    request<MailActionResponse>("POST", `/world/characters/${encodeURIComponent(characterId)}/mail/${encodeURIComponent(letter)}/refuse`),
  /** 城鎮公告板（5F-1）：只讀，後端用換日後的世界算。 */
  worldBoard: (characterId: string) =>
    request<SeasonBoardView>("GET", `/world/characters/${encodeURIComponent(characterId)}/board`),
  /** 「你不在的時候」摘要（5F-1b）：只讀；看過送 `news_seen` 動作（`until` ＝ `as_of`）。 */
  worldAbsence: (characterId: string) =>
    request<AbsenceView>("GET", `/world/characters/${encodeURIComponent(characterId)}/absence`),
  /** 影子循環賽（5F-4）：報名狀態、排行榜、場次（5F-4b 分頁，`page` 從 1 起）。 */
  worldLeague: (characterId: string, page = 1) =>
    request<LeagueView>("GET", `/world/characters/${encodeURIComponent(characterId)}/league?page=${page}`),
  /** 某一場循環賽的重播（從開場播到結束；既有戰鬥畫面）。 */
  /** 開發用（6F-3；`?dev=1`，伺服器另要 `TRPG_DEV_ROUTES=1`）：Boss 戰直接開打，不回寫世界。
   * QK-9b：`more` 帶 `region`（地點在別區）、`facing`（主角開場朝向）、`opening`（`summon`／`form`：開場就放出召喚物／變身）。 */
  worldDevBoss: (characterId: string, location = "cloud_summit", level?: number, aiUntil?: string, more: DevBattleMore = {}) =>
    request<WorldDevBattleResponse>(
      "POST",
      `/world/characters/${encodeURIComponent(characterId)}/dev-boss?location=${encodeURIComponent(location)}${level === undefined ? "" : `&level=${level}`}${aiUntil === undefined ? "" : `&ai_until=${encodeURIComponent(aiUntil)}`}${devMoreQuery(more)}`,
    ),
  /** 開發用（QK-9b；`?dev=1`，伺服器另要 `TRPG_DEV_ROUTES=1`）：角色直接搬到某區的城鎮（會改角色存檔、不寫世界日誌）。 */
  worldDevTeleport: (characterId: string, region: string) =>
    worldRequest("POST", `/world/characters/${encodeURIComponent(characterId)}/dev-teleport?region=${encodeURIComponent(region)}`),
  worldLeagueReplay: (characterId: string, matchId: string) =>
    request<LeagueReplayResponse>(
      "POST",
      `/world/characters/${encodeURIComponent(characterId)}/league/matches/${encodeURIComponent(matchId)}/replay`,
    ),
  /** 編年史（5F-5）：每季的季末紀錄、首位發現的配方、循環賽排名、首殺與評分榜；所有人可看。 */
  worldChronicle: () => request<ChronicleView>("GET", "/world/chronicle"),
  /** 自己帳號上季的角色（5F-5；建角時沿用名字與外觀）。 */
  worldLegacy: () => request<LegacyHeroView[]>("GET", "/world/legacy"),
  /** 季末重置（5F-5，管理者）：預設 dry-run；真的執行要帶 `confirm_season`。 */
  seasonReset: (body: SeasonResetRequest) => request<SeasonResetReport>("POST", "/world/season/reset", body),
  /** 管理者刪任何一則留言（5E-3；回 204）。 */
  adminDeleteWorldNote: (noteId: string) => request<null>("DELETE", `/world/notes/${encodeURIComponent(noteId)}`),
  decide: (
    id: string,
    accept: boolean,
    copyCast: UseSkill | null = null,
    followupTarget: FollowupTarget | null = null,
  ) =>
    request<BattleResponse>("POST", `/battles/${id}/decision`, {
      accept,
      copy_cast: copyCast,
      followup_target: followupTarget,
    }),
};

/** 戰鬥紀錄的下載網址（`trpg battle --log-json` 同格式，可用 `trpg battle replay` 重播）。 */
export function logUrl(battleId: string): string {
  return `/api/battles/${battleId}/log`;
}
