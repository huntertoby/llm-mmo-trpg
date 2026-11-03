// 「魔導樞市」的地形畫法（Phase 5A-ART7；docs/art/四區移植需求.md 第 4 節；畫法移植自 docs/art/sample/regions4.js）。
// 鐵板、煤黑、黃銅、晶能青、符文橘。晶能線只是裝飾：約 1/3 的格子有、2 寬、模糊 6、半透明，比導電提示與技能特效暗。
// 功能特徵不變：牆比單位高、豎井有崖線、熔爐槽保留紅橘、冷卻槽是致命的冰藍液體（靠黃銅邊和格子區分）。
// 座標以 52 的虛擬格為單位（同 terrainArt 的 ART_T）。這個檔案不匯入 terrainArt 的值（避免循環匯入）；表由 terrainArt 組裝。
import { dot, glowLine, roundRect, type Ctx } from "./artDraw";
import { rgba, shade } from "./color";
import { hash, rng } from "./artRandom";
import type { TileArtSpec } from "./terrainArt";

const T = 52;

/** 魔導樞市色票（需求第 4 節）。 */
export const ARCANE = {
  plate: "#4a4238", // 鐵板
  coal: "#2a241e", // 煤黑
  brass: "#b08a4a", // 黃銅
  energy: "#4ae0d0", // 晶能
  rune: "#e8a040", // 符文
  iron: "#5a5248", // 鐵框、崖緣
  coolant: "#2a7a9a", // 冷卻槽液體
  outline: "#1c1712",
} as const;

/** 晶能線的參數：2 寬、模糊 6；顏色用半透明的晶能青（比導電提示、技能特效暗）。 */
export const ARCANE_LINE = { width: 2, blur: 6, alpha: 0.55 } as const;

type TerrainDrawer = (ctx: Ctx, s: TileArtSpec) => void;

/** 這一格鐵板有沒有晶能線（約 1/3 的格子，格子座標雜湊，固定）。 */
export function arcaneLineAt(x: number, y: number): boolean {
  return hash(x, y, 401) % 3 === 0;
}

/** 鉚釘鐵板：四角黃銅鉚釘；約 1/3 的格子有一條轉折的晶能線。 */
function arcaneStone(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 402);
  ctx.fillStyle = shade(ARCANE.plate, 0.94 + r() * 0.12);
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = ARCANE.coal;
  ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, T - 2, T - 2);
  ctx.fillStyle = "rgba(255,255,255,0.08)";
  ctx.fillRect(3, 3, T - 6, 2);
  for (const [dx, dy] of [[5, 5], [T - 5, 5], [5, T - 5], [T - 5, T - 5]] as const) {
    dot(ctx, dx, dy, 2, ARCANE.brass);
    dot(ctx, dx - 0.6, dy - 0.6, 0.8, "rgba(255,255,255,0.5)");
  }
  if (arcaneLineAt(s.x, s.y)) {
    const horiz = r() < 0.5;
    glowLine(ctx, rgba(ARCANE.energy, ARCANE_LINE.alpha), ARCANE_LINE.width, ARCANE_LINE.blur, () => {
      if (horiz) {
        ctx.moveTo(0, T / 2);
        ctx.lineTo(T * 0.4, T / 2);
        ctx.lineTo(T * 0.5, T * 0.38);
        ctx.lineTo(T, T * 0.38);
      } else {
        ctx.moveTo(T / 2, 0);
        ctx.lineTo(T / 2, T * 0.6);
        ctx.lineTo(T * 0.62, T * 0.7);
        ctx.lineTo(T * 0.62, T);
      }
    });
  }
}

/** 鐵格柵下的苔草。 */
function arcaneGrass(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 403);
  ctx.fillStyle = shade("#3e4a34", 0.95 + r() * 0.1);
  ctx.fillRect(0, 0, T, T);
  ctx.lineWidth = 1.5;
  ctx.lineCap = "round";
  const n = 6 + Math.floor(r() * 4);
  for (let i = 0; i < n; i++) {
    const x = 5 + r() * (T - 10);
    const y = 8 + r() * (T - 13);
    ctx.strokeStyle = r() < 0.55 ? "#7aa060" : "#4a6a3a";
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x - 1, y - 5, x - 4, y - 8);
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x + 1, y - 5, x + 4, y - 9);
    ctx.stroke();
  }
  // 格柵蓋在苔草上面
  ctx.strokeStyle = ARCANE.coal;
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let k = 6; k < T; k += 10) {
    ctx.moveTo(k, 0);
    ctx.lineTo(k, T);
  }
  ctx.stroke();
  ctx.strokeRect(1, 1, T - 2, T - 2);
}

