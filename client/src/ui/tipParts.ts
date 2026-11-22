// AR-X10（美術 PM `docs/art/X10-3d驗收.md` 小修 1）：說明卡的骰子行「擲 NdM，每點 ×10」自己一行、用次要字色，
// 排法同技能長說明（`skill-card-dice`）與主角面板的普攻：不加分隔符號，接在它補充的那句（傷害句）下面。
// HC-6c（AR-X10 待決 5）：哪幾行是骰子行改讀 /api/glossary 的結構化欄位 `rules_dice`（後端 `dice_note` 產生的行），
// 不再比對句型。
import type { GlossaryEntry } from "../api/types";

/** 說明卡的一段：一般說明，或次要字色的補充行（骰子行）。 */
export interface TipPart {
  text: string;
  secondary: boolean;
}

/**
 * 說明與規則句 → 說明卡的各段：一般句照舊用空白接成一段（同 `statusTile` 的 tip），`dice` 列出的行（`lines` 的索引）
 * 另起一段次要字色。空字串略過。
 */
export function tipParts(lines: readonly string[], dice: ReadonlySet<number> = new Set()): TipPart[] {
  const out: TipPart[] = [];
  let buf: string[] = [];
  const flush = (): void => {
    if (buf.length > 0) out.push({ text: buf.join(" "), secondary: false });
    buf = [];
  };
  lines.forEach((line, i) => {
    if (line === "") return;
    if (dice.has(i)) {
      flush();
      out.push({ text: line, secondary: true });
    } else buf.push(line);
  });
  flush();
  return out;
}

/** 名詞表一項的說明卡各段：說明＋規則句，骰子行照 `rules_dice` 另起一行。對照表沒有這一項（或沒有任何字）時寫 `fallback`。 */
export function entryTipParts(entry: GlossaryEntry | undefined, fallback: string): TipPart[] {
  const rules = entry?.rules_zh ?? [];
  // E4（KD-1 驗收小修 1）：只列規則的項目（倒地）一條規則一行、前面加「・」，不接說明（同「扶起」說明卡的排法）
  if (entry?.rules_only === true && rules.length > 0) return rules.map((line) => ({ text: `・${line}`, secondary: false }));
  const dice = new Set((entry?.rules_dice ?? []).map((d) => d.line + 1)); // 第 0 行是說明
  const found = tipParts([entry?.description_zh ?? "", ...rules], dice);
  return found.length === 0 ? [{ text: fallback, secondary: false }] : found;
}
