// BM-1（美術 PM GB A5 審查，`docs/art/GB巨型頭目-移植需求.md` 第 8 節第 2 條）：延遲預告格右上角的小字（「蓄」「炸」「爆」、倒數數字…）
// 在 800 寬地圖縮小時跟著縮（字級 12 → 畫面約 6 px），讀不出來。改成和其他標記一樣有最小畫面尺寸（`minMark.minMarkScale`）：
// 圓底與字等比反向放大；**錨在格子角**：圓上離格子中心最近的那一點不動，往右上（格子角的方向）長，所以不會比 1600 寬多蓋到格子裡的人頭；
// 倍率另設上限 `TELEGRAPH_BADGE_MAX_K`（圓心不超出格子），地圖再小也不會長到蓋過隔壁格。
//
// 純函式；`HighlightLayer.setHighlights` 建節點、`telegraphRescale`（縮放改變時）重排。

import { TILE_SIZE } from "../battle/geometry";
import { minMarkScale } from "./minMark";

const T = TILE_SIZE;
/** 預告字節點（圓底＋字）的標籤（測試用）。 */
export const TELEGRAPH_BADGE_LABEL = "telegraph-badge";
/** 預告字的字級（世界座標，1600 寬照原本）。 */
export const TELEGRAPH_FONT = 12;
/** 預告字的圓底半徑（世界座標）。 */
export const TELEGRAPH_BADGE_R = 9;
/** 圓心離格子右上角的距離（世界座標，x 往左、y 往下各 11）。 */
export const TELEGRAPH_BADGE_INSET = 11;
/**
 * 預告字在畫面上至少幾 px：照美術 PM GB A5 審查第 8 節第 2 條「畫面字 ≥10 px」（和狀態圖示、高度標記、召喚物回合數同一個下限）。
 * 不用「破」字記號的 12 px：預告字底下有黑圓襯底、字色是飽和的警示色；12 px 在 800 寬（地圖 0.53）要放大 ×1.89，圓的直徑
 * 約佔一格的 71%，會蓋過格子裡的人頭（同一條「設上限不蓋目標頭」）。
 */
export const MIN_TELEGRAPH_FONT_PX = 10;
/** 倍率上限（地圖縮放 < 0.42 才用到）：×2 時圓心仍在格子裡（離右緣約 4.6、上緣約 4.6），圓最多伸出格子約 13。 */
export const TELEGRAPH_BADGE_MAX_K = 2;

/** 這個地圖縮放下預告字（與圓底）的倍率：畫面字 ≥ `MIN_TELEGRAPH_FONT_PX`，不超過上限；地圖夠大時 1。 */
export function telegraphBadgeScale(boardScale: number): number {
  return Math.min(TELEGRAPH_BADGE_MAX_K, minMarkScale(TELEGRAPH_FONT, MIN_TELEGRAPH_FONT_PX, boardScale));
}

/**
 * 倍率 `k` 時圓心相對格子左上角的位置（世界座標）：`k = 1` 是原本的 (T − 11, 11)；放大時圓上朝格子中心那一點（左下 45°）不動，
 * 圓心沿右上 45° 往格子角移 `R × (k − 1) / √2`。
 */
export function telegraphBadgeCenter(k: number): { x: number; y: number } {
  const d = (TELEGRAPH_BADGE_R * (k - 1)) / Math.SQRT2;
  return { x: T - TELEGRAPH_BADGE_INSET + d, y: TELEGRAPH_BADGE_INSET - d };
}
