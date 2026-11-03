// 影子循環賽的顯示小工具（Phase 5F-4）：文字與數字都由後端算好，這裡只排版。
import type { LeagueReplayResponse, LeagueStandingView, LeagueView } from "../api/types";

/** 名次欄：還沒開跑顯示「—」。 */
export function rankLabel(r: LeagueStandingView): string {
  return r.rank == null ? "—" : `${r.rank}`;
}

/** 戰績，例「5 勝 2 負 1 和」。 */
export function recordLabel(r: LeagueStandingView): string {
  return `${r.wins} 勝 ${r.losses} 負 ${r.draws} 和`;
}

/** 進度，例「已完成 12／36 場」；還沒開跑時 `null`。 */
export function progressLabel(v: LeagueView): string | null {
  if (v.total === 0) return null;
  return `已完成 ${v.done}／${v.total} 場`;
}

/** 報名區的說明：已報名（哪個角色、打法）或為什麼不能報名。 */
export function signupNote(v: LeagueView): string {
  if (v.status === "none") return v.status_zh;
  const entry = v.entry;
  if (entry !== null && entry !== undefined) {
    const who = entry.this_character ? "這個角色" : `「${entry.name}」`;
    return `已用${who}報名（打法：${entry.ai_zh}）。`;
  }
  if (v.enter_problem_zh != null) return `不能報名：${v.enter_problem_zh}`;
  return v.status === "signup" ? `尚未報名（第 ${v.signup_close_day} 天截止）。` : "沒有報名。";
}

/** 重播畫面開場的說明：標題與重播驗證結果。 */
export function replayNotes(r: LeagueReplayResponse): string[] {
  const check = r.verified ? "重播驗證一致：依紀錄的步驟重算出相同的結果。" : "注意：重播結果和紀錄不一致。";
  return [r.title_zh, check];
}
