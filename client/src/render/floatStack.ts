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
  /** 這一組最上面那個字的上緣（從頭頂線往上算，含半高；停住、還沒飄時）。 */
  top: number;
  endMs: number;
  /** 這一組目前往下推的量（6F-10b）：`from` → `to`，從 `t0` 起 `FLOAT_SLIDE_MS` 內滑過去。 */
  slide: { from: number; to: number; t0: number };
}

/** 6F-10b：同一格放不下、整疊一起往下推時，已經在畫面上的字滑下來的時間（毫秒，實際時間）。 */
export const FLOAT_SLIDE_MS = 160;

/** 一組字在 `nowMs` 時往下推的量：滑動中 ease-out 補間，滑完停在 `to`。 */
function slideAt(s: Placed["slide"], nowMs: number): number {
  if (s.from === s.to) return s.to;
  const u = Math.max(0, Math.min(1, (nowMs - s.t0) / FLOAT_SLIDE_MS));
  return s.from + (s.to - s.from) * (1 - (1 - u) * (1 - u));
}

/**
 * `placeGroup` 的結果：每個字的往上位移（相對第一個字貼頭頂時的中心）、這一組在某個時間往下推的量，
 * 和這一組要晚多久才出現（舊組要滑下來時等它們滑完，滑動途中新字不會先壓上去；不用滑時 0）。
 */
export interface PlacedGroup {
  offsets: number[];
  shiftAt: (nowMs: number) => number;
  waitMs: number;
}

/**
 * 每一格目前還在播的浮動字（只記位移與結束時間）。`place` 放一組新的字，回傳每個字的往上位移：
 * 這一格還有字沒播完，新的一組從舊的上緣再往上 `FLOAT_RISE_MAX`＋空隙開始（舊字還在往上飄，留一段飄的距離）。
 *
 * 6F-10b（美術 PM 6F-10 檢查待決 4：推回畫面內的字也要照「同一格往上堆疊」錯開，不能互相蓋住）：
 * - 位置一律從**頭頂線**（第一個字的下緣）算，兩組的第一個字高度不同（「撞擊！」比「−3」高）時也對得齊；
 * - 頭頂上方放不下（`room` ＝ 停住時最上緣最高能到哪，從頭頂線算）時，**這一格整疊一起往下推**：
 *   新的一組直接放在推過的位置，還在畫面上的舊組在 `FLOAT_SLIDE_MS` 內滑下來，同一格的字彼此距離不變。
 *   舊做法只推新的一組，會壓到同一格舊的字上（「撞擊！」蓋住「−3」）。
 */
export class FloatStack {
  private readonly cells = new Map<string, Placed[]>();

  place(key: string, nowMs: number, endMs: number, heights: readonly number[], room = Number.POSITIVE_INFINITY): number[] {
    return this.placeGroup(key, nowMs, endMs, heights, room).offsets;
  }

  placeGroup(key: string, nowMs: number, endMs: number, heights: readonly number[], room = Number.POSITIVE_INFINITY): PlacedGroup {
    if (heights.length === 0) return { offsets: [], shiftAt: () => 0, waitMs: 0 };
    const alive = (this.cells.get(key) ?? []).filter((p) => p.endMs > nowMs);
    const below = alive.reduce((m, p) => Math.max(m, p.top), Number.NEGATIVE_INFINITY);
    // 第一個字的下緣：這一格沒有字時貼頭頂（0），有字時在最上面那組的上緣再往上留一段飄的距離
    const bottom = alive.length === 0 ? 0 : below + FLOAT_RISE_MAX + FLOAT_STACK_GAP;
    const offsets = stackOffsets(heights, bottom);
    const last = heights.length - 1;
    const top = (heights[0] ?? 0) / 2 + (offsets[last] ?? 0) + (heights[last] ?? 0) / 2;
    // 整疊往下推的量：同一格還有字時只增不減；舊組從現在的位置滑過去
    const prev = alive.reduce((m, p) => Math.max(m, p.slide.to), 0);
    const need = Math.max(prev, top - room, 0);
    let waitMs = 0;
    for (const p of alive) {
      if (p.slide.to === need) continue;
      p.slide = { from: slideAt(p.slide, nowMs), to: need, t0: nowMs };
      waitMs = FLOAT_SLIDE_MS;
    }
    const placed: Placed = { top, endMs, slide: { from: need, to: need, t0: nowMs } };
    alive.push(placed);
    this.cells.set(key, alive);
    return { offsets, shiftAt: (ms) => slideAt(placed.slide, ms), waitMs };
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

/**
 * 6F-12（美術 PM 6F-11 檢查第 2 點：戰場震動時「撞擊！」超出戰場左緣約 5～6px）：浮動字夾在「震動、鏡頭偏移之後
 * 畫面上看得到的戰場」裡（世界座標）。
 * - 浮動字和地圖在同一個場景裡，震動（`shake`，場景位移）與鏡頭（`cam`，地圖位移）本來就一起動；
 * - 但 6F-10 夾的是畫布邊緣（`-cam.x` 起）：鏡頭往右推、或震動把地圖往右移時，畫布左邊露出一條底色，字卻還貼著畫布左緣；
 * - 改成左右、下緣取「地圖」和「畫布上看得到的範圍」的交集：地圖被推出畫布時，字也往內推，不會被切掉。
 * 上緣照舊是畫布上緣（含頭頂預留；第一排的人頭上沒空間時字可以在地圖上面，6F-10），只多扣掉震動的位移。
 */
export function visibleFieldBounds(mapW: number, mapH: number, reserveTop: number, cam: { x: number; y: number }, shake: { x: number; y: number }): FloatBounds {
  const ox = cam.x + shake.x;
  const oy = cam.y + shake.y;
  return { left: Math.max(0, -ox), top: -reserveTop - oy, right: Math.min(mapW, mapW - ox), bottom: Math.min(mapH, mapH - oy) };
}

/**
 * 6F-11（美術 PM 6F-10b 檢查第 2 點）：頭頂上方放不下、整疊往下推時，再多往下推幾 px（畫面 px，6～8px 的中間），
 * 最上面的字（例如左上角主角的「−7」）留在戰場上緣以內。
 */
export const FLOAT_TOP_SHIFT_PX = 7;

/**
 * 6F-11：一組字往上飄的最大距離。停住時最上面那個字的上緣 `restTop` 在戰場上緣 `mapTop` 以內的，
 * 飄到最高也不超過上緣往下 `pad`（離上緣不到 `pad` 的就不往上飄）；停住時就在上緣之外的
 * （第一排的人頭上沒空間，字本來就在頭頂預留裡）照舊。
 */
export function capRise(riseMax: number, restTop: number, mapTop: number, pad = FLOAT_EDGE_PAD): number {
  if (restTop < mapTop) return riseMax;
  return Math.min(riseMax, Math.max(0, restTop - (mapTop + pad)));
}

/** `FLOAT_TOP_SHIFT_PX` 換成世界座標（地圖縮放 `scale`）：畫面上不論 1600 或 800 寬都是 7px。 */
export function floatTopShift(scale: number): number {
  return scale > 0 ? FLOAT_TOP_SHIFT_PX / scale : FLOAT_TOP_SHIFT_PX;
}

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
