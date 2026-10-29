// 紙娃娃小人（Phase 3-16b；Phase C-1a 起骨架與四方向改為 C 手繪墨線畫法，見 inkDoll.ts、inkStyle.ts）。
// 這個檔案保留：外觀顏色解析（itemColors）、圖騰柱、倒地姿勢、貼圖產生。手持物、頭部裝備一律在 ink*.ts 以 C 畫法畫（Phase 3T-4 已刪掉舊畫法）。
// 座標：腳底中心為原點、往上為負；C 骨架身高約 52（尖帽到 -70）。
import type { Facing } from "../api/types";
import { roundRect as rr, TAU, type Ctx } from "./artDraw";
import { elementTint, RARITY_GLOW, type DollSpec, type GearItem } from "./appearance";
import { mix } from "./color";
import { drawInkFigure, type InkHooks } from "./inkDoll";
import { MATERIAL } from "./material";
import type { View } from "./inkStyle";

/** 離屏畫布的虛擬大小與腳底位置（虛擬像素）。 */
export const DOLL_W = 64;
export const DOLL_H = 88; // C 畫風頭頂最高約 -70（尖帽），要留夠
export const DOLL_FOOT_Y = DOLL_H - 6;
/** C 畫風的戰場縮放：52px 格約 0.74 倍，人約 40px 高（需求第 2 節）。 */
export const DOLL_SCALE = 0.74;
/** 非人形召喚物（summonArt.ts 自己的畫法）沿用的畫布大小與腳底位置：舊的 64×64，不隨 C 骨架改。 */
export const SUMMON_W = 64;
export const SUMMON_H = 64;
export const SUMMON_FOOT_Y = SUMMON_H - 6;

function darker(c: string, f = 0.68): string {
  return mix(c, "#000000", 1 - f);
}

/** 小人骨架取裝備顏色的掛勾。 */
const HOOKS: InkHooks = { colors: itemColors };

/** 一件裝備的 [主色, 暗色]：指定顏色或材質色（不認得 → 布料色），有元素時混入元素色 45%。 */
export function itemColors(item: GearItem): [string, string] {
  const base = MATERIAL[item.material ?? "cloth"] ?? MATERIAL.cloth!;
  let [main, dark]: [string, string] = item.color !== undefined ? [item.color, darker(item.color)] : [base[0], base[1]];
  const tint = elementTint(item.element);
  if (tint !== undefined) {
    main = mix(main, tint, 0.45);
    dark = mix(dark, tint, 0.3);
  }
  return [main, dark];
}

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
export function drawFigure(ctx: Ctx, spec: DollSpec, facing: Facing, ground = true): void {
  if (spec.totem === true) {
    drawTotem(ctx);
    return;
  }
  ctx.save();
  if (facing === "west") ctx.scale(-1, 1);
  const view: View = facing === "north" ? "back" : facing === "south" ? "front" : "side";
  drawInkFigure(ctx, spec, view, HOOKS, ground);
  ctx.restore();
}

/** 倒地時橫躺的位置（旋轉前的平移量）。 */
const DOWNED_DX = 27;
const DOWNED_DY = 11;

/** 倒地姿勢：整個小人橫躺（頭朝右），腳底仍在原點附近。 */
export function drawFigurePose(ctx: Ctx, spec: DollSpec, facing: Facing, downed: boolean): void {
  if (!downed || spec.totem === true) {
    drawFigure(ctx, spec, facing);
    return;
  }
  ctx.save();
  ctx.translate(-DOWNED_DX, -DOWNED_DY);
  ctx.rotate(Math.PI / 2);
  drawFigure(ctx, spec, facing, false);
  ctx.restore();
}

/**
 * 產生一張離屏 canvas（`dpr` 倍解析度；沒有 DOM 時回傳 `null`）。腳底在 (DOLL_W/2, DOLL_FOOT_Y)。
 * C 畫風沒有黑色剪影外框（墨線取代它）；史詩、傳說（頭目）保留外光，是唯一的身體外光。
 */
export function renderFigureCanvas(spec: DollSpec, facing: Facing, downed: boolean, dpr: number): HTMLCanvasElement | null {
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
  drawFigurePose(o, spec, facing, downed);
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
