import { describe, expect, it } from "vitest";
import type { PrepOut } from "../api/types";
import { prepActions, prepMode, prepPromptText } from "./prep";
import { PREP_HINT_ZH, actionHintKind, actionHintText } from "./skillTray";

const PREP: PrepOut = {
  unit_id: "unit_0001",
  zone: [
    [0, 0],
    [1, 0],
  ],
  options: [
    { skill_id: "skill_bear_trap", kind: "trap", tiles: [[1, 0]] },
    { skill_id: "skill_hunt_sigil", kind: "rune", tiles: [[0, 0], [1, 0]] },
  ],
};

describe("SK-3 戰前佈置", () => {
  it("選了一招：每個放得下的格子一個 prepare 動作", () => {
    expect(prepActions(PREP, "skill_hunt_sigil")).toEqual([
      { type: "prepare", unit_id: "unit_0001", skill_id: "skill_hunt_sigil", target_pos: { x: 0, y: 0 } },
      { type: "prepare", unit_id: "unit_0001", skill_id: "skill_hunt_sigil", target_pos: { x: 1, y: 0 } },
    ]);
    expect(prepActions(PREP, "skill_unknown")).toEqual([]);
  });
  it("選取模式的格子就是那一招放得下的格子", () => {
    const mode = prepMode(PREP, "skill_bear_trap", "捕獸夾");
    expect(mode?.label).toBe("捕獸夾（戰前佈置）");
    expect([...(mode?.targets.tiles.keys() ?? [])]).toHaveLength(1);
    expect(prepMode(PREP, "skill_unknown", "?")).toBeNull();
  });
  it("提示文字", () => {
    expect(prepPromptText(PREP, null, "")).toContain("我方起始區");
    expect(prepPromptText(PREP, "skill_bear_trap", "捕獸夾")).toContain("放陷阱");
  });
  it("戰前佈置時技能列上方寫佈置的提示（選了一招進入選格模式時也一樣）", () => {
    const base = { copying: true, canAct: false, ended: false, moveCount: 0, attackCount: 0, prep: true };
    expect(actionHintText(base)).toBe(PREP_HINT_ZH);
    expect(actionHintKind(base)).toBeNull();
    expect(actionHintText({ ...base, prep: false })).toContain("複製");
  });
});
