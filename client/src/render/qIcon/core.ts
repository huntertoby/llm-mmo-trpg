// Q 版小圖示的共用核心（Phase QI-1a；照 docs/art/sample/qIcons.js 逐行搬，需求 docs/art/Q版小圖示-武器防具移植需求.md 2.1、3.1）。
// 這裡只搬武器、裝備圖示用得到的部分：外框色、材質色 M、元素色 EL、畫法小工具、剪影外框（dilate、halo）、render、outlinePx、
// badgeScale（圓章自動縮放）、GEAR_PAD（裝備格留白）、blit（真 1 倍對齊），以及第 1 批用到的八把樣本畫法（W）。技能、物品、狀態、HUD 不搬。
// 畫法和樣張一樣：每個圖樣畫在 48×48 的格子裡；d 畫主體（會被包外框）、pre 畫在外框底下（光暈）、post 畫在最上面（細線、閃光）。
// 和樣張不同的地方（PM 決定，docs/phases/PhaseQI-1計畫.md 0.0）：
// - 材質色用遊戲端 `material.ts`（人物那一份；鐵、鋼比樣張暗一階），樣張自己的 M／MAT 表不搬。
// - 混色用共用的 `color.ts` 的 `mix`。
// - 建立畫布集中在 `blank()`，由 `setQCanvasFactory` 換掉（vitest 用假畫布；沒有 DOM 時 `render` 回傳 null）。
import { mix } from "../color";
import { MATERIAL } from "../material";
import { KEYWORD_COLOR } from "../palette";

export type Ctx = CanvasRenderingContext2D;
export type Pt = readonly [number, number];

/** 畫法收到的旗標（需求 3.1 第 6 點）。 */
export interface QOpts {
  /** 圖樣邊長 ≤ 24px（省掉小零件）。 */
  small: boolean;
  /** 圖樣邊長 ≤ 14px（只留主形與一階亮面）。 */
  tiny: boolean;
  /** 外框幾個裝置像素。 */
  owPx: number;
  /** 畫在米色圓章裡。 */
  badge: boolean;
  /** 1 CSS px 是幾個 48 格單位（畫 1px 細線用）。 */
  u: number;
  /** 量整體剪影的那一遍。 */
  flat?: boolean;
  /** 成對武器裡的一把。 */
  pair?: boolean;
  /** 成對武器裡後面那把。 */
  rear?: boolean;
}
export type DrawFn = (c: Ctx, o: QOpts) => void;
/** 一個圖樣：d 主體、pre 外框底下、post 最上面。 */
export interface QDef {
  d: DrawFn;
  pre?: DrawFn | undefined;
  post?: DrawFn | undefined;
}
export interface RenderOpt {
  /** 外框粗細（CSS px）；預設 `outlinePx(px)`。0＝不畫外框。 */
  ow?: number;
  /** 畫在米色圓章裡。 */
  badge?: boolean;
}

export const TAU = Math.PI * 2;
/** 剪影外框色（和 Q 版人物 `Q_OUT` 同色）。 */
export const OUT = "#16121a";
const mat = (id: string): readonly [string, string] => MATERIAL[id] as readonly [string, string];
/** 畫法固定零件的顏色。鋼、鐵、木、皮照 `material.ts`（第 0.0 節第 3 點）；其餘照樣張。 */
export const M = {
  steel: mat("steel")[0],
  steelD: mat("steel")[1],
  iron: mat("iron")[0],
  ironD: mat("iron")[1],
  wood: mat("wood")[0],
  woodD: mat("wood")[1],
  shaft: "#6a4420",
  grip: "#4a3020",
  brass: "#8a6a2a",
  gold: "#d8b04a",
  goldL: "#f6d878",
  leather: mat("leather")[0],
  leatherD: mat("leather")[1],
  skin: "#f1c9a5",
  cream: "#f2e6c8",
  arcane: "#9a86ff",
} as const;
/** 元素色（照 `palette.ts`）：[主色, 亮色]。 */
export const EL: Readonly<Record<string, readonly [string, string]>> = {
  fire: ["#ff6a1a", "#ffd23f"],
  ice: ["#8fe3ff", "#ffffff"],
  lightning: ["#fff36b", "#ffffff"],
  poison: ["#7ddc3a", "#d6f59a"],
  holy: ["#ffd75e", "#fff6c8"],
  shadow: ["#9a6ad8", "#d2b0ff"],
  wind: ["#7fe0c0", "#dcfff1"],
  earth: ["#b0814a", "#f0c890"],
  water: ["#4aa8ff", "#cfe8ff"],
};
/** 寶石色（QI-1b，美術 PM 對 1a 的追加）：有元素關鍵字就用元素色，沒有才用其他關鍵字的色；都沒有時晶石 `#b8a8ff`、其他 `#e04060`。
 *  照固定順序挑（`KEYWORD_COLOR` 的宣告順序：元素四個 ignite、wet、charged、frozen 在前），**不受關鍵字順序影響**。 */
