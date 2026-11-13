// 頭目部位的戰場畫法（PB-1e；美術移植需求 docs/art/頭目部位-移植需求.md 2.3、2.4、3.4～3.6；畫法照 docs/art/sample/bossParts.js 逐行搬）。
// - 頭頂部位小格（`partStripNode`）：HP 條正下方、共用黑底，800 寬只放大高度（`registerMark` 的重排，地圖縮放改變時重畫）；
//   朝南三角形跟著往下移（節點的 `pivot`，三角形本身照 `facingArrowPoly` 的基準位置畫）。
// - 選單滑過部位時的亮起（`partGlowCanvas`）：部位圖層（`partLayer.ts`）往外長的亮青白描邊＋外框色襯邊＋部位上 35% 同色；
//   氣海是一團柔光＋兩道逗號形氣痕（樣張 `glowQi`）。描邊用距離轉換（同被遮擋外框的 `sqDistTo`）＝圓盤膨脹。
// - 地上的掉落物（`debrisCanvas`）、破壞演出 5 格（`breakFxCanvas`）、「破」字記號。
import { Graphics } from "pixi.js";
import type { Facing } from "../api/types";
import type { PartBarState } from "../battle/partMenu";
import { HP_H, HP_W, HP_Y, STRIP, STRIP_COLOR, STRIP_X_INK, STRIP_X_LINE, stripBars, stripLayout, type PartDraw, type PartFx, type StripLayout } from "../battle/partStrip";
import type { DollSpec } from "./appearance";
import { FONT } from "./labels";
import { FACING_ARROW_LABEL, MIN_BREAK_POP_FONT_PX, minMarkScale, PART_STRIP_LABEL, registerMark, SOUTH_ARROW_LABEL } from "./minMark";
import { sqDistTo } from "./occludeOutline";
import { DOLL_FOOT_Y, DOLL_H, DOLL_W } from "./paperdoll";
import { bellyPx, PART_KIND, renderPartLayer, tpM, type FigureFrame } from "./partLayer";
import type { M6 } from "./qCore";
import { drawCreatureFx } from "./qCreatureAnim";
import { SWORD_BRK } from "./qWeapons";

type C2 = CanvasRenderingContext2D;
const TAU = Math.PI * 2;
const OUT = "#16121a";
/** 人物貼圖的畫布（同 `paperdoll.renderFigureCanvas`）。 */
export const FIGURE: FigureFrame = { w: DOLL_W, h: DOLL_H, footY: DOLL_FOOT_Y };

function blank(w: number, h: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(w));
  c.height = Math.max(1, Math.round(h));
  return c;
}

// ---- 頭頂部位小格 ----------------------------------------------------------------

/** 樣張的基準（1600 寬以上：條高 2.6、「×」5.6 不放大）；三角形的基準位置照它算。 */
export const STRIP_BASE_SCALE = 10;

/** 一條部位條畫到 Graphics（模型 px）。 */
function drawBar(g: Graphics, x: number, y: number, L: StripLayout, st: PartBarState): void {
  if (st.kind === "hidden") {
    g.rect(x, y, L.w, L.h).fill(STRIP_COLOR.hidden);
    return;
  }
  if (st.kind === "broken") {
    g.rect(x, y, L.w, L.h).fill(STRIP_COLOR.broken);
    return;
  }
  g.rect(x, y, L.w, L.h).fill(STRIP_COLOR.empty);
  const r = st.max <= 0 ? 0 : Math.max(0, Math.min(1, st.hp / st.max));
  if (r > 0) g.rect(x, y, L.w * r, L.h).fill(STRIP_COLOR.ok);
}

