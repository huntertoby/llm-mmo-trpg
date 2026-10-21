import { describe, expect, it } from "vitest";
import { pedestalScale } from "./heightModel";
import { TILE_SIZE } from "./geometry";

describe("pedestalScale", () => {
  it("底座：高度 0 不畫，越高越大", () => {
    expect(pedestalScale(0)).toBe(0);
    expect(pedestalScale(2)).toBeGreaterThan(pedestalScale(1));
  });

  it("格子基礎尺寸是 16 px 素材的整數倍", () => {
    expect(TILE_SIZE % 16).toBe(0);
  });
});
