// Phase RT-6：主城 HUD 小修（6F-20 待決 3、RT-5d 檢查第 3 節）。
// 1. 窄視窗收合的任務鈕貼在錢包下方（不懸在地圖中段蓋到房子）；其他寬度不變。
// 2. 功能列說明卡開著時，說明列讓位（CSS `body:has(.float-card .hud-bar-card)`）。
// 3. 說明列也避開碑前木橋（浮橋每一格當裝飾物）。
// 另外測 `dev/townSmoke.ts` 的純函式 `evaluateTown`。
// RT-6b（RT-6 檢查的四題決定）：夾邊「！」上緣分欄、「！」旁的箭頭與半格避讓、說明列只在真的重疊時讓位、寬視窗收合的任務鈕。
import { describe, expect, it } from "vitest";
import { evaluateTown, type TownSnapshot } from "../dev/townSmoke";
import { HUD_BLOCKS, hudInsets, hudLayout, TRACKER_TUCK_TOP, type Rect } from "./hud";
import { bridgeCellRect, captionShiftDecor, hudColumnRects, rectsOverlap, unitRect } from "./hudAvoid";
import { edgeToward, guideAlertBox, guideAnchor, guideBubbleBox, guideTopLimit, padBox } from "./opening";
import { FieldHeads } from "./FieldHeads";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

const bottom = (r: Rect): number => r.top + r.height;
const right = (r: Rect): number => r.left + r.width;
const hits = (a: Rect, b: Rect): boolean => a.left < right(b) && b.left < right(a) && a.top < bottom(b) && b.top < bottom(a);

/** 主城 800×600 的 HUD 舞台（開發頁量到的 768×532；正式頁 768×540 也測）。 */
const NARROW_STAGES = [
  { width: 768, height: 532 },
  { width: 768, height: 540 },
  { width: 800, height: 520 },
];

describe("RT-6 第 1 項：窄視窗收合的任務鈕貼在錢包下方", () => {
  for (const st of NARROW_STAGES) {
    it(`${st.width}×${st.height}：緊貼錢包下方 6、右緣對齊、不碰其他塊`, () => {
      const l = hudLayout(st.width, st.height, { mates: 2, narrow: true, collapsed: true });
      const { tracker, wallet } = l.blocks;
      expect(tracker.top).toBeCloseTo(TRACKER_TUCK_TOP * l.scale, 6);
      expect(tracker.top - bottom(wallet)).toBeCloseTo(6 * l.scale, 6);
      expect(right(tracker)).toBeCloseTo(right(wallet), 6);
      // 在右欄的範圍內（不往地圖中間伸）
      expect(tracker.left).toBeGreaterThanOrEqual(wallet.left);
      // 和其他塊都不重疊
      for (const id of HUD_BLOCKS) if (id !== "tracker" && l.blocks[id].height > 0) expect(hits(tracker, l.blocks[id]), id).toBe(false);
      // 舊位置（地圖中段，6f19_float_800_pinned 壓到房子的地方）在下面很遠
      expect(bottom(tracker)).toBeLessThan(st.height * 0.5);
    });
  }

  it("RT-6b：寬視窗手動收合也貼錢包下方（寬窄一致）", () => {
    for (const [w, h] of [
      [1568, 832],
      [1024, 556],
    ] as const) {
      const l = hudLayout(w, h, { mates: 2, narrow: false, collapsed: true });
      const { tracker, wallet } = l.blocks;
      expect(tracker.top / l.scale).toBeCloseTo(TRACKER_TUCK_TOP, 6);
      expect(tracker.top - bottom(wallet)).toBeCloseTo(6 * l.scale, 6);
      expect(right(tracker)).toBeCloseTo(right(wallet), 6);
      for (const id of HUD_BLOCKS) if (id !== "tracker" && l.blocks[id].height > 0) expect(hits(tracker, l.blocks[id]), id).toBe(false);
      // 鏡頭的安全區不變（任務鈕在右欄裡面）
      expect(hudInsets(l, { width: w, height: h })).toEqual(hudInsets(hudLayout(w, h, { mates: 2, narrow: false, collapsed: false }), { width: w, height: h }));
    }
  });

  it("展開的任務欄照舊（窄、寬都一樣）", () => {
    for (const narrow of [true, false]) {
      const l = hudLayout(768, 532, { mates: 2, narrow, collapsed: false });
      const H = 532 / l.scale;
      expect(l.blocks.tracker.top / l.scale).toBeCloseTo(Math.max(214, Math.min(H * 0.55, H - 56 - 14 - 150 - 8)), 6);
    }
  });
});

