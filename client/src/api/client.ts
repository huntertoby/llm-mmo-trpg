// fetch 包裝：所有請求走相對路徑 /api（開發時由 Vite proxy 轉到 127.0.0.1:8000）。
import type {
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
  RunBattleResponse,
  RunChoice,
  RunResponse,
  RunRules,
  RunSaveOut,
  RunSaveSummary,
  SkillCard,
  SkillReasons,
  StartOptions,
  StartPreview,
  StartResources,
  AllocationPreview,
  UseSkill,
  WorkshopArena,
  WorkshopCheck,
  WorkshopExport,
  WorkshopRandom,
  WorkshopRandomRequest,
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

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
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
  if (!res.ok) throw new ApiError(res.status, detailText(res.status, data));
  return data as T;
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
  /** 設定我方隊友的戰術指令（空集合 ＝ 取消）；不推進戰鬥，`steps` 為空。 */
  setOrders: (id: string, orders: OrderSet) =>
    request<BattleResponse>("PUT", `/battles/${id}/orders`, orders),
  /** 回答暫停中的結算：反應詢問（`accept`），或複製技能的選目標（`copyCast` 為選取，`accept: false` 放棄）。 */
  /** 技能工坊（Phase 3F-1）：skill 是組到一半（或完整）的技能定義。 */
  workshopArena: () => request<WorkshopArena>("GET", "/workshop/arena"),
  /** `weapon`（選填）：主角目前手上武器的 ID，武器技的縮放屬性會顯示手上武器（Phase 3-48b）。 */
  workshopOptions: (skill: Record<string, unknown>, weapon?: string) =>
    request<DraftOptions>("POST", "/workshop/options", weapon === undefined ? { skill } : { skill, weapon }),
  workshopCheck: (skill: Record<string, unknown>) =>
    request<WorkshopCheck>("POST", "/workshop/check", { skill }),
  workshopRandom: (body: WorkshopRandomRequest) =>
    request<WorkshopRandom>("POST", "/workshop/random", body),
  /** 匯出 YAML；`allowIllegal`（開發者模式）才能匯出不合法的技能。 */
  workshopExport: (skill: Record<string, unknown>, allowIllegal = false) =>
    request<WorkshopExport>("POST", "/workshop/export", { skill, allow_illegal: allowIllegal }),
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
  runSaves: () => request<RunSaveSummary[]>("GET", "/runs/saves"),
  loadRun: (runId: string) => request<RunResponse>("POST", "/runs/load", { run_id: runId }),
  run: (runId: string) => request<RunResponse>("GET", `/runs/${encodeURIComponent(runId)}`),
  runBattle: (runId: string) =>
    request<RunBattleResponse>("POST", `/runs/${encodeURIComponent(runId)}/battle`),
  runChoice: (runId: string, choice: RunChoice) =>
    request<RunResponse>("POST", `/runs/${encodeURIComponent(runId)}/choice`, choice),
  saveRun: (runId: string) =>
    request<RunSaveOut>("POST", `/runs/${encodeURIComponent(runId)}/save`),
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