export function gemAccent(keywords: readonly string[], material: string): string {
  const k = Object.keys(KEYWORD_COLOR).find((id) => keywords.includes(id));
  return k !== undefined ? (KEYWORD_COLOR[k] as string) : material === "crystal" ? "#b8a8ff" : "#e04060";
}
export const HI = "rgba(255,255,255,0.45)";
export const HI2 = "rgba(255,255,255,0.8)";
export const SH = "rgba(0,0,0,0.22)";

// ---------------- 畫布 ----------------
type CanvasFactory = (w: number, h: number) => HTMLCanvasElement | null;
const domCanvas: CanvasFactory = (w, h) => {
  if (typeof document === "undefined") return null;
  const cv = document.createElement("canvas");
  cv.width = w;
  cv.height = h;
  return cv;
};
let factory: CanvasFactory = domCanvas;
/** 換掉建立畫布的方式（測試用假畫布）；`null` 換回 DOM。 */
export function setQCanvasFactory(f: CanvasFactory | null): void {
  factory = f ?? domCanvas;
}
/** 現在建得出畫布嗎（沒有 DOM、也沒有注入假畫布時不行）。 */
export const qCanvasAvailable = (): boolean => factory !== domCanvas || typeof document !== "undefined";
/** 一張空白畫布（寬 w、高 h 裝置像素）。只在 `render` 裡用（`render` 先確認建得出畫布）。 */
export function blank(w: number, h = w): HTMLCanvasElement {
  const cv = factory(w, h);
  if (cv === null) throw new Error("qIcon: no canvas");
  return cv;
}
export function ctxOf(cv: HTMLCanvasElement): Ctx {
  const x = cv.getContext("2d");
  if (x === null) throw new Error("qIcon: no 2d context");
  return x;
}

