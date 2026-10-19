import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { directionText, previewOverlays, sceneLines } from "./scenePreview";
import { previewLines } from "./previewText";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

// smallView：桶子 obj_0001 (2,2)、木箱 obj_0002 (1,2)；敵人 unit_0003 (2,1)、unit_0004 (2,0)。
const view = smallView();
const names = unitNames(view);
const base = {
  action: { type: "end_turn", unit_id: "unit_0001" },
  hit_permille: null,
  crit_permille: null,
  damage: null,
  affected_tiles: [],
  affected_units: [],
  certain: [],
  possible: [],
  cover: null,
  notes: [],
  targets: [],
  healed: [],
  min_events: [],
  max_events: [],
} as unknown as PreviewOut;

const pierce = {
  route: [[1, 0], [2, 0]],
  objects: [{ object_id: "obj_0002", pos: [1, 0] }],
  behind: ["unit_0004"],
  behind_permille: 700,
};
const topple = {
  object_id: "obj_0001",
  pos: [2, 2],
  direction: [0, -1],
  tiles: [[2, 1], [2, 0]],
  units: ["unit_0003", "unit_0004"],
  rubble: [2, 0],
};
const hurl = { object_id: "obj_0001", kind: "oil_barrel", from_pos: [2, 2], to_pos: [3, 2], outcome: "exploded", placed_pos: null };

describe("previewOverlays", () => {
  it("is empty without scene data (older servers and plain actions)", () => {
    expect(previewOverlays(null, view)).toEqual([]);
    expect(previewOverlays(base, view)).toEqual([]);
  });

  it("marks the pierce route, the pierced objects and the units behind them", () => {
    const marks = previewOverlays({ ...base, pierce } as unknown as PreviewOut, view);
    // 穿過的物件所在格只畫「穿」，不重複畫路線點
    expect(marks.filter((m) => m.kind === "route").map((m) => m.pos)).toEqual([{ x: 2, y: 0 }]);
    expect(marks.filter((m) => m.kind === "pierced")).toEqual([{ pos: { x: 1, y: 0 }, kind: "pierced", label: "穿" }]);
    expect(marks.filter((m) => m.kind === "behind")).toEqual([{ pos: { x: 2, y: 0 }, kind: "behind", label: "70%" }]);
  });

  it("marks the crushed tiles and the rubble of a topple", () => {
    const marks = previewOverlays({ ...base, topples: [topple] } as unknown as PreviewOut, view);
    expect(marks.filter((m) => m.kind === "crush").map((m) => m.pos)).toEqual([{ x: 2, y: 1 }, { x: 2, y: 0 }]);
    expect(marks.find((m) => m.kind === "rubble")).toEqual({ pos: { x: 2, y: 0 }, kind: "rubble", label: "礫" });
    expect(previewOverlays({ ...base, topples: [{ ...topple, rubble: null }] } as unknown as PreviewOut, view).some((m) => m.kind === "rubble")).toBe(false);
  });

  it("marks the lifted object and its landing for a hurl", () => {
    const marks = previewOverlays({ ...base, hurls: [hurl] } as unknown as PreviewOut, view);
    expect(marks).toEqual([
      { pos: { x: 2, y: 2 }, kind: "hurl_from", label: "舉" },
      { pos: { x: 3, y: 2 }, kind: "hurl_to", label: "落" },
    ]);
  });
});

describe("sceneLines", () => {
  it("explains a pierce through an object, with the discounted target behind it", () => {
    const lines = sceneLines({ ...base, pierce } as unknown as PreviewOut, names, view);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toContain("穿透：穿過");
    expect(lines[0]).toContain("(1, 0)");
    expect(lines[0]).toContain("只受 70% 傷害");
    expect(lines[0]).toContain(names.label("unit_0004"));
  });

  it("says a pierce without objects only ignores cover", () => {
    const bare = { ...pierce, objects: [], behind: [] };
    expect(sceneLines({ ...base, pierce: bare } as unknown as PreviewOut, names, view)[0]).toContain("無視半掩護");
  });

  it("explains a topple: direction, crushed tiles and units, rubble", () => {
    const [line] = sceneLines({ ...base, topples: [topple] } as unknown as PreviewOut, names, view);
    expect(line).toContain("往北倒下");
    expect(line).toContain("壓住 (2, 1)、(2, 0)");
    expect(line).toContain(`壓到 ${names.label("unit_0003")}`);
    expect(line).toContain("倒塌物留在 (2, 0)");
  });

  it("explains a hurl and what happens when it lands", () => {
    const [line] = sceneLines({ ...base, hurls: [hurl] } as unknown as PreviewOut, names, view);
    expect(line).toContain("(2, 2) → (3, 2)");
    expect(line).toContain("爆炸");
  });

  it("is part of the preview lines", () => {
    const p = { ...base, topples: [topple] } as unknown as PreviewOut;
    expect(previewLines(p, names, view).some((l) => l.startsWith("推倒："))).toBe(true);
    expect(previewLines(base, names, view).some((l) => l.startsWith("推倒：") || l.startsWith("穿透："))).toBe(false);
  });

  it("names the four directions", () => {
    expect([[1, 0], [-1, 0], [0, 1], [0, -1]].map((d) => directionText(d))).toEqual(["東", "西", "南", "北"]);
  });
});
