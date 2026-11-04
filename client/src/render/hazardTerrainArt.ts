// 致命地形與水面的畫法（Phase 6V-2；docs/art/Fable審查.md 第 2 節 A）。只換外觀，規則、格子與致命判定不動。
// - 雲海／深淵（`chasm`）：白雲團鋪滿格子、邊緣羽化、底下透淡藍；雲團照 `docs/art/sample/worldPaintedArt.js` 的
//   `cloudBank`／`cloudPuff` 縮小。鄰格也是雲海時，連鄰格種子的雲團一起畫（裁在本格內），格與格之間雲團就接得起來。
// - 熔岩（`lava`）：橘紅發光底、亮黃熱紋、黑色岩殼裂紋（照 `ashenRegionArt.js` 的熔岩河）；靠岸的邊一圈冷卻黑殼。
//   岩殼塊的慢速漂移是另一層（`surfaceAnim.terrainShimmer`），貼圖本身是靜態的。
// - 水面（`water` 表面）：填滿格子、岸邊一圈濕痕（深一階）、細反光線；水色依區域（`regionArt.waterColorOf`）。
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

/** 水面：填滿格子，岸邊（鄰格不是水）留一圈濕痕，細反光線。`color` 是區域的水色。 */
export function drawWaterFill(ctx: Ctx, s: TileArtSpec, color: string): void {
  const r = rng(s.x, s.y, 21);
  const same = s.surfSame;
  const x0 = same.w ? 0 : WATER_SHORE;
  const y0 = same.n ? 0 : WATER_SHORE;
  const x1 = same.e ? T : T - WATER_SHORE;
  const y1 = same.s ? T : T - WATER_SHORE;
  // 濕痕：岸那一側的地面壓深一階（整格先鋪，水面蓋上去）
  ctx.fillStyle = "rgba(20,30,40,0.32)";
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = rgba(color, 0.86);
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  // 水邊：岸側一條細亮線（水線）
  ctx.strokeStyle = "rgba(230,245,255,0.5)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  if (!same.n) {
    ctx.moveTo(x0, y0 + 0.5);
    ctx.lineTo(x1, y0 + 0.5);
  }
  if (!same.s) {
    ctx.moveTo(x0, y1 - 0.5);
    ctx.lineTo(x1, y1 - 0.5);
  }
  if (!same.w) {
    ctx.moveTo(x0 + 0.5, y0);
    ctx.lineTo(x0 + 0.5, y1);
  }
  if (!same.e) {
    ctx.moveTo(x1 - 0.5, y0);
    ctx.lineTo(x1 - 0.5, y1);
  }
  ctx.stroke();
  // 深一點的水色暈（水不是一片平的）
  const cx = x0 + r() * (x1 - x0);
  const cy = y0 + r() * (y1 - y0);
  const g = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18 + r() * 8);
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
