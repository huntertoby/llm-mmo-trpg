// 規則句裡的「可滑過」小段（Phase 3H-5）：後端把「目前 +4」這類顯示整數、實際值帶小數的加成寫成
// `⟦顯示字｜說明⟧`（`trpg.shared.bonus_text`），這裡排成 <Hint>（共用浮動卡，規則見 docs/開發PM交接.md 6.5.1）。
// 不支援標記的地方（原生提示、純文字）用 `plainRule` 還原成顯示字。
import type { ReactNode } from "react";
import { Hint } from "./Hint";

const MARK = /⟦([^｜⟧]*)｜([^⟧]*)⟧/g;

/** 切成純文字與標記段（標記段：顯示字＋說明）。 */
export function ruleParts(text: string): { text: string; hint: string | null }[] {
  const parts: { text: string; hint: string | null }[] = [];
  let last = 0;
  for (const m of text.matchAll(MARK)) {
    const at = m.index ?? 0;
    if (at > last) parts.push({ text: text.slice(last, at), hint: null });
    parts.push({ text: m[1] ?? "", hint: m[2] ?? "" });
    last = at + m[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), hint: null });
  return parts;
}

/** 去掉標記，只留顯示字。 */
export function plainRule(text: string): string {
  return text.replace(MARK, "$1");
}

/** 一行規則句：標記段變成可滑過的說明框，其餘照寫。 */
export function RuleText({ text }: { text: string }): ReactNode {
  return (
    <>
      {ruleParts(text).map((p, i) =>
        p.hint === null ? (
          <span key={i}>{p.text}</span>
        ) : (
          <Hint key={i} text={p.hint}>
            <span className="has-hint" data-testid="bonus-hint">
              {p.text}
            </span>
          </Hint>
        ),
      )}
    </>
  );
}
