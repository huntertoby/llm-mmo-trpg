import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { damageText, outcomeText, percent, previewLines } from "./previewText";
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
} as unknown as PreviewOut;

describe("previewText", () => {
  it("formats percentages and damage", () => {
    expect(percent(875)).toBe("87.5%");
    expect(percent(500)).toBe("50%");
    expect(percent(null)).toBe("—");
    expect(damageText(base.damage!)).toBe("3–9（期望 5.3）");
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
});
