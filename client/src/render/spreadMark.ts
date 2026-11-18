// 狀態框的「會擴散」記號（AR-SK2；移植需求 docs/art/SK-2原語-移植需求.md 第 6 項，美術第 2 版必修 2 的 B 案）。
// 由 docs/art/sample/sk2Primitives.js 的 `frameOuter`／`snap`／`spore`／`spreadMark`（B 案）逐行搬：
// 框頂右段正上方一顆病菌黃綠的孢子＋一顆往右上跳出去的小點，全部在框線外面（框線一個像素都不蓋）。
// 排法看「畫面上的框邊長」：< 14 px 用頭頂的（孢子 3 px、小點 2 px），否則用狀態卡的（孢子 4.4 px、小點 2.2 px，畫在裁切圓外面）。
// 記號往上凸出圖示的格子約 6～7 px：畫記號的 canvas 四周留邊（頭頂 `HEAD_PAD` 7、狀態卡 `CARD_PAD` 8），圖示仍在正中。
// 確定性：沒有亂數；對齊裝置像素時一律往離開框的方向。
import { blank, ctxOf, qCanvasAvailable, TAU, type Ctx } from "./qIcon/core";
import { GERM_COLORS } from "./palette";

const OUT = "#16121a";
const SPORE = { fill: GERM_COLORS.knob, ink: OUT } as const;
/** 畫面上的框邊長（CSS px）小於這個值用頭頂的大小。 */
export const SPORE_HEAD = 14;
/** 記號凸出圖示格子的留邊（CSS px）：頭頂（戰場狀態列 11）、狀態卡（20）。 */
export const HEAD_PAD = 7;
export const CARD_PAD = 8;

/** 減益方框（`statusFrame.framePath`，線寬 max(1.5, 框邊長×0.09)）的外緣：half＝頂邊外緣離框心；clipR：狀態卡裁切圓的半徑。 */
function frameOuter(size: number, unitPx: number, clipR?: number): number {
  const lw = Math.max(1.5, size * unitPx * 0.09) / unitPx, half = 0.45 * size + lw / 2;
  return clipR !== undefined ? Math.min(half, clipR) : half;
}

/** 把 ctx 單位的點對齊到裝置像素的中心；一律往右上（離開框的方向）對齊。 */
function snap(ctx: Ctx, x: number, y: number): [number, number] {
  const m = ctx.getTransform(), X = m.a * x + m.c * y + m.e, Y = m.b * x + m.d * y + m.f, sx = Math.ceil(X - 0.5) + 0.5, sy = Math.floor(Y + 0.5) - 0.5, inv = m.inverse();
  return [inv.a * sx + inv.c * sy + inv.e, inv.b * sx + inv.d * sy + inv.f];
}

function dot(ctx: Ctx, x: number, y: number, r: number, ink: number): void {
  ctx.beginPath();
  ctx.arc(x, y, r + ink, 0, TAU);
  ctx.fillStyle = SPORE.ink;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fillStyle = SPORE.fill;
  ctx.fill();
}

/**
 * 「會擴散」記號（B 案）。ctx 原點＝框心；`size`＝框邊長（ctx 的單位）；`unitPx`＝ctx 的 1 單位是幾個 CSS px；
 * `res`＝每 CSS px 幾個裝置像素；`clipR`＝狀態卡的裁切圓（ctx 的單位）。
 */
export function spreadMark(ctx: Ctx, size: number, unitPx = 1, res = 2, clipR?: number): void {
  const dev = 1 / (res * unitPx), head = size * unitPx < SPORE_HEAD, half = frameOuter(size, unitPx, clipR);
  const rs = (head ? 1.5 : 2.2) / unitPx, rd = (head ? 1 : 1.1) / unitPx;
  let [x, y] = [half - rs - dev, -(half + dev + dev + rs)];
  [x, y] = snap(ctx, x, y);
  const ang = -0.42, dd = rs + dev + rd + 0.7 / unitPx;
  const [dx, dy] = snap(ctx, x + Math.cos(ang) * dd, y + Math.sin(ang) * dd);
  ctx.save();
  dot(ctx, dx, dy, rd, dev);
  dot(ctx, x, y, rs, dev);
  ctx.restore();
}

const cache = new Map<string, HTMLCanvasElement>();

/**
 * 戰場頭頂（`statusIconCanvas(id, px)`：框 px−2）的記號：邊長 px＋2×`HEAD_PAD` 的 canvas，框心在正中（和圖示同一個中心）。
 * 沒有畫布時回 null。只有記號，圖示另外畫。
 */
export function spreadMarkHeadCanvas(px: number, res = 2): HTMLCanvasElement | null {
  if (!qCanvasAvailable()) return null;
  const key = `h|${px}|${res}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const W = px + 2 * HEAD_PAD, cv = blank(Math.round(W * res)), x = ctxOf(cv);
  x.scale(res, res);
  x.translate(W / 2, W / 2);
  spreadMark(x, px - 2, 1, res);
  cache.set(key, cv);
  return cv;
}

/**
 * 狀態卡（`statusIconTile`＋`tileCanvas`：100 單位、裁成半徑 49 的圓，框 84）的記號：邊長 px＋2×`CARD_PAD` 的 canvas，
 * 圖示的格子在正中。沒有畫布時回 null。
 */
export function spreadMarkCardCanvas(px: number, res = 2): HTMLCanvasElement | null {
  if (!qCanvasAvailable()) return null;
  const key = `c|${px}|${res}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const W = px + 2 * CARD_PAD, cv = blank(Math.round(W * res)), x = ctxOf(cv), u = (px * res) / 100;
  x.scale(u, u);
  const o = (CARD_PAD * 100) / px;
  x.translate(50 + o, 50 + o);
  spreadMark(x, 84, px / 100, res, 49);
  cache.set(key, cv);
  return cv;
}
