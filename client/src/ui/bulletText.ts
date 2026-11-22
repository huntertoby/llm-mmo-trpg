// E3b（美術 E4 驗收末節）：說明框裡用「・」分點的，換行時都對齊上一行「・」後面的字（懸掛縮排）。
// 全部共用同一個 class `part-tip-bullet`（`float-card.css` 那一條規則，E4b 倒地說明框起用）。
// 說明文字（`actionInfo.ts` 的動作說明、`stackInfo.ts` 的層數說明、狀態列的說明卡……）是用 "\n" 接起來的字串，
// 這裡把它切成行，「・」開頭的行標成分點；`Hint` 的預設內容與 `PartTip` 的 `tip` 都經過這裡。

/** 懸掛縮排的 class（和 E4b 倒地說明框同一條 CSS 規則）。 */
export const BULLET_CLASS = "part-tip-bullet";

export interface TextLine {
  text: string;
  /** 「・」開頭的分點：套 `BULLET_CLASS`。 */
  bullet: boolean;
}

/** 有「・」開頭的行時切成行（`bullet` 標出分點）；沒有分點時回傳 `null`（照舊整段顯示）。 */
export function bulletLines(text: string): TextLine[] | null {
  const lines = text.split("\n");
  if (!lines.some((l) => l.startsWith("・"))) return null;
  return lines.map((l) => ({ text: l, bullet: l.startsWith("・") }));
}