// ---------------- 畫法小工具（樣張 H） ----------------
export { mix };
export const f = (c: Ctx, col: string | CanvasGradient, path: (c: Ctx) => void): void => {
  c.beginPath();
  c.fillStyle = col;
  path(c);
  c.fill();
};
export const rr = (c: Ctx, col: string, x: number, y: number, w: number, h: number, r: number | number[]): void => f(c, col, () => c.roundRect(x, y, w, h, r));
export const ci = (c: Ctx, col: string, x: number, y: number, r: number): void => f(c, col, () => c.arc(x, y, r, 0, TAU));
export const el = (c: Ctx, col: string, x: number, y: number, rx: number, ry: number, rot = 0): void => f(c, col, () => c.ellipse(x, y, rx, ry, rot, 0, TAU));
/** 多邊形；round＞0 時用同色粗線把角磨圓（外形往外長 round 單位）。 */
export function poly(c: Ctx, col: string, pts: readonly Pt[], round = 0): void {
  c.beginPath();
  pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
  c.closePath();
  c.fillStyle = col;
  c.fill();
  if (round) {
    c.strokeStyle = col;
    c.lineWidth = round * 2;
    c.lineJoin = "round";
    c.stroke();
  }
}
export function ln(c: Ctx, col: string, w: number, pts: readonly Pt[], join: CanvasLineJoin = "round"): void {
  c.beginPath();
  pts.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
  c.strokeStyle = col;
  c.lineWidth = w;
  c.lineCap = join === "round" ? "round" : "butt";
  c.lineJoin = join;
  c.miterLimit = 6;
  c.stroke();
}
export function starPts(x: number, y: number, R: number, r: number, n: number, rot = -Math.PI / 2): Pt[] {
  const p: Pt[] = [];
  for (let i = 0; i < n * 2; i++) {
    const a = rot + (i * Math.PI) / n,
      q = i % 2 ? r : R;
    p.push([x + Math.cos(a) * q, y + Math.sin(a) * q]);
  }
  return p;
}
export function glow(c: Ctx, x: number, y: number, r: number, col: string, a = 0.5): void {
  const g = c.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, col);
  g.addColorStop(1, mix(col, "#000000", 0) + "00");
  c.save();
  c.globalAlpha = a;
  c.fillStyle = g;
  c.beginPath();
  c.arc(x, y, r, 0, TAU);
  c.fill();
  c.restore();
}
/** 火焰外形：中心 (x,y)、高 20s、寬 14s，尖端朝上，左邊一小撮分岔。 */
export function flame(c: Ctx, col: string, x: number, y: number, s: number): void {
  c.save(); c.translate(x, y); c.scale(s, s); c.beginPath(); c.moveTo(0.5, -10); c.bezierCurveTo(1.5, -5, 7, -3, 7, 3); c.bezierCurveTo(7, 7.5, 3.5, 10, 0, 10); c.bezierCurveTo(-3.5, 10, -7, 7.5, -7, 3);
  c.bezierCurveTo(-7, 0, -5, -2, -4.2, -4.8); c.bezierCurveTo(-3.5, -2.5, -2.6, -2, -1.8, -2.4); c.bezierCurveTo(-2.5, -5, -1.5, -8, 0.5, -10); c.closePath(); c.fillStyle = col; c.fill(); c.restore();
}
export function sparkle(c: Ctx, col: string, x: number, y: number, R: number): void {
  poly(c, col, starPts(x, y, R, R * 0.3, 4));
}

