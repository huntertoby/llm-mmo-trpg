// RT-3b（美術 PM 6F-7 檢查小修：說明框把「右鍵」拆成兩行，詞不能被拆開）：
// 中文在任何兩個字之間都可以換行，所以操作詞（右鍵、左鍵、Esc、Shift……）包成不換行的一小段。
// 其他字照常換行（不用 `word-break: keep-all`，那會讓長句整段不換行而超出框）。
import type { ReactNode } from "react";

/** 不可以拆開的詞（長的放前面，才不會先被短的切掉）。 */
// 6F-9（美術 PM 6F-8 檢查第 3 節：選取面板第二行以「／右鍵取消。」開頭）：「Esc／右鍵」整組不拆；
// balance 之後 1600 寬把「紅框」拆成「紅」「框」兩行，所以「紅框」也不拆。
export const KEEP_WORDS: readonly string[] = ["Esc／右鍵", "Shift＋", "右鍵", "紅框", "左鍵", "滑鼠", "長按", "Esc", "Shift", "Ctrl", "Enter", "空白鍵"];

/** 6F-9：數字和後面的量詞也不拆（balance 之後曾拆成「19」換行「個）」）。 */
export const NUMBER_UNIT = String.raw`\d+ ?(?:個|格|回合|輪|點|次)`;

const KEEP_RE = new RegExp(`(${[...KEEP_WORDS.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), NUMBER_UNIT].join("|")})`, "u");

/** 字串切成「一般字」與「不可拆的詞」（奇數位是不可拆的詞）。 */
export function splitKeepWords(text: string): string[] {
  return text.split(KEEP_RE);
}

/** 把不可拆的詞包成 `white-space: nowrap` 的小段。 */
export function keepWords(text: string): ReactNode {
  const parts = splitKeepWords(text);
  if (parts.length === 1) return text;
  return parts.map((p, i) =>
    i % 2 === 1 ? (
      <span key={i} className="keep-word">
        {p}
      </span>
    ) : (
      p
    ),
  );
}
