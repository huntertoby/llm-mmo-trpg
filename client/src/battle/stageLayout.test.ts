import { describe, expect, it } from "vitest";
import { TILE_SIZE, tileCenter } from "./geometry";
import {
  CARD_GAP,
  cardPlacement,
  clientToTile,
  dialogStartsLow,
  fitScale,
  MAX_SCALE,
  MIN_SCALE,
  scaledSize,
} from "./stageLayout";

const T = TILE_SIZE;

describe("fitScale", () => {
  it("fits the limiting dimension and keeps tiles square", () => {
    const grid = { width: 10, height: 10 };
    // 1250×700 的可用空間：高度是限制
    expect(fitScale({ width: 1250, height: 700 }, grid)).toBeCloseTo(700 / (10 * T));
    // 寬度是限制
    expect(fitScale({ width: 400, height: 900 }, grid)).toBeCloseTo(400 / (10 * T));
    const s = fitScale({ width: 1250, height: 700 }, { width: 14, height: 9 });
    expect(s).toBeCloseTo(Math.min(1250 / (14 * T), 700 / (9 * T)));
  });

  it("clamps to the min and max scale and falls back to 1 for an unmeasured area", () => {
    const grid = { width: 4, height: 4 };
    expect(fitScale({ width: 5000, height: 5000 }, grid)).toBe(MAX_SCALE);
    expect(fitScale({ width: 10, height: 10 }, grid)).toBe(MIN_SCALE);
    expect(fitScale({ width: 0, height: 500 }, grid)).toBe(1);
    expect(fitScale({ width: Number.NaN, height: 500 }, grid)).toBe(1);
  });

  it("scaledSize never exceeds the scaled model size", () => {
    const grid = { width: 10, height: 10 };
    const s = fitScale({ width: 1001, height: 683 }, grid);
    const size = scaledSize(grid, s);
    expect(size.width).toBeLessThanOrEqual(683);
    expect(size.height).toBeLessThanOrEqual(683);
    expect(size.width).toBe(size.height);
  });
});

describe("clientToTile", () => {
  const grid = { width: 10, height: 8 };

  it("is the plain pixel mapping at scale 1 with the canvas at the page origin", () => {
    const rect = { left: 0, top: 0, width: 10 * T, height: 8 * T };
    expect(clientToTile(0, 0, rect, grid)).toEqual({ x: 0, y: 0 });
    expect(clientToTile(T - 0.01, T - 0.01, rect, grid)).toEqual({ x: 0, y: 0 });
    expect(clientToTile(T, 0, rect, grid)).toEqual({ x: 1, y: 0 });
  });

  it("maps tile centers back to the same tile when the canvas is scaled and offset", () => {
    for (const scale of [0.5, 0.73, 1, 1.31, 1.87, 2]) {
      const rect = { left: 137.5, top: 48.25, width: 10 * T * scale, height: 8 * T * scale };
      for (let y = 0; y < grid.height; y += 1) {
        for (let x = 0; x < grid.width; x += 1) {
          const c = tileCenter({ x, y });
          const cx = rect.left + c.x * scale;
          const cy = rect.top + c.y * scale;
          expect(clientToTile(cx, cy, rect, grid)).toEqual({ x, y });
        }
      }
    }
  });

  it("picks the right tile right next to a tile border after scaling", () => {
    const scale = 1.4;
    const rect = { left: 100, top: 50, width: 10 * T * scale, height: 8 * T * scale };
    const border = rect.left + 3 * T * scale; // 第 2 與第 3 格的分界
    expect(clientToTile(border - 0.5, 60, rect, grid)?.x).toBe(2);
    expect(clientToTile(border + 0.5, 60, rect, grid)?.x).toBe(3);
  });

  it("uses the rect's real width and height independently (non-uniform CSS scaling)", () => {
    const rect = { left: 0, top: 0, width: 10 * T * 2, height: 8 * T }; // 只橫向放大兩倍
    expect(clientToTile(2 * T * 2 + 1, T * 3 + 1, rect, grid)).toEqual({ x: 2, y: 3 });
  });

  it("returns null outside the canvas", () => {
    const rect = { left: 100, top: 50, width: 10 * T * 1.5, height: 8 * T * 1.5 };
    expect(clientToTile(99, 60, rect, grid)).toBeNull();
    expect(clientToTile(110, 49, rect, grid)).toBeNull();
    expect(clientToTile(rect.left + rect.width, 60, rect, grid)).toBeNull();
    expect(clientToTile(110, rect.top + rect.height, rect, grid)).toBeNull();
    expect(clientToTile(110, 60, { ...rect, width: 0 }, grid)).toBeNull();
  });
});

describe("cardPlacement", () => {
  const grid = { width: 10, height: 10 };

  it("puts the card right of a tile in the left half and left of a tile in the right half", () => {
    const s = 1.5;
    const t = T * s;
    expect(cardPlacement({ x: 2, y: 1 }, grid, s)).toEqual({ left: Math.round(3 * t + CARD_GAP), top: Math.round(1 * t) });
    expect(cardPlacement({ x: 7, y: 1 }, grid, s)).toEqual({ right: Math.round(3 * t + CARD_GAP), top: Math.round(1 * t) });
  });

  it("grows upward from the tile's bottom edge in the lower half", () => {
    const s = 1;
    expect(cardPlacement({ x: 0, y: 9 }, grid, s)).toEqual({ left: T + CARD_GAP, bottom: 0 });
    expect(cardPlacement({ x: 9, y: 6 }, grid, s)).toEqual({ right: T + CARD_GAP, bottom: 3 * T });
  });
});

describe("dialogStartsLow", () => {
  const grid = { width: 10, height: 10 };
  it("moves the reaction dialog down when the trigger is in the upper half", () => {
    expect(dialogStartsLow({ x: 3, y: 2 }, grid)).toBe(true);
    expect(dialogStartsLow({ x: 3, y: 4 }, grid)).toBe(true);
    expect(dialogStartsLow({ x: 3, y: 5 }, grid)).toBe(false);
    expect(dialogStartsLow(null, grid)).toBe(false);
  });
});
