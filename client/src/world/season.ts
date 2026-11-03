// 季末重置、編年史與沿用上季角色的純函式（Phase 5F-5；docs/phases/Phase5計畫.md 40.6）。
import type { AuthStatus, ChronicleSeasonView, LegacyHeroView, ResetLine, SeasonResetReport, SeasonResetRequest } from "../api/types";

/** 看得到管理者介面：管理者帳號，或開發模式沒登入（權限仍由伺服器檢查）。 */
export function canAdmin(auth: AuthStatus | null): boolean {
  if (auth === null) return false;
  if (auth.account == null) return auth.dev_mode;
  return auth.account.admin === true;
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** 開賽日欄位的問題（`null` ＝可以預覽）。 */
export function startDateProblem(date: string): string | null {
  if (date.trim() === "") return "請填新一季的開賽日";
  if (!DATE_RE.test(date.trim()) || Number.isNaN(Date.parse(date.trim()))) return "開賽日格式是 YYYY-MM-DD";
  return null;
}

/** 送給 `POST /api/world/season/reset` 的 body（預覽＝dry-run；執行要帶目前季 ID）。 */
export function resetBody(date: string, force: boolean, confirm: string | null): SeasonResetRequest {
  return {
    start_date: date.trim(),
    force,
    dry_run: confirm === null,
    ...(confirm === null ? {} : { confirm_season: confirm.trim() }),
  };
}

/** 「執行」按鈕能不能按：預覽過、預覽之後開賽日與強制沒改、輸入的季 ID 等於預覽的舊季。 */
export function canExecute(preview: SeasonResetReport | null, previewedFor: string | null, current: string, confirm: string): boolean {
  if (preview === null || !preview.dry_run) return false;
  return previewedFor === current && confirm.trim() === preview.old_season;
}

/** 清／留清單的一行：「角色 2（等級、技能……）」。 */
export function resetLineText(line: ResetLine): string {
  const detail = line.detail_zh ? `（${line.detail_zh}）` : "";
  return `${line.label_zh} ${line.count}${detail}`;
}

/** 沿用上季角色選單的一項：「阿霧（第一季・狐族）」。 */
export function legacyLabel(hero: LegacyHeroView): string {
  const tail = [hero.season_name_zh, hero.race_name_zh].filter((s): s is string => s !== null && s !== "").join("・");
  return `${hero.name}（${tail}）`;
}

/** 編年史一季有沒有東西可以顯示。 */
export function seasonHasRecords(season: ChronicleSeasonView): boolean {
  return (
    season.heroes.length + season.recipes.length + season.first_kills.length + season.league.length + season.boss_board.length >
    0
  );
}

/** 編年史一季的標題：「第一季」／「第二季（進行中）」。 */
export function seasonTitle(season: ChronicleSeasonView): string {
  return season.current ? `${season.name_zh}（進行中）` : season.name_zh;
}
