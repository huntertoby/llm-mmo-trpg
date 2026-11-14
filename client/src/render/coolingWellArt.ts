// 冷卻井 `cooling_well` 的畫法與破壞演出（CW-1；移植需求 docs/art/冷卻井-移植需求.md，樣張 docs/art/sample/coolingWell.js 第 2 版）。
// 全部在 52 單位的格子座標畫（呼叫端 translate＋scale）；格子座標雜湊用 `artRandom.rng`（salt 241～243，同樣張）。
// 美術 PM 結案的兩條可修（第 10 節）照做：受損小水灘往格內收（不伸到格邊）；K1、K2 飛在空中的碎塊放大 1.3 倍、外框 2。
// 受損級距自己畫（同薄冰；`objectArt.drawObject` 不再疊通用裂痕）。
import { TAU, type Ctx } from "./artDraw";
import { rng } from "./artRandom";
import type { HpStage } from "./fieldFx";

const T = 52;
const OUT = "#1c1712"; // ASH.outline
export const WELL_COLORS = {
  top: "#7a6e64", // ASH.ruinTop
  face: "#5a4e44", // ASH.ruinFace
  mortar: "#2e2620",
  crack: "#1a1410",
  iron: "#3a3c3e",
  rust: "#9a4a20",
  inner: "#231c17",
  water: "#3a8ee0", // 井水亮藍（物件識別色，和漏出的普通水表面 #45627a 不同色，美術 PM 已接受）
  waterHi: "#8fd4ff",
  drop: "#4aa8ff",
  ink: "#1a1208",
  steam: "rgba(232,242,250,0.42)",
} as const;
const C = WELL_COLORS;

/** 井圈幾何：頂面橢圓中心 (26, 24.5)、半徑 20×9（上緣 15.5，不高於殘牆壓頂石）；正面高 10；井口 13×5.5。 */
export const WELL_GEOM = { cx: 26, ty: 24.5, rx: 20, ry: 9, face: 10, irx: 13, iry: 5.5 } as const;
const G = WELL_GEOM;
const KY = G.ry / 11.5;

/** 破壞演出的時間表（毫秒，事件到達起算；正常速度）：K0 裂、K1 爆開、K2 漫出、K3 鋪滿、K4 留下。 */
export const WELL_FRAMES_MS: readonly number[] = [0, 90, 200, 340, 520];
/** 演出長度（毫秒，正常速度）：到 K4 就是靜態的打破後。 */
export const WELL_BREAK_MS = 520;
/** 新水面遮罩的半徑（52 單位，從井那一格的中心算）；K4 不用遮罩。 */
export const WELL_MASK_R: readonly number[] = [0, 30, 60, 92, Infinity];

/** 演出到 `ms`（正常速度）時是第幾格（0～4）。 */
export function wellFrameAt(ms: number): number {
  let k = 0;
  for (let i = 0; i < WELL_FRAMES_MS.length; i++) if (ms >= (WELL_FRAMES_MS[i] as number)) k = i;
  return k;
}

/** 演出到 `ms` 時新水面遮罩的半徑（52 單位；格間線性內插，K3 → K4 內插到蓋滿 3×3 的角 ≈ 110；到 K4 為 `Infinity`）。 */
export function wellMaskRadius(ms: number): number {
  if (ms >= WELL_BREAK_MS) return Infinity;
  if (ms <= 0) return 0;
  const k = wellFrameAt(ms);
  const t0 = WELL_FRAMES_MS[k] as number;
  const t1 = WELL_FRAMES_MS[k + 1] as number;
  const r0 = WELL_MASK_R[k] as number;
  const r1 = k + 1 >= 4 ? 112 : (WELL_MASK_R[k + 1] as number);
  return r0 + ((r1 - r0) * (ms - t0)) / (t1 - t0);
}

/** 遮罩邊緣（微微不規則的圓）的點：從井那一格的中心 (26, 26) 長，半徑 `R`（52 單位）。 */
export function wellMaskPoints(R: number): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (let i = 0; i < 32; i++) {
    const a = (i / 32) * TAU;
    const q = R * (1 + 0.07 * Math.sin(a * 5 + 1.3) + 0.04 * Math.sin(a * 9));
    out.push([T / 2 + Math.cos(a) * q, T / 2 + Math.sin(a) * q]);
  }
  return out;
}

