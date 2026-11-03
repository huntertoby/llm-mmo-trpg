// 「霜潮海境」的地形畫法（Phase 5A-ART7；docs/art/四區移植需求.md 第 5 節；畫法移植自 docs/art/sample/regions4.js）。
// 沙岸、濕沙、淺海藍、浮冰白、礁石、珊瑚紅。整區地板是亮色系：牆（冰崖）和其他地形相接的邊一律 2px 深色外框，才不會糊在沙上。
// 功能特徵不變：冰崖比單位高、深海溝有沙色崖線、熱泉保留紅橘、冰窟（主場）是深色的水。
// 座標以 52 的虛擬格為單位（同 terrainArt 的 ART_T）。這個檔案不匯入 terrainArt 的值（避免循環匯入）；表由 terrainArt 組裝。
import { TAU, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";
import { rng } from "./artRandom";
import type { TileArtSpec } from "./terrainArt";

const T = 52;

/** 霜潮海境色票（需求第 5 節）。 */
export const FROST = {
  sand: "#d8c89a", // 沙岸
  wetSand: "#b8a478", // 濕沙
  sea: "#3f8ac8", // 淺海
  floe: "#cdeeff", // 浮冰
  reef: "#6a7a80", // 礁石
  coral: "#e8807a", // 珊瑚
  /** 牆與物件的深色外框（2px）。 */
  outline: "#18222a",
} as const;

/** 冰崖與物件外框的線寬（需求第 5 節：2px）。 */
export const FROST_OUTLINE_WIDTH = 2;

type TerrainDrawer = (ctx: Ctx, s: TileArtSpec) => void;

function speckle(ctx: Ctx, r: () => number, base: string, fleck: string, fleck2: string | null, n: number): void {
  ctx.fillStyle = shade(base, 0.94 + r() * 0.12);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 5 + r() * 7, r() * TAU, 0, TAU);
    ctx.fill();
  }
  for (let i = 0; i < n; i++) {
    ctx.fillStyle = fleck2 !== null && r() < 0.4 ? fleck2 : fleck;
    ctx.fillRect(r() * T, r() * T, 1.8, 1.8);
  }
}

/** 沙岸：沙色加深淺沙粒。 */
function frostStone(ctx: Ctx, s: TileArtSpec): void {
  speckle(ctx, rng(s.x, s.y, 501), FROST.sand, "rgba(122,106,72,0.5)", "rgba(255,255,255,0.5)", 12);
}

/** 海草灘：彎曲的海草。 */
function frostGrass(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 502);
  ctx.fillStyle = shade("#8a9a6a", 0.95 + r() * 0.1);
  ctx.fillRect(0, 0, T, T);
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  const n = 6 + Math.floor(r() * 4);
  for (let i = 0; i < n; i++) {
    const x = 5 + r() * (T - 10);
    const y = 12 + r() * (T - 17);
    ctx.strokeStyle = r() < 0.55 ? "#4a8a6a" : "#2e6a50";
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.bezierCurveTo(x - 3, y - 3, x + 3, y - 6, x, y - 9);
    ctx.stroke();
  }
}

/** 濕沙：深一點的沙，加兩道淺色波紋。 */
function frostDirt(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 503);
  speckle(ctx, r, FROST.wetSand, "rgba(90,74,48,0.5)", null, 8);
  ctx.strokeStyle = "rgba(255,255,255,0.3)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 2; i++) {
    const y = 14 + i * 20 + r() * 4;
    ctx.beginPath();
    ctx.moveTo(6, y);
    ctx.quadraticCurveTo(T / 2, y - 4, T - 6, y);
    ctx.stroke();
  }
}

