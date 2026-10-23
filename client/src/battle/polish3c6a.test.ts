// Phase 3C-6a：源力圖示與傳說成本、技能種類字樣、源泉格與被揭露的陷阱、殘影分身的剩餘輪數、環境預告的炸彈不重複。
import { describe, expect, it } from "vitest";
import type { TelegraphChange, TelegraphOut } from "../api/types";
import { buildDrawModel } from "./drawModel";
import { categoryLabel, kindLabel, sourceCostText, sourcePips } from "./source";
import { remainingRounds } from "./summons";
import { telegraphLines, telegraphMarks } from "./telegraph";
import { smallView, unit } from "./testFixtures";

describe("source pips", () => {
  it("fills the first N of max pips and clamps", () => {
    expect(sourcePips(2, 3)).toEqual([true, true, false]);
    expect(sourcePips(0, 3)).toEqual([false, false, false]);
    expect(sourcePips(5, 3)).toEqual([true, true, true]);
    expect(sourcePips(-1, 3)).toEqual([false, false, false]);
  });

  it("writes the legendary source cost as filled pips", () => {
    expect(sourceCostText({ source_cost: 2 }, 3)).toBe("源力 2　●●○");
    expect(sourceCostText({ source_cost: 1 }, 3)).toBe("源力 1　●○○");
    expect(sourceCostText({ source_cost: null }, 3)).toBeNull();
    expect(sourceCostText({ source_cost: 0 }, 3)).toBeNull();
  });

  it("labels modifier skills as 改造／修正", () => {
    expect(kindLabel({ kind: "修正", kind_id: "modifier", modifiers: [] })).toBe("修正（改造／修正）");
    expect(kindLabel({ kind: "主動", kind_id: "active", modifiers: [] })).toBe("主動");
    // 3-48：卡片標題標示武器技／法術技
    expect(categoryLabel({ category_id: "spell", kind_id: "active" })).toBe("法術技・花法力");
    expect(categoryLabel({ category_id: "weapon", kind_id: "active" })).toBe("武器技・花耐力・看手上武器");
    expect(categoryLabel({ category_id: "spell", kind_id: "passive" })).toBe("法術技");
    expect(categoryLabel({ category_id: "weapon", kind_id: "modifier" })).toBe("武器技・看手上武器");
  });
});

describe("source wells and revealed traps on the canvas", () => {
  it("draws every source well", () => {
    const view = smallView({ source_wells: [{ x: 2, y: 2 }, { x: 3, y: 2 }] });
    expect(buildDrawModel(view, "unit_0001").wells).toEqual([
      { x: 2, y: 2 },
      { x: 3, y: 2 },
    ]);
    expect(buildDrawModel(smallView(), "unit_0001").wells).toEqual([]);
  });

  it("marks an enemy trap that was revealed differently from our own", () => {
    const view = smallView({
      traps: [
        { owner_id: "unit_0001", team: "ally", pos: { x: 1, y: 1 }, skill_id: "trap", remaining: 3 },
        { owner_id: "unit_0003", team: "enemy", pos: { x: 2, y: 2 }, skill_id: "trap", remaining: 2 },
      ],
    });
    const traps = buildDrawModel(view, "unit_0001").traps;
    expect(traps.map((t) => t.revealed)).toEqual([false, true]);
    expect(traps[0]?.color).not.toBe(traps[1]?.color);
  });
});

describe("orphan clone remaining rounds", () => {
  // 第 2 輪；召喚者 unit_0002 已倒下，留下分身 unit_0006（到第 3 輪環境回合消失）。
  function view(activeId: string, order: string[]) {
    const base = smallView({ round: 2, active_unit: activeId, turn_order: order });
    const clone = unit("unit_0006", "ally", 0, 1, { owner_id: "unit_0002", summon_expires_round: 3 });
    return { ...base, units: [...base.units, clone] };
  }

  it("does not count this round once the clone's slot has passed", () => {
    const passed = view("unit_0004", ["unit_0001", "unit_0006", "unit_0003", "unit_0004"]);
    const clone = passed.units.find((u) => u.id === "unit_0006");
    expect(remainingRounds(passed, clone!)).toBe(1);
  });

  it("counts this round while the clone still has a turn coming", () => {
    const coming = view("unit_0001", ["unit_0001", "unit_0006", "unit_0003", "unit_0004"]);
    const clone = coming.units.find((u) => u.id === "unit_0006");
    expect(remainingRounds(coming, clone!)).toBe(2);
  });

  it("keeps the plain summon formula when the owner is alive", () => {
    const base = smallView({ round: 2 });
    const skeleton = unit("unit_0007", "ally", 1, 0, { owner_id: "unit_0001", summon_expires_round: 3 });
    expect(remainingRounds({ ...base, units: [...base.units, skeleton] }, skeleton)).toBe(2);
  });
});

describe("telegraph bombs", () => {
  const change = (kind: string, text: string, over: Partial<TelegraphChange> = {}): TelegraphChange =>
    ({ kind, pos: null, before: null, after: null, object_id: null, unit_id: null, amount: null, text, ...over }) as TelegraphChange;
  const bomb = (explodes: boolean) => ({
    unit_id: "unit_0003",
    pos: { x: 2, y: 1 },
    remaining: explodes ? 1 : 2,
    radius: 1,
    tiles: [{ x: 2, y: 1 }],
    explodes,
    text: "盜賊 身上的定時炸彈",
  });
  const forecast = (explodes: boolean): TelegraphOut => ({
    round: 1,
    changes: explodes
      ? [change("bomb_exploded", "盜賊 身上的定時炸彈將在 (2, 1) 爆炸", { unit_id: "unit_0003", pos: { x: 2, y: 1 }, tiles: [{ x: 2, y: 1 }] })]
      : [],
    burning: [],
    upcoming: [],
    bombs: [bomb(explodes)],
    charges: [],
  });

  it("lists a bomb that explodes next round once", () => {
    expect(telegraphLines(forecast(true))).toHaveLength(1);
    const marks = telegraphMarks(forecast(true), smallView());
    expect(marks.every((m) => m.texts.length === 1)).toBe(true);
  });

  it("still lists a bomb that has more rounds to go", () => {
    expect(telegraphLines(forecast(false))).toEqual(["盜賊 身上的定時炸彈"]);
  });
});