const yTop = (x: number): number => G.ty + G.ry * Math.sqrt(Math.max(0, 1 - ((x - G.cx) / G.rx) ** 2));

function shadow(ctx: Ctx, cx: number, cy: number, rx: number, ry: number): void {
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.beginPath();
  ctx.ellipse(cx, cy, rx, ry, 0, 0, TAU);
  ctx.fill();
}

function facePath(ctx: Ctx): void {
  const { cx, ty, rx, ry, face } = G;
  ctx.beginPath();
  ctx.moveTo(cx - rx, ty);
  ctx.lineTo(cx - rx, ty + face);
  ctx.ellipse(cx, ty + face, rx, ry, 0, Math.PI, 0, true);
  ctx.lineTo(cx + rx, ty);
  ctx.ellipse(cx, ty, rx, ry, 0, 0, Math.PI, false);
  ctx.closePath();
}

function line(ctx: Ctx, pts: ReadonlyArray<readonly [number, number]>, color: string, w: number): void {
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
  ctx.stroke();
}

/** 水滴記號（打破會漏水；照油桶危險記號：黑框實心小圖形畫在物件正面）。 */
export function wellSpillMark(ctx: Ctx, cx: number, cy: number, s = 6.5): void {
  ctx.beginPath();
  ctx.moveTo(cx, cy - s);
  ctx.bezierCurveTo(cx + s * 0.35, cy - s * 0.45, cx + s * 0.72, cy - s * 0.05, cx + s * 0.72, cy + s * 0.32);
  ctx.arc(cx, cy + s * 0.32, s * 0.72, 0, Math.PI, false);
  ctx.bezierCurveTo(cx - s * 0.72, cy - s * 0.05, cx - s * 0.35, cy - s * 0.45, cx, cy - s);
  ctx.closePath();
  ctx.fillStyle = C.drop;
  ctx.fill();
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = C.ink;
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.beginPath();
  ctx.ellipse(cx - s * 0.3, cy + s * 0.18, s * 0.17, s * 0.3, 0.3, 0, TAU);
  ctx.fill();
}

function wellWater(ctx: Ctx, stage: HpStage): void {
  const { cx, ty, irx, iry } = G;
  ctx.save();
  ctx.beginPath();
  ctx.ellipse(cx, ty + 0.5, irx, iry, 0, 0, TAU);
  ctx.clip();
  ctx.fillStyle = C.inner;
  ctx.fillRect(cx - irx, ty - iry, irx * 2, iry * 2 + 1);
  const wy = ty + 2 + (stage === 2 ? 0.8 : 0);
  ctx.beginPath();
  ctx.ellipse(cx, wy, irx - 0.8, iry - 1.4, 0, 0, TAU);
  ctx.fillStyle = C.water;
  ctx.fill();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.beginPath();
  ctx.ellipse(cx + 4, wy + 2, irx - 4, iry - 3, 0, 0, TAU);
  ctx.fill();
  ctx.fillStyle = C.waterHi;
  ctx.beginPath();
  ctx.ellipse(cx - 4, wy - 1.2, 5.5, 1.5, -0.08, 0, TAU);
  ctx.fill();
  line(ctx, [[cx + 2, wy + 1], [cx + 8, wy + 0.7]], "rgba(255,255,255,0.75)", 1.1);
  ctx.restore();
  ctx.lineWidth = 1.4;
  ctx.strokeStyle = OUT;
  ctx.beginPath();
  ctx.ellipse(cx, ty + 0.5, irx, iry, 0, 0, TAU);
  ctx.stroke();
}

function steam(ctx: Ctx): void {
  const { cx, ty } = G;
  ctx.save();
  ctx.lineCap = "round";
  ctx.strokeStyle = C.steam;
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(cx - 4, ty);
  ctx.bezierCurveTo(cx - 9, ty - 3, cx - 1, ty - 6, cx - 6, ty - 10);
  ctx.stroke();
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(cx + 5, ty - 1);
  ctx.bezierCurveTo(cx + 9, ty - 4, cx + 3, ty - 6, cx + 7, ty - 9);
  ctx.stroke();
  ctx.restore();
}

