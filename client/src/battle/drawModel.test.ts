import { describe, expect, it } from "vitest";
import { buildDrawModel, shadeForHeight, tileAt, tileFill } from "./drawModel";
import { surfaceName, TERRAIN, TEAM_COLORS } from "./glossary";
import { smallView, unit } from "./testFixtures";
import { isAlive, onField } from "./units";

describe("buildDrawModel", () => {
  const model = buildDrawModel(smallView(), "unit_0001");

  it("keeps the grid size and one tile per cell in row-major order", () => {
    expect(model.width).toBe(4);
    expect(model.height).toBe(3);
    expect(model.tiles).toHaveLength(12);
    expect(tileAt(model, { x: 3, y: 1 })?.terrain).toBe("wall");
  });

  it("colours tiles by terrain and surface, shaded by height", () => {
    const flat = tileAt(model, { x: 0, y: 1 })!;
    const high = tileAt(model, { x: 1, y: 0 })!;
    expect(flat.fill).toBe(shadeForHeight(TERRAIN.stone!.color, 0));
    expect(high.fill).toBe(shadeForHeight(TERRAIN.stone!.color, 2));
    expect(high.heightLabel).toBe("2");
    const oil = tileAt(model, { x: 0, y: 2 })!;
    expect(oil.fill).not.toBe(flat.fill);
    expect(oil.surfaceName).toBe(surfaceName("oil"));
  });

  it("marks walls, chasms and deadly terrain", () => {
    const chasm = tileAt(model, { x: 3, y: 0 })!;
    expect(chasm).toMatchObject({ blocked: true, deadly: true, wall: false, terrainName: "深淵" });
    expect(chasm.fill).toBe(TERRAIN.chasm!.color); // 洞不做高度明暗
    expect(tileAt(model, { x: 3, y: 1 })).toMatchObject({ blocked: true, deadly: false, wall: true });
  });

  it("places units with markers, hp bars and outlines; escaped units are removed", () => {
    expect(model.units.map((u) => u.id)).toEqual(["unit_0002", "unit_0001", "unit_0003", "unit_0004"]);
    const hero = model.units.find((u) => u.id === "unit_0001")!;
    expect(hero).toMatchObject({ x: 0, y: 0, marker: "A", hero: true, active: true, hpRatio: 0.5 });
    expect(hero.fill).toBe(TEAM_COLORS.ally);
    const downed = model.units.find((u) => u.id === "unit_0002")!;
    expect(downed).toMatchObject({ marker: "B", downed: true, hero: false, hpRatio: 0 });
    const enemy = model.units.find((u) => u.id === "unit_0003")!;
    expect(enemy).toMatchObject({ marker: "a", team: "enemy", active: false });
    expect(model.units.find((u) => u.id === "unit_0004")?.marker).toBe("b");
  });

  it("marks a downed ally that can still be revived and shows a bomb countdown (Phase 3D-8b)", () => {
    const view = smallView();
    const ally = unit("unit_0002", "ally", 0, 1, { hp: 0, downed: true, revivable: true });
    const used = unit("unit_0006", "ally", 3, 2, { hp: 0, downed: true, revivable: false });
    const carrier = unit("unit_0003", "enemy", 2, 1, {
      statuses: [{ status_id: "time_bomb", remaining: 2, source_id: "unit_0001", amount: null, blast_radius: 1 }],
    });
    const units = [view.units[0]!, ally, used, carrier];
    const drawn = buildDrawModel({ ...view, units }, "unit_0001");
    expect(drawn.units.find((u) => u.id === "unit_0002")).toMatchObject({ downed: true, revivable: true, bomb: null });
    expect(drawn.units.find((u) => u.id === "unit_0006")).toMatchObject({ downed: true, revivable: false });
    expect(drawn.units.find((u) => u.id === "unit_0003")).toMatchObject({ downed: false, bomb: 2 });
    expect(drawn.units.find((u) => u.id === "unit_0001")?.bomb).toBeNull();
  });

  it("draws summons like other units and removes dismissed summons (Phase 3D-4a)", () => {
    const view = smallView();
    const summoned = unit("unit_0006", "ally", 3, 0, { owner_id: "unit_0001", summon_expires_round: 3 });
    const gone = unit("unit_0007", "ally", 3, 2, { owner_id: "unit_0001", dismissed: true });
    const drawn = buildDrawModel({ ...view, units: [...view.units, summoned, gone] }, "unit_0001");
    expect(drawn.units.map((u) => u.id)).toContain("unit_0006");
    expect(drawn.units.map((u) => u.id)).not.toContain("unit_0007");
    expect(isAlive(gone)).toBe(false);
    expect(onField(gone)).toBe(false);
    expect(isAlive(summoned)).toBe(true);
  });

  it("distinguishes flammable and burning objects and shows traps", () => {
    const barrel = model.objects.find((o) => o.id === "obj_0001")!;
    const crate = model.objects.find((o) => o.id === "obj_0002")!;
    expect(barrel).toMatchObject({ name: "油桶", flammable: true, burning: false, hpRatio: 0.5 });
    expect(crate).toMatchObject({ name: "木箱", burning: true });
    expect(model.traps).toEqual([expect.objectContaining({ x: 1, y: 1 })]);
  });
});

describe("colours", () => {
  it("higher tiles are brighter", () => {
    const c = TERRAIN.grass!.color;
    const lum = (x: number) => ((x >> 16) & 255) + ((x >> 8) & 255) + (x & 255);
    expect(lum(shadeForHeight(c, 3))).toBeGreaterThan(lum(shadeForHeight(c, 1)));
    expect(lum(shadeForHeight(c, 1))).toBeGreaterThan(lum(shadeForHeight(c, 0)));
  });

  it("unknown terrain falls back without throwing", () => {
    expect(typeof tileFill("mystery", "none", 1)).toBe("number");
  });
});