/** 已破壞的紅「×」（外框色襯邊、比條高；最後畫，蓋到上下黑邊）。 */
function drawX(g: Graphics, cx: number, cy: number, L: StripLayout): void {
  const r = L.xs / 2;
  for (const [color, w] of [
    [STRIP_COLOR.ink, STRIP_X_LINE * L.k + STRIP_X_INK * L.k],
    [STRIP_COLOR.x, STRIP_X_LINE * L.k],
  ] as const) {
    g.moveTo(cx - r, cy - r).lineTo(cx + r, cy + r).moveTo(cx + r, cy - r).lineTo(cx - r, cy + r).stroke({ width: w, color, cap: "round" });
  }
}

/** 整條部位小格（黑底從 HP 條下緣接著往下）。 */
export function drawStrip(g: Graphics, bars: readonly PartBarState[], L: StripLayout): void {
  g.clear();
  g.rect(-HP_W / 2, HP_Y + HP_H, HP_W, L.bottom - (HP_Y + HP_H)).fill(0x000000);
  bars.forEach((st, i) => drawBar(g, L.x0 + i * (L.w + STRIP.gap), L.top, L, st));
  bars.forEach((st, i) => {
    if (st.kind === "broken") drawX(g, L.x0 + i * (L.w + STRIP.gap) + L.w / 2, L.top + L.h / 2, L);
  });
}

/**
 * 頭頂部位小格的節點（`PART_STRIP_LABEL`，跟著 HP 條掛同一層）。地圖縮放改變時（`applyMarkScale` 的重排）照新縮放重畫，
 * 朝南三角形（`southMoved`）跟著部位條的下緣往下挪。
 */
export function partStripNode(parts: readonly PartDraw[], hiddenInfo: boolean, fx: PartFx | undefined, hudDy: number, southMoved: boolean, arrowAt?: (boardScale: number) => number[]): Graphics {
  const g = new Graphics();
  g.label = PART_STRIP_LABEL;
  g.position.y = hudDy;
  const bars = stripBars(parts, hiddenInfo, fx);
  const base = stripLayout(bars.length, STRIP_BASE_SCALE).bottom;
  const draw = (boardScale: number): void => {
    const L = stripLayout(bars.length, boardScale);
    drawStrip(g, bars, L);
    if (!southMoved) return;
    const arrow = g.parent?.children.find((n) => n.label === SOUTH_ARROW_LABEL || n.label === FACING_ARROW_LABEL);
    if (arrow === undefined) return;
    arrow.pivot.y = -(L.bottom - base);
    // PB-1f：南邊有人時朝南三角形的大小也看縮放（`facingArrowPoly` 的第二個參數；800 寬不縮 0.6）
    if (arrowAt !== undefined && arrow instanceof Graphics) arrow.clear().poly(arrowAt(boardScale)).fill(0xffffff).stroke({ width: 1, color: 0x000000 });
  };
  draw(STRIP_BASE_SCALE);
  registerMark(g, { base: 1, min: 0 }, [], (_k, boardScale) => draw(boardScale));
  return g;
}

// ---- 選單滑過部位的亮起 -------------------------------------------------------------

/** 亮起（模型 px；樣張 `HOVER`）。 */
export const HOVER = { color: "#a8f4ff", ink: OUT, width: 1.4, inkW: 0.9, fill: 0.35 } as const;

const rgbOf = (hex: string): [number, number, number] => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
const clamp01 = (v: number): number => (v <= 0 ? 0 : v >= 1 ? 1 : v);

/**
 * 亮起的像素（純函式）：`alpha`＝部位圖層每個像素的透明度；部位外 `width` 內是亮青白、再往外 `ink` 是外框色（像素中心到輪廓的距離，
 * 邊緣 1 px 線性過渡）；部位上是 `fill` 的同色。回傳 RGBA。
 */
