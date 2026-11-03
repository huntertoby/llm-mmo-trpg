// Phase 5A-M1b：單位卡的「特性」欄
import { describe, expect, it } from "vitest";
import { unit } from "../battle/testFixtures";
import { traitRows } from "./UnitInfo";

describe("traitRows", () => {
  it("沒有特性時不列", () => {
    expect(traitRows(unit("unit_0002", "enemy", 1, 1))).toEqual([]);
  });

  it("有特性時列成一個「特性」列，每項一行", () => {
    const u = unit("unit_0002", "enemy", 1, 1, {
      traits_zh: ["反應「同門相護」：2 格內的同門被攻擊命中時加護盾。", "開場狀態「碎晶」：倒下時留下導電的水。"],
    });
    const rows = traitRows(u);
    expect(rows).toHaveLength(1);
    expect(rows[0]?.[0]).toBe("特性");
  });
});
