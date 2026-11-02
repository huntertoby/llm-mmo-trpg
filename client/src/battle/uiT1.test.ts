// UI-T1 試玩小修的回歸測試。
import { describe, expect, it } from "vitest";
import { skeletonLabel } from "./source";

describe("skeletonLabel（技能卡標題不重複種類字樣）", () => {
  it("骨架名與種類相同或以種類開頭時不顯示", () => {
    expect(skeletonLabel({ kind: "被動", skeleton_zh: "被動" })).toBe("");
    expect(skeletonLabel({ kind: "姿態", skeleton_zh: "姿態" })).toBe("");
    expect(skeletonLabel({ kind: "修正", skeleton_zh: "修正" })).toBe("");
    expect(skeletonLabel({ kind: "反應", skeleton_zh: "反應技" })).toBe("");
  });

  it("主動技能的骨架名照常顯示", () => {
    expect(skeletonLabel({ kind: "主動", skeleton_zh: "單體打擊" })).toBe("單體打擊");
    expect(skeletonLabel({ kind: "主動", skeleton_zh: "" })).toBe("");  });
});