export function glowRgba(alpha: ArrayLike<number>, w: number, h: number, width: number, ink: number, fill = HOVER.fill, color = HOVER.color, inkColor = HOVER.ink): Uint8ClampedArray {
  const bits = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) bits[i] = (alpha[i] ?? 0) >= 128 ? 1 : 0;
  const dout = sqDistTo(bits, w, h, 1);
  const [cr, cg, cb] = rgbOf(color);
  const [ir, ig, ib] = rgbOf(inkColor);
  const out = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) {
    const o = i * 4;
    if (bits[i] === 1) {
      out[o] = cr;
      out[o + 1] = cg;
      out[o + 2] = cb;
      out[o + 3] = Math.round(255 * fill);
      continue;
    }
    const d = Math.sqrt(dout[i] as number) - 0.5;
    const cc = clamp01(width + 0.5 - d);
    const ic = clamp01(width + ink + 0.5 - d);
    if (ic <= 0) continue;
    const t = cc / ic;
    out[o] = Math.round(ir + (cr - ir) * t);
    out[o + 1] = Math.round(ig + (cg - ig) * t);
    out[o + 2] = Math.round(ib + (cb - ib) * t);
    out[o + 3] = Math.round(255 * ic);
  }
  return out;
}

/** 氣海的亮起（樣張 `glowQi`）：一團柔光（半徑 7.5、漸淡、不描外框）＋兩道逗號形的亮青白氣痕（外框色襯底）。單位＝紙娃娃單位。 */
function glowQi(c: C2, x: number, y: number, s: number): void {
  const g = c.createRadialGradient(x, y, 0, x, y, 7.5 * s);
  g.addColorStop(0, "rgba(232,252,255,0.75)");
  g.addColorStop(0.4, "rgba(168,244,255,0.45)");
  g.addColorStop(1, "rgba(168,244,255,0)");
  c.fillStyle = g;
  c.beginPath();
  c.arc(x, y, 7.5 * s, 0, TAU);
  c.fill();
  c.lineCap = "round";
  const arcs = (): void => {
    for (const a0 of [-0.5, Math.PI - 0.5]) {
      c.beginPath();
      c.arc(x, y, 3.6 * s, a0, a0 + 1.9);
      c.stroke();
      c.beginPath();
      c.moveTo(x + Math.cos(a0 + 1.9) * 3.6 * s, y + Math.sin(a0 + 1.9) * 3.6 * s);
      c.quadraticCurveTo(x + Math.cos(a0 + 2.5) * 2.4 * s, y + Math.sin(a0 + 2.5) * 2.4 * s, x + Math.cos(a0 + 2.9) * 1.2 * s, y + Math.sin(a0 + 2.9) * 1.2 * s);
      c.stroke();
    }
  };
  c.strokeStyle = HOVER.ink;
  c.lineWidth = (HOVER.width + HOVER.inkW * 2) * s;
  arcs();
  c.strokeStyle = HOVER.color;
  c.lineWidth = HOVER.width * s;
  arcs();
}

/**
 * 亮起的畫布（和人物貼圖同一個畫布座標：`FIGURE` × `res`，貼法同身體）。`k`＝1 紙娃娃單位幾個模型 px（`dollPx`）。
 * 沒有 DOM、或這個部位畫不出來時 `null`。
 */
export function partGlowCanvas(spec: DollSpec, facing: Facing, part: string, res: number, k: number): HTMLCanvasElement | null {
  if (part === "dantian") {
    const cv = blank(FIGURE.w * res, FIGURE.h * res);
    const c = cv?.getContext("2d") ?? null;
    if (cv === null || c === null) return null;
    const [x, y] = bellyPx(facing, res, FIGURE);
    glowQi(c, x, y, res);
    return cv;
  }
  if (PART_KIND[part] === undefined) return null;
  const layer = renderPartLayer(spec, facing, part, res, FIGURE);
  if (layer === null) return null;
  const { canvas } = layer;
  const g = canvas.getContext("2d");
  if (g === null) return null;
  const img = g.getImageData(0, 0, canvas.width, canvas.height);
  const n = canvas.width * canvas.height;
  const alpha = new Uint8Array(n);
  for (let i = 0; i < n; i++) alpha[i] = img.data[i * 4 + 3] ?? 0;
  const px = res / Math.max(0.01, k); // 畫布 px／模型 px
  const rgba = glowRgba(alpha, canvas.width, canvas.height, HOVER.width * px, HOVER.inkW * px);
  const out = blank(canvas.width, canvas.height);
  const o = out?.getContext("2d") ?? null;
  if (out === null || o === null) return null;
  const data = o.createImageData(canvas.width, canvas.height);
  data.data.set(rgba);
  o.putImageData(data, 0, 0);
  return out;
}

