// 浮動卡自動檢查（Phase 3-32b；規則見 docs/開發PM交接.md 6.5.1）：
// `client/src` 除了共用浮動卡元件之外，不准有自製的彈出層或原生 `title=` tooltip。
// 這裡用文字規則掃原始碼；有正當理由的例外一律列在白名單，並寫明原因。
import { describe, expect, it } from "vitest";
import { readSources, readStyleFiles, stripCssComments, stripTsComments } from "../test/sourceScan";

// 6C-R1：原始碼與 CSS 都在執行時用 node 的 fs 遞迴讀（`test/sourceScan.ts`），不用 `import.meta.glob`——
// vitest 的 fsModuleCache 會把 glob 的檔案清單跟著測試檔一起快取，新加的檔案不會被掃到。
// CSS 掃 `src/**/*.css`（含 `world/*.css`）；全部串起來檢查（規則只看內容，不看層疊順序）。
const styleFiles = readStyleFiles().map(([path, text]) => [path, stripCssComments(text)] as const);
const styles: string = styleFiles.map(([, text]) => text).join("\n");

/** 去掉註解（保留換行，行號不變）：說明文字裡提到 `title=` 不算違規。 */
const files = readSources().map(([path, text]) => [path, stripTsComments(text, path)] as const);

/** 共用浮動卡元件本身：可以用 portal、`position: fixed`。 */
const SHARED = new Set(["ui/useFloatCard.tsx", "ui/HoverFloat.tsx", "ui/Hint.tsx", "ui/PartTip.tsx"]);

/**
 * 內聯 `position: fixed／absolute` 的例外：檔名 → 原因。不是彈出層、也不是正式畫面的才放這裡。
 */
const INLINE_POSITION_OK: Record<string, string> = {
  "dev/storyGallery.tsx":
    "開發用樣張頁（`story-gallery.html`，不進正式 build、不屬於正式畫面）：`position: absolute` 只用在假戰場底圖的格線層與下方頭像對照面板的版面，不是彈出層（6C-R1）",
};

/** 允許帶 `title=` 的元件標籤：`title` 是它的 prop（視窗標題），不是 DOM 的 tooltip 屬性。 */
const TITLE_PROP_OK = new Set(["DialogFrame"]);

/**
 * 不是「滑過顯示的說明卡」、但有自己的彈出外觀的元件（點擊才開的選單、對話框）。
 * 檔名 → 原因。新增這類元件時要在這裡列出並寫明原因，否則測試會擋下。
 */
const NON_HOVER_POPUPS: Record<string, string> = {
  "ui/DialogFrame.tsx": "反應詢問／複製／灌注等對話框的外框（`role=dialog`，互動式，不是說明卡）",
  "ui/PopupFrame.tsx": "UI-E2 共用彈窗元件（大世界面板、遇敵卡、事件卡、詢問視窗的外框；`role` 由呼叫端傳入，點擊開關，不是說明卡）",
  "ui/BattleTopBar.tsx": "頂端列的設定／圖例面板（點按鈕開關的面板 `role=dialog`；已改用 `usePopupMenu`，見下方檢查）",
  "world/WorldHud.tsx": "大世界 HUD 功能列的浮動面板（6B-5：點圖示或快捷鍵開關、同時一個、Esc 關閉；不是說明卡）",
  "world/RegionMap.tsx": "區域圖（6C-6：M 或地圖鈕開關的全畫面面板，Esc 關閉；不是說明卡）",
  "world/AtlasMap.tsx": "大世界圖（6D-5：在區域圖上按 M 或鈕切換的全畫面面板，Esc 關閉；不是說明卡）",
};

/** 這些檔案裡的點擊式面板必須用 `usePopupMenu`（Esc、點外面關閉、同時一張）。 */
const MUST_USE_POPUP_MENU = ["ui/BattleTopBar.tsx", "ui/TurnControls.tsx"];

function tagBefore(text: string, index: number): string | null {
  let last: string | null = null;
  for (const m of text.slice(0, index).matchAll(/<([A-Za-z][\w.]*)(?=[\s/>])/g)) last = m[1] ?? null;
  return last;
}

