// 「灰燼荒原」的地形畫法（Phase 5A-ART6；docs/art/四區移植需求.md 第 2 節；畫法移植自 docs/art/sample/regions4.js）。
// 焦土、炭黑、熔岩橘：整體最暗，只有岩漿是亮的。裂縫的熔岩光要細（1.4 線寬、模糊 5），不搶岩漿（致命）的紅。
// 功能特徵不變：牆比單位高、裂谷有崖線且是黑的（和整格亮的岩漿分得開）、灰水坑是深色水。
// 座標以 52 的虛擬格為單位（同 terrainArt 的 ART_T）。這個檔案不匯入 terrainArt 的值（避免循環匯入）；表由 terrainArt 組裝。
import { dot, glowLine, TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";
import { rng } from "./artRandom";
import { drawLavaBase } from "./hazardTerrainArt";
import type { TileArtSpec } from "./terrainArt";

const T = 52;

/** 灰燼荒原色票（需求第 2 節）。 */
export const ASH = {
  scorch: "#4a3a30", // 焦土（地板）
  char: "#2a1e18", // 炭黑（接縫、陰影）
  lavaGlow: "#ff6a1a", // 熔岩光（裂縫）
  ruin: "#6a5e54", // 殘牆
  ruinTop: "#7a6e64",
  ruinFace: "#5a4e44",
  dryGrass: "#8a7a48", // 枯草
  blade: "#b8a060",
  bladeLight: "#c8b070",
  ash: "#5a5450", // 灰燼
  ember: "#ff7a2a", // 餘燼亮點
  outline: "#1c1712",
} as const;

/** 裝飾光（裂縫熔岩光、餘燼點）出現的比例上限：同一張圖最多約 1/3 的格子有（規格 43.0 第 3 條）。 */
export const ASH_GLOW_RATE = 1 / 3;

/** 裂谷底部紅光的最大透明度（需求第 2 節：≤ 0.3）。 */
export const ASH_RIFT_GLOW_ALPHA = 0.28;

type TerrainDrawer = (ctx: Ctx, s: TileArtSpec) => void;

/** 這一格有沒有裝飾光（格子座標雜湊，固定）。 */
export function ashGlowAt(x: number, y: number, salt: number): boolean {
  return rng(x, y, salt)() < ASH_GLOW_RATE;
}

/** 焦土裂地：深褐地面、黑斑、細灰點；部分格子一道細熔岩光裂縫（先畫 3 寬黑縫，再疊 1.4 寬、模糊 5 的橘光）。 */
function ashStone(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 201);
  ctx.fillStyle = shade(ASH.scorch, 0.9 + r() * 0.2);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 5; i++) dot(ctx, r() * T, r() * T, 3 + r() * 5, "rgba(0,0,0,0.18)");
  for (let i = 0; i < 6; i++) dot(ctx, r() * T, r() * T, 1, "rgba(200,180,160,0.25)");
  if (ashGlowAt(s.x, s.y, 202)) {
    let px = r() * T;
    let py = 0;
    const pts: Array<readonly [number, number]> = [[px, py]];
    for (let i = 0; i < 5; i++) {
      px += (r() - 0.5) * 16;
      py += T / 5;
      pts.push([px, py]);
    }
    const trace = (): void => {
      pts.forEach(([a, b], i) => (i === 0 ? ctx.moveTo(a, b) : ctx.lineTo(a, b)));
    };
    ctx.strokeStyle = "#140c08";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.beginPath();
    trace();
    ctx.stroke();
    glowLine(ctx, ASH.lavaGlow, 1.4, 5, trace);
  }
  ctx.strokeStyle = "rgba(0,0,0,0.25)";
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, T - 1, T - 1);
}

/** 枯黃草。 */
function ashGrass(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 203);
  ctx.fillStyle = shade("#6e6040", 0.95 + r() * 0.1);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(255,240,200,0.05)" : "rgba(0,0,0,0.07)";
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 6 + r() * 8, r() * TAU, 0, TAU);
    ctx.fill();
  }
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  const n = 6 + Math.floor(r() * 4);
  for (let i = 0; i < n; i++) {
    const gx = 5 + r() * (T - 10);
    const gy = 8 + r() * (T - 13);
    ctx.strokeStyle = r() < 0.55 ? ASH.blade : "#5a4a2a";
    ctx.beginPath();
    ctx.moveTo(gx, gy);
    ctx.quadraticCurveTo(gx - 1, gy - 5, gx - 4, gy - 8);
    ctx.moveTo(gx, gy);
    ctx.quadraticCurveTo(gx + 1, gy - 5, gx + 4, gy - 9);
    ctx.stroke();
  }
}

/** 灰燼：灰色地面加深淺碎點。 */
function ashDirt(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 204);
  ctx.fillStyle = shade(ASH.ash, 0.94 + r() * 0.12);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 5 + r() * 7, r() * TAU, 0, TAU);
    ctx.fill();
  }
  for (let i = 0; i < 14; i++) {
    ctx.fillStyle = r() < 0.4 ? "rgba(210,200,190,0.35)" : "rgba(30,24,20,0.55)";
    ctx.fillRect(r() * T, r() * T, 1.8, 1.8);
  }
}

