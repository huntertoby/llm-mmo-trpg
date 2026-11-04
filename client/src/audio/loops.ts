// 循環音的「槽」（AU-3）：環境音的底聲、戰鬥中的燃燒劈啪。每個槽同時只放一條（燃燒全場一條就是一個槽）。
// - `set(slot, spec)`：要放什麼；`null`＝停（淡出）。同樣的內容再設一次不會重開。
// - 還沒解鎖時先記著，解鎖（引擎發出變更通知）後才開始；減少刺耳音效切換時重開（柔和版／環境軌 harsh 不出聲）。
// 不讀時鐘、不用 Math.random：開始與淡出都排在 AudioContext 的時間上。
import type { AudioEngine, LoopHandle } from "./engine";
import type { Track } from "./types";

export interface LoopSpec {
  id: string;
  track?: Track;
  /** 這一條的音量（線性，預設 1）。 */
  gain?: number;
  variantKey?: string;
}

interface Live {
  sig: string;
  handle: LoopHandle | null;
}

const sigOf = (s: LoopSpec, harsh: boolean): string => `${s.id}|${s.track ?? ""}|${s.gain ?? 1}|${s.variantKey ?? ""}|${harsh ? 1 : 0}`;

export class LoopDeck {
  private readonly want = new Map<string, LoopSpec>();
  private readonly live = new Map<string, Live>();
  private unsubscribe: (() => void) | null = null;

  constructor(
    private readonly engine: AudioEngine,
    private readonly fade = 0.8,
  ) {}

  /** 設定一個槽；`null`＝停。 */
  set(slot: string, spec: LoopSpec | null): void {
    if (spec === null) this.want.delete(slot);
    else this.want.set(slot, spec);
    this.ensureListening();
    this.sync();
  }

  /** 目前想放的槽（測試、開發頁用）。 */
  slots(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const slot of [...this.want.keys()].sort()) out[slot] = this.want.get(slot)?.id ?? "";
    return out;
  }

  /** 真的在出聲的槽（解鎖後、沒有被減少刺耳音效擋掉）。 */
  playing(): string[] {
    return [...this.live.entries()].filter(([, l]) => l.handle !== null).map(([slot]) => slot).sort();
  }

  /** 全部停掉（離開畫面時）。 */
  clear(): void {
    this.want.clear();
    this.sync();
  }

  private ensureListening(): void {
    if (this.unsubscribe === null) this.unsubscribe = this.engine.subscribe(() => this.sync());
  }

  /** 把想要的狀態套上去（冪等）。 */
  sync(): void {
    const harsh = this.engine.settings.reduceHarsh;
    for (const [slot, l] of [...this.live]) {
      const w = this.want.get(slot);
      if (w !== undefined && sigOf(w, harsh) === l.sig && (l.handle !== null || !this.engine.unlocked)) continue;
      l.handle?.stop(this.fade);
      this.live.delete(slot);
    }
    if (!this.engine.unlocked) return;
    for (const slot of [...this.want.keys()].sort()) {
      if (this.live.has(slot)) continue;
      const w = this.want.get(slot) as LoopSpec;
      const opts = { fadeIn: this.fade, ...(w.track === undefined ? {} : { track: w.track }), ...(w.gain === undefined ? {} : { gain: w.gain }), ...(w.variantKey === undefined ? {} : { variantKey: w.variantKey }) };
      this.live.set(slot, { sig: sigOf(w, harsh), handle: this.engine.startLoop(w.id, opts) });
    }
  }
}
