// 區域圖插畫的共用層（Phase 6F-ART1；docs/art/雲嶺區域插畫.md 第 2、4 節，B 俯視彩繪）。
// 照樣張 `docs/art/sample/regionArt.js` 的 `painted` 分支移植（`scroll` 分支是沒選上的 A 案，不移植）。
// 全部程式繪製，座標用畫布 1280×860 的邏輯像素（`P()`：pos 0～100 換算，左右各留 80、上下各留 70）。
// 亂數一律用 `seeded`（固定種子），同一區每次畫出來都一樣；禁止 Math.random。
// 各區地景在 `regionArtCloud.ts`、`regionArtAshen.ts`；快取與組合在 `regionMapPainter.ts`。
import { seeded } from "./artRandom";

export const W = 1280;
export const H = 860;
export const MX = 80;
export const MY = 70;
export const FONT = '"Noto Sans TC","Microsoft JhengHei","PingFang TC",sans-serif';
const TAU = Math.PI * 2;

export type Ctx = CanvasRenderingContext2D;
export type Pt = [number, number];
export type Rand = () => number;

/** pos（0～100）→ 畫布邏輯座標。 */
export const P = (x: number, y: number): Pt => [MX + (x / 100) * (W - 2 * MX), MY + (y / 100) * (H - 2 * MY)];
export const rng = seeded;

// ---------------------------------------------------------------------------
// 場景資料（由 `world/regionModel.ts` 的 `regionScene` 從伺服器欄位算出；霧裡的地點不在裡面）
// ---------------------------------------------------------------------------

export interface ArtSpot {
  id: string;
  kind: string;
  /** pos（0～100）。 */
  x: number;
  y: number;
  fog: "visited" | "silhouette";
  /** 畫出來的名字（剪影是「？？？」）。 */
  name: string;
  /** 等級牌文字（伺服器的 `level_zh`，已含「Lv」；不畫＝空字串）。 */
  level: string;
  cleared: boolean;
  current: boolean;
  quest: boolean;
  /** 傳送石：`on`＝已解鎖、`off`＝沒解鎖、`null`＝沒有。 */
  stone: "on" | "off" | null;
}

export interface ArtRoad {
  a: string;
  b: string;
  /** 兩端都去過＝土黃色實路；一端剪影＝白色虛線。 */
  solid: boolean;
}

/** 朋友的足跡：畫在 `road` 這條路上，往 `to` 那一端走。 */
export interface ArtTrail {
  road: ArtRoad;
  to: string;
}

export interface RegionScene {
  region: string;
  title: string;
  /** 標題牌的等級（伺服器的區域 `level_zh`）。 */
  level: string;
  spots: ArtSpot[];
  roads: ArtRoad[];
  trails: ArtTrail[];
  /** 有足跡但沒有看得到的路可以畫的地點：腳印畫在地點旁邊。 */
  lonelyTrails: string[];
}

export interface FogPalette {
  base: string;
  puff: readonly [number, number, number];
  shade: string;
}

/** 一區的地景定義（各區地景檔登記）。 */
export interface RegionArtDef {
  terrain(ctx: Ctx): void;
  /** 霧上仍露出的地景（雪峰尖、火山口；不洩漏地點）。 */
  afterFog?(ctx: Ctx): void;
  fog: FogPalette;
}

export const CLOUD_FOG: FogPalette = { base: "#e9edf1", puff: [255, 255, 255], shade: "170,182,198" };

// ---------------------------------------------------------------------------
// 共用畫法
// ---------------------------------------------------------------------------

export function pathThrough(ctx: Ctx, pts: readonly Pt[]): void {
  const first = pts[0];
  const last = pts[pts.length - 1];
  if (first === undefined || last === undefined) return;
  ctx.beginPath();
  ctx.moveTo(first[0], first[1]);
  for (let i = 1; i < pts.length - 1; i++) {
    const p = pts[i] as Pt;
    const n = pts[i + 1] as Pt;
    ctx.quadraticCurveTo(p[0], p[1], (p[0] + n[0]) / 2, (p[1] + n[1]) / 2);
  }
  ctx.lineTo(last[0], last[1]);
}

