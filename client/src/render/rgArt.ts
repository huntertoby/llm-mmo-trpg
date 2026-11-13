// RG-3（#162）戰場標記的畫法：照樣張 `docs/art/sample/rgMarks.js`（第 2 版，只搬 A 強招紫）逐行搬成 canvas 2D。
// 準星、小盾、可疑痕跡（翻土＋「？」）、看一眼；線與點線用 Pixi Graphics 畫（`render/battle/rgMarkLayer.ts`）。
// 座標：每個函式的 (x, y) 是圖案中心（可疑痕跡是格子左上角），單位模型像素；呼叫端先把 ctx 換到要的解析度。
import { glanceFrame, type Pt } from "../battle/rgMarks";

const TAU = Math.PI * 2;
const INK = "#16121a";
const MAIN = "#b06bff";
const BLOCKED = "#b0b8c4";
const CREAM = "#f2e6c8";
const STEEL = "#c3ccd6";
const STEEL_D = "#7d8794";

type Ctx = CanvasRenderingContext2D;

/** 準星（樣張 `reticle`）：空心圓＋三根刻度＋朝下實心三角；`phase` 1＝收（縮 0.86、線細、沒有亮弧）；被擋時灰、不閃。 */
export function drawReticle(ctx: Ctx, x: number, y: number, phase: 0 | 1, blocked: boolean, k = 1): void {
  const dim = phase === 1 && !blocked;
  const col = blocked ? BLOCKED : MAIN;
  const s = dim ? 0.86 : 1;
  const R = 6.2;
  const lw = dim ? 2.2 : 2.6;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k * s, k * s);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const ticks: Array<[number, number]> = [[-1, 0], [1, 0], [0, -1]];
  const tri = () => {
    ctx.beginPath();
    ctx.moveTo(-4.2, R + 1.6);
    ctx.lineTo(4.2, R + 1.6);
    ctx.lineTo(0, R + 6.4);
    ctx.closePath();
  };
  const shape = () => {
    ctx.beginPath();
    ctx.arc(0, 0, R, 0, TAU);
    for (const [dx, dy] of ticks) {
      ctx.moveTo(dx * (R - 1.6), dy * (R - 1.6));
      ctx.lineTo(dx * (R + 3.4), dy * (R + 3.4));
    }
  };
  ctx.strokeStyle = INK;
  ctx.lineWidth = lw + 2;
  shape();
  ctx.stroke();
  tri();
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = INK;
  ctx.fill();
  ctx.strokeStyle = col;
  ctx.lineWidth = lw;
  shape();
  ctx.stroke();
  tri();
  ctx.fillStyle = col;
  ctx.fill();
  if (!dim && !blocked) {
    ctx.strokeStyle = "rgba(255,255,255,0.8)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(0, 0, R, Math.PI * 1.08, Math.PI * 1.42);
    ctx.stroke();
  }
  ctx.restore();
}

/** 小盾（樣張 `coverChip` 的 unit 版，第 2 版：沒有人頭）：鳶形盾 11.2×12.8、鋼色、右半暗、左亮條、金釘。 */
export function drawShieldChip(ctx: Ctx, x: number, y: number, k = 1): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.lineJoin = "round";
  const shield = () => {
    ctx.beginPath();
    ctx.moveTo(-5.6, -5.1);
    ctx.quadraticCurveTo(0, -6.8, 5.6, -5.1);
    ctx.lineTo(5.6, -0.2);
    ctx.quadraticCurveTo(5.1, 4.4, 0, 6.85);
    ctx.quadraticCurveTo(-5.1, 4.4, -5.6, -0.2);
    ctx.closePath();
  };
  shield();
  ctx.lineWidth = 2;
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.fillStyle = STEEL;
  ctx.fill();
  ctx.save();
  shield();
  ctx.clip();
  ctx.fillStyle = STEEL_D;
  ctx.fillRect(0.7, -8, 8, 16);
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.fillRect(-4.2, -3.6, 1.4, 5.4);
  ctx.restore();
  ctx.beginPath();
  ctx.arc(0.35, -0.5, 1.5, 0, TAU);
  ctx.fillStyle = "#e8bb48";
  ctx.fill();
  ctx.restore();
}