/** 受損漏出的小灘中心（52 單位）：井身左右兩側，往格內收（美術 PM 結案可修 1：不伸到格邊）。 */
export const WELL_PUDDLES: readonly [number, number] = [8, 44];
const PUDDLE_RX = 3.8;

function puddle(ctx: Ctx, x: number): void {
  ctx.fillStyle = "rgba(58,142,224,0.7)";
  ctx.beginPath();
  ctx.ellipse(x, 41, PUDDLE_RX, 1.8, 0, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "rgba(143,212,255,0.8)";
  ctx.beginPath();
  ctx.ellipse(x - 1, 40.4, 1.6, 0.6, 0, 0, TAU);
  ctx.fill();
}

function body(ctx: Ctx): void {
  const { cx, ty, rx, ry, face } = G;
  facePath(ctx);
  ctx.fillStyle = C.face;
  ctx.fill();
  ctx.save();
  facePath(ctx);
  ctx.clip();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  ctx.fillRect(cx + 7, 0, T, T);
  ctx.strokeStyle = C.mortar;
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  ctx.ellipse(cx, ty + face * 0.55, rx, ry, 0, 0.05, Math.PI - 0.05);
  ctx.stroke();
  for (const x of [13, 25, 37]) {
    const y0 = yTop(x);
    ctx.beginPath();
    ctx.moveTo(x, y0 + 3.2);
    ctx.lineTo(x, y0 + face * 0.55);
    ctx.stroke();
  }
  for (const x of [8, 19, 31, 42]) {
    const y0 = yTop(x);
    ctx.beginPath();
    ctx.moveTo(x, y0 + face * 0.55);
    ctx.lineTo(x, y0 + face);
    ctx.stroke();
  }
  ctx.restore();
  ctx.strokeStyle = C.iron;
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.ellipse(cx, ty + 2.4, rx, ry, 0, 0.02, Math.PI - 0.02);
  ctx.stroke();
  for (const x of [10, 26, 42]) {
    ctx.fillStyle = "#6a6e70";
    ctx.beginPath();
    ctx.arc(x, yTop(x) + 2.4, 1.1, 0, TAU);
    ctx.fill();
  }
  for (const [x, dy, rad] of [[17, 2.6, 1.6], [34, 2.8, 1.3]] as const) {
    ctx.fillStyle = C.rust;
    ctx.beginPath();
    ctx.arc(x, yTop(x) + dy, rad, 0, TAU);
    ctx.fill();
  }
  facePath(ctx);
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  // 頂面井圈
  ctx.beginPath();
  ctx.ellipse(cx, ty, rx, ry, 0, 0, TAU);
  ctx.fillStyle = C.top;
  ctx.fill();
  ctx.strokeStyle = C.mortar;
  ctx.lineWidth = 1.1;
  ctx.beginPath();
  for (const a of [0.3, 1.15, 1.95, 2.8, 3.55, 4.35, 5.15, 5.85]) {
    ctx.moveTo(cx + Math.cos(a) * G.irx, ty + 0.5 + Math.sin(a) * G.iry);
    ctx.lineTo(cx + Math.cos(a) * rx, ty + Math.sin(a) * ry);
  }
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.4)";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.ellipse(cx, ty, rx - 2, ry - 1.6, 0, Math.PI * 1.08, Math.PI * 1.42);
  ctx.stroke();
  ctx.lineWidth = 2;
  ctx.strokeStyle = OUT;
  ctx.beginPath();
  ctx.ellipse(cx, ty, rx, ry, 0, 0, TAU);
  ctx.stroke();
}

function crack(ctx: Ctx, pts: ReadonlyArray<readonly [number, number]>, w = 1.9): void {
  line(ctx, pts.map(([x, y]) => [x - 1.1, y] as const), "rgba(255,255,255,0.3)", 1);
  line(ctx, pts, C.crack, w);
}

