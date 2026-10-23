import { describe, expect, it } from "vitest";
import { fireOnField, flameEmphasis, skillIgnites, type IgniteCard } from "./flameMarks";

const tile = (surface: string) => ({ surface }) as never;
const field = (o: { surface?: string; burningObject?: boolean; statuses?: string[] } = {}) => ({
  tiles: [tile("none"), tile(o.surface ?? "none")],
  objects: [{ burning: o.burningObject === true }] as never,
  units: [{ statusIds: o.statuses ?? [] }] as never,
});
const card = (makes: string[], elements: string[]): IgniteCard => ({
  keywords: { makes: makes.map((id) => ({ id })) },
  icon: { elements },
});

describe("可燃標記明顯判斷", () => {
  it.each([
    ["沒選技能、場上沒火", field(), null, false],
    ["選取製造 ignite 的技能", field(), card(["ignite"], []), true],
    ["選取火元素技能", field(), card([], ["fire"]), true],
    ["選取其他技能", field(), card(["prone"], ["ice"]), false],
    ["格子有火表面", field({ surface: "fire" }), null, true],
    ["油表面不算火", field({ surface: "oil" }), null, false],
    ["物件燃燒中", field({ burningObject: true }), null, true],
    ["單位燃燒中", field({ statuses: ["burning"] }), null, true],
    ["單位有別的狀態", field({ statuses: ["poison"] }), null, false],
    ["技能卡還沒載入", field(), undefined, false],
  ])("%s", (_name, model, selected, expected) => {
    expect(flameEmphasis(model, selected)).toBe(expected);
  });

  it("單項判斷", () => {
    expect(skillIgnites({})).toBe(false);
    expect(fireOnField(field())).toBe(false);
  });
});
