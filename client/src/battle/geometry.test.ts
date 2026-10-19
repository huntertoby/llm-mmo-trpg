import { describe, expect, it } from "vitest";
import { canvasSize, pixelToTile, tileCenter, TILE_SIZE } from "./geometry";

describe("pixelToTile", () => {
  const grid = { width: 4, height: 3 };

  it("maps a click inside a tile to that tile", () => {
    expect(pixelToTile(0, 0, grid)).toEqual({ x: 0, y: 0 });
    expect(pixelToTile(TILE_SIZE - 0.1, TILE_SIZE - 0.1, grid)).toEqual({ x: 0, y: 0 });
    expect(pixelToTile(TILE_SIZE, 0, grid)).toEqual({ x: 1, y: 0 });
    expect(pixelToTile(3 * TILE_SIZE + 5, 2 * TILE_SIZE + 5, grid)).toEqual({ x: 3, y: 2 });
  });

  it("returns null outside the grid", () => {
    expect(pixelToTile(-1, 5, grid)).toBeNull();
    expect(pixelToTile(4 * TILE_SIZE, 5, grid)).toBeNull();
    expect(pixelToTile(5, 3 * TILE_SIZE, grid)).toBeNull();
  });

  it("round-trips with tileCenter and respects a custom tile size", () => {
    const c = tileCenter({ x: 2, y: 1 }, 10);
    expect(c).toEqual({ x: 25, y: 15 });
    expect(pixelToTile(c.x, c.y, grid, 10)).toEqual({ x: 2, y: 1 });
    expect(canvasSize(grid, 10)).toEqual({ width: 40, height: 30 });
  });
});
