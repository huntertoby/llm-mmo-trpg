import { describe, expect, it } from "vitest";
import { isProcedural, proceduralPatches } from "./proceduralTerrain";

describe("proceduralTerrain", () => {
  it("岩漿、深淵、冰窟有程式紋理；其他地形沒有", () => {
    for (const t of ["lava", "chasm", "ice_hole"]) {
      expect(isProcedural(t)).toBe(true);
      expect(proceduralPatches(t, 2, 3, 48).length).toBeGreaterThan(1);
    }
    expect(isProcedural("stone")).toBe(false);
    expect(proceduralPatches("stone", 0, 0, 48)).toEqual([]);
  });

  it("同一格永遠一樣、不同格不同（確定性）", () => {
    expect(proceduralPatches("lava", 1, 2, 48)).toEqual(proceduralPatches("lava", 1, 2, 48));
    expect(proceduralPatches("lava", 1, 2, 48)).not.toEqual(proceduralPatches("lava", 5, 7, 48));
  });

  it("所有矩形都在格子內（容許邊緣碎石 1 px 內）", () => {
    for (const t of ["lava", "chasm", "ice_hole"]) {
      for (const p of proceduralPatches(t, 4, 4, 48)) {
        expect(p.x).toBeGreaterThanOrEqual(0);
        expect(p.y).toBeGreaterThanOrEqual(0);
        expect(p.x + p.w).toBeLessThanOrEqual(48);
        expect(p.y + p.h).toBeLessThanOrEqual(48);
      }
    }
  });
});