/** 冰崖：頂面冰白、裂紋；南鄰不是牆時畫冰藍立面，頂緣垂著冰柱（比單位高）。和其他地形相接的邊畫 2px 深色外框。 */
function frostWall(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 504);
  ctx.fillStyle = "#e8f6ff";
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = "rgba(138,184,216,0.35)";
  for (let i = 0; i < 3; i++) {
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 6 + r() * 8, 3 + r() * 4, r() * TAU, 0, TAU);
    ctx.fill();
  }
  ctx.strokeStyle = "rgba(40,80,110,0.4)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let i = 0; i < 2; i++) {
    const x = 6 + r() * (T - 12);
    ctx.moveTo(x, 4 + r() * 10);
    ctx.lineTo(x + (r() - 0.5) * 12, T * 0.6);
  }
  ctx.stroke();
  if (s.wallFace) {
    const faceY = T - 14;
    ctx.fillStyle = "#8ab8d8";
    ctx.fillRect(0, faceY, T, 14);
    ctx.strokeStyle = "rgba(255,255,255,0.55)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let i = 0; i < 3; i++) {
      const x = 6 + r() * (T - 12);
      ctx.moveTo(x, faceY + 2);
      ctx.lineTo(x - 3, T);
    }
    ctx.stroke();
    // 頂緣冰柱
    ctx.fillStyle = "rgba(255,255,255,0.75)";
    for (let k = 4; k < T - 2; k += 9) {
      ctx.beginPath();
      ctx.moveTo(k, faceY);
      ctx.lineTo(k + 4, faceY);
      ctx.lineTo(k + 2, faceY + 5 + r() * 4);
      ctx.fill();
    }
    ctx.fillStyle = FROST.outline;
    ctx.fillRect(0, faceY - 1, T, 1.5);
  }
  // 2px 深色外框：只畫在和其他地形相接的邊（相連的冰崖接得起來）
  ctx.strokeStyle = FROST.outline;
  ctx.lineWidth = FROST_OUTLINE_WIDTH;
  ctx.beginPath();
  if (s.lip.n) {
    ctx.moveTo(0, 1);
    ctx.lineTo(T, 1);
  }
  if (s.lip.s || s.wallFace) {
    ctx.moveTo(0, T - 1);
    ctx.lineTo(T, T - 1);
  }
  if (s.lip.w) {
    ctx.moveTo(1, 0);
    ctx.lineTo(1, T);
  }
  if (s.lip.e) {
    ctx.moveTo(T - 1, 0);
    ctx.lineTo(T - 1, T);
  }
  ctx.stroke();
}

/** 深海溝：深藍漸層、兩道淡波紋；和其他地形相接的邊是沙色崖線（北緣加深的崖影）。 */
function frostChasm(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 505);
  const g = ctx.createLinearGradient(0, 0, 0, T);
  g.addColorStop(0, "#123a6a");
  g.addColorStop(1, "#061a34");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = "rgba(160,210,255,0.18)";
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 2; i++) {
    const y = 22 + i * 16 + r() * 4;
    ctx.beginPath();
    ctx.moveTo(8, y);
    ctx.quadraticCurveTo(T / 2, y - 4, T - 8, y);
    ctx.stroke();
  }
  ctx.fillStyle = "#c8b88a";
  if (s.lip.n) ctx.fillRect(0, 0, T, 9);
  if (s.lip.s) ctx.fillRect(0, T - 4, T, 4);
  if (s.lip.w) ctx.fillRect(0, 0, 4, T);
  if (s.lip.e) ctx.fillRect(T - 4, 0, 4, T);
  ctx.fillStyle = "rgba(0,0,0,0.5)";
  if (s.lip.n) ctx.fillRect(0, 9, T, 2);
}

/** 海底熱泉（少見）：紅橘岩漿上面多兩團白蒸氣。 */
function frostLava(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 506);
  ctx.fillStyle = "#d04010";
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 4; i++) {
    const cx = r() * T;
    const cy = r() * T;
    const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 18);
    gg.addColorStop(0, "#ffb030");
    gg.addColorStop(1, rgba("#ffb030", 0));
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, T);
  }
  for (let i = 0; i < 2; i++) {
    const cx = 10 + r() * 32;
    const cy = 10 + r() * 20;
    const gg = ctx.createRadialGradient(cx, cy, 1, cx, cy, 14);
    gg.addColorStop(0, "rgba(240,240,235,0.45)");
    gg.addColorStop(1, "rgba(240,240,235,0)");
    ctx.fillStyle = gg;
    ctx.fillRect(0, 0, T, T);
  }
}

/** 冰窟（主場）：深藍水；和其他地形相接的邊是冰白外框加淺藍內緣（深色水，致命）。 */
function frostIceHole(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 507);
  ctx.fillStyle = "#1e3a5a";
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = "rgba(255,255,255,0.3)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  const wy = 16 + r() * 18;
  ctx.moveTo(12, wy);
  ctx.quadraticCurveTo(20, wy - 4, 28, wy);
  ctx.stroke();
  const edge = (fill: string, d: number, w: number): void => {
    ctx.fillStyle = fill;
    if (s.lip.n) ctx.fillRect(0, d, T, w);
    if (s.lip.s) ctx.fillRect(0, T - d - w, T, w);
    if (s.lip.w) ctx.fillRect(d, 0, w, T);
    if (s.lip.e) ctx.fillRect(T - d - w, 0, w, T);
  };
  edge("#9ad0f0", 4, 3);
  edge("#e8f6ff", 0, 4);
}

/** 霜潮海境的地形畫法（地形 ID → 畫法）；需求第 5 節七種地形。 */
export const FROST_TERRAIN: Readonly<Record<string, TerrainDrawer>> = {
  stone: frostStone,
  grass: frostGrass,
  dirt: frostDirt,
  wall: frostWall,
  chasm: frostChasm,
  lava: frostLava,
  ice_hole: frostIceHole,
};
