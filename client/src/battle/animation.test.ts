import { describe, expect, it } from "vitest";
import { moveAnimOf, rowDuringMove } from "./animation";

describe("移動動畫途中的圖層排（使用者回報「移動中陷進地板」）", () => {
  it.each([
    // [起點 y, 終點 y, t, 期望的排]
    [5, 4, 0, 5], // 往北走：還在起點那排
    [5, 4, 0.3, 5], // 跨在 4、5 之間 → 較南的 5（不會被第 5 排的地板蓋住）
    [5, 4, 0.99, 5],
    [5, 4, 1, 4], // 到了才換到終點那排
    [2, 3, 0, 2],
    [2, 3, 0.01, 3], // 往南走：一離開就換到較南的 3
    [2, 3, 1, 3],
    [4, 4, 0.5, 4], // 同一排左右走不換
    [1, 4, 0.5, 3], // 一次跨多排：當下 y＝2.5 → 3
  ])("從第 %i 排到第 %i 排，t=%f → 第 %i 排", (from, to, t, row) => {
    expect(rowDuringMove(from, to, t)).toBe(row);
  });

  it("t 超出 0～1 時夾住", () => {
    expect(rowDuringMove(5, 4, -1)).toBe(5);
    expect(rowDuringMove(5, 4, 2)).toBe(4);
  });
});

describe("6R-1c：沒有技能卡的跳躍（獸躍）也播跳躍片段", () => {
  const ev = (mode: string) => ({ seq: 1, round: 1, type: "unit_moved", unit_id: "h", from_pos: { x: 1, y: 4 }, to_pos: { x: 4, y: 4 }, mode }) as never;
  it("leap 帶 leap_air（離地弧度），其他位移不帶", () => {
    expect(moveAnimOf(ev("leap")).clip).toBe("leap_air");
    for (const mode of ["walk", "dash", "forced", "teleport", "swap"]) expect(moveAnimOf(ev(mode)).clip).toBeUndefined();
  });
});
