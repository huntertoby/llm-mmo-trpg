// 事件插圖的新場景 `awaken`（Phase RT-5 ①；docs/art/區域主題移植需求.md 第 5 節、樣張 docs/art/shots/misc/capital-opening.png 第 1 格）。
// 主城背景（RT-2 的白石板＋源晶燈＋遠處藍頂白牆）、中央傳送陣（地上的光圈＋發光晶柱）、五面區旗，
// 主角（玩家自己的紙娃娃外觀）在光圈裡：第 1 格躺著，第 2 格半坐起（減少動態時直接畫第 2 格）。
// 不是伺服器事件骨架的場景（不進 `EVENT_ART_IDS`）：主角外觀每個人不同，所以不走 `eventArtUrl` 的快取，直接畫在畫布上。
// 確定性：沒有亂數，擺法固定；畫法全部沿用 capitalArt（光圈、晶柱、區旗）與 paperdoll（紙娃娃），沒有另畫一套。
import type { DollSpec } from "./appearance";
import type { Ctx } from "./artDraw";
import { drawBanner, drawPortalPillar, drawPortalRing, PORTAL_TILES, REGION_ORDER, type CapitalRegion } from "./capitalArt";
import { capitalBackdrop, capitalTile } from "./eventArtCapital";
import { drawBadgeIcon, glow, T } from "./eventArtParts";
import { dollSkin } from "./inkStyle";
import type { InkPose } from "./inkPose";
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
 * 主角的擺法：原點位置（虛擬單位）、整個人的旋轉（弧度）、骨架姿勢（6M-1 的 `InkPose`；部件畫法不改）。
 * 躺著＝整個人轉 -1.5（仰躺、腳朝東、臉朝上），原點是腳底。
 * RT-5b（必修 4）：照樣張移到晶柱右側（頭不壓在晶柱上，也不壓光圈東北邊雲嶺那顆光點）。
 * RT-5c（必修 1，美術 PM）：半坐起原本整個人直直往後斜 24°、髖部沒彎，看起來像往後倒。改成髖部彎：整個人不轉，
 * 用既有骨架在髖部把兩條腿往前抬 90°（平貼地面、腳朝東），上半身以髖為軸往後仰約 20°，兩手往後撐地；
 * 再整個往下放 `drop`，讓屁股和腿貼在地上（坐著時原點＝髖部正下方的地面）。
 */
export interface AwakenHeroPlace {
  x: number;
  y: number;
  rot: number;
  pose: InkPose | null;
  /** 畫之前往下放多少（紙娃娃座標）。 */
  drop: number;
}

/**
 * 坐起：兩腿以髖為軸往前 90°（平貼地面），上身往後仰約 34°，兩手在髖部後方打直撐地。
 * RT-5d（必修 1，美術 PM）：RT-5c 的手停在髖部高度、沒碰到地。Q 版的手臂只到腰（肩到手約 8.9），上身後仰 30～35° 時肩膀離地約 14，
 * 原長怎麼轉都撐不到地，所以用骨架的臂長加量 `reach`／`reachF`（上臂、前臂沿方向拉長，手的大小不變）。
 * 數字由「手的下緣落在地面線上」反推：近側的手在髖後約 12.5、遠側的手再往後約 4（從近側的手後面露出來；兩條手臂都往後斜），
 * 遠側較遠、接地點在畫面上略高約 1 像素（遠側的手臂部件本來較短，又要伸得更後面，所以加量較多）。
 */
export const AWAKEN_SIT_POSE: Readonly<InkPose> = Object.freeze({
  hipN: Math.PI / 2,
  hipF: Math.PI / 2,
  lean: -0.6,
  arm: 1.37,
  reach: 0.55,
  armF: 1.87,
  reachF: 1.1,
});

/** 醒來的主角：武器先收起來（主手、副手都不畫，躺著、坐起兩格一樣），其他外觀照舊。 */
export function awakenHeroSpec(hero: DollSpec): DollSpec {
  if (hero.gear.main_hand === undefined && hero.gear.off_hand === undefined) return hero;
  const gear = { ...hero.gear };
  delete gear.main_hand;
  delete gear.off_hand;
  return { ...hero, gear };
}

