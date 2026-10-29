import { describe, expect, it } from "vitest";
import type { RunHero, SkillCard } from "../api/types";
import { canEquip, loadoutChanged, loadoutChoice, loadoutUsage } from "./loadout";

function card(id: string, kind_id: string): SkillCard {
  return { id, name_zh: id, kind_id, kind: kind_id } as unknown as SkillCard;
}

function hero(skills: SkillCard[], bench: SkillCard[] = []): RunHero {
  return { level: 3, insight: 0, skills, bench } as unknown as RunHero;
}

describe("營火換裝", () => {
  const act = ["a1", "a2", "a3", "a4", "a5", "a6"].map((id) => card(id, "active"));
  const spare = card("spare", "active");
  const react = card("r1", "reaction");
  const h = hero([...act, react], [spare]);
  const ids = h.skills.map((s) => s.id);

  it("欄位滿了不能裝，卸下一個才能裝", () => {
    expect(loadoutUsage(h, ids).active).toBe(6);
    expect(canEquip(h, ids, "spare")).toBe(false);
    const fewer = ids.filter((x) => x !== "a1");
    expect(canEquip(h, fewer, "spare")).toBe(true);
    expect(canEquip(h, fewer, "a1")).toBe(true); // 卸下的技能也在備用裡可以裝回
    expect(canEquip(h, ids, "a1")).toBe(false); // 已經裝備
    expect(canEquip(h, ids, "nobody")).toBe(false);
  });

  it("有改動才能套用；請求帶完整清單", () => {
    expect(loadoutChanged(h, ids)).toBe(false);
    const next = [...ids.filter((x) => x !== "a1"), "spare"];
    expect(loadoutChanged(h, next)).toBe(true);
    expect(loadoutChoice(next)).toEqual({ kind: "loadout", skills: next });
  });
});
