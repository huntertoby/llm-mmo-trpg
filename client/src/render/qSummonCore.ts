// Q 版召喚物與形態共用的畫法層（QK-3；照 docs/art/sample/qSummon.js 的 H 與 qCreature.js 的 layer 改寫）。
// 平塗＋部件之間一條本色加深的細縫線（外輪廓由剪影外框負責）、整隻剪影外框 1.3 單位 #16121a、方眼＋高光。確定性：不用亂數。
// 沒有 DOM（vitest）時 layer 直接畫平塗、不做外框。
import type { Ctx } from "./artDraw";
import { mix } from "./qCore";

export const TAU = Math.PI * 2;
/** 剪影外框色（同 Q 版主角）。 */
export const OUT = "#16121a";
export type Pt = readonly [number, number];

export const dark = (c: string, t = 0.3): string => mix(c, "#000000", t);
export const light = (c: string, t = 0.3): string => mix(c, "#ffffff", t);
export { mix };

export function ellPts(cx: number, cy: number, rx: number, ry: number, n = 18): Pt[] {
  return Array.from({ length: n }, (_, i): Pt => [cx + Math.cos((i / n) * TAU) * rx, cy + Math.sin((i / n) * TAU) * ry]);
}

/** 中點二次曲線（圓潤，不抖）；closed＝false 畫開放曲線。 */
export function smooth(ctx: Ctx, pts: readonly Pt[], closed = true): void {
  ctx.beginPath();
  const n = pts.length;
  const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  if (n === 0) return;
  if (!closed) {
    ctx.moveTo(pts[0]![0], pts[0]![1]);
    for (let i = 1; i < n - 1; i++) {
      const m = mid(pts[i]!, pts[i + 1]!);
      ctx.quadraticCurveTo(pts[i]![0], pts[i]![1], m[0], m[1]);
    }
    ctx.lineTo(pts[n - 1]![0], pts[n - 1]![1]);
    return;
  }
  const m0 = mid(pts[n - 1]!, pts[0]!);
  ctx.moveTo(m0[0], m0[1]);
  for (let i = 0; i < n; i++) {
    const p = pts[i]!;
    const m = mid(p, pts[(i + 1) % n]!);
    ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
  }
  ctx.closePath();
}

export function poly(ctx: Ctx, pts: readonly Pt[]): void {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
}

export interface InkOpt {
  /** 直線多邊形（晶、石）。 */
  sharp?: boolean;
  /** false：不畫縫線。 */
  line?: boolean;
  w?: number;
}
/** 平塗一塊＋本色加深的細縫線。 */
export function ink(ctx: Ctx, pts: readonly Pt[], color: string, o: InkOpt = {}): void {
  ctx.save();
  if (o.sharp) poly(ctx, pts);
  else smooth(ctx, pts);
  ctx.fillStyle = color;
  ctx.fill();
  if (o.line !== false) {
    ctx.strokeStyle = mix(color, OUT, 0.55);
    ctx.lineWidth = o.w ?? 0.55;
    ctx.lineJoin = "round";
    ctx.stroke();
  }
  ctx.restore();
}

export function stroke(ctx: Ctx, pts: readonly Pt[], w = 0.7, color = OUT): void {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  smooth(ctx, pts, false);
  ctx.stroke();
  ctx.restore();
}

/** 四肢：一條深一點的粗線墊底＋本色線。 */
export function limb(ctx: Ctx, pts: readonly Pt[], w: number, color: string): void {
  stroke(ctx, pts, w + 1.1, mix(color, OUT, 0.55));
  stroke(ctx, pts, w, color);
}

export function dot(ctx: Ctx, x: number, y: number, rx: number, ry: number, c: string): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, TAU);
  ctx.fill();
}

/** 野獸的眼睛：圓角方眼＋方瞳＋高光。 */
export function beye(ctx: Ctx, x: number, y: number, col = "#ffd23a", r = 1): void {
  const s = r * 1.25;
  ctx.fillStyle = col;
  ctx.beginPath();
  ctx.roundRect(x - 1.15 * s, y - 1.25 * s, 2.3 * s, 2.5 * s, 0.7 * s);
  ctx.fill();
  ctx.fillStyle = OUT;
  ctx.fillRect(x - 0.2 * s, y - 0.95 * s, 1.0 * s, 1.9 * s);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(x + 0.15 * s, y - 0.85 * s, 0.45 * s, 0.45 * s);
}

/** 精靈、構造體的眼睛（同 qDoll 的方眼）：深色方塊＋一點高光。 */
export function qeye(ctx: Ctx, x: number, y: number, col = "#1d1a22", r = 1): void {
  ctx.fillStyle = col;
  ctx.beginPath();
  ctx.roundRect(x - 0.95 * r, y - 1.5 * r, 1.9 * r, 3 * r, 0.6 * r);
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(x - 0.6 * r, y - 1.2 * r, 0.6 * r, 0.6 * r);
}