// ---------------- 剪影外框 ----------------
/** 剪影往一圈方向各位移 r（外圈）與 r/2（內圈）疊起來再染外框色（樣張 dilate；不用逐步膨脹，見樣張註解）。 */
export function dilate(src: HTMLCanvasElement, r: number, col = OUT): HTMLCanvasElement {
  const w = src.width,
    h = src.height,
    o = blank(w, h),
    x = ctxOf(o),
    n = Math.max(16, Math.ceil(r * 5));
  for (const q of [1, 0.5]) for (let i = 0; i < n; i++) { const t = (i / n) * TAU; x.drawImage(src, Math.cos(t) * r * q, Math.sin(t) * r * q); }
  x.drawImage(src, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = col; x.fillRect(0, 0, w, h); return o;
}
/** 圖樣裡前後重疊的零件：後畫的那一件自己先包一圈外框，兩件才分得開。 */
export function halo(c: Ctx, o: QOpts, fn: (x: Ctx) => void, col = OUT, k = 1): void {
  if (o.flat) { fn(c); return; } /* 量整體剪影的那一遍：不畫內圈外框，免得整體外框在這裡變兩倍粗 */
  const cv = blank(c.canvas.width, c.canvas.height), x = ctxOf(cv); x.setTransform(c.getTransform()); fn(x);
  c.save(); c.setTransform(1, 0, 0, 1, 0, 0); if (o.owPx > 0) c.drawImage(dilate(cv, o.owPx * k, col), 0, 0); c.drawImage(cv, 0, 0); c.restore();
}
/** 外框粗細（CSS px）：顯示邊長的 5%，最細 1px、最粗 1.6px。 */
export const outlinePx = (px: number): number => Math.min(1.6, Math.max(1, px * 0.05));
/** 只畫圖樣（不含框）：回傳邊長 round(px×res) 的 canvas；建不出畫布時回傳 null。 */
export function render(def: QDef, px: number, res: number, opt: RenderOpt = {}): HTMLCanvasElement | null {
  if (!qCanvasAvailable()) return null;
  const S = Math.max(4, Math.round(px * res)), o: QOpts = { small: px <= 24, tiny: px <= 14, owPx: (opt.ow ?? outlinePx(px)) * res, badge: !!opt.badge, u: 48 / px };
  const main = blank(S), m = ctxOf(main); m.scale(S / 48, S / 48); def.d(m, o);
  const out = blank(S), x = ctxOf(out);
  if (def.pre) { x.save(); x.scale(S / 48, S / 48); def.pre(x, o); x.restore(); }
  if (o.owPx > 0) { const solid = blank(S), s = ctxOf(solid); s.scale(S / 48, S / 48); def.d(s, { ...o, flat: true }); x.drawImage(dilate(solid, o.owPx), 0, 0); }
  x.drawImage(main, 0, 0);
  if (def.post) { x.save(); x.scale(S / 48, S / 48); def.post(x, o); x.restore(); }
  return out;
}

// ---------------- 圓章自動縮放、裝備格留白、貼圖 ----------------
/** 圖樣（不含外框、光暈、閃光；照圓章裡的構圖）離格子中心最遠幾個單位：大、小兩種簡化程度各量一次取大的。 */
function farOf(d: DrawFn): number {
  let far = 0;
  for (const [px, res] of [[24, 4], [48, 2]] as const) {
    const cv = render({ d }, px, res, { ow: 0, badge: true });
    if (cv === null) return 0;
    const S = cv.width, a = ctxOf(cv).getImageData(0, 0, S, S).data;
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) if ((a[(y * S + x) * 4 + 3] ?? 0) > 128) far = Math.max(far, (Math.hypot(x + 0.5 - S / 2, y + 0.5 - S / 2) * 48) / S);
  }
  return far;
}
/** 放進米色圓章時，含外框不可以超出圓章外緣：圖樣最遠點 × 縮放 ≤ 21.2 單位。cap＝這個圖樣另外指定的上限。 */
export const BADGE_R = 21.2;
/** 裝備格裡圖樣四邊各留 6%。 */
export const GEAR_PAD = 0.06;
/** 圓章裡的縮放（`floor` 到千分位，以 cap 封頂）。量不到（沒有畫布）時回傳 cap。 */
export const badgeScale = (d: DrawFn, cap = 1): number => {
  const far = farOf(d);
  return Math.floor(Math.min(cap, far > 0 ? BADGE_R / far : cap) * 1000) / 1000;
};
/** 內部解析度（畫布像素 ＝ CSS px × 2；D4 本段固定）。 */
export const ICON_RES = 2;
/** 貼圖左上角（CSS px）：照 canvas 原尺寸、以 (x,y)～(x+a,y+a) 為中心、四捨五入到整數裝置像素（需求 3.1 第 1 點）。 */
export function blitOrigin(cvWidth: number, x: number, y: number, a: number, res: number): { x: number; y: number; w: number } {
  const w = cvWidth / res, snap = (v: number): number => Math.round(v * res) / res;
  return { x: snap(x + (a - w) / 2), y: snap(y + (a - w) / 2), w };
}
/** 把 `render` 畫好的圖樣貼上（不縮放、對齊整數裝置像素）。ctx 目前每單位 res 個裝置像素、原點在整數像素上。 */
export function blit(ctx: Ctx, cv: HTMLCanvasElement, x: number, y: number, a: number, res: number): void {
  const p = blitOrigin(cv.width, x, y, a, res);
  ctx.drawImage(cv, p.x, p.y, p.w, p.w);
}

