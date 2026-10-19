import { describe, expect, it } from "vitest";
import type { StepOut } from "../api/types";
import { MOVE_DURATION_MS, movePlan } from "./animation";
import { logLines } from "./log";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

const names = unitNames(smallView());
let seq = 0;
const walk = (unit: string, fx: number, fy: number, tx: number, ty: number) => ({
  seq: seq++,
  round: 1,
  type: "unit_moved",
  unit_id: unit,
  from_pos: { x: fx, y: fy },
  to_pos: { x: tx, y: ty },
  mode: "walk",
  cost: 1,
});
const said = (text: string) => ({ seq: seq++, round: 1, type: "something", text });
const step = (...events: Record<string, unknown>[]): StepOut => ({
  actor_id: null,
  step: null,
  events,
  view: smallView(),
});

describe("logLines", () => {
  it("merges consecutive walking steps of one unit into one line", () => {
    const lines = logLines([step(walk("unit_0001", 0, 0, 1, 0), walk("unit_0001", 1, 0, 1, 1))], names);
    expect(lines.map((l) => l.text)).toEqual(["A 單位1 從 (0, 0) 移動到 (1, 1)（消耗 2 移動）"]);
  });

  it("keeps event texts in order and trims the CLI indentation", () => {
    const lines = logLines([step(said("  先攻：A"), walk("unit_0003", 2, 1, 2, 2), said("  a 攻擊"))], names);
    expect(lines.map((l) => l.text)).toEqual([
      "先攻：A",
      "a 單位3 從 (2, 1) 移動到 (2, 2)（消耗 1 移動）",
      "a 攻擊",
    ]);
  });

  it("does not merge across a teleport or another unit, and skips silent events", () => {
    const teleport = { ...walk("unit_0001", 1, 0, 3, 2), mode: "teleport", text: "  單位1 被傳送到 (3, 2)" };
    const silent = { seq: seq++, round: 1, type: "ap_spent" };
    const lines = logLines(
      [
        step(walk("unit_0001", 0, 0, 1, 0), silent, teleport, walk("unit_0001", 3, 2, 3, 1)),
        step(walk("unit_0003", 2, 1, 2, 0), walk("unit_0001", 3, 1, 3, 0)),
      ],
      names,
    );
    expect(lines.map((l) => l.text)).toEqual([
      "A 單位1 從 (0, 0) 移動到 (1, 0)（消耗 1 移動）",
      "單位1 被傳送到 (3, 2)",
      "A 單位1 從 (3, 2) 移動到 (3, 1)（消耗 1 移動）",
      "a 單位3 從 (2, 1) 移動到 (2, 0)（消耗 1 移動）",
      "A 單位1 從 (3, 1) 移動到 (3, 0)（消耗 1 移動）",
    ]);
  });

  it("merges a walk that continues into the next step of the same unit", () => {
    const lines = logLines([step(walk("unit_0001", 0, 0, 1, 0)), step(walk("unit_0001", 1, 0, 2, 0))], names);
    expect(lines).toHaveLength(1);
  });
});

describe("movePlan", () => {
  it("animates walking, forced and teleport moves in order with their speeds", () => {
    const plan = movePlan([
      step(
        walk("unit_0001", 0, 0, 1, 0),
        said("x"),
        { ...walk("unit_0003", 2, 1, 2, 2), mode: "forced" },
        { ...walk("unit_0004", 2, 0, 0, 2), mode: "teleport" },
      ),
    ]);
    expect(plan.map((m) => [m.unitId, m.mode, m.durationMs > 0])).toEqual([
      ["unit_0001", "walk", true],
      ["unit_0003", "forced", true],
      ["unit_0004", "teleport", false],
    ]);
    expect(plan[0]!.durationMs).toBeGreaterThan(plan[1]!.durationMs);
  });

  it("animates a dash step faster than a walk, and leaps and swaps as one move each", () => {
    const plan = movePlan([
      step(
        { ...walk("unit_0001", 0, 0, 1, 0), mode: "dash" },
        { ...walk("unit_0001", 3, 0, 5, 0), mode: "leap" },
        { ...walk("unit_0002", 4, 0, 1, 1), mode: "swap" },
      ),
    ]);
    expect(plan.map((m) => [m.mode, m.durationMs > 0])).toEqual([
      ["dash", true],
      ["leap", true],
      ["swap", true],
    ]);
    expect(plan[0]!.durationMs).toBeLessThan(MOVE_DURATION_MS.walk);
  });
});