describe("RT-6 第 2 項（RT-6b 改）：說明列只在和功能列說明卡真的重疊時讓位", () => {
  const css = readFileSync("src/styles/world-hud.css", "utf-8");
  const field = readFileSync("src/world/WorldField.tsx", "utf-8");
  it("CSS：不再用 body:has 一律隱藏；`.yield` 才隱藏、不接滑鼠", () => {
    expect(css).not.toMatch(/body:has\(\.float-card \.hud-bar-card\)/);
    const rule = /\.world-field\.hud \.world-field-bar\.yield \{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toContain("opacity: 0");
    expect(rule).toContain("pointer-events: none");
  });
  it("WorldField 量功能列說明卡與說明列的矩形，重疊才加 `.yield`", () => {
    expect(field).toContain("MutationObserver");
    expect(field).toContain('.hud-bar-card');
    expect(field).toMatch(/rectsOverlap\(c\.getBoundingClientRect\(\), cap\)/);
    expect(field).toContain('capYield ? " yield" : ""');
  });
  it("說明列沒有 opacity 的轉場（量測與畫面一致，說明卡一出現就讓位）", () => {
    const base = /\.world-field\.hud \.world-field-bar \{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(base).toContain("transition: transform");
    expect(base).not.toContain("opacity");
  });
  it("rectsOverlap：重疊才算；邊碰邊、空矩形不算", () => {
    const box = (l: number, t: number, w: number, h: number) => ({ left: l, top: t, right: l + w, bottom: t + h });
    // 1600 寬站傳送石：說明列（含「傳送」）在中間，最右邊「潛行」的說明卡在右邊，不重疊
    const cap = box(560, 724, 450, 24);
    expect(rectsOverlap(box(1020, 610, 250, 120), cap)).toBe(false);
    expect(rectsOverlap(box(1010, 610, 250, 120), cap)).toBe(false); // 邊碰邊
    expect(rectsOverlap(box(900, 610, 250, 120), cap)).toBe(true);
    expect(rectsOverlap(box(900, 610, 0, 0), cap)).toBe(false);
  });
});

describe("RT-6 第 3 項：說明列避開碑前木橋", () => {
  it("浮橋一格＝整格", () => {
    const grid = { width: 4, height: 4 };
    const r = bridgeCellRect(grid, { x: 2, y: 3 }, 1);
    expect(r.width).toBe(48);
    expect(r.height).toBe(48);
    expect(r.left).toBe(96);
  });

  // rt5d_3_caption_1600 的實測（舞台座標）：說明列 [649,724,919,745]，碑前兩格木橋 [720,716,912,764]（舞台＝畫面 −(16,60)）
  const cap = { left: 649, top: 724, width: 270, height: 21 };
  const bridge = [
    { left: 720, top: 716, width: 48, height: 48 },
    { left: 768, top: 716, width: 48, height: 48 },
  ];
  const hud = [
    { left: 1347, top: 458, width: 212, height: 95 }, // 任務欄
    { left: 551, top: 755, width: 468, height: 70 }, // 功能列
  ];

  it("壓到木橋時水平挪開，挪過去不壓木橋也不壓 HUD", () => {
    const dx = captionShiftDecor(cap, [], bridge, hud, 1568);
    expect(dx).not.toBe(0);
    const moved = { ...cap, left: cap.left + dx };
    for (const b of bridge) expect(hits(moved, b)).toBe(false);
    for (const h of hud.filter((x) => !hits(x, cap))) expect(hits(moved, h)).toBe(false);
    expect(dx).toBe(816 + 6 - 649); // 貼著木橋右邊（實機 data-shift=173）
  });

  it("沒壓到木橋不挪", () => {
    expect(captionShiftDecor({ ...cap, left: 300 }, [], bridge, hud, 1568)).toBe(0);
  });
});

describe("RT-6：townSmoke.evaluateTown", () => {
  const good = (): TownSnapshot => ({
    viewport: { width: 800, height: 600 },
    stage: { left: 16, top: 60, width: 768, height: 532 },
    blocks: {
      hero: { left: 22, top: 66, width: 185, height: 55 },
      mates: { left: 22, top: 133, width: 71, height: 56 },
      shadow: { left: 22, top: 195, width: 27, height: 27 },
      place: { left: 652, top: 66, width: 126, height: 18 },
      minimap: { left: 652, top: 87, width: 126, height: 77 },
      clock: { left: 652, top: 166, width: 126, height: 22 },
      wallet: { left: 652, top: 191, width: 126, height: 18 },
      tracker: { left: 751.5, top: 213.5, width: 26.6, height: 26.6 },
      bar: { left: 265, top: 546, width: 270, height: 41 },
      toasts: { left: 23, top: 553, width: 170, height: 18 },
    },
    scale: 0.7385,
    narrow: true,
    trackerCollapsed: true,
    caption: { left: 265, top: 519, width: 270, height: 21 },
    barCards: [{ name: "btn-skills", card: { left: 200, top: 436, width: 252, height: 114 }, captionOpacity: 0 }],
    captionOpacityAfter: 1,
  });

  it("好的版面全 PASS", () => {
    const rows = evaluateTown(good());
    expect(rows.filter((r) => !r.pass)).toEqual([]);
  });

  it("說明卡開著、說明列還看得到又被蓋：FAIL", () => {
    const s = good();
    s.barCards = [{ name: "btn-skills", card: { left: 200, top: 436, width: 252, height: 114 }, captionOpacity: 1 }];
    expect(evaluateTown(s).find((r) => r.id === "town/caption-card")?.pass).toBe(false);
  });

  it("說明卡關了說明列沒回來：FAIL", () => {
    const s = good();
    s.captionOpacityAfter = 0;
    expect(evaluateTown(s).find((r) => r.id === "town/caption-back")?.pass).toBe(false);
  });

  it("收合的任務鈕懸在地圖中段（舊位置）：FAIL", () => {
    const s = good();
    s.blocks.tracker = { left: 751.5, top: 348, width: 26.6, height: 26.6 };
    expect(evaluateTown(s).find((r) => r.id === "town/tracker-tuck")?.pass).toBe(false);
  });

  it("RT-6b：寬視窗收合的任務鈕懸在地圖中段也 FAIL；展開時不檢查", () => {
    const s = good();
    s.narrow = false;
    s.blocks.tracker = { left: 751.5, top: 348, width: 26.6, height: 26.6 };
    expect(evaluateTown(s).find((r) => r.id === "town/tracker-tuck")?.pass).toBe(false);
    s.trackerCollapsed = false;
    expect(evaluateTown(s).find((r) => r.id === "town/tracker-tuck")?.pass).toBe(true);
  });

  it("RT-6b：說明卡沒重疊、說明列卻隱藏：FAIL；沒重疊照常顯示：PASS", () => {
    const s = good();
    s.barCards = [{ name: "btn-sneak", card: { left: 560, top: 436, width: 200, height: 76 }, captionOpacity: 0 }];
    expect(evaluateTown(s).find((r) => r.id === "town/caption-card")?.pass).toBe(false);
    s.barCards = [{ name: "btn-sneak", card: { left: 560, top: 436, width: 200, height: 76 }, captionOpacity: 1 }];
    expect(evaluateTown(s).find((r) => r.id === "town/caption-card")?.pass).toBe(true);
  });
});

describe("RT-6b 決定 1：夾邊「！」的上緣只在左欄、右欄的水平範圍內避開它們", () => {
  // 1600×900 的舞台（1568×832），鏡頭在畫布原點：畫布座標＝舞台座標
  const W = 1568;
  const H = 832;
  const l = hudLayout(W, H, { mates: 2, narrow: false, collapsed: false });
  const ins = hudInsets(l, { width: W, height: H });
  const safe = { left: ins.left, top: ins.top, right: W - ins.right, bottom: H - ins.bottom };
  const visible = { left: 8, top: 8, right: W - 8, bottom: H - 8 };
  const columns = hudColumnRects(l);
  const mapTop = 8;
  /** x＝120 的「！」（96～144）連同往右的泡泡（144～354）水平重疊到的左欄塊：主角卡、隊友卡（影子鈕在 8～44，不算）。 */
  const leftColBottom = Math.max(...columns.filter((c) => c.left < 354 && right(c) > 96).map((c) => bottom(c)));

  it("畫面中間：夾在地圖可見範圍上緣往下一個「！」的高度（不是隊友卡的下緣）", () => {
    const a = guideAnchor({ left: 760, top: -60 }, safe, visible, { columns, mapTop, bubble: true });
    expect(a.edge).toBe("n");
    expect(guideAlertBox(a).top).toBe(mapTop);
    expect(a.top).toBeLessThan(safe.top); // 舊規則會停在左欄下緣（約 226）
    // 「！」與泡泡都不壓到任何 HUD 塊
    for (const c of columns) {
      expect(hits(guideAlertBox(a), c)).toBe(false);
      expect(hits(guideBubbleBox(a, a.side), c)).toBe(false);
    }
  });

  it("在左欄的水平範圍內（含泡泡）：停在左欄的下緣", () => {
    const a = guideAnchor({ left: 120, top: -60 }, safe, visible, { columns, mapTop, bubble: true });
    expect(a.edge).toBe("n");
    expect(guideAlertBox(a).top).toBe(leftColBottom);
    expect(leftColBottom).toBeCloseTo(bottom(l.blocks.mates), 6);
    expect(guideTopLimit(120, safe, { columns, mapTop }, "e")).toBe(leftColBottom);
    for (const c of columns) expect(hits(guideAlertBox(a), c)).toBe(false);
  });

  it("收起來（只剩「！」）時只看「！」本身的寬度", () => {
    const x = l.blocks.hero.left + l.blocks.hero.width + 40;
    expect(guideTopLimit(x, safe, { columns, mapTop, bubble: false })).toBe(mapTop);
    expect(guideTopLimit(x, safe, { columns, mapTop, bubble: true }, "e")).toBe(mapTop);
    expect(guideTopLimit(x, safe, { columns, mapTop, bubble: true }, "w")).toBeGreaterThan(mapTop); // 往左的泡泡伸進左欄
  });

  it("沒有 columns 照 RT-5 舊規則（整條上緣用安全區）", () => {
    const a = guideAnchor({ left: 760, top: -60 }, safe, visible);
    expect(guideAlertBox(a).top).toBe(safe.top);
  });
});

describe("RT-6b 決定 2：夾邊「！」旁的箭頭，與每個單位保持至少半格", () => {
  const grid = { width: 40, height: 20, tiles: [] } as never;
  const box = { left: 0, top: 0, right: 1568, bottom: 760 };
  const visible = { left: 8, top: 8, right: 1560, bottom: 824 };
  const opts = { columns: [], mapTop: 8, bubble: true };

  it("「！」夾在上緣中間、正下方站著人（朝向三角形）：沿邊挪開，「！」和那人至少隔半格；上緣照新規則", () => {
    const plain = guideAnchor({ left: 696, top: -60 }, box, visible, opts);
    // 找一個人讓「！」落在他的半格內（Q 版的頭頂、腳下）
    const near = [0, 1, 2]
      .map((y) => unitRect(grid, { x: 14, y }, 1))
      .find((u) => hits(guideAlertBox(plain), padBox(u, 24)));
    expect(near).toBeDefined();
    const units = [near as Rect];
    const a = guideAnchor({ left: 696, top: -60 }, box, visible, { ...opts, units, pad: 24 });
    // 箭頭指向說話的人真正的方向（挪開之後從「！」看過去）
    expect(a.edge).toBe(edgeToward(a, { left: 696, top: -60 }, "n", ""));
    expect(a.edge).toMatch(/^n/);
    expect(a.top).toBe(plain.top);
    expect(a.left).not.toBe(plain.left);
    expect(hits(guideAlertBox(a), padBox(near as Rect, 24))).toBe(false);
    expect(hits(guideBubbleBox(a, a.side), near as Rect)).toBe(false);
    // 確定性
    expect(guideAnchor({ left: 696, top: -60 }, box, visible, { ...opts, units, pad: 24 })).toEqual(a);
  });

  it("edgeToward：保留夾住的邊，沿邊挪開超過一格才加斜向", () => {
    const o = { left: 100, top: 100 };
    expect(edgeToward(o, { left: 120, top: 0 }, "n", "")).toBe("n");
    expect(edgeToward(o, { left: 300, top: 90 }, "n", "")).toBe("ne"); // 人在右上方（只高一點也算上方：夾的是上緣）
    expect(edgeToward(o, { left: -100, top: 90 }, "n", "")).toBe("nw");
    expect(edgeToward(o, { left: 300, top: 300 }, "", "e")).toBe("se");
    expect(edgeToward(o, { left: 300, top: 120 }, "", "e")).toBe("e");
    expect(edgeToward(o, { left: 300, top: 0 }, "n", "e")).toBe("ne");
  });

  it("挪的時候每個位置重算上緣（挪進左欄的範圍就停在左欄下緣）", () => {
    const col = { left: 0, top: 0, width: 260, height: 200 };
    const blocker = { left: 120, top: 0, width: 600, height: 60 }; // 擋住中間一大段
    const a = guideAnchor({ left: 300, top: -60 }, box, visible, { columns: [col], mapTop: 8, bubble: false, units: [blocker], pad: 24 });
    expect(hits(guideAlertBox(a), padBox(blocker, 24))).toBe(false);
    if (guideAlertBox(a).left < col.left + col.width) expect(guideAlertBox(a).top).toBeGreaterThanOrEqual(200);
    else expect(guideAlertBox(a).top).toBe(8);
  });

  it("FieldHeads：夾邊時「！」旁一律有箭頭（展開、收起來都是），泡泡名字旁沒有", () => {
    const base = { key: "fig:keeper", id: "keeper", kind: "figure" as const, name: "守印人", pos: { x: 14, y: 0 }, alert: "quest" as const, alertZh: "開場", rank: null, rankZh: "", main: true };
    const safe = { left: 200, top: 400, right: 1400, bottom: 700 };
    for (const folded of [false, true]) {
      const marks = [{ ...base, bubble: folded ? null : "站上傳送陣。", folded }];
      const html = renderToStaticMarkup(createElement(FieldHeads, { marks: marks as never, grid, scale: 1, onPick: () => undefined, view: safe, visible: safe, people: [{ x: 14, y: 0 }], columns: [], mapTop: 400 }));
      const icons = /<button[^>]*field-head-icons[\s\S]*?<\/button>/.exec(html)?.[0] ?? "";
      expect(icons).toContain('data-testid="field-edge-arrow"');
      expect(icons).toContain('data-dir="n"');
      const name = /<b class="field-bubble-name">([\s\S]*?)<\/b>/.exec(html)?.[1] ?? "";
      expect(name).not.toContain("svg");
      expect(html.match(/field-edge-arrow/g)?.length).toBe(1);
    }
  });

  it("在畫面裡（沒夾邊）不畫箭頭", () => {
    const base = { key: "fig:keeper", id: "keeper", kind: "figure" as const, name: "守印人", pos: { x: 14, y: 8 }, alert: "quest" as const, alertZh: "開場", rank: null, rankZh: "", main: true };
    const all = { left: 0, top: 0, right: 2000, bottom: 2000 };
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks: [{ ...base, bubble: "站上傳送陣。", folded: false }] as never, grid, scale: 1, onPick: () => undefined, view: all, visible: all, people: [], columns: [], mapTop: 0 }));
    expect(html).not.toContain("field-edge-arrow");
  });
});
