// 數值工坊的 1 階比值（Phase NW-2c，規格 docs/phases/PhaseNW-2計畫.md 5.7、T11、T12、D4）：純函式。
// 比值＝（技能對木樁的傷害 ÷ 花掉的 AP）÷（普攻對木樁的傷害 ÷ 花掉的 AP），量測核心在後端 `trpg.sim.skill_ratio`。
// 參考線只當參考（D4），不擋寫回；「建議，未定案」的兩條另標。
import type { TuningRatioLine, TuningRatioPlan, TuningRatioSimResult, TuningRatioSummary } from "../api/types";
import { secondsText } from "./model";

/** 比值情境的表單。`skills` 為 `null` ＝ 用草稿改到的技能（沒有就用目前打開的那招）。 */
export interface RatioForm {
  skills: readonly string[] | null;
  seedsText: string;
}

export const DEFAULT_RATIO_FORM: RatioForm = { skills: null, seedsText: "50" };

/** 摘要表的六格（順序同 `t1_skill_ratio.py` 的摘要表）。 */
export const RATIO_CELLS: readonly { key: keyof Pick<TuningRatioSummary, "plain" | "plain_tot" | "on" | "on_tot" | "dual" | "bound">; label: string }[] = [
  { key: "plain", label: "直接" },
  { key: "plain_tot", label: "含持續" },
  { key: "on", label: "成立 直接" },
  { key: "on_tot", label: "成立 含持續" },
  { key: "dual", label: "雙匕首" },
  { key: "bound", label: "綁定武器" },
];

/** 一條參考線的文字：「無條件單體（直接）≥ 0.90：0.78 低於」。 */
export function lineText(line: TuningRatioLine): string {
  const value = line.value == null ? "沒有值" : line.value.toFixed(2);
  const verdict = line.ok == null ? "" : line.ok ? " 達標" : " 低於";
  return `${line.label_zh} ≥ ${line.threshold.toFixed(2)}：${value}${verdict}`;
}

/** 參考線的樣式：達標／低於／沒有值。 */
export function lineClass(line: TuningRatioLine): string {
  if (line.ok == null) return "muted";
  return line.ok ? "tn-v-ok" : "tn-v-weak";
}

/** 一格改前改後有沒有變（文字比對；顯示「變了」用）。 */
export function cellChanged(before: TuningRatioSummary | null | undefined, after: TuningRatioSummary | null | undefined, key: (typeof RATIO_CELLS)[number]["key"]): boolean {
  return (before?.[key] ?? "—") !== (after?.[key] ?? "—");
}

/** 比值情境實際要量的招（沒有自己選＝草稿改到的技能）。 */
export function ratioSkillsOf(form: RatioForm, edited: readonly string[]): string[] {
  return [...(form.skills ?? edited)];
}

/** 種子數的問題（1～250 的整數）；沒問題回 `null`。 */
export function ratioSeedsProblem(text: string): string | null {
  const t = text.trim();
  if (!/^\d+$/.test(t)) return "種子數要填 1～250 的整數";
  const n = Number(t);
  return n < 1 || n > 250 ? "種子數要填 1～250 的整數" : null;
}

/**
 * 比值情境的「N 組 × M 種子、預估 X 秒」或問題（規格 T11）。`plan` 是後端算的組數（招 × 可用武器 × 情境數）；
 * 改前沒有快取、草稿又改了內容時改前改後各跑一次。
 */
export function ratioEstimate(plan: TuningRatioPlan | null, form: RatioForm, edited: readonly string[]): { problem: string | null; text: string } {
  if (ratioSkillsOf(form, edited).length === 0) {
    const problem = "至少要有一招（草稿改到的技能，或自己加）";
    return { problem, text: problem };
  }
  const seeds = ratioSeedsProblem(form.seedsText);
  if (seeds !== null) return { problem: seeds, text: seeds };
  if (plan === null) return { problem: "正在算規模……", text: "正在算規模……" };
  if (plan.problem_zh != null) return { problem: plan.problem_zh, text: plan.problem_zh };
  const skipped = plan.skipped.length > 0 ? `；不量 ${plan.skipped.length} 招（不是 1 階主動武器技）` : "";
  return {
    problem: null,
    text: `${plan.groups} 組 × ${plan.seeds} 種子（${plan.skills.length} 招、${plan.jobs} 組武器×招${skipped}），預估約 ${secondsText(plan.seconds)}～${secondsText(plan.seconds * 2)}（改前已有快取或草稿沒改內容時較快）`,
  };
}

/** 結果表的說明行（快取、同內容、跳過、條件檢查）。 */
export function ratioResultNotes(result: TuningRatioSimResult): string[] {
  const out: string[] = [`每組 ${result.seeds} 種子、${result.groups} 組。`];
  if (result.same_content) out.push("草稿沒改內容：只跑一次（改前＝改後），結果已記成目前內容的比值。");
  else if (result.before_cached) out.push("改前結果用的是快取（同一份內容、同樣的招與種子量過）。");
  for (const s of result.skipped ?? []) out.push(`「${s.name_zh}」沒量：${s.reason_zh}`);
  const odd = result.odd ?? [];
  if (odd.length > 0) out.push(`條件檢查：施放前條件和情境不符 ${odd.length} 組（${odd.slice(0, 3).join("、")}${odd.length > 3 ? "…" : ""}）`);
  return out;
}