// ---- 部位的位置 -----------------------------------------------------------------

/** 部位中心（樣張 `centerOf`；拂塵＝武器座標 (−3, −3)、長劍 (0, −12)、氣海＝腹部）。回傳模型 px、相對腳底；畫不出來時 `null`。 */
export function partCenter(spec: DollSpec, facing: Facing, part: string, k: number): { x: number; y: number } | null {
  const toFeet = (px: number, py: number): { x: number; y: number } => ({ x: (px - FIGURE.w / 2) * k, y: (py - FIGURE.footY) * k });
  if (part === "dantian") {
    const [x, y] = bellyPx(facing, 1, FIGURE);
    return toFeet(x, y);
  }
  const m = partMatrix(spec, facing, part);
  if (m === null) return null;
  const [x, y] = part === "sword" ? tpM(m, 0, -12) : tpM(m, -3, -3);
  return toFeet(x, y);
}

/** 部位那件手持物的變換（紙娃娃單位、畫布座標，res 1）。 */
function partMatrix(spec: DollSpec, facing: Facing, part: string): M6 | null {
  const kind = PART_KIND[part];
  if (kind === undefined) return null;
  return renderPartLayer(spec, facing, part, 1, FIGURE)?.mats[kind] ?? null;
}

/** 手持物座標 → 模型 px（相對腳底）。 */
export function weaponToFeet(spec: DollSpec, facing: Facing, part: string, k: number): M6 | null {
  const m = partMatrix(spec, facing, part);
  if (m === null) return null;
  return { a: m.a * k, b: m.b * k, c: m.c * k, d: m.d * k, e: (m.e - FIGURE.w / 2) * k, f: (m.f - FIGURE.footY) * k };
}

// ---- 地上的掉落物 ----------------------------------------------------------------

/** 先畫外框色的粗描邊再填色（Q 版「剪影往外長一圈」的簡化；樣張 `outlined`）。 */
function outlined(c: C2, path: (c: C2) => void, fillFn: (c: C2) => void, w: number): void {
  c.save();
  c.strokeStyle = OUT;
  c.lineWidth = w * 2;
  c.lineJoin = "round";
  path(c);
  c.stroke();
  c.restore();
  fillFn(c);
}

/** 拂塵的毛（qNpcHeld 的 whisk 原樣；飛出去的那一撮用）。 */
export function tuftPath(c: C2): void {
  c.beginPath();
  c.moveTo(-0.9, -7);
  c.quadraticCurveTo(-5.6, -7.6, -6.4, 1.6);
  c.quadraticCurveTo(-4.6, 3.2, -3.2, 0.6);
  c.quadraticCurveTo(-2.4, -4.4, 0.9, -6.6);
  c.closePath();
}

/** 斷下的劍尖的輪廓（武器座標：刃的上半＋鋸齒斷口）。 */
function tipPath(c: C2): void {
  c.beginPath();
  c.moveTo(-1.3, -16);
  c.lineTo(0, -19);
  c.lineTo(1.3, -16);
  for (let i = SWORD_BRK.length - 1; i >= 0; i--) c.lineTo(SWORD_BRK[i]![0], SWORD_BRK[i]![1]);
  c.closePath();
}

/** 斷下的劍尖（鋼色照 qDoll 的 steel、亮線照 sword() 的白 45%）。 */
function swordTip(c: C2): void {
  c.fillStyle = "#c3ccd6";
  tipPath(c);
  c.fill();
  c.fillStyle = "rgba(255,255,255,0.45)";
  c.fillRect(-0.7, -16, 0.9, 6);
}

