import { describe, expect, it } from "vitest";
import { FONT } from "./labels";

// 沒有 @types/node：用變數名載入 node:fs（vitest 在 node 環境執行；CSS 的 ?raw 會被 vite 處理成空字串）。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const fontCss = readFileSync("src/assets/fonts/noto-sans-tc/noto-sans-tc.css", "utf-8");
const styles = readFileSync("src/styles/base.css", "utf-8");

describe("字型（Phase 3-35）", () => {
  it("畫布字型清單以 Noto Sans TC 開頭，且與 styles/base.css 的 body 一致", () => {
    expect(FONT.startsWith("'Noto Sans TC'")).toBe(true);
    expect(styles).toContain('font-family: "Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif;');
  });
  it("@font-face 只有 400／700、相對路徑、沒有外部網址", () => {
    expect(fontCss).not.toMatch(/https?:\/\//);
    const weights = new Set([...fontCss.matchAll(/font-weight:\s*(\d+)/g)].map((m) => m[1]));
    expect([...weights].sort()).toEqual(["400", "700"]);
    expect(fontCss).toContain("font-display: swap");
    expect(fontCss).toContain("unicode-range");
  });
});
