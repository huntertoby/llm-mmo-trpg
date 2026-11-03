// 戰鬥紀錄的浮動提示（Phase 6A-3，去文字化④；docs/art/去文字化移植需求.md 第 4 節）：
// 紀錄預設收成戰場左下 2～3 條浮動提示，舊的約 6 秒淡出；點紀錄圖示才展開完整清單，展開後可以釘選。
// 純函式：每行「出現的時間」由元件記在 Map（`stampArrivals`），這裡只決定現在要畫哪幾條、哪幾條正在淡出。
import type { LogLine } from "./log";

/** 同時最多幾條浮動提示。 */
export const TOAST_MAX = 3;
/** 一條提示從出現到消失的時間（毫秒）。 */
export const TOAST_TTL_MS = 6000;
/** 最後這段時間在淡出（CSS 的 opacity 過場）。 */
export const TOAST_FADE_MS = 1000;

/** 回合與輪的分隔行不當提示（展開的完整清單照樣有）。 */
const DIVIDER_TYPES = new Set(["turn_started", "environment_started", "turn_ended"]);

export interface LogToast {
  seq: number;
  line: LogLine;
  /** 已進入淡出（最後 `TOAST_FADE_MS`）。 */
  fading: boolean;
}

/**
 * 記下每行出現的時間：新出現的行記為 `now`。`initial`（剛進戰鬥、讀檔還原的舊紀錄）記為 `-Infinity`，
 * 不會冒出一排舊提示。回傳新的 Map（沒有新行時回傳原本那個）。
 */
export function stampArrivals(
  prev: ReadonlyMap<number, number>,
  lines: readonly LogLine[],
  now: number,
  initial = false,
): ReadonlyMap<number, number> {
  if (lines.every((line) => prev.has(line.seq))) return prev;
  // 插在已知紀錄前面的行（讀檔後非同步取回、補在前面的舊紀錄）也當舊的
  let lastKnown = -1;
  lines.forEach((line, i) => {
    if (prev.has(line.seq)) lastKnown = i;
  });
  const next = new Map(prev);
  lines.forEach((line, i) => {
    if (!next.has(line.seq)) next.set(line.seq, initial || i < lastKnown ? Number.NEGATIVE_INFINITY : now);
  });
  return next;
}

/** 現在要畫的浮動提示：最新的 `TOAST_MAX` 條、還沒過 `TOAST_TTL_MS` 的；舊的在上、新的在下。 */
export function liveToasts(lines: readonly LogLine[], arrivals: ReadonlyMap<number, number>, now: number): LogToast[] {
  const out: LogToast[] = [];
  for (let i = lines.length - 1; i >= 0 && out.length < TOAST_MAX; i -= 1) {
    const line = lines[i];
    if (line === undefined || DIVIDER_TYPES.has(line.type)) continue;
    const at = arrivals.get(line.seq);
    if (at === undefined) continue;
    const age = now - at;
    if (age >= TOAST_TTL_MS) break; // 更舊的一定也過期了
    out.push({ seq: line.seq, line, fading: age >= TOAST_TTL_MS - TOAST_FADE_MS });
  }
  return out.reverse();
}

/** 下一次畫面要變（開始淡出或消失）還要幾毫秒；沒有提示時 `null`。 */
export function nextToastChange(toasts: readonly LogToast[], arrivals: ReadonlyMap<number, number>, now: number): number | null {
  let soonest: number | null = null;
  for (const t of toasts) {
    const at = arrivals.get(t.seq);
    if (at === undefined) continue;
    const edge = t.fading ? at + TOAST_TTL_MS : at + TOAST_TTL_MS - TOAST_FADE_MS;
    const wait = Math.max(0, edge - now);
    soonest = soonest === null ? wait : Math.min(soonest, wait);
  }
  return soonest;
}
