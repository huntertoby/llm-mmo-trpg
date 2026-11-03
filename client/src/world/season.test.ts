// 季末重置、編年史與沿用上季角色的純函式（Phase 5F-5）。
import { describe, expect, it } from "vitest";
import type { AuthStatus, ChronicleSeasonView, SeasonResetReport } from "../api/types";
import { canAdmin, canExecute, legacyLabel, resetBody, resetLineText, seasonHasRecords, seasonTitle, startDateProblem } from "./season";

const account = { account_id: "a1", username: "alice", characters: 0, max_characters: 3, can_create: true, admin: false };

describe("canAdmin", () => {
  it("管理者帳號或開發模式沒登入", () => {
    expect(canAdmin(null)).toBe(false);
    expect(canAdmin({ dev_mode: true, account: null } as AuthStatus)).toBe(true);
    expect(canAdmin({ dev_mode: false, account: null } as AuthStatus)).toBe(false);
    expect(canAdmin({ dev_mode: true, account: { ...account, admin: false } })).toBe(false);
    expect(canAdmin({ dev_mode: false, account: { ...account, admin: true } })).toBe(true);
  });
});

describe("startDateProblem / resetBody", () => {
  it("開賽日要是 YYYY-MM-DD", () => {
    expect(startDateProblem("")).toBe("請填新一季的開賽日");
    expect(startDateProblem("2027/1/1")).toBe("開賽日格式是 YYYY-MM-DD");
    expect(startDateProblem(" 2027-01-01 ")).toBeNull();
  });
  it("預覽是 dry-run，執行帶確認的季 ID", () => {
    expect(resetBody("2027-01-01", false, null)).toEqual({ start_date: "2027-01-01", force: false, dry_run: true });
    expect(resetBody("2027-01-01", true, " s1 ")).toEqual({
      start_date: "2027-01-01",
      force: true,
      dry_run: false,
      confirm_season: "s1",
    });
  });
});

describe("canExecute", () => {
  const preview = { dry_run: true, old_season: "s1" } as SeasonResetReport;
  it("預覽過、條件沒改、季 ID 對才能執行", () => {
    expect(canExecute(null, null, "2027-01-01|0", "s1")).toBe(false);
    expect(canExecute(preview, "2027-01-01|0", "2027-01-01|0", "s1")).toBe(true);
    expect(canExecute(preview, "2027-01-01|0", "2027-01-02|0", "s1")).toBe(false);
    expect(canExecute(preview, "2027-01-01|0", "2027-01-01|0", "s2")).toBe(false);
    expect(canExecute({ ...preview, dry_run: false }, "x", "x", "s1")).toBe(false);
  });
});

describe("文字", () => {
  it("清單一行與上季角色", () => {
    expect(resetLineText({ label_zh: "角色", count: 2, detail_zh: "等級" })).toBe("角色 2（等級）");
    expect(resetLineText({ label_zh: "留言", count: 0, detail_zh: "" })).toBe("留言 0");
    const hero = {
      character_id: "c1",
      season_id: "s1",
      season_name_zh: "第一季",
      name: "阿霧",
      race: "fox",
      race_name_zh: "狐族",
      text_zh: "第一季：走過這一季",
    };
    expect(legacyLabel(hero)).toBe("阿霧（第一季・狐族）");
    expect(legacyLabel({ ...hero, race: null, race_name_zh: null })).toBe("阿霧（第一季）");
  });
  it("編年史一季", () => {
    const season: ChronicleSeasonView = {
      season_id: "s2",
      name_zh: "第二季",
      current: true,
      started_at: null,
      reset_at: null,
      heroes: [],
      recipes: [],
      first_kills: [],
      league: [],
      boss_board: [],
    };
    expect(seasonHasRecords(season)).toBe(false);
    expect(seasonTitle(season)).toBe("第二季（進行中）");
    expect(seasonHasRecords({ ...season, heroes: [{ name: "阿霧", text_zh: "x" }] })).toBe(true);
    expect(seasonTitle({ ...season, current: false })).toBe("第二季");
  });
});
