// 實地地圖上的標記（Phase 6C-8；美術 PM 代決 #58，docs/art/地圖標記.md、map-marks.png、sample/mapMarks.js）：
// 取代 6C-5 格子裡的「足／碑／火／！」文字方塊——事件「！」、營火、朋友腳印、留言石碑用東西自己的形狀畫；
// 敵人視野併成一塊（`regionBlobs.ts`，這裡只給樣式）；「誰在看」是敵群頭上的一個眼睛（潛行時半閉）。
// 全部程式繪製（C 手繪墨線，`inkStyle.ts`），沒有亂數；文字只出現在滑過的說明（`fieldModel.hoverText`）。
// 純函式（標記清單、腳印幾何、視野樣式、眼睛位置）可以在沒有 DOM 的測試裡跑；畫布繪製函式照樣張的座標（每格 48px）。
import { Texture } from "pixi.js";
import type { Pos } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import { TAU, type Ctx } from "./artDraw";
import { ellPts, ink, stroke } from "./inkStyle";

/** 樣張的格子邊長（和 `TILE_SIZE` 相同：48）。 */
export const MARK_T = 48;
/** 標記貼圖在格子四周多留的邊（光暈、浮在格子上方的泡泡）。 */
export const MARK_PAD = 16;
/** 標記貼圖的邊長（模型像素）。 */
export const MARK_SIZE = MARK_T + MARK_PAD * 2;
/** 標記貼圖的解析度倍率。 */
const MARK_RES = 3;

/** 「！」上下浮動的幅度（px）與週期（毫秒）。 */
export const EVENT_BOB_PX = 3;
export const EVENT_BOB_MS = 1600;

export type MapThing =
  | { kind: "event"; pos: Pos }
  | { kind: "campfire"; pos: Pos; lit: boolean }
  | { kind: "note_stone"; pos: Pos; unread: boolean }
  | { kind: "footprint"; pos: Pos; facing: "n" | "e" | "s" | "w"; alpha: number };

/** 敵群頭上的眼睛：`sneaking` ＝ 主角潛行中（眼睛半閉）。 */
export interface WatchEye {
  pos: Pos;
  sneaking: boolean;
}

// ---- 純函式 ----

/** 「！」這一刻的上下位移（px）：`t` 毫秒，週期 1.6 秒、幅度 3px。 */
export function eventBob(t: number): number {
  return Math.sin((t / EVENT_BOB_MS) * TAU) * EVENT_BOB_PX;
}

const DIR: Readonly<Record<"n" | "e" | "s" | "w", readonly [number, number]>> = { n: [0, -1], e: [1, 0], s: [0, 1], w: [-1, 0] };

/** 一個腳印的兩個橢圓（鞋尖、鞋跟），相對格子左上角的模型像素。 */
export interface PrintEllipse {
  cx: number;
  cy: number;
  rx: number;
  ry: number;
}

/**
 * 一格裡的兩步腳印（照樣張 `footprints`／`footprint`）：沿 `facing` 走，第一步在格子中心往後 1/4 格、第二步往前 1/4 格，
 * 左右腳交替（往兩側各偏 4.4px）；每步一個鞋尖橢圓（往前 3px）、一個鞋跟橢圓（往後 4.6px）。只有四個方向，所以橢圓不必旋轉，橫走時長短軸對調。
 */
export function footprintShapes(facing: "n" | "e" | "s" | "w", T = MARK_T): PrintEllipse[] {
  const [dx, dy] = DIR[facing];
  const side: [number, number] = [-dy, dx]; // 前進方向的右手邊
  const horizontal = dx !== 0;
  const out: PrintEllipse[] = [];
  for (let s = 0; s < 2; s++) {
    const f = s === 0 ? -0.25 : 0.25;
    const left = s === 0;
    const ox = T / 2 + dx * f * T + side[0] * (left ? -4.4 : 4.4);
    const oy = T / 2 + dy * f * T + side[1] * (left ? -4.4 : 4.4);
    const ell = (along: number, rAcross: number, rAlong: number): PrintEllipse => ({
      cx: ox + dx * along,
      cy: oy + dy * along,
      rx: horizontal ? rAlong : rAcross,
      ry: horizontal ? rAcross : rAlong,
    });
    out.push(ell(3, 3.2, 4.4), ell(-4.6, 2.5, 2.8));
  }
  return out;
}

