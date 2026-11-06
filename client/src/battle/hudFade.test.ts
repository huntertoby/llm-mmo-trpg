import { describe, expect, it } from "vitest";
import type { ClientRect } from "./stageLayout";
import { FADE_BLOCKS, fadeCells, fadedHudBlocks, tileClientRect } from "./hudFade";
import { stagePixels, topReserve } from "./elevation";
import { TILE_SIZE } from "./geometry";

const flat = { width: 10, height: 8, tiles: Array.from({ length: 80 }, () => ({ height: 0 })) };
const rect = (left: number, top: number, width: number, height: number): ClientRect => ({ left, top, width, height });
const noMarks = { moves: [], attacks: [], directions: [], vaults: [] };

describe("tileClientRect", () => {
  it("依畫布實際大小換算（含上方預留）", () => {
    const px = stagePixels(flat);
    const canvas = rect(100, 50, px.width / 2, px.height / 2); // 0.5 倍
    const r = tileClientRect({ x: 2, y: 3 }, flat, canvas);
    expect(r.width).toBeCloseTo(TILE_SIZE / 2);
    expect(r.left).toBeCloseTo(100 + 2 * TILE_SIZE * 0.5);
    expect(r.top).toBeCloseTo(50 + (topReserve(flat) + 3 * TILE_SIZE) * 0.5);
  });
});

describe("fadeCells", () => {
  it("單位與可點的格子，去重排序", () => {
    const cells = fadeCells(
      { units: [{ x: 3, y: 1 }, { x: 0, y: 0 }] as never },
      { moves: [{ x: 3, y: 1 }, { x: 1, y: 2 }], attacks: [{ x: 5, y: 5 }], directions: [{ pos: { x: 4, y: 0 }, arrow: "→" }], vaults: [{ pos: { x: 6, y: 6 }, kind: "jump" }] },
    );
    expect(cells).toEqual([
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 3, y: 1 },
      { x: 1, y: 2 },
      { x: 5, y: 5 },
      { x: 6, y: 6 },
    ]);
  });
  it("沒有單位也沒有可點格子為空", () => {
    expect(fadeCells({ units: [] }, noMarks)).toEqual([]);
  });
});

describe("fadedHudBlocks", () => {
  const blocks = { hero: rect(8, 8, 250, 100), corner: rect(560, 8, 230, 90), log: rect(8, 300, 200, 80), order: null };
  it("單位在 HUD 塊底下：那一塊變半透明", () => {
    expect(fadedHudBlocks(blocks, [rect(40, 60, 30, 30)])).toEqual(["hero"]);
  });
  it("可點的格子在底下（含半格緩衝）也算", () => {
    // 格子在戰況框左邊 10px：半格（15px）緩衝內
    expect(fadedHudBlocks(blocks, [rect(520, 40, 30, 30)])).toEqual(["corner"]);
  });
  it("都沒有：不變半透明", () => {
    expect(fadedHudBlocks(blocks, [])).toEqual([]);
    expect(fadedHudBlocks(blocks, [rect(350, 200, 30, 30)])).toEqual([]);
  });
  it("多塊依固定順序、量不到的塊不算", () => {
    const cells = [rect(100, 320, 30, 30), rect(600, 20, 30, 30), rect(10, 10, 30, 30)];
    expect(fadedHudBlocks(blocks, cells)).toEqual(["hero", "corner", "log"]);
    expect(fadedHudBlocks({ hero: rect(0, 0, 0, 0) }, [rect(0, 0, 30, 30)])).toEqual([]);
    expect(FADE_BLOCKS).toContain("log");
  });
});

// 6C-8（docs/archive/art/6A-4g與6C-5與6M-4與6C-7檢查.md 第 1 節待決 1）：上方行動順序列也鋪滿、套同一條半透明規則；底部列保留高度、不變淡。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const hudCss = readFileSync("src/styles/battle-hud.css", "utf-8");

describe("6C-8：上方行動順序列鋪滿並套半透明規則", () => {
  const scrollRule = /\.battle-screen\.hud-a \.board-scroll \{([^}]*)\}/.exec(hudCss)?.[1] ?? "";

  it("地圖從畫面最上面開始（不再扣掉行動順序列），底部照舊扣掉底部列的高度", () => {
    expect(scrollRule).toMatch(/inset:\s*0 0 calc\(var\(--hud-bottom, 160px\) \+ var\(--hud-gap\)\) 0;/);
    expect(scrollRule).not.toContain("--hud-top");
  });
  it("行動順序列底下有單位：那一塊變半透明（0.38），沒有就不變", () => {
    const blocks = { order: rect(300, 8, 220, 40), hero: rect(8, 8, 250, 100) };
    expect(fadedHudBlocks(blocks, [rect(400, 20, 30, 30)])).toEqual(["order"]);
    expect(fadedHudBlocks(blocks, [rect(400, 120, 30, 30)])).toEqual([]);
    expect(hudCss).toMatch(/\[data-hud-faded~="order"\] \.bhud-top \.turn-bar,[\s\S]*?opacity: 0\.38;/);
  });
  it("底部列（技能列、回合操作）不在變淡的塊裡", () => {
    expect(FADE_BLOCKS).toContain("order");
    expect(FADE_BLOCKS.some((id) => /bottom|skill|turn/.test(id))).toBe(false);
  });
});
