// LW-2b（PNL-4 複驗新可修）：「用〔…〕抵」小鈕裡，線頭名字最後兩個字連同「〕抵」不斷行，
// 145 寬時斷成「用〔商人欠你／人情〕抵」，不會斷成「商人欠你人／情〕抵」。
import { describe, expect, it } from "vitest";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { WAIVE_GLUE_CHARS, waiveRuns } from "./solutionGrid";

describe("waiveRuns", () => {
  it("尾巴＝名字最後兩個字＋「〕抵」", () => {
    expect(WAIVE_GLUE_CHARS).toBe(2);
    expect(waiveRuns("用〔商人欠你人情〕抵")).toEqual({ head: "用〔商人欠你", tail: "人情〕抵" });
    expect(waiveRuns("用〔舊債〕抵")).toEqual({ head: "用〔", tail: "舊債〕抵" });
  });
  it("名字不到兩個字：整個名字＋「〕抵」；空名字只黏「〕抵」", () => {
    expect(waiveRuns("用〔債〕抵")).toEqual({ head: "用〔", tail: "債〕抵" });
    expect(waiveRuns("用〔〕抵")).toEqual({ head: "用〔", tail: "〕抵" });
  });
  it("不是「用〔…〕抵」的樣子：整句當前段、沒有尾巴", () => {
    expect(waiveRuns("peddler_owes_you")).toEqual({ head: "peddler_owes_you", tail: "" });
    expect(waiveRuns("用商人抵")).toEqual({ head: "用商人抵", tail: "" });
  });
  it("前段＋尾巴＝原字（不丟字）", () => {
    for (const s of ["用〔商人欠你人情〕抵", "用〔a〕抵", "用〔𠀋𠀋𠀋〕抵"]) {
      const { head, tail } = waiveRuns(s);
      expect(head + tail).toBe(s);
    }
    expect(waiveRuns("用〔𠀋𠀋𠀋〕抵").tail).toBe("𠀋𠀋〕抵");
  });
  it("接線：小鈕與看不見的同字都畫 WaiveText（同一套斷行）；尾巴用不斷行的 .world-sol-glue", () => {
    const tile = readFile(SRC_DIR, "world/SolutionTile.tsx");
    expect(tile.match(/<WaiveText label=\{waive\} \/>/g)?.length).toBe(2);
    expect(tile).toContain('<span className="world-sol-glue">{tail}</span>');
    expect(readFile(SRC_DIR, "world/story.css")).toMatch(/\.world-sol-glue \{\s*white-space: nowrap;/);
  });
});
