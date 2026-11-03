import { describe, expect, it } from "vitest";
import type { LeagueReplayResponse, LeagueStandingView, LeagueView } from "../api/types";
import { outcomeText } from "../ui/EndPanel";
import type { BattleResponse } from "../api/types";
import {
  allocationToSend,
  pageLabel,
  progressLabel,
  rankLabel,
  recordLabel,
  replayNotes,
  signupNote,
  tiebreakLabel,
} from "./league";

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
  hp_permille_total: 1825,
  rounds_total: 40,
  tied: false,
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
    page: 1,
    pages: 1,
    page_size: 20,
    allocation: null,
    stale_zh: null,
    reruns: 0,
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

  it("同分（5F-4b）：名次標同分、同勝場比 HP 比例合計與總輪數", () => {
    expect(rankLabel({ ...row, rank: 1, tied: true })).toBe("1（同分）");
    expect(tiebreakLabel(row)).toBe("剩餘 HP 合計 182%・共 40 輪");
    expect(tiebreakLabel({ ...row, played: 0 })).toBeNull();
  });

  it("場次分頁（5F-4b）", () => {
    expect(pageLabel({ page: 1, pages: 1 })).toBeNull();
    expect(pageLabel({ page: 2, pages: 5 })).toBe("第 2／5 頁");
  });

  it("報名配點（5F-4b）：和自動配點一樣時不送", () => {
    const auto = { wis: 18 };
    expect(allocationToSend({ wis: 18 }, auto)).toBeNull();
    expect(allocationToSend({ wis: 10, con: 8, dex: 0 }, auto)).toEqual({ wis: 10, con: 8 });
    const entry = { character_id: "c1", name: "阿霧", ai: null, ai_zh: "預設", this_character: true, allocation: { con: 18 } };
    expect(signupNote(view({ entry }))).toBe("已用這個角色報名（打法：預設、自己配點）。");
  });

  it("重播結束面板用中性的「某某 勝」（5F-4b）", () => {
    const res = {
      awaiting: "ended",
      outcome: { winner: "enemy", end_reason: null, round: 7 },
    } as unknown as BattleResponse;
    expect(outcomeText(res)).toBe("敗北……・第 7 輪");
    expect(outcomeText(res, "小美 勝")).toBe("小美 勝・第 7 輪");
  });

  it("重播的開場說明帶驗證結果", () => {
    const res = { title_zh: "m0001：阿霧（先手） vs 小美", verified: true } as LeagueReplayResponse;
    expect(replayNotes(res)).toEqual(["m0001：阿霧（先手） vs 小美", "重播驗證一致：依紀錄的步驟重算出相同的結果。"]);
    expect(replayNotes({ ...res, verified: false })[1]).toContain("不一致");
  });
});
