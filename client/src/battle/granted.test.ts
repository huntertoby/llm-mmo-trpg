import { describe, expect, it } from "vitest";
import type { PreviewOut, UnitView } from "../api/types";
import { grantedBadge, grantedLine, grantedOf, grantedRemaining, grantLines } from "./granted";
import { skillButtons } from "./targeting";
import { unit } from "./testFixtures";
import { unitNames } from "./units";

const winged = (over: Partial<UnitView> = {}): UnitView =>
  unit("unit_0001", "ally", 1, 1, {
    skills: ["skill_wing_spread"],
    granted_skills: [{ skill_id: "skill_flight", name_zh: "飛行", remaining: 3 }],
    ...over,
  });

describe("暫時獲得的技能", () => {
  it("取出暫時技能與剩餘輪數", () => {
    const hero = winged();
    expect(grantedOf(hero)).toHaveLength(1);
    expect(grantedRemaining(hero, "skill_flight")).toBe(3);
    expect(grantedRemaining(hero, "skill_wing_spread")).toBeNull();
    expect(grantedOf(winged({ granted_skills: [] }))).toEqual([]);
  });

  it("標記與 HUD 文字", () => {
    expect(grantedBadge(3)).toBe("暫時・剩 3 輪");
    expect(grantedLine({ skill_id: "skill_flight", name_zh: "飛行", remaining: 2 })).toBe("飛行 剩 2 輪");
  });

  it("技能列：裝備的技能在前，暫時技能接在後面並帶剩餘輪數", () => {
    const hero = winged();
    const legal = [
      { type: "use_skill", unit_id: "unit_0001", skill_id: "skill_flight", target_pos: { x: 2, y: 1 } },
    ] as never[];
    const buttons = skillButtons(hero, legal, {});
    expect(buttons.map((b) => [b.skillId, b.grantedRemaining])).toEqual([
      ["skill_wing_spread", null],
      ["skill_flight", 3],
    ]);
    expect(buttons[1]?.disabledReason).toBeNull(); // 有合法動作
    expect(buttons[0]?.disabledReason).not.toBeNull(); // 展翼沒有合法動作
  });

  it("預覽的說明：獲得與刷新", () => {
    const names = unitNames({ units: [winged()] } as never);
    const preview = (refreshed: boolean) =>
      ({ grants: [{ unit_id: "unit_0001", skill_id: "skill_flight", name_zh: "飛行", duration: 3, refreshed }] }) as PreviewOut;
    expect(grantLines(preview(false), names)[0]).toContain("暫時獲得技能「飛行」3 輪");
    expect(grantLines(preview(true), names)[0]).toContain("刷新為 3 輪");
    expect(grantLines({ grants: [] } as unknown as PreviewOut, names)).toEqual([]);
  });
});
