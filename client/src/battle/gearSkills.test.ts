// Phase 3G-G3b：裝備授予的技能與反應——技能列與反應設定的「來自裝備」。
import { describe, expect, it } from "vitest";
import type { Action, GearSkillView, ReactionRuleView } from "../api/types";
import { gearSkillBadge, gearSkillSource, gearSkillsOf } from "./gearSkills";
import { gearSourceText } from "./reactions";
import { skillButtons } from "./targeting";
import { unit } from "./testFixtures";

const grapple: GearSkillView = {
  skill_id: "skill_gear_grapple",
  name_zh: "鉤爪",
  affix_id: "affix_act_grapple",
  slot: "hands",
  slot_zh: "手",
  item_name_zh: "鉤爪護手",
};

const hero = unit("unit_0001", "ally", 1, 1, {
  skills: ["skill_bone_crusher", "skill_gear_grapple"],
  gear_skills: [grapple],
});

describe("gear granted skills", () => {
  it("names the equipment source of a granted skill and nothing else", () => {
    expect(gearSkillsOf(hero)).toHaveLength(1);
    expect(gearSkillSource(hero, "skill_gear_grapple")).toBe("手：鉤爪護手");
    expect(gearSkillSource(hero, "skill_bone_crusher")).toBeNull();
    expect(gearSkillBadge("手：鉤爪護手")).toBe("來自裝備・手：鉤爪護手");
  });

  it("marks only the granted skill on the skill bar buttons", () => {
    const legal = [
      { type: "use_skill", unit_id: "unit_0001", skill_id: "skill_gear_grapple", target_id: "unit_0002" } as Action,
    ];
    const buttons = skillButtons(hero, legal, {});
    expect(buttons.map((b) => [b.skillId, b.gearSource])).toEqual([
      ["skill_bone_crusher", null],
      ["skill_gear_grapple", "手：鉤爪護手"],
    ]);
    // 卸下裝備後伺服器不再列出 gear_skills 與技能：按鈕跟著消失
    const bare = unit("unit_0001", "ally", 1, 1, { skills: ["skill_bone_crusher"] });
    expect(skillButtons(bare, [], {}).map((b) => b.skillId)).toEqual(["skill_bone_crusher"]);
  });

  it("shows where a reaction rule comes from", () => {
    const rule = { gear_source_zh: "壁壘塔盾：被遠程攻擊時也可以格擋" } as ReactionRuleView;
    expect(gearSourceText(rule)).toBe("來自裝備・壁壘塔盾：被遠程攻擊時也可以格擋");
    expect(gearSourceText({ gear_source_zh: "" })).toBe("");
  });
});
