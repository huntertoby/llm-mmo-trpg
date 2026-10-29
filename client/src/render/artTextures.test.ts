// 3U-2：小人貼圖照實際顯示大小畫（解析度隨螢幕縮放；鍵含解析度）。
import { describe, expect, it } from "vitest";
import { ArtTextures, FIGURE_RESOLUTION, figureResolution } from "./artTextures";
import { DOLL_SCALE, DOLL_SCALE_OLD, SUMMON_SCALE } from "./paperdoll";

describe("小人貼圖解析度", () => {
  it("向上取 0.5 級距，夾在 1.5～6", () => {
    expect(figureResolution(1.55)).toBe(2);
    expect(figureResolution(2)).toBe(2);
    expect(figureResolution(2.01)).toBe(2.5);
    expect(figureResolution(0.3)).toBe(1.5);
    expect(figureResolution(99)).toBe(6);
    expect(figureResolution(0)).toBe(FIGURE_RESOLUTION);
  });

  it("未設螢幕縮放用預設；設了之後依顯示大小算（88px 格比 52px 格解析度高）", () => {
    const art = new ArtTextures();
    const d = (48 / 52) * DOLL_SCALE;
    expect(art.figureRes(d)).toBe(FIGURE_RESOLUTION);
    art.setScreenScale(88 / 48);
    const big = art.figureRes(d);
    art.setScreenScale(1);
    const small = art.figureRes(d);
    expect(big).toBeGreaterThan(small);
    expect(big).toBeGreaterThanOrEqual(d * (88 / 48)); // 不會畫小再放大
  });
});

describe("3U-2 縮放常數", () => {
  it("人 0.74 → 0.92、野獸物件召喚物 1 → 1.15", () => {
    expect(DOLL_SCALE_OLD).toBe(0.74);
    expect(DOLL_SCALE).toBe(0.92);
    expect(SUMMON_SCALE).toBe(1.15);
    expect(52 * (DOLL_SCALE - DOLL_SCALE_OLD)).toBeCloseTo(9.36, 2);
  });
});
