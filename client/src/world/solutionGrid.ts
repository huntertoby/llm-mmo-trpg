// 事件卡選項列 A（PNL-4；docs/art/資訊面板-移植需求.md 3.4、改字 #34）的純函式：主字斷詞、次行內容、放棄分出去。
// 樣張 docs/art/sample/infoPanels.js 的 `wordBreaks()`、`sub()`、`solGrid({ splitLeave: true })` 照搬；畫面在 `SolutionTile.tsx`。
// （檔名不叫 solutionTile.ts：Windows 上和 SolutionTile.tsx 只差大小寫會撞，上手筆記第 84 點。）
import type { WorldEventSolution } from "../api/types";
import { attrKey, type AttrKey } from "./narration";

/** 收尾標點（黏在前一個詞後面，不會落到行首）與開頭標點（黏在下一個詞前面）。 */
const CLOSE_PUNCT = /^[，、；：）」』。！？…]+$/u;
const OPEN_PUNCT = /^[（「『]+$/u;

let segmenter: Intl.Segmenter | null | undefined;
function wordSegmenter(): Intl.Segmenter | null {
  if (segmenter === undefined) segmenter = typeof Intl !== "undefined" && typeof Intl.Segmenter === "function" ? new Intl.Segmenter("zh-Hant", { granularity: "word" }) : null;
  return segmenter;
}

/**
 * 主字切成「詞」（樣張 `wordBreaks()`）：呼叫端在詞與詞之間插 `<wbr>`，CSS `word-break: keep-all` 只在詞間或標點後換行。
 * 瀏覽器沒有 `Intl.Segmenter` 時回整句一段。單字的詞（「談」「丟」這類動詞）併進下一個詞，免得斷成「談／條件」；
 * 最後剩下的單字併進前一個詞。連續好幾個單字（Chrome 把「亮出商隊」切成「亮|出|商|隊」）已經湊到兩個字以上時自成一詞，
 * 不再併進下一個詞（PNL-4b：不然會變成「亮出商隊旗號，」一整段比一行長，被任意斷成「亮出商隊旗／號，」）。
 * PNL-4 和樣張不同：樣張有標點時整句不插斷點，但 800×600 的格子（約 137～145 寬）放不下「亮出商隊旗號，」這種長的一段，
 * `overflow-wrap: anywhere` 會把「，」斷到行首；所以有標點也照詞切，收尾標點黏前一個詞、開頭標點黏下一個詞。
 */
export function wordBreaks(text: string, seg: Intl.Segmenter | null = wordSegmenter()): string[] {
  if (seg === null) return [text];
  const words: string[] = [];
  let carry = "";
  for (const { segment } of seg.segment(text)) {
    if (CLOSE_PUNCT.test(segment) && carry === "" && words.length > 0) words[words.length - 1] += segment;
    else if (CLOSE_PUNCT.test(segment) && carry !== "") {
      words.push(carry + segment);
      carry = "";
    } else if (OPEN_PUNCT.test(segment) || [...segment].length === 1) carry += segment;
    else {
      if (charCount(carry) >= 2) {
        words.push(carry);
        carry = "";
      }
      words.push(carry + segment);
      carry = "";
    }
  }
  if (carry !== "") {
    if (words.length > 0) words[words.length - 1] += carry;
    else words.push(carry);
  }
  return words;
}

/** 不算標點的字數（「（亮出」＝2）。 */
function charCount(text: string): number {
  return [...text].filter((c) => !CLOSE_PUNCT.test(c) && !OPEN_PUNCT.test(c)).length;
}

/**
 * 整個詞黏住收尾標點的上限（不算標點的字數）：800×600 最窄的字欄約 94 寬（13.5px 粗體約 6 字），5 字＋標點一定放得下一行。
 * 比這長的詞只黏最後一個字，詞比一行還長時才讓 `overflow-wrap: anywhere` 任意斷。
 */
export const GLUE_WORD_MAX = 5;

