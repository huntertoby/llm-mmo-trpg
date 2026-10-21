import { describe, expect, it } from "vitest";
import type { Action } from "../api/types";
import { actionLabel } from "./actions";
import { basicModes, fallbackActions } from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const ALLY = "unit_0002";
const hero = unit(H, "ally", 1, 1, {});
const view = smallView({ units: [hero, unit(ALLY, "ally", 2, 1)] });

const guardSelf = { type: "defend", unit_id: H, target_id: null } as Action;
const guardAlly = { type: "defend", unit_id: H, target_id: ALLY } as Action;
const swap = { type: "swap", unit_id: H, target_id: ALLY } as Action;
const aim = { type: "aim", unit_id: H } as Action;

describe("guard, swap and aim (Phase 3-21a)", () => {
  it("keeps guarding yourself as the resident guard mode", () => {
    const modes = basicModes([guardSelf, guardAlly, swap, aim]);
    expect(modes.map((m) => [m.kind, m.label])).toEqual([["defend", "守護"]]);
    expect(modes[0]?.targets.self).toBe(guardSelf);
  });

  it("puts guarding an ally, swap and aim into the other-actions list", () => {
    expect(fallbackActions([guardSelf, guardAlly, swap, aim], hero)).toEqual([guardAlly, swap, aim]);
  });

  it("labels them in Chinese", () => {
    expect(actionLabel(guardSelf, view, {})).toBe("守護自己");
    expect(actionLabel(guardAlly, view, {})).toContain("守護：");
    expect(actionLabel(swap, view, {})).toContain("換位：");
    expect(actionLabel(aim, view, {})).toBe("瞄準");
  });
});
