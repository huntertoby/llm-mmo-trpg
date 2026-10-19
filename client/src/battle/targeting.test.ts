import { describe, expect, it } from "vitest";
import type { Action, SkillCard } from "../api/types";
import realFixture from "./fixtures/oil_depot_seed3.json";
import { smallView, unit } from "./testFixtures";
import {
  actionAtTile,
  basicModes,
  buildTargets,
  fallbackActions,
  isSelfOnly,
  skillButtons,
  skillMode,
  targetTiles,
} from "./targeting";

const H = "unit_0001";
const skill = (id: string, extra: Record<string, unknown> = {}): Action =>
  ({ type: "use_skill", unit_id: H, skill_id: id, ...extra }) as Action;
const hero = unit(H, "ally", 1, 1, { skills: ["blink", "slash", "nova", "wind_cut"], cooldowns: { nova: 2 } });
const view = smallView({ units: [hero, unit("unit_0003", "enemy", 2, 1)] });
const card = (id: string, name: string, cost: string[]): SkillCard => ({ id, name_zh: name, cost }) as SkillCard;

describe("buildTargets", () => {
  it("classifies unit, tile, direction and self targets", () => {
    const t = buildTargets([
      skill("a", { target_id: "unit_0003" }),
      skill("a", { target_pos: { x: 2, y: 2 } }),
      skill("a", { direction: "east" }),
      skill("a"),
    ]);
    expect([...t.units.keys()]).toEqual(["unit_0003"]);
    expect([...t.tiles.keys()]).toEqual(["2,2"]);
    expect([...t.directions.keys()]).toEqual(["east"]);
    expect(t.self).not.toBeNull();
    expect(isSelfOnly(t)).toBe(false);
  });

  it("recognises a self-only skill", () => {
    expect(isSelfOnly(buildTargets([skill("buff")]))).toBe(true);
  });

  it("keeps the first action when several reach the same target", () => {
    const first = skill("a", { target_pos: { x: 2, y: 2 } });
    const t = buildTargets([first, skill("a", { target_pos: { x: 2, y: 2 }, direction: "north" })]);
    expect(t.tiles.get("2,2")).toBe(first);
  });
});

describe("skillButtons", () => {
  const legal: Action[] = [
    skill("blink", { target_pos: { x: 3, y: 2 } }),
    skill("blink", { target_pos: { x: 0, y: 2 } }),
    skill("nova", { direction: "north" }),
    { type: "end_turn", unit_id: H },
  ];
  const buttons = skillButtons(hero, legal, { blink: card("blink", "閃現", ["AP 2", "法力 4"]) });

  it("lists every equipped skill with names and costs from the card", () => {
    expect(buttons.map((b) => b.skillId)).toEqual(["blink", "slash", "nova", "wind_cut"]);
    expect(buttons[0]).toMatchObject({ name: "閃現", costs: ["AP 2", "法力 4"], disabledReason: null });
    expect(buttons[0]!.actions).toHaveLength(2);
    expect(buttons[1]!.name).toBe("slash");
  });

  it("disables skills on cooldown (even with legal actions) and skills without legal targets", () => {
    expect(buttons[2]).toMatchObject({ cooldown: 2 });
    expect(buttons[2]!.disabledReason).toContain("冷卻中");
    expect(buttons[1]!.disabledReason).toContain("沒有合法目標");
    expect(buttons[3]!.disabledReason).not.toBeNull();
  });
});

describe("modes and clicks", () => {
  const legal: Action[] = [
    { type: "attack", unit_id: H, target_id: "unit_0003" },
    { type: "shove", unit_id: H, target_id: "unit_0003", direction: "east" } as Action,
    { type: "interact", unit_id: H, object_id: "obj_0001" } as Action,
    { type: "defend", unit_id: H },
    { type: "move", unit_id: H, path: [{ x: 1, y: 1 }] },
    { type: "move", unit_id: H, path: [{ x: 1, y: 1 }, { x: 1, y: 0 }] },
    skill("blink", { target_pos: { x: 3, y: 2 } }),
    skill("wind_cut", { direction: "east" }),
  ];

  it("builds the basic modes, treating a one-tile move as standing up", () => {
    expect(basicModes(legal).map((m) => m.kind)).toEqual(["attack", "shove", "interact", "defend", "stand"]);
    expect(fallbackActions(legal, hero)).toEqual([]);
  });

  it("resolves a click to a unit, an object, a tile or an adjacent direction tile", () => {
    const attack = basicModes(legal).find((m) => m.kind === "attack")!;
    expect(actionAtTile(attack, view, hero, { x: 2, y: 1 })).toBe(legal[0]);
    expect(actionAtTile(attack, view, hero, { x: 3, y: 2 })).toBeNull();
    const interact = basicModes(legal).find((m) => m.kind === "interact")!;
    expect(actionAtTile(interact, view, hero, { x: 2, y: 2 })).toBe(legal[2]);
    const buttons = skillButtons(hero, legal, {});
    const blink = skillMode(buttons[0]!);
    expect(actionAtTile(blink, view, hero, { x: 3, y: 2 })).toBe(legal[6]);
    const wind = skillMode(buttons[3]!);
    expect(actionAtTile(wind, view, hero, { x: 2, y: 1 })).toBe(legal[7]);
    expect(actionAtTile(wind, view, hero, { x: 0, y: 1 })).toBeNull();
  });

  it("lists target tiles for highlighting", () => {
    const buttons = skillButtons(hero, legal, {});
    const wind = skillMode(buttons[3]!);
    expect(targetTiles(wind, view, hero)).toEqual({ targets: [], directions: [{ pos: { x: 2, y: 1 }, direction: "east" }] });
    const blink = skillMode(buttons[0]!);
    expect(targetTiles(blink, view, hero).targets).toEqual([{ x: 3, y: 2 }]);
    const attack = basicModes(legal)[0]!;
    expect(targetTiles(attack, view, hero).targets).toEqual([{ x: 2, y: 1 }]);
  });
});

describe("a real response", () => {
  it("never leaves skills in the fallback list; every skill action lands on a button", () => {
    const real = realFixture as unknown as {
      legal_actions: Action[];
      view: { units: { id: string }[] };
      hero_id: string;
    };
    const h = (real.view.units as unknown as ReturnType<typeof smallView>["units"]).find(
      (u) => u.id === real.hero_id,
    )!;
    const skills = real.legal_actions.filter((a) => a.type === "use_skill");
    expect(skills.length).toBeGreaterThan(0);
    expect(fallbackActions(real.legal_actions, h)).toEqual([]);
    const buttons = skillButtons(h, real.legal_actions, {});
    expect(buttons.reduce((n, b) => n + b.actions.length, 0)).toBe(skills.length);
  });
});