/**
 * 一個詞拆成「前段｜尾巴」：尾巴＝收尾標點連同它黏住的字（呼叫端包成不斷行），「，」「）」不會單獨落到行首。
 * PNL-4b：詞不長（≤ `GLUE_WORD_MAX` 字）時尾巴是整個詞（「旗號，」不會斷成「旗／號，」）；比較長的詞尾巴只到最後一個字。
 * 沒有收尾標點時尾巴是空字串。
 */
export function glueTail(word: string): { head: string; tail: string } {
  const chars = [...word];
  let i = chars.length;
  while (i > 0 && CLOSE_PUNCT.test(chars[i - 1]!)) i -= 1;
  if (i === chars.length || i === 0) return { head: word, tail: "" };
  const cut = charCount(chars.slice(0, i).join("")) <= GLUE_WORD_MAX ? 0 : i - 1;
  return { head: chars.slice(0, cut).join(""), tail: chars.slice(cut).join("") };
}

/** 「用〔…〕抵」小鈕裡黏住不斷的尾巴長度：線頭名字的最後幾個字（不含「〕抵」）。 */
export const WAIVE_GLUE_CHARS = 2;

/**
 * 「用〔…〕抵」拆成「前段｜尾巴」（PNL-4 複驗新可修，LW-2b）：尾巴＝線頭名字最後兩個字＋「〕抵」，呼叫端包成不斷行，
 * 145 寬時斷成「用〔商人欠你／人情〕抵」，不會把雙字詞拆成「商人欠你人／情〕抵」。名字不到兩個字時尾巴是整個名字＋「〕抵」；
 * 字不是「…〕抵」的樣子就整句當前段。
 */
export function waiveRuns(label: string): { head: string; tail: string } {
  const close = "〕抵";
  const open = label.indexOf("〔");
  if (!label.endsWith(close) || open < 0) return { head: label, tail: "" };
  const name = [...label.slice(open + 1, label.length - close.length)];
  const keep = Math.min(WAIVE_GLUE_CHARS, name.length);
  const cut = label.length - close.length - name.slice(name.length - keep).join("").length;
  return { head: label.slice(0, cut), tail: label.slice(cut) };
}

/** 選項格的次行（改字 #34）：種類名（主字已是種類名時不重複）、屬性（圖＋名，兩個用「／」）、交涉的補給。 */
export interface SolutionSub {
  /** 種類名（「情境判定」「交涉」「機遇」）；主字就是種類名（戰鬥、放棄、沒寫說明）時 `null`。 */
  kind: string | null;
  /** 屬性（照伺服器的順序）：認得的有 `key`（畫圖示），不認得的只寫字。 */
  attrs: { name: string; key: AttrKey | null }[];
  /** 交涉付出的補給（> 0 才有）。 */
  cost: number | null;
}

/** 選項格主字（同現行 `solutionLine`）：情境判定與交涉用說明，其他用種類名。 */
export function tileMain(s: Pick<WorldEventSolution, "kind" | "kind_zh" | "note_zh">): string {
  return s.note_zh !== "" && s.kind !== "abandon" && s.kind !== "combat" ? s.note_zh : s.kind_zh;
}

export function solutionSub(s: Pick<WorldEventSolution, "kind" | "kind_zh" | "note_zh" | "attributes_zh" | "cost_supplies">): SolutionSub | null {
  const kind = tileMain(s) === s.kind_zh ? null : s.kind_zh;
  const attrs = s.attributes_zh
    .split(/[、,，／/]/u)
    .map((n) => n.trim())
    .filter((n) => n !== "")
    .map((name) => ({ name, key: attrKey(name) }));
  const cost = s.kind === "parley" && s.cost_supplies > 0 ? s.cost_supplies : null;
  if (kind === null && attrs.length === 0 && cost === null) return null;
  return { kind, attrs, cost };
}

/** 放棄分出去（需求 3.4 第 4 點：縮成右下小鈕、不佔格）；其他照伺服器的順序排進兩欄格子。 */
export function splitSolutions<T extends Pick<WorldEventSolution, "kind">>(solutions: readonly T[]): { tiles: T[]; leave: T[] } {
  return { tiles: solutions.filter((s) => s.kind !== "abandon"), leave: solutions.filter((s) => s.kind === "abandon") };
}
