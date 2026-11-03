// 城鎮公告板的顯示小工具（Phase 5F-1）：文字與數字都由後端算好，這裡只排版。
import type { BoardGoalView, BoardWorldEventView } from "../api/types";

/** 進度條寬度（0～100 的百分比字串）。 */
export function barWidth(permille: number): string {
  const clamped = Math.max(0, Math.min(1000, permille));
  return `${clamped / 10}%`;
}

/** 世界事件的進度文字，例「12／30・進行中」。 */
export function eventProgressLabel(e: BoardWorldEventView): string {
  return `${e.progress}／${e.target}・${e.status_zh}`;
}

/** 今日目標的進度文字，例「1／2」或「完成（+1 任務幣）」。 */
export function goalProgressLabel(g: BoardGoalView): string {
  if (g.done) return g.coins > 0 ? `完成（+${g.coins} 任務幣）` : "完成";
  return `${g.progress}／${g.count}`;
}

/** 重生時間的當地時刻（HH:MM）。 */
export function respawnLabel(at: number): string {
  const d = new Date(at * 1000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
