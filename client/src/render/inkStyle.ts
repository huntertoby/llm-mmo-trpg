// C 手繪墨線繪本畫法層（Phase C-1a；移植自美術 PM 樣張 docs/art/sample/storyDoll.js 的「畫法層」，需求 docs/art/C畫風移植需求.md 第 1 節）。
// ink() ＝ 水彩填色（略溢出、邊緣深一圈）＋暗面斜排線＋兩次抖動墨線；stroke() ＝ 開放的抖動線。
// 確定性：抖動的亂數種子 ＝ 部件名稱 key 的 FNV-1a 雜湊，再用 LCG；禁止 Math.random()，同一部件每次重畫完全一樣。
import { TAU, type Ctx } from "./artDraw";
import { MATERIAL } from "./material";

export const INK = "#2b1e16";

/** 二維點 [x, y]。 */
export type Pt = readonly [number, number];

/** 部件名稱 → 32 位元種子（FNV-1a）。 */
export function seedOf(s: string): number {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ (ch.codePointAt(0) ?? 0), 16777619);
  return h >>> 0;
}

/** 線性同餘亂數（回傳 [0, 1)）；同一個種子永遠產生同一串數字。 */
export function lcg(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** 橢圓取點（n 個點）。 */
export function ellPts(cx: number, cy: number, rx: number, ry: number, n = 18): Pt[] {
  return Array.from({ length: n }, (_, i): Pt => [cx + Math.cos((i / n) * TAU) * rx, cy + Math.sin((i / n) * TAU) * ry]);
}

/** 每個點隨機抖動 ±amt/2。 */
export function wobble(pts: readonly Pt[], r: () => number, amt: number): Pt[] {
  return pts.map(([x, y]): Pt => [x + (r() - 0.5) * amt, y + (r() - 0.5) * amt]);
}

const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

/** 用中點二次曲線把折線圓滑化（closed ＝ 封閉形狀）。 */
export function smooth(ctx: Ctx, pts: readonly Pt[], closed = true): void {
  ctx.beginPath();
  const n = pts.length;
  const first = pts[0];
  const last = pts[n - 1];
  if (first === undefined || last === undefined) return;
  if (!closed) {
    ctx.moveTo(first[0], first[1]);
    for (let i = 1; i < n - 1; i++) {
      const p = pts[i]!;
      const m = mid(p, pts[i + 1]!);
      ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
    }
    ctx.lineTo(last[0], last[1]);
    return;
  }
  const m0 = mid(last, first);
  ctx.moveTo(m0[0], m0[1]);
  for (let i = 0; i < n; i++) {
    const p = pts[i]!;
    const m = mid(p, pts[(i + 1) % n]!);
    ctx.quadraticCurveTo(p[0], p[1], m[0], m[1]);
  }
  ctx.closePath();
}

function outline(ctx: Ctx, pts: readonly Pt[], sharp: boolean | undefined): void {
  if (sharp !== true) {
    smooth(ctx, pts);
    return;
  }
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i > 0 ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.closePath();
}

/** 視角：正面、背面、側面（東；西由呼叫端左右鏡像）。小人、裝備、種族部件共用。 */
export type View = "front" | "back" | "side";

/** 暗面方向：1 ＝ 暗面在右（正面，光從左上）；-1 ＝ 暗面在左（側面朝東、背面）。 */
export type ShadeDir = 1 | -1;

/**
 * 暗面方向跟著畫布走（Phase 3T-4：原本是模組變數，畫出來的樣子取決於「上一個畫的是誰」）。
 * 沒有指定的畫布一律 1；要改方向請用 `withShadeDir`，它在結束時還原，所以呼叫順序不影響結果。
 * 貼圖快取鍵已含朝向（暗面方向由朝向決定），不需另外加。
 */
const shadeDirs = new WeakMap<object, ShadeDir>();

/** 在 `fn` 執行期間把 `ctx` 的暗面方向設成 `dir`，結束時還原（含例外）。 */
export function withShadeDir<T>(ctx: Ctx, dir: ShadeDir, fn: () => T): T {
  const before = shadeDirs.get(ctx);
  shadeDirs.set(ctx, dir);
  try {
    return fn();
  } finally {
    if (before === undefined) shadeDirs.delete(ctx);
    else shadeDirs.set(ctx, before);
  }
}

export interface InkOpt {
  /** 墨線寬（預設 0.85；第二次描線為 0.45 倍）。 */
  w?: number;
  /** false ＝ 不畫暗面排線。 */
  shade?: boolean;
  /** false ＝ 不描墨線。 */
  line?: boolean;
  /** true ＝ 尖角形狀，不圓滑化。 */
  sharp?: boolean;
  /** 填色透明度（預設 0.94）。 */
  alpha?: number;
}

function hatch(ctx: Ctx, pts: readonly Pt[], sharp: boolean | undefined): void {
  const dir = shadeDirs.get(ctx) ?? 1;
  let x0 = Infinity;
  let x1 = -Infinity;
  let y0 = Infinity;
  let y1 = -Infinity;
  for (const [x, y] of pts) {
    x0 = Math.min(x0, x);
    x1 = Math.max(x1, x);
    y0 = Math.min(y0, y);
    y1 = Math.max(y1, y);
  }
  const w = x1 - x0;
  const h = y1 - y0;
  if (w <= 3 || h <= 3) return;
  ctx.save();
  outline(ctx, pts, sharp);
  ctx.clip();
  const a = dir > 0 ? x0 + w * 0.6 : x0 - h;
  const b = dir > 0 ? x1 + h : x0 + w * 0.4;
  ctx.strokeStyle = "rgba(43,30,22,0.42)";
  ctx.lineWidth = 0.35;
  ctx.beginPath();
  for (let x = a; x < b; x += 1.3) {
    ctx.moveTo(x, y0);
    ctx.lineTo(x - h * 0.9, y1);
  }
  ctx.stroke();
  ctx.restore();
}

/** 畫一個部件：水彩填色＋暗面排線＋兩次抖動墨線。`key` 決定抖動（同一部件在不同方向用不同 key）。 */
export function ink(ctx: Ctx, key: string, pts: readonly Pt[], color: string, opt: InkOpt = {}): void {
  const r = lcg(seedOf(key));
  ctx.save();
  ctx.translate(0.45, 0.35);
  outline(ctx, wobble(pts, r, 0.7), opt.sharp);
  ctx.globalAlpha = opt.alpha ?? 0.94;
  ctx.fillStyle = color;
  ctx.fill();
  ctx.globalAlpha = 0.35;
  ctx.strokeStyle = "rgba(0,0,0,0.55)";
  ctx.lineWidth = 0.9;
  ctx.stroke();
  ctx.restore();
  if (opt.shade !== false) hatch(ctx, pts, opt.sharp);
  if (opt.line === false) return;
  const w = opt.w ?? 0.85;
  ctx.strokeStyle = INK;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.lineWidth = w;
  outline(ctx, wobble(pts, r, 0.5), opt.sharp);
  ctx.stroke();
  ctx.lineWidth = w * 0.45;
  outline(ctx, wobble(pts, r, 0.85), opt.sharp);
  ctx.stroke();
}

/** 開放的抖動線（腰帶、縫線、嘴、骨架線）。 */
export function stroke(ctx: Ctx, key: string, pts: readonly Pt[], w = 0.7, color: string = INK): void {
  const r = lcg(seedOf(key));
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  smooth(ctx, wobble(pts, r, 0.35), false);
  ctx.stroke();
}

/** 小橢圓點（眼睛、手上的點）。 */
export function dot(ctx: Ctx, x: number, y: number, rx: number, ry: number, c: string): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.ellipse(x, y, rx, ry, 0, 0, TAU);
  ctx.fill();
}

/** 地面影子：一排短斜線（不是深色橢圓）。 */
export function shadow(ctx: Ctx, rx = 9): void {
  const r = lcg(7);
  ctx.strokeStyle = "rgba(43,30,22,0.5)";
  ctx.lineWidth = 0.5;
  ctx.beginPath();
  for (let x = -rx; x < rx; x += 2.2) {
    const j = r();
    ctx.moveTo(x + j, 1.2);
    ctx.lineTo(x + j + 2.4, -0.6);
  }
  ctx.stroke();
}

/** 左右鏡像一組點。 */
export const mirrorPts = (pts: readonly Pt[]): Pt[] => pts.map(([x, y]): Pt => [-x, y]);

/**
 * 墨線畫風共用的材質色（Phase 3T-4）。金、木取自 `appearance.MATERIAL`（同一份）；
 * 鋼、鐵是墨線畫風專用的較亮金屬色（美術 PM 定案，與 `MATERIAL` 的 steel／iron 不同，改了會動所有小人的盔甲與劍）。
 */
export const MAT = {
  steel: "#c3ccd6",
  iron: "#8d969f",
  gold: MATERIAL["gold"]![0],
  wood: MATERIAL["wood"]![0],
} as const;
