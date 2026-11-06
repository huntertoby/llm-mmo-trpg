// 隊伍、系統傭兵與影子的純函式（Phase 5C-1、5C-2）。
import { describe, expect, it } from "vitest";
import type { WorldMercenary, WorldPartyView, WorldShadow } from "../api/types";
import { groupByRole, hireAction, hireLabel, hireLimit, hiredIds, hiredShadows, memberAi, sameParty, toggleMercenary } from "./party";

function merc(id: string, role: string, role_zh: string, name_zh: string): WorldMercenary {
  return { id, name_zh, title_zh: "稱號", role, role_zh, theme_zh: "主題", skills_zh: ["技能"], skill_ids: ["skill_a"], hired: false };
}

function shadow(owner: string, name_zh: string): WorldShadow {
  return {
    owner,
    name_zh,
    level: 3,
    role_zh: "火焰法杖・人類",
    skills_zh: ["火球"],
    skill_ids: ["gen_fireball"],
    borrowed_level: 1,
    borrowed_tier: 1,
    capped: true,
    cap_zh: "借用時壓到 Lv 1・技能 1 階（你的上限）",
    hired: false,
    own: false,
    saved_zh: "霧渡鎮",
    titles: [],
  };
}

const ROSTER = [
  merc("merc_qingfeng", "damage", "輸出", "青鋒"),
  merc("merc_tiebi", "guardian", "守護", "賽倫"),
  merc("merc_chuanyun", "damage", "輸出", "珊瑚"),
  merc("merc_huichun", "support", "輔助", "回春"),
];

const SHADOWS = [shadow("c1", "阿霧"), shadow("c2", "小美")];

function party(hired: string[], shadows: string[] = [], ai: Record<string, string> = {}): WorldPartyView {
  return {
    members: [
      { name_zh: "阿霧", title_zh: "主角", level: 1, mercenary: null },
      ...hired.map((id) => ({ name_zh: id, title_zh: "x", level: 1, mercenary: id })),
      ...shadows.map((id) => ({ name_zh: `${id}的影子`, title_zh: "影子", level: 1, mercenary: null, shadow: id })),
    ],
    max_hired: 2,
    can_hire: true,
    hire_problem_zh: null,
    mercenaries: ROSTER,
    shadows: SHADOWS,
    ai_choices: [],
    ai,
    season_boss_ok: shadows.length === 0,
    free_slots: 2,
  };
}

describe("toggleMercenary", () => {
  it("keeps pick order and caps at max", () => {
    let chosen = toggleMercenary([], "merc_tiebi", 2);
    chosen = toggleMercenary(chosen, "merc_huichun", 2);
    expect(chosen).toEqual(["merc_tiebi", "merc_huichun"]);
    expect(toggleMercenary(chosen, "merc_qingfeng", 2)).toEqual(["merc_tiebi", "merc_huichun"]);
    expect(toggleMercenary(chosen, "merc_tiebi", 2)).toEqual(["merc_huichun"]);
  });

  it("shares the two slots between mercenaries and shadows", () => {
    expect(toggleMercenary(["merc_tiebi"], "merc_huichun", 2, 1)).toEqual(["merc_tiebi"]);
    expect(toggleMercenary([], "c1", 2, 1)).toEqual(["c1"]);
    expect(toggleMercenary([], "c2", 2, 2)).toEqual([]);
  });
});

describe("party helpers", () => {
  it("reads hired ids and shadows from members in order", () => {
    expect(hiredIds(party(["merc_huichun", "merc_tiebi"]))).toEqual(["merc_huichun", "merc_tiebi"]);
    expect(hiredIds(party([]))).toEqual([]);
    expect(hiredShadows(party(["merc_tiebi"], ["c2"]))).toEqual(["c2"]);
  });

  it("detects unchanged selection (order and ai matter)", () => {
    const p = party(["merc_tiebi", "merc_huichun"]);
    expect(sameParty(p, ["merc_tiebi", "merc_huichun"])).toBe(true);
    expect(sameParty(p, ["merc_huichun", "merc_tiebi"])).toBe(false);
    expect(sameParty(party([]), [])).toBe(true);
    const withAi = party(["merc_tiebi"], ["c1"], { c1: "guard" });
    expect(sameParty(withAi, ["merc_tiebi"], ["c1"], { c1: "guard" })).toBe(true);
    expect(sameParty(withAi, ["merc_tiebi"], ["c1"], {})).toBe(false);
    expect(sameParty(withAi, ["merc_tiebi"], [], { c1: "guard" })).toBe(false);
  });

  it("groups by role in roster order", () => {
    const groups = groupByRole(ROSTER);
    expect(groups.map((g) => g.role_zh)).toEqual(["輸出", "守護", "輔助"]);
    expect(groups[0]?.members.map((m) => m.name_zh)).toEqual(["青鋒", "珊瑚"]);
  });

  it("labels the apply button (zero = solo)", () => {
    expect(hireLabel([], ROSTER)).toBe("確定：獨行（只帶主角）");
    expect(hireLabel(["merc_tiebi", "merc_huichun"], ROSTER)).toBe("確定隊伍：賽倫、回春");
    expect(hireLabel(["merc_tiebi"], ROSTER, ["c2"], SHADOWS)).toBe("確定隊伍：賽倫、小美的影子");
  });

  it("builds the hire action with ai only for members", () => {
    expect(memberAi({ c1: "guard", merc_tiebi: "brute" }, ["c1"])).toEqual({ c1: "guard" });
    expect(hireAction(["merc_tiebi"], ["c1"], { c1: "guard", merc_qingfeng: "brute" })).toEqual({
      kind: "hire",
      mercenaries: ["merc_tiebi"],
      shadows: ["c1"],
      ai: { c1: "guard" },
    });
  });
});

describe("hireLimit（劇情夥伴佔隊友位，5C-3）", () => {
  it("沒有夥伴時＝max_hired、夥伴在隊時少 1", () => {
    expect(hireLimit(party([]))).toBe(2);
    expect(hireLimit({ ...party(["merc_tiebi"]), free_slots: 1, companion_zh: "阿岳跟著你" })).toBe(1);
  });

  it("夥伴在隊時勾 1 名就滿", () => {
    const limit = hireLimit({ ...party(["merc_tiebi"]), free_slots: 1 });
    expect(toggleMercenary(["merc_tiebi"], "merc_huichun", limit)).toEqual(["merc_tiebi"]);
  });
});