/** 地上一撮白毛（橫躺的一束，左端剪口灰、右端散成三綹；樣張 `clumpPath`）。 */
function clumpPath(c: C2): void {
  c.beginPath();
  c.moveTo(-5.8, -1.3);
  c.bezierCurveTo(-1.6, -3.4, 3.6, -3.4, 6.6, -1.9);
  c.lineTo(5.0, -0.9);
  c.lineTo(7.0, 0.1);
  c.lineTo(5.0, 0.9);
  c.lineTo(6.4, 2.1);
  c.bezierCurveTo(2.6, 2.7, -1.6, 2.4, -5.8, 1.5);
  c.closePath();
}

function fallenTuft(c: C2, fx: number, fy: number, s: number, flip: boolean): void {
  c.save();
  c.translate(fx, fy);
  c.scale(s, s);
  if (flip) c.scale(-1, 1);
  outlined(
    c,
    clumpPath,
    (g) => {
      g.fillStyle = "#f2f0ea";
      clumpPath(g);
      g.fill();
      g.save();
      clumpPath(g);
      g.clip();
      g.fillStyle = "#c8c4b8";
      g.fillRect(-7, 0.6, 15, 3);
      g.fillStyle = "#ffffff";
      g.fillRect(-3, -2.5, 6.5, 0.8);
      g.strokeStyle = "#c8c4b8";
      g.lineWidth = 0.45;
      g.beginPath();
      g.moveTo(-3, -0.4);
      g.quadraticCurveTo(1.6, -0.9, 5, -0.3);
      g.stroke();
      g.restore();
      g.fillStyle = "#a8a296";
      g.beginPath();
      g.ellipse(-5.6, 0.1, 0.8, 1.4, 0, 0, TAU);
      g.fill();
    },
    1.1,
  );
  c.restore();
}

function fallenTip(c: C2, fx: number, fy: number, s: number, rot: number): void {
  c.save();
  c.translate(fx, fy);
  c.scale(s, s);
  c.rotate(rot);
  c.translate(0, 14.5);
  outlined(c, tipPath, swordTip, 1.1);
  c.restore();
}

/** 掉落物畫布的範圍（模型 px、相對腳底）。 */
export const DEBRIS_BOX = { x: -26, y: -10, w: 52, h: 20 } as const;

/**
 * 頭目腳下的掉落物（樣張 `debris`）：劍尖在畫面左（主手那側）、白毛在右；朝西左右對調。`k`＝紙娃娃單位→模型 px，`res`＝畫布 px／模型 px。
 */
export function debrisCanvas(whisk: boolean, sword: boolean, west: boolean, k: number, res: number): HTMLCanvasElement | null {
  const cv = blank(DEBRIS_BOX.w * res, DEBRIS_BOX.h * res);
  const c = cv?.getContext("2d") ?? null;
  if (cv === null || c === null) return null;
  c.scale(res, res);
  c.translate(-DEBRIS_BOX.x, -DEBRIS_BOX.y);
  const sd = west ? -1 : 1;
  if (sword) fallenTip(c, -10.5 * sd, 2.6, k, west ? -1.25 : 1.25);
  if (whisk) fallenTuft(c, 11 * sd, 1.4, k, west);
  return cv;
}

// ---- 破壞演出 -------------------------------------------------------------------

/** 5 格的時間（毫秒，正常速度；紀錄 3.6）：命中白閃、裂開、斷開、落地，之後定格。 */
export const BREAK_FRAMES_MS = [80, 80, 160, 160] as const;
export const BREAK_MS = BREAK_FRAMES_MS.reduce((a, b) => a + b, 0);

