import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "../battle/geometry";
import { ROW_ICON_FEET, ROW_MAX_ICONS, ROW_Y_FEET, rowPlacement, rowShiftForMarker } from "./unitSprite";
import { SUMMON_BADGE_RADIUS, summonBadgeOffset } from "./unitLook";

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
  it("最多 2 個圖示（3U-2c）", () => {
    expect(ROW_MAX_ICONS).toBe(2);
  });
  it("一般單位：兩個圖示不出格、不碰字母標記", () => {
    const { shift, pitch } = rowPlacement(2, null);
    expect(pitch).toBe(ROW_ICON_FEET + 1);
    const left = shift - pitch / 2 - ROW_ICON_FEET / 2;
    const right = shift + pitch / 2 + ROW_ICON_FEET / 2;
    expect(left).toBeGreaterThanOrEqual(-TILE_SIZE * 0.37 + 8);
    expect(right).toBeLessThan(TILE_SIZE / 2 - 5); // 留位置給 +N 角標
  });
  it("召喚物：兩個圖示擠進字母標記與回合數徽章之間，不蓋住回合數", () => {
    const badgeLeft = summonBadgeOffset({ bomb: null }, TILE_SIZE).x - SUMMON_BADGE_RADIUS;
    const { shift, pitch } = rowPlacement(2, badgeLeft);
    const left = shift - pitch / 2 - ROW_ICON_FEET / 2;
    const right = shift + pitch / 2 + ROW_ICON_FEET / 2;
    expect(left).toBeGreaterThanOrEqual(-TILE_SIZE * 0.37 + 8);
    expect(right).toBeLessThanOrEqual(badgeLeft);
    expect(pitch).toBeGreaterThanOrEqual(6);
  });
});
