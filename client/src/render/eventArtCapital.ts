// 事件插圖的主城背景（Phase RT-2；需求 docs/art/區域主題移植需求.md 第 2 節，樣子照 docs/art/region-themes.png 右欄）。
// 不另畫一套：地面用主城實地圖的石板畫法（terrainArt 的 `capital` 區，6D-ART2；嵌線密度照 6Q-1 的 CAPITAL_INLAY），
// 源晶燈與藍頂白牆用 capitalArt 的 `drawCrystalLamp`、`paintBuilding`。確定性：沒有亂數，擺法固定。
import type { Ctx } from "./artDraw";
import { drawCrystalLamp, paintBuilding } from "./capitalArt";
import { T } from "./eventArtParts";
import { drawTile, type TileArtSpec } from "./terrainArt";

const NO_SIDES = { n: false, s: false, w: false, e: false };

/** 主城地面一格（主城實地圖的石板＋金色嵌線）。 */
export function capitalTile(ctx: Ctx, gx: number, gy: number): void {
  const spec: TileArtSpec = {
    region: "capital",
    look: "",
    terrain: "stone",
    x: gx,
    y: gy,
    height: 0,
    surface: "none",
    surfSame: NO_SIDES,
    lip: NO_SIDES,
    wallFace: false,
    blocked: false,
    tint: null,
  };
  ctx.save();
  ctx.translate(gx * T, gy * T);
  drawTile(ctx, spec);
  ctx.restore();
}

/**
 * 兩盞源晶燈的位置（燈畫布的左上角，虛擬單位；畫布 1×2 格、下面那格是燈座；畫時縮成 0.8）：
 * 左邊那盞避開左上角的事件小牌、放低一點；右邊那盞在最上一列的右端。
 */
export const CAPITAL_LAMPS: readonly (readonly [number, number])[] = [
  [0.25 * T, 0.2 * T],
  [6.1 * T, -0.3 * T],
];

/** 石板上的一層米白（實地圖的石板偏灰；插圖縮小後要讀成「白石板」，照 region-themes.png 右欄）。 */
export const CAPITAL_WASH = "rgba(255,248,232,0.28)";

/** 遠處藍頂白牆一角：一棟 3 格寬的白石廳，縮小放在右上角、一部分在畫面外。 */
function distantHall(ctx: Ctx): void {
  ctx.save();
  ctx.translate(4.2 * T, -0.05 * T);
  ctx.scale(0.55, 0.55);
  paintBuilding(ctx, { kind: "stone_hall", w: 3, h: 1, doors: [1], sign: null });
  ctx.restore();
}

/** 主城背景的點綴（地面之上、場景之下）：石板提亮、遠處的藍頂白牆一角、兩盞源晶燈。 */
export function capitalBackdrop(ctx: Ctx): void {
  ctx.fillStyle = CAPITAL_WASH;
  ctx.fillRect(0, 0, 7 * T, 3 * T);
  distantHall(ctx);
  for (const [x, y] of CAPITAL_LAMPS) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(0.8, 0.8);
    drawCrystalLamp(ctx);
    ctx.restore();
  }
}
