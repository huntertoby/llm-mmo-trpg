// 事件卡選項列 A（PNL-4；docs/art/資訊面板-移植需求.md 3.4、改字 #34）的純函式：主字斷詞、次行內容、放棄分出去。
// 樣張 docs/art/sample/infoPanels.js 的 `wordBreaks()`、`sub()`、`solGrid({ splitLeave: true })` 照搬；畫面在 `SolutionTile.tsx`。
// （檔名不叫 solutionTile.ts：Windows 上和 SolutionTile.tsx 只差大小寫會撞，上手筆記第 84 點。）
import type { WorldEventSolution } from "../api/types";
import { attrKey, type AttrKey } from "./narration";

/** 有這些標點時不另插斷點：`word-break: keep-all` 本來就只在標點後換行（「亮出商隊旗號，／談條件」）。 */
const PUNCT = /[，、；：（）「」。！？]/u;

let segmenter: Intl.Segmenter | null | undefined;
function wordSegmenter(): Intl.Segmenter | null {
  if (segmenter === undefined) segmenter = typeof Intl !== "undefined" && typeof Intl.Segmenter === "function" ? new Intl.Segmenter("zh-Hant", { granularity: "word" }) : null;
  return segmenter;
}

/**
 * 主字切成「詞」（樣張 `wordBreaks()`）：呼叫端在詞與詞之間插 `<wbr>`，CSS `word-break: keep-all` 只在詞間或標點後換行。
 * 有標點、或瀏覽器沒有 `Intl.Segmenter` 時回整句一段。單字的詞（「談」「丟」這類動詞）併進下一個詞，免得斷成「談／條件」；
 * 最後剩下的單字併進前一個詞。
 */
export function wordBreaks(text: string, seg: Intl.Segmenter | null = wordSegmenter()): string[] {
  if (seg === null || PUNCT.test(text)) return [text];
  const words: string[] = [];
  let carry = "";
  for (const { segment } of seg.segment(text)) {
    if ([...segment].length === 1) carry += segment;
    else {
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
