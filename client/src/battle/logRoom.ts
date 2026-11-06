// 選取時戰鬥紀錄縮短讓開（Phase 6A-4c，併入 6A-3 驗收結論，`docs/archive/art/6A-3與6A-4a檢查.md`）：
// 紀錄底部固定在戰場左下，最大高度 ＝ 選取面板底下到紀錄底部、留 8px；不到 3 行時只顯示最新 3 行（可捲動）。
// 選取結束恢復；釘住的也縮。純函式，量測在 `screens/battle/useLogRoom.ts`。

/** 紀錄與選取面板之間留的空隙。 */
export const LOG_ROOM_GAP = 8;
/** 紀錄離戰場底部的距離（`.log-dock` 的 `bottom`）。 */
export const LOG_DOCK_BOTTOM = 4;
/** 一行紀錄的高度（13px × 1.45）。 */
export const LOG_LINE_PX = 19;
/** 展開的紀錄除了行以外的高度：標題列、面板內距、紀錄圖示與間距。 */
export const LOG_CHROME_PX = 30 + 12 + 32;
/** 至少顯示 3 行。 */
export const LOG_MIN_LINES = 3;
export const LOG_MIN_PX = LOG_CHROME_PX + LOG_MIN_LINES * LOG_LINE_PX;

/** 選取面板底下到紀錄底部可用的高度（`panelBottom` 是面板底邊相對戰場頂端的距離）；沒有選取時 `null`。 */
export function logRoom(boardHeight: number, panelBottom: number | null): number | null {
  if (panelBottom === null || !(boardHeight > 0)) return null;
  return Math.floor(boardHeight - LOG_DOCK_BOTTOM - panelBottom - LOG_ROOM_GAP);
}

export interface LogLimit {
  maxHeight: number;
  /** 空間不到 3 行：只顯示最新 3 行（可捲動），會疊到選取面板下面。 */
  tight: boolean;
}

/** 紀錄的高度上限（`null` ＝ 不限，照原本的版面）。 */
export function logLimit(room: number | null): LogLimit | null {
  if (room === null) return null;
  if (room < LOG_MIN_PX) return { maxHeight: LOG_MIN_PX, tight: true };
  return { maxHeight: room, tight: false };
}
