// Phase RT-6：主城 HUD 小修（6F-20 待決 3、RT-5d 檢查第 3 節）。
// 1. 窄視窗收合的任務鈕貼在錢包下方（不懸在地圖中段蓋到房子）；其他寬度不變。
// 2. 功能列說明卡開著時，說明列讓位（CSS `body:has(.float-card .hud-bar-card)`）。
// 3. 說明列也避開碑前木橋（浮橋每一格當裝飾物）。
// 另外測 `dev/townSmoke.ts` 的純函式 `evaluateTown`。
import { describe, expect, it } from "vitest";
import { evaluateTown, type TownSnapshot } from "../dev/townSmoke";
import { HUD_BLOCKS, hudLayout, TRACKER_TUCK_TOP, type Rect } from "./hud";
import { bridgeCellRect, captionShiftDecor } from "./hudAvoid";

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

  it("寬視窗手動收合：位置照舊（其他寬度不變）", () => {
    for (const [w, h] of [
      [1568, 832],
      [1024, 556],
    ] as const) {
      const l = hudLayout(w, h, { mates: 2, narrow: false, collapsed: true });
      const H = h / l.scale;
      const old = Math.max(214, Math.min(H * 0.55, H - 56 - 14 - 36 - 8));
      expect(l.blocks.tracker.top / l.scale).toBeCloseTo(old, 6);
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

describe("RT-6 第 2 項：功能列說明卡開著時說明列讓位", () => {
  const css = readFileSync("src/styles/world-hud.css", "utf-8");
  it("CSS：說明卡在畫面上時說明列隱藏、不接滑鼠", () => {
    const rule = /body:has\(\.float-card \.hud-bar-card\) \.world-field\.hud \.world-field-bar \{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toContain("opacity: 0");
    expect(rule).toContain("pointer-events: none");
  });
  it("說明列沒有 opacity 的轉場（量測與畫面一致，說明卡一出現就讓位）", () => {
    const base = /\.world-field\.hud \.world-field-bar \{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(base).toContain("transition: transform");
    expect(base).not.toContain("opacity");
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

  it("寬視窗不檢查任務鈕位置", () => {
    const s = good();
    s.narrow = false;
    s.blocks.tracker = { left: 751.5, top: 348, width: 26.6, height: 26.6 };
    expect(evaluateTown(s).find((r) => r.id === "town/tracker-tuck")?.pass).toBe(true);
  });
});
