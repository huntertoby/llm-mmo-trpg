// 浮動卡自動檢查（Phase 3-32b；規則見 docs/開發PM交接.md 6.5.1）：
// `client/src` 除了共用浮動卡元件之外，不准有自製的彈出層或原生 `title=` tooltip。
// 這裡用文字規則掃原始碼；有正當理由的例外一律列在白名單，並寫明原因。
import { describe, expect, it } from "vitest";
import styles from "../styles.css?raw";

const sources = import.meta.glob<string>("/src/**/*.tsx", { query: "?raw", import: "default", eager: true });
const files = Object.entries(sources)
  .map(([path, text]) => [path.replace(/^\/src\//, ""), text] as const)
  .filter(([path]) => !path.endsWith(".test.tsx"))
  .map(([path, text]) => [path, stripComments(text)] as const);

/** 去掉註解（保留換行，行號不變）：說明文字裡提到 `title=` 不算違規。 */
function stripComments(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " ")).replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
}

/** 共用浮動卡元件本身：可以用 portal、`position: fixed`。 */
const SHARED = new Set(["ui/useFloatCard.tsx", "ui/HoverFloat.tsx", "ui/Hint.tsx", "ui/PartTip.tsx"]);

/** 允許帶 `title=` 的元件標籤：`title` 是它的 prop（視窗標題），不是 DOM 的 tooltip 屬性。 */
const TITLE_PROP_OK = new Set(["DialogFrame"]);

/**
 * 不是「滑過顯示的說明卡」、但有自己的彈出外觀的元件（點擊才開的選單、對話框）。
 * 檔名 → 原因。新增這類元件時要在這裡列出並寫明原因，否則測試會擋下。
 */
const NON_HOVER_POPUPS: Record<string, string> = {
  "ui/DialogFrame.tsx": "反應詢問／複製／灌注等對話框的外框（`role=dialog`，互動式，不是說明卡）",
  "ui/BattleTopBar.tsx": "頂端列的設定／圖例面板（點按鈕開關的面板 `role=dialog`，不是滑過說明）",
};

function tagBefore(text: string, index: number): string | null {
  let last: string | null = null;
  for (const m of text.slice(0, index).matchAll(/<([A-Za-z][\w.]*)(?=[\s/>])/g)) last = m[1] ?? null;
  return last;
}

describe("浮動卡規則（6.5.1）", () => {
  it("沒有原生 title= tooltip（說明一律用 Hint／PartTip／技能卡）", () => {
    const bad: string[] = [];
    for (const [path, text] of files) {
      for (const m of text.matchAll(/\btitle=/g)) {
        const tag = tagBefore(text, m.index ?? 0);
        if (tag !== null && TITLE_PROP_OK.has(tag)) continue;
        const line = text.slice(0, m.index).split("\n").length;
        bad.push(`${path}:${line} <${tag ?? "?"} title=…>`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("沒有自製的 portal 彈出層", () => {
    const bad = files.filter(([path, text]) => !SHARED.has(path) && /createPortal\(/.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("沒有在元件裡用內聯樣式做 fixed／absolute 的彈出層", () => {
    const bad: string[] = [];
    for (const [path, text] of files) {
      if (SHARED.has(path)) continue;
      for (const m of text.matchAll(/position:\s*["'](fixed|absolute)["']/g)) {
        bad.push(`${path}:${text.slice(0, m.index).split("\n").length}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("`role=tooltip` 只出現在共用元件與 Hint／PartTip 的呼叫端", () => {
    const bad = files
      .filter(([path, text]) => !SHARED.has(path) && /role=["']tooltip["']/.test(text) && !/FloatCard/.test(text))
      .map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("`role=dialog` 的面板都在白名單（點擊開關的對話框／面板，不是說明卡）", () => {
    const bad = files.filter(([path, text]) => /role=["']dialog["']/.test(text) && NON_HOVER_POPUPS[path] === undefined).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("styles.css 裡 position: fixed 的規則只屬於共用浮動卡、對話框與遮罩", () => {
    const allowed = [".float-card", ".unit-float", ".modal-backdrop", ".decision-card"];
    const bad: string[] = [];
    for (const m of styles.matchAll(/([^{}]+)\{([^{}]*position:\s*fixed[^{}]*)\}/g)) {
      const selector = (m[1] ?? "").replace(/\/\*[\s\S]*?\*\//g, "").trim();
      if (!allowed.some((a) => selector.startsWith(a))) bad.push(selector);
    }
    expect(bad).toEqual([]);
  });
});
