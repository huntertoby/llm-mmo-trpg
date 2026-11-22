// 說明文字裡共用的規則數字寫法（HC-6b）：數字照伺服器（`/api/glossary` 的 `rules`），前端只管怎麼寫。
import type { GameRules } from "../api/types";
import { gameRules } from "../battle/glossary";
import { percent } from "../battle/previewText";

type BudgetWindow = Pick<GameRules, "budget_min_ratio_permille" | "budget_max_ratio_permille">;

/** 技能預算的合格區間「70～100%」（`sep` 是兩端中間的符號；百分號只寫一次）。 */
export function budgetWindowText(sep: string, rules: BudgetWindow = gameRules()): string {
  const low = percent(rules.budget_min_ratio_permille).replace(/%$/u, "");
  return `${low}${sep}${percent(rules.budget_max_ratio_permille)}`;
}

const ZH_DIGITS = "零一二三四五六七八九十";

/**
 * 張數、招數的中文寫法（HC-6b，許願張數 `wish_cards` 用；和後端 `llm/prompts/wish_pick.py` 的 `_count_zh` 同規則）：
 * - 0～10 寫中文數字（一、二、三…十），超過 10 寫阿拉伯數字；
 * - `measure`（後面接量詞「招」「張」）時 2 寫「兩」（「兩招挑一招」「兩招都不拿」）；
 *   「N 選一」這種固定說法 2 照寫「二」（「二選一」）。
 */
export function countZh(n: number, measure = false): string {
  if (measure && n === 2) return "兩";
  const zh = Number.isInteger(n) && n >= 0 ? ZH_DIGITS[n] : undefined;
  return zh ?? String(n);
}

/** 秒數寫成「N 天」（整天）或「N 小時」（不整天，四捨五入；HC-7 a 裁定 8，同後端 `cooldown_zh`）。 */
export function durationText(seconds: number): string {
  const hour = 3600;
  const day = 24 * hour;
  if (seconds % day === 0) return `${seconds / day} 天`;
  return `${Math.round(seconds / hour)} 小時`;
}

/** 秒數寫成「約 N 天」（整天）或「約 N 小時」（不整天；HC-6b，線頭到期）。 */
export function aboutDurationText(seconds: number): string {
  return `約 ${durationText(seconds)}`;
}
