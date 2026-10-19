import { describe, expect, it } from "vitest";
import type { Action } from "../api/types";
import { actionForClick, actionLabel, classifyActions, skillIdsOf } from "./actions";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const p = (x: number, y: number) => ({ x, y });

const LEGAL: Action[] = [
  { type: "move", unit_id: H, path: [p(0, 0), p(1, 0)] },
  { type: "move", unit_id: H, path: [p(0, 0), p(1, 0), p(1, 1)] },
  { type: "move", unit_id: H, path: [p(0, 0), p(0, 1), p(1, 1)] }, // 同一格第二條路徑：忽略
  { type: "attack", unit_id: H, target_id: "unit_0004" },
  { type: "attack", unit_id: H, target_object_id: "obj_0001" },
  { type: "use_skill", unit_id: H, skill_id: "skill_fire", target_id: "unit_0003" },
  { type: "use_skill", unit_id: H, skill_id: "skill_cone", direction: "east" },
  { type: "use_skill", unit_id: H, skill_id: "skill_aoe", target_pos: p(2, 2) },
  { type: "use_skill", unit_id: H, skill_id: "skill_self" },
  { type: "shove", unit_id: H, target_id: "unit_0004" },
  { type: "trip", unit_id: H, target_id: "unit_0004" },
  { type: "interact", unit_id: H, object_id: "obj_0001", mode: "push" },
  { type: "defend", unit_id: H },
  { type: "end_stance", unit_id: H },
  { type: "end_turn", unit_id: H },
];
const SKILLS = { skill_fire: "火球", skill_cone: "烈焰吐息", skill_aoe: "爆裂" };

describe("classifyActions", () => {
  const view = smallView();
  const c = classifyActions(LEGAL, view, SKILLS);

  it("collects move destinations, keeping the first path per tile", () => {
    expect([...c.moves.keys()]).toEqual(["1,0", "1,1"]);
    expect(c.moves.get("1,1")?.path).toHaveLength(3);
    expect(c.moves.get("1,1")?.path[1]).toEqual(p(1, 0));
  });

  it("collects attacks on enemy units only", () => {
    expect([...c.attacks.keys()]).toEqual(["unit_0004"]);
  });

  it("lists every other action once with a Chinese label", () => {
    expect(c.others.map((o) => o.label)).toEqual([
      "攻擊：油桶 (2, 2)",
      "技能：火球 → a 單位3",
      "技能：烈焰吐息 → 向東",
      "技能：爆裂 → (2, 2)",
      "技能：skill_self",
      "推擊：b 單位4",
      "絆倒：b 單位4",
      "推動：油桶 (2, 2)",
      "防禦",
      "結束姿態",
    ]);
    expect(c.endTurn).toEqual({ type: "end_turn", unit_id: H });
  });

  it("puts every legal action in exactly one bucket (except duplicate move paths)", () => {
    const total = c.moves.size + c.attacks.size + c.others.length + (c.endTurn === null ? 0 : 1);
    expect(total).toBe(LEGAL.length - 1);
  });

  it("treats a prone stand-up (path of one tile) as another action", () => {
    const up: Action = { type: "move", unit_id: H, path: [p(0, 0)] };
    const c2 = classifyActions([up], view, {});
    expect(c2.moves.size).toBe(0);
    expect(c2.others).toEqual([{ action: up, label: "起身" }]);
  });

  it("attacks on allies are not click targets", () => {
    const v = smallView({ units: [unit(H, "ally", 0, 0), unit("unit_0002", "ally", 1, 0)] });
    const c3 = classifyActions([{ type: "attack", unit_id: H, target_id: "unit_0002" }], v, {});
    expect(c3.attacks.size).toBe(0);
    expect(c3.others[0]?.label).toBe("攻擊：B 單位2");
  });
});

describe("actionForClick", () => {
  const view = smallView();
  const c = classifyActions(LEGAL, view, SKILLS);

  it("attacks an attackable enemy on the clicked tile", () => {
    expect(actionForClick(c, view, p(2, 0))).toEqual(LEGAL[3]);
  });

  it("moves to a reachable tile", () => {
    expect(actionForClick(c, view, p(1, 1))).toBe(c.moves.get("1,1"));
  });

  it("does nothing on an unreachable tile or a non-attackable enemy", () => {
    expect(actionForClick(c, view, p(3, 2))).toBeNull();
    expect(actionForClick(c, view, p(2, 1))).toBeNull(); // unit_0003 沒有普攻動作
  });
});

describe("labels and skill ids", () => {
  it("labels a move and end turn", () => {
    const view = smallView();
    expect(actionLabel({ type: "move", unit_id: H, path: [p(0, 0), p(1, 0)] }, view, {})).toBe("移動到 (1, 0)");
    expect(actionLabel({ type: "end_turn", unit_id: H }, view, {})).toBe("結束回合");
  });

  it("collects skill ids from legal actions and ally loadouts, sorted", () => {
    const view = smallView({ units: [unit(H, "ally", 0, 0, { skills: ["skill_z", "skill_fire"] })] });
    expect(skillIdsOf(LEGAL, view)).toEqual(["skill_aoe", "skill_cone", "skill_fire", "skill_self", "skill_z"]);
  });
});
