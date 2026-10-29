// Phase 3T-4b：武器小圖示的斜放角度。
import { describe, expect, it } from "vitest";
import { iconAngle, isDiagonal } from "./weaponIcon";

describe("武器小圖示斜放", () => {
  it("一律 45°：槍弩朝右上（逆時針），其餘刃、柄朝右上（順時針）", () => {
    for (const kind of ["sword", "axe", "hammer", "staff", "bow", "fist", "scythe", "whip"]) {
      expect(isDiagonal(kind)).toBe(true);
      expect(iconAngle(kind)).toBeCloseTo(Math.PI / 4, 9);
    }
    for (const kind of ["pistol", "shotgun", "longgun", "crossbow"]) expect(iconAngle(kind)).toBeCloseTo(-Math.PI / 4, 9);
  });
});
