// TXT-2（`docs/phases/現代網頁指南試用.md` 第 A 項）：文字輸入框按 Enter 送出之前要先排除輸入法選字。
// 原始碼掃描：凡是在 `<input>`／`<textarea>` 上處理 Enter 的地方，都必須用 `ui/imeEnter.ts` 的 `isSubmitEnter`，
// 不准自己比 `e.key === "Enter"`（選字中那一下會把半截字送出去）。
import { describe, expect, it } from "vitest";
import { readSources, stripTsComments } from "../test/sourceScan";
import { isImeComposing, isSubmitEnter } from "./imeEnter";

const files = readSources().map(([path, text]) => [path, stripTsComments(text, path)] as const);

/** 文字輸入框的開頭標籤到結尾（`/>` 或第一個 `>` 之後的 `</input|textarea>`）；夠用的近似。 */
function textFieldTags(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(/<(input|textarea)\b/g)) {
    const start = m.index ?? 0;
    const end = text.indexOf("/>", start);
    out.push(text.slice(start, end < 0 ? text.length : end + 2));
  }
  return out;
}

/** 文字輸入框不包含的種類（按鈕類、勾選類不會碰到輸入法）。 */
const NOT_TEXT = /type=["'](checkbox|radio|range|button|submit|color|file)["']/;

const RAW_ENTER = /key\s*[!=]==?\s*["']Enter["']|["']Enter["']\s*[!=]==?\s*\w*\.?key\b|keyCode\s*[!=]==?\s*13\b/;

describe("文字輸入框的 Enter 一律經過 isSubmitEnter", () => {
  it("輸入框上的 onKeyDown／onKeyUp／onKeyPress 處理 Enter 時用 isSubmitEnter", () => {
    const bad: string[] = [];
    let checked = 0;
    for (const [path, text] of files) {
      for (const tag of textFieldTags(text)) {
        if (NOT_TEXT.test(tag) || !/onKey(Down|Up|Press)/.test(tag)) continue;
        checked += 1;
        if (RAW_ENTER.test(tag) || (/Enter/.test(tag) && !tag.includes("isSubmitEnter"))) bad.push(path);
      }
    }
    expect(bad).toEqual([]);
    expect(checked).toBeGreaterThanOrEqual(2); // 留言（NotesPanel）、郵寄個數（MailPanel）
  });

  it("有文字輸入框的檔案不自己比 Enter 鍵", () => {
    const bad = files
      .filter(([, text]) => textFieldTags(text).some((t) => !NOT_TEXT.test(t)))
      .filter(([, text]) => RAW_ENTER.test(text))
      .map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("留言與郵寄個數都用 isSubmitEnter", () => {
    const byPath = new Map(files);
    for (const path of ["world/NotesPanel.tsx", "world/MailPanel.tsx"]) {
      expect(byPath.get(path) ?? "", path).toContain("isSubmitEnter(e)");
    }
  });
});

describe("isSubmitEnter", () => {
  const ev = (key: string, keyCode: number, composing?: boolean) => ({ key, keyCode, nativeEvent: { isComposing: composing } });

  it("一般 Enter 送出", () => {
    expect(isSubmitEnter(ev("Enter", 13, false))).toBe(true);
  });
  it("isComposing 時不送出（Chrome、Edge、Firefox）", () => {
    expect(isSubmitEnter(ev("Enter", 13, true))).toBe(false);
  });
  it("keyCode 229 時不送出（Safari 沒有 isComposing）", () => {
    expect(isSubmitEnter(ev("Enter", 229, undefined))).toBe(false);
    expect(isImeComposing({ key: "Process", keyCode: 229 })).toBe(true);
  });
  it("原生事件的 isComposing 也算", () => {
    expect(isSubmitEnter({ key: "Enter", keyCode: 13, isComposing: true })).toBe(false);
  });
  it("別的鍵不送出", () => {
    expect(isSubmitEnter(ev("a", 65, false))).toBe(false);
  });
});
