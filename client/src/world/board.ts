// 城鎮公告板的顯示小工具（Phase 5F-1）：文字與數字都由後端算好，這裡只排版。
import type { BoardBossEntryView, BoardGoalView, BoardSeasonBossView, BoardWorldEventView } from "../api/types";

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

/** 賽季 Boss 的封印鑰匙（5F-3），例「全服 5／12 把・你有 1 把（需要 1 把）」。 */
export function bossKeysLabel(b: BoardSeasonBossView): string {
  const world = b.keys_target == null ? `全服 ${b.world_keys} 把` : `全服 ${b.world_keys}／${b.keys_target} 把`;
  return `${world}・你有 ${b.my_keys} 把（需要 ${b.keys_required} 把）`;
}

/** 賽季 Boss 封印共鳴的進度條（‰）；門檻未定時 0。 */
export function bossKeysPermille(b: BoardSeasonBossView): number {
  if (b.keys_target == null || b.keys_target <= 0) return 0;
  return Math.min(1000, Math.floor((b.world_keys * 1000) / b.keys_target));
}

/** 帳號今天的挑戰次數，例「今天還剩 2／3 次（算帳號）」。 */
export function bossAttemptsLabel(b: BoardSeasonBossView): string {
  return `今天還剩 ${b.attempts_left}／${b.daily_attempts} 次（算帳號）`;
}

/** 評分榜的一行，例「1. 小美　1240 分・8 輪・存活 3／3・無人倒下（霧渡鎮）」。 */
export function bossEntryLabel(e: BoardBossEntryView): string {
  const down = e.no_down ? "・無人倒下" : "";
  return `${e.rank}. ${e.name}　${e.score} 分・${e.rounds} 輪・存活 ${e.survivors}／${e.allies}${down}（${e.location_zh}）`;
}

/** 重生時間的當地時刻（HH:MM）。 */
export function respawnLabel(at: number): string {
  const d = new Date(at * 1000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
