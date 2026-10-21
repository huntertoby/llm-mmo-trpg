import { describe, expect, it } from "vitest";
import { BASE_LEGEND } from "./legend";
import { LABEL_BURNING, LABEL_DEADLY, LABEL_TRAP, LABEL_ZONE, tileSections } from "./tileInfo";
import { object, smallView, tile } from "./testFixtures";
import { zoneLinesAt } from "./zones";
import { unitNames } from "./units";

const skills = { trap: "地刺陷阱" };
const at = (x: number, y: number) => ({ x, y });

function texts(view = smallView(), x = 0, y = 0, extra: string[] = []): string[] {
  return tileSections(view, at(x, y), skills, extra).flatMap((s) => [s.title, ...s.lines]);
}

describe("tileSections", () => {
  it("plain ground is a single line with the one rule inline", () => {
    const sections = tileSections(smallView(), at(0, 0), skills);
    expect(sections).toHaveLength(1);
    expect(sections[0]).toMatchObject({ kind: "terrain", title: "石地・高度 0・可通行", lines: [] });
  });

  it("shows height and multi-line terrain rules", () => {
    expect(texts(smallView(), 1, 0)[0]).toBe("石地・高度 2・可通行");
    const chasm = texts(smallView(), 3, 0);
    expect(chasm[0]).toBe("深淵・高度 0");
    expect(chasm.join("\n")).toContain("不可通行");
    expect(chasm.join("\n")).toContain(LABEL_DEADLY);
  });

  it("surface with remaining rounds and its rules", () => {
    const view = smallView();
    const tiles = view.tiles.map((t) =>
      t.x === 2 && t.y === 0 ? tile(2, 0, { surface: "ice", surface_remaining: 2 }) : t,
    );
    const lines = texts({ ...view, tiles }, 2, 0);
    expect(lines).toContain("冰・剩 2 回合");
    expect(lines.join("\n")).toContain("火焰：變成水");
  });

  it("object shows hp, burning and its rules", () => {
    const view = smallView();
    const lines = texts(view, 1, 2);
    expect(lines.some((l) => l.startsWith("木箱・HP 5/10・" + LABEL_BURNING))).toBe(true);
    expect(lines.join("\n")).toContain("半掩護");
    const barrel = texts(view, 2, 2).join("\n");
    expect(barrel).toContain("油桶・HP 5/10");
    expect(barrel).toContain("碰火爆炸");
  });

  it("temporary obstacle shows the remaining rounds", () => {
    const view = smallView({ objects: [object("o1", "ice_wall", 2, 0, { expires_in: 2 })] });
    const tiles = view.tiles.map((t) => (t.x === 2 && t.y === 0 ? tile(2, 0, { object_id: "o1" }) : t));
    expect(texts({ ...view, tiles }, 2, 0).join("\n")).toContain("冰牆・HP 5/10・剩 2 回合消失");
  });

  it("visible trap, zones and telegraph lines", () => {
    const lines = texts(smallView(), 1, 1, ["區域 火牆", "預告：下一輪起火"]);
    expect(lines).toContain(`${LABEL_TRAP}：地刺陷阱・剩 3 回合`);
    expect(lines).toContain(`${LABEL_ZONE}與預告`);
    expect(lines).toContain("預告：下一輪起火");
  });

  it("zone lines from the view flow into the card", () => {
    const view = smallView({
      zones: [
        {
          id: 1,
          owner_id: "unit_0001",
          team: "ally",
          skill_id: "s",
          name_zh: "火牆",
          anchor: "tile",
          affects: "enemies",
          when: "both",
          cells: [at(2, 0)],
          direction: null,
          speed: 0,
          expires_round: 3,
          harmful: true,
          next_cells: null,
        },
      ],
    });
    const extra = zoneLinesAt(view, at(2, 0), unitNames(view));
    expect(extra.length).toBe(1);
    expect(texts(view, 2, 0, extra).join("\n")).toContain("火牆");
  });

  it("empty for no hover or unknown tile", () => {
    expect(tileSections(smallView(), null, skills)).toEqual([]);
    expect(tileSections(smallView(), at(9, 9), skills)).toEqual([]);
  });
});

describe("legend uses the same terms", () => {
  it("legend labels contain the card labels", () => {
    const all = BASE_LEGEND.map((e) => e.label).join("\n");
    for (const term of [LABEL_DEADLY, LABEL_BURNING, LABEL_TRAP, LABEL_ZONE]) expect(all).toContain(term);
  });
});
