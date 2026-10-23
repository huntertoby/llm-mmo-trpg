// 浮動卡自動檢查（Phase 3-32b；規則見 docs/開發PM交接.md 6.5.1）：
// `client/src` 除了共用浮動卡元件之外，不准有自製的彈出層或原生 `title=` tooltip。
// 這裡用文字規則掃原始碼；有正當理由的例外一律列在白名單，並寫明原因。
import { describe, expect, it } from "vitest";
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀 CSS 檔
import { readFileSync } from "node:fs";

// 注意：vitest 預設不處理 CSS，`styles.css?raw` 會變成空字串（舊的 CSS 規則因此形同虛設），所以直接讀檔。
const styles: string = (readFileSync as (url: URL, enc: string) => string)(new URL("../styles.css", import.meta.url), "utf8");

const sources = import.meta.glob<string>(["/src/**/*.tsx", "/src/**/*.ts", "!/src/**/*.test.ts", "!/src/**/*.d.ts"], {
  query: "?raw",
  import: "default",
  eager: true,
});
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
  "ui/BattleTopBar.tsx": "頂端列的設定／圖例面板（點按鈕開關的面板 `role=dialog`；已改用 `usePopupMenu`，見下方檢查）",
};

/** 這些檔案裡的點擊式面板必須用 `usePopupMenu`（Esc、點外面關閉、同時一張）。 */
const MUST_USE_POPUP_MENU = ["ui/BattleTopBar.tsx", "ui/TurnControls.tsx"];

function tagBefore(text: string, index: number): string | null {
  let last: string | null = null;
  for (const m of text.slice(0, index).matchAll(/<([A-Za-z][\w.]*)(?=[\s/>])/g)) last = m[1] ?? null;
  return last;
}

describe("浮動卡規則（6.5.1）", () => {
  it("讀得到 styles.css（CSS 規則不是對空字串空過）", () => {
    expect(styles.length).toBeGreaterThan(10000);
  });

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

  it("`role=tooltip` 只出現在共用浮動卡元件（Hint／PartTip 的卡片本體；`[role=\"tooltip\"]` 查詢選擇器不算）", () => {
    const bad = files.filter(([path, text]) => !SHARED.has(path) && /(?<!\[)role=["']tooltip["']/.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("點擊式選單（更多動作、頂端面板）都套用 `popup-menu` 並使用 `usePopupMenu`", () => {
    for (const path of MUST_USE_POPUP_MENU) {
      const text = files.find(([p]) => p === path)?.[1] ?? "";
      expect(text, path).toMatch(/usePopupMenu\(/);
      expect(text, path).toMatch(/popup-menu/);
    }
    const hook = files.find(([p]) => p === "ui/usePopupMenu.ts")?.[1] ?? "";
    expect(hook).toMatch(/stopPropagation\(\)/); // Esc 處理過就不讓 BattleScreen 再取消瞄準
    expect(hook).toMatch(/pointerdown/);
  });

  it("`.more-list`、`.top-popup` 不自己定位（位置與捲動來自 `.popup-menu`）", () => {
    for (const sel of [".more-list", ".top-popup"]) {
      const m = styles.match(new RegExp(`^\\${sel}\\s*\\{([^{}]*)\\}`, "m"));
      expect(m, sel).not.toBeNull();
      expect(m?.[1], sel).not.toMatch(/position:|z-index:/);
    }
    expect(styles).toMatch(/\.popup-menu\s*\{[^{}]*overflow-y:\s*auto/);
  });

  it(".decision-card 有最大高度並可捲動（小視窗不被切掉）", () => {
    const m = styles.match(/^\.decision-card\s*\{([^{}]*)\}/m);
    expect(m?.[1]).toMatch(/max-height:/);
    expect(m?.[1]).toMatch(/overflow-y:\s*auto/);
  });

  it("`role=dialog` 的面板都在白名單（點擊開關的對話框／面板，不是說明卡）", () => {
    const bad = files.filter(([path, text]) => /role=["']dialog["']/.test(text) && NON_HOVER_POPUPS[path] === undefined).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("styles.css 裡 position: fixed 的規則只屬於共用浮動卡、對話框與遮罩", () => {
    const allowed = [".float-card", ".unit-float", ".decision-card"];
    const bad: string[] = [];
    for (const m of styles.matchAll(/([^{}]+)\{([^{}]*position:\s*fixed[^{}]*)\}/g)) {
      const selector = (m[1] ?? "").replace(/\/\*[\s\S]*?\*\//g, "").trim();
      if (!allowed.some((a) => selector.startsWith(a))) bad.push(selector);
    }
    expect(bad).toEqual([]);
  });

  it("styles.css 裡 position: absolute 且 z-index ≥ 20 的規則只屬於共用彈出元件或版面分隔線", () => {
    // `.popup-menu`：點擊式選單；`.resize-handle`：拖曳分隔線（版面，不是彈出層）
    const allowed = [".float-card", ".unit-float", ".decision-card", ".popup-menu", ".resize-handle"];
    const bad: string[] = [];
    for (const m of styles.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const body = m[2] ?? "";
      if (!/position:\s*(absolute|fixed)/.test(body)) continue;
      const z = /z-index:\s*(\d+)/.exec(body);
      if (z === null || Number(z[1]) < 20) continue;
      const selector = (m[1] ?? "").replace(/\/\*[\s\S]*?\*\//g, "").trim();
      if (!allowed.some((a) => selector.startsWith(a))) bad.push(selector);
    }
    expect(bad).toEqual([]);
  });

  it("styles.css 沒有已移除的死碼（.modal-backdrop、.fallback-list）", () => {
    expect(styles).not.toMatch(/\.modal-backdrop|\.fallback-list/);
  });
});
