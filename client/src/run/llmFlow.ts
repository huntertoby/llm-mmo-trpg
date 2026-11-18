// 網頁版 LLM 開關（Phase 4-L6b）的純函式：開局欄位、候選卡來源標記、一輪結束摘要。
// 標記與說明文字集中在這裡（玩法 PM 2026-10-29 定案）。
import type { CreateRunRequest, LlmStats, OfferTag } from "../api/types";

/** 候選卡的 LLM 來源標記（暫定）。 */
export const LLM_SOURCE_LABEL = "源晶推演";
export const LLM_SOURCE_HINT = "這張技能由本機模型提議，數值由規則補齊。";
/** 挑選模式（`pick: llm`，許願、升級等三選一）的說明句（玩法 PM 2026-11-19，4.1.27 題 5）。 */
export const LLM_PICK_HINT = "這張技能的名字和描述由本機模型取；效果和數值都照規則出題。";
/** 開新一輪畫面的開關文字與說明（說明走共用浮動卡）。 */
export const LLM_TOGGLE_LABEL = "用本機模型生成升級技能";
export const LLM_TOGGLE_HINT = "由本機模型生成升級技能；需要先啟動本機模型。沒有啟動時，這一輪照常使用一般技能生成。";

/** 開局欄位加上 LLM 開關：沒開就原樣回傳（請求不帶 `llm`，與以往逐字相同）。 */
export function withLlm<T extends Partial<CreateRunRequest>>(body: T, on: boolean): T | (T & Pick<CreateRunRequest, "llm">) {
  return on ? { ...body, llm: true } : body;
}

/** 「源晶推演」小標的說明句：自由設計照舊，挑選模式用挑選的說明（4.1.27 題 5）；不是 LLM 的卡為 `null`。 */
export function llmTagHint(tag: OfferTag | undefined): string | null {
  if (tag === undefined) return null;
  if (tag.source === "llm") return LLM_SOURCE_HINT;
  return tag.pick === "llm" ? LLM_PICK_HINT : null;
}

/** 一輪結束摘要的 LLM 統計列；沒開 LLM 且沒有題目時為空。 */
export function llmSummaryLines(stats: LlmStats | null | undefined): string[] {
  if (stats === null || stats === undefined) return [];
  const rate = `${(stats.fallback_permille / 10).toFixed(1)}%`;
  const lines = [`LLM 提議 ${stats.total} 題：成功 ${stats.succeeded}、退回 ${stats.failed}（${rate}），呼叫 ${stats.attempts} 次`];
  if (stats.named > 0) {
    lines.push(`命名 ${stats.named} 個：生成 ${stats.name_generated}、組合式名稱 ${stats.name_fallback}`);
  }
  if (stats.alert) lines.push(`提醒：退回率超過 ${stats.alert_permille / 10}%`);
  return lines;
}
