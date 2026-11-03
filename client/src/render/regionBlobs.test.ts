import { describe, expect, it } from "vitest";
import { blobEdges } from "./surfaceBlobs";
import { regionShapes } from "./regionBlobs";

const T = 48;

describe("regionShapes（範圍併塊）", () => {
  it("相鄰兩格併成一塊：接縫不描，只描外緣", () => {
    const shapes = regionShapes(
      [
        { x: 3, y: 4 },
        { x: 2, y: 4 },
      ],
      T,
    );
    expect(shapes.map((s) => s.pos)).toEqual([
      { x: 2, y: 4 },
      { x: 3, y: 4 },
    ]);
    const [west, east] = shapes;
    // 西格的東邊貼齊格子邊界（接縫）：形狀有點在 x＝T 上，但沒有任何一段外緣沿著 x＝T 走（接縫不描）
    const segsAlong = (runs: { x: number; y: number }[][], x: number) =>
      runs.flatMap((r) => r.slice(1).map((p, i) => [r[i]!, p] as const)).filter(([a, b]) => Math.abs(a.x - x) < 0.01 && Math.abs(b.x - x) < 0.01);
    const westRuns = blobEdges(west!.shape);
    expect(westRuns.length).toBeGreaterThan(0);
    expect(west!.shape.points.some((p) => Math.abs(p.x - T) < 0.01)).toBe(true);
    expect(segsAlong(westRuns, T)).toEqual([]);
    expect(segsAlong(blobEdges(east!.shape), 0)).toEqual([]);
  });

  it("單格：四邊都是外緣，所有點都在格子裡", () => {
    const [one] = regionShapes([{ x: 0, y: 0 }], T);
    expect(one!.shape.full).toBe(false);
    expect(one!.shape.points.every((p) => p.x >= 0 && p.x <= T && p.y >= 0 && p.y <= T)).toBe(true);
    expect(one!.shape.points.every((p) => p.edge)).toBe(true);
  });

  it("3×3 的中間格整格填滿（沒有外緣）", () => {
    const cells = [];
    for (let y = 0; y < 3; y++) for (let x = 0; x < 3; x++) cells.push({ x, y });
    const mid = regionShapes(cells, T).find((s) => s.pos.x === 1 && s.pos.y === 1);
    expect(mid?.shape.full).toBe(true);
    expect(blobEdges(mid!.shape)).toEqual([]);
  });

  it("重複的格子去重；結果固定", () => {
    const a = regionShapes([{ x: 1, y: 1 }, { x: 1, y: 1 }], T);
    expect(a).toHaveLength(1);
    expect(regionShapes([{ x: 1, y: 1 }], T)).toEqual(a);
    expect(regionShapes([], T)).toEqual([]);
  });
});