/** 煤渣地：黑點加少量黃銅屑。 */
function arcaneDirt(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 404);
  ctx.fillStyle = shade("#3a3430", 0.94 + r() * 0.12);
  ctx.fillRect(0, 0, T, T);
  for (let i = 0; i < 3; i++) {
    ctx.fillStyle = r() < 0.5 ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.07)";
    ctx.beginPath();
    ctx.ellipse(r() * T, r() * T, 8 + r() * 10, 5 + r() * 7, r() * Math.PI * 2, 0, Math.PI * 2);
    ctx.fill();
  }
  for (let i = 0; i < 16; i++) {
    ctx.fillStyle = r() < 0.4 ? "rgba(176,138,74,0.4)" : "rgba(10,8,6,0.6)";
    ctx.fillRect(r() * T, r() * T, 1.8, 1.8);
  }
}

/** 鐵壁：分板、鉚釘；南鄰不是牆時畫深色立面，下段一條黃銅管線（比單位高）。 */
function arcaneWall(ctx: Ctx, s: TileArtSpec): void {
  ctx.fillStyle = ARCANE.iron;
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = "rgba(255,255,255,0.14)";
  ctx.fillRect(0, 0, T, 3);
  ctx.strokeStyle = "rgba(0,0,0,0.55)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (const k of [T * 0.33, T * 0.66]) {
    ctx.moveTo(k, 0);
    ctx.lineTo(k, T);
  }
  ctx.moveTo(0, T / 2);
  ctx.lineTo(T, T / 2);
  ctx.stroke();
  for (const y of [6, T / 2 + 6]) for (const k of [8, T / 2, T - 8]) dot(ctx, k, y, 1.8, ARCANE.brass);
  if (s.wallFace) {
    ctx.fillStyle = "#3a342c";
    ctx.fillRect(0, T - 12, T, 12);
    ctx.fillStyle = "rgba(0,0,0,0.3)";
    ctx.fillRect(0, T - 12, T, 2);
    ctx.fillStyle = ARCANE.brass;
    ctx.fillRect(0, T - 8, T, 5);
    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.fillRect(0, T - 8, T, 1.5);
  }
}

/** 崖緣：和其他地形相接的那一邊是鐵框，邊緣一條煤黑的崖線。 */
function shaftLip(ctx: Ctx, s: TileArtSpec): void {
  ctx.fillStyle = ARCANE.iron;
  if (s.lip.n) ctx.fillRect(0, 0, T, 9);
  if (s.lip.s) ctx.fillRect(0, T - 5, T, 5);
  if (s.lip.w) ctx.fillRect(0, 0, 5, T);
  if (s.lip.e) ctx.fillRect(T - 5, 0, 5, T);
  ctx.fillStyle = "rgba(0,0,0,0.5)";
  if (s.lip.n) ctx.fillRect(0, 9, T, 2);
  if (s.lip.n) for (const k of [6, T / 2, T - 6]) dot(ctx, k, 4.5, 1.5, ARCANE.brass);
}

/** 機械豎井：深色井底，兩條黃銅管線，幾個晶能光點；邊緣有崖線。 */
function arcaneChasm(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 405);
  const g = ctx.createLinearGradient(0, 0, 0, T);
  g.addColorStop(0, "#14181a");
  g.addColorStop(1, "#06080a");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, T, T);
  ctx.strokeStyle = rgba(ARCANE.brass, 0.55);
  ctx.lineWidth = 3;
  ctx.beginPath();
  for (const k of [12, 40]) {
    ctx.moveTo(k, 0);
    ctx.lineTo(k, T);
  }
  ctx.stroke();
  for (let i = 0; i < 3; i++) dot(ctx, 8 + r() * (T - 16), 20 + r() * 28, 1.6, rgba(ARCANE.energy, 0.7));
  shaftLip(ctx, s);
}

/** 熔爐槽：岩漿（紅橘）外圍是鐵框，四角鉚釘。 */
function arcaneLava(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 406);
  ctx.fillStyle = "#e0400a";
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
  ctx.strokeStyle = ARCANE.iron;
  ctx.lineWidth = 4;
  ctx.strokeRect(2, 2, T - 4, T - 4);
  for (const [dx, dy] of [[5, 5], [T - 5, 5], [5, T - 5], [T - 5, T - 5]] as const) dot(ctx, dx, dy, 1.6, "#d8b070");
}

/** 冷卻槽：冰藍液體 #2a7a9a，外圍黃銅邊（每格一個槽，靠黃銅邊和格子區分；致命）。 */
function arcaneIceHole(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 407);
  ctx.fillStyle = ARCANE.plate;
  ctx.fillRect(0, 0, T, T);
  roundRect(ctx, 4, 4, T - 8, T - 8, 10);
  ctx.fillStyle = ARCANE.coolant;
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = ARCANE.brass;
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,0.3)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  const wy = 16 + r() * 18;
  ctx.moveTo(12, wy);
  ctx.quadraticCurveTo(20, wy - 4, 28, wy);
  ctx.stroke();
}

/** 魔導樞市的地形畫法（地形 ID → 畫法）；需求第 4 節七種地形。 */
export const ARCANE_TERRAIN: Readonly<Record<string, TerrainDrawer>> = {
  stone: arcaneStone,
  grass: arcaneGrass,
  dirt: arcaneDirt,
  wall: arcaneWall,
  chasm: arcaneChasm,
  lava: arcaneLava,
  ice_hole: arcaneIceHole,
};