/** 一團雲（徑向漸層的圓）。 */
export function puff(ctx: Ctx, x: number, y: number, rad: number, a: number, col: readonly [number, number, number] = [255, 255, 255]): void {
  const [r, g0, b] = col;
  const c2 = `${r - 15},${g0 - 11},${b - 7}`;
  const c3 = `${r - 25},${g0 - 19},${b - 13}`;
  const g = ctx.createRadialGradient(x, y - rad * 0.3, rad * 0.1, x, y, rad);
  g.addColorStop(0, `rgba(${r},${g0},${b},${a})`);
  g.addColorStop(0.7, `rgba(${c2},${a * 0.85})`);
  g.addColorStop(1, `rgba(${c3},0)`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, rad, 0, TAU);
  ctx.fill();
}

export function pine(ctx: Ctx, x: number, y: number, k: number): void {
  ctx.fillStyle = "#5a3c24";
  ctx.fillRect(x - 1.5, y - 5, 3, 5);
  for (let i = 0; i < 3; i++) {
    const yy = y - 4 - i * 6 * k;
    const w = (11 - i * 3) * k;
    ctx.fillStyle = i % 2 ? "#2f5a3a" : "#3b6d45";
    ctx.beginPath();
    ctx.moveTo(x - w, yy);
    ctx.lineTo(x, yy - 10 * k);
    ctx.lineTo(x + w, yy);
    ctx.closePath();
    ctx.fill();
  }
}

function snowCap(ctx: Ctx, x: number, y: number, h: number, w: number, px: number): void {
  const t = 0.38;
  ctx.fillStyle = "#f4f7fb";
  ctx.beginPath();
  ctx.moveTo(px, y - h);
  ctx.lineTo(px - (px - (x - w)) * t, y - h + h * t);
  ctx.lineTo(px - w * 0.1, y - h + h * t * 0.7);
  ctx.lineTo(px + w * 0.1, y - h + h * t);
  ctx.lineTo(px + (x + w - px) * t, y - h + h * t * 0.9);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "rgba(170,190,210,0.6)";
  ctx.beginPath();
  ctx.moveTo(px, y - h);
  ctx.lineTo(px + (x + w - px) * t, y - h + h * t * 0.9);
  ctx.lineTo(px + w * 0.1, y - h + h * t);
  ctx.closePath();
  ctx.fill();
}

/** 一座山（左亮右暗兩面，可加雪頂）。 */
export function mountain(ctx: Ctx, x: number, y: number, h: number, r: Rand, snowy: boolean, col: readonly [string, string] = ["#9aa596", "#68756a"]): void {
  const w = h * (0.8 + r() * 0.3);
  const px = x + (r() - 0.5) * w * 0.3;
  ctx.fillStyle = col[0];
  ctx.beginPath();
  ctx.moveTo(x - w, y);
  ctx.lineTo(px, y - h);
  ctx.lineTo(px + w * 0.05, y);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = col[1];
  ctx.beginPath();
  ctx.moveTo(px, y - h);
  ctx.lineTo(x + w, y);
  ctx.lineTo(px + w * 0.05, y);
  ctx.closePath();
  ctx.fill();
  if (snowy) snowCap(ctx, x, y, h, w, px);
  ctx.strokeStyle = "rgba(40,48,58,0.7)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(x - w, y);
  ctx.lineTo(px, y - h);
  ctx.lineTo(x + w, y);
  ctx.stroke();
}

