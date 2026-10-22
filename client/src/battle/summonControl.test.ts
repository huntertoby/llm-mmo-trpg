// 召喚物操控（Phase 3-33c）：按鈕出現條件、目前模式標示、指揮鈕的限制、指揮動作與選項。
import { describe, expect, it } from "vitest";
import type { Action, CommandOptions, UnitView } from "../api/types";
import { actionLabel } from "./actions";
import {
  commandAction,
  commandBlocked,
  commandMoveTiles,
  commandTargetTiles,
  controllableSummons,
  focusTargets,
  modeButtons,
  modeText,
  optionAt,
  optionLabel,
  setModeAction,
} from "./summonControl";
import { smallView, unit } from "./testFixtures";
import { unitNames } from "./units";

const HERO = "unit_0001";

function summon(id: string, over: Partial<UnitView> = {}): UnitView {
  return unit(id, "ally", 1, 0, {
    owner_id: HERO,
    summon_mode: "follow",
    summon_expires_round: 4,
    name_zh: "骷髏戰士1",
    ...over,
  });
}

const view = () =>
  smallView({
    units: [
      unit(HERO, "ally", 0, 0, { ap: 3 }),
      summon("unit_0006"),
      summon("unit_0007", { summon_mode: "focus", summon_target_id: "unit_0003" }),
      unit("unit_0008", "ally", 1, 1, { owner_id: HERO, totem_radius: 2, summon_mode: null }), // 圖騰
      unit("unit_0009", "ally", 2, 2, { owner_id: "unit_0002", summon_mode: "follow" }), // 別人的召喚物
      unit("unit_0003", "enemy", 2, 1),
      unit("unit_0004", "enemy", 2, 0, { downed: true }),
    ],
  });

describe("controllableSummons", () => {
  it("lists only my living summons that have a mode (no totems, no other owners)", () => {
    expect(controllableSummons(view(), HERO).map((u) => u.id)).toEqual(["unit_0006", "unit_0007"]);
  });
  it("drops a summon that has left the field", () => {
    const v = view();
    v.units = v.units.map((u) => (u.id === "unit_0006" ? { ...u, dismissed: true } : u));
    expect(controllableSummons(v, HERO).map((u) => u.id)).toEqual(["unit_0007"]);
  });
});

describe("modeButtons", () => {
  it("shows four buttons and marks the current mode", () => {
    const buttons = modeButtons(summon("unit_0006"), true, view());
    expect(buttons.map((b) => b.label)).toEqual(["集火", "守護我", "跟隨", "待命"]);
    expect(buttons.filter((b) => b.current).map((b) => b.label)).toEqual(["跟隨"]);
    expect(buttons.find((b) => b.mode === "focus")?.needsTarget).toBe(true);
    expect(buttons.find((b) => b.mode === "hold")?.disabled).toBe(false);
  });
  it("disables the current mode (nothing to change) but keeps focus usable to change target", () => {
    const focused = summon("unit_0007", { summon_mode: "focus", summon_target_id: "unit_0003" });
    const buttons = modeButtons(focused, true, view());
    expect(buttons.find((b) => b.mode === "focus")).toMatchObject({ current: true, disabled: false });
    const follow = modeButtons(summon("unit_0006"), true, view());
    expect(follow.find((b) => b.mode === "follow")?.disabled).toBe(true);
  });
  it("disables everything when it is not my turn, and focus when there is no enemy", () => {
    expect(modeButtons(summon("unit_0006"), false, view()).every((b) => b.disabled)).toBe(true);
    const empty = smallView({ units: [unit(HERO, "ally", 0, 0), summon("unit_0006")] });
    expect(modeButtons(summon("unit_0006"), true, empty).find((b) => b.mode === "focus")?.disabled).toBe(true);
  });
});

describe("text and actions", () => {
  it("writes the mode with the focus target", () => {
    const v = view();
    const names = unitNames(v);
    expect(modeText(summon("unit_0006"), names)).toBe("跟隨");
    expect(modeText(v.units.find((u) => u.id === "unit_0007") as UnitView, names)).toContain("集火 → ");
    expect(modeText(unit(HERO, "ally", 0, 0), names)).toBe("");
  });
  it("builds set_summon_mode actions (focus carries the target)", () => {
    expect(setModeAction(HERO, "unit_0006", "hold")).toEqual({
      type: "set_summon_mode",
      unit_id: HERO,
      summon_id: "unit_0006",
      mode: "hold",
    });
    expect(setModeAction(HERO, "unit_0006", "focus", "unit_0003")).toMatchObject({ mode: "focus", target_id: "unit_0003" });
  });
  it("offers living enemies as focus targets", () => {
    expect(focusTargets(view()).map((u) => u.id)).toEqual(["unit_0003"]);
  });
  it("labels both actions for the log and fallback buttons", () => {
    const v = view();
    expect(actionLabel(setModeAction(HERO, "unit_0006", "guard"), v, {})).toContain("守護我");
    const options = commandOptions();
    const action = commandAction(HERO, "unit_0006", options.options[1]!, "unit_0003") as Action;
    expect(actionLabel(action, v, {})).toContain("移動到 (2, 0)");
    expect(actionLabel(action, v, {})).toContain("攻擊");
  });
});

function commandOptions(): CommandOptions {
  return {
    summon_id: "unit_0006",
    ap_cost: 1,
    options: [
      { dest: { x: 1, y: 0 }, path: [{ x: 1, y: 0 }], targets: [] },
      {
        dest: { x: 2, y: 0 },
        path: [
          { x: 1, y: 0 },
          { x: 2, y: 0 },
        ],
        targets: ["unit_0003"],
      },
    ],
  };
}

describe("command", () => {
  it("is blocked when it is not my turn, already commanded, or AP is short", () => {
    const v = view();
    const hero = v.units[0] as UnitView;
    const s = summon("unit_0006");
    expect(commandBlocked(v, hero, s, true)).toBeNull();
    expect(commandBlocked(v, hero, s, false)).toContain("不是你的回合");
    expect(commandBlocked(v, hero, { ...s, commanded: true }, true)).toContain("已經指揮過");
    expect(commandBlocked(v, { ...hero, ap: 0 }, s, true)).toContain("AP 不足");
  });
  it("lists reachable tiles (not the origin) and the targets from a chosen tile", () => {
    const options = commandOptions();
    expect(commandMoveTiles(options)).toEqual([{ x: 2, y: 0 }]);
    expect(commandTargetTiles(optionAt(options, { x: 2, y: 0 }), view())).toEqual([{ x: 2, y: 1 }]);
    expect(commandTargetTiles(optionAt(options, { x: 1, y: 0 }), view())).toEqual([]);
    expect(optionAt(options, { x: 5, y: 5 })).toBeUndefined();
  });
  it("builds command_summon actions: path only when moving, nothing when there is nothing to do", () => {
    const [stay, move] = commandOptions().options;
    expect(commandAction(HERO, "unit_0006", stay!)).toBeNull();
    expect(commandAction(HERO, "unit_0006", stay!, "unit_0003")).toMatchObject({ path: [], target_id: "unit_0003" });
    expect(commandAction(HERO, "unit_0006", move!)).toMatchObject({ path: move!.path });
    expect(commandAction(HERO, "unit_0006", move!, "unit_0003")).toMatchObject({ target_id: "unit_0003" });
  });
  it("describes options in the dropdown", () => {
    const names = unitNames(view());
    const [stay, move] = commandOptions().options;
    expect(optionLabel(stay!, names)).toBe("原地");
    expect(optionLabel(move!, names)).toBe(`(2, 0)・可打 ${names.name("unit_0003")}`);
  });
});
