import { describe, expect, it } from "vitest";
import type { ActivationView, SkillCard } from "../api/types";
import { activationLine, activationRemaining, activeReason } from "./activations";
import { skillButtons } from "./targeting";
import { smallView, unit } from "./testFixtures";

const timed: ActivationView = {
  skill_id: "skill_war_avatar",
  name_zh: "戰神降臨",
  activation: "timed",
  expires_round: 4,
  rule_name_zh: null,
};
const battle: ActivationView = {
  skill_id: "skill_kindred_flame",
  name_zh: "慈焰誓約",
  activation: "battle",
  expires_round: null,
  rule_name_zh: "慈焰",
};

describe("lasting legendaries (3D-6)", () => {
  it("counts the rounds left for a timed activation and says 整場 for a battle one", () => {
    const view = smallView({ round: 2 });
    expect(activationRemaining(view, timed)).toBe(2);
    expect(activationRemaining(view, battle)).toBeNull();
    expect(activationLine(view, timed)).toBe("戰神降臨：剩 2 輪（第 4 輪你的回合開始時結束）");
    expect(activationLine(view, battle)).toBe("慈焰誓約（規則改變「慈焰」）：整場");
  });

  it("disables the skill button of an active legendary and keeps the others", () => {
    const hero = unit("unit_0001", "ally", 0, 0, {
      skills: ["skill_war_avatar", "skill_other"],
      activations: [timed],
    });
    expect(activeReason(hero, "skill_war_avatar")).toBe("已啟動（到第 4 輪你的回合開始）");
    expect(activeReason(hero, "skill_other")).toBeNull();
    const card = { name_zh: "戰神降臨", ap_cost: 1, cost: ["AP 1", "源力 1"], source_cost: 1, activation_id: "timed" };
    const [avatar] = skillButtons(hero, [], { skill_war_avatar: card as unknown as SkillCard });
    expect(avatar?.disabledReason).toBe("已啟動（到第 4 輪你的回合開始）");
    expect(avatar?.costs).toEqual(["AP 1", "源力 1", "傳說啟動"]);
  });
});
