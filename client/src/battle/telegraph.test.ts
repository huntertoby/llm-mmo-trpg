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
  return { round: 1, changes, burning: [], upcoming: [], bombs: [], charges: [], ...rest };
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

  it("marks a temporary wall that will vanish (Phase 3-11)", () => {
    const t = telegraph([change("object_expired", "冰牆 將在本輪結束時消失", { pos: { x: 1, y: 2 } })]);
    const [mark] = telegraphMarks(t, view);
    expect(mark).toMatchObject({ kind: "object_expired", glyph: "消" });
    expect(telegraphLines(t)).toEqual(["冰牆 將在本輪結束時消失"]);
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

describe("time bomb marks (Phase 3D-8b)", () => {
  const bomb = {
    unit_id: "unit_0003",
    pos: { x: 2, y: 1 },
    remaining: 2,
    radius: 1,
    tiles: [
      { x: 2, y: 1 },
      { x: 1, y: 1 },
      { x: 2, y: 2 },
    ],
    explodes: false,
    text: "單位3 身上的定時炸彈還要 2 次環境回合爆炸（半徑 1 格）",
  };

  it("marks the carrier with the countdown and the blast area with a faint mark", () => {
    const marks = telegraphMarks(telegraph([], { bombs: [bomb] }), view);
    const carrier = marks.find((m) => m.pos.x === 2 && m.pos.y === 1);
    expect(carrier).toMatchObject({ kind: "bomb", glyph: "2" });
    const area = marks.find((m) => m.pos.x === 1 && m.pos.y === 1);
    expect(area).toMatchObject({ kind: "bomb_area", glyph: "炸" });
    expect(marksTextAt(marks, { x: 2, y: 2 })).toEqual([bomb.text]);
  });

  it("lists the bombs in the side panel and counts them as something to show", () => {
    const t = telegraph([], { bombs: [bomb] });
    expect(telegraphLines(t)).toEqual([bomb.text]);
    expect(telegraphIsEmpty(t)).toBe(false);
  });

  it("marks the blast tiles when the bomb goes off in the next environment turn", () => {
    const t = telegraph(
      [
        change("bomb_exploded", "炸彈將爆炸", {
          pos: { x: 2, y: 1 },
          unit_id: "unit_0003",
          tiles: [
            { x: 2, y: 1 },
            { x: 1, y: 1 },
          ],
        } as Partial<TelegraphChange>),
      ],
      { bombs: [{ ...bomb, remaining: 1, explodes: true }] },
    );
    const marks = telegraphMarks(t, view);
    expect(marks.find((m) => m.pos.x === 1 && m.pos.y === 1)?.kind).toBe("bomb_exploded");
    expect(marks.find((m) => m.pos.x === 2 && m.pos.y === 1)?.kind).toBe("bomb");
  });
});