function flashOver(ctx: Ctx): void {
  const { cx, ty, rx, ry, face } = G;
  ctx.save();
  ctx.fillStyle = "rgba(255,255,255,0.5)";
  facePath(ctx);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(cx, ty, rx, ry, 0, 0, TAU);
  ctx.ellipse(cx, ty + 0.5, G.irx, G.iry, 0, 0, TAU);
  ctx.fill("evenodd");
  ctx.restore();
  const cracks: ReadonlyArray<ReadonlyArray<readonly [number, number]>> = [
    [[15, yTop(15)], [16.5, yTop(15) + 4], [14.5, yTop(15) + 7.5], [16, yTop(15) + face]],
    [[37, yTop(37)], [35.5, yTop(37) + 4], [38, yTop(37) + 8], [36.5, yTop(37) + face]],
    [[cx + 1, ty + 7.6 * KY], [cx + 2.5, ty + ry + 0.5], [cx, ty + ry + 4.5]],
  ];
  for (const pts of cracks) {
    line(ctx, pts, C.crack, 2.6);
    line(ctx, pts, C.waterHi, 1.2);
  }
  for (const [x0, y0, dx, dy] of [[16, yTop(15) + 6, -6, -2], [36.5, yTop(37) + 6, 6, -2.5], [cx + 1.5, ty + ry + 3, 0.5, 4]] as const) {
    line(ctx, [[x0, y0], [x0 + dx, y0 + dy]], C.waterHi, 2);
  }
}

export interface WellSpec {
  x: number;
  y: number;
  hpStage: HpStage;
  /** 破壞演出 K0：白閃＋裂縫亮、裂縫噴水。 */
  flash?: boolean;
}

