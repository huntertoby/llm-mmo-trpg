import { describe, expect, it } from "vitest";
import type { Action, PreviewOut } from "../api/types";
import { buildDrawModel } from "./drawModel";
import { backTile, facingArrow, facingText } from "./facing";
import { previewOverlays, sceneLines } from "./scenePreview";
import { hurlPromptText, skillMode, type SkillButton } from "./targeting";
import { smallView, unit } from "./testFixtures";
import { unitNames } from "./units";

// 朝向與瞬步（Phase 3D-8d）
describe("朝向", () => {
  it("背後格是朝向的反方向，單位資訊寫出朝向與背後格", () => {
    expect(backTile({ x: 3, y: 3 }, "west")).toEqual({ x: 4, y: 3 });
    expect(backTile({ x: 3, y: 3 }, "north")).toEqual({ x: 3, y: 4 });
    expect(facingText({ pos: { x: 3, y: 3 }, facing: "east" })).toBe("東 →（背後 (2, 3)）");
  });

  it("箭頭的尖端在朝向那一側、底邊兩點對稱", () => {
    const [tx, ty, ax, ay, bx, by] = facingArrow("east", 10, 4);
    expect([tx, ty]).toEqual([14, 0]);
    expect(ax).toBe(bx);
    expect(ay).toBe(-(by ?? 0));
    const [, northTip] = facingArrow("north", 10, 4);
    expect(northTip).toBe(-14);
  });

  it("繪製模型帶著每個單位的朝向", () => {
    const view = smallView({
      units: [unit("unit_0001", "ally", 0, 0, { facing: "south" }), unit("unit_0003", "enemy", 2, 1, { facing: "west" })],
    });
    const model = buildDrawModel(view, "unit_0001");
    expect(Object.fromEntries(model.units.map((u) => [u.id, u.facing]))).toEqual({ unit_0001: "south", unit_0003: "west" });
  });
});

describe("一般瞬步（兩段選取）", () => {
  const pair = (target: string, x: number, y: number): Action =>
    ({ type: "use_skill", unit_id: "unit_0001", skill_id: "skill_shadow_ambush", target_id: target, target_pos: { x, y } }) as Action;
  const button = (effectIds: string[]): SkillButton => ({
    skillId: "skill_shadow_ambush",
    name: "暗影突襲",
    costs: [],
    cooldown: 0,
    actions: [pair("unit_0003", 2, 2), pair("unit_0003", 3, 1)],
    disabledReason: null,
    effectIds,
  });

  it("有 shadowstep 效果的「單位 → 落點」技能是瞬步，不是傳送他人", () => {
    expect(skillMode(button(["shadowstep", "damage"])).targets.pairKind).toBe("shadowstep");
    expect(skillMode(button(["teleport_target"])).targets.pairKind).toBe("teleport");
  });

  it("提示文字：先選敵人，再選落在他身旁哪一格", () => {
    expect(hurlPromptText(null, 0, 2, "shadowstep")).toContain("要瞬步過去的敵人");
    const second = hurlPromptText("盜賊1", 4, 2, "shadowstep");
    expect(second).toContain("已鎖定盜賊1");
    expect(second).toContain("背後可以背刺");
  });

  it("預覽：落點標「瞬」、文字寫出瞬步", () => {
    const view = smallView();
    const p = {
      action: { type: "end_turn", unit_id: "unit_0001" },
      notes: ["背刺 盜賊：命中 +2、暴擊範圍 +1（從背後近戰攻擊）"],
      moves: [{ kind: "shadowstep", unit_id: "unit_0001", other_id: null, path: [[0, 0], [3, 1]] }],
      backstab: ["unit_0003"],
    } as unknown as PreviewOut;
    expect(previewOverlays(p, view).filter((o) => o.label === "瞬").map((o) => [o.pos.x, o.pos.y])).toEqual([[3, 1]]);
    expect(sceneLines(p, unitNames(view), view).join("\n")).toContain("瞬步：");
  });
});
