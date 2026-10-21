import { describe, expect, it } from "vitest";
import type { BattleResponse } from "../api/types";
import { RAISE, LIFT_MS } from "../battle/elevation";
import { frameOps, playbackPlan } from "../battle/playback";
import fixture from "../battle/fixtures/oil_depot_seed3.json";
import { dashSegments, dirtBit, dirtCount, dustRing, mixColor, silhouetteLoops, strataLines } from "./heightShapes";

describe("崖面", () => {
  it("每階一條暗線（不含崖頂與地面）", () => {
    expect(strataLines(0)).toEqual([]);
    expect(strataLines(RAISE)).toEqual([]);
    expect(strataLines(3 * RAISE)).toEqual([RAISE, 2 * RAISE]);
    expect(strataLines(1.5 * RAISE)).toEqual([RAISE]); // 補間中
  });

  it("漸層色在兩端等於上下色", () => {
    expect(mixColor(0x6b5236, 0x4a3824, 0)).toBe(0x6b5236);
    expect(mixColor(0x6b5236, 0x4a3824, 1)).toBe(0x4a3824);
  });
});

describe("遮擋剪影的虛線", () => {
  it("直線：3 實 2 空交錯", () => {
    const segs = dashSegments(
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
      ],
      false,
      3,
      2,
    );
    expect(segs.map(([a, b]) => [a.x, b.x])).toEqual([
      [0, 3],
      [5, 8],
    ]);
  });

  it("閉合路徑跨轉角也連續計長", () => {
    const square = [
      { x: 0, y: 0 },
      { x: 4, y: 0 },
      { x: 4, y: 4 },
      { x: 0, y: 4 },
    ];
    const segs = dashSegments(square, true, 3, 2);
    const total = segs.reduce((n, [a, b]) => n + Math.hypot(b.x - a.x, b.y - a.y), 0);
    // 周長 16：實線在 0–3、5–8、10–13、15–16（跨轉角不重新起算）
    expect(total).toBeCloseTo(10, 5);
  });

  it("輪廓是身體與頭兩個閉合圈，在腳底上方", () => {
    const loops = silhouetteLoops(24, 40, 48);
    expect(loops).toHaveLength(2);
    for (const loop of loops) for (const p of loop) expect(p.y).toBeLessThanOrEqual(40.0001);
  });
});

describe("升降粒子", () => {
  it("碎土 6～8 顆、位置確定、結束時透明", () => {
    for (const [x, y] of [
      [0, 0],
      [1, 0],
      [2, 5],
      [7, 3],
    ] as const) {
      const n = dirtCount(x, y);
      expect(n).toBeGreaterThanOrEqual(6);
      expect(n).toBeLessThanOrEqual(8);
    }
    expect(dirtBit(2, 7, 0.4, 48)).toEqual(dirtBit(2, 7, 0.4, 48));
    expect(dirtBit(0, 7, 1, 48).alpha).toBe(0);
    expect(dirtBit(0, 7, 0.5, 48).x).toBeLessThan(0); // 左緣往外噴
  });

  it("塵土圈往外擴散並淡出", () => {
    expect(dustRing(1, 48).radius).toBeGreaterThan(dustRing(0, 48).radius);
    expect(dustRing(1, 48).alpha).toBe(0);
  });
});

describe("播放計畫的升降動畫", () => {
  const base = fixture as unknown as BattleResponse;
  const step = base.steps[1]!;
  const raised: BattleResponse = {
    ...base,
    steps: [
      base.steps[0]!,
      {
        ...step,
        events: [...step.events, { type: "terrain_changed", pos: { x: 2, y: 3 }, height_before: 0, height_after: 1, terrain_before: "stone", terrain_after: "stone" }],
      },
    ],
  } as BattleResponse;

  it("高度改變的那一步在畫面更新後播升降，時間依速度縮放", () => {
    const normal = playbackPlan(raised, base.hero_id, "normal").frames[1]!;
    expect(normal.lifts).toEqual([{ pos: { x: 2, y: 3 }, from: 0, to: 1 }]);
    expect(normal.liftMs).toBe(LIFT_MS);
    const ops = frameOps(normal).map((o) => o.op);
    expect(ops.indexOf("lift")).toBe(ops.indexOf("view") + 1);
    expect(playbackPlan(raised, base.hero_id, "slow").frames[1]!.liftMs).toBe(LIFT_MS * 2);
    expect(playbackPlan(raised, base.hero_id, "fast").frames[1]!.liftMs).toBe(LIFT_MS / 2);
  });

  it("略過：沒有升降動畫，直接是結果", () => {
    const skip = playbackPlan(raised, base.hero_id, "skip");
    expect(skip.frames.every((f) => f.lifts.length === 0)).toBe(true);
    expect(skip.frames.flatMap(frameOps).some((o) => o.op === "lift")).toBe(false);
  });

  it("沒有高度改變的步驟不加升降", () => {
    const plan = playbackPlan(base, base.hero_id, "normal");
    expect(plan.frames.flatMap(frameOps).some((o) => o.op === "lift")).toBe(false);
  });
});
