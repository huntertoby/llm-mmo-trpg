// 致命地形與水面的畫法（Phase 6V-2；docs/art/Fable審查.md 第 2 節 A）。只換外觀，規則、格子與致命判定不動。
// - 雲海／深淵（`chasm`）：白雲團鋪滿格子、邊緣羽化、底下透淡藍；雲團照 `docs/art/sample/worldPaintedArt.js` 的
//   `cloudBank`／`cloudPuff` 縮小。鄰格也是雲海時，連鄰格種子的雲團一起畫（裁在本格內），格與格之間雲團就接得起來。
// - 熔岩（`lava`）：橘紅發光底、亮黃熱紋、黑色岩殼裂紋（照 `ashenRegionArt.js` 的熔岩河）；靠岸的邊一圈冷卻黑殼。
//   岩殼塊的慢速漂移是另一層（`surfaceAnim.terrainShimmer`），貼圖本身是靜態的。
// - 水面（`water` 表面）：填滿格子、岸邊一圈濕痕（深一階）、細反光線；水色依區域（`regionArt.waterColorOf`）。
//   6V-2b：岸邊改成羽化（`featherFill`）；灰渡口的深淵（`look.chasm_style: deep_water`）畫成深水（`drawDeepWater`）。
// 座標以 52 的虛擬格為單位（同 terrainArt 的 ART_T）。全部只看格子座標雜湊（`artRandom.rng`），不用 Math.random。
// 這個檔案不匯入 terrainArt 的值（避免循環匯入）；只用 `TileArtSpec` 型別。
import { TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";
import { rng } from "./artRandom";
import type { TileArtSpec } from "./terrainArt";

const T = 52;

type Rgb = readonly [number, number, number];

/** 雲海的色票：底下的淡藍、雲團的白與陰影（照大世界圖的雲層）。 */
export const CLOUD_SEA = {
  deep: "#8fa9c8",
  shallow: "#c4d4e6",
  tint: [250, 250, 253] as Rgb,
  shade: [168, 182, 210] as Rgb,
} as const;

/** 一團雲（`cloudPuff`）：左上偏亮、邊緣羽化到透明。 */
function cloudPuff(ctx: Ctx, x: number, y: number, r: number, a: number, tint: Rgb, shadeC: Rgb, sy: number): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(1, sy);
  ctx.translate(-x, -y);
  const g = ctx.createRadialGradient(x - r * 0.25, y - r * 0.45, r * 0.1, x, y, r);
  const mid = tint.map((v, i) => Math.round(v * 0.6 + (shadeC[i] ?? 0) * 0.4)).join(",");
  g.addColorStop(0, `rgba(${tint.join(",")},${a})`);
  g.addColorStop(0.55, `rgba(${mid},${a})`);
  g.addColorStop(0.9, `rgba(${shadeC.join(",")},${a * 0.9})`);
  g.addColorStop(1, `rgba(${shadeC.join(",")},0)`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  ctx.restore();
}

/** 一格的雲團（格子座標雜湊；`ox`、`oy` 是這一格相對於畫布的位移，鄰格用 ±T）。 */
function puffsOf(ctx: Ctx, x: number, y: number, ox: number, oy: number, salt: number): void {
  const r = rng(x, y, salt);
  const count = 5 + Math.floor(r() * 3);
  const items: Array<[number, number, number, number]> = [];
  for (let i = 0; i < count; i++) {
    const px = ox + (i / count) * T + (r() - 0.5) * 14;
    const py = oy + 8 + r() * (T - 16);
    const rad = 11 + r() * 9;
    items.push([px, py, rad, 0.62 + r() * 0.2]);
  }
  items.sort((p, q) => p[1] - q[1]);
  for (const [px, py, rad, a] of items) cloudPuff(ctx, px, py, rad, a, CLOUD_SEA.tint, CLOUD_SEA.shade, 0.7);
}

/** 哪些鄰格也是雲海（`lip` 為假＝同種地形）；斜鄰看兩邊都不是崖。 */
export function cloudNeighbors(s: TileArtSpec): Array<readonly [number, number]> {
  const n = !s.lip.n;
  const so = !s.lip.s;
  const w = !s.lip.w;
  const e = !s.lip.e;
  const out: Array<readonly [number, number]> = [];
  if (n && w) out.push([-1, -1]);
  if (n) out.push([0, -1]);
  if (n && e) out.push([1, -1]);
  if (w) out.push([-1, 0]);
  if (e) out.push([1, 0]);
  if (so && w) out.push([-1, 1]);
  if (so) out.push([0, 1]);
  if (so && e) out.push([1, 1]);
  return out;
}

/** 雲海底圖（不含崖緣）：淡藍底 → 鄰格的雲團（接縫）→ 本格的雲團。 */
export function drawCloudSea(ctx: Ctx, s: TileArtSpec, salt: number): void {
  const r = rng(s.x, s.y, salt);
  const g = ctx.createLinearGradient(0, 0, 0, T);
  g.addColorStop(0, shade(CLOUD_SEA.deep, 0.96 + r() * 0.08));
  g.addColorStop(1, CLOUD_SEA.shallow);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  // 底下透一點更深的藍（雲縫）
  for (let i = 0; i < 2; i++) {
    const cx = r() * T;
    const cy = r() * T;
    const rg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14 + r() * 8);
    rg.addColorStop(0, rgba("#6f8db4", 0.5));
    rg.addColorStop(1, rgba("#6f8db4", 0));
    ctx.fillStyle = rg;
    ctx.fillRect(0, 0, T, T);
  }
  for (const [dx, dy] of cloudNeighbors(s)) puffsOf(ctx, s.x + dx, s.y + dy, dx * T, dy * T, salt);
  puffsOf(ctx, s.x, s.y, 0, 0, salt);
}

