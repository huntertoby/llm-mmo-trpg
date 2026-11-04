// 戰鬥音效的排程（AU-3）：把一段「實際時間（正常倍速）」的音效清單排到 AudioContext 的時間上。
// - 只提前一小段（`LOOKAHEAD_S`）交給引擎，其餘留在清單裡，由計時器每隔一下補上：同時播放上限只算真的快要響的聲音，
//   而且按住空白鍵加速、按「跳過」時改得動。
// - 按住加速（`setBoost`）：只改排程，剩下的聲音照新倍率提早；不改 playbackRate，所以不變調。
// - 「跳過」（`cancelAll`）：清單清空，已經交給引擎但還沒開始的也取消（`cancelPending`），不補放。
// - 內容（哪個音效、變體鍵）在排程前就決定了（`battleSfx.ts` 的純函式）；這裡讀 AudioContext 時間只決定「何時」。
import type { AudioEngine } from "./engine";

/** 提前交給引擎的時間（秒）。 */
export const LOOKAHEAD_S = 0.12;
/** 計時器間隔（毫秒）。 */
export const PUMP_MS = 30;
/** 同一刻同一個音效最多呼叫幾次（合併的音量在 4 次左右就到頂了）。 */
export const MERGE_CALLS_MAX = 5;
export const BATTLE_GROUP = "battle";

export interface TimedCue {
  id: string;
  /** 從 `start` 那一刻起的實際毫秒（正常倍速）。 */
  realMs: number;
  key: string;
  count: number;
}

interface Batch {
  /** 開始那一刻的 AudioContext 時間（秒）與當時的進度（正常倍速的毫秒）。 */
  anchorT: number;
  anchorP: number;
  boost: number;
  cues: TimedCue[];
}

export interface PumpTimers {
  set(fn: () => void, ms: number): unknown;
  clear(handle: unknown): void;
}

const browserTimers: PumpTimers = {
  set: (fn, ms) => window.setTimeout(fn, ms),
  clear: (h) => window.clearTimeout(h as number),
};

export interface Sent {
  id: string;
  at: number;
  key: string;
}

export class CueScheduler {
  private batches: Batch[] = [];
  private boost = 1;
  private timer: unknown = null;
  /** 交給引擎的紀錄（測試、開發頁用；最多留 64 筆）。 */
  readonly sent: Sent[] = [];

  constructor(
    private readonly engine: AudioEngine,
    private readonly timers: PumpTimers = browserTimers,
    private readonly group = BATTLE_GROUP,
  ) {}

  /** 排一批（時間從現在算）。還沒解鎖時直接丟掉（解鎖前不出聲）。 */
  start(cues: readonly TimedCue[]): void {
    if (!this.engine.unlocked || cues.length === 0) return;
    const sorted = [...cues].sort((a, b) => a.realMs - b.realMs);
    this.batches.push({ anchorT: this.engine.now(), anchorP: 0, boost: this.boost, cues: sorted });
    this.pump();
  }

  /** 按住空白鍵加速（倍率 1 或 2）：還沒響的照新倍率重排。 */
  setBoost(rate: number): void {
    if (rate === this.boost) return;
    const now = this.engine.now();
    this.pendingSent = this.pendingSent.filter((s) => s.at > now);
    const all = new Set<Batch>([...this.batches, ...this.pendingSent.map((s) => s.batch)]);
    for (const b of all) {
      b.anchorP = this.progress(b, now);
      b.anchorT = now;
      b.boost = rate;
    }
    this.boost = rate;
    if (all.size === 0) return;
    // 已經交給引擎、還沒開始的是照舊倍率排的：取消，放回清單重排
    this.engine.cancelPending(this.group);
    for (const s of this.pendingSent) {
      s.batch.cues.push(s.cue);
      if (!this.batches.includes(s.batch)) this.batches.push(s.batch);
    }
    this.pendingSent = [];
    for (const b of this.batches) b.cues.sort((x, y) => x.realMs - y.realMs);
    this.pump();
  }

  /** 「跳過」：全部取消，不補放。 */
  cancelAll(): void {
    this.batches = [];
    this.pendingSent = [];
    this.engine.cancelPending(this.group);
    this.stopTimer();
  }

  /** 還沒交給引擎的數量（測試用）。 */
  get waiting(): number {
    return this.batches.reduce((s, b) => s + b.cues.length, 0);
  }

  /** 這一批在 `now`（秒）的進度（正常倍速的毫秒）。 */
  private progress(b: Batch, now: number): number {
    return b.anchorP + (now - b.anchorT) * 1000 * b.boost;
  }

  /** 已經交給引擎、時間還沒到的（加速重排時取消再放回清單）。 */
  private pendingSent: { at: number; cue: TimedCue; batch: Batch }[] = [];

  /** 把快要響的交給引擎；還有剩的就再排一次計時器。 */
  pump(): void {
    const now = this.engine.now();
    this.pendingSent = this.pendingSent.filter((s) => s.at > now);
    for (const b of this.batches) {
      const p = this.progress(b, now);
      const horizon = p + LOOKAHEAD_S * 1000 * b.boost;
      while (b.cues.length > 0 && (b.cues[0] as TimedCue).realMs <= horizon) {
        const c = b.cues.shift() as TimedCue;
        const at = now + Math.max(0, c.realMs - p) / 1000 / b.boost;
        for (let i = 0; i < Math.min(MERGE_CALLS_MAX, Math.max(1, c.count)); i++) this.engine.play(c.id, { at, variantKey: c.key, group: this.group });
        this.pendingSent.push({ at, cue: c, batch: b });
        this.sent.push({ id: c.id, at, key: c.key });
        if (this.sent.length > 64) this.sent.shift();
      }
    }
    this.batches = this.batches.filter((b) => b.cues.length > 0);
    this.stopTimer();
    if (this.batches.length > 0) this.timer = this.timers.set(() => this.pump(), PUMP_MS);
  }

  private stopTimer(): void {
    if (this.timer !== null) this.timers.clear(this.timer);
    this.timer = null;
  }
}
