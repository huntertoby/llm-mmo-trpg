// 戰場畫布的縮放與座標換算（Phase 3-8；純函式）。
// 畫布依可用空間等比縮放：繪製時仍用「模型像素」（每格 TILE_SIZE），畫面上的大小 ＝ 模型像素 × 縮放。
// 滑鼠事件一律由 DOM 的 client 座標與畫布實際的 `getBoundingClientRect()` 換算回格子，
// 縮放比例取自實際矩形（不依賴 Pixi 內部的換算），所以 CSS 怎麼縮放都對得上。
import type { Pos } from "../api/types";
import { pixelToTile, TILE_SIZE, type GridSize } from "./geometry";

export interface Size {
  width: number;
  height: number;
}

export interface ClientRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** 縮放的上下限：太小看不清、太大格子過粗（大螢幕上小地圖不必放到滿）。 */
export const MIN_SCALE = 0.5;
export const MAX_SCALE = 2;

/** 把 `grid` 等比放進 `avail`（保持格子正方形）的縮放比例，夾在 [min, max]；可用空間無效時回傳 1。 */
export function fitScale(
  avail: Size,
  grid: GridSize,
  tile = TILE_SIZE,
  min = MIN_SCALE,
  max = MAX_SCALE,
): number {
  const w = grid.width * tile;
  const h = grid.height * tile;
  if (w <= 0 || h <= 0 || !(avail.width > 0) || !(avail.height > 0)) return 1;
  const s = Math.min(avail.width / w, avail.height / h);
  return Math.max(min, Math.min(max, s));
}

/** 縮放後的畫布在畫面上的大小（整數像素，向下取整避免超出可用空間）。 */
export function scaledSize(grid: GridSize, scale: number, tile = TILE_SIZE): Size {
  return { width: Math.floor(grid.width * tile * scale), height: Math.floor(grid.height * tile * scale) };
}

/**
 * 滑鼠的 client 座標 → 格子。`rect` 是畫布元素在畫面上的實際矩形；x、y 方向的縮放分別由
 * 「實際寬高 ÷ 模型像素寬高」算出。在畫布外或格子範圍外回傳 `null`。
 */
export function clientToTile(
  clientX: number,
  clientY: number,
  rect: ClientRect,
  grid: GridSize,
  tile = TILE_SIZE,
): Pos | null {
  const modelW = grid.width * tile;
  const modelH = grid.height * tile;
  if (rect.width <= 0 || rect.height <= 0 || modelW <= 0 || modelH <= 0) return null;
  const px = ((clientX - rect.left) * modelW) / rect.width;
  const py = ((clientY - rect.top) * modelH) / rect.height;
  if (px >= modelW || py >= modelH) return null;
  return pixelToTile(px, py, grid, tile);
}

/** 反應詢問視窗一開始是否放在下方：觸發者在戰場上半部時放下方，免得視窗蓋住它（沒有觸發者時放上方）。 */
export function dialogStartsLow(focus: Pos | null, grid: GridSize): boolean {
  return focus !== null && focus.y + 0.5 <= grid.height / 2;
}

/** 浮動資訊卡相對於畫布左上角的位置（CSS 像素）；只有一邊的水平、一邊的垂直會有值。 */
export interface CardPlacement {
  left?: number;
  right?: number;
  top?: number;
  bottom?: number;
}

/** 浮動卡和格子之間的間距（CSS 像素）。 */
export const CARD_GAP = 8;

/**
 * 滑過單位時的浮動資訊卡位置：格子在左半邊時放在格子右側、右半邊時放在左側；
 * 上半邊時卡片頂端對齊格子頂端（往下長）、下半邊時卡片底端對齊格子底端（往上長），盡量不出畫布。
 */
export function cardPlacement(tile: Pos, grid: GridSize, scale: number, size = TILE_SIZE): CardPlacement {
  const t = size * scale;
  const out: CardPlacement = {};
  if (tile.x + 0.5 <= grid.width / 2) out.left = Math.round((tile.x + 1) * t + CARD_GAP);
  else out.right = Math.round((grid.width - tile.x) * t + CARD_GAP);
  if (tile.y + 0.5 <= grid.height / 2) out.top = Math.round(tile.y * t);
  else out.bottom = Math.round((grid.height - tile.y - 1) * t);
  return out;
}
