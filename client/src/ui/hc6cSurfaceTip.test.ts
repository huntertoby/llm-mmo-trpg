// HC-6c（AR-X10 待決 4）：腳下表面的提示（`SurfaceBadge`）骰子行另起一行、次要字色，排法同狀態提示。
import { describe, expect, it } from "vitest";
import { surfaceTile } from "../render/skillIcon";
import { surfaceTipParts } from "./StatusCardParts";

// 沒有 @types/node：同 statusCard.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("HC-6c：腳下表面提示的骰子行", () => {
  it("毒：骰子行自己一段、次要字色；其他字和改前接成一句時相同", () => {
    const parts = surfaceTipParts("poison");
    expect(parts.filter((p) => p.secondary).map((p) => p.text)).toEqual(["擲 1d4，每點 ×10"]);
    expect(parts.map((p) => p.text).join(" ")).toBe(surfaceTile("poison").tip);
  });
  it("聖光兩行骰子都另起一段", () => {
    expect(surfaceTipParts("holy").filter((p) => p.secondary)).toHaveLength(2);
  });
  it("沒有骰子的表面照舊一段；對照表沒有的寫「地面上的表面」", () => {
    expect(surfaceTipParts("oil").every((p) => !p.secondary)).toBe(true);
    expect(surfaceTipParts("no_such_surface")).toEqual([{ text: "地面上的表面", secondary: false }]);
  });
  it("SurfaceBadge 把分段交給說明卡", () => {
    const src = readFileSync("src/ui/StatusCardParts.tsx", "utf8");
    expect(src).toContain("parts={surfaceTipParts(surface)}");
  });
});