/** 焦黑岩壁：深色岩面加岩縫，偶爾有餘燼亮點；南鄰不是牆時畫更深的立面（比單位高）。 */
function ashWall(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 205);
  ctx.fillStyle = "#4a3e38";
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = "rgba(255,255,255,0.1)";
  ctx.fillRect(0, 0, T, 3);
  ctx.strokeStyle = "rgba(0,0,0,0.6)";
  ctx.lineWidth = 1.5;
  for (let i = 0; i < 4; i++) {
    const x = r() * T;
    ctx.beginPath();
    ctx.moveTo(x, r() * T * 0.3);
    ctx.lineTo(x + (r() - 0.5) * 10, T * 0.55);
    ctx.lineTo(x + (r() - 0.5) * 12, T);
    ctx.stroke();
  }
  if (ashGlowAt(s.x, s.y, 206)) {
    for (let i = 0; i < 3; i++) dot(ctx, 4 + r() * (T - 8), T * 0.25 + r() * T * 0.6, 1.3, ASH.ember);
  }
  if (s.wallFace) {
    ctx.fillStyle = "#2a221e";
    ctx.fillRect(0, T - 12, T, 12);
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.fillRect(0, T - 12, T, 2);
    ctx.strokeStyle = "rgba(0,0,0,0.6)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let k = 8 + r() * 6; k < T; k += 13 + r() * 6) {
      ctx.moveTo(k, T - 10);
      ctx.lineTo(k + (r() - 0.5) * 4, T);
    }
    ctx.stroke();
  }
}

function cliffLip(ctx: Ctx, r: () => number, p: readonly [number, number, number, number], n: readonly [number, number]): void {
  const [x0, y0, x1, y1] = p;
  ctx.fillStyle = "#3a302a";
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  const steps = 6;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const d = 3 + r() * 5;
    ctx.lineTo(x0 + (x1 - x0) * t + n[0] * d, y0 + (y1 - y0) * t + n[1] * d);
  }
  ctx.lineTo(x1, y1);
  ctx.closePath();
  ctx.fill();
  // 崖線：邊緣一條炭黑的線
  ctx.strokeStyle = "#140c08";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x0 + n[0] * 5, y0 + n[1] * 5);
  ctx.lineTo(x1 + n[0] * 5, y1 + n[1] * 5);
  ctx.stroke();
}

/** 黑色裂谷：近黑的深谷，底部只有淡淡的紅光（透明度 ≤ 0.3，只在格子下半）；邊緣有崖線。 */
function ashChasm(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 207);
  const g = ctx.createLinearGradient(0, 0, 0, T);
  g.addColorStop(0, "#0c0806");
  g.addColorStop(1, "#1a0a06");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  const glow = ctx.createRadialGradient(T / 2, T, 2, T / 2, T, T * 0.45);
  glow.addColorStop(0, rgba("#ff4a10", ASH_RIFT_GLOW_ALPHA));
  glow.addColorStop(1, rgba("#ff4a10", 0));
  ctx.fillStyle = glow;
  ctx.fillRect(0, T / 2, T, T / 2);
  if (s.lip.n) cliffLip(ctx, r, [0, 0, T, 0], [0, 1]);
  if (s.lip.s) cliffLip(ctx, r, [0, T, T, T], [0, -1]);
  if (s.lip.w) cliffLip(ctx, r, [0, 0, 0, T], [1, 0]);
  if (s.lip.e) cliffLip(ctx, r, [T, 0, T, T], [-1, 0]);
  if (s.lip.n) {
    const gg = ctx.createLinearGradient(0, 0, 0, 14);
    gg.addColorStop(0, "rgba(58,48,42,0.85)");
    gg.addColorStop(1, "rgba(58,48,42,0)");
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, 14);
  }
}

/** 岩漿（本區主場；6V-2）：照熔岩河的畫法——橘紅發光、亮黃熱紋、黑色岩殼裂紋、靠岸一圈冷卻黑殼；荒原底色略暗。 */
function ashLava(ctx: Ctx, s: TileArtSpec): void {
  drawLavaBase(ctx, s, 208, 0.92);
}

/** 灰水坑：暗灰的水，上面浮著灰膜；和地面相接的邊是焦土（深色水，致命）。 */
function ashIceHole(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 209);
  ctx.fillStyle = "#2c3034";
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = "rgba(150,140,130,0.35)";
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.ellipse(10 + r() * 32, 10 + r() * 32, 5 + r() * 4, 2 + r() * 2, r(), 0, TAU);
    ctx.fill();
  }
  ctx.strokeStyle = "rgba(255,255,255,0.22)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  const wy = 14 + r() * 20;
  ctx.moveTo(12, wy);
  ctx.quadraticCurveTo(20, wy - 4, 28, wy);
  ctx.stroke();
  ctx.fillStyle = ASH.scorch;
  if (s.lip.n) ctx.fillRect(0, 0, T, 4);
  if (s.lip.w) ctx.fillRect(0, 0, 4, T);
  if (s.lip.e) ctx.fillRect(T - 4, 0, 4, T);
  if (s.lip.s) ctx.fillRect(0, T - 4, T, 4);
}

/** 灰燼荒原的地形畫法（地形 ID → 畫法）；需求第 2 節「地形」七種。 */
export const ASHEN_TERRAIN: Readonly<Record<string, TerrainDrawer>> = {
  stone: ashStone,
  grass: ashGrass,
  dirt: ashDirt,
  wall: ashWall,
  chasm: ashChasm,
  lava: ashLava,
  ice_hole: ashIceHole,
};
