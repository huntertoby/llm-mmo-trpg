// AR-X10（美術 PM `docs/art/AR-X10驗收.md`）：走路預覽小牌的字在畫面上 ≥10 px，地圖縮小時小牌整張反向放大。
import { describe, expect, it } from "vitest";
import { MIN_PATH_TAG_FONT_PX, PATH_TAG_FONT, pathTagFontPx, pathTagScale, placeTags, TAG_HEIGHT } from "./pathArt";

// 沒有 @types/node：同 ui/statusCard.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("AR-X10：路徑小牌字的最小畫面尺寸", () => {
  it("800 寬實機縮放 0.62：畫面字 ≥ 10 px（原本 12 × 0.62 ≈ 7.4 px）", () => {
    expect(PATH_TAG_FONT * 0.62).toBeLessThan(10);
    expect(pathTagFontPx(0.62)).toBeGreaterThanOrEqual(MIN_PATH_TAG_FONT_PX);
    expect(pathTagFontPx(0.62)).toBeGreaterThanOrEqual(10);
    expect(pathTagScale(0.62)).toBeCloseTo(10 / (12 * 0.62));
  });
  it("地圖再小也不低於 10 px；1600 寬（1.308）與原本一樣、倍率 1", () => {
    for (const s of [0.3, 0.42, 0.531, 0.62, 0.8, 0.83]) expect(pathTagFontPx(s)).toBeGreaterThanOrEqual(10 - 1e-9);
    expect(pathTagScale(1.308)).toBe(1);
    expect(pathTagFontPx(1.308)).toBeCloseTo(12 * 1.308);
  });
  it("擺位用放大後的高度：放大的小牌放在格子上方時，往上移整張高度", () => {
    const o = { x: 0, y: 100 };
    const k = pathTagScale(0.62);
    const [plain] = placeTags([{ o, w: 80 }]);
    const [big] = placeTags([{ o, w: 80 * k }], [], TAG_HEIGHT * k);
    expect(plain).toEqual({ x: 24, y: 100 - TAG_HEIGHT + 4 });
    expect(big?.y).toBeCloseTo(100 - TAG_HEIGHT * k + 4);
  });
  it("戰場的高亮層在畫小牌與改縮放時都套用倍率（pathTagRescale）", () => {
    const layer = readFileSync("src/render/battle/highlightLayer.ts", "utf8");
    expect(layer).toContain("pathTagScale(this.scale)");
    expect(layer).toContain("TAG_HEIGHT * k");
    const renderer = readFileSync("src/render/BattleRenderer.ts", "utf8");
    expect(renderer).toContain("this.pathTagRescale();");
  });
});
