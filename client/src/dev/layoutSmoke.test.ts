// 排版煙霧檢查的純函式（Phase 3-47）：用假的量測結果確認「好的版面全 PASS、每種壞法各自 FAIL」。
import { describe, expect, it } from "vitest";
import { alphaOf, evaluate, formatTable, ICON_CANVAS_SELECTOR, iconScaleProblem, iconScaleRows, mapCoverIssues, type IconBox, type LayoutSnapshot } from "./layoutSmoke";

const bx = (left: number, top: number, right: number, bottom: number) => ({ left, top, right, bottom });

/** 1600×900 預設版面的實測數值（2026-10-24 main 上量到的；6A-4e 起沒有拖曳線、多量 HUD 各塊）。 */
const good = (): LayoutSnapshot => ({
  viewport: { width: 1600, height: 900 },
  turnControls: bx(1342, 740, 1592, 894),
  endTurn: bx(1342, 784, 1592, 832),
  speed: bx(1342, 871, 1592, 894),
  speedButtons: [1342, 1380, 1418, 1456, 1494, 1532].map((l) => bx(l, 871, l + 36, 894)),
  board: bx(8, 52, 1286, 722),
  tileCard: { float: bx(643, 344, 900, 480), bar: bx(643, 450, 900, 480), barAlpha: 0.96 },
  moreMenu: { open: true, tooltips: 0, hintBefore: 1 },
  hintWrappers: 0,
  floatCards: [{ name: "float-card.skill-card-float「刺擊」", alpha: 1 }],
  textIssues: [],
  hud: {
    hero: bx(8, 8, 260, 112),
    order: bx(680, 8, 920, 46),
    status: bx(1368, 8, 1592, 52),
    tools: bx(1368, 56, 1592, 92),
    skills: bx(480, 746, 1334, 892),
    turn: bx(1342, 740, 1592, 894),
    log: bx(8, 690, 38, 720),
  },
  // 6F-8 讓開安全區後 1600×900 的實測：地圖 508～1120、上緣 68
  mapCover: {
    canvas: bx(508, 68, 1120, 716),
    blocks: { hero: bx(8, 8, 260, 130), order: bx(695, 8, 933, 52), corner: bx(1368, 8, 1592, 105), telegraph: bx(1368, 111, 1592, 179), log: bx(8, 618, 260, 716), zoom: bx(1400, 688, 1592, 716), mode: null },
  },
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

  it("版面 A 的 HUD 塊重疊或出畫面 → FAIL（6A-4e）", () => {
    expect(failedIds({ ...good(), hud: { ...good().hud, order: bx(200, 8, 520, 46) } })).toEqual(["hud-blocks"]);
    expect(failedIds({ ...good(), hud: { ...good().hud, turn: bx(1342, 740, 1620, 894) } })).toEqual(["hud-blocks"]);
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

  it("浮動卡沒有底色、文字溢出或重疊 → FAIL（3U-1）", () => {
    const clear = { ...good(), floatCards: [{ name: "float-card.race-pick-card「人類」", alpha: 0 }] };
    expect(failedIds(clear)).toEqual(["float-card-bg"]);
    expect(failedIds({ ...good(), textIssues: ["溢出 span.run-alloc-name「敏捷 ★建議」"] })).toEqual(["no-text-clash"]);
  });

  it("800×600：HUD 塊收窄後也全 PASS", () => {
    const hud = {
      hero: bx(8, 8, 238, 112),
      order: bx(300, 8, 520, 46),
      status: bx(582, 8, 792, 52),
      tools: bx(582, 56, 792, 92),
      skills: bx(8, 448, 564, 592),
      turn: bx(572, 432, 792, 592),
      log: bx(8, 390, 38, 418),
    };
    const narrow: LayoutSnapshot = { ...good(), viewport: { width: 800, height: 600 }, turnControls: bx(572, 432, 792, 592), endTurn: bx(572, 480, 792, 520), speed: bx(572, 569, 792, 592), speedButtons: [572, 610, 648, 686, 724, 756].map((l) => bx(l, 569, l + 34, 592)), tileCard: { float: bx(108, 189, 378, 296), bar: bx(108, 270, 378, 296), barAlpha: 0.96 }, hud };
    expect(failedIds(narrow)).toEqual([]);
  });

  it("量不到元件時 FAIL，不當作通過", () => {
    const s: LayoutSnapshot = { ...good(), endTurn: null, tileCard: null, moreMenu: null };
    expect(failedIds(s)).toEqual(["end-turn-wide", "tile-hint", "more-menu"]);
  });

  it("6F-8：地圖被 HUD 蓋到 → FAIL（RT-3b 時 800 寬的實測：戰況框、行動順序列都蓋到地圖）", () => {
    const rt3b: LayoutSnapshot = {
      ...good(),
      mapCover: { canvas: bx(340, 8, 707, 397), blocks: { hero: bx(8, 8, 238, 156), order: bx(291, 8, 529, 52), corner: bx(582, 8, 792, 105), log: bx(8, 299, 238, 397), zoom: bx(606, 369, 792, 397) } },
    };
    expect(failedIds(rt3b)).toEqual(["map-clear"]);
    const row = evaluate(rt3b).find((r) => r.id === "map-clear");
    expect(row?.detail).toMatch(/order 189×44；corner 125×97；zoom 101×28/);
    // 6F-8 讓開後的 800 寬實測：都在外面
    const f8: LayoutSnapshot = {
      ...good(),
      mapCover: { canvas: bx(255, 68, 565, 397), blocks: { hero: bx(8, 8, 238, 156), order: bx(291, 8, 529, 52), corner: bx(582, 8, 792, 105), log: bx(8, 299, 238, 397), zoom: bx(606, 369, 792, 397), mode: bx(8, 162, 238, 280) } },
    };
    expect(failedIds(f8)).toEqual([]);
    expect(failedIds({ ...good(), mapCover: { canvas: null, blocks: {} } })).toEqual(["map-clear"]);
  });

  it("6F-8：只差 1px（邊框、子像素）不算蓋到", () => {
    expect(mapCoverIssues(bx(100, 60, 400, 400), { order: bx(150, 8, 300, 61), corner: bx(399, 8, 600, 100) })).toEqual([]);
    expect(mapCoverIssues(bx(100, 60, 400, 400), { order: bx(150, 8, 300, 63) })).toEqual(["order 150×3"]);
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

// QI-2c：圖示畫布檢查擴到技能圖示、部件圓片、卡片小圖；身上裝備格另查左上角對齊裝置像素（T-C4、開發 PM 追加）
describe("圖示畫布（QI-1b／QI-2c）", () => {
  const box = (over: Partial<IconBox> = {}): IconBox => ({ name: "canvas", cssW: 40, cssH: 40, canvasW: 80, canvasH: 80, ...over });

  it("量的是裝備、武器、技能圖示、部件圓片與三種卡片小圖", () => {
    for (const cls of ["gear-icon", "weapon-icon", "skill-icon", "part-tile", "skill-chip-glyph", "skill-effect-glyph", "pin-glyph"]) expect(ICON_CANVAS_SELECTOR).toContain(`canvas.${cls}`);
  });

  it("整數 CSS px 且畫布＝顯示 × 2 才過；小數、被縮放都不過", () => {
    expect(iconScaleProblem(box())).toBeNull();
    expect(iconScaleProblem(box({ cssW: 13, cssH: 13, canvasW: 26, canvasH: 26 }))).toBeNull();
    expect(iconScaleProblem(box({ cssW: 39.5, cssH: 39.5 }))).toContain("不是整數");
    expect(iconScaleProblem(box({ canvasW: 112, canvasH: 112 }))).toContain("被 CSS 縮放");
  });

  it("身上裝備格（snap）：左上角在裝置像素上才過", () => {
    expect(iconScaleProblem(box({ snap: { left: 812, top: 300, dpr: 1 } }))).toBeNull();
    expect(iconScaleProblem(box({ snap: { left: 812.5, top: 300, dpr: 2 } }))).toBeNull();
    expect(iconScaleProblem(box({ snap: { left: 812.5, top: 300, dpr: 1 } }))).toContain("沒對齊裝置像素");
    expect(iconScaleProblem(box({ snap: { left: 812, top: 300.4, dpr: 1.25 } }))).toContain("沒對齊裝置像素");
    const rows = iconScaleRows([box({ snap: { left: 1, top: 1, dpr: 1 } }), box({ name: "canvas skill-icon@x" })]);
    expect(rows[0]?.pass).toBe(true);
    expect(rows[0]?.detail).toContain("身上裝備格 1 個左上角對齊裝置像素");
  });
});
