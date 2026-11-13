// WP-3b：許願池的美術驗收修正（docs/art/WP-3驗收.md 必修 1 乙案、可修 1～6）、三個許願池圖示（Q版小圖示-第7批HUD.md 13.7）、
// 一輪與世界日誌統一「都不拿」（玩法 PM 定案）。和樣張逐像素（指紋）比對在開發頁 `hud-gallery.html?set=wishhash`（報告第 2 節）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { setQCanvasFactory } from "../render/qIcon/core";
import * as QH from "../render/qIcon/hud";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { readFile as readAt, SRC_DIR, stripCssComments } from "../test/sourceScan";
import { WishPanel } from "./WishPanel";
import { pickedFocus, WISH_ZH, type WishData } from "./wish";

const readFile = (path: string): string => readAt(SRC_DIR, path);
const log: FakeCanvasLog = { calls: null };
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => setQCanvasFactory(null));

const MENU = [
  { id: "ignite", name_zh: "點燃", description_zh: "火焰讓目標燃燒。" },
  { id: "frozen", name_zh: "冰凍", description_zh: "寒冰凍結目標。" },
  { id: "collision", name_zh: "撞擊", description_zh: "推擊把人撞上牆。" },
];

function wishData(over: Partial<WishData> = {}): WishData {
  return {
    title_zh: "許願池",
    speaker: { name_zh: "守池人", portrait: null, region: "capital" },
    line_zh: "池水記得每個走過這裡的人。",
    cost: 4,
    refund: 2,
    coins: 9,
    left: 2,
    per_week: 2,
    available: true,
    blocked_zh: null,
    llm: false,
    text_max_chars: 60,
    max_keywords: 2,
    menu: MENU,
    ...over,
  };
}

const render = (w: WishData) => renderToStaticMarkup(createElement(WishPanel, { wish: w, busy: false, fallback: null, onWish: () => {}, onBack: () => {} }));
const css = () => stripCssComments(readFile("styles/world-panel-wish.css"));

describe("WP-3b 三個許願池圖示", () => {
  it("三筆在另一張表 WISH（只搬推薦 A），不進 ICON／list()：第⑦批的指紋 55 行不動", () => {
    expect(Object.keys(QH.WISH)).toEqual(["wish_text", "wish_menu", "wish_left"]);
    expect(QH.wishList().map((e) => [e.id, e.entry.sizes])).toEqual([
      ["wish_text", [16]],
      ["wish_menu", [16]],
      ["wish_left", [15]],
    ]);
    for (const id of Object.keys(QH.WISH)) {
      expect(QH.ICON[id]).toBeUndefined();
      expect(QH.list().some((e) => e.id === id)).toBe(false);
    }
    // 沒有框：和 HudBare 的其他第⑦批「gen」同一條路徑
    for (const { entry } of QH.wishList()) expect(entry.grp).toBe("gen");
  });

  it("畫得出來（canvas 邊長＝顯示 × res）", () => {
    for (const { id, entry } of QH.wishList()) {
      const px = entry.sizes[0]!;
      expect(QH.canvas(id, px, 2, { frame: "none" }).width).toBe(px * 2);
      expect(QH.canvas(id, px, 1, { frame: "none" }).width).toBe(px);
    }
  });

  it("接線：分頁圖 16 在字前、本週還能許籌碼圖 15（照任務幣籌碼）；標題列不畫圖", () => {
    const html = render(wishData({ llm: true }));
    expect(html).toMatch(/data-tab="text"[^>]*>.*?<canvas[^>]*data-icon="wish_text"[^>]*>.*?<span class="lbl"/);
    expect(html).toMatch(/data-tab="menu"[^>]*>.*?<canvas[^>]*data-icon="wish_menu"[^>]*>.*?<span class="lbl"/);
    expect(html).toMatch(/<canvas[^>]*style="width:16px;height:16px"[^>]*data-icon="wish_text"/);
    expect(html).toMatch(/data-testid="wish-left"><canvas[^>]*style="width:15px;height:15px"[^>]*data-icon="wish_left"/);
    expect(html).toMatch(/data-testid="wish-coins"><canvas[^>]*data-icon="token"/);
    const head = html.slice(html.indexOf('data-testid="wish-head"'), html.indexOf("</h2>"));
    expect(head).not.toContain("<canvas");
  });
});

