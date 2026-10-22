import { describe, expect, it } from "vitest";
import type { RunHero, SkillCard } from "../api/types";
import { pickChoice } from "./flow";
import {
  adjustLevel,
  canEquip,
  canLower,
  canRaise,
  draftCost,
  draftLevel,
  draftLevels,
  growthLines,
  hasDraft,
  levelBadge,
  levelOf,
  loadoutChanged,
  loadoutChoice,
  loadoutUsage,
  pointsLeft,
  spendChoice,
} from "./skillGrowth";

function card(id: string, kind_id: string, level: number | null = 1): SkillCard {
  const growth =
    level === null
      ? null
      : {
          level,
          max_level: 5,
          bonus_permille: 0,
          current_text: `Lv.${level}：傷害、治療、護盾 +${level >= 4 ? 20 : level >= 2 ? 10 : 0}%`,
          next_level: level < 5 ? level + 1 : null,
          next_text: level < 5 ? `Lv.${level + 1}：效果 +10%` : null,
          trait: "cooldown",
          trait_text: "5 級小特性：冷卻 −1 回合",
          trait_active: level >= 5,
          cost: 1,
        };
  return { id, name_zh: id, kind_id, kind: kind_id, growth } as unknown as SkillCard;
}

function hero(points: number, skills: SkillCard[], bench: SkillCard[] = []): RunHero {
  return {
    level: 3,
    skill_points: points,
    skill_growth: { max_level: 5, upgrade_cost: 1, points_per_level: 2, trait_level: 5, evolve_level: 3 },
    skills,
    bench,
  } as unknown as RunHero;
}

describe("技能點分配草稿", () => {
  const a = card("skill_a", "active", 1);
  const b = card("skill_b", "active", 4);
  const passive = card("skill_p", "passive", null);
  const h = hero(3, [a, b, passive]);

  it("等級標籤與沒有成長資料的技能", () => {
    expect(levelBadge(3)).toBe("Lv.3");
    expect(levelOf(passive)).toBe(1);
    expect(canRaise(h, passive, {})).toBe(false);
  });

  it("加一級花 1 點，不能超過剩下的點數與最高等級", () => {
    let draft = adjustLevel(h, a, {}, 1);
    expect(draft).toEqual({ skill_a: 2 });
    expect(draftLevel(a, draft)).toBe(2);
    draft = adjustLevel(h, a, draft, 1);
    draft = adjustLevel(h, a, draft, 1);
    expect(draft).toEqual({ skill_a: 4 });
    expect(pointsLeft(h, draft)).toBe(0);
    expect(canRaise(h, a, draft)).toBe(false);
    expect(adjustLevel(h, a, draft, 1)).toBe(draft); // 沒有點數了
    expect(draftCost(h, draft)).toBe(3);
  });

  it("滿級的技能不能再加；草稿不能降到目前等級以下", () => {
    const full = hero(9, [card("skill_f", "active", 5)]);
    expect(canRaise(full, full.skills[0] as SkillCard, {})).toBe(false);
    expect(canLower(a, {})).toBe(false);
    const draft = adjustLevel(h, a, {}, 1);
    expect(canLower(a, draft)).toBe(true);
    expect(adjustLevel(h, a, draft, -1)).toEqual({}); // 降回目前等級就從草稿拿掉
    expect(hasDraft({})).toBe(false);
  });

  it("送出的請求：技能 ID 排序，只放要升的", () => {
    expect(draftLevels({ skill_b: 5, skill_a: 2 })).toEqual({ skill_a: 2, skill_b: 5 });
    expect(Object.keys(draftLevels({ skill_b: 5, skill_a: 2 }))).toEqual(["skill_a", "skill_b"]);
    expect(spendChoice({ skill_a: 3 })).toEqual({ kind: "spend", levels: { skill_a: 3 } });
  });

  it("升級的選擇帶著草稿；沒有草稿就不帶 levels", () => {
    const view = { screen: "level_up", level: 2, points: 2, offer: {} } as never;
    expect(pickChoice(view, { str: 2 }, null, null)).toEqual({
      kind: "level_up",
      attributes: { str: 2 },
      pick: null,
      replace: null,
    });
    expect(pickChoice(view, { str: 2 }, null, null, { skill_a: 3 })).toEqual({
      kind: "level_up",
      attributes: { str: 2 },
      pick: null,
      replace: null,
      levels: { skill_a: 3 },
    });
  });

  it("技能卡的等級說明：目前、下一級、小特性", () => {
    expect(growthLines(a)).toEqual([
      "Lv.1：傷害、治療、護盾 +0%",
      "下一級　Lv.2：效果 +10%",
      "5 級小特性：冷卻 −1 回合",
    ]);
    expect(growthLines(card("skill_m", "active", 5))).toEqual([
      "Lv.5：傷害、治療、護盾 +20%",
      "5 級小特性：冷卻 −1 回合",
    ]);
    expect(growthLines(passive)).toEqual([]);
  });
});

describe("營火換裝", () => {
  const act = ["a1", "a2", "a3", "a4", "a5", "a6"].map((id) => card(id, "active", 3));
  const spare = card("spare", "active", 5);
  const react = card("r1", "reaction", null);
  const h = hero(0, [...act, react], [spare]);
  const ids = h.skills.map((s) => s.id);

  it("欄位滿了不能裝，卸下一個才能裝（等級保留）", () => {
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
