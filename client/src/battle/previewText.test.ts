import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { chainLines, costLine, damageText, outcomeText, percent, previewLines } from "./previewText";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

const view = smallView();
const names = unitNames(view);
const base = {
  action: { type: "end_turn", unit_id: "unit_0001" },
  hit_permille: 875,
  crit_permille: 50,
  damage: { minimum: 3, maximum: 9, expected_milli: 5250, expected_if_hit_milli: 6000 },
  affected_tiles: [[2, 1]],
  affected_units: ["unit_0003"],
  certain: [],
  possible: [],
  cover: null,
  notes: [],
  targets: [],
  healed: [],
  min_events: [],
  max_events: [],
} as unknown as PreviewOut;

describe("previewText", () => {
  it("formats percentages and damage", () => {
    expect(percent(875)).toBe("87.5%");
    expect(percent(500)).toBe("50%");
    expect(percent(null)).toBe("—");
    expect(damageText(base.damage!)).toBe("3–9（期望 5.3）");
  });

  it("shows the (modified) AP cost and reach on the last line when the server sends them", () => {
    expect(costLine(base)).toBeNull();
    const p = { ...base, ap_cost: 2, reach: 3 } as PreviewOut;
    expect(costLine(p)).toBe("AP 2　射程 3");
    expect(previewLines(p, names, view).at(-1)).toBe("AP 2　射程 3");
    expect(costLine({ ...base, ap_cost: 1, reach: null } as PreviewOut)).toBe("AP 1");
  });

  it("lists the possible collision damage per unit", () => {
    const p = { ...base, collisions: [{ unit_id: "unit_0003", minimum: 0, maximum: 12 }] } as PreviewOut;
    expect(previewLines(p, names, view)).toContain(`撞擊傷害 ${names.label("unit_0003")} 最多 12`);
    expect(previewLines(base, names, view).some((l) => l.startsWith("撞擊傷害"))).toBe(false);
  });

  it("summarises hit, crit and damage on the first line", () => {
    expect(previewLines(base, names, view)[0]).toBe("命中 87.5%　暴擊 5%　傷害 3–9（期望 5.3）");
  });

  it("lists per-target statuses and certain / possible outcomes in Chinese", () => {
    const p = {
      ...base,
      targets: [
        {
          unit_id: "unit_0003",
          hit_permille: 800,
          crit_permille: 0,
          damage: null,
          ally: false,
          knock_permille: null,
          status_chances: [{ status_id: "burning", original_id: "burning", apply_permille: 400, diminished: false }],
        },
      ],
      certain: [{ kind: "downed", unit_id: "unit_0003", object_id: null, pos: null, detail: null }],
      possible: [{ kind: "object_exploded", unit_id: null, object_id: "obj_0001", pos: [2, 2], detail: null }],
      notes: ["注意"],
    } as unknown as PreviewOut;
    const lines = previewLines(p, names, view);
    expect(lines).toContain("a 單位3：燃燒 40%");
    expect(lines).toContain("確定：a 單位3 倒下");
    expect(lines).toContain("可能：油桶 (2, 2) 爆炸");
    expect(lines.at(-1)).toBe("注意");
  });

  it("describes every outcome kind with some text", () => {
    for (const kind of ["damaged", "moved", "status", "surface", "stacks", "trap_triggered", "weird"]) {
      const text = outcomeText(
        { kind, unit_id: "unit_0001", object_id: null, pos: [1, 1], detail: "oil" },
        names,
        view,
      );
      expect(text).not.toBe("");
    }
  });

  it("describes entering a form (3J-1a)", () => {
    const text = outcomeText({ kind: "form", unit_id: "unit_0001", object_id: null, pos: null, detail: "bear" }, names, view);
    expect(text).toContain("進入形態");
  });
});

describe("chain preview", () => {
  const ev = (type: string, text?: string) => ({ seq: 1, round: 1, type, ...(text ? { text } : {}) });
  const p = {
    ...base,
    min_events: [ev("attack_rolled", "攻擊"), ev("object_exploded", "  油桶 (2, 2) 爆炸")],
    max_events: [
      ev("object_exploded", "油桶 (2, 2) 爆炸"),
      ev("surface_changed", "(2, 1) 變成火焰"),
      ev("surface_changed", "(2, 1) 變成火焰"),
      ev("unit_fell", "b 墜落"),
      ev("object_ignited"),
    ],
    certain: [{ kind: "object_exploded", unit_id: null, object_id: "obj_0001", pos: [2, 2], detail: null }],
    possible: [{ kind: "downed", unit_id: "unit_0003", object_id: null, pos: null, detail: null }],
  } as unknown as PreviewOut;

  it("splits chain events into certain and possible by their Chinese text", () => {
    expect(chainLines(p)).toEqual({
      certain: ["油桶 (2, 2) 爆炸"],
      possible: ["(2, 1) 變成火焰", "b 墜落"],
    });
    expect(chainLines(base)).toEqual({ certain: [], possible: [] });
  });

  it("does not repeat chain outcomes in the summary when asked to skip them", () => {
    expect(previewLines(p, names, view)).toContain("確定：油桶 (2, 2) 爆炸");
    const skipped = previewLines(p, names, view, true);
    expect(skipped.some((l) => l.includes("爆炸"))).toBe(false);
    expect(skipped).toContain("可能：a 單位3 倒下");
  });
});
