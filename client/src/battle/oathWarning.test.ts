import { describe, expect, it } from "vitest";
import type { Action } from "../api/types";
import { needsOathCheck, oathWarningOf } from "./oathWarning";

const endTurn = { type: "end_turn", unit_id: "unit_0001" } as Action;
const other = { type: "end_turn", unit_id: "unit_0002" } as Action;

describe("oathWarning", () => {
  it("only asks while the oath is active and for the hero's own actions", () => {
    expect(needsOathCheck({ oath_active: true, hero_id: "unit_0001" }, endTurn)).toBe(true);
    expect(needsOathCheck({ oath_active: false, hero_id: "unit_0001" }, endTurn)).toBe(false);
    expect(needsOathCheck({ oath_active: true, hero_id: "unit_0001" }, other)).toBe(false);
  });

  it("reads the engine's warning text without guessing", () => {
    expect(oathWarningOf(null)).toBeNull();
    expect(oathWarningOf({ oath_warning: null })).toBeNull();
    expect(oathWarningOf({ oath_warning: "" })).toBeNull();
    expect(oathWarningOf({ oath_warning: "會違反誓約「X」" })).toBe("會違反誓約「X」");
  });
});
