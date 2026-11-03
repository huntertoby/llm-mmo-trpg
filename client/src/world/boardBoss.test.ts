// 公告板的賽季 Boss 區塊（Phase 5F-3）：鑰匙、次數、評分榜的顯示文字。
import { describe, expect, it } from "vitest";
import type { BoardBossEntryView, BoardSeasonBossView } from "../api/types";
import { bossAttemptsLabel, bossEntryLabel, bossKeysLabel, bossKeysPermille } from "./board";

const boss: BoardSeasonBossView = {
  boss: "rift_shard_lord",
  name_zh: "碎晶之主",
  status: "sealed",
  status_zh: "封印中",
  note_zh: "最晚 11 月 11 日 06:00 解鎖",
  announce_at: 0,
  unlock_at: 0,
  close_at: 0,
  world_keys: 5,
  keys_target: 12,
  my_keys: 1,
  keys_required: 1,
  attempts_left: 2,
  daily_attempts: 3,
  can_challenge: false,
  problem_zh: "「碎晶之主」還在封印中",
  first_kill_zh: null,
  first_kill_titles: [],
  title_zh: "碎晶的終結者",
  board: [],
};

const entry: BoardBossEntryView = {
  rank: 1,
  name: "小美",
  score: 1240,
  rounds: 8,
  survivors: 3,
  allies: 3,
  no_down: true,
  location_zh: "霧渡鎮",
  mine: false,
  at: 0,
  titles: [],
};

describe("賽季 Boss 區塊", () => {
  it("封印鑰匙與進度條", () => {
    expect(bossKeysLabel(boss)).toBe("全服 5／12 把・你有 1 把（需要 1 把）");
    expect(bossKeysPermille(boss)).toBe(416);
    expect(bossKeysLabel({ ...boss, keys_target: null })).toBe("全服 5 把・你有 1 把（需要 1 把）");
    expect(bossKeysPermille({ ...boss, keys_target: null })).toBe(0);
    expect(bossKeysPermille({ ...boss, world_keys: 30 })).toBe(1000);
  });

  it("帳號今天的次數", () => {
    expect(bossAttemptsLabel(boss)).toBe("今天還剩 2／3 次（算帳號）");
  });

  it("評分榜的一行", () => {
    expect(bossEntryLabel(entry)).toBe("1. 小美　1240 分・8 輪・存活 3／3・無人倒下（霧渡鎮）");
    expect(bossEntryLabel({ ...entry, no_down: false, survivors: 2 })).toBe(
      "1. 小美　1240 分・8 輪・存活 2／3（霧渡鎮）",
    );
  });
});