/** 第幾格（0 命中、1 裂開、2 斷開、3 落地、4 定格）。`ms`＝正常速度的毫秒。 */
export function breakFrameAt(ms: number): 0 | 1 | 2 | 3 | 4 {
  let acc = 0;
  for (let i = 0; i < BREAK_FRAMES_MS.length; i++) {
    acc += BREAK_FRAMES_MS[i]!;
    if (ms < acc) return i as 0 | 1 | 2 | 3;
  }
  return 4;
}

/** 這一格人物要怎麼蓋過（`PartFx`）；落地以後回到伺服器給的樣子（`null`）。 */
export function breakFxOf(part: string, frame: number): PartFx | null {
  return frame === 0 ? { part, k: "flash" } : frame === 1 ? { part, k: "crack" } : frame === 2 ? { part, k: "fly" } : null;
}

/** 「破」相對部位中心的位置（模型 px；紀錄 12.2）：拂塵、劍在各自那一側的正上方；氣海在腰的外側同高。朝西左右對調。 */
export const BREAK_POP: Readonly<Record<string, readonly [number, number]>> = { whisk: [3, -14], sword: [-3, -15], dantian: [15, -2] };
/** 「破」記號（預告格一字記號的樣式放大：黑圓 72%、外圈紅、字亮黃）。 */
export const POP_STYLE = { r: 10, font: 14, ring: "#ff5a4a", ringW: 1.5, fill: "rgba(0,0,0,0.72)", text: "#ffd23f" } as const;

/** PB-1f：`k`＝整個記號的等比倍率（`popScale`；圓心位置照模型 px，不跟著放大）。 */
function pop(c: C2, x: number, y: number, a: number, k: number): void {
  c.save();
  c.globalAlpha = a;
  c.beginPath();
  c.arc(x, y, POP_STYLE.r * k, 0, TAU);
  c.fillStyle = POP_STYLE.fill;
  c.fill();
  c.lineWidth = POP_STYLE.ringW * k;
  c.strokeStyle = POP_STYLE.ring;
  c.stroke();
  c.font = `bold ${POP_STYLE.font * k}px ${FONT}`;
  c.textAlign = "center";
  c.textBaseline = "middle";
  c.fillStyle = POP_STYLE.text;
  c.fillText("破", x, y + 0.5 * k);
  c.restore();
}

/**
 * PB-1f（美術 PM PB-1e 驗收裁定待決 5）：「破」字在畫面上至少 `MIN_BREAK_POP_FONT_PX`（12 px），整個記號等比放大：
 * 倍率 max(1, 12 ／ (14 × 地圖縮放))；800 寬（0.53）約 ×1.62，1600 寬（1.31）是 1。
 */
export function popScale(boardScale: number): number {
  return minMarkScale(POP_STYLE.font, MIN_BREAK_POP_FONT_PX, boardScale);
}

/** 破壞演出畫布的範圍（模型 px、相對腳底）。 */
export const BREAK_BOX = { x: -48, y: -84, w: 96, h: 104 } as const;

export interface BreakFxIn {
  part: string;
  /** 0～3（定格沒有特效）。 */
  frame: number;
  /** 部位中心（模型 px、相對腳底）。 */
  center: { x: number; y: number };
  /** 手持物座標 → 模型 px（相對腳底）；氣海、畫不出來時 `null`。 */
  weapon: M6 | null;
  west: boolean;
  /** PB-1f：「破」記號的等比倍率（`popScale`）；沒給是 1。 */
  popK?: number;
}

