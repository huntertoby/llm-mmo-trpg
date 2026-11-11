// 大世界成長畫面的純函式（Phase 5A-7）。
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { choiceLabel, defaultParams, growthBadge, leftPane, oathButton, paramLabel, spendLock, swearAction, worldActionOf } from "./growth";

type Over = {
  growth?: Partial<WorldView["growth"]>;
  oath?: Partial<WorldView["oath"]>;
  points?: number;
  pending?: boolean;
};

/** 測試只用到的欄位（其他欄位不讀）。 */
function view({ growth = {}, oath = {}, points = 0, pending = false }: Over = {}): WorldView {
  return {
    character: { attribute_points: points },
    pending_flash: pending ? { skill_id: "skill_a", nth: 1, slot: null, category: null, major: false, cost: 1, options: [] } : null,
    growth: {
      insight: 0,
      skill_tier: 1,
      at_service: true,
      service_zh: "閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）",
      can_allocate: false,
      can_spend: true,
      blocked_zh: null,
      pending,
      can_flash: true,
      flash_blocked_zh: null,
      ...growth,
    },
    oath: {
      available: false,
      unavailable_zh: "尚未開放",
      current: null,
      cooldown_until: 0,
      cooldown_zh: null,
      can_swear: false,
      swear_problem_zh: "尚未開放",
      can_release: false,
      templates: [],
      ...oath,
    },
  } as unknown as WorldView;
}

describe("一輪的選擇轉成世界動作", () => {
  it("配點、重配、閃現、選、溶掉、傳承", () => {
    expect(worldActionOf({ kind: "allocate", attributes: { con: 2 } })).toEqual({ kind: "allocate", attributes: { con: 2 } });
    expect(worldActionOf({ kind: "respec_attributes" })).toEqual({ kind: "respec" });
    expect(worldActionOf({ kind: "flash", skill: "s", slot: null, category: "combo" })).toEqual({ kind: "flash", skill: "s", slot: null, category: "combo" });
    expect(worldActionOf({ kind: "flash", skill: "s", slot: 2, category: null })).toEqual({ kind: "flash", skill: "s", slot: 2, category: null });
    expect(worldActionOf({ kind: "flash_pick", pick: 1, unequip: null })).toEqual({ kind: "flash_pick", pick: 1, unequip: null });
    expect(worldActionOf({ kind: "dissolve", skill: "s" })).toEqual({ kind: "dissolve", skill: "s" });
    expect(worldActionOf({ kind: "inherit", skill: "t", source: "s", records: [1, 2] })).toEqual({ kind: "inherit", skill: "t", source: "s", records: [1, 2] });
  });

  it("大世界沒有的選擇為 null", () => {
    expect(worldActionOf({ kind: "leave" } as never)).toBeNull();
  });
});

describe("左欄與成長狀態", () => {
  it("閃現待選時固定顯示選項，不管玩家切到哪裡", () => {
    expect(leftPane(view({ pending: true }), false)).toBe("pending");
    expect(leftPane(view({ pending: true }), true)).toBe("pending");
    expect(leftPane(view(), true)).toBe("growth");
    expect(leftPane(view(), false)).toBe("map");
  });

  it("不在城鎮或營火時花點被擋，原因照後端", () => {
    expect(spendLock(view())).toBeNull();
    expect(spendLock(view({ growth: { can_spend: false, at_service: false, blocked_zh: "這裡不是城鎮或營火" } }))).toBe("這裡不是城鎮或營火");
    expect(spendLock(view({ growth: { can_spend: false, blocked_zh: "先選完閃現的變化" } }))).toBe("先選完閃現的變化");
  });

  it("按鈕小字提醒可用的點數", () => {
    expect(growthBadge(view())).toBe("");
    expect(growthBadge(view({ points: 2, growth: { insight: 2 } }))).toBe("屬性點 2・靈感 2");
  });
});

describe("誓約", () => {
  it("沒有誓約內容時「尚未開放」", () => {
    expect(oathButton(view())).toEqual({ label: "立誓（尚未開放）", reason: "尚未開放" });
  });

  it("有內容時照後端的可用狀態", () => {
    expect(oathButton(view({ oath: { available: true, unavailable_zh: null, can_swear: true, swear_problem_zh: null } }))).toEqual({ label: "立誓", reason: null });
    expect(
      oathButton(view({ oath: { available: true, unavailable_zh: null, can_swear: false, swear_problem_zh: "只有城鎮與營火能立誓" } })),
    ).toEqual({ label: "立誓", reason: "只有城鎮與營火能立誓" });
  });

  it("參數初值與立誓動作（來源一律模板選單）", () => {
    const template = {
      id: "melee_kills",
      name_zh: "每場至少用近戰擊殺 N 名敵人",
      difficulty: "medium" as const,
      difficulty_zh: "中",
      params: [
        { id: "n", kind: "int" as const, choices: [], min: 1, max: 2, name_zh: "", choice_names_zh: {} },
        { id: "element", kind: "choice" as const, choices: ["fire", "ice"], min: 0, max: 0, name_zh: "", choice_names_zh: {} },
      ],
      description_zh: "",
      bonus_zh: "",
      judge_zh: "",
    };
    expect(defaultParams(template)).toEqual({ n: 1, element: "fire" });
    expect(swearAction("melee_kills", { n: 2 }, "  我絕不後退 ")).toEqual({
      kind: "swear_oath",
      proposal: { template: "melee_kills", params: { n: 2 } },
      player_text: "我絕不後退",
    });
  });
});

describe("誓約參數的中文（5C-3）", () => {
  const element = {
    id: "element",
    kind: "choice" as const,
    choices: ["fire", "ice"],
    min: 0,
    max: 0,
    name_zh: "元素",
    choice_names_zh: { fire: "火焰", ice: "冰霜" },
  };

  it("參數名與選項用中文，沒有時退回 ID", () => {
    expect(paramLabel(element)).toBe("元素");
    expect(choiceLabel(element, "fire")).toBe("火焰");
    expect(paramLabel({ id: "n", kind: "int", choices: [], min: 1, max: 2, name_zh: "", choice_names_zh: {} })).toBe("n");
    expect(choiceLabel({ ...element, choice_names_zh: {} }, "ice")).toBe("ice");
  });

  it("送出的動作仍用原本的值", () => {
    const template = {
      id: "oath_one_element",
      name_zh: "只用某一種元素",
      difficulty: "hard" as const,
      difficulty_zh: "難",
      params: [element],
      description_zh: "",
      bonus_zh: "",
      judge_zh: "",
    };
    expect(swearAction(template.id, defaultParams(template), "")).toEqual({
      kind: "swear_oath",
      proposal: { template: "oath_one_element", params: { element: "fire" } },
      player_text: "",
    });
  });
});
