// 6N-5：命中時的停頓（效果時鐘停在那一刻，用掉停頓的時間再走）。
import { describe, expect, it } from "vitest";
import { addFreeze, advanceClock, type Freeze } from "./hitStop";

describe("hit stop clock (6N-5)", () => {
  it("no stop: the clock just moves", () => {
    expect(advanceClock(10, 16, [])).toBe(26);
  });

  it("stops at the hit point for the stop length, then moves on", () => {
    const f: Freeze[] = [{ at: 100, left: 100 }];
    let c = 0;
    const seen: number[] = [];
    for (let i = 0; i < 20; i++) {
      c = advanceClock(c, 16, f);
      seen.push(c);
    }
    // 走到 100 停住，100 毫秒（約 6 幀）後才往下走；總共少走 100 毫秒
    expect(seen.filter((x) => x === 100).length).toBeGreaterThanOrEqual(6);
    expect(c).toBe(20 * 16 - 100);
    expect(f).toEqual([]);
  });

  it("a long frame crosses the stop and keeps the remainder", () => {
    const f: Freeze[] = [{ at: 50, left: 60 }];
    expect(advanceClock(40, 200, f)).toBe(40 + 200 - 60);
  });

  it("addFreeze: same moment keeps the longer; sorted; past or zero ones ignored", () => {
    const f: Freeze[] = [];
    addFreeze(f, 300, 60, 0);
    addFreeze(f, 100, 100, 0);
    addFreeze(f, 300, 100, 0);
    addFreeze(f, 50, 100, 80); // 已經過了
    addFreeze(f, 400, 0, 0);
    expect(f).toEqual([
      { at: 100, left: 100 },
      { at: 300, left: 100 },
    ]);
  });

  it("deterministic: same deltas → same clock", () => {
    const run = () => {
      const f: Freeze[] = [{ at: 120, left: 100 }, { at: 400, left: 60 }];
      let c = 0;
      for (const d of [16, 17, 16, 33, 16, 50, 16, 16, 100, 16, 16]) c = advanceClock(c, d, f);
      return c;
    };
    expect(run()).toBe(run());
  });
});
