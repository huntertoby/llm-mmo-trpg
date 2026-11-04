// 浮動字錯開往上堆（Phase 6F-6，巡檢 bug 8：「擊倒／暴擊 −9／倒地！」三行壓在一起、「＋11 盾」和「閃避」重疊）。
// 純函式＋一個小記錄表，不碰 Pixi、不用 Math.random()、不讀時鐘（時間由呼叫端傳進來）。
//
// 舊的做法（6N-7）每個字只看「同一步同一格的第幾個」往上 22 px，三種情況會疊在一起：
// 1. 同一格的字是不同幾步（例如陷阱夾住那一拍、接著的傷害那一步）各自從第 0 個算起；
// 2. 一般字約 28 px 高、暴擊字更高，22 px 的間距本來就不夠；後出現的字晚開始飄，先出現的字往上追；
// 3. 第一排的人頭頂沒空間時每個字都被壓到同一個高度。
// 現在：
// - 同一格的字照實際高度累加（字距 `FLOAT_STACK_GAP`）；
// - 同一格還有字沒播完時，新的一組接在舊的一組上面，再多留一段飄的距離（`FLOAT_RISE_MAX`）；
// - 同一組的字一起飄（飄的距離照整組的時間算，`groupRise`），只有出現（彈一下）照各自的延遲；
// - 頭頂上方放不下時整組一起往下推（寧可蓋到身體也不切掉字，同 6N-7 的取捨），不會壓在同一個高度。
import { FLOAT_RISE_MAX } from "./uiAnim";

/** 同一格兩個字之間的空隙（模型像素；字的外框之間）。 */
export const FLOAT_STACK_GAP = 2;

/** 一組字裡第 `i` 個字的往上位移（0 ＝ 第一個，貼頭頂）：照實際高度累加，中心距 ＝ 兩字半高相加＋空隙。 */
export function stackOffsets(heights: readonly number[], base = 0, gap = FLOAT_STACK_GAP): number[] {
  const out: number[] = [];
  let y = base;
  heights.forEach((h, i) => {
    if (i > 0) y += ((heights[i - 1] ?? 0) + h) / 2 + gap;
    out.push(y);
  });
  return out;
}

interface Placed {
  /** 這一組最上面那個字的上緣（往上位移，含半高）。 */
  top: number;
  endMs: number;
}

/**
 * 每一格目前還在播的浮動字（只記位移與結束時間）。`place` 放一組新的字，回傳每個字的往上位移：
 * 這一格還有字沒播完，新的一組從舊的上緣再往上 `FLOAT_RISE_MAX`＋空隙開始（舊字還在往上飄，留一段飄的距離）。
 */
export class FloatStack {
  private readonly cells = new Map<string, Placed[]>();

  place(key: string, nowMs: number, endMs: number, heights: readonly number[]): number[] {
    if (heights.length === 0) return [];
    const alive = (this.cells.get(key) ?? []).filter((p) => p.endMs > nowMs);
    const top = alive.reduce((m, p) => Math.max(m, p.top), Number.NEGATIVE_INFINITY);
    const first = heights[0] ?? 0;
    const base = alive.length === 0 ? 0 : top + FLOAT_RISE_MAX + FLOAT_STACK_GAP + first / 2;
    const offsets = stackOffsets(heights, base);
    const last = heights.length - 1;
    alive.push({ top: (offsets[last] ?? 0) + (heights[last] ?? 0) / 2, endMs });
    this.cells.set(key, alive);
    return offsets;
  }

  /** 換場景（新的戰鬥、重畫全部）時清掉。 */
  clear(): void {
    this.cells.clear();
  }
}

/**
 * 字的中心 y（往上位移 `offset` 之後）：`natural` ＝ 第一個字貼頭頂時的中心 y，`limit` ＝ 字飄到最高時中心 y 的下限
 * （地圖上緣＋半高＋最大飄高）。`topOffset` ＝ 同一組最上面那個字的位移。頭頂上方放得下就往上疊；放不下時
 * 整組一起往下推到最上面那個字剛好在 `limit`（字的順序、間距都不變，不會壓在一起；下面的字可能蓋到身體）。
 */
export function stackedY(natural: number, offset: number, limit: number, topOffset = offset): number {
  const shift = Math.max(0, limit - (natural - topOffset));
  return natural - offset + shift;
}

/**
 * 一組字一起飄：`p` ＝ 這個字自己的進度（出現延遲之後才從 0 起），換成整組的進度再算飄的距離，
 * 先出現的字和後出現的字飄一樣高，後面的字不會被前面的追上。`delayFrac` ＝ 延遲佔整組時間的比例。
 */
export function groupRise(p: number, delayFrac: number, riseMax: number): number {
  const q = Math.max(0, Math.min(1, p));
  const g = delayFrac + q * (1 - delayFrac);
  return Math.min(1, g * 1.5) * riseMax;
}

// ---- 6F-10：浮動字不超出戰場（美術 PM 6F-9 檢查第 2 節第 2 點：「撞擊！」被戰場左緣切掉） ----

/** 畫布上看得到的範圍（世界座標）：左、上、右、下。 */
export interface FloatBounds {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/** 字的外框（含黑邊）離戰場邊緣至少幾 px。 */
export const FLOAT_EDGE_PAD = 2;

function clampAxis(c: number, half: number, lo: number, hi: number, pad: number): number {
  if (!(hi > lo)) return c;
  // 字比戰場還寬／高時放在正中間（兩邊一樣多，不會只切一邊）
  if (half * 2 + pad * 2 >= hi - lo) return (lo + hi) / 2;
  return Math.min(Math.max(c, lo + half + pad), hi - half - pad);
}

/**
 * 浮動字中心的位置，往內推到整個字（`halfW`、`halfH` ＝ 這一幀的半寬、半高，含彈一下的放大與黑邊）都在 `b` 裡，
 * 四個邊都一樣；靠邊的單位頭上的字往內推，其他的不動。每一幀照當下的大小算（彈一下時比停住時大）。
 */
export function clampFloatCenter(x: number, y: number, halfW: number, halfH: number, b: FloatBounds, pad = FLOAT_EDGE_PAD): { x: number; y: number } {
  return { x: clampAxis(x, halfW, b.left, b.right, pad), y: clampAxis(y, halfH, b.top, b.bottom, pad) };
}
