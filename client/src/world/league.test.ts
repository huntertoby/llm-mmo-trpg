import { describe, expect, it } from "vitest";
import type { LeagueReplayResponse, LeagueStandingView, LeagueView } from "../api/types";
import { progressLabel, rankLabel, recordLabel, replayNotes, signupNote } from "./league";

const row: LeagueStandingView = {
  rank: 2,
  name: "阿霧",
  level: 10,
  role_zh: "火焰法杖・人類",
  place_zh: "霧渡口",
  wins: 5,
  losses: 2,
  draws: 1,
  played: 8,
  mine: true,
};

function view(over: Partial<LeagueView> = {}): LeagueView {
  return {
    status: "signup",
    status_zh: "報名中",
    season_day: 3,
    signup_close_day: 13,
    maps_zh: ["開闊平原", "竹林", "沼澤"],
    per_pair: 12,
    rules_zh: "",
    entry: null,
    can_enter: true,
    enter_problem_zh: null,
    can_withdraw: false,
    ai_choices: [],
    entrants: 0,
    standings: [],
    matches: [],
    done: 0,
    total: 0,
    champion_zh: null,
    ...over,
  };
}

describe("影子循環賽", () => {
  it("名次與戰績", () => {
    expect(rankLabel(row)).toBe("2");
    expect(rankLabel({ ...row, rank: null })).toBe("—");
    expect(recordLabel(row)).toBe("5 勝 2 負 1 和");
  });

  it("進度只在開跑後顯示", () => {
    expect(progressLabel(view())).toBeNull();
    expect(progressLabel(view({ done: 12, total: 36 }))).toBe("已完成 12／36 場");
  });

  it("報名區的說明", () => {
    expect(signupNote(view())).toBe("尚未報名（第 13 天截止）。");
    const entry = { character_id: "c1", name: "阿霧", ai: "guard", ai_zh: "守衛", this_character: true };
    expect(signupNote(view({ entry }))).toBe("已用這個角色報名（打法：守衛）。");
    expect(signupNote(view({ entry: { ...entry, this_character: false } }))).toBe("已用「阿霧」報名（打法：守衛）。");
    expect(signupNote(view({ can_enter: false, enter_problem_zh: "要在城鎮報名" }))).toBe("不能報名：要在城鎮報名");
    expect(signupNote(view({ status: "none", status_zh: "這一季沒有影子循環賽" }))).toBe("這一季沒有影子循環賽");
  });

  it("重播的開場說明帶驗證結果", () => {
    const res = { title_zh: "m0001：阿霧（先手） vs 小美", verified: true } as LeagueReplayResponse;
    expect(replayNotes(res)).toEqual(["m0001：阿霧（先手） vs 小美", "重播驗證一致：依紀錄的步驟重算出相同的結果。"]);
    expect(replayNotes({ ...res, verified: false })[1]).toContain("不一致");
  });
});
