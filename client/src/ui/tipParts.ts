// AR-X10（美術 PM `docs/art/X10-3d驗收.md` 小修 1）：狀態提示的骰子行「擲 NdM，每點 ×10」自己一行、用次要字色，
// 排法同技能長說明（`skill-card-dice`）與主角面板的普攻：不加分隔符號，接在它補充的那句（傷害句）下面。
// 規則句來自 /api/glossary 的 `rules_zh`（後端 `trpg.shared.range_text.dice_note` 產生的骰子行是獨立的一行）。

/** 說明卡的一段：一般說明，或次要字色的補充行（骰子行）。 */
export interface TipPart {
  text: string;
  secondary: boolean;
}

/** 骰子行：「擲 1d6，每點 ×10」。 */
export const DICE_NOTE_RE = /^擲 \d+d\d+，每點 ×\d+$/u;

/**
 * 說明與規則句 → 說明卡的各段：一般句照舊用空白接成一段（同 `statusTile` 的 tip），遇到骰子行就另起一段次要字色。
 * 空字串略過。
 */
export function tipParts(lines: readonly string[]): TipPart[] {
  const out: TipPart[] = [];
  let buf: string[] = [];
  const flush = (): void => {
    if (buf.length > 0) out.push({ text: buf.join(" "), secondary: false });
    buf = [];
  };
  for (const line of lines) {
    if (line === "") continue;
    if (DICE_NOTE_RE.test(line)) {
      flush();
      out.push({ text: line, secondary: true });
    } else buf.push(line);
  }
  flush();
  return out;
}
