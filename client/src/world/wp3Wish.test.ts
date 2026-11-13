// WP-3：許願池面板（`WishPanel.tsx`、`wish.ts`）、主城物件開面板、文字許願先等 LLM、三選一的標題與「都不拿（退 N 任務幣）」。
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { nowStyle } from "../run/flashChoice";
import { objectHud } from "./atlasModel";
import { panelAvailable } from "./hud";
import { PREGEN_WAIT_NOTE, pregenRequestId, pregenWaitBody, pregenWaitNote, pregenWaitText } from "./pregen";
import { WishPanel } from "./WishPanel";
import {
  offerSkipLabel,
  offerSubtitle,
  offerTitle,
  toggleKeyword,
  WISH_ZH,
  wishAction,
  wishDiffs,
  wishModes,
  wishSubmitBlock,
  type WishData,
} from "./wish";

function wishData(over: Partial<WishData> = {}): WishData {
  return {
    title_zh: "許願池",
    speaker: { name_zh: "守池人", portrait: null, region: "capital" },
    line_zh: "池水記得每個走過這裡的人。說說你想要什麼樣的力量——說得越具體，它越聽得懂。",
    cost: 4,
    refund: 2,
    coins: 9,
    left: 2,
    per_week: 2,
    available: true,
    blocked_zh: null,
    llm: true,
    text_max_chars: 60,
    max_keywords: 2,
    menu: [
      { id: "ignite", name_zh: "點燃", description_zh: "火焰讓目標燃燒。" },
      { id: "frozen", name_zh: "冰凍", description_zh: "寒冰凍結目標。" },
      { id: "collision", name_zh: "撞擊", description_zh: "推擊把人撞上牆。" },
    ],
    ...over,
  };
}

const render = (w: WishData, fallback: { seq: number; text: string } | null = null) =>
  renderToStaticMarkup(createElement(WishPanel, { wish: w, busy: false, fallback, onWish: () => {}, onBack: () => {} }));

describe("WP-3 許願池：純函式", () => {
  it("LLM 開著有兩種許法、關著只有選單", () => {
    expect(wishModes({ llm: true })).toEqual(["text", "menu"]);
    expect(wishModes({ llm: false })).toEqual(["menu"]);
  });

  it("選單點關鍵字：照點的順序、最多 2 個、再點一次拿掉", () => {
    expect(toggleKeyword([], "frozen", 2)).toEqual(["frozen"]);
    expect(toggleKeyword(["frozen"], "collision", 2)).toEqual(["frozen", "collision"]);
    expect(toggleKeyword(["frozen", "collision"], "ignite", 2)).toEqual(["frozen", "collision"]);
    expect(toggleKeyword(["frozen", "collision"], "frozen", 2)).toEqual(["collision"]);
  });

  it("送出鈕：伺服器說不能許＝它的原因；文字空白、沒挑關鍵字＝提示；其他可以按", () => {
    const w = wishData();
    expect(wishSubmitBlock(w, "text", "  ", [])).toBe(WISH_ZH.needText);
    expect(wishSubmitBlock(w, "text", "想把敵人凍住", [])).toBeNull();
    expect(wishSubmitBlock(w, "menu", "", [])).toBe(WISH_ZH.needKeyword);
    expect(wishSubmitBlock(w, "menu", "", ["frozen"])).toBeNull();
    const off = wishData({ available: false, blocked_zh: "任務幣不足，許願要 4 任務幣" });
    expect(wishSubmitBlock(off, "menu", "", ["frozen"])).toBe("任務幣不足，許願要 4 任務幣");
  });

  it("世界動作：文字許願帶 keywords: []（WP-2 待決 5）、去頭尾空白；選單許願不帶 text", () => {
    expect(wishAction("text", "  想把敵人凍住 ", ["frozen"])).toEqual({ kind: "wish", text: "想把敵人凍住", keywords: [] });
    expect(wishAction("menu", "隨便", ["frozen", "collision"])).toEqual({ kind: "wish", keywords: ["frozen", "collision"] });
  });

  it("前 → 後：任務幣與本週次數是代價、三選一是新（FL-1b 記號）；付不起、沒次數照寫", () => {
    const rows = wishDiffs(wishData());
    expect(rows.map((r) => [r.name_zh, r.before_zh, r.after_zh, nowStyle(r)])).toEqual([
      ["任務幣", "9", "5", "cost"],
      ["本週次數", "剩 2 次", "剩 1 次", "cost"],
      ["得到", null, "技能三選一", "new"],
    ]);
    const poor = wishDiffs(wishData({ coins: 3, left: 0 }));
    expect(poor[0]?.after_zh).toBe(WISH_ZH.notEnough);
    expect(poor[1]?.after_zh).toBe(WISH_ZH.noneLeft);
  });

  it("三選一畫面：許願池的標題、副標、都不拿（退 N 任務幣）；任務與機遇照舊", () => {
    const wish = { source: "wish" as const, quest_name_zh: "許願池", step_zh: "許願：都不拿可退 2 任務幣（次數照扣）。", refund: 2 };
    expect(offerTitle(wish)).toBe("許願池");
    expect(offerSubtitle(wish)).toBe("許願：都不拿可退 2 任務幣（次數照扣）。");
    expect(offerSkipLabel(wish)).toBe("都不拿（退回 2 任務幣）"); // TXT-2
    const quest = { source: "quest" as const, quest_name_zh: "迷路的信", step_zh: "交給守印人", refund: 0 };
    expect(offerTitle(quest)).toBe("任務給的技能三選一");
    expect(offerSubtitle(quest)).toBe("迷路的信：交給守印人");
    expect(offerSkipLabel(quest)).toBe("都不拿"); // TXT-2：用詞統一成「都不拿」
  });
});

