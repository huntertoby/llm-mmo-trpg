// 三方混戰的第三方（Phase 5B-M3）：代號、顏色、可攻擊目標。
import { describe, expect, it } from "vitest";
import { buildDrawModel } from "./drawModel";
import { TEAM_COLORS } from "./glossary";
import { smallView, unit } from "./testFixtures";
import { unitMarkers } from "./units";
import { RING } from "../render/artPalette";

const units = [
  unit("unit_0001", "ally", 0, 0),
  unit("unit_0002", "enemy", 3, 2),
  unit("unit_0003", "third", 2, 2),
  unit("unit_0004", "third", 2, 1),
];

describe("third team", () => {
  it("uses reversed lowercase markers for the third team", () => {
    const markers = unitMarkers(units);
    expect([...markers.values()]).toEqual(["A", "a", "z", "y"]);
  });

  it("has its own colour, distinct from ally, enemy and summons", () => {
    const model = buildDrawModel(smallView({ units }), "unit_0001");
    const third = model.units.find((u) => u.id === "unit_0003")!;
    expect(third.team).toBe("third");
    expect(third.fill).toBe(TEAM_COLORS.third);
    expect(new Set([TEAM_COLORS.ally, TEAM_COLORS.enemy, TEAM_COLORS.third]).size).toBe(3);
    expect(new Set([RING.ally.fill, RING.enemy.fill, RING.third.fill, RING.summon.fill]).size).toBe(4);
  });
});
