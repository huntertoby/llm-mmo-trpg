// 影子循環賽的顯示小工具（Phase 5F-4）：文字與數字都由後端算好，這裡只排版。
import type { LeagueReplayResponse, LeagueStandingView, LeagueView } from "../api/types";

/** 名次欄：還沒開跑顯示「—」；同名次（5F-4b：勝場、HP 比例合計、總輪數都相同）加「（同分）」。 */
export function rankLabel(r: LeagueStandingView): string {
  if (r.rank == null) return "—";
  return r.tied ? `${r.rank}（同分）` : `${r.rank}`;
}

/** 同勝場時比的數字（5F-4b，6.8 BAL-12a），例「剩餘 HP 合計 182%・共 40 輪」；還沒打時 `null`。 */
export function tiebreakLabel(r: LeagueStandingView): string | null {
  if (r.played === 0) return null;
  return `剩餘 HP 合計 ${Math.floor(r.hp_permille_total / 10)}%・共 ${r.rounds_total} 輪`;
}

/** 場次分頁，例「第 2／5 頁」；只有 1 頁時 `null`。 */
export function pageLabel(v: Pick<LeagueView, "page" | "pages">): string | null {
  return v.pages <= 1 ? null : `第 ${v.page}／${v.pages} 頁`;
}

/** 報名時的配點（5F-4b，#32）：送出用的屬性點；和自動配點一樣時送 `null`（照自動配點）。 */
export function allocationToSend(
  alloc: Readonly<Partial<Record<string, number>>>,
  auto: Readonly<Record<string, number>>,
): Record<string, number> | null {
  const keys = new Set([...Object.keys(alloc), ...Object.keys(auto)]);
  const same = [...keys].every((k) => (alloc[k] ?? 0) === (auto[k] ?? 0));
  if (same) return null;
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(alloc)) if ((v ?? 0) > 0) out[k] = v ?? 0;
  return out;
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
    const points = entry.allocation != null ? "、自己配點" : "";
    return `已用${who}報名（打法：${entry.ai_zh}${points}）。`;
  }
  if (v.enter_problem_zh != null) return `不能報名：${v.enter_problem_zh}`;
  return v.status === "signup" ? `尚未報名（第 ${v.signup_close_day} 天截止）。` : "沒有報名。";
}

/** 重播畫面開場的說明：標題與重播驗證結果。 */
export function replayNotes(r: LeagueReplayResponse): string[] {
  const check = r.verified ? "重播驗證一致：依紀錄的步驟重算出相同的結果。" : "注意：重播結果和紀錄不一致。";
  return [r.title_zh, check];
}
