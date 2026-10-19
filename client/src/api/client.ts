// fetch 包裝：所有請求走相對路徑 /api（開發時由 Vite proxy 轉到 127.0.0.1:8000）。
import type {
  Action,
  BattleResponse,
  BuildSummary,
  CreateBattleRequest,
  Glossary,
  MapSummary,
  OrderSet,
  PreviewOut,
  SkillCard,
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
  skill: (id: string) => request<SkillCard>("GET", `/skills/${encodeURIComponent(id)}`),
  glossary: () => request<Glossary>("GET", "/glossary"),
  createBattle: (body: CreateBattleRequest) => request<BattleResponse>("POST", "/battles", body),
  battle: (id: string) => request<BattleResponse>("GET", `/battles/${id}`),
  act: (id: string, action: Action) => request<BattleResponse>("POST", `/battles/${id}/actions`, action),
  preview: (id: string, action: Action) =>
    request<PreviewOut>("POST", `/battles/${id}/preview`, action),
  /** 設定我方隊友的戰術指令（空集合 ＝ 取消）；不推進戰鬥，`steps` 為空。 */
  setOrders: (id: string, orders: OrderSet) =>
    request<BattleResponse>("PUT", `/battles/${id}/orders`, orders),
  decide: (id: string, accept: boolean) =>
    request<BattleResponse>("POST", `/battles/${id}/decision`, { accept }),
};

/** 戰鬥紀錄的下載網址（`trpg battle --log-json` 同格式，可用 `trpg battle replay` 重播）。 */
export function logUrl(battleId: string): string {
  return `/api/battles/${battleId}/log`;
}
