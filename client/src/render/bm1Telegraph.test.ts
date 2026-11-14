// BM-1：延遲預告字的最小畫面尺寸（美術 PM GB A5 審查第 8 節第 2 條：畫面字 ≥10 px、錨在格子角、設上限不蓋目標頭）。
import { describe, expect, it } from "vitest";
import { TILE_SIZE } from "../battle/geometry";
import { MIN_TELEGRAPH_FONT_PX, TELEGRAPH_BADGE_MAX_K, TELEGRAPH_BADGE_R, TELEGRAPH_FONT, telegraphBadgeCenter, telegraphBadgeScale } from "./telegraphBadge";
import { readFile, SRC_DIR } from "../test/sourceScan";

const T = TILE_SIZE;

describe("倍率", () => {
  it("1600 寬（地圖 1.03～1.31）不放大；800 寬（0.53）放大到畫面字剛好 10 px", () => {
    expect(telegraphBadgeScale(1.31)).toBe(1);
    expect(telegraphBadgeScale(1.03)).toBe(1);
    const k = telegraphBadgeScale(0.53);
    expect(k).toBeCloseTo(10 / (12 * 0.53), 6);
    expect(TELEGRAPH_FONT * k * 0.53).toBeCloseTo(MIN_TELEGRAPH_FONT_PX, 6);
  });
  it("有上限：地圖再小也不超過 ×2", () => {
    expect(telegraphBadgeScale(0.3)).toBe(TELEGRAPH_BADGE_MAX_K);
    expect(telegraphBadgeScale(0)).toBe(1);
  });
});

describe("錨在格子角", () => {
  it("×1 是原本的位置（格子右上角往內 11）", () => {
    expect(telegraphBadgeCenter(1)).toEqual({ x: T - 11, y: 11 });
  });
  it("放大時圓上朝格子中心那一點不動（不比 1600 多蓋到格子裡的人），往右上長；圓心仍在格子裡", () => {
    const inner = (k: number) => {
      const c = telegraphBadgeCenter(k);
      const r = TELEGRAPH_BADGE_R * k;
      return { x: c.x - r / Math.SQRT2, y: c.y + r / Math.SQRT2 };
    };
    for (const k of [1.2, telegraphBadgeScale(0.53), TELEGRAPH_BADGE_MAX_K]) {
      expect(inner(k).x).toBeCloseTo(inner(1).x, 6);
      expect(inner(k).y).toBeCloseTo(inner(1).y, 6);
      const c = telegraphBadgeCenter(k);
      expect(c.x).toBeLessThan(T);
      expect(c.y).toBeGreaterThan(0);
    }
  });
});

describe("接線", () => {
  it("HighlightLayer 用 telegraphBadge 的常數畫預告字，縮放改變時重排（BattleRenderer.setScale）", () => {
    const hl = readFile(SRC_DIR, "render/battle/highlightLayer.ts");
    expect(hl).toContain("const glyph = label(m.glyph, TELEGRAPH_FONT, m.color, true);");
    expect(hl).toContain("this.telegraphRescale();");
    expect(hl).toContain("b.node.scale.set(k);");
    expect(readFile(SRC_DIR, "render/BattleRenderer.ts")).toContain("this.telegraphRescale();");
  });
});
