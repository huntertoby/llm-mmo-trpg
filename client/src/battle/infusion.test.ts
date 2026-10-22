// 召喚物的灌注關鍵字（Phase 3-33b）：什麼時候問、帶上選擇、單位資訊的名稱。
import { describe, expect, it } from "vitest";
import type { Action, SkillCard, UnitView } from "../api/types";
import { infusionChoices, infusionName, infusionPromptText, isSummonCard, withInfusion } from "./infusion";

const opt = (id: string, name: string) => ({ id, name_zh: name, effect_zh: `${name}的效果` });
const caster = (options: ReturnType<typeof opt>[]) =>
  ({ id: "unit_0001", infusion_options: options }) as unknown as UnitView;
const card = (summon: boolean) =>
  ({ keywords: { makes: summon ? [{ id: "summon", name_zh: "召喚" }] : [], uses: [] } }) as unknown as SkillCard;
const cast = (skill: string, extra: object = {}): Action =>
  ({ type: "use_skill", unit_id: "unit_0001", skill_id: skill, target_pos: { x: 2, y: 3 }, ...extra }) as Action;
const two = [opt("ignite", "點燃"), opt("collision", "碰撞")];

describe("infusionChoices", () => {
  it("asks for a summon skill when two or more keywords are available", () => {
    expect(infusionChoices(caster(two), cast("raise"), { raise: card(true) })).toEqual(two);
  });
  it("does not ask for a single option, a plain skill, or a chosen infusion", () => {
    expect(infusionChoices(caster([two[0]!]), cast("raise"), { raise: card(true) })).toEqual([]);
    expect(infusionChoices(caster(two), cast("bolt"), { bolt: card(false) })).toEqual([]);
    expect(infusionChoices(caster(two), cast("raise", { infusion: "ignite" }), { raise: card(true) })).toEqual([]);
    expect(infusionChoices(caster(two), cast("raise"), {})).toEqual([]); // 卡片還沒載入
    expect(infusionChoices(null, cast("raise"), { raise: card(true) })).toEqual([]);
    expect(infusionChoices(caster(two), { type: "end_turn", unit_id: "unit_0001" } as Action, {})).toEqual([]);
  });
});

describe("helpers", () => {
  it("recognises summon cards", () => {
    expect(isSummonCard(card(true))).toBe(true);
    expect(isSummonCard(card(false))).toBe(false);
    expect(isSummonCard(undefined)).toBe(false);
  });
  it("adds the chosen keyword to a use_skill action only", () => {
    expect(withInfusion(cast("raise"), "ignite")).toMatchObject({ infusion: "ignite", skill_id: "raise" });
    const end = { type: "end_turn", unit_id: "unit_0001" } as Action;
    expect(withInfusion(end, "ignite")).toBe(end);
  });
  it("names the infusion of a summon from its owner", () => {
    const summon = { infusion: "ignite" } as unknown as UnitView;
    expect(infusionName(summon, caster(two))).toBe("點燃");
    expect(infusionName(summon, null)).toBe("ignite");
    expect(infusionName({ infusion: null } as unknown as UnitView, caster(two))).toBeNull();
  });
  it("words the prompt", () => {
    expect(infusionPromptText("喚起骷髏", 2)).toContain("喚起骷髏");
  });
});
