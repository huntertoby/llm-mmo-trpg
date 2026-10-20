// fetch 包裝：所有請求走相對路徑 /api（開發時由 Vite proxy 轉到 127.0.0.1:8000）。
import type {
  Action,
  BattleResponse,
  BuildSummary,
  CreateBattleRequest,
  DraftOptions,
  FollowupTarget,
  Glossary,
  MapSummary,
  OrderSet,
  PreviewOut,
  SkillReasons,
  SkillCard,
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
  glossary: () => request<Glossary>("GET", "/glossary"),
  createBattle: (body: CreateBattleRequest) => request<BattleResponse>("POST", "/battles", body),
  battle: (id: string) => request<BattleResponse>("GET", `/battles/${id}`),
  act: (id: string, action: Action) => request<BattleResponse>("POST", `/battles/${id}/actions`, action),
  preview: (id: string, action: Action) =>
    request<PreviewOut>("POST", `/battles/${id}/preview`, action),
  /** 設定我方隊友的戰術指令（空集合 ＝ 取消）；不推進戰鬥，`steps` 為空。 */
  setOrders: (id: string, orders: OrderSet) =>
    request<BattleResponse>("PUT", `/battles/${id}/orders`, orders),
  /** 回答暫停中的結算：反應詢問（`accept`），或複製技能的選目標（`copyCast` 為選取，`accept: false` 放棄）。 */
  /** 技能工坊（Phase 3F-1）：skill 是組到一半（或完整）的技能定義。 */
  workshopArena: () => request<WorkshopArena>("GET", "/workshop/arena"),
  workshopOptions: (skill: Record<string, unknown>) =>
    request<DraftOptions>("POST", "/workshop/options", { skill }),
  workshopCheck: (skill: Record<string, unknown>) =>
    request<WorkshopCheck>("POST", "/workshop/check", { skill }),
  workshopRandom: (body: WorkshopRandomRequest) =>
    request<WorkshopRandom>("POST", "/workshop/random", body),
  workshopExport: (skill: Record<string, unknown>) =>
    request<WorkshopExport>("POST", "/workshop/export", { skill }),
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
