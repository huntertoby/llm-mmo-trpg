// 同時播放上限（AU-1；docs/art/音效與音樂方案.md 第 3 節）：
// - 同一個音效最多 `PER_ID_MAX` 個、全部最多 `GLOBAL_MAX` 個，超過就不放新的（不搶舊的，結果可預期）；
// - 同一個 id 在同一個 `at`（毫秒取整）只放一聲，之後的次數改成把那一聲的音量略增。
// 用 AudioContext 的時間判斷哪些聲音已經結束，不讀牆上時鐘。

export const PER_ID_MAX = 3;
export const GLOBAL_MAX = 16;
/** 合併時每多一次 +15%，最多 1.45 倍。 */
export const MERGE_STEP = 0.15;
export const MERGE_MAX = 1.45;

export function mergeGain(count: number): number {
  return Math.min(MERGE_MAX, 1 + MERGE_STEP * Math.max(0, count - 1));
}

export interface Voice<H> {
  id: string;
  /** `at` 的毫秒整數（合併用）。 */
  atMs: number;
  /** 開始時間（秒；AU-3 取消還沒開始的聲音用）。 */
  at: number;
  end: number;
  count: number;
  handle: H;
  /** 分組（AU-3：`battle`）。 */
  group?: string;
}

export type Admit<H> = { kind: "play" } | { kind: "merge"; voice: Voice<H> } | { kind: "drop"; reason: "per_id" | "global" };

export class VoiceTracker<H> {
  private voices: Voice<H>[] = [];

  constructor(
    private readonly perIdMax = PER_ID_MAX,
    private readonly globalMax = GLOBAL_MAX,
  ) {}

  /** 丟掉 `now` 之前已經結束的聲音，回傳丟掉的（呼叫端斷開節點）。 */
  prune(now: number): Voice<H>[] {
    const gone = this.voices.filter((v) => v.end <= now);
    if (gone.length > 0) this.voices = this.voices.filter((v) => v.end > now);
    return gone;
  }

  /** 要不要放這一聲（呼叫前先 `prune`）。合併時順便把次數加一。 */
  admit(id: string, at: number): Admit<H> {
    const atMs = Math.round(at * 1000);
    const same = this.voices.find((v) => v.id === id && v.atMs === atMs);
    if (same !== undefined) {
      same.count += 1;
      return { kind: "merge", voice: same };
    }
    if (this.voices.filter((v) => v.id === id).length >= this.perIdMax) return { kind: "drop", reason: "per_id" };
    if (this.voices.length >= this.globalMax) return { kind: "drop", reason: "global" };
    return { kind: "play" };
  }

  add(id: string, at: number, end: number, handle: H, group?: string): Voice<H> {
    const v: Voice<H> = { id, atMs: Math.round(at * 1000), at, end, count: 1, handle, ...(group === undefined ? {} : { group }) };
    this.voices.push(v);
    return v;
  }

  /** AU-3：拿走 `group` 這一組在 `now` 之後才開始的聲音（呼叫端斷開節點；「跳過」、加速重排時用）。 */
  takePending(now: number, group: string): Voice<H>[] {
    const gone = this.voices.filter((v) => v.group === group && v.at > now);
    if (gone.length > 0) this.voices = this.voices.filter((v) => !(v.group === group && v.at > now));
    return gone;
  }

  get active(): number {
    return this.voices.length;
  }

  countOf(id: string): number {
    return this.voices.filter((v) => v.id === id).length;
  }

  clear(): void {
    this.voices = [];
  }
}