/** 熔岩的色票（照荒原區域插畫的熔岩河）。 */
export const LAVA = {
  base: "#c2410c",
  bright: "#ff7a1a",
  hot: "#ffd36b",
  crust: "#2a1610",
  crustEdge: "#140a06",
} as const;

/** 熔岩的岩殼塊：不規則的深色板塊、邊緣一圈更深的裂紋。 */
export function crustPlate(ctx: Ctx, cx: number, cy: number, rad: number, r: () => number, fill: string, edge: string): void {
  ctx.beginPath();
  const n = 7;
  for (let k = 0; k < n; k++) {
    const a = (k / n) * TAU;
    const rr = rad * (0.7 + r() * 0.4);
    const px = cx + Math.cos(a) * rr;
    const py = cy + Math.sin(a) * rr * 0.75;
    if (k === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = edge;
  ctx.lineWidth = 1.2;
  ctx.lineJoin = "round";
  ctx.stroke();
}

/** 冷卻黑殼：靠岸（`lip`）那一邊一圈凹凸的黑殼，內側透一點熱光。 */
function cooledRim(ctx: Ctx, r: () => number, side: "n" | "s" | "w" | "e"): void {
  const horizontal = side === "n" || side === "s";
  const depth = 5;
  ctx.fillStyle = LAVA.crust;
  ctx.beginPath();
  const steps = 7;
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * T;
    const d = depth + r() * 3;
    const px = horizontal ? t : side === "w" ? d : T - d;
    const py = horizontal ? (side === "n" ? d : T - d) : t;
    if (i === 0) ctx.moveTo(horizontal ? 0 : side === "w" ? 0 : T, horizontal ? (side === "n" ? 0 : T) : 0);
    ctx.lineTo(px, py);
  }
  ctx.lineTo(horizontal ? T : side === "w" ? 0 : T, horizontal ? (side === "n" ? 0 : T) : T);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = rgba(LAVA.hot, 0.35);
  ctx.lineWidth = 1;
  ctx.stroke();
}

/** 熔岩底圖：發光底 → 熱紋 → 岩殼塊 → 冷卻黑殼。`tone` 微調底色（荒原更暗紅）。 */
export function drawLavaBase(ctx: Ctx, s: TileArtSpec, salt: number, tone = 1): void {
  const r = rng(s.x, s.y, salt);
  ctx.fillStyle = shade(LAVA.base, tone * (0.94 + r() * 0.12));
  ctx.fillRect(0, 0, T, T);
  // 發光：2～3 個亮橘光團
  const glows = 2 + Math.floor(r() * 2);
  for (let i = 0; i < glows; i++) {
    const cx = r() * T;
    const cy = r() * T;
    const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 16 + r() * 10);
    gg.addColorStop(0, rgba(LAVA.bright, 0.9));
    gg.addColorStop(1, rgba(LAVA.bright, 0));
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, T);
  }
  // 熱紋：亮黃的細流線
  ctx.strokeStyle = rgba(LAVA.hot, 0.8);
  ctx.lineWidth = 1.6;
  ctx.lineCap = "round";
  for (let i = 0; i < 2; i++) {
    const x0 = r() * T;
    const y0 = 8 + i * 22 + r() * 10;
    ctx.beginPath();
    ctx.moveTo(x0 - 14, y0);
    ctx.bezierCurveTo(x0 - 6, y0 - 5, x0 + 2, y0 + 5, x0 + 12, y0 - 2);
    ctx.stroke();
  }
  // 岩殼塊：2～3 片固定的小板塊（漂移的另一層另畫），再 2 道黑色裂紋線
  const crusts = 2 + Math.floor(r() * 2);
  for (let i = 0; i < crusts; i++) crustPlate(ctx, 8 + r() * (T - 16), 8 + r() * (T - 16), 4 + r() * 4, r, rgba(LAVA.crust, 0.8), rgba(LAVA.crustEdge, 0.85));
  ctx.strokeStyle = rgba(LAVA.crustEdge, 0.7);
  ctx.lineWidth = 1.3;
  ctx.lineCap = "round";
  for (let i = 0; i < 2; i++) {
    let px = r() * T;
    let py = r() * T;
    ctx.beginPath();
    ctx.moveTo(px, py);
    for (let k = 0; k < 3; k++) {
      px += (r() - 0.5) * 16;
      py += (r() - 0.5) * 16;
      ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
  if (s.lip.n) cooledRim(ctx, r, "n");
  if (s.lip.s) cooledRim(ctx, r, "s");
  if (s.lip.w) cooledRim(ctx, r, "w");
  if (s.lip.e) cooledRim(ctx, r, "e");
}

/** 岸邊濕痕的寬度（虛擬像素）。 */
export const WATER_SHORE = 4;
/** 水面在岸邊羽化的寬度（虛擬像素；6V-2b：濕痕不再是硬邊，水由不透明淡到透明）。 */
export const WATER_FEATHER = 9;

/** 四邊「同種」的旗標（`true` ＝ 那一側也是水，不是岸）。 */
interface SameSides {
  n: boolean;
  s: boolean;
  w: boolean;
  e: boolean;
}

/**
 * 羽化的填色（6V-2b）：中間實心，岸那一側（`same` 為假）在 `f` 像素內由 `alpha` 淡到 0；兩個岸相接的角用 1/4 圓的放射漸層。
 * 各塊不重疊（不會有疊兩次變深的條紋）。
 */
export function featherFill(ctx: Ctx, same: SameSides, f: number, color: string, alpha: number): void {
  const x0 = same.w ? 0 : f;
  const y0 = same.n ? 0 : f;
  const x1 = same.e ? T : T - f;
  const y1 = same.s ? T : T - f;
  ctx.fillStyle = rgba(color, alpha);
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  const stops = (g: CanvasGradient, inner: 0 | 1): void => {
    g.addColorStop(inner, rgba(color, alpha));
    g.addColorStop(0.5, rgba(color, alpha * 0.55));
    g.addColorStop(1 - inner, rgba(color, 0));
  };
  // 邊：漸層從格緣（透明）到內側（實心）
  const band = (gx0: number, gy0: number, gx1: number, gy1: number, rect: readonly [number, number, number, number]): void => {
    const g = ctx.createLinearGradient(gx0, gy0, gx1, gy1);
    stops(g, 1);
    ctx.fillStyle = g;
    ctx.fillRect(rect[0], rect[1], rect[2], rect[3]);
  };
  if (!same.n) band(0, 0, 0, f, [x0, 0, x1 - x0, f]);
  if (!same.s) band(0, T, 0, T - f, [x0, T - f, x1 - x0, f]);
  if (!same.w) band(0, 0, f, 0, [0, y0, f, y1 - y0]);
  if (!same.e) band(T, 0, T - f, 0, [T - f, y0, f, y1 - y0]);
  // 角：以內側的角為圓心，半徑 f 由實心淡到透明
  const corner = (cx: number, cy: number, rx: number, ry: number): void => {
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, f);
    stops(g, 0);
    ctx.fillStyle = g;
    ctx.fillRect(rx, ry, f, f);
  };
  if (!same.n && !same.w) corner(f, f, 0, 0);
  if (!same.n && !same.e) corner(T - f, f, T - f, 0);
  if (!same.s && !same.e) corner(T - f, T - f, T - f, T - f);
  if (!same.s && !same.w) corner(f, T - f, 0, T - f);
}