/** 完好／受損 1／受損 2 的冷卻井（`flash`：破壞演出 K0）。 */
export function drawCoolingWell(ctx: Ctx, s: WellSpec): void {
  const st = s.hpStage;
  const { cx, ty, ry, face } = G;
  const r = rng(s.x, s.y, 241);
  shadow(ctx, cx + 3, ty + face + 5, G.rx + 3, ry - 2);
  if (st >= 1) puddle(ctx, WELL_PUDDLES[0]);
  if (st === 2) puddle(ctx, WELL_PUDDLES[1]);
  body(ctx);
  wellWater(ctx, st);
  if (st === 2) {
    ctx.beginPath();
    ctx.moveTo(cx + 9, ty + 5.6 * KY);
    ctx.lineTo(cx + 12.5, ty + 10.8 * KY);
    ctx.lineTo(cx + 16.5, ty + 7.6 * KY);
    ctx.lineTo(cx + 13.2, ty + 3.6 * KY);
    ctx.closePath();
    ctx.fillStyle = C.water;
    ctx.fill();
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
  if (st >= 1) {
    const k = (r() - 0.5) * 2;
    const y0 = yTop(15);
    crack(ctx, [[15, y0 - 0.5], [16.5 + k, y0 + 3.5], [14.5, y0 + 6.5], [16 + k, y0 + face]]);
    line(ctx, [[16 + k, y0 + 5], [15.6 + k, y0 + face - 0.5], [12, 41.6], [WELL_PUDDLES[0] + 2, 41.2]], C.water, 1.7);
  }
  if (st === 2) {
    const y0 = yTop(37);
    crack(ctx, [[37, y0], [35.5, y0 + 4], [38, y0 + 7], [36.5, y0 + face]]);
    crack(ctx, [[cx - 6, ty - 9.5 * KY], [cx - 4, ty - 7 * KY], [cx - 6.5, ty - 5.6 * KY]], 1.5);
    line(ctx, [[36.5, y0 + 5], [37, y0 + face - 0.5], [40.5, 41.6], [WELL_PUDDLES[1] - 2, 41.2]], C.water, 1.7);
  }
  if (s.flash === true) flashOver(ctx);
  else if (st < 2) steam(ctx);
  wellSpillMark(ctx, cx, ty + ry + face * 0.5 - 0.5, 5.6);
}

// ---- 碎屑（打破後殘留的裝飾，不是物件）與破壞演出 ----

const RUB_N = 10;
const RUB_Y = 28;
/** K1、K2 飛在空中的碎塊放大倍率與外框（美術 PM 結案可修 2）。 */
export const AIR_CHUNK_SCALE = 1.3;
export const AIR_CHUNK_OUTLINE = 2;

interface Chunk {
  x: number;
  y: number;
  lift: number;
  pts: Array<[number, number]>;
  wet: boolean;
  /** 在空中（K1、K2）：放大、外框加粗。 */
  air: boolean;
}

/** 10 塊碎石：k 1 往外飛、k 2 快落地、k ≥ 3 落定（＝碎屑）。照 y 排序。 */
export function wellChunks(s: { x: number; y: number }, k: number): Chunk[] {
  const r = rng(s.x, s.y, 242);
  const kk = Math.min(4, k);
  const spread = [0, 6, 10, 4, 4][kk] as number;
  const lift = [0, 9, 4, 0, 0][kk] as number;
  const air = kk === 1 || kk === 2;
  const out: Chunk[] = [];
  for (let i = 0; i < RUB_N; i++) {
    const a = (i / RUB_N) * TAU + 0.35 + (r() - 0.5) * 1.0;
    const rad = (2.5 + r() * 1.5) * (air ? AIR_CHUNK_SCALE : 1);
    const d = 14 + (r() - 0.5) * 10;
    const n = 5 + (i % 2);
    const pts: Array<[number, number]> = [];
    for (let j = 0; j < n; j++) {
      const b = (j / n) * TAU + r() * 0.6;
      const q = rad * (0.7 + r() * 0.45);
      pts.push([Math.cos(b) * q, Math.sin(b) * q * 0.66]);
    }
    out.push({ x: G.cx + Math.cos(a) * (d + spread), y: RUB_Y + Math.sin(a) * (d * 0.58 + spread * 0.6), lift: lift * (0.7 + r() * 0.6), pts, wet: kk >= 3, air });
  }
  return out.sort((p, q) => p.y - q.y);
}

function drawChunk(ctx: Ctx, c: Chunk): void {
  const th = 2.2;
  const top = c.y - c.lift;
  const ow = c.air ? AIR_CHUNK_OUTLINE : 1.3;
  if (c.lift >= 1) {
    ctx.fillStyle = "rgba(0,0,0,0.2)";
    ctx.beginPath();
    ctx.ellipse(c.x, c.y + th, 2.6, 1, 0, 0, TAU);
    ctx.fill();
  }
  const path = (dy: number): void => {
    ctx.beginPath();
    c.pts.forEach(([px, py], i) => (i === 0 ? ctx.moveTo(c.x + px, top + py + dy) : ctx.lineTo(c.x + px, top + py + dy)));
    ctx.closePath();
  };
  ctx.lineJoin = "round";
  path(th);
  ctx.fillStyle = C.face;
  ctx.fill();
  ctx.lineWidth = ow;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  for (let dy = 1; dy < th; dy += 1) {
    path(dy);
    ctx.fill();
  }
  path(0);
  ctx.fillStyle = C.top;
  ctx.fill();
  ctx.lineWidth = ow;
  ctx.strokeStyle = OUT;
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,0.18)";
  ctx.beginPath();
  ctx.ellipse(c.x - 0.8, top - 0.5, 1.2, 0.5, -0.2, 0, TAU);
  ctx.fill();
  if (c.wet) {
    let w = 0;
    let yb = -Infinity;
    for (const [px, py] of c.pts) {
      w = Math.max(w, Math.abs(px));
      yb = Math.max(yb, py);
    }
    const wl = top + yb * 0.15 + th * 0.5;
    ctx.save();
    ctx.beginPath();
    ctx.rect(c.x - w - 2, wl, 2 * w + 4, 12);
    ctx.clip();
    path(0);
    ctx.fillStyle = "rgba(69,98,122,0.4)";
    ctx.fill();
    path(th);
    ctx.fill();
    ctx.restore();
    line(ctx, [[c.x - w - 1.2, wl + 0.3], [c.x + w + 1.2, wl]], "rgba(215,236,250,0.5)", 0.9);
  }
}

/** 打破後的碎屑（表面裝飾層：水表面之上、單位之下）：舊井口的深水影＋10 塊泡在淺水裡的碎屑。`k` 預設 4（靜態）。 */
export function drawWellRubble(ctx: Ctx, s: { x: number; y: number }, k = 4): void {
  if (k >= 3) {
    ctx.fillStyle = "rgba(16,40,72,0.45)";
    ctx.beginPath();
    ctx.ellipse(G.cx, RUB_Y, 9, 5, 0, 0, TAU);
    ctx.fill();
  }
  for (const c of wellChunks(s, k)) drawChunk(ctx, c);
}

