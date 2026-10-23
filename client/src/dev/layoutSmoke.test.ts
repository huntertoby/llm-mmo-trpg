// 排版煙霧檢查的純函式（Phase 3-47）：用假的量測結果確認「好的版面全 PASS、每種壞法各自 FAIL」。
import { describe, expect, it } from "vitest";
import { alphaOf, evaluate, formatTable, type LayoutSnapshot } from "./layoutSmoke";

const bx = (left: number, top: number, right: number, bottom: number) => ({ left, top, right, bottom });

/** 1600×900 預設版面的實測數值（2026-10-24，main 上量到的）。 */
const good = (): LayoutSnapshot => ({
  viewport: { width: 1600, height: 900 },
  turnControls: bx(1342, 740, 1592, 894),
  endTurn: bx(1342, 784, 1592, 832),
  speed: bx(1342, 871, 1592, 894),
  speedButtons: [1342, 1380, 1418, 1456, 1494, 1532].map((l) => bx(l, 871, l + 36, 894)),
  board: bx(8, 52, 1286, 722),
  bottomHandle: bx(8, 714, 1286, 722),
  sideHandle: bx(1278, 52, 1286, 722),
  hero: bx(8, 728, 308, 894),
  heroHandle: bx(307, 728, 315, 894),
  tileCard: { float: bx(643, 344, 900, 480), bar: bx(643, 450, 900, 480), barAlpha: 0.96 },
  moreMenu: { open: true, tooltips: 0, hintBefore: 1 },
  hintWrappers: 0,
});

const failedIds = (s: LayoutSnapshot): string[] => evaluate(s).filter((r) => !r.pass).map((r) => r.id);

describe("排版煙霧檢查 evaluate", () => {
  it("好的版面全 PASS", () => {
    expect(failedIds(good())).toEqual([]);
  });

  it("結束回合變直條（寬度不到右欄 90%）→ FAIL", () => {
    const s = { ...good(), endTurn: bx(1342, 784, 1400, 832) };
    expect(failedIds(s)).toEqual(["end-turn-wide"]);
  });

  it("播放列被擠出畫面或折成兩行 → FAIL", () => {
    expect(failedIds({ ...good(), speed: bx(1342, 890, 1592, 913) })).toEqual(["speed-visible"]);
    // 容器在畫面內，但最後一顆按鈕超出播放列／視窗右緣
    expect(failedIds({ ...good(), speedButtons: [bx(1342, 871, 1378, 894), bx(1560, 871, 1620, 894)] })).toEqual(["speed-visible"]);
    const wrapped ={ ...good(), speedButtons: [bx(1342, 871, 1378, 894), bx(1380, 880, 1416, 894)] };
    expect(failedIds(wrapped)).toEqual(["speed-one-row"]);
  });

  it("拖曳線跑位（不貼齊戰場邊緣）→ FAIL", () => {
    expect(failedIds({ ...good(), bottomHandle: bx(8, 380, 1286, 388) })).toEqual(["bottom-handle"]);
    expect(failedIds({ ...good(), sideHandle: bx(600, 52, 608, 722) })).toEqual(["side-handle"]);
    expect(failedIds({ ...good(), heroHandle: bx(307, 300, 315, 466) })).toEqual(["hero-handle"]);
  });

  it("格子資訊卡的提示列跑出卡片或沒有底色 → FAIL", () => {
    const out = { ...good(), tileCard: { float: bx(643, 344, 900, 450), bar: bx(643, 450, 900, 480), barAlpha: 0.96 } };
    expect(failedIds(out)).toEqual(["tile-hint"]);
    const clear = { ...good(), tileCard: { float: bx(643, 344, 900, 480), bar: bx(643, 450, 900, 480), barAlpha: 0 } };
    expect(failedIds(clear)).toEqual(["tile-hint"]);
  });

  it("選單開著卻有說明卡、或說明卡外包元素 → FAIL", () => {
    expect(failedIds({ ...good(), moreMenu: { open: true, tooltips: 1, hintBefore: 1 } })).toEqual(["more-menu"]);
    // 滑過時說明卡根本沒出現：這項檢查沒有意義，不算通過
    expect(failedIds({ ...good(), moreMenu: { open: true, tooltips: 0, hintBefore: 0 } })).toEqual(["more-menu"]);
    expect(failedIds({ ...good(), hintWrappers: 40 })).toEqual(["no-hint-wrapper"]);
  });

  it("窄螢幕不顯示拖曳線：沒有才 PASS，出現反而 FAIL", () => {
    const narrow: LayoutSnapshot = { ...good(), viewport: { width: 800, height: 600 }, speed: bx(572, 540, 792, 563), speedButtons: [572, 610, 648, 686, 724, 756].map((l) => bx(l, 540, l + 34, 563)), tileCard: { float: bx(108, 189, 378, 296), bar: bx(108, 270, 378, 296), barAlpha: 0.96 }, bottomHandle: null, sideHandle: null, heroHandle: null };
    expect(failedIds(narrow)).toEqual([]);
    expect(failedIds({ ...narrow, sideHandle: bx(1, 1, 9, 9) })).toEqual(["side-handle"]);
  });

  it("量不到元件時 FAIL，不當作通過", () => {
    const s: LayoutSnapshot = { ...good(), endTurn: null, tileCard: null, moreMenu: null };
    expect(failedIds(s)).toEqual(["end-turn-wide", "tile-hint", "more-menu"]);
  });
});

describe("輸出表與顏色", () => {
  it("表頭寫出 PASS／FAIL 數", () => {
    const ok = formatTable("1600×900", evaluate(good()));
    expect(ok.failed).toBe(0);
    expect(ok.text.split("\n")[0]).toBe("== 1600×900：全 PASS ==");
    const bad = formatTable("x", evaluate({ ...good(), hintWrappers: 3 }));
    expect(bad.failed).toBe(1);
    expect(bad.text).toContain("FAIL  說明卡不外包元素");
  });

  it("背景色不透明度", () => {
    expect(alphaOf("rgb(28, 28, 38)")).toBe(1);
    expect(alphaOf("rgba(28, 28, 38, 0.96)")).toBeCloseTo(0.96);
    expect(alphaOf("rgb(28 28 38 / 96%)")).toBeCloseTo(0.96);
    expect(alphaOf("rgba(0, 0, 0, 0)")).toBe(0);
    expect(alphaOf("transparent")).toBe(0);
  });
});