// =====================================================================
// 樣張的八把武器畫法（W）：握把在左下、作用端在右上。斜放的武器畫在「握把 +y、作用端 −y」的直立座標，長度 ±21。
// =====================================================================
/** 直立座標轉 45°。 */
export const diag = (c: Ctx, fn: (x: Ctx) => void): void => { c.save(); c.translate(24, 24); c.rotate(Math.PI / 4); fn(c); c.restore(); };
/** 武器畫法的配色（第 1 批的參數 P）。 */
export interface ArtPal {
  a: string;
  d: string;
  guard: string;
  guard2: string;
  arc: string;
  wood: string;
  woodD: string;
  shaft: string;
  head: string;
  headD: string;
  orb?: string;
}
export const PW: ArtPal = { a: M.steel, d: M.steelD, guard: M.brass, guard2: M.gold, arc: "#dcd8f4", wood: M.wood, woodD: M.woodD, shaft: M.shaft, head: M.iron, headD: M.ironD };
/** 單手劍：劍身細、劍尖收得長；銅色小護手、短握柄、圓柄頭。 */
export function swordArt(c: Ctx, _o: QOpts, P: ArtPal = PW): void {
  poly(c, P.a, [[-3.3, 5], [-3.3, -14], [0, -21], [3.3, -14], [3.3, 5]]);
  f(c, SH, () => { c.moveTo(0.9, 5); c.lineTo(0.9, -18.8); c.lineTo(3.3, -14); c.lineTo(3.3, 5); c.closePath(); });
  f(c, HI2, () => c.rect(-2.3, -13.5, 1.3, 17.5));
  rr(c, P.guard, -8, 4.6, 16, 3.8, 1.8);
  rr(c, M.grip, -1.9, 8.4, 3.8, 8.4, 1);
  ci(c, P.guard, 0, 18.2, 2.8);
}
/** 雙手劍：劍身寬一倍、劍尖鈍、中間一道血槽；金色大護手；握柄長。 */
export function greatswordArt(c: Ctx, o: QOpts, P: ArtPal = PW): void {
  poly(c, P.a, [[-5.6, 1.5], [-5.6, -16], [0, -21.5], [5.6, -16], [5.6, 1.5]]);
  f(c, SH, () => { c.moveTo(2.2, 1.5); c.lineTo(2.2, -19.4); c.lineTo(5.6, -16); c.lineTo(5.6, 1.5); c.closePath(); });
  f(c, HI2, () => c.rect(-4.4, -15.5, 1.5, 16));
  rr(c, P.d, -0.8, -15, 1.6, 15, 0.8);
  rr(c, P.guard2, -11.5, 0.8, 23, 4.4, 2.2);
  if (!o.small) f(c, M.goldL, () => c.rect(-9.5, 1.5, 19, 1));
  rr(c, M.grip, -2.2, 5.2, 4.4, 16.3, 1.6);
  if (!o.small) f(c, "rgba(255,255,255,0.18)", () => c.rect(-1.4, 6.5, 0.9, 13.5));
}
/** 魔導劍：淡紫的刃、中間一道發光的晶紫導槽、三道符紋橫槓；齒輪形護手、中心一顆晶紫寶石。 */
export function arcaneArt(c: Ctx, o: QOpts, P: ArtPal = PW): void {
  poly(c, P.arc, [[-3.6, 3], [-3.6, -14.5], [0, -21], [3.6, -14.5], [3.6, 3]]);
  rr(c, M.arcane, -1.2, -17.5, 2.4, 20, 1.2);
  if (!o.tiny) for (const y of [-13.4, -8.8, -4.2]) rr(c, "#f6f0ff", -2.7, y, 5.4, 1.4, 0.5);
  poly(c, "#b08a4a", starPts(0, 5.4, 7.6, 5.3, 8, 0), 0.5);
  ci(c, M.arcane, 0, 5.4, 2.7); ci(c, HI2, -0.8, 4.6, 0.9);
  rr(c, M.grip, -1.8, 11, 3.6, 6.6, 1);
  poly(c, M.arcane, [[0, 16.6], [2.6, 19.2], [0, 21.8], [-2.6, 19.2]], 0.3);
}
/* 弓（第 1 批第 2 版）：三款弓共用一套幾何；圓章裡（o.badge）弦是 1px 深褐線、箭桿 1.25px 更深的褐線，畫在 post；裝備格弦白、箭桿淺木色、紅箭羽。 */
const BOW_STRING = "#5a3a22", BOW_SHAFT = "#3a2616";
interface BowForm { ex: number; dep: number; top: number; recurve?: boolean; tx?: number; ty?: number; R?: number; A?: number }
const BOW_FORM: Readonly<Record<string, BowForm>> = { short: { ex: 13.5, dep: 13.5, top: -8 }, long: { ex: 18.5, dep: 12.8, top: -8 }, recurve: { ex: 14.6, dep: 13.7, top: -8.4, recurve: true, tx: 18.6, ty: 0.6, R: 13, A: 1.35 } };
export interface BowGeo { ex: number; dep: number; top: number; recurve?: boolean; R: number; A: number; y0: number; nock: number; tx: number; ty: number }
export const bowGeo = (form = "short"): BowGeo => { const g = BOW_FORM[form] ?? (BOW_FORM["short"] as BowForm), R = (g.ex * g.ex + g.dep * g.dep) / (2 * g.dep), y0 = g.top + g.dep; return { ...g, R: g.R ?? R, A: g.A ?? Math.asin(Math.min(1, g.ex / R)), y0, nock: y0 + 3, tx: g.tx ?? g.ex, ty: g.ty ?? y0 }; };
/** 弓臂的路徑：短弓＝半圓、長弓＝又長又淺的圓弧；反曲弓兩端多一小段反翹的弓梢。 */
const bowLimb = (c: Ctx, G: BowGeo): void => {
  if (!G.recurve) { c.arc(0, G.top + G.R, G.R, -Math.PI / 2 - G.A, -Math.PI / 2 + G.A); return; }
  const ex = Math.sin(G.A) * G.R, ey = G.top + G.R * (1 - Math.cos(G.A)), dx = Math.cos(G.A) * 3.6, dy = Math.sin(G.A) * 3.6, y = G.y0;
  c.moveTo(-G.tx, G.ty); c.bezierCurveTo(-G.tx + 1, y + 1.1, -ex - dx, ey + dy, -ex, ey); c.arc(0, G.top + G.R, G.R, -Math.PI / 2 - G.A, -Math.PI / 2 + G.A); c.bezierCurveTo(ex + dx, ey + dy, G.tx - 1, y + 1.1, G.tx, G.ty);
};
export function bowArt(c: Ctx, o: QOpts, P: ArtPal = PW, G0: BowGeo | null = null, tip: string | null = null): void {
  const G = G0 ?? bowGeo(), w = o.small ? 2.8 : 3.4, onDark = !o.badge, headBase = G.top - w / 2 + 0.2;
  if (onDark) ln(c, "#e8e8e8", 1.5, [[-G.ex + 0.4, G.y0], [0, G.nock], [G.ex - 0.4, G.y0]]);
  c.beginPath(); bowLimb(c, G); c.strokeStyle = P.wood; c.lineWidth = w; c.lineCap = "round"; c.lineJoin = "round"; c.stroke();
  c.beginPath(); c.arc(0, G.top + G.R, G.R + 0.5, -Math.PI / 2 - G.A * 0.8, -Math.PI / 2 - G.A * 0.12);
  c.strokeStyle = "rgba(255,255,255,0.5)"; c.lineWidth = 1; c.lineCap = "round"; c.stroke();
  ci(c, tip ?? P.woodD, -G.tx, G.ty, o.small ? 1.9 : 2.2); ci(c, tip ?? P.woodD, G.tx, G.ty, o.small ? 1.9 : 2.2);
  if (onDark) { ln(c, "#c8a070", 2.2, [[0, G.nock], [0, headBase]]); poly(c, "#c0392b", [[0, G.nock - 5], [-3, G.nock - 1], [-3, G.nock + 2], [0, G.nock - 1]]); poly(c, "#c0392b", [[0, G.nock - 5], [3, G.nock - 1], [3, G.nock + 2], [0, G.nock - 1]]); }
  rr(c, M.grip, -2.8, G.top - 2.7, 5.6, 5.4, 1.6);
  poly(c, M.steel, [[-3.6, headBase - 1.6], [0, -20.8], [3.6, headBase - 1.6], [0, headBase]], 0.3);
  f(c, HI2, () => { c.moveTo(-2.2, headBase - 2.2); c.lineTo(0, -18.6); c.lineTo(0, headBase - 1.2); c.closePath(); });
}
/** 圓章裡的弦與箭桿：1px、1.25px 的深褐線，畫在外框之上（def.post）。 */
export function bowString(c: Ctx, o: QOpts, G0: BowGeo | null = null): void {
  if (!o.badge) return; const G = G0 ?? bowGeo(), sx = G.ex - 0.6;
  ln(c, BOW_STRING, o.u, [[-sx, G.y0 + 0.3], [0, G.nock], [sx, G.y0 + 0.3]]); ln(c, BOW_SHAFT, o.u * 1.25, [[0, G.nock + 0.6], [0, G.top + 2.9]], "miter");
}
/** 法杖：木杖身、杖頭一顆元素色光球、左上白色高光；球裡一撮亮色，球下一個小托座。 */
export const staffArt = (element: string | undefined, P: ArtPal = PW) => (c: Ctx, o: QOpts): void => {
  const [e1, e2] = (element !== undefined ? EL[element] : undefined) ?? [P.orb ?? "#c8bcff", "#ffffff"];
  rr(c, P.shaft, -1.5, -7, 3, 28.5, 1.2);
  if (!o.small) f(c, HI, () => c.rect(-0.9, -4, 0.7, 22));
  if (!o.small) rr(c, M.grip, -2, 7, 4, 6, 1);
  poly(c, M.brass, [[-4.6, -8.4], [4.6, -8.4], [2, -5.2], [-2, -5.2]], 0.5);
  ci(c, e1, 0, -13.6, 6.6);
  if (element === "fire") flame(c, e2, 0.3, -12.6, 0.46); else if (element === "lightning") poly(c, e2, [[1.5, -18.5], [-3, -12.6], [0, -12.6], [-1.5, -8.6], [3, -14.4], [0, -14.4]]); else poly(c, e2, starPts(0, -13.2, 4.4, 1.6, 4));
  ci(c, HI2, -2.9, -16.4, 1.5);
};
/** 鎚：一大塊長方形鎚頭橫在柄頂，中間一道暗色箍。 */
export function hammerArt(c: Ctx, _o: QOpts, P: ArtPal = PW, shaft: string = M.shaft): void {
  rr(c, shaft, -1.9, -10, 3.8, 31, 1.4);
  rr(c, M.grip, -2.5, 9.5, 5, 8, 1.2);
  rr(c, M.ironD, -2.8, 18.8, 5.6, 3, 1.2);
  rr(c, P.head, -9.2, -19.5, 18.4, 11.4, 2.4);
  f(c, P.headD, () => c.rect(-1.9, -19.5, 3.8, 11.4));
  f(c, SH, () => c.roundRect(-9.2, -12, 18.4, 3.9, [0, 0, 2.4, 2.4]));
  f(c, HI2, () => c.rect(-7.4, -18.1, 4.6, 1.9)); f(c, HI2, () => c.rect(2.8, -18.1, 4.6, 1.9));
}
/** 拳套：握緊的鐵拳正面直立，圓拳上緣切成四個指節的起伏。 */
export function fistArt(c: Ctx, o: QOpts, P: ArtPal = PW): void {
  rr(c, P.headD, 14, 31.5, 20, 11.5, 3);
  rr(c, P.head, 7.5, 11.5, 33, 22.5, 9);
  for (let i = 0; i < 4; i++) rr(c, P.head, 8.4 + i * 8, 6.8, 7.2, 11, 3.4);
  f(c, P.headD, () => c.roundRect(8.4, 14.6, 31.2, 4.2, 1.6));
  if (!o.small) for (let i = 1; i < 4; i++) f(c, P.headD, () => c.rect(7.6 + i * 8, 8.6, 0.9, 6));
  for (let i = 0; i < 4; i++) f(c, i ? HI : HI2, () => c.roundRect(9.8 + i * 8, 8, 4.4, 2.2, 1.1));
  halo(c, o, (x) => { rr(x, P.head, 8.5, 23, 21, 9, 4.5); f(x, HI2, () => x.roundRect(11.5, 24.4, 13, 2, 1)); });
}
/** 塔盾：高的圓角長方形、深褐色的邊、盾面、正中一條米白直紋；deco＝武器／裝備圖示用（頂邊微拱、32px 以上四角鉚釘）。cx,cy＝中心。 */
const SHIELD_FACE = "#6a4a2e", SHIELD_RIM = mix(SHIELD_FACE, "#000000", 0.32), SHIELD_STRIPE = "#e8e0c8";
export function towerShield(c: Ctx, o: QOpts, cx = 24, cy = 24, k = 1, rot = 0, face = SHIELD_FACE, deco = false): void {
  c.save(); c.translate(cx, cy); c.rotate(rot); c.scale(k, k);
  if (deco) {
    const rim = face === SHIELD_FACE ? SHIELD_RIM : mix(face, "#000000", 0.32), lit = face === SHIELD_FACE ? "#86603c" : mix(face, "#ffffff", 0.18);
    const body = (x: number, y: number, w: number, h: number, r: number, arch: number): void => { c.moveTo(x, y + arch); c.quadraticCurveTo(x + w / 2, y - arch, x + w, y + arch); c.lineTo(x + w, y + h - r); c.quadraticCurveTo(x + w, y + h, x + w - r, y + h); c.lineTo(x + r, y + h); c.quadraticCurveTo(x, y + h, x, y + h - r); c.closePath(); };
    f(c, rim, () => body(-13, -19.6, 26, 38.1, 3.6, 2.4)); f(c, face, () => body(-9.6, -15.9, 19.2, 31, 2.2, 1.8));
    c.save(); c.beginPath(); body(-9.6, -15.9, 19.2, 31, 2.2, 1.8); c.clip(); f(c, lit, () => c.rect(-9.6, -18, 5, 34)); f(c, SH, () => c.rect(5.8, -18, 3.8, 34)); c.restore();
    rr(c, SHIELD_STRIPE, -2, -14.6, 4, 28.9, 1);
    if (!o.small) { f(c, "#ffffff", () => c.rect(-1.3, -13.6, 1, 27)); for (const [x, y] of [[-6.7, -11.4], [6.7, -11.4], [-6.7, 11.6], [6.7, 11.6]] as const) { ci(c, mix(face, "#000000", 0.4), x + 0.3, y + 0.4, 1.7); ci(c, mix(face, "#ffffff", 0.62), x, y, 1.4); } }
    c.restore(); return;
  }
  rr(c, face === SHIELD_FACE ? SHIELD_RIM : mix(face, "#000000", 0.32), -13, -18.5, 26, 37, 3.6);
  rr(c, face, -9.6, -15.1, 19.2, 30.2, 2.2);
  f(c, face === SHIELD_FACE ? "#86603c" : mix(face, "#ffffff", 0.18), () => c.roundRect(-9.6, -15.1, 5, 30.2, [2.2, 0, 0, 2.2]));
  f(c, SH, () => c.roundRect(5.8, -15.1, 3.8, 30.2, [0, 2.2, 2.2, 0]));
  rr(c, SHIELD_STRIPE, -2, -14.3, 4, 28.6, 1);
  if (!o.small) f(c, "#ffffff", () => c.rect(-1.3, -13.4, 1, 26.8));
  c.restore();
}