/** 濕痕的顏色：岸那一側的地面壓深一階（羽化，邊緣淡到透明）。 */
const WET = "#141e28";

/** 水面：填滿格子，岸邊（鄰格不是水）一圈羽化的濕痕、水由實心淡到透明（6V-2b），細反光線。`color` 是區域的水色。 */
export function drawWaterFill(ctx: Ctx, s: TileArtSpec, color: string): void {
  const r = rng(s.x, s.y, 21);
  const same = s.surfSame;
  // 濕痕：岸那一側的地面壓深（只在最外 ~2px 淡掉），水面再從裡面羽化蓋上去
  featherFill(ctx, same, 2, WET, 0.32);
  featherFill(ctx, same, WATER_FEATHER, color, 0.86);
  const x0 = same.w ? 0 : WATER_SHORE;
  const y0 = same.n ? 0 : WATER_SHORE;
  const x1 = same.e ? T : T - WATER_SHORE;
  const y1 = same.s ? T : T - WATER_SHORE;
  // 深一點的水色暈（水不是一片平的；只在內側，不碰岸）
  const cx = x0 + 6 + r() * Math.max(1, x1 - x0 - 12);
  const cy = y0 + 6 + r() * Math.max(1, y1 - y0 - 12);
  const g = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14 + r() * 6);
  g.addColorStop(0, rgba(shade(color, 0.8), 0.45));
  g.addColorStop(1, rgba(shade(color, 0.8), 0));
  ctx.fillStyle = g;
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  // 細反光線：1 像素、低透明（飄動的反光由 6N-9 的 surfaceAnim 另畫）
  ctx.strokeStyle = "rgba(235,248,255,0.55)";
  ctx.lineWidth = 1;
  ctx.lineCap = "round";
  for (let i = 0; i < 2; i++) {
    const wx = x0 + 6 + r() * Math.max(1, x1 - x0 - 24);
    const wy = y0 + 8 + r() * Math.max(1, y1 - y0 - 16);
    ctx.beginPath();
    ctx.moveTo(wx, wy);
    ctx.lineTo(wx + 9 + r() * 6, wy - 1);
    ctx.stroke();
  }
}

