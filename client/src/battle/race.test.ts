import { describe, expect, it } from "vitest";
import type { Action, RaceView } from "../api/types";
import { actionLabel } from "./actions";
import { passiveLine, raceBlockedReason, raceCardLines, raceHudText, raceLabel, raceModes, raceUsesText } from "./race";
import { actionAtTile, basicModes, fallbackActions, isSelfOnly } from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const FOE = "unit_0002";

function race(over: Partial<RaceView> = {}): RaceView {
  return {
    id: "seafolk",
    name_zh: "海民",
    skill_id: "race_anchor_haul",
    skill_name_zh: "拋錨",
    skill_description_zh: "把 4 格內一個敵人拉近 2 格，不造成撞擊傷害。每場限用 1 次。",
    skill_ap: 1,
    skill_uses_max: 1,
    skill_uses_left: 1,
    skill_shape: "single",
    skill_range: 4,
    skill_size: null,
    skill_choices: [],
    passive_name_zh: "雨中海步",
    passive_description_zh: "下雨天氣時，移動 +1。",
    passive_active: false,
    ...over,
  };
}

const pull = { type: "use_race_skill", unit_id: H, target_id: FOE } as Action;

describe("race skill modes (Phase 3R-2)", () => {
  it("has no race modes without a race", () => {
    expect(raceModes(unit(H, "ally", 1, 1), [pull])).toEqual([]);
    expect(raceModes(null, [pull])).toEqual([]);
  });

  it("makes one race mode whose targets are the legal units", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    const [mode] = raceModes(hero, [pull]);
    expect(mode?.kind).toBe("race");
    expect(mode?.label).toBe("拋錨");
    expect(mode?.targets.units.get(FOE)).toBe(pull);
    expect(mode?.blockedReason).toBeUndefined();
  });

  it("is a self-only instant mode for self skills", () => {
    const self = { type: "use_race_skill", unit_id: H } as Action;
    const hero = unit(H, "ally", 1, 1, { race: race({ skill_shape: "self", skill_name_zh: "應變" }) });
    const [mode] = raceModes(hero, [self]);
    expect(mode !== undefined && isSelfOnly(mode.targets)).toBe(true);
    expect(mode?.targets.self).toBe(self);
  });

  it("splits Overcharge into one mode per resource", () => {
    const stamina = { type: "use_race_skill", unit_id: H, choice: "stamina" } as Action;
    const mana = { type: "use_race_skill", unit_id: H, choice: "mana" } as Action;
    const hero = unit(H, "ally", 1, 1, {
      race: race({ skill_shape: "self", skill_name_zh: "過充", skill_choices: ["stamina", "mana"] }),
    });
    const modes = raceModes(hero, [stamina, mana]);
    expect(modes.map((m) => m.label)).toEqual(["過充（耐力）", "過充（法力）"]);
    expect(modes.map((m) => m.targets.self)).toEqual([stamina, mana]);
    expect(modes.map((m) => m.key)).toEqual(["race:stamina", "race:mana"]);
  });

  it("registers a hurl as two stages: the object first, then the landing tile", () => {
    const hurl = { type: "use_race_skill", unit_id: H, target_object_id: "obj_1", target_pos: { x: 3, y: 1 } } as Action;
    const hero = unit(H, "ally", 1, 1, { race: race({ skill_shape: "object_then_tile", skill_name_zh: "蠻力投擲" }) });
    const [mode] = raceModes(hero, [hurl]);
    expect(mode?.targets.pairKind).toBe("hurl");
    expect(mode?.targets.hurls.get("obj_1")?.get("3,1")).toBe(hurl);
  });

  it("registers cone directions and ground tiles", () => {
    const breath = { type: "use_race_skill", unit_id: H, direction: "east" } as Action;
    const tile = { type: "use_race_skill", unit_id: H, target_pos: { x: 2, y: 1 } } as Action;
    const hero = unit(H, "ally", 1, 1, { race: race({ skill_shape: "cone" }) });
    expect(raceModes(hero, [breath])[0]?.targets.directions.get("east")).toBe(breath);
    expect(raceModes(hero, [tile])[0]?.targets.tiles.get("2,1")).toBe(tile);
  });

  it("explains why the button is grey", () => {
    const hero = unit(H, "ally", 1, 1, { ap: 0, race: race() });
    expect(raceBlockedReason(hero, race(), false)).toMatch(/AP 不足/);
    expect(raceBlockedReason(hero, race({ skill_uses_left: 0 }), false)).toMatch(/本場已用完/);
    expect(raceBlockedReason(unit(H, "ally", 1, 1, { ap: 2 }), race(), false)).toMatch(/沒有合法的目標/);
    expect(raceBlockedReason(hero, race(), true)).toBeUndefined();
    const [mode] = raceModes(hero, []);
    expect(mode?.blockedReason).toMatch(/AP 不足/);
  });

  it("keeps race skills out of the basic and fallback actions", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    expect(basicModes([pull])).toEqual([]);
    expect(fallbackActions([pull], hero)).toEqual([]);
  });

  it("labels the action with the race skill name and its target", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    const view = smallView({ units: [hero, unit(FOE, "enemy", 4, 1)] });
    expect(actionLabel(pull, view, {})).toBe("種族技：拋錨 → a 單位2");
    expect(actionLabel({ type: "use_race_skill", unit_id: H, choice: "mana" } as Action, view, {})).toBe("種族技：拋錨 → 法力");
  });

  it("picks the unit under the cursor for a single-target race mode", () => {
    const hero = unit(H, "ally", 1, 1, { race: race() });
    const view = smallView({ units: [hero, unit(FOE, "enemy", 4, 1)] });
    const [mode] = raceModes(hero, [pull]);
    expect(mode !== undefined && actionAtTile(mode, view, hero, { x: 4, y: 1 })).toBe(pull);
  });
});

describe("race text", () => {
  it("builds the card lines from the same data the engine uses", () => {
    const lines = raceCardLines(race());
    expect(lines[0]).toContain("拉近 2 格");
    expect(lines[1]).toBe("花費 1 AP・本場限用 1 次（剩 1 次）・不佔技能欄");
    expect(lines[2]).toBe("選一個目標・射程 4 格");
  });

  it("formats labels, uses and the passive line", () => {
    expect(raceLabel(race(), "")).toBe("拋錨");
    expect(raceLabel(race(), "stamina")).toBe("拋錨（耐力）");
    expect(raceUsesText(race({ skill_uses_left: 0 }))).toBe("1 AP・剩 0／1 次");
    expect(passiveLine(race())).toBe("被動・雨中海步：下雨天氣時，移動 +1。");
    expect(passiveLine(race({ passive_active: true }))).toContain("（目前有作用）");
  });

  it("writes one HUD line only for raced heroes", () => {
    expect(raceHudText(unit(H, "ally", 1, 1))).toBeNull();
    const hero = unit(H, "ally", 1, 1, { race: race({ passive_active: true }) });
    expect(raceHudText(hero)).toBe("種族：海民｜拋錨 剩 1／1 次｜被動：雨中海步（目前有作用）");
  });
});