/** 可疑痕跡的地面（樣張 `trace` 第 2 版，不含「？」）：(x0, y0)＝格子左上角、`T`＝一格。形固定、不畫陷阱的種類。 */
export function drawTraceGround(ctx: Ctx, x0: number, y0: number, T = 48): void {
  const cx = x0 + T / 2;
  const cy = y0 + T / 2 + 4;
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const L0: [number, number] = [x0 + 5, y0 + T - 9];
  const L1: [number, number] = [cx - 9, cy + 3];
  const L2: [number, number] = [cx + 9, cy + 2];
  const L3: [number, number] = [x0 + T - 6, y0 + 22];
  const lines: Array<[[number, number], [number, number]]> = [[L0, L1], [L2, L3]];
  for (const [w, c] of [[2.2, "rgba(20,14,8,0.6)"], [1, "rgba(240,232,210,0.9)"]] as const) {
    ctx.strokeStyle = c;
    ctx.lineWidth = w;
    for (const [a, b] of lines) {
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]);
      ctx.lineTo(b[0], b[1]);
      ctx.stroke();
    }
  }
  const hx = cx + 7;
  const hy = cy + 4.5;
  ctx.beginPath();
  ctx.ellipse(hx, hy, 8, 3.6, 0, 0, TAU);
  ctx.fillStyle = "rgba(74,54,34,0.9)";
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(hx, hy + 0.6, 6.6, 2.6, 0, 0, TAU);
  ctx.fillStyle = "rgba(18,11,6,0.95)";
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(hx, hy + 0.2, 7.6, 3.3, 0, 0.12 * Math.PI, 0.88 * Math.PI);
  ctx.strokeStyle = "rgba(222,196,150,0.85)";
  ctx.lineWidth = 1.1;
  ctx.stroke();
  const top = () => {
    ctx.moveTo(cx - 15, cy + 4);
    ctx.quadraticCurveTo(cx - 17, cy - 2, cx - 11.5, cy - 4);
    ctx.quadraticCurveTo(cx - 9, cy - 10.5, cx - 3.5, cy - 7.5);
    ctx.quadraticCurveTo(cx + 1.5, cy - 7, cx + 1.5, cy - 2);
    ctx.quadraticCurveTo(cx + 5, cy - 1, cx + 4.5, cy + 3.5);
  };
  const heap = () => {
    ctx.beginPath();
    top();
    ctx.quadraticCurveTo(cx - 5, cy + 8, cx - 15, cy + 4);
    ctx.closePath();
  };
  heap();
  ctx.fillStyle = "rgba(128,96,62,0.97)";
  ctx.fill();
  ctx.save();
  heap();
  ctx.clip();
  ctx.fillStyle = "rgba(46,32,18,0.6)";
  ctx.beginPath();
  ctx.ellipse(cx - 4, cy + 7, 14, 4.8, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "rgba(232,208,164,0.85)";
  ctx.lineWidth = 1.8;
  ctx.translate(0.4, 1.1);
  ctx.beginPath();
  top();
  ctx.stroke();
  ctx.restore();
  heap();
  ctx.strokeStyle = "rgba(20,14,8,0.75)";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  for (const [x, y, rr] of [[cx + 17, cy + 1.5, 1.6], [cx + 15.5, cy + 8.5, 1.3]] as const) {
    ctx.beginPath();
    ctx.arc(x, y, rr + 0.6, 0, TAU);
    ctx.fillStyle = "rgba(20,14,8,0.5)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x, y, rr, 0, TAU);
    ctx.fillStyle = "#6a4c30";
    ctx.fill();
  }
  for (const [px, py] of [L0, L3]) {
    ctx.fillStyle = INK;
    ctx.fillRect(px - 1.6, py - 3.2, 3.2, 4.4);
    ctx.fillStyle = "#8a6440";
    ctx.fillRect(px - 0.9, py - 2.5, 1.8, 3);
  }
  ctx.restore();
}

