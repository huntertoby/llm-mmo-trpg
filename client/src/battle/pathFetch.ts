// 路徑預覽的請求節流與快取（Phase 6A-4c）：滑鼠在格子間移動時，最多每 120ms 送一次請求（先送一次，之後在
// 時間到時補送最新的那條），同一條路徑在同一個戰鬥狀態下只問一次。晚到的舊回應只進快取，不蓋掉目前要的。
// 計時器與請求函式由外面傳入，方便測試；React 的包裝在 `ui/usePathPreview.ts`。
import type { PathPreview, PathQuery } from "./pathPreview";

export const PATH_PREVIEW_THROTTLE_MS = 120;

export interface FetcherDeps {
  fetch(body: PathQuery["body"]): Promise<PathPreview>;
  /** 目前要的路徑有結果（或換成沒有要的路徑）時通知。 */
  onResult(key: string | null, preview: PathPreview | null): void;
  now(): number;
  setTimer(fn: () => void, ms: number): number;
  clearTimer(id: number): void;
  throttleMs?: number;
}

/**
 * React 包裝用的範圍（6C-R1）：fetcher 只建一次，但送請求時讀「目前」的戰鬥 id（舊版建立時把 battleId 綁死，
 * 換戰鬥後仍向舊戰鬥問路徑）。`update` 每次 render 呼叫：戰鬥或狀態變了回傳 `true`，呼叫端要 `reset` fetcher。
 */
export class PathPreviewScope {
  constructor(
    private battle: string,
    private stateKey: unknown,
  ) {}

  get battleId(): string {
    return this.battle;
  }

  update(battleId: string, stateKey: unknown): boolean {
    if (battleId === this.battle && stateKey === this.stateKey) return false;
    this.battle = battleId;
    this.stateKey = stateKey;
    return true;
  }

  /** 送出時才讀目前的戰鬥 id 的請求函式。 */
  fetchWith(fetchFor: (battleId: string, body: PathQuery["body"]) => Promise<PathPreview>): FetcherDeps["fetch"] {
    return (body) => fetchFor(this.battle, body);
  }
}

export class PathPreviewFetcher {
  private readonly cache = new Map<string, PathPreview>();
  /** 已經送出、還沒回來的請求（同一條不重送）。 */
  private readonly inflight = new Set<string>();
  private wanted: PathQuery | null = null;
  private lastSent = Number.NEGATIVE_INFINITY;
  private timer: number | null = null;
  /** 戰鬥狀態的世代：狀態改變（`reset`）之後，之前送出的請求回來時丟掉。 */
  private generation = 0;
  private readonly throttle: number;

  constructor(private readonly deps: FetcherDeps) {
    this.throttle = deps.throttleMs ?? PATH_PREVIEW_THROTTLE_MS;
  }

  /** 送出的請求次數（測試用）。 */
  sent = 0;

  /** 現在要預覽的路徑（`null` ＝ 不預覽）。快取有就立刻回傳。 */
  want(query: PathQuery | null): void {
    this.wanted = query;
    if (query === null) {
      this.cancelTimer();
      this.deps.onResult(null, null);
      return;
    }
    const hit = this.cache.get(query.key);
    if (hit !== undefined) {
      this.cancelTimer();
      this.deps.onResult(query.key, hit);
      return;
    }
    if (this.inflight.has(query.key)) return;
    const wait = this.lastSent + this.throttle - this.deps.now();
    if (wait <= 0) {
      this.cancelTimer();
      this.send(query);
    } else if (this.timer === null) {
      this.timer = this.deps.setTimer(() => {
        this.timer = null;
        const cur = this.wanted;
        if (cur !== null && !this.cache.has(cur.key) && !this.inflight.has(cur.key)) this.send(cur);
      }, wait);
    }
  }

  /** 戰鬥狀態變了：清掉快取，之前的請求作廢。 */
  reset(): void {
    this.generation += 1;
    this.cache.clear();
    this.inflight.clear();
    this.cancelTimer();
  }

  dispose(): void {
    this.reset();
    this.wanted = null;
  }

  private cancelTimer(): void {
    if (this.timer === null) return;
    this.deps.clearTimer(this.timer);
    this.timer = null;
  }

  private send(query: PathQuery): void {
    const gen = this.generation;
    this.lastSent = this.deps.now();
    this.sent += 1;
    this.inflight.add(query.key);
    this.deps
      .fetch(query.body)
      .then((pv) => {
        if (gen !== this.generation) return;
        this.inflight.delete(query.key);
        this.cache.set(query.key, pv);
        if (this.wanted?.key === query.key) this.deps.onResult(query.key, pv);
      })
      .catch(() => {
        // 預覽失敗（例如狀態剛變）：不畫路徑，不打擾玩家
        if (gen === this.generation) this.inflight.delete(query.key);
      });
  }
}