/** 面向：ex＝眼睛的水平偏移；null＝背面（不畫臉）。 */
export interface Face {
  ex: number | null;
}

/** 地面影子：深色橢圓（Q 版平塗）。 */
export function groundShadow(ctx: Ctx, rx: number, y = 0.2, a = 0.3): void {
  ctx.fillStyle = `rgba(10,8,14,${a})`;
  ctx.beginPath();
  ctx.ellipse(0, y, rx, rx * 0.3, 0, 0, TAU);
  ctx.fill();
}

/** 以 (x, y) 為中心放大 s 倍畫（Q 大頭：以頸為中心放大）。 */
export function scaleAt(ctx: Ctx, x: number, y: number, s: number, fn: () => void): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.translate(-x, -y);
  fn();
  ctx.restore();
}

// ============================== 一層平塗＋剪影外框 ==============================
type C2 = CanvasRenderingContext2D;
const canDom = (): boolean => typeof document !== "undefined" && typeof document.createElement === "function";
function mkc(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return c;
}
function tint(src: HTMLCanvasElement, color: string): HTMLCanvasElement {
  const c = mkc(src.width, src.height);
  const g = c.getContext("2d")!;
  g.drawImage(src, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = color;
  g.fillRect(0, 0, c.width, c.height);
  return c;
}
/** 剪影膨脹 r（像素）：16 個方向 × 3 圈（同 qCreature.js）。 */
function dilate(src: HTMLCanvasElement, r: number, N = 16): HTMLCanvasElement {
  const c = mkc(src.width, src.height);
  const g = c.getContext("2d")!;
  for (const f of [1, 0.66, 0.33]) for (let i = 0; i < N; i++) g.drawImage(src, Math.cos((i / N) * TAU) * r * f, Math.sin((i / N) * TAU) * r * f);
  g.drawImage(src, 0, 0);
  return c;
}

export interface LayerOpt {
  /** 外框粗（目前座標系的單位，預設 1.3）。 */
  ow?: number;
  /** 整層透明度（藤蔓 0.9）。 */
  alpha?: number;
  /** [下緣 y, 開始淡出的 y]：分 3 段平塗淡出，本體和外框一起（暗影形態的下緣）。 */
  fade?: readonly [number, number];
}

/**
 * 在目前座標系的 box [x0, y0, x1, y1]（單位）裡畫一層：draw(g) 畫平塗部件，再整隻描剪影外框。
 * 離屏解析度跟著目前座標系的縮放（至少 3 倍取樣，免得外框糊成灰霧）；沒有 DOM 時直接畫、不描外框。
 */
export function layer(ctx: Ctx, box: readonly [number, number, number, number], draw: (g: Ctx) => void, o: LayerOpt = {}): void {
  if (!canDom()) {
    ctx.save();
    if (o.alpha !== undefined) ctx.globalAlpha = o.alpha;
    draw(ctx);
    ctx.restore();
    return;
  }
  const T = (ctx as { getTransform?: () => DOMMatrix }).getTransform?.();
  const k = T ? Math.hypot(T.a, T.b) : 1;
  const m = Math.min(24, Math.max(3, k * 2));
  const W = (box[2] - box[0]) * m;
  const H = (box[3] - box[1]) * m;
  const off = mkc(W, H);
  const g = off.getContext("2d") as C2;
  g.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m);
  draw(g);
  const ow = (o.ow ?? 1.3) * m;
  const rim = dilate(tint(off, OUT), ow);
  const rg = rim.getContext("2d")!;
  rg.globalCompositeOperation = "destination-out";
  rg.drawImage(off, 0, 0);
  if (o.fade) {
    const [yb, yt] = o.fade;
    for (const c of [off, rim]) {
      const q = c.getContext("2d")!;
      q.save();
      q.setTransform(m, 0, 0, m, -box[0] * m, -box[1] * m);
      q.globalCompositeOperation = "destination-out";
      [0.35, 0.65, 0.92].forEach((al, i) => {
        const y0 = yt + ((yb - yt) * i) / 3;
        const y1 = i === 2 ? box[3] : yt + ((yb - yt) * (i + 1)) / 3;
        q.globalAlpha = al;
        q.fillRect(box[0], y0, box[2] - box[0], y1 - y0);
      });
      q.restore();
    }
  }
  const bw = box[2] - box[0];
  const bh = box[3] - box[1];
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  const a = o.alpha ?? 1;
  ctx.globalAlpha = a < 1 ? Math.min(1, a + 0.2 * Math.min(1, a * 5)) : 1; // 外框比本體實一點
  ctx.drawImage(rim, box[0], box[1], bw, bh);
  ctx.globalAlpha = a;
  ctx.drawImage(off, box[0], box[1], bw, bh);
  ctx.restore();
}
