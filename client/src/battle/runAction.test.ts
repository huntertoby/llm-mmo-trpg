import { describe, expect, it } from "vitest";
import type { Action, PreviewOut, RunOption } from "../api/types";
import { actionLabel } from "./actions";
import { runButton, runRangeTiles } from "./runAction";
import { basicModes, fallbackActions } from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const hero = unit(H, "ally", 1, 1, {});
const view = smallView({ units: [hero] });
const run = { type: "run", unit_id: H } as Action;
const option = (legal: boolean, reason: string | null): RunOption => ({ legal, reason, ap_cost: 1, move_bonus: 3 });

describe("run button", () => {
  it("is enabled when the engine lists a legal run", () => {
    const mode = basicModes([run]).find((m) => m.kind === "run") ?? null;
    expect(mode?.label).toBe("跑步");
    expect(mode?.targets.self).toBe(run);
    expect(runButton(mode, option(true, null))).toEqual({ enabled: true, reason: null });
  });

  it("is greyed out with the engine's reason when run is not legal", () => {
    for (const reason of ["已經跑過了", "被定身，不能跑", "AP 不足：需要 1，剩餘 0"]) {
      expect(basicModes([])).toEqual([]);
      expect(runButton(null, option(false, reason))).toEqual({ enabled: false, reason });
    }
  });

  it("falls back to a generic reason when the response carries no run option", () => {
    expect(runButton(null, null)).toEqual({ enabled: false, reason: "目前不能跑步" });
    expect(runButton(null, undefined).enabled).toBe(false);
  });

  it("is a basic mode, not a fallback action, and has a Chinese label", () => {
    expect(fallbackActions([run], hero)).toEqual([]);
    expect(actionLabel(run, view, {})).toBe("跑步");
  });
});

describe("run preview range", () => {
  const base = { action: run, run_range: [[1, 0], [2, 0]] } as unknown as PreviewOut;

  it("turns the previewed run range into highlight tiles", () => {
    expect(runRangeTiles(base)).toEqual([
      { x: 1, y: 0 },
      { x: 2, y: 0 },
    ]);
  });

  it("is empty for other previews or none", () => {
    expect(runRangeTiles(null)).toEqual([]);
    expect(runRangeTiles({ ...base, action: { type: "defend", unit_id: H } } as unknown as PreviewOut)).toEqual([]);
  });
});
