// HC-6c（美術 PM `docs/art/HC-3看圖.md`）：營火「重閃」鈕統一成懸掛縮排——「重閃」固定在左邊、內文在它右邊換行並對齊。
import { describe, expect, it } from "vitest";

// 沒有 @types/node：同 statusCard.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("HC-6c：重閃鈕的懸掛縮排", () => {
  it("「重閃」與內文分成兩欄，內文（含轉型、變弱、沒有選項的提醒）都在右欄", () => {
    const src = readFileSync("src/run/CampfireSkillCare.tsx", "utf8");
    expect(src).toContain('<span className="reflash-word">重閃</span>');
    const body = src.slice(src.indexOf('<span className="reflash-body">'));
    expect(body.indexOf("{s.label}")).toBeGreaterThan(0);
    expect(body.indexOf("reflash-transform-")).toBeGreaterThan(0);
    expect(body.indexOf("<WeakerNote")).toBeGreaterThan(0);
    expect(body.indexOf("reflash-none-")).toBeGreaterThan(0);
    expect(src).not.toContain("重閃　{s.label}");
  });
  it("CSS：鈕是左右兩欄，「重閃」不換行不縮，右欄可縮、換行對齊右欄左緣", () => {
    const css = readFileSync("src/styles/flash.css", "utf8");
    expect(css).toMatch(/\.reflash-slots button:has\(> \.reflash-word\) \{\s*display: flex;\s*align-items: baseline;\s*gap: 1em;/);
    expect(css).toMatch(/\.reflash-word \{\s*flex: none;\s*white-space: nowrap;/);
    expect(css).toMatch(/\.reflash-body \{\s*flex: 1 1 0;\s*min-width: 0;/);
  });
});