/** 可疑痕跡右上的「？」小圓（半徑 6、米白底、深褐粗「?」）：(x, y)＝圓心。 */
export function drawTraceQuestion(ctx: Ctx, x: number, y: number, k = 1): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.beginPath();
  ctx.arc(0, 0, 6, 0, TAU);
  ctx.lineWidth = 2;
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.fillStyle = CREAM;
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.beginPath();
  ctx.arc(-2.4, -2.6, 1.2, 0, TAU);
  ctx.fill();
  ctx.fillStyle = "#3a2410";
  ctx.font = "900 10px 'Noto Sans TC','Microsoft JhengHei',sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("?", 0.2, 0.8);
  ctx.restore();
}

/** 「？」的圓心相對格子左上角（樣張：格子左上角＋(37, 11)）。 */
export const QUESTION_AT = { x: 37, y: 11 } as const;

/** 看一眼（樣張 `glance` 第 2 版）：(x, y)＝泡泡中心、`dir`＝往那一格的單位向量、`ms`＝0～600。 */
export function drawGlance(ctx: Ctx, x: number, y: number, dir: Pt, ms: number, k = 1, reduced = false): void {
  const f = glanceFrame(ms, reduced);
  const kk = k * f.scale;
  if (f.alpha <= 0) return;
  const d = Math.hypot(dir.x, dir.y) || 1;
  const ux = dir.x / d;
  const uy = dir.y / d;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(kk, kk);
  ctx.globalAlpha = f.alpha;
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(-5, -5.5);
  ctx.lineTo(5, -5.5);
  ctx.quadraticCurveTo(7, -5.5, 7, -3.5);
  ctx.lineTo(7, 2);
  ctx.quadraticCurveTo(7, 4, 5, 4);
  ctx.lineTo(2, 4);
  ctx.lineTo(0, 7);
  ctx.lineTo(-2, 4);
  ctx.lineTo(-5, 4);
  ctx.quadraticCurveTo(-7, 4, -7, 2);
  ctx.lineTo(-7, -3.5);
  ctx.quadraticCurveTo(-7, -5.5, -5, -5.5);
  ctx.closePath();
  ctx.lineWidth = 2;
  ctx.strokeStyle = INK;
  ctx.stroke();
  ctx.fillStyle = "#e8d6a8";
  ctx.fill();
  const mx = ux * 1.2 * f.look;
  const my = uy * 1.4 * f.look;
  for (const ex of [-2.7, 2.7]) {
    ctx.beginPath();
    ctx.ellipse(ex, -0.8, 2.5, 3.1, 0, 0, TAU);
    ctx.lineWidth = 0.8;
    ctx.strokeStyle = INK;
    ctx.stroke();
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(ex + mx, -0.8 + my, 1.35, 0, TAU);
    ctx.fillStyle = "#1c1410";
    ctx.fill();
  }
  if (f.sight > 0) {
    const bx = ux * 9.5;
    const by = uy * 8 - 0.8;
    const nx = -uy;
    const ny = ux;
    const L = 3.4 * f.sight;
    ctx.lineCap = "round";
    for (const s of [-1, 1]) {
      const sx = bx + nx * s * 2.4;
      const sy = by + ny * s * 2.4;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + ux * L, sy + uy * L);
      ctx.strokeStyle = INK;
      ctx.lineWidth = 2.6;
      ctx.stroke();
      ctx.strokeStyle = "#fff8e8";
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
  }
  ctx.restore();
}

/** 畫成畫布：`w`×`h` 模型像素、原點在 (`ox`, `oy`)（模型像素）、`res`＝每模型像素幾個畫布像素。沒有 DOM 時 null。 */
export function rgCanvas(w: number, h: number, ox: number, oy: number, res: number, paint: (ctx: Ctx) => void): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w * res));
  c.height = Math.max(1, Math.ceil(h * res));
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(res, res);
  ctx.translate(ox, oy);
  paint(ctx);
  return c;
}
