import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "../battle/geometry";
import { ROW_ICON_FEET, ROW_Y_FEET, rowShiftForMarker } from "./unitSprite";

describe("腳邊狀態列（3U-2b）", () => {
  it("圖示列在 HP 條正上方，仍在自己的格子內", () => {
    expect(ROW_Y_FEET + ROW_ICON_FEET / 2).toBeLessThan(TILE_SIZE * 0.36);
    expect(ROW_Y_FEET - ROW_ICON_FEET / 2).toBeGreaterThan(-TILE_SIZE / 2);
  });
  it("88px 格的圖示約 20px", () => {
    const px = (ROW_ICON_FEET * 88) / TILE_SIZE;
    expect(px).toBeGreaterThan(19);
    expect(px).toBeLessThan(21);
  });
  it("碰到字母標記就整排往右讓，單一圖示不用讓", () => {
    const markerRight = -TILE_SIZE * 0.37 + 8;
    for (const n of [1, 2, 3]) {
      const left = rowShiftForMarker(n) - ((n - 1) * (ROW_ICON_FEET + 1)) / 2 - ROW_ICON_FEET / 2;
      expect(left).toBeGreaterThanOrEqual(markerRight);
    }
    expect(rowShiftForMarker(1)).toBe(0);
    expect(rowShiftForMarker(3)).toBeGreaterThan(rowShiftForMarker(2));
  });
});
