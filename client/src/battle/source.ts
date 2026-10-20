// 源力的顯示（Phase 3C-6a；純函式）：HUD 用 `max` 格圖示表示，前 `value` 格是亮的。
import type { SkillCard } from "../api/types";

/** `max` 個圖示，前 `value` 個為 `true`（超出範圍時夾在 0..max）。 */
export function sourcePips(value: number, max: number): boolean[] {
  const filled = Math.max(0, Math.min(max, value));
  return Array.from({ length: Math.max(0, max) }, (_, i) => i < filled);
}

/** 傳說技能的源力成本文字：「源力 ●●○」（成本 2、上限 3）；不花源力的技能回傳 `null`。 */
export function sourceCostText(card: Pick<SkillCard, "source_cost">, max: number): string | null {
  const cost = card.source_cost ?? null;
  if (cost === null || cost <= 0) return null;
  const pips = sourcePips(cost, Math.max(max, cost)).map((on) => (on ? "●" : "○")).join("");
  return `源力 ${cost}　${pips}`;
}

/** 技能卡片標題的種類字樣：「主動」「被動」「反應」「姿態」；修正技能一併註明是「改造／修正」。 */
export function kindLabel(card: Pick<SkillCard, "kind" | "kind_id" | "modifiers">): string {
  if (card.kind_id === "modifier") return `${card.kind}（改造／修正）`;
  return card.kind;
}
