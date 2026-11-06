// 6T-1d（docs/art/6T-1c檢查.md）：郵寄面板收尾（寄出黏在底部、捲動區上緣不透明、附件格說明卡往下開、青石郵筒的苔）
// 與全遊戲主要按鈕（滑過亮一階、只有停用才是深灰）。
import { describe, expect, it } from "vitest";
import { POSTBOX_MOSS, POSTBOX_MOSS_HI } from "../render/objectArt";
import { floatPlacement } from "../ui/floatCard";

const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const baseCss = readFileSync("src/styles/base.css", "utf-8");
const entryCss = readFileSync("src/styles/entry.css", "utf-8");
const mailCss = readFileSync("src/world/mail.css", "utf-8");
const panelSrc = readFileSync("src/world/MailPanel.tsx", "utf-8");

/** 選擇器（完全相同）對應的規則內容。 */
function rule(css: string, selector: string): string | null {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`).exec(css);
  return m === null ? null : m[1]!;
}

const lum = (hex: string): number => {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
};

describe("6T-1d 小修 7：全遊戲主要按鈕", () => {
  it("滑過時亮一階（不是共用 button:hover 的深灰）", () => {
    const hover = rule(baseCss, "button.primary:hover:not(:disabled)");
    expect(hover).not.toBeNull();
    expect(hover).toContain("background: #4d6cb3");
    expect(lum("#4d6cb3")).toBeGreaterThan(lum("#3d5a99"));
  });

  it("只有停用時才是深灰；建角畫面的主要按鈕停用也是灰底", () => {
    expect(rule(baseCss, "button.primary:disabled")).toContain("background: #36364a");
    expect(rule(baseCss, "button:disabled")).toContain("opacity: 0.45"); // 停用照舊半透明
    expect(rule(entryCss, ".entry-skin button.primary:disabled")).toContain("linear-gradient(180deg, #3a3c50, #2c2e40)");
  });

  it("郵寄面板不再自己蓋一條滑過規則（改由 base.css 全遊戲一起）", () => {
    expect(mailCss).not.toContain(".world-mail button.primary:hover");
  });
});

describe("6T-1d 小修 3、4：寄出黏在底部、捲動區上緣不透明", () => {
  it("「寄出」那一列在兩欄格線外面、黏在捲動區底部、不透明底", () => {
    const wrap = panelSrc.indexOf('className="mail-send-wrap"');
    const grid = panelSrc.indexOf('className="mail-send" data-testid="mail-send"');
    const check = panelSrc.indexOf('data-testid="mail-check"');
    const actions = panelSrc.indexOf('className="mail-actions"');
    expect(wrap).toBeGreaterThan(-1);
    expect(grid).toBeGreaterThan(wrap);
    // 檢查框之後、mail-actions 之前要先關掉 mail-send-main 與 mail-send 兩層
    const between = panelSrc.slice(panelSrc.indexOf("</section>", check), actions);
    expect(between.match(/<\/div>/g)?.length).toBe(2);
    const css = rule(mailCss, ".mail-actions");
    expect(css).toContain("position: sticky");
    expect(css).toContain("bottom: 0");
    expect(css).toContain("background: var(--ui-navy)");
  });

  it("郵寄面板捲下去以後的上緣色塊是實色（沒有半透明的漸層）", () => {
    const top = rule(mailCss, '.world-hud-panel[data-panel="mail"] > .ui-popup-body::before');
    expect(top).toContain("background: var(--ui-navy);");
    expect(top).not.toContain("gradient");
  });
});

describe("6T-1d 小修 5：附件格的說明卡先往下開", () => {
  const view = { width: 1600, height: 900 };
  const size = { width: 80, height: 36 };
  it("prefer below：下方放得下就放下方，放不下才翻到上方", () => {
    expect(floatPlacement({ left: 100, top: 300, width: 24, height: 26 }, size, view, "center", 4, "below").side).toBe("below");
    expect(floatPlacement({ left: 100, top: 860, width: 24, height: 26 }, size, view, "center", 4, "below").side).toBe("above");
    expect(floatPlacement({ left: 100, top: 300, width: 24, height: 26 }, size, view, "center").side).toBe("above"); // 預設不變
  });

  it("附件格的 −／＋／×／裝備格的說明卡都 prefer below", () => {
    for (const t of ['"少寄 1 個"} prefer="below"', '"多寄 1 個"} prefer="below"', 'text="拿掉這一格" prefer="below"', 'text="點了拿掉" prefer="below"']) {
      expect(panelSrc).toContain(t);
    }
  });
});

describe("6T-1d 小修 6：青石郵筒的苔再加深一階", () => {
  it("苔斑比 6T-1c 的 #2a5e18 深、亮點比 #8ac850 亮", () => {
    expect(lum(POSTBOX_MOSS)).toBeLessThan(lum("#2a5e18"));
    expect(lum(POSTBOX_MOSS_HI)).toBeGreaterThan(lum("#8ac850"));
  });
});
