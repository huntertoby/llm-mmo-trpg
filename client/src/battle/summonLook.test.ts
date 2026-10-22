import { describe, expect, it } from "vitest";
import { buildDrawModel } from "./drawModel";
import { smallView, unit } from "./testFixtures";

describe("召喚物外觀欄位進繪製模型（Phase 3-33h1）", () => {
  const base = smallView({ round: 2 });
  const look = { body: "beast", variant: "wolf", element: "prone", size: "medium", trait: null };
  const wolf = unit("unit_0006", "ally", 1, 0, { owner_id: "unit_0001", summon_look: look });
  const plain = unit("unit_0007", "ally", 2, 0, { owner_id: "unit_0001" });
  const ghost = unit("unit_0008", "ally", 3, 0, {
    owner_id: "unit_0001",
    summon_look: { body: "humanoid", variant: "afterimage", element: "concealed", size: "medium", trait: "translucent" },
  });
  const view = { ...base, units: [...base.units, wolf, plain, ghost] };

  it("帶出外觀；沒有外觀的召喚物與一般單位為 null", () => {
    const draws = new Map(buildDrawModel(view, "unit_0001").units.map((u) => [u.id, u]));
    expect(draws.get("unit_0006")?.summonLook).toEqual(look);
    expect(draws.get("unit_0007")?.summonLook).toBeNull();
    expect(draws.get("unit_0001")?.summonLook).toBeNull();
    expect(draws.get("unit_0006")?.copyOf).toBeUndefined();
  });

  it("殘影分身帶出召喚者的紙娃娃輸入", () => {
    const draws = new Map(buildDrawModel(view, "unit_0001").units.map((u) => [u.id, u]));
    const owner = view.units.find((u) => u.id === "unit_0001");
    expect(draws.get("unit_0008")?.copyOf).toMatchObject({ template: owner?.template_id, summon: false });
  });
});
