import { describe, expect, it } from "vitest";
import type { DrawModel, TileDraw } from "./drawModel";
import { CLIFF_MIN_DIFF, heightDecor, pedestalScale } from "./heightModel";
import { clientToTile } from "./stageLayout";
import { TILE_SIZE } from "./geometry";

function tile(x: number, y: number, height: number, blocked = false): TileDraw {
  return {
    x,
    y,
    height,
    fill: 0,
    heightLabel: String(height),
    terrain: blocked ? "chasm" : "stone",
    surface: "none" as TileDraw["surface"],
    terrainName: "",
    surfaceName: null,
    blocked,
    deadly: blocked,
    wall: false,
  };
}

function model(heights: number[][], blockedAt: Array<[number, number]> = []): DrawModel {
  const tiles: TileDraw[] = [];
  heights.forEach((row, y) =>
    row.forEach((h, x) => tiles.push(tile(x, y, h, blockedAt.some(([bx, by]) => bx === x && by === y)))),
  );
  return { width: heights[0]?.length ?? 0, height: heights.length, tiles, objects: [], units: [], traps: [], auras: [], zones: [], wells: [] };
}

describe("heightDecor", () => {
  it("平地沒有任何裝飾", () => {
    const d = heightDecor(model([[0, 0], [0, 0]]));
    expect(d.cliffs).toEqual([]);
  });

  it("高度差 1 沒有懸崖線，≥ 2 有（每個較低的邊）", () => {
    expect(heightDecor(model([[1, 0]])).cliffs).toEqual([]);
    const d = heightDecor(model([[CLIFF_MIN_DIFF, 0], [0, 0]]));
    expect(d.cliffs.map((c) => c.side).sort()).toEqual(["east", "south"]);
  });

  it("阻擋地形（深淵）不參與高度比較", () => {
    const d = heightDecor(model([[3, 0]], [[1, 0]]));
    expect(d.cliffs).toEqual([]);
  });

  it("底座：高度 0 不畫，越高越大", () => {
    expect(pedestalScale(0)).toBe(0);
    expect(pedestalScale(2)).toBeGreaterThan(pedestalScale(1));
  });
});

describe("clientToTile 不受高度影響", () => {
  it("點格子頂面仍換算成該格（側面只是繪圖）", () => {
    const grid = { width: 4, height: 4 };
    const rect = { left: 10, top: 20, width: 4 * TILE_SIZE, height: 4 * TILE_SIZE };
    expect(clientToTile(10 + 1.5 * TILE_SIZE, 20 + 1.5 * TILE_SIZE, rect, grid)).toEqual({ x: 1, y: 1 });
    // 南側面畫在 (1,2) 頂端，點在其中仍是 (1,2)
    expect(clientToTile(10 + 1.5 * TILE_SIZE, 20 + 2 * TILE_SIZE + 3, rect, grid)).toEqual({ x: 1, y: 2 });
    const half = { ...rect, width: rect.width / 2, height: rect.height / 2 };
    expect(clientToTile(10 + (1.5 * TILE_SIZE) / 2, 20 + (2 * TILE_SIZE) / 2 + 1, half, grid)).toEqual({ x: 1, y: 2 });
  });

  it("格子基礎尺寸是 16 px 素材的整數倍", () => {
    expect(TILE_SIZE % 16).toBe(0);
  });
});
