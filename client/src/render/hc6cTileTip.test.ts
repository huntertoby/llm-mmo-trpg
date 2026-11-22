// HC-6c（AR-X10 待決 4）：組裝列部件（`statusTile`／`surfaceTile` 與工坊選項的小圖）的說明，骰子行另起一行、次要字色。
import { describe, expect, it } from "vitest";
import { optionTile, statusTile, surfaceTile } from "./skillIcon";

// 沒有 @types/node：同 statusCard.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("HC-6c：組裝列部件說明的骰子行", () => {
  it("狀態「燃燒」：骰子行另起一段；字串 tip 不變（接起來和分段的字相同）", () => {
    const t = statusTile("burning");
    expect(t.parts?.filter((p) => p.secondary).map((p) => p.text)).toEqual(["擲 1d6，每點 ×10"]);
    expect(t.parts?.map((p) => p.text).join(" ")).toBe(t.tip);
  });
  it("表面「毒」、工坊選項的狀態與表面也帶分段", () => {
    expect(surfaceTile("poison").parts?.some((p) => p.secondary)).toBe(true);
    expect(optionTile("status", "burning")?.parts?.some((p) => p.secondary)).toBe(true);
    expect(optionTile("surface", "poison")?.parts?.some((p) => p.secondary)).toBe(true);
  });
  it("對照表沒有的照舊寫「狀態」「地面上的表面」", () => {
    expect(statusTile("no_such").parts).toEqual([{ text: "狀態", secondary: false }]);
    expect(surfaceTile("no_such").parts).toEqual([{ text: "地面上的表面", secondary: false }]);
  });
  it("部件說明框都把分段交給 PartTip", () => {
    const src = readFileSync("src/ui/SkillIconView.tsx", "utf8");
    expect(src.match(/parts=\{(tile|t)\.parts\}/g)).toHaveLength(4);
  });
});
