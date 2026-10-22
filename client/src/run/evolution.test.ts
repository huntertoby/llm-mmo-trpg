import { describe, expect, it } from "vitest";
import type { RunHero, SkillCard } from "../api/types";
import { pickChoice, type RunView } from "./flow";
import {
  canRaise,
  crossesEvolution,
  draftEvolve,
  evolutionOptions,
  evolveBlocked,
  growthLines,
  missingEvolutions,
  raiseBlockedText,
  spendChoice,
} from "./skillGrowth";

function card(id: string, level: number, uses: number, evolvedFrom: string | null = null): SkillCard {
  return {
    id,
    name_zh: id,
    kind_id: "active",
    growth: {
      level,
      max_level: 5,
      bonus_permille: 0,
      current_text: `Lv.${level}`,
      next_level: level + 1,
      next_text: `Lv.${level + 1}`,
      trait: null,
      trait_text: "",
      trait_active: false,
      cost: 1,
      uses,
      evolve_uses: 3,
      evolved_from_zh: evolvedFrom,
      blocked_text: null,
    },
  } as unknown as SkillCard;
}

const OPTION = (index: number, branch: "deepen" | "bridge") => ({
  index,
  branch,
  label_zh: branch === "deepen" ? "加深" : "橋接",
  template: "t",
  keyword: null,
  summary_zh: "s",
  fallback: false,
  card: card(`evo_${index}`, 1, 0),
});

function hero(points: number, skills: SkillCard[]): RunHero {
  return {
    skill_points: points,
    skill_growth: {
      max_level: 5,
      upgrade_cost: 1,
      points_per_level: 2,
      trait_level: 5,
      evolve_level: 3,
      evolve_uses: 3,
    },
    skills,
    bench: [],
    evolutions: [{ skill_id: "a", name_zh: "a", options: [OPTION(0, "deepen"), OPTION(1, "bridge")] }],
  } as unknown as RunHero;
}

describe("分歧進化的門檻", () => {
  it("用過的次數不夠時不能升到 3 級，並說明原因", () => {
    const rare = card("b", 2, 1);
    const h = hero(4, [rare]);
    expect(evolveBlocked(h, rare, 3)).toBe(true);
    expect(canRaise(h, rare, {})).toBe(false);
    expect(raiseBlockedText(h, rare, {})).toContain("用過 3 次");
    // 2 級不受門檻影響
    const low = card("c", 1, 0);
    expect(canRaise(hero(4, [low]), low, {})).toBe(true);
    expect(canRaise(hero(4, [low]), low, { c: 2 })).toBe(false);
  });

  it("已進化的技能再升過 3 級不會再進化", () => {
    const evolved = card("e", 1, 0, "火焰箭");
    expect(crossesEvolution(hero(4, [evolved]), evolved, 3)).toBe(false);
    expect(canRaise(hero(4, [evolved]), evolved, { e: 2 })).toBe(true);
    expect(growthLines(evolved)).toContain("進化自　火焰箭");
  });
});

describe("分歧進化的二選一", () => {
  it("草稿升到 3 級才出現兩支，選了才算完成", () => {
    const a = card("a", 2, 3);
    const h = hero(4, [a]);
    expect(evolutionOptions(h, a, {})).toEqual([]);
    expect(evolutionOptions(h, a, { a: 3 }).map((o) => o.label_zh)).toEqual(["加深", "橋接"]);
    expect(missingEvolutions(h, { a: 3 }, {})).toEqual(["a"]);
    expect(missingEvolutions(h, { a: 3 }, { a: 1 })).toEqual([]);
    // 退回 2 級時，之前的選擇不會送出
    expect(draftEvolve(h, {}, { a: 1 })).toEqual({});
    expect(draftEvolve(h, { a: 3 }, { a: 1 })).toEqual({ a: 1 });
  });

  it("送出的選擇帶 evolve", () => {
    expect(spendChoice({ a: 3 }, { a: 0 })).toEqual({ kind: "spend", levels: { a: 3 }, evolve: { a: 0 } });
    expect(spendChoice({ a: 2 })).toEqual({ kind: "spend", levels: { a: 2 } });
    const view = { screen: "level_up", points: 2, level: 3 } as unknown as RunView;
    expect(pickChoice(view, {}, null, null, { a: 3 }, { a: 1 })).toMatchObject({
      kind: "level_up",
      levels: { a: 3 },
      evolve: { a: 1 },
    });
  });
});
