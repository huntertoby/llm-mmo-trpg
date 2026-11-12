import { describe, expect, it } from "vitest";
import type { BoardGoalView, BoardWorldEventView } from "../api/types";
import { barWidth, eventProgressLabel, goalProgressLabel } from "./board";

const event: BoardWorldEventView = {
  event: "mist_tide",
  name_zh: "霧潮入侵",
  text_zh: "",
  status: "active",
  status_zh: "進行中",
  progress: 12,
  target: 30,
  permille: 400,
  days_zh: "第 1～3 天",
  start_day: 1,
  end_day: 3,
  target_note_zh: null,
};

const goal: BoardGoalView = {
  goal: "win_battles",
  text_zh: "打贏 3 場戰鬥",
  progress: 1,
  count: 3,
  done: false,
  coins: 1,
};

describe("公告板", () => {
  it("進度條寬度夾在 0～100%", () => {
    expect(barWidth(400)).toBe("40%");
    expect(barWidth(1500)).toBe("100%");
    expect(barWidth(-3)).toBe("0%");
  });

  it("世界事件與今日目標的進度文字", () => {
    expect(eventProgressLabel(event)).toBe("12／30・進行中");
    expect(goalProgressLabel(goal)).toBe("1／3");
    expect(goalProgressLabel({ ...goal, progress: 3, done: true })).toBe("完成（+1 任務幣）");
    expect(goalProgressLabel({ ...goal, done: true, coins: 0 })).toBe("完成");
  });
});