export const AWAKEN_HERO: Readonly<Record<AwakenPose, AwakenHeroPlace>> = {
  0: { x: AWAKEN_RING.x + 96, y: AWAKEN_RING.y + 30, rot: -1.5, pose: null, drop: 0 },
  1: { x: AWAKEN_RING.x + 66, y: AWAKEN_RING.y + 44, rot: 0, pose: AWAKEN_SIT_POSE, drop: 13.5 },
};

/**
 * QK-2（恢復暫停畫面）：Q 版的半坐起。Q 版骨架的髖角正負與 C 相反（正值往後），而且上身後仰時整個人（含腿）一起繞髖轉，
 * 所以髖角要把後仰抵掉，腿才會平貼地面；Q 版腿短（8 單位）、髖在 −9。
 * QK-5（QK-2 檢查）：Q 版 `qDoll` 也吃臂長加量 `reach`／`reachF`（只有這一格用），上身後仰回到約 34°（原本 46°），
 * 兩手打直往後撐地：近側的手在髖後約 9.5、遠側再往後約 4；手的下緣落在地面線上（肩到手約 13.3、15.2，原長 10.5）。
 */
export const AWAKEN_SIT_POSE_Q: Readonly<InkPose> = Object.freeze({
  hipN: -0.5,
  hipF: -0.5,
  lean: -0.6,
  arm: 0.98,
  reach: 0.26,
  armF: 1.23,
  reachF: 0.45,
});

/** Q 版的擺法：位置與躺姿同 C，半坐起換 Q 版姿勢與下放量。 */
export const AWAKEN_HERO_Q: Readonly<Record<AwakenPose, AwakenHeroPlace>> = {
  0: AWAKEN_HERO[0],
  1: { ...AWAKEN_HERO[1], pose: AWAKEN_SIT_POSE_Q, drop: 4.5 },
};

/** 目前畫法的擺法（Q 版預設；C 只剩測試）。 */
export const awakenHero = (pose: AwakenPose): AwakenHeroPlace => (dollSkin() === "q" ? AWAKEN_HERO_Q : AWAKEN_HERO)[pose];

const BADGE_FONT = "bold 13px 'Noto Sans TC', 'Microsoft JhengHei', sans-serif";

function heroDoll(ctx: Ctx, hero: DollSpec, pose: AwakenPose): void {
  const p = awakenHero(pose);
  // 地上的影子（躺著時往頭那邊長；坐著時在屁股與腿下面）；Q 版人短（頭頂 38、C 53），影子跟著縮
  const q = dollSkin() === "q";
  ctx.fillStyle = "rgba(0,0,0,0.28)";
  ctx.beginPath();
  if (q) ctx.ellipse(p.x + (pose === 0 ? -21 : 2), p.y + 1, pose === 0 ? 28 : 18, 7, 0, 0, Math.PI * 2);
  else ctx.ellipse(p.x + (pose === 0 ? -30 : 8), p.y + 1, pose === 0 ? 40 : 28, 9, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.save();
  if (q && pose === 1) {
    // QK-5（QK-2 檢查）：半坐起時地面以下不畫（龍裔等的尾巴從髖後往下伸，不穿進地面；手、屁股的外框留 1.5）
    ctx.beginPath();
    ctx.rect(p.x - 200, p.y - 300, 400, 300 + 1.5 * 1.05);
    ctx.clip();
  }
  ctx.translate(p.x, p.y);
  if (p.rot !== 0) ctx.rotate(p.rot);
  ctx.scale(1.05, 1.05);
  if (p.drop !== 0) ctx.translate(0, p.drop);
  drawFigure(ctx, awakenHeroSpec(hero), "east", false, p.pose);
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
  drawBadgeIcon(ctx, "portal", 21, 20); /* QI-6：覺醒插圖的小牌也換 Q 版源晶（需求 4 第 3 點） */
  ctx.fillStyle = "#f2e6c8";
  ctx.textBaseline = "middle";
  ctx.fillText(place, 32, 21);
}