export function roundRect(ctx: Ctx, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// ---------------------------------------------------------------------------
// 地點圖示（照樣張 `icon()`；秘境發現後先用圓圈）
// ---------------------------------------------------------------------------

type Shape = (fill: string, pts: readonly Pt[]) => void;

function shapeOf(ctx: Ctx): Shape {
  return (fill, pts) => {
    ctx.fillStyle = fill;
    ctx.beginPath();
    pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  };
}

const ICONS: Readonly<Record<string, (ctx: Ctx, shape: Shape) => void>> = {
  town(ctx, shape) {
    shape("#e8dcc4", [[-16, 10], [-16, -2], [-4, -2], [-4, 10]]);
    shape("#3d6f9c", [[-19, -1], [-10, -10], [-1, -1]]);
    shape("#efe4cc", [[-2, 10], [-2, -6], [14, -6], [14, 10]]);
    shape("#c0503a", [[-5, -5], [6, -17], [17, -5]]);
    ctx.fillStyle = "#5a3c24";
    ctx.fillRect(3, 2, 5, 8);
  },
  camp(ctx, shape) {
    shape("#d9a441", [[-14, 10], [0, -14], [14, 10]]);
    shape("#8a5a2a", [[-3, 10], [0, 0], [3, 10]]);
    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.lineTo(0, -22);
    ctx.stroke();
    shape("#c0392b", [[0, -22], [9, -19], [0, -16]]);
  },
  village(ctx, shape) {
    shape("#e2cfa8", [[-12, 10], [-12, -2], [12, -2], [12, 10]]);
    shape("#a9813f", [[-16, -1], [0, -15], [16, -1]]);
    ctx.fillStyle = "#5a3c24";
    ctx.fillRect(-3, 2, 6, 8);
  },
  altar(ctx, shape) {
    shape("#a7a39a", [[-12, 10], [-10, 3], [10, 3], [12, 10]]);
    ctx.fillStyle = "#5a3c24";
    ctx.fillRect(-2, -6, 4, 9);
    shape("#2f6a46", [[-14, -4], [0, -20], [14, -4]]);
    shape("#3b8055", [[-10, -12], [0, -24], [10, -12]]);
  },
  ruin(_ctx, shape) {
    shape("#c9c2b0", [[-14, 10], [-14, -10], [-8, -13], [-8, 10]]);
    shape("#c9c2b0", [[-3, 10], [-3, -4], [3, -2], [3, 10]]);
    shape("#c9c2b0", [[8, 10], [8, -15], [14, -15], [14, 10]]);
    shape("#a59e8c", [[-16, -12], [-6, -15], [-4, -12]]);
  },
  elite_lair(ctx) {
    ctx.fillStyle = "#7a2e2e";
    ctx.beginPath();
    ctx.arc(0, -2, 14, 0, TAU);
    ctx.fill();
    ctx.stroke();
    ctx.strokeStyle = "#f3e6d0";
    ctx.lineWidth = 2.5;
    for (const o of [-6, 0, 6]) {
      ctx.beginPath();
      ctx.moveTo(o - 3, -10);
      ctx.lineTo(o + 3, 6);
      ctx.stroke();
    }
  },
  anomaly(_ctx, shape) {
    shape("#9b5de5", [[0, -20], [10, -4], [0, 10], [-10, -4]]);
    shape("#d3b5ff", [[0, -20], [4, -4], [0, 10], [-3, -4]]);
  },
  boss(_ctx, shape) {
    shape("#efe4cc", [[-10, 10], [-10, -4], [10, -4], [10, 10]]);
    shape("#7a2e2e", [[-18, -3], [0, -14], [18, -3]]);
    shape("#7a2e2e", [[-12, -12], [0, -22], [12, -12]]);
  },
  gate(ctx, shape) {
    shape("#8a5a2a", [[-16, 2], [16, 2], [10, 10], [-10, 10]]);
    ctx.beginPath();
    ctx.moveTo(0, 2);
    ctx.lineTo(0, -18);
    ctx.stroke();
    shape("#e9e2d0", [[1, -17], [12, -2], [1, -2]]);
  },
};

/** 地點圖示（依 `kind`；不認得的種類＝圓圈）。`grey`＝剪影。 */
export function icon(ctx: Ctx, kind: string, x: number, y: number, grey: boolean): void {
  ctx.save();
  ctx.translate(x, y);
  if (grey) ctx.filter = "grayscale(1) brightness(1.15) opacity(0.8)";
  ctx.lineJoin = "round";
  const ink = "#232a33";
  ctx.lineWidth = 2;
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.beginPath();
  ctx.ellipse(0, 10, 20, 7, 0, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "rgba(35,42,51,0.5)";
  ctx.stroke();
  ctx.strokeStyle = ink;
  const draw = ICONS[kind];
  if (draw !== undefined) draw(ctx, shapeOf(ctx));
  else {
    ctx.beginPath();
    ctx.arc(0, -2, 12, 0, TAU);
    ctx.stroke();
  }
  ctx.restore();
}

/** 名字牌（白底；剪影灰底）。回傳文字寬度（給清空的綠勾定位）。 */
export function label(ctx: Ctx, text: string, x: number, y: number, grey: boolean): number {
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `bold ${grey ? 13 : 14}px ${FONT}`;
  const tw = ctx.measureText(text).width;
  const w = tw + 14;
  ctx.fillStyle = grey ? "rgba(70,78,90,0.75)" : "rgba(255,255,255,0.92)";
  roundRect(ctx, x - w / 2, y - 10, w, 20, 10);
  ctx.fill();
  if (!grey) {
    ctx.strokeStyle = "rgba(35,42,51,0.6)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  ctx.fillStyle = grey ? "#e8ecf0" : "#1d2530";
  ctx.fillText(text, x, y + 1);
  return tw;
}

/** 等級牌（深色底金字）；`text` 已含「Lv」，空字串不畫。 */
export function lvTag(ctx: Ctx, text: string, x: number, y: number, grey: boolean): void {
  if (text === "") return;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `bold 11px ${FONT}`;
  const w = ctx.measureText(text).width + 10;
  ctx.fillStyle = grey ? "rgba(40,48,58,0.6)" : "rgba(35,42,51,0.85)";
  roundRect(ctx, x - w / 2, y - 8, w, 16, 8);
  ctx.fill();
  ctx.fillStyle = "#ffe08a";
  ctx.fillText(text, x, y + 1);
}

export function check(ctx: Ctx, x: number, y: number): void {
  ctx.fillStyle = "#2e9d57";
  ctx.beginPath();
  ctx.arc(x, y, 8, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(x - 4, y);
  ctx.lineTo(x - 1, y + 3);
  ctx.lineTo(x + 4, y - 3);
  ctx.stroke();
}

export function quest(ctx: Ctx, x: number, y: number): void {
  ctx.fillStyle = "#f2c230";
  ctx.strokeStyle = "#5a3a00";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.arc(x, y, 10, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x - 4, y + 8);
  ctx.lineTo(x, y + 15);
  ctx.lineTo(x + 3, y + 8);
  ctx.fill();
  ctx.fillStyle = "#3a2600";
  ctx.font = `bold 15px ${FONT}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("!", x, y + 1);
}

export function stone(ctx: Ctx, x: number, y: number, unlocked: boolean): void {
  ctx.save();
  if (unlocked) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, 18);
    g.addColorStop(0, "rgba(90,200,255,0.6)");
    g.addColorStop(1, "rgba(90,200,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - 18, y - 18, 36, 36);
  }
  ctx.fillStyle = unlocked ? "#3fb4f0" : "#8d97a3";
  ctx.strokeStyle = "#1b2a38";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x, y - 11);
  ctx.lineTo(x + 7, y);
  ctx.lineTo(x, y + 10);
  ctx.lineTo(x - 7, y);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = unlocked ? "#c9f0ff" : "#c4cad2";
  ctx.beginPath();
  ctx.moveTo(x, y - 11);
  ctx.lineTo(x + 2.5, y);
  ctx.lineTo(x, y + 10);
  ctx.lineTo(x - 2, y);
  ctx.closePath();
  ctx.fill();
  if (!unlocked) {
    ctx.fillStyle = "#3a414a";
    ctx.fillRect(x + 3, y + 2, 9, 7);
    ctx.strokeStyle = "#3a414a";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.arc(x + 7.5, y + 2, 3, Math.PI, 0);
    ctx.stroke();
  }
  ctx.restore();
}

/** 自己：腳下藍色橢圓圈＋左上方藍色定位釘。 */
export function selfMark(ctx: Ctx, x: number, y: number): void {
  ctx.save();
  ctx.strokeStyle = "rgba(60,150,255,0.45)";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.ellipse(x, y + 10, 30, 12, 0, 0, TAU);
  ctx.stroke();
  ctx.strokeStyle = "#2f8cff";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.ellipse(x, y + 10, 30, 12, 0, 0, TAU);
  ctx.stroke();
  ctx.fillStyle = "#2f8cff";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(x - 28, y - 14, 8, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x - 32, y - 8);
  ctx.lineTo(x - 28, y + 2);
  ctx.lineTo(x - 24, y - 8);
  ctx.fill();
  ctx.restore();
}

/** 一個腳印（白色加深色描邊；`ang` 是行進方向）。 */
export function footprint(ctx: Ctx, x: number, y: number, ang: number, alpha: number): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(ang + Math.PI / 2);
  ctx.globalAlpha = alpha;
  ctx.fillStyle = "#f6f8ff";
  ctx.strokeStyle = "rgba(30,36,50,0.8)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.ellipse(0, 0, 3.6, 5.6, 0, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(0, -8, 2.4, 0, TAU);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 迷霧
// ---------------------------------------------------------------------------

/** 整張霧（還沒挖洞；照區域與尺寸快取）。 */
export function fogTexture(ctx: Ctx, fp: FogPalette): void {
  const r = rng(91);
  ctx.fillStyle = fp.base;
  ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 520; i++) puff(ctx, r() * W, r() * H, 30 + r() * 55, 0.55 + r() * 0.4, fp.puff);
  for (let i = 0; i < 160; i++) {
    const x = r() * W;
    const y = r() * H;
    const rad = 20 + r() * 40;
    const g = ctx.createRadialGradient(x, y + rad * 0.4, 0, x, y + rad * 0.4, rad);
    g.addColorStop(0, `rgba(${fp.shade},0.25)`);
    g.addColorStop(1, `rgba(${fp.shade},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2.4);
  }
}

/** 迷霧挖洞的半徑與透明度（21.1 三段：去過＝撥開、剪影＝留薄霧、霧＝不挖）。 */
export const FOG_HOLE = {
  visited: { rad: 190, alpha: 1 },
  silhouette: { rad: 105, alpha: 0.72 },
  road: { rad: 120, alpha: 1 },
} as const;

export interface FogHole {
  x: number;
  y: number;
  rad: number;
  alpha: number;
}

/** 這個場景要在霧上挖的洞（邏輯座標）：去過、剪影、兩端都去過的路上三點。 */
export function fogHoles(scene: RegionScene): FogHole[] {
  const out: FogHole[] = [];
  for (const s of scene.spots) {
    const [x, y] = P(s.x, s.y);
    const h = FOG_HOLE[s.fog];
    out.push({ x, y, rad: h.rad, alpha: h.alpha });
  }
  const byId = spotIndex(scene);
  for (const road of scene.roads) {
    if (!road.solid) continue;
    const a = byId.get(road.a);
    const b = byId.get(road.b);
    if (a === undefined || b === undefined) continue;
    const [x1, y1] = P(a.x, a.y);
    const [x2, y2] = P(b.x, b.y);
    for (const t of [0.25, 0.5, 0.75]) out.push({ x: x1 + (x2 - x1) * t, y: y1 + (y2 - y1) * t, rad: FOG_HOLE.road.rad, alpha: FOG_HOLE.road.alpha });
  }
  return out;
}

/** 在已經畫好霧的畫布上挖洞（`destination-out`）。 */
export function cutFog(ctx: Ctx, holes: readonly FogHole[]): void {
  ctx.save();
  ctx.globalCompositeOperation = "destination-out";
  for (const { x, y, rad, alpha } of holes) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, rad);
    g.addColorStop(0, `rgba(0,0,0,${alpha})`);
    g.addColorStop(0.6, `rgba(0,0,0,${alpha * 0.85})`);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x - rad, y - rad, rad * 2, rad * 2);
  }
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 路與足跡
// ---------------------------------------------------------------------------

export function spotIndex(scene: RegionScene): Map<string, ArtSpot> {
  return new Map(scene.spots.map((s) => [s.id, s]));
}

type Curve = readonly [number, number, number, number, number, number];

/** 路的弧線（照樣張 `curveOf`：依兩端 ID 長度決定往哪邊彎）。 */
export function curveOf(a: ArtSpot, b: ArtSpot): Curve {
  const [x1, y1] = P(a.x, a.y);
  const [x2, y2] = P(b.x, b.y);
  const h = ((a.id.length * 7 + b.id.length * 13) % 5) - 2;
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const len = Math.hypot(x2 - x1, y2 - y1) || 1;
  return [x1, y1, mx + (-(y2 - y1) / len) * h * 9, my + ((x2 - x1) / len) * h * 9, x2, y2];
}

/** 弧線上 t 的點與切線。 */
export function qpt(c: Curve, t: number): [number, number, number, number] {
  const [x1, y1, cx, cy, x2, y2] = c;
  const q = (1 - t) * (1 - t);
  const m = 2 * t * (1 - t);
  const u = t * t;
  return [q * x1 + m * cx + u * x2, q * y1 + m * cy + u * y2, 2 * (1 - t) * (cx - x1) + 2 * t * (x2 - cx), 2 * (1 - t) * (cy - y1) + 2 * t * (y2 - cy)];
}

export function roads(ctx: Ctx, scene: RegionScene): void {
  const byId = spotIndex(scene);
  ctx.lineCap = "round";
  for (const road of scene.roads) {
    const a = byId.get(road.a);
    const b = byId.get(road.b);
    if (a === undefined || b === undefined) continue;
    const c = curveOf(a, b);
    const stroke = (): void => {
      ctx.beginPath();
      ctx.moveTo(c[0], c[1]);
      ctx.quadraticCurveTo(c[2], c[3], c[4], c[5]);
      ctx.stroke();
    };
    if (road.solid) {
      ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(80,60,30,0.6)";
      ctx.lineWidth = 9;
      stroke();
      ctx.strokeStyle = "#d9b679";
      ctx.lineWidth = 6;
      stroke();
    } else {
      ctx.setLineDash([8, 9]);
      ctx.strokeStyle = "rgba(255,255,255,0.85)";
      ctx.lineWidth = 3.5;
      stroke();
    }
  }
  ctx.setLineDash([]);
}

/** 足跡的位置（路的後段約 40%，越接近地點越清楚）：回傳 [x, y, 方向, 透明度]。 */
export function trailSteps(scene: RegionScene, trail: ArtTrail): [number, number, number, number][] {
  const byId = spotIndex(scene);
  const a = byId.get(trail.road.a);
  const b = byId.get(trail.road.b);
  if (a === undefined || b === undefined) return [];
  const c = curveOf(a, b);
  const forward = trail.to === trail.road.b;
  const out: [number, number, number, number][] = [];
  let k = 0;
  for (let s = 0.55; s < 0.93; s += 0.075, k++) {
    const t = forward ? s : 1 - s;
    const [x, y, tx, ty] = qpt(c, t);
    const ang = Math.atan2(forward ? ty : -ty, forward ? tx : -tx);
    const side = k % 2 ? 1 : -1;
    out.push([x - Math.sin(ang) * 6 * side, y + Math.cos(ang) * 6 * side, ang, 0.5 + (0.45 * (s - 0.55)) / 0.38]);
  }
  return out;
}

export function trails(ctx: Ctx, scene: RegionScene): void {
  for (const t of scene.trails) for (const [x, y, ang, alpha] of trailSteps(scene, t)) footprint(ctx, x, y, ang, alpha);
  const byId = spotIndex(scene);
  for (const id of scene.lonelyTrails) {
    const s = byId.get(id);
    if (s === undefined) continue;
    const [x, y] = P(s.x, s.y);
    footprint(ctx, x - 34, y + 18, -0.3, 0.9);
    footprint(ctx, x - 26, y + 10, -0.3, 0.95);
  }
}

// ---------------------------------------------------------------------------
// 地點標記（`k`：字牌放大倍數，面板窄時保持可讀）
// ---------------------------------------------------------------------------

/** 一個地點的標記：自己、圖示、名字牌、等級牌、清空、任務、傳送石。 */
export function spotMarks(ctx: Ctx, s: ArtSpot, k = 1): void {
  const [x, y] = P(s.x, s.y);
  const grey = s.fog === "silhouette";
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  if (s.current) selfMark(ctx, 0, 0);
  icon(ctx, s.kind, 0, 0, grey);
  const tw = label(ctx, s.name, 0, 30, grey);
  lvTag(ctx, grey && s.kind === "gate" ? "" : s.level, 0, 50, grey);
  if (!grey && s.cleared) check(ctx, tw / 2 + 18, 30);
  if (s.quest) quest(ctx, 18, -28);
  if (s.stone !== null) stone(ctx, 28, 2, s.stone === "on");
  ctx.restore();
}

/** 點擊、滑過區（邏輯座標的矩形）：地點本體與傳送石，給 DOM 透明節點定位用（同一套 `P()`）。 */
export interface HitBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function spotHitBox(x: number, y: number, k = 1): HitBox {
  const [cx, cy] = P(x, y);
  return { x: cx - 24 * k, y: cy - 26 * k, w: 48 * k, h: 66 * k };
}

export function stoneHitBox(x: number, y: number, k = 1): HitBox {
  const [cx, cy] = P(x, y);
  return { x: cx + 16 * k, y: cy - 11 * k, w: 24 * k, h: 24 * k };
}

export function questHitBox(x: number, y: number, k = 1): HitBox {
  const [cx, cy] = P(x, y);
  return { x: cx + 7 * k, y: cy - 39 * k, w: 22 * k, h: 22 * k };
}

/** 邏輯座標的矩形 → 畫布的百分比（DOM 節點的 left／top／width／height）。 */
export function hitPercent(b: HitBox, w = W, h = H): { left: string; top: string; width: string; height: string } {
  const pct = (v: number, of: number): string => `${((v / of) * 100).toFixed(3)}%`;
  return { left: pct(b.x, w), top: pct(b.y, h), width: pct(b.w, w), height: pct(b.h, h) };
}

// ---------------------------------------------------------------------------
// 標題、指北針、圖例、外框
// ---------------------------------------------------------------------------

export function title(ctx: Ctx, name: string, level: string): void {
  const x = MX + 4;
  const y = 34;
  ctx.font = `bold 28px ${FONT}`;
  const tw = ctx.measureText(name).width;
  const lv = level === "" ? "" : `建議 ${level}`;
  ctx.font = `bold 15px ${FONT}`;
  const lw = lv === "" ? 0 : ctx.measureText(lv).width + 16;
  ctx.fillStyle = "rgba(35,42,51,0.82)";
  roundRect(ctx, x, y, tw + 36 + lw, 60, 12);
  ctx.fill();
  ctx.strokeStyle = "#e0c27a";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.font = `bold 28px ${FONT}`;
  ctx.fillText(name, x + 18, y + 31);
  if (lv !== "") {
    ctx.fillStyle = "#ffe08a";
    ctx.font = `bold 15px ${FONT}`;
    ctx.fillText(lv, x + tw + 34, y + 32);
  }
}

export function compass(ctx: Ctx): void {
  ctx.save();
  ctx.translate(W - MX - 40, 80);
  ctx.strokeStyle = "#ffffff";
  ctx.fillStyle = "#e05a4a";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(0, -30);
  ctx.lineTo(7, 0);
  ctx.lineTo(-7, 0);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = "rgba(35,42,51,0.8)";
  ctx.beginPath();
  ctx.moveTo(0, 30);
  ctx.lineTo(7, 0);
  ctx.lineTo(-7, 0);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(0, 0, 20, 0, TAU);
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.font = `bold 14px ${FONT}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("N", 0, -42);
  ctx.restore();
}

export function legend(ctx: Ctx): void {
  const w = 330;
  const h = 86;
  const x = W - MX - w + 10;
  const y = H - 30 - h;
  ctx.fillStyle = "rgba(35,42,51,0.82)";
  roundRect(ctx, x, y, w, h, 10);
  ctx.fill();
  const cell = (cx: number, cy: number, draw: (cx: number, cy: number) => void, text: string): void => {
    draw(cx, cy);
    ctx.fillStyle = "#f2f4f7";
    ctx.font = `13px ${FONT}`;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText(text, cx + 16, cy + 1);
  };
  const c1 = x + 22;
  const c2 = x + 128;
  const c3 = x + 232;
  const r1 = y + 26;
  const r2 = y + 60;
  cell(c1, r1, (cx, cy) => {
    ctx.fillStyle = "#2f8cff";
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 7, 0, TAU);
    ctx.fill();
    ctx.stroke();
  }, "自己");
  cell(c2, r1, (cx, cy) => {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(0.75, 0.75);
    quest(ctx, 0, -2);
    ctx.restore();
  }, "任務");
  cell(c3, r1, (cx, cy) => check(ctx, cx, cy), "已清空");
  cell(c1, r2, (cx, cy) => stone(ctx, cx, cy, true), "傳送石");
  cell(c2, r2, (cx, cy) => stone(ctx, cx - 3, cy, false), "未解鎖");
  cell(c3, r2, (cx, cy) => {
    footprint(ctx, cx - 3, cy + 2, -0.3 - Math.PI / 2, 1);
    footprint(ctx, cx + 4, cy - 3, -0.3 - Math.PI / 2, 1);
  }, "朋友足跡");
}

export function frame(ctx: Ctx): void {
  ctx.strokeStyle = "#5a3c24";
  ctx.lineWidth = 22;
  ctx.strokeRect(11, 11, W - 22, H - 22);
  ctx.strokeStyle = "#8a5f38";
  ctx.lineWidth = 6;
  ctx.strokeRect(19, 19, W - 38, H - 38);
  ctx.strokeStyle = "#e0c27a";
  ctx.lineWidth = 2;
  ctx.strokeRect(25, 25, W - 50, H - 50);
}

/** 沒有地景檔的區（之後開放的區還沒補）：只畫草地底色。 */
export function plainTerrain(ctx: Ctx): void {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#8e9a8c");
  g.addColorStop(0.35, "#86a06a");
  g.addColorStop(1, "#78a552");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}