/** 一位朋友的第 `i` 個腳印（共 `n` 個）的不透明度：越舊越淡（第一個最淡 0.4，最後一個 0.85）。 */
export function footprintAlpha(i: number, n: number): number {
  return 0.4 + 0.45 * (n <= 1 ? 1 : i / (n - 1));
}

/** 敵人視野的樣式（照樣張 `sightBlob`）：平常淡紅 0.20、外緣紅色虛線 [7, 4]；潛行時更淡 0.10、虛線更短更淡 [3, 5]。 */
export function sightStyle(sneaking: boolean): { fill: number; edge: number; edgeColor: number; dash: readonly [number, number] } {
  return sneaking ? { fill: 0.1, edge: 0.55, edgeColor: 0xff7864, dash: [3, 5] } : { fill: 0.2, edge: 0.9, edgeColor: 0xff6e5a, dash: [7, 4] };
}

/** 眼睛相對格子左上角（含抬高）的位置：敵群頭上（格子上緣再往上 18px），不放在格角。 */
export function eyeOffset(T = TILE_SIZE): { x: number; y: number } {
  return { x: T / 2, y: -18 };
}

// ---- 畫法（樣張 mapMarks.js，原點＝格子左上角）----

/** 事件「！」：浮在格子上方的金色泡泡，地上一圈淡金光。浮動另外由戰場做（`eventBob`），這裡畫在中間位置。 */
export function drawEventMark(ctx: Ctx, part: "ground" | "bubble" | "all" = "all"): void {
  const T = MARK_T;
  const cx = T / 2;
  const cy = T / 2;
  ctx.save();
  if (part !== "bubble") {
    const g = ctx.createRadialGradient(cx, cy + 10, 2, cx, cy + 10, 22);
    g.addColorStop(0, "rgba(255,210,58,0.45)");
    g.addColorStop(1, "rgba(255,210,58,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(cx, cy + 10, 22, 10, 0, 0, TAU);
    ctx.fill();
  }
  if (part !== "ground") {
    ctx.translate(cx, cy - 16);
    ink(ctx, "ev-bubble", [[-11, -12], [11, -12], [12, 6], [4, 7], [0, 13], [-4, 7], [-12, 6]], "#ffd23a", { w: 1 });
    ink(ctx, "ev-bar", [[-2.2, -8], [2.2, -8], [1.4, 1], [-1.4, 1]], "#3a2410", { shade: false, w: 0.4 });
    ctx.fillStyle = "#3a2410";
    ctx.beginPath();
    ctx.arc(0, 4, 1.8, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

/** 營火：一圈石頭＋交叉的柴＋火苗＋地上暖光；`lit` ＝ false 時只剩柴和灰（今天已經紮過營）。 */
export function drawCampfire(ctx: Ctx, lit = true): void {
  const T = MARK_T;
  const cx = T / 2;
  const cy = T * 0.62;
  ctx.save();
  if (lit) {
    const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, 30);
    g.addColorStop(0, "rgba(255,150,40,0.5)");
    g.addColorStop(1, "rgba(255,150,40,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(cx, cy, 30, 0, TAU);
    ctx.fill();
  }
  ctx.translate(cx, cy);
  for (let k = 0; k < 6; k++) {
    const a = (k / 6) * TAU;
    ink(ctx, `cf-stone${k}`, ellPts(Math.cos(a) * 13, Math.sin(a) * 6, 3.4, 2.6, 8), "#8a8a84", { w: 0.6 });
  }
  ink(ctx, "cf-log1", [[-11, 2], [9, -5], [11, -2], [-9, 5]], "#7a4e2a", { w: 0.8 });
  ink(ctx, "cf-log2", [[-9, -5], [11, 2], [9, 5], [-11, -2]], "#8a5a30", { w: 0.8 });
  if (lit) {
    ink(ctx, "cf-flame", [[-7, 0], [-5, -10], [-1, -7], [0, -17], [3, -8], [6, -12], [7, 0]], "#ff7a2a", { shade: false, w: 0.8 });
    ink(ctx, "cf-core", [[-3.5, 0], [-1.5, -6], [0, -9], [2, -5], [3.5, 0]], "#ffd23a", { shade: false, w: 0.4 });
  } else {
    ctx.fillStyle = "rgba(120,120,120,0.7)";
    ctx.beginPath();
    ctx.ellipse(0, 0, 6, 3, 0, 0, TAU);
    ctx.fill();
  }
  ctx.restore();
}

/** 留言石碑：直立的石板、三條刻線、一張釘著的紙；`unread` 時右上一個紅點。 */
export function drawStele(ctx: Ctx, unread = false): void {
  const T = MARK_T;
  const cx = T / 2;
  const by = T * 0.86;
  ctx.save();
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.beginPath();
  ctx.ellipse(cx, by, 14, 4, 0, 0, TAU);
  ctx.fill();
  ctx.translate(cx, by);
  ink(ctx, "st-base", [[-14, 0], [14, 0], [12, -6], [-12, -6]], "#7a7a74", { w: 0.8 });
  ink(ctx, "st-slab", [[-10, -6], [10, -6], [10, -30], [6, -36], [-6, -36], [-10, -30]], "#a8a8a0", { w: 1 });
  for (const y of [-28, -23, -18]) stroke(ctx, `st-l${y}`, [[-6, y], [6, y]], 0.8, "#6a6a64");
  ink(ctx, "st-note", [[-1, -16], [9, -18], [10, -8], [0, -6]], "#f2e6c8", { shade: false, w: 0.6 });
  ctx.fillStyle = "#c83a2a";
  ctx.beginPath();
  ctx.arc(5, -16, 1.4, 0, TAU);
  ctx.fill();
  if (unread) {
    ctx.beginPath();
    ctx.arc(11, -36, 4.5, 0, TAU);
    ctx.fillStyle = "#e04a3a";
    ctx.fill();
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = "#1c1712";
    ctx.stroke();
  }
  ctx.restore();
}

/** 敵群頭上的眼睛（原點＝眼睛中心）：白底紅瞳；`sneaking` ＝ 潛行時上眼皮蓋下來（半閉）。 */
export function drawWatchEye(ctx: Ctx, sneaking = false): void {
  ctx.save();
  ink(ctx, "eye-bg", [[-9, 0], [-4, -5], [4, -5], [9, 0], [4, 5], [-4, 5]], "#f2e6c8", { shade: false, w: 0.8 });
  ctx.fillStyle = "#c83a2a";
  ctx.beginPath();
  ctx.arc(0, 0, 3, 0, TAU);
  ctx.fill();
  if (sneaking) {
    ctx.fillStyle = "#3a3450";
    ctx.beginPath();
    ctx.moveTo(-9.5, 0.5);
    ctx.lineTo(-4, -5.5);
    ctx.lineTo(4, -5.5);
    ctx.lineTo(9.5, 0.5);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
}

// ---- 貼圖（每種狀態一張，全場共用；沒有 DOM 時 `null`）----

const textures = new Map<string, Texture>();

/** 標記貼圖：`MARK_SIZE` 見方，格子左上角在 (MARK_PAD, MARK_PAD)；`key` 決定快取。 */
function markTexture(key: string, draw: (ctx: Ctx) => void): Texture | null {
  if (typeof document === "undefined") return null;
  const hit = textures.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = MARK_SIZE * MARK_RES;
  canvas.height = MARK_SIZE * MARK_RES;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(MARK_RES, MARK_RES);
  ctx.translate(MARK_PAD, MARK_PAD);
  draw(ctx);
  const tex = Texture.from(canvas);
  textures.set(key, tex);
  return tex;
}

/** 腳印以外的標記貼圖；事件「！」分成地上的光（`event`）與浮動的泡泡（`event_bubble`）兩張。 */
export function thingTexture(thing: Exclude<MapThing, { kind: "footprint" }>, part: "main" | "bubble" = "main"): Texture | null {
  switch (thing.kind) {
    case "event":
      return part === "bubble" ? markTexture("event_bubble", (c) => drawEventMark(c, "bubble")) : markTexture("event", (c) => drawEventMark(c, "ground"));
    case "campfire":
      return markTexture(`campfire|${thing.lit ? 1 : 0}`, (c) => drawCampfire(c, thing.lit));
    case "note_stone":
      return markTexture(`stele|${thing.unread ? 1 : 0}`, (c) => drawStele(c, thing.unread));
  }
}

/** 眼睛貼圖（中心＝貼圖中心）。 */
export function eyeTexture(sneaking: boolean): Texture | null {
  return markTexture(`eye|${sneaking ? 1 : 0}`, (c) => {
    c.translate(MARK_T / 2, MARK_T / 2);
    drawWatchEye(c, sneaking);
  });
}
