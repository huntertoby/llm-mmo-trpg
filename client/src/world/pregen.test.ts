import { describe, expect, it } from "vitest";
import { pregenWaitBody, pregenWaitText } from "./pregen";

describe("pregen wait (6L-2)", () => {
  it("waits before flash and reflash", () => {
    expect(pregenWaitBody({ kind: "flash", skill: "skill_x", slot: null, category: null })).toEqual({
      kind: "flash",
      skill: "skill_x",
      slot: null,
      category: null,
    });
    expect(pregenWaitBody({ kind: "flash", skill: "skill_x", slot: 2, category: "range" })).toEqual({
      kind: "flash",
      skill: "skill_x",
      slot: 2,
      category: "range",
    });
  });

  it("asks the server about an event solution (only opportunities wait)", () => {
    expect(pregenWaitBody({ kind: "event_solve", solution: 1, use_thread: null })).toEqual({ kind: "opportunity", solution: 1 });
  });

  it("does not wait for other actions", () => {
    expect(pregenWaitBody({ kind: "tavern" })).toBeNull();
    expect(pregenWaitBody({ kind: "flash_pick", pick: 0, unequip: null })).toBeNull();
  });

  it("has a hint text per kind", () => {
    expect(pregenWaitText({ kind: "flash", skill: "s" })).toContain("變化");
    expect(pregenWaitText({ kind: "opportunity", solution: 0 })).toContain("機遇");
  });
});
