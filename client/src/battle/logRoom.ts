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

// UI-1（美術 PM BS-2 驗收複驗）：800×600 時展開的紀錄上緣會伸到左上主角卡底下（約 100px），標題列與擲骰細節、
// 釘選鈕點不到。沒有選取時，紀錄的高度上限另外扣掉主角卡：上緣停在主角卡下緣＋8px。1600 等夠高的視窗，
// 這個上限比原本的 58% 大，`min(58%, …)` 照舊是 58%，版面不變。

/** 主角卡底下到紀錄底部可用的高度（兩者都相對戰場頂端）；量不到時 `null`。不到 3 行時給 3 行（會疊到主角卡下面）。 */
export function heroLogCap(dockBottom: number, heroBottom: number | null): number | null {
  if (heroBottom === null || !(dockBottom > 0)) return null;
  return Math.max(LOG_MIN_PX, Math.floor(dockBottom - heroBottom - LOG_ROOM_GAP));
}

/** 紀錄的 `max-height`：選取中照 `logLimit`；沒選取時照主角卡上限；都沒有時 `undefined`（只用 CSS 的 58%）。 */
export function logDockMaxHeight(limit: LogLimit | null, heroCap: number | null): string | undefined {
  if (limit !== null) return limit.tight ? `${limit.maxHeight}px` : `min(58%, ${limit.maxHeight}px)`;
  if (heroCap !== null) return `min(58%, ${heroCap}px)`;
  return undefined;
}
