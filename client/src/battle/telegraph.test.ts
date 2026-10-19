import { describe, expect, it } from "vitest";
import type { TelegraphChange, TelegraphOut } from "../api/types";
import { smallView } from "./testFixtures";
import { marksTextAt, telegraphIsEmpty, telegraphLines, telegraphMarks } from "./telegraph";

function change(kind: string, text: string, over: Partial<TelegraphChange> = {}): TelegraphChange {
  return {
    kind,
    pos: null,
    before: null,
    after: null,
    object_id: null,
    unit_id: null,
    amount: null,
    text,
    ...over,
  } as TelegraphChange;
}

function telegraph(changes: TelegraphChange[], rest: Partial<TelegraphOut> = {}): TelegraphOut {
  return { round: 1, changes, burning: [], upcoming: [], ...rest };
}

const view = smallView();

describe("telegraph marks", () => {
  it("makes one mark per tile with the highest-priority glyph and all texts", () => {
    const t = telegraph([
      change("surface", "表面變化", { pos: { x: 2, y: 2 } }),
      change("object_exploded", "油桶將爆炸", { pos: { x: 2, y: 2 } }),
      change("object_ignited", "木箱將被點燃", { pos: { x: 1, y: 2 } }),
    ]);
    const marks = telegraphMarks(t, view);
    expect(marks.map((m) => [m.pos.x, m.pos.y, m.kind])).toEqual([
      [1, 2, "object_ignited"],
      [2, 2, "object_exploded"],
    ]);
    expect(marks[1]?.texts).toEqual(["表面變化", "油桶將爆炸"]);
    expect(marksTextAt(marks, { x: 2, y: 2 })).toHaveLength(2);
    expect(marksTextAt(marks, { x: 0, y: 0 })).toEqual([]);
    expect(marksTextAt(marks, null)).toEqual([]);
  });

  it("places unit changes without a position on the unit's tile", () => {
    const t = telegraph([change("unit_downed", "A 將倒下", { unit_id: "unit_0003" })]);
    expect(telegraphMarks(t, view).map((m) => [m.pos.x, m.pos.y])).toEqual([[2, 1]]);
    const lost = telegraph([change("unit_downed", "？", { unit_id: "nobody" })]);
    expect(telegraphMarks(lost, view)).toEqual([]);
  });

  it("summarises everything for the side panel", () => {
    const t = telegraph([change("surface", "表面變化")], {
      burning: [{ object_id: "obj_0002", pos: { x: 1, y: 2 }, remaining: 2, text: "木箱還能燃燒 2 次" }],
      upcoming: [{ round: 2, kind: "spawn_units", tiles: [[0, 0]], text: "援軍出現" }],
    });
    expect(telegraphLines(t)).toEqual(["表面變化", "木箱還能燃燒 2 次", "援軍出現"]);
    expect(telegraphIsEmpty(t)).toBe(false);
    expect(telegraphIsEmpty(telegraph([]))).toBe(true);
  });
});
