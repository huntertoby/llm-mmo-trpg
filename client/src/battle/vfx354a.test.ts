// Phase 3-54a 吹送：沒有傷害的吹送技能用風的特效配色。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { vfxFor } from "./vfx";

const CASTER = "u_hero";
const at = (x: number, y: number): Pos => ({ x, y });
const view = { units: [{ id: CASTER, pos: at(2, 2) }] } as unknown as BattleView;
const cards: Record<string, SkillCard> = { skill_x: { id: "skill_x", shape: "直線（2 格）", skeleton: "control" } as unknown as SkillCard };
const used = { seq: 1, round: 1, type: "skill_used", unit_id: CASTER, skill_id: "skill_x", tiles: [at(3, 2), at(4, 2)] };
const blown = (source: string) => ({ seq: 2, round: 1, type: "surface_blown", source_id: source, from_pos: at(3, 2), to_pos: at(5, 2), surface: "fire", direction: [1, 0] });

describe("吹送技能的特效", () => {
  it("施放者吹動表面：配色是風", () => {
    expect(vfxFor([used, blown(CASTER)], view, cards).casts[0]!.element).toBe("wind");
  });
  it("不是施放者吹的不算", () => {
    expect(vfxFor([used, blown("u_other")], view, cards).casts[0]!.element).not.toBe("wind");
  });
});
