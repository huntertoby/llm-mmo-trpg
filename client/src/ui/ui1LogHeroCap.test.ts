// UI-1（美術 PM BS-2 驗收複驗）：800×600 展開的戰鬥紀錄上緣被左上主角卡蓋住約 100px，標題列、擲骰細節、釘選鈕點不到。
// 修法：沒選取時紀錄的高度上限扣掉主角卡（上緣停在主角卡下緣＋8px）；1600 等夠高的視窗照舊是 58%。
// 實機量測（無頭 Chrome 真 1 倍）見 docs/phases/PhaseUI-1報告.md；這裡是純函式、標記與原始碼結構。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { heroLogCap, LOG_MIN_PX, LOG_ROOM_GAP, logDockMaxHeight, logLimit } from "../battle/logRoom";
import { readFile, SRC_DIR, stripCssComments } from "../test/sourceScan";
import { BattleLogDockView } from "./BattleLogDock";

const dock = (heroCap: number | null, limit: ReturnType<typeof logLimit> = null) =>
  renderToStaticMarkup(
    createElement(BattleLogDockView, {
      toasts: [],
      open: true,
      pinned: false,
      onToggleOpen: () => undefined,
      onTogglePin: () => undefined,
      log: () => createElement("div", { className: "battle-log" }, "紀錄"),
      limit,
      heroCap,
    }),
  );

describe("UI-1：紀錄上緣停在主角卡下緣", () => {
  it("上限 ＝ 紀錄底邊 − 主角卡下緣 − 8px（實機 800×600：底 450、主角卡 156 → 286）", () => {
    expect(heroLogCap(450, 156)).toBe(450 - 156 - LOG_ROOM_GAP);
    expect(heroLogCap(450, 156)).toBe(286);
  });

  it("量不到主角卡或紀錄時不限", () => {
    expect(heroLogCap(450, null)).toBeNull();
    expect(heroLogCap(0, 156)).toBeNull();
    expect(logDockMaxHeight(null, null)).toBeUndefined();
    expect(dock(null)).not.toContain("max-height");
  });

  it("空間不到 3 行時至少給 3 行", () => {
    expect(heroLogCap(200, 156)).toBe(LOG_MIN_PX);
  });

  it("沒選取：只加高度上限，不加 squeezed（清單照原本的伸縮方式）", () => {
    const html = dock(286);
    expect(html).toContain('class="log-dock open"');
    expect(html).not.toContain("squeezed");
    expect(html).toContain("max-height:min(58%, 286px)");
  });

  it("1600×900 的上限（552px）比 58% 大，min() 照舊取 58%：版面不變", () => {
    // 實機：紀錄底 716、主角卡 156 → 552；紀錄的 58% ＝ 352px（量到的紀錄高度，修前修後相同）
    expect(heroLogCap(716, 156)).toBe(552);
    expect(dock(552)).toContain("max-height:min(58%, 552px)");
  });

  it("選取中照舊用選取面板的上限（比主角卡嚴）", () => {
    expect(logDockMaxHeight(logLimit(200), 286)).toBe("min(58%, 200px)");
    expect(logDockMaxHeight(logLimit(40), 286)).toBe(`${LOG_MIN_PX}px`);
    const html = dock(286, logLimit(200));
    expect(html).toContain("squeezed");
    expect(html).toContain("max-height:min(58%, 200px)");
    expect(html).not.toContain("286px");
  });
});

describe("UI-1：接線與樣式", () => {
  it("戰鬥畫面量主角卡並傳給紀錄", () => {
    const screen = readFile(SRC_DIR, "screens/BattleScreen.tsx");
    expect(screen).toMatch(/useHeroLogCap\(boardRef,/);
    expect(screen).toMatch(/<BattleLogDock[^>]*heroCap=\{heroLogCapPx\}/);
    const hook = readFile(SRC_DIR, "screens/battle/useLogRoom.ts");
    expect(hook).toContain('querySelector<HTMLElement>(".bhud-hero")');
  });

  it("紀錄被壓矮時圖示不縮（縮的是清單）", () => {
    const css = stripCssComments(readFile(SRC_DIR, "styles/log-dock.css"));
    const rule = /\.log-dock-icon\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toMatch(/flex-shrink:\s*0/);
  });
});
