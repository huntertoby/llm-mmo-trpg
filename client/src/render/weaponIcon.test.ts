// Phase 3T-4b：武器小圖示的斜放角度。
import { describe, expect, it } from "vitest";
import { iconAngle, isDiagonal } from "./weaponIcon";

describe("武器小圖示斜放", () => {
  it("一律 45°：槍弩朝右上（逆時針），其餘刃、柄朝右上（順時針）", () => {
    for (const kind of ["sword", "axe", "hammer", "staff", "bow", "scythe", "whip"]) {
      expect(isDiagonal(kind)).toBe(true);
      expect(iconAngle(kind)).toBeCloseTo(Math.PI / 4, 9);
    }
    for (const kind of ["shotgun", "longgun", "crossbow"]) expect(iconAngle(kind)).toBeCloseTo(-Math.PI / 4, 9);
  });

  it("手槍（側面 L 形，槍口朝右）與拳套（正面指虎）不斜放（3T-4c）", () => {
    expect(isDiagonal("fist")).toBe(false);
    expect(iconAngle("fist")).toBe(0);
    expect(isDiagonal("pistol")).toBe(false);
    expect(iconAngle("pistol")).toBe(0);
  });
});