/** 一格演出的特效（模型 px；`res`＝畫布 px／模型 px）。用現有的 burst、shard、dust、ring、puff（`drawCreatureFx`）。 */
export function breakFxCanvas(f: BreakFxIn, res: number): HTMLCanvasElement | null {
  const cv = blank(BREAK_BOX.w * res, BREAK_BOX.h * res);
  const c = cv?.getContext("2d") ?? null;
  if (cv === null || c === null) return null;
  c.scale(res, res);
  c.translate(-BREAK_BOX.x, -BREAK_BOX.y);
  const { part, frame, center } = f;
  const sd = f.west ? -1 : 1;
  const qi = part === "dantian";
  const D = (list: Parameters<typeof drawCreatureFx>[1]): void => {
    c.save();
    c.translate(center.x, center.y);
    drawCreatureFx(c, list, undefined, [-30, -30, 30, 30]);
    c.restore();
  };
  const [px, py] = BREAK_POP[part] ?? [0, -14];
  if (frame === 0) D([{ k: "burst", x: 0, y: 0, r: 7, c: "#ffffff", c2: "#ffe08a", a: 1 }]);
  if (frame === 1) {
    const sc = qi ? "#8ff0e0" : part === "sword" ? "#c3ccd6" : "#f2f0ea";
    D([
      { k: "burst", x: 0, y: 0, r: 5, c: "#ffe08a", c2: "#ffffff", a: 0.8 },
      ...([
        [-6, -4, 0.6],
        [6, -5, -0.8],
        [5, 4, 2.2],
      ] as const).map(([x, y, rot]) => ({ k: "shard" as const, x: x * sd, y, rot: rot * sd, s: 1.6, c: sc })),
    ]);
  }
  if (frame === 2) {
    D([
      { k: "burst", x: 0, y: 0, r: 11, c: qi ? "#8ff0e0" : "#ffd23f", c2: "#ffffff", a: 1 },
      { k: "ring", x: 0, y: 0, rx: 13, c: qi ? "#a8f4ff" : "#ffe08a", w: 1.4 },
    ]);
    const m = f.weapon;
    if (m !== null && part === "whisk") {
      c.save();
      c.transform(m.a, m.b, m.c, m.d, m.e, m.f);
      c.translate(3, -10);
      c.rotate(-0.7);
      c.strokeStyle = OUT;
      c.lineWidth = 2.2;
      c.lineJoin = "round";
      tuftPath(c);
      c.stroke();
      c.fillStyle = "#f2f0ea";
      tuftPath(c);
      c.fill();
      c.restore();
    }
    if (m !== null && part === "sword") {
      c.save();
      c.transform(m.a, m.b, m.c, m.d, m.e, m.f);
      c.translate(4, -6);
      c.rotate(0.9);
      c.translate(0, 4);
      c.strokeStyle = OUT;
      c.lineWidth = 2.2;
      c.lineJoin = "round";
      c.beginPath();
      c.moveTo(-1.3, -16);
      c.lineTo(0, -19);
      c.lineTo(1.3, -16);
      c.lineTo(1.3, -10);
      c.lineTo(-1.3, -10);
      c.closePath();
      c.stroke();
      swordTip(c);
      c.restore();
    }
    if (qi)
      D([
        { k: "puff", x: -9, y: -2, r: 3.4, c: "#e6f6f4" },
        { k: "puff", x: 9, y: -1, r: 3, c: "#e6f6f4" },
        { k: "puff", x: 0, y: -9, r: 2.6, c: "#e6f6f4" },
      ]);
    pop(c, center.x + px * sd, center.y + py, 1, f.popK ?? 1);
  }
  if (frame === 3) {
    const dust = (x: number, y: number): void => {
      c.save();
      c.translate(x, y);
      drawCreatureFx(c, [{ k: "dust", x: 0, y: 0, r: 4, c: "#cfc8b6", a: 1 }], undefined, [-20, -20, 20, 20]);
      c.restore();
    };
    if (part === "whisk") dust(11 * sd, 2);
    if (part === "sword") dust(-10.5 * sd, 3);
    if (qi)
      D([
        { k: "puff", x: -12, y: -4, r: 2.6, c: "#e6f6f4", a: 0.6 },
        { k: "puff", x: 12, y: -3, r: 2.2, c: "#e6f6f4", a: 0.6 },
      ]);
    pop(c, center.x + px * sd, center.y + py - 3, 0.55, f.popK ?? 1);
  }
  return cv;
}
