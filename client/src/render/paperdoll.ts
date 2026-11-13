// 紙娃娃小人（Phase 3-16b；Phase C-1a 起骨架與四方向改為 C 手繪墨線畫法，見 inkDoll.ts、inkStyle.ts）。
// 這個檔案保留：圖騰柱、倒地姿勢、貼圖產生；外觀顏色解析在 itemColors.ts（這裡轉出口）。手持物、頭部裝備一律在 ink*.ts 以 C 畫法畫（Phase 3T-4 已刪掉舊畫法）。
// 座標：腳底中心為原點、往上為負；C 骨架身高約 52（尖帽到 -70）。
import type { Facing } from "../api/types";
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import { RARITY_GLOW, type DollSpec } from "./appearance";
import { drawInkFigure, type InkHooks } from "./inkDoll";
import { itemColors } from "./itemColors";
import type { InkPose } from "./inkPose";
import { dollSkin, type View } from "./inkStyle";
import { qStampLocal } from "./qStamp";
import { GAME_HOOKS, qPoseOf, qUnitOf } from "./qSpec";
import { whiteSilhouette } from "./creaturePose";
import { paintPartFx } from "./partLayer";

/** 離屏畫布的虛擬大小與腳底位置（虛擬像素）。 */
export const DOLL_W = 64;
export const DOLL_H = 92; // QK-5：腳底下多留 4（正面長槍刺向鏡頭時槍頭到腳底下 +8.5）； C 畫風頭頂最高約 -70（尖帽），要留夠；QK-1 的 Q 版只到約 -52，縮成 64 是選做，待 PM 決定（inkDoll.test 鎖著 ≥ 76）
export const DOLL_FOOT_Y = DOLL_H - 10;
/** 3U-2 之前的戰場縮放（0.74）；頭頂狀態列的位移以它為基準算增量。 */
export const DOLL_SCALE_OLD = 0.74;
/**
 * 戰場縮放：C 畫風 3U-2 定案 52px 格約 0.92 倍；QK-5 起 Q 版放大 1.15 倍 → 1.06（美術 PM 建議、使用者「不 照建議」）。
 * Q 版頭頂 38 → 52px 格約 40px，頭頂超出本格上緣一點；高帽（巫師帽、角盔）會伸進上一格，畫布上方的頭頂預留 28 不變。
 */
export const DOLL_SCALE = 1.06;
/** 野獸、物件類召喚物（用 64×64 舊畫布）的戰場縮放：舊的 1 → 1.15（3U-2）。 */
export const SUMMON_SCALE = 1.15;
/** 非人形召喚物（summonArt.ts 自己的畫法）沿用的畫布大小與腳底位置：舊的 64×64，不隨 C 骨架改。 */
export const SUMMON_W = 64;
export const SUMMON_H = 64;
export const SUMMON_FOOT_Y = SUMMON_H - 6;

export { itemColors };

/** 小人骨架取裝備顏色的掛勾。 */
const HOOKS: InkHooks = { colors: itemColors };

function fill(ctx: Ctx, color: string, path: () => void): void {
  ctx.fillStyle = color;
  ctx.beginPath();
  path();
  ctx.fill();
}

/** 圖騰柱（召喚的圖騰）：木柱＋刻出的臉＋頂端寶珠。 */
function drawTotem(ctx: Ctx): void {
  fill(ctx, "rgba(0,0,0,0.25)", () => ctx.ellipse(0, -1, 9, 3, 0, 0, TAU));
  fill(ctx, "#6e4620", () => rr(ctx, -6, -40, 12, 40, 2));
  fill(ctx, "#8f5f2c", () => rr(ctx, -6, -40, 4, 40, 2));
  fill(ctx, "#b77f3f", () => rr(ctx, -8, -28, 16, 5, 1));
  fill(ctx, "#b77f3f", () => rr(ctx, -8, -14, 16, 5, 1));
  ctx.fillStyle = "#1d1a22";
  ctx.fillRect(-4, -36, 2.4, 3);
  ctx.fillRect(1.6, -36, 2.4, 3);
  ctx.fillRect(-2.5, -31, 5, 1.4);
  fill(ctx, "rgba(143,240,226,0.4)", () => ctx.arc(0, -44, 6.5, 0, TAU));
  fill(ctx, "#8ff0e2", () => ctx.arc(0, -44, 3.6, 0, TAU));
  fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -45.2, 1.1, 0, TAU));
}

