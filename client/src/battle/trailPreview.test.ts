// E3b（08 8.29 E3 顯示）：走路預覽畫出這次會留下表面的格子（框線，不畫成冰），預覽牌加一行
// 「沿路留下冰 N 格（M 回合後消失）」；表面不是冰時換成那種表面的名字。
import { describe, expect, it } from "vitest";
import { pathDraw, trailCells, trailTag, trailText, TRAIL_COLORS, type PathPreview, type PathStep } from "./pathPreview";
import { drawPathMarks, TRAIL_INSET, type Pen, type StrokeStyle } from "../render/pathArt";

function step(index: number, x: number, y: number): PathStep {
  return { pos: [x, y], index, surface: "none", trap: false, reach: "certain", events: [] };
}

function preview(trail: PathPreview["trail"]): PathPreview {
  const steps = [step(0, 0, 0), step(1, 1, 0), step(2, 2, 0), step(3, 2, 1)];
  return {
    unit_id: "unit_0001",
    path: steps.map((s) => s.pos),
    legal_length: steps.length,
    reachable: true,
    reason: null,
    steps,
    stop: [2, 1],
    worst_stop: [2, 1],
    stops: [[2, 1]],
    stop_certain: true,
    certain: true,
    move_cost: 3,
    slip_runs: [],
    trail,
  };
}

const ICE = preview({ tiles: [[0, 0], [1, 0], [2, 0]], surface: "ice", duration: 1 });
const FIRE = preview({ tiles: [[0, 0], [1, 0]], surface: "fire", duration: 2 });

function recorder(): Pen & { calls: string[]; strokes: StrokeStyle[] } {
  const calls: string[] = [];
  const strokes: StrokeStyle[] = [];
  return {
    calls,
    strokes,
    moveTo: (x, y) => calls.push(`M${Math.round(x)},${Math.round(y)}`),
    lineTo: (x, y) => calls.push(`L${Math.round(x)},${Math.round(y)}`),
    roundRect: (x, y, w, h, r) => calls.push(`R${x},${y},${w},${h},${r}`),
    circle: (x, y, r) => calls.push(`C${x},${y},${r}`),
    closePath: () => calls.push("Z"),
    fill: (s) => calls.push(`F${s.color.toString(16)}`),
    stroke: (s) => {
      strokes.push(s);
      calls.push(`S${s.color.toString(16)}`);
    },
  };
}

const geo = {
  origin: (p: { x: number; y: number }) => ({ x: p.x * 48, y: p.y * 48 }),
  center: (p: { x: number; y: number }) => ({ x: p.x * 48 + 24, y: p.y * 48 + 24 }),
};

describe("E3b 霜行預覽", () => {
  it("預覽牌那一行：冰", () => {
    expect(trailText(ICE.trail!)).toBe("沿路留下冰 3 格（1 回合後消失）");
    expect(trailTag(ICE)).toEqual({ pos: { x: 2, y: 1 }, icon: "ice", text: "沿路留下冰 3 格（1 回合後消失）" });
  });

  it("預覽牌那一行：不是冰時換成那種表面的名字", () => {
    expect(trailText(FIRE.trail!)).toBe("沿路留下火焰 2 格（2 回合後消失）");
    expect(trailTag(FIRE)?.icon).toBe("fire");
  });

  it("沒有霜行時沒有框線、沒有那一行", () => {
    for (const pv of [preview(null), preview(undefined)]) {
      expect(trailTag(pv)).toBeNull();
      expect(trailCells(pv)).toEqual([]);
      expect(pathDraw(pv).trail).toEqual([]);
      expect(pathDraw(pv).tags.some((t) => t.text.startsWith("沿路留下"))).toBe(false);
    }
  });

  it("畫面要畫的：起點與途經的框線、預覽牌放在停點", () => {
    const d = pathDraw(ICE);
    expect(d.trail).toEqual([
      { pos: { x: 0, y: 0 }, surface: "ice" },
      { pos: { x: 1, y: 0 }, surface: "ice" },
      { pos: { x: 2, y: 0 }, surface: "ice" },
    ]);
    expect(d.tags.filter((t) => t.text.startsWith("沿路留下"))).toEqual([trailTag(ICE)]);
  });

  it("框線：內縮的虛線、不填色、顏色依表面（不畫成冰）", () => {
    const g = recorder();
    drawPathMarks(g, { ...pathDraw(ICE), frames: [], bangs: [], slipStops: [], missEnd: null }, geo);
    expect(g.strokes.map((s) => s.color)).toEqual([TRAIL_COLORS.ice, TRAIL_COLORS.ice, TRAIL_COLORS.ice]);
    expect(g.calls.some((c) => c.startsWith("F"))).toBe(false); // 不填色
    expect(g.calls.some((c) => c.startsWith("R"))).toBe(false); // 不是實線圓角框
    // 第一格 (0,0)：虛線從內縮 TRAIL_INSET 的框上開始，一筆裡有多段
    const firstStroke = g.calls.indexOf(`S${(TRAIL_COLORS.ice as number).toString(16)}`);
    const moves = g.calls.slice(0, firstStroke).filter((c) => c.startsWith("M"));
    expect(moves.length).toBeGreaterThan(4);
    for (const m of moves) {
      const [x, y] = m.slice(1).split(",").map(Number) as [number, number];
      expect(x).toBeGreaterThanOrEqual(TRAIL_INSET - 1);
      expect(y).toBeGreaterThanOrEqual(TRAIL_INSET - 1);
      expect(x).toBeLessThanOrEqual(48 - TRAIL_INSET + 1);
      expect(y).toBeLessThanOrEqual(48 - TRAIL_INSET + 1);
    }
  });
});
