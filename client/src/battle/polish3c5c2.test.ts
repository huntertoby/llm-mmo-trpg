// Phase 3-5c-2 介面小修：灰掉技能的原因、戰場圖例、試玩前的法力比對、Boss 地圖選項。
import { describe, expect, it } from "vitest";
import type { Action, SkillCard, WorkshopCheck } from "../api/types";
import { manaNote } from "../workshop/tryout";
import { cssColor, legendEntries } from "./legend";
import { HIGHLIGHT } from "./glossary";
import { blockedMessage, withReasons } from "./skillReasons";
import { GENERIC_REASON, buildTargets, skillButtons, type ActionMode } from "./targeting";
import { unit } from "./testFixtures";

const H = "unit_0001";
const hero = unit(H, "ally", 1, 1, { skills: ["slash", "blast", "ward", "nova"], cooldowns: { nova: 2 } });
const legal: Action[] = [{ type: "use_skill", unit_id: H, skill_id: "slash", target_id: "x" } as Action];
const card = (id: string, name: string): SkillCard => ({ id, name_zh: name, cost: [] }) as unknown as SkillCard;
const cards = { slash: card("slash", "斬擊"), blast: card("blast", "爆裂"), ward: card("ward", "護盾"), nova: card("nova", "新星") };

describe("gray skill reasons (3-5c-2)", () => {
  const buttons = skillButtons(hero, legal, cards);

  it("replaces only the generic reason with the server's reason", () => {
    const shown = withReasons(buttons, { blast: "視線被阻擋：主角 看不到 木樁", ward: "法力不足：需要 8，剩餘 0", nova: "不該蓋掉冷卻" });
    const byId = Object.fromEntries(shown.map((b) => [b.skillId, b.disabledReason]));
    expect(byId["slash"]).toBeNull(); // 可以用的不動
    expect(byId["blast"]).toBe("視線被阻擋：主角 看不到 木樁");
    expect(byId["ward"]).toBe("法力不足：需要 8，剩餘 0");
    expect(byId["nova"]).toContain("冷卻中（剩 2 回合）"); // 本地端有具體原因就保留
  });

  it("keeps the generic text until the server answers, and ignores unknown skills", () => {
    expect(withReasons(buttons, null).find((b) => b.skillId === "blast")?.disabledReason).toBe(GENERIC_REASON);
    expect(withReasons(buttons, { other: "x" }).find((b) => b.skillId === "ward")?.disabledReason).toBe(GENERIC_REASON);
  });

  it("builds the message for a click on a gray skill and none for a usable one", () => {
    const shown = withReasons(buttons, { blast: "視線被阻擋：主角 看不到 木樁" });
    expect(blockedMessage(shown.find((b) => b.skillId === "blast")!)).toBe("爆裂不能用：視線被阻擋：主角 看不到 木樁");
    expect(blockedMessage(shown.find((b) => b.skillId === "slash")!)).toBeNull();
  });
});

describe("battlefield legend (3-5c-2)", () => {
  const composite = { targets: { ...buildTargets([]), composite: {} } } as unknown as ActionMode;

  it("explains purple as the second stage when a composite preview is on screen", () => {
    const entries = legendEntries([{ pos: { x: 1, y: 1 }, kind: "followup_area", label: "" }], null);
    expect(entries.map((e) => e.color)).toContain(HIGHLIGHT.followup);
    expect(entries.find((e) => e.color === HIGHLIGHT.followup)?.label).toContain("第二段");
  });

  it("shows during the two-step pick and stays hidden otherwise", () => {
    expect(legendEntries([], composite)).not.toHaveLength(0);
    expect(legendEntries([], null)).toEqual([]);
    expect(legendEntries([{ pos: { x: 1, y: 1 }, kind: "route", label: "" }], null)).toEqual([]);
  });

  it("formats colors as css", () => {
    expect(cssColor(HIGHLIGHT.followup)).toBe("#c77dff");
    expect(cssColor(0x0000ff)).toBe("#0000ff");
  });
});

describe("tryout mana note with the build's mana limit (3-5c-2)", () => {
  const withMana = { skill: { cost: { mana: 8 } } } as unknown as WorkshopCheck;
  it("compares against max_mana when known", () => {
    expect(manaNote(withMana, 3)).toContain("法力上限 3，技能需要 8");
    expect(manaNote(withMana, 3)).toContain("放不出來");
    expect(manaNote(withMana, 8)).toContain("夠用");
    expect(manaNote(withMana)).toContain("8 點法力");
    expect(manaNote({ skill: {} } as unknown as WorkshopCheck, 3)).toBeNull();
  });
});