/** 深水的色票（6V-2b：灰渡口的灰河；比荒原水面 `#45627a` 深一階）。 */
export const DEEP_WATER = {
  /** 岸邊的濕泥（深淵格本身沒有地面，羽化的水邊底下要有東西）。 */
  bank: "#3e3a37",
  base: "#2b3c4d",
  dark: "#16212c",
  ripple: "rgba(170,196,220,0.22)",
} as const;

/**
 * 深水（6V-2b，`look.chasm_style: deep_water`）：只換畫法，地形仍是 `chasm`（致命判定不動）。
 * 濕泥岸 → 羽化的深灰藍水 → 一層暗色 → 兩道很淡的大波紋（靜態；慢慢飄的大波紋在 `surfaceAnim.terrainShimmer`）。
 * 不畫裂谷的崖緣與底部紅光。`lip` 為真的那一側是岸。
 */
export function drawDeepWater(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 231);
  const same = { n: !s.lip.n, s: !s.lip.s, w: !s.lip.w, e: !s.lip.e };
  const shore = s.lip.n || s.lip.s || s.lip.w || s.lip.e;
  if (shore) {
    ctx.fillStyle = shade(DEEP_WATER.bank, 0.94 + r() * 0.1);
    ctx.fillRect(0, 0, T, T);
    featherFill(ctx, same, 3, WET, 0.4);
  }
  featherFill(ctx, same, WATER_FEATHER, shade(DEEP_WATER.base, 0.95 + r() * 0.1), 0.97);
  // 暗色層：深處更暗（只在內側，不碰岸）
  const x0 = same.w ? 0 : WATER_FEATHER;
  const y0 = same.n ? 0 : WATER_FEATHER;
  const x1 = same.e ? T : T - WATER_FEATHER;
  const y1 = same.s ? T : T - WATER_FEATHER;
  for (let i = 0; i < 2; i++) {
    const cx = x0 + r() * (x1 - x0);
    const cy = y0 + r() * (y1 - y0);
    const g = ctx.createRadialGradient(cx, cy, 1, cx, cy, 16 + r() * 8);
    g.addColorStop(0, rgba(DEEP_WATER.dark, 0.5));
    g.addColorStop(1, rgba(DEEP_WATER.dark, 0));
    ctx.fillStyle = g;
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  }
  // 很淡的大波紋：兩道寬弧
  ctx.strokeStyle = DEEP_WATER.ripple;
  ctx.lineWidth = 1.2;
  ctx.lineCap = "round";
  for (let i = 0; i < 2; i++) {
    const wy = 14 + i * 22 + r() * 6;
    const wx = 6 + r() * 14;
    ctx.beginPath();
    ctx.moveTo(wx, wy);
    ctx.quadraticCurveTo(wx + 12, wy - 4, wx + 26, wy);
    ctx.stroke();
  }
}