/** 畫一個小人（腳底中心在 (0, 0)）。facing：south ＝ 正面、north ＝ 背面、east／west ＝ 側面（西 ＝ 東的左右鏡像）。C 畫風（Phase C-1a）。 */
/** `pose`（6M-1）：骨架姿勢（inkPose.ts）；不給＝和加鉤子之前逐像素相同。圖騰柱不吃姿勢。 */
export function drawFigure(ctx: Ctx, spec: DollSpec, facing: Facing, ground = true, pose: InkPose | null = null): void {
  if (spec.totem === true) {
    drawTotem(ctx);
    return;
  }
  const view: View = facing === "north" ? "back" : facing === "south" ? "front" : "side";
  if (dollSkin() === "q") {
    // QK-1：Q 版純色＋剪影外框；地上影子在外框之外（深色橢圓），不算剪影
    if (ground) {
      ctx.fillStyle = "rgba(0,0,0,0.25)";
      ctx.beginPath();
      ctx.ellipse(0, 0, Q_SHADOW[0], Q_SHADOW[1], 0, 0, TAU);
      ctx.fill();
    }
    qStampLocal(ctx, qUnitOf(spec), view, facing === "west", GAME_HOOKS, qPoseOf(pose));
    return;
  }
  ctx.save();
  if (facing === "west") ctx.scale(-1, 1);
  drawInkFigure(ctx, spec, view, HOOKS, ground, pose);
  ctx.restore();
}

/** Q 版地上影子的半徑（同 closeups 的影子：38／3.4 × 7／3.4 單位）。 */
const Q_SHADOW = [11.2, 2.1] as const;

/** 倒地時橫躺的位置（旋轉前的平移量）。 */
const DOWNED_DX_C = 27;
const DOWNED_DX_Q = 19; // QK-1：Q 版身高 38（頭頂），橫躺時頭腳置中
const DOWNED_DY = 11;

/** 倒地姿勢：整個小人橫躺（頭朝右），腳底仍在原點附近。 */
export function drawFigurePose(ctx: Ctx, spec: DollSpec, facing: Facing, downed: boolean, ground = true, pose: InkPose | null = null): void {
  if (!downed || spec.totem === true) {
    drawFigure(ctx, spec, facing, ground, pose);
    return;
  }
  ctx.save();
  ctx.translate(-(dollSkin() === "q" ? DOWNED_DX_Q : DOWNED_DX_C), -DOWNED_DY);
  ctx.rotate(Math.PI / 2);
  drawFigure(ctx, spec, facing, false, pose);
  ctx.restore();
}

/**
 * 產生一張離屏 canvas（`dpr` 倍解析度；沒有 DOM 時回傳 `null`）。腳底在 (DOLL_W/2, DOLL_FOOT_Y)。
 * C 畫風沒有黑色剪影外框（墨線取代它）；史詩、傳說（頭目）保留外光，是唯一的身體外光。
 */
export function renderFigureCanvas(spec: DollSpec, facing: Facing, downed: boolean, dpr: number, ground = true, pose: InkPose | null = null, flash = 0): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const make = (): HTMLCanvasElement => {
    const c = document.createElement("canvas");
    c.width = DOLL_W * dpr;
    c.height = DOLL_H * dpr;
    return c;
  };
  const off = make();
  const o = off.getContext("2d");
  if (o === null) return null;
  o.scale(dpr, dpr);
  o.translate(DOLL_W / 2, DOLL_FOOT_Y);
  drawFigurePose(o, spec, facing, downed, ground, pose);
  if (flash > 0) {
    // 受擊白閃（6M-4，同 6M-3 異形）：另畫一次不含地上影子的身體，轉成白色剪影疊回去；剪影外不變白、外光不閃
    const body = make();
    const b = body.getContext("2d");
    if (b !== null) {
      b.scale(dpr, dpr);
      b.translate(DOLL_W / 2, DOLL_FOOT_Y);
      drawFigurePose(b, spec, facing, downed, false, pose);
      const img = b.getImageData(0, 0, body.width, body.height);
      whiteSilhouette(img.data, flash);
      b.putImageData(img, 0, 0);
      o.save();
      o.setTransform(1, 0, 0, 1, 0, 0); // 目標畫布已經縮放、平移到腳底：以像素疊回去
      o.drawImage(body, 0, 0);
      o.restore();
    }
  }
  // PB-1e：頭目部位破壞演出的前兩格（部位白閃、裂紋），疊在身體上、外光之前
  if (spec.parts?.fx !== undefined && !downed) paintPartFx(o, spec, facing, dpr, { w: DOLL_W, h: DOLL_H, footY: DOLL_FOOT_Y }, pose);
  const glowColor = spec.rarity !== undefined ? RARITY_GLOW[spec.rarity] : undefined;
  if (glowColor === undefined) return off;
  const glow = make();
  const g = glow.getContext("2d");
  const out = make();
  const ctx = out.getContext("2d");
  if (g === null || ctx === null) return off;
  g.drawImage(off, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = glowColor;
  g.fillRect(0, 0, glow.width, glow.height);
  ctx.save();
  ctx.globalAlpha = 0.5;
  for (let a = 0; a < 12; a++) {
    const ang = (a / 12) * TAU;
    ctx.drawImage(glow, Math.cos(ang) * 2.6 * dpr, Math.sin(ang) * 2.6 * dpr);
  }
  ctx.restore();
  ctx.drawImage(off, 0, 0);
  return out;
}
