import { describe, expect, it } from "vitest";
import { areaCenter, feedbackFor, type FeedbackItem, type FloatItem } from "./feedback";
import { smallView } from "./testFixtures";

// smallView：unit_0001 (0,0) 我方、unit_0003 (2,1) 敵、unit_0004 (2,0) 敵
const view = smallView();
const ev = (type: string, extra: Record<string, unknown> = {}) => ({ seq: 1, round: 1, type, ...extra });
const floats = (items: FeedbackItem[]): FloatItem[] => items.filter((i): i is FloatItem => i.kind === "float");
const texts = (items: FeedbackItem[]) => floats(items).map((f) => [f.text, f.tone, f.pos.x, f.pos.y]);

describe("feedbackFor: numbers", () => {
  it("shows damage as red minus, bigger on a crit, none for 0", () => {
    const items = feedbackFor(
      [
        ev("damage_dealt", { target_id: "unit_0003", amount: 12, crit: false }),
        ev("damage_dealt", { target_id: "unit_0004", amount: 20, crit: true }),
        ev("damage_dealt", { target_id: "unit_0004", amount: 0, crit: false }),
      ],
      view,
    );
    expect(texts(items)).toEqual([
      ["−12", "damage", 2, 1],
      ["−20", "damage", 2, 0],
    ]);
    expect(floats(items).map((f) => f.big)).toEqual([false, true]);
  });

  it("shows heals green and shields in their own tone", () => {
    const items = feedbackFor(
      [
        ev("healed", { target_id: "unit_0001", amount: 8 }),
        ev("shield_gained", { unit_id: "unit_0001", amount: 5 }),
        ev("shield_absorbed", { unit_id: "unit_0003", absorbed: 4 }),
      ],
      view,
    );
    expect(texts(items)).toEqual([
      ["＋8", "heal", 0, 0],
      ["＋5盾", "shield", 0, 0],
      ["吸收 4", "shield", 2, 1],
    ]);
  });

  it("shows damage to an object and redirected damage", () => {
    const items = feedbackFor(
      [ev("object_damaged", { pos: { x: 2, y: 2 }, amount: 3 }), ev("damage_redirected", { to_id: "unit_0004", amount: 6 })],
      view,
    );
    expect(texts(items)).toEqual([
      ["−3", "damage", 2, 2],
      ["−6", "damage", 2, 0],
    ]);
  });

  it("staggers several numbers on the same tile with increasing slots", () => {
    const items = feedbackFor(
      [ev("damage_dealt", { target_id: "unit_0003", amount: 1 }), ev("damage_dealt", { target_id: "unit_0003", amount: 2 })],
      view,
    );
    expect(floats(items).map((f) => f.slot)).toEqual([0, 1]);
  });
});

describe("feedbackFor: words", () => {
  it("maps miss, backstab, ambush and block", () => {
    const items = feedbackFor(
      [
        ev("attack_rolled", { attacker_id: "unit_0001", target_id: "unit_0003", hit: false }),
        ev("attack_rolled", { attacker_id: "unit_0001", target_id: "unit_0004", hit: true, backstab: 2 }),
        ev("attack_rolled", { attacker_id: "unit_0001", target_id: "unit_0004", hit: true, ambush: 1 }),
        ev("reaction_triggered", { unit_id: "unit_0003", reaction: "block" }),
        ev("reaction_triggered", { unit_id: "unit_0003", reaction: "opportunity_attack" }),
      ],
      view,
    );
    expect(texts(items).map((t) => t[0])).toEqual(["失手", "背刺！", "伏擊！", "格擋"]);
  });

  it("maps collisions, falls, deadly terrain, resists, downs and revives", () => {
    const items = feedbackFor(
      [
        ev("collided", { unit_id: "unit_0003", pos: { x: 3, y: 1 } }),
        ev("unit_fell", { unit_id: "unit_0003" }),
        ev("entered_deadly_terrain", { unit_id: "unit_0004", pos: { x: 3, y: 0 } }),
        ev("status_resisted", { target_id: "unit_0004", status_id: "burn" }),
        ev("push_resisted", { unit_id: "unit_0001" }),
        ev("maneuver_rolled", { target_id: "unit_0003", success: false }),
        ev("maneuver_rolled", { target_id: "unit_0003", success: true }),
        ev("unit_downed", { unit_id: "unit_0003" }),
        ev("unit_revived", { unit_id: "unit_0001" }),
      ],
      view,
    );
    expect(texts(items).map((t) => t[0])).toEqual([
      "撞擊！",
      "墜落",
      "致命地形",
      "抵抗",
      "抵抗",
      "抵抗",
      "擊倒",
      "復活",
    ]);
    expect(floats(items)[0]!.big).toBe(true);
  });

  it("ignores events without feedback and unknown units", () => {
    const items = feedbackFor(
      [ev("round_started"), ev("turn_started", { unit_id: "unit_0001" }), ev("healed", { target_id: "ghost", amount: 3 })],
      view,
    );
    expect(items).toEqual([]);
  });
});

describe("feedbackFor: lines and statuses", () => {
  it("draws attacker to single target once", () => {
    const hit = ev("attack_rolled", { attacker_id: "unit_0001", target_id: "unit_0003", hit: true });
    const items = feedbackFor([hit, hit], view);
    expect(items.filter((i) => i.kind === "line")).toEqual([{ kind: "line", from: { x: 0, y: 0 }, to: { x: 2, y: 1 } }]);
  });

  it("draws an area skill to the centre of its tiles, not to itself", () => {
    const tiles = [{ x: 1, y: 1 }, { x: 2, y: 1 }, { x: 3, y: 1 }, { x: 2, y: 0 }, { x: 2, y: 2 }];
    const items = feedbackFor([ev("skill_used", { unit_id: "unit_0001", tiles })], view);
    expect(items).toEqual([{ kind: "line", from: { x: 0, y: 0 }, to: { x: 2, y: 1 } }]);
    expect(feedbackFor([ev("skill_used", { unit_id: "unit_0001", tiles: [{ x: 0, y: 0 }] })], view)).toEqual([]);
  });

  it("pops a status icon with its name (the id when the glossary has none)", () => {
    const items = feedbackFor([ev("status_applied", { target_id: "unit_0003", status_id: "no_such_status" })], view);
    expect(items).toEqual([{ kind: "status", pos: { x: 2, y: 1 }, text: "no_such_status", slot: 0 }]);
  });

  it("areaCenter picks the tile closest to the average", () => {
    expect(areaCenter([{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }])).toEqual({ x: 1, y: 0 });
  });
});