describe("浮動卡規則（6.5.1）", () => {
  it("讀得到 src/**/*.css 與各資料夾原始碼（規則不是對空清單空過）", () => {
    expect(styles.length).toBeGreaterThan(10000);
    expect(styleFiles.map(([p]) => p)).toContain("world/story.css");
    expect(files.length).toBeGreaterThan(100);
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
    /** portal 但不是彈出層：檔名 → 原因。 */
    const PORTAL_OK: Record<string, string> = {
      "ui/PopupSlot.tsx": "FL-1b 上下固定區插槽（`PopupFrame slots`）：把同一個面板的標頭與確定列放進框的不捲區，不是浮在畫面上的彈出層",
    };
    const bad = files.filter(([path, text]) => !SHARED.has(path) && !(path in PORTAL_OK) && /createPortal\(/.test(text)).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("沒有在元件裡用內聯樣式做 fixed／absolute 的彈出層", () => {
    const bad: string[] = [];
    for (const [path, text] of files) {
      if (SHARED.has(path) || INLINE_POSITION_OK[path] !== undefined) continue;
      // 內聯樣式物件 `position: "fixed"`，以及直接改 DOM 的 `el.style.position = "fixed"`（5D-R1 補）
      for (const m of text.matchAll(/(?:position:|\.position\s*=)\s*["'](fixed|absolute)["']/g)) {
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

  it(".decision-card 有最大高度並可捲動（小視窗不被切掉；UI-E2 起在共用彈窗的 .ui-popup-body 裡捲）", () => {
    const m = styles.match(/^\.decision-card\s*\{([^{}]*)\}/m);
    expect(m?.[1]).toMatch(/max-height:/);
    const body = styles.match(/\.ui-popup-dialog > \.ui-popup-body\s*\{([^{}]*)\}/);
    expect(body?.[1]).toMatch(/overflow-y:\s*auto/);
    expect(body?.[1]).toMatch(/min-height:\s*0/);
    const frame = styles.match(/\.ui-popup-dialog\s*\{([^{}]*)\}/);
    expect(frame?.[1]).toMatch(/display:\s*flex/);
    expect(frame?.[1]).toMatch(/overflow:\s*hidden/);
  });

  it("UI-E2：彈窗外框一律用共用彈窗元件 PopupFrame（大世界面板、遇敵卡、事件卡、詢問視窗）", () => {
    const uses: Record<string, RegExp> = {
      "world/WorldHud.tsx": /<PopupFrame[\s\S]*?className="world-hud-panel"/,
      "world/WorldPanel.tsx": /<PopupFrame[\s\S]*?tone="danger"[\s\S]*?className="world-encounter"/,
      "world/EventCard.tsx": /<PopupFrame[\s\S]*?className="world-event"/,
      // UI-E1 追加 2：大世界時多一個 world-dialog class（照 HUD 規則放），所以 className 是樣板字串
      "ui/DialogFrame.tsx": /<PopupFrame[\s\S]*?className=\{?[`"]decision-card/,
    };
    for (const [path, re] of Object.entries(uses)) {
      const text = files.find(([p]) => p === path)?.[1] ?? "";
      expect(text, path).toMatch(re);
    }
    // 舊的自製外框不再出現
    for (const [path, old] of [
      ["world/WorldHud.tsx", /<div\s+className="world-hud-panel"/],
      ["world/WorldPanel.tsx", /className="panel world-encounter"/],
      ["world/EventCard.tsx", /className="panel world-event"/],
      ["ui/DialogFrame.tsx", /<div className={`decision-card/],
    ] as const) {
      expect(files.find(([p]) => p === path)?.[1] ?? "", path).not.toMatch(old);
    }
    // 共用元件本身不做 fixed／absolute 內聯定位、不用 portal（位置規則只是 top／寬高）
    const frame = files.find(([p]) => p === "ui/PopupFrame.tsx")?.[1] ?? "";
    expect(frame).toMatch(/export function PopupFrame/);
    expect(frame).not.toMatch(/createPortal|position:/);
  });

  it("`role=dialog` 的面板都在白名單（點擊開關的對話框／面板，不是說明卡）", () => {
    const bad = files.filter(([path, text]) => /role=["']dialog["']/.test(text) && NON_HOVER_POPUPS[path] === undefined).map(([path]) => path);
    expect(bad).toEqual([]);
  });

  it("src/**/*.css 裡 position: fixed 的規則只屬於共用浮動卡、對話框與遮罩", () => {
    const allowed = [".float-card", ".unit-float", ".decision-card"];
    const bad: string[] = [];
    for (const [path, text] of styleFiles) {
      for (const m of text.matchAll(/([^{}]+)\{([^{}]*position:\s*fixed[^{}]*)\}/g)) {
        const selector = (m[1] ?? "").trim();
        if (!allowed.some((a) => selector.startsWith(a))) bad.push(`${path}: ${selector}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("src/**/*.css 裡 position: absolute 且 z-index ≥ 20 的規則只屬於共用彈出元件", () => {
    // `.popup-menu`：點擊式選單（6A-4g：舊版的拖曳分隔線 `.resize-handle` 已刪）
    const allowed = [".float-card", ".unit-float", ".decision-card", ".popup-menu"];
    const bad: string[] = [];
    for (const [path, text] of styleFiles) {
      for (const m of text.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
        const body = m[2] ?? "";
        if (!/position:\s*(absolute|fixed)/.test(body)) continue;
        const z = /z-index:\s*(\d+)/.exec(body);
        if (z === null || Number(z[1]) < 20) continue;
        const selector = (m[1] ?? "").trim();
        if (!allowed.some((a) => selector.startsWith(a))) bad.push(`${path}: ${selector}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("src/**/*.css 沒有已移除的死碼（.modal-backdrop、.fallback-list）", () => {
    expect(styles).not.toMatch(/\.modal-backdrop|\.fallback-list/);
  });

  it("每個 <FloatCard> 要嘛帶 .skill-card（SkillCardView）、要嘛用有底色的變體（part-tip-box／float-panel）", () => {
    // 3U-1：種族卡的浮動卡內容不是技能卡，整張透明，說明文字疊在畫面文字上
    const bad: string[] = [];
    for (const [path, text] of files) {
      if (SHARED.has(path)) continue;
      for (const m of text.matchAll(/<FloatCard\b([^>]*)>([\s\S]*?)<\/FloatCard>/g)) {
        const attrs = m[1] ?? "";
        const body = m[2] ?? "";
        const hasBg = /\b(part-tip-box|float-panel)\b/.test(attrs);
        if (!hasBg && !/<SkillCardView\b/.test(body)) bad.push(`${path}:${text.slice(0, m.index).split("\n").length}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it(".float-panel 的內容區有不透明底色與邊框", () => {
    const m = styles.match(/\.float-card\.float-panel\s*>\s*\.float-card-body\s*\{([^{}]*)\}/);
    // UI-E1b：改用共用彈窗的深藍（--ui-navy＝#1e2236，不透明）
    expect(m?.[1]).toMatch(/background:\s*(#[0-9a-f]{6}|var\(--ui-navy\))/i);
    expect(m?.[1]).toMatch(/border:/);
  });
});
