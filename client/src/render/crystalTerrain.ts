// 「晶冠城邦」的地形點綴（Phase 5A-ART6；docs/art/四區移植需求.md 第 3 節；畫法移植自 docs/art/sample/regions4.js）。
// 晶冠就是預設畫法，只多幾樣點綴；而且只在地圖明確是 `crystal_crown` 時才畫（`region` 空字串照預設，不跟著變）。
// 石板與深淵＝預設畫法再疊點綴；城牆換成白石城牆＋金邊。草、土、岩漿、冰窟不在表內（退回預設）。
// 這個檔案不匯入 terrainArt 的值（避免循環匯入）：預設畫法由 terrainArt 傳進 `crystalTerrain`。
import { dot, type Ctx } from "./artDraw";
import { hash, rng } from "./artRandom";
import type { TileArtSpec } from "./terrainArt";

const T = 52;

/** 晶冠色票（需求第 3 節）。 */
export const CRYSTAL = {
  slab: "#d8ccb0", // 石板
  gap: "#a89a7c", // 接縫
  glint: "#8f7bff", // 晶光
  banner: "#3a5ad0", // 旗藍
  gold: "#e8bb48", // 金飾
  outline: "#1c1712",
} as const;

type TerrainDrawer = (ctx: Ctx, s: TileArtSpec) => void;

/** 這一格石板有沒有金色菱形嵌線（約 1/7 的格子，格子座標雜湊，固定）。 */
export function crystalInlayAt(x: number, y: number): boolean {
  return hash(x, y, 301) % 7 === 0;
}

/** 主城石板的嵌線比例（6Q-1：從約 1/7 降到約 1/12，避免菱形框像格子標記）。 */
export const CAPITAL_INLAY_EVERY = 12;
/** 主城嵌線的線色：金飾色降低透明度（6Q-1）。 */
export const CAPITAL_INLAY_STROKE = "rgba(232,187,72,0.45)";
/** 主城嵌線中心晶光點的顏色（同樣降低透明度）。 */
export const CAPITAL_INLAY_GLINT = "rgba(143,123,255,0.5)";

/** 主城這一格石板有沒有金色嵌線（約 1/12 的格子，格子座標雜湊，固定）。 */
export function capitalInlayAt(x: number, y: number): boolean {
  return hash(x, y, 301) % CAPITAL_INLAY_EVERY === 0;
}

/** 嵌線的樣式：哪些格子畫、線與晶光點的顏色。 */
export interface InlayStyle {
  at: (x: number, y: number) => boolean;
  stroke: string;
  glint: string;
}

const CROWN_INLAY: InlayStyle = { at: crystalInlayAt, stroke: CRYSTAL.gold, glint: CRYSTAL.glint };
/** 主城的嵌線樣式（6Q-1）。 */
export const CAPITAL_INLAY: InlayStyle = { at: capitalInlayAt, stroke: CAPITAL_INLAY_STROKE, glint: CAPITAL_INLAY_GLINT };

/** 金色菱形嵌線（1.5 寬）＋中心一個晶光點。 */
function inlay(ctx: Ctx, s: TileArtSpec, style: InlayStyle): void {
  if (!style.at(s.x, s.y)) return;
  ctx.strokeStyle = style.stroke;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(T / 2, 6);
  ctx.lineTo(T - 6, T / 2);
  ctx.lineTo(T / 2, T - 6);
  ctx.lineTo(6, T / 2);
  ctx.closePath();
  ctx.stroke();
  dot(ctx, T / 2, T / 2, 2.5, style.glint);
}

/** 深淵上的 4 個晶光碎點（避開北緣崖線）。 */
function voidGlints(ctx: Ctx, s: TileArtSpec): void {
  const r = rng(s.x, s.y, 302);
  for (let i = 0; i < 4; i++) dot(ctx, 4 + r() * (T - 8), 14 + r() * (T - 18), 1.2, CRYSTAL.glint);
}

/** 白石城牆：頂面米白錯縫磚；南鄰不是牆時畫正面，頂面和正面之間一條金邊（比單位高）。 */
function crystalWall(ctx: Ctx, s: TileArtSpec): void {
  ctx.fillStyle = "#e8dcc0";
  ctx.fillRect(0, 0, T, T);
  ctx.fillStyle = "rgba(255,255,255,0.2)";
  ctx.fillRect(0, 0, T, 3);
  ctx.strokeStyle = "rgba(90,74,50,0.5)";
  ctx.lineWidth = 1.5;
  const rows = 4;
  const rh = T / rows;
  ctx.beginPath();
  for (let i = 1; i < rows; i++) {
    ctx.moveTo(0, i * rh);
    ctx.lineTo(T, i * rh);
  }
  for (let i = 0; i < rows; i++) {
    for (let bx = i % 2 === 0 ? T / 4 : T / 2; bx < T; bx += T / 2) {
      ctx.moveTo(bx, i * rh);
      ctx.lineTo(bx, (i + 1) * rh);
    }
  }
  ctx.stroke();
  if (s.wallFace) {
    ctx.fillStyle = "#b8aa8a";
    ctx.fillRect(0, T - 10, T, 10);
    ctx.strokeStyle = "rgba(90,74,50,0.6)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let bx = 9; bx < T; bx += 13) {
      ctx.moveTo(bx, T - 10);
      ctx.lineTo(bx, T);
    }
    ctx.stroke();
    ctx.fillStyle = CRYSTAL.gold; // 金邊
    ctx.fillRect(0, T - 12, T, 2);
  }
}

/** 晶冠的地形畫法表：`base` 是預設畫法（由 terrainArt 傳入），石板與深淵在預設上疊點綴。 */
export function crystalTerrain(
  base: { stone: TerrainDrawer; chasm: TerrainDrawer },
  inlayStyle: InlayStyle = CROWN_INLAY,
): Readonly<Record<string, TerrainDrawer>> {
  return {
    stone: (ctx, s) => {
      base.stone(ctx, s);
      inlay(ctx, s, inlayStyle);
    },
    wall: crystalWall,
    chasm: (ctx, s) => {
      base.chasm(ctx, s);
      voidGlints(ctx, s);
    },
  };
}
