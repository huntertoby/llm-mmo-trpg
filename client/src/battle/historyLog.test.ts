import { describe, expect, it } from "vitest";
import { logLines } from "./log";
import { unitNames } from "./units";
import type { BattleView } from "../api/types";

const names = unitNames({ units: [] } as unknown as BattleView);

describe("logLines：/history 的步驟（只有事件）", () => {
  it("事件的中文描述逐行列出，沒有 text 的略過", () => {
    const steps = [
      { events: [{ seq: 1, round: 1, type: "battle_started", text: "戰鬥開始" }] },
      { events: [{ seq: 2, round: 1, type: "turn_started" }, { seq: 3, round: 1, type: "x", text: " 攻擊 " }] },
    ];
    const lines = logLines(steps, names);
    expect(lines.map((l) => l.text)).toEqual(["戰鬥開始", "攻擊"]);
    expect(lines.map((l) => l.seq)).toEqual([1, 3]);
  });
});