function drops(ctx: Ctx, list: ReadonlyArray<readonly [number, number, number]>): void {
  for (const [x, y, rad] of list) {
    ctx.beginPath();
    ctx.arc(x, y, rad, 0, TAU);
    ctx.fillStyle = C.waterHi;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
}

/**
 * 破壞演出「空中」那一層（物件層、那一排；座標仍是井那一格的 52 單位，會畫出格外）：
 * K0＝受損 2 的井白閃；K1＝碎塊往外飛＋中央冠狀水柱＋9 顆水珠；K2＝碎塊快落地＋8 個小水花＋7 顆水珠。K3 起沒有。
 */
export function drawWellBreakAir(ctx: Ctx, s: { x: number; y: number }, k: number): void {
  if (k === 0) {
    drawCoolingWell(ctx, { x: s.x, y: s.y, hpStage: 2, flash: true });
    return;
  }
  if (k > 2) return;
  for (const c of wellChunks(s, k)) drawChunk(ctx, c);
  const { cx } = G;
  const r = rng(s.x, s.y, 243);
  const cy = RUB_Y - 2;
  if (k === 1) {
    const pts: ReadonlyArray<readonly [number, number]> = [[-12, 0], [-11, -6], [-8, -3], [-6, -14], [-3, -7], [0, -20], [3, -8], [6, -15], [8, -4], [11, -8], [12, 0]];
    ctx.beginPath();
    pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(cx + x, cy + y) : ctx.lineTo(cx + x, cy + y)));
    ctx.ellipse(cx, cy, 12, 4, 0, 0, Math.PI, false);
    ctx.closePath();
    ctx.fillStyle = C.waterHi;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.lineJoin = "round";
    ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.7)";
    ctx.beginPath();
    ctx.moveTo(cx - 4, cy - 2);
    ctx.lineTo(cx - 1, cy - 14);
    ctx.lineTo(cx + 1, cy - 2);
    ctx.closePath();
    ctx.fill();
    const d: Array<[number, number, number]> = [];
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * TAU + r() * 0.4;
      const q = 17 + r() * 8;
      d.push([cx + Math.cos(a) * q, cy + Math.sin(a) * q * 0.55 - 10 - r() * 6, 1.8 + r() * 0.8]);
    }
    drops(ctx, d);
    return;
  }
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU + 0.2;
    const x = cx + Math.cos(a) * 30;
    const y = cy + Math.sin(a) * 17;
    ctx.beginPath();
    ctx.moveTo(x - 4, y);
    ctx.quadraticCurveTo(x, y - 7 - r() * 3, x + 4, y);
    ctx.closePath();
    ctx.fillStyle = C.waterHi;
    ctx.fill();
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
  const d: Array<[number, number, number]> = [];
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * TAU + r() * 0.5;
    const q = 38 + r() * 8;
    d.push([cx + Math.cos(a) * q, cy + Math.sin(a) * q * 0.55 - 3, 1.5 + r() * 0.5]);
  }
  drops(ctx, d);
}

/**
 * 破壞演出「地面」那一層（表面裝飾層：新水面之後、單位之前；座標是井那一格的 52 單位，畫到 3×3）：
 * K1～K3 遮罩邊一圈亮色水沫（`#8fd4ff`、寬 1.5、60%，只畫在 3×3 內）；K3 再加兩圈漣漪。`maskR`＝這一刻遮罩的半徑。
 */
export function drawWellBreakGround(ctx: Ctx, k: number, maskR: number): void {
  if (k < 1 || k > 3) return;
  ctx.save();
  ctx.beginPath();
  ctx.rect(-T, -T, 3 * T, 3 * T);
  ctx.clip();
  if (Number.isFinite(maskR) && maskR > 0) {
    ctx.beginPath();
    wellMaskPoints(maskR).forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
    ctx.closePath();
    ctx.strokeStyle = "rgba(143,212,255,0.6)";
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    ctx.stroke();
  }
  if (k === 3) {
    ctx.strokeStyle = "rgba(235,248,255,0.6)";
    ctx.lineWidth = 1.6;
    for (const q of [44, 74]) {
      ctx.beginPath();
      ctx.ellipse(G.cx, RUB_Y - 2, q, q * 0.92, 0, 0, TAU);
      ctx.stroke();
    }
  }
  ctx.restore();
}
