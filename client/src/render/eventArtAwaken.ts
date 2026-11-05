// 事件插圖的新場景 `awaken`（Phase RT-5 ①；docs/art/區域主題移植需求.md 第 5 節、樣張 docs/art/capital-opening.png 第 1 格）。
// 主城背景（RT-2 的白石板＋源晶燈＋遠處藍頂白牆）、中央傳送陣（地上的光圈＋發光晶柱）、五面區旗，
// 主角（玩家自己的紙娃娃外觀）在光圈裡：第 1 格躺著，第 2 格半坐起（減少動態時直接畫第 2 格）。
// 不是伺服器事件骨架的場景（不進 `EVENT_ART_IDS`）：主角外觀每個人不同，所以不走 `eventArtUrl` 的快取，直接畫在畫布上。
// 確定性：沒有亂數，擺法固定；畫法全部沿用 capitalArt（光圈、晶柱、區旗）與 paperdoll（紙娃娃），沒有另畫一套。
import type { DollSpec } from "./appearance";
import type { Ctx } from "./artDraw";
import { drawBanner, drawPortalPillar, drawPortalRing, PORTAL_TILES, REGION_ORDER, type CapitalRegion } from "./capitalArt";
import { capitalBackdrop, capitalTile } from "./eventArtCapital";
import { BADGE_ICON_INK, glow, ICON, T } from "./eventArtParts";
import { drawFigure } from "./paperdoll";

/** 場景 ID（事件插圖的第 11 種，只在開場用）。 */
export const AWAKEN_ART = "awaken";
/** 8×4 格（比一般事件插圖的 7×3 大一圈，放得下傳送陣、五面區旗和躺著的主角）。 */
export const AWAKEN_COLS = 8;
export const AWAKEN_ROWS = 4;
export const AWAKEN_W = AWAKEN_COLS * T;
export const AWAKEN_H = AWAKEN_ROWS * T;

/** 兩格動作：0＝躺著、1＝半坐起。 */
export type AwakenPose = 0 | 1;
/** 第 1 格（躺著）停多久才換第 2 格（毫秒）。 */
export const AWAKEN_LIE_MS = 900;

/** 傳送陣中心（虛擬單位）。 */
export const AWAKEN_RING = { x: 4 * T, y: 2.05 * T } as const;

/**
 * 五面區旗的位置（旗子畫布的左上角，格；畫布 1×2、旗杆立在下面那格的中央），順序同 `REGION_ORDER`
 *（晶冠、雲嶺、樞市、灰燼、霜潮）：圍著傳送陣的後半圈，左右兩面稍微往前，不擋主角。
 * RT-5b（必修 4）：晶冠那面原本在正後方，旗桿穿過遠處的藍頂建築（`distantHall`，4.2～5.7 格）；改到晶柱左後方，
 * 旗桿與旗面都在建築左邊、也不碰晶柱。
 */
export const AWAKEN_BANNERS: Readonly<Record<CapitalRegion, readonly [number, number]>> = {
  crystal_crown: [2.75, -0.75],
  cloud_ridge: [1.6, 0.25],
  arcane_hub: [6.0, 0.25],
  ashen_waste: [0.55, 1.35],
  frost_tide: [7.05, 1.35],
};

/**
 * 主角的擺法：腳底位置（虛擬單位）、旋轉（弧度；側面朝東的紙娃娃往後倒＝負）。躺著＝仰躺、腳朝東、臉朝上；
 * 半坐起＝上身往後仰（紙娃娃部件不改，只轉整個人）。
 * RT-5b（必修 4，美術 PM 2c）：照樣張移到晶柱右側（頭不壓在晶柱上），半坐起的角度改小（約 24°），看得出是在坐起來；
 * 往下一點，頭也不壓在光圈東北邊雲嶺那顆光點上。
 */
export const AWAKEN_HERO: Readonly<Record<AwakenPose, { x: number; y: number; rot: number }>> = {
  0: { x: AWAKEN_RING.x + 96, y: AWAKEN_RING.y + 30, rot: -1.5 },
  1: { x: AWAKEN_RING.x + 80, y: AWAKEN_RING.y + 46, rot: -0.42 },
};

const BADGE_FONT = "bold 13px 'Noto Sans TC', 'Microsoft JhengHei', sans-serif";

