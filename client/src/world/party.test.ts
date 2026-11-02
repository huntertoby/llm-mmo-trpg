// 隊伍與系統傭兵的純函式（Phase 5C-1）。
import { describe, expect, it } from "vitest";
import type { WorldMercenary, WorldPartyView } from "../api/types";
import { groupByRole, hireLabel, hiredIds, sameParty, toggleMercenary } from "./party";

function merc(id: string, role: string, role_zh: string, name_zh: string): WorldMercenary {
  return { id, name_zh, title_zh: "稱號", role, role_zh, theme_zh: "主題", skills_zh: ["技能"], hired: false };
}

const ROSTER = [
  merc("merc_qingfeng", "damage", "輸出", "青鋒"),
  merc("merc_tiebi", "guardian", "守護", "鐵壁"),
  merc("merc_chuanyun", "damage", "輸出", "穿雲"),
  merc("merc_huichun", "support", "輔助", "回春"),
];

function party(hired: string[]): WorldPartyView {
  return {
    members: [
      { name_zh: "阿霧", title_zh: "主角", level: 1, mercenary: null },
      ...hired.map((id) => ({ name_zh: id, title_zh: "x", level: 1, mercenary: id })),
    ],
    max_hired: 2,
    can_hire: true,
    hire_problem_zh: null,
    mercenaries: ROSTER,
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
});

describe("party helpers", () => {
  it("reads hired ids from members in order", () => {
    expect(hiredIds(party(["merc_huichun", "merc_tiebi"]))).toEqual(["merc_huichun", "merc_tiebi"]);
    expect(hiredIds(party([]))).toEqual([]);
  });

  it("detects unchanged selection (order matters)", () => {
    const p = party(["merc_tiebi", "merc_huichun"]);
    expect(sameParty(p, ["merc_tiebi", "merc_huichun"])).toBe(true);
    expect(sameParty(p, ["merc_huichun", "merc_tiebi"])).toBe(false);
    expect(sameParty(party([]), [])).toBe(true);
  });

  it("groups by role in roster order", () => {
    const groups = groupByRole(ROSTER);
    expect(groups.map((g) => g.role_zh)).toEqual(["輸出", "守護", "輔助"]);
    expect(groups[0]?.members.map((m) => m.name_zh)).toEqual(["青鋒", "穿雲"]);
  });

  it("labels the apply button", () => {
    expect(hireLabel([], ROSTER)).toBe("確定：不帶傭兵（用標準隊友）");
    expect(hireLabel(["merc_tiebi", "merc_huichun"], ROSTER)).toBe("確定雇用：鐵壁、回春");
  });
});