describe("WP-3b 必修 1：從選單挑＝乙案", () => {
  it("格子只放圓章＋名字（＋第 N 個），說明不在格子裡", () => {
    const html = render(wishData());
    const menu = html.slice(html.indexOf('data-testid="wish-menu"'), html.indexOf("</ul>"));
    expect(menu).toContain("點燃");
    for (const k of MENU) expect(menu).not.toContain(k.description_zh);
    expect(menu).not.toContain('class="desc');
  });

  it("說明在 Hint 說明卡（原始碼）：每格的按鈕包在 <Hint text={k.description_zh}>", () => {
    const src = readFile("world/WishPanel.tsx");
    expect(src).toContain("<Hint text={k.description_zh}>");
    // 不能點也看得到說明：用 aria-disabled，不用 disabled
    const pane = src.slice(src.indexOf("function MenuPane"), src.indexOf("function PickedNote"));
    expect(pane).toContain("aria-disabled={locked}");
    expect(pane).not.toMatch(/\sdisabled=\{/);
  });

  it("挑中的那一個（最後挑的）說明放在下固定區；拿掉後退回前一個；沒挑＝空白但佔位", () => {
    expect(pickedFocus(MENU, [])).toBeNull();
    expect(pickedFocus(MENU, ["frozen"])?.id).toBe("frozen");
    expect(pickedFocus(MENU, ["frozen", "ignite"])?.id).toBe("ignite");
    expect(pickedFocus(MENU, ["gone", "collision"])?.id).toBe("collision");
    expect(pickedFocus(MENU, ["collision", "gone"])?.id).toBe("collision");
    const empty = render(wishData());
    expect(empty).toMatch(/<div class="wish-picked" data-testid="wish-picked"><\/div>/);
  });

  it("CSS：寬版 4 欄、窄版 3 欄；下固定區預留兩行（兩個分頁同高）", () => {
    const c = css();
    expect(c).toMatch(/\.wish-menu \{[^}]*grid-template-columns: repeat\(4, minmax\(0, 1fr\)\)/);
    expect(c).toMatch(/@container world-panel \(max-width: 559px\) \{[^@]*\.wish-menu \{[^}]*grid-template-columns: repeat\(3, minmax\(0, 1fr\)\)/);
    expect(c).toMatch(/\.wish-picked \{[^}]*min-height: calc\(2 \* 1\.5 \* 12\.5px \+ 6px\)/);
  });
});

describe("WP-3b 可修 1～6", () => {
  it("1：HUD 彈窗的捲動區預留捲軸寬", () => {
    expect(stripCssComments(readFile("styles/theme.css"))).toMatch(/\.ui-popup-hud > \.ui-popup-body \{\s*scrollbar-gutter: stable;/);
  });
  it("2：矮視窗（≤ 820 高）守池人收成標題旁一行", () => {
    expect(css()).toMatch(/@media \(max-height: 820px\) \{\s*\.wish-panel \.pnl-speaker \{\s*display: none;\s*\}\s*\.wish-panel \.pnl-speaker-mini \{\s*display: flex;/);
  });
  it("3：偏離路線不用虛線框", () => {
    const run = stripCssComments(readFile("styles/run.css"));
    const rule = run.match(/\.run-offer-card\.off-route \{[^}]*\}/)?.[0] ?? "";
    expect(rule).not.toBe("");
    expect(rule).not.toContain("dashed");
  });
  it("4：說明句 text-wrap: pretty；5：選單格 align-content: start", () => {
    const c = css();
    expect(c).toMatch(/\.wish-lead \{[^}]*text-wrap: pretty/);
    expect(c).toMatch(/\.wish-picked-desc \{[^}]*text-wrap: pretty/);
    expect(c).toMatch(/\.wish-kw \{[^}]*align-content: start/);
  });
  it("6：不能許時「得到」那列也灰掉", () => {
    expect(css()).toMatch(/\.wish-foot\.off \.fc-diffs > :nth-last-child\(-n \+ 5\) \{[^}]*opacity: 0\.55/);
    const html = render(wishData({ coins: 2, available: false, blocked_zh: "任務幣不足" }));
    expect(html).toContain('class="wish-foot off"');
    // 「得到」固定是最後一列（CSS 用最後 5 格選它）
    expect(html.lastIndexOf(WISH_ZH.gain)).toBeGreaterThan(html.lastIndexOf(WISH_ZH.notEnough));
  });
});

describe("WP-3b 一輪三選一統一「都不拿」", () => {
  it("一輪的三選一按鈕與說明不再寫「跳過」", () => {
    for (const f of ["screens/RunCompleteOffer.tsx", "screens/RunLevelUp.tsx", "screens/RunGearOffer.tsx"]) {
      const code = readFile(f).replace(/^\s*\/\/.*$/gm, "");
      expect(code, f).not.toContain("跳過");
    }
    expect(readFile("screens/RunCompleteOffer.tsx")).toContain('"都不拿"');
    expect(readFile("screens/RunLevelUp.tsx")).toContain('"確定（技能都不拿）"');
    expect(readFile("screens/RunGearOffer.tsx")).toContain('"都不拿（不換裝備）"');
  });
});