function heroDoll(ctx: Ctx, hero: DollSpec, pose: AwakenPose): void {
  const p = AWAKEN_HERO[pose];
  // 地上的影子（身體平躺時長、坐起時短）
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.beginPath();
  ctx.ellipse(p.x - (pose === 0 ? 30 : 16), p.y + 1, pose === 0 ? 40 : 26, 9, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.rotate(p.rot);
  ctx.scale(1.05, 1.05);
  drawFigure(ctx, hero, "east", false);
  ctx.restore();
}

/**
 * 畫 `awaken` 插圖（左上角在原點、大小 AWAKEN_W×AWAKEN_H）。`open`＝已開放的區（光圈亮該區顏色，同主城實地圖）；
 * `place`＝左上角小牌的地名（例「樞島・中央廣場」，空字串＝不畫小牌）。
 */
export function drawAwakenArt(ctx: Ctx, hero: DollSpec, pose: AwakenPose, open: readonly string[], place: string): void {
  const W = AWAKEN_W;
  const H = AWAKEN_H;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(0, 0, W, H, 12);
  ctx.clip();
  for (let gy = 0; gy < AWAKEN_ROWS; gy++) for (let gx = 0; gx < AWAKEN_COLS; gx++) capitalTile(ctx, gx, gy);
  capitalBackdrop(ctx);
  // 傳送陣：地上的光圈（3×3 格畫布、中心在傳送石）＋整圈紫光
  glow(ctx, AWAKEN_RING.x, AWAKEN_RING.y, 150, "rgba(168,152,255,0.9)", 0.42);
  ctx.save();
  ctx.translate(AWAKEN_RING.x - (PORTAL_TILES * T) / 2, AWAKEN_RING.y - (PORTAL_TILES * T) / 2);
  drawPortalRing(ctx, open);
  ctx.restore();
  for (const region of REGION_ORDER) {
    const [bx, by] = AWAKEN_BANNERS[region];
    if (by > 0.5) continue; // 前排兩面最後畫（在主角前面）
    ctx.save();
    ctx.translate(bx * T, by * T);
    drawBanner(ctx, region);
    ctx.restore();
  }
  // 晶柱（1×2 格畫布，下面那格＝傳送石）：還在低鳴（多一層光）
  ctx.save();
  ctx.translate(AWAKEN_RING.x - T / 2, AWAKEN_RING.y - T * 1.5 - 8);
  drawPortalPillar(ctx);
  ctx.restore();
  glow(ctx, AWAKEN_RING.x, AWAKEN_RING.y - 40, 46, "rgba(200,188,255,0.95)", 0.45);
  heroDoll(ctx, hero, pose);
  for (const region of REGION_ORDER) {
    const [bx, by] = AWAKEN_BANNERS[region];
    if (by <= 0.5) continue;
    ctx.save();
    ctx.translate(bx * T, by * T);
    drawBanner(ctx, region);
    ctx.restore();
  }
  // 四周暗角（剛醒來：中央亮、四周暗）
  const v = ctx.createRadialGradient(AWAKEN_RING.x, AWAKEN_RING.y, H * 0.42, AWAKEN_RING.x, AWAKEN_RING.y, W * 0.62);
  v.addColorStop(0, "rgba(0,0,0,0)");
  v.addColorStop(1, "rgba(10,12,30,0.62)");
  ctx.fillStyle = v;
  ctx.fillRect(0, 0, W, H);
  ctx.restore();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#c8a868";
  ctx.beginPath();
  ctx.roundRect(1, 1, W - 2, H - 2, 12);
  ctx.stroke();
  if (place === "") return;
  ctx.font = BADGE_FONT;
  const measured = ctx.measureText(place) as TextMetrics | undefined;
  const tw = (measured?.width ?? place.length * 13) + 34;
  ctx.fillStyle = "rgba(16,18,34,0.88)";
  ctx.beginPath();
  ctx.roundRect(8, 8, tw, 24, 12);
  ctx.fill();
  ctx.strokeStyle = "#c8a868";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ICON.portal(ctx, 21, 20, 13, BADGE_ICON_INK);
  ctx.fillStyle = "#f2e6c8";
  ctx.textBaseline = "middle";
  ctx.fillText(place, 32, 21);
}
