// AR-SK2 移植需求第 5 項：鎖鏈與虛線的畫面下限 K＝max(1, 3 ÷ (4.2 × 地圖縮放))。
import { describe, expect, it } from "vitest";
import { chain, chainMinK, LINK_LEN, LINK_MIN_PX } from "./sk2FxArt";

/** 只記 ellipse 的半徑（鏈節正面＝外環＋洞兩個 ellipse）的假 ctx。 */
function fakeCtx(out: number[]): CanvasRenderingContext2D {
  const noop = () => undefined;
  return new Proxy({} as Record<string, unknown>, {
    get: (_t, k) => (k === "ellipse" ? (_x: number, _y: number, rx: number) => out.push(rx) : k === "globalAlpha" ? 1 : noop),
    set: () => true,
  }) as unknown as CanvasRenderingContext2D;
}

describe("AR-SK2 鎖鏈的畫面下限", () => {
  it("1600 寬（地圖縮放 1.31）不放大、800 寬（0.53）放大到鏈節 3 畫面 px", () => {
    expect(chainMinK(1.31)).toBe(1);
    const k800 = chainMinK(0.53);
    expect(k800).toBeCloseTo(1.348, 3);
    expect(LINK_LEN * k800 * 0.53).toBeCloseTo(LINK_MIN_PX, 6);
    expect(chainMinK(0)).toBe(1);
    expect(chainMinK(Number.NaN)).toBe(1);
  });

  it("鏈節大小與間距都乘 K（同一段路徑，K 大的節數少、每節大）", () => {
    const a: number[] = [], b: number[] = [];
    chain(fakeCtx(a), [[0, 0], [100, 0]], 1);
    chain(fakeCtx(b), [[0, 0], [100, 0]], 1.35);
    expect(Math.max(...b)).toBeCloseTo(Math.max(...a) * 1.35, 6);
    expect(b.length).toBeLessThan(a.length);
  });
});