describe("WP-3 許願池：接線", () => {
  it("池子與守池人開許願池面板；人在主城（有 wish）才開得了", () => {
    expect(objectHud({ panel: "wish" })).toEqual({ panel: "wish", who: null });
    expect(panelAvailable({ wish: wishData() } as unknown as WorldView, "wish")).toBe(true);
    expect(panelAvailable({ wish: null } as unknown as WorldView, "wish")).toBe(false);
  });

  it("文字許願先等 LLM（kind: wish，帶願望）；選單許願不等", () => {
    const body = pregenWaitBody({ kind: "wish", text: "想把敵人凍住", keywords: [] });
    expect(body).toEqual({ kind: "wish", text: "想把敵人凍住" });
    expect(pregenWaitText(body!)).toBe(WISH_ZH.waitText);
    expect(pregenRequestId(body!)).toBe("wish:想把敵人凍住");
    expect(pregenWaitNote(body!)).toBe(WISH_ZH.waitNote);
    expect(pregenWaitNote({ kind: "flash", skill: "s" })).toBe(PREGEN_WAIT_NOTE);
    expect(pregenWaitBody({ kind: "wish", keywords: ["frozen"] })).toBeNull();
  });

  it("三選一畫面用 offerTitle／offerSubtitle／offerSkipLabel（不再寫死「任務給的技能三選一」「跳過」）", () => {
    const src = (readFileSync as (url: URL, enc: string) => string)(new URL("./QuestLog.tsx", import.meta.url), "utf-8");
    expect(src).toContain("{offerTitle(pending)}");
    expect(src).toContain("{offerSkipLabel(pending)}");
    expect(src).not.toContain("<h2>任務給的技能三選一</h2>");
  });
});

describe("WP-3 許願池：面板", () => {
  it("可以許：標題、守池人、籌碼、兩個分頁、願望輸入框（字數上限）、前 → 後與許願鈕", () => {
    const html = render(wishData());
    expect(html).toContain('data-available="1"');
    expect(html).toContain("許願池");
    expect(html).toContain("守池人");
    expect(html).toContain('data-testid="wish-coins"');
    expect(html).toContain('role="tablist"');
    expect(html).toContain(WISH_ZH.tabText);
    expect(html).toContain(WISH_ZH.tabMenu);
    expect(html).toContain('maxLength="60"');
    expect(html).toContain('data-testid="flash-diffs"');
    expect(html).toContain(WISH_ZH.refundNote(2));
    expect(html).not.toContain('data-testid="wish-blocked"');
    // 還沒寫願望：鈕按不下去、旁邊說為什麼
    expect(html).toMatch(/data-testid="wish-submit"[^>]*disabled|disabled[^>]*data-testid="wish-submit"/);
    expect(html).toContain(WISH_ZH.needText);
  });

  it("不能許：第一行「現在不能用：原因」、表單灰掉", () => {
    const html = render(wishData({ coins: 2, available: false, blocked_zh: "任務幣不足，許願要 4 任務幣" }));
    expect(html).toContain('data-available="0"');
    expect(html).toContain('class="wish-panel off"');
    expect(html).toContain("<b>現在不能用</b>：任務幣不足，許願要 4 任務幣");
    expect(html).toMatch(/<textarea[^>]*disabled/);
    expect(html).toContain(WISH_ZH.notEnough);
    // 原因只寫在第一行，送出列不重複
    expect(html).not.toContain('data-testid="wish-need"');
  });

  it("LLM 關著：只有選單、不畫分頁列", () => {
    const html = render(wishData({ llm: false }));
    expect(html).not.toContain('role="tablist"');
    expect(html).not.toContain("<textarea");
    expect(html).toContain('data-testid="wish-menu"');
    expect(html).toContain('data-kw="frozen"');
    expect(html).toContain(WISH_ZH.needKeyword);
  });

  it("逾時或被退回：開在選單分頁，第一行說明", () => {
    const html = render(wishData(), { seq: 1, text: WISH_ZH.timeout });
    expect(html).toContain('data-pane="menu"');
    expect(html).toContain('data-testid="wish-fallback"');
    expect(html).toContain(WISH_ZH.timeout);
  });
});
