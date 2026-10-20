import { describe, expect, it } from "vitest";
import type { TelegraphChange, TelegraphOut, ZoneView } from "../api/types";
import { buildDrawModel } from "./drawModel";
import { HIGHLIGHT } from "./glossary";
import { marksTextAt, telegraphMarks } from "./telegraph";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";
import {
  zoneArrow,
  zoneDraws,
  zoneLine,
  zoneLinesAt,
  zoneNextText,
  zonePreviewLines,
  zoneRemaining,
} from "./zones";

// 第 2 輪：主角的火牆（向東移動，到第 3 輪結束）與戰歌（跟隨主角，有益）。
function fireWall(over: Partial<ZoneView> = {}): ZoneView {
  return {
    id: 1,
    owner_id: "unit_0001",
    team: "ally",
    skill_id: "skill_fire_wall",
    name_zh: "火牆",
    anchor: "moving",
    affects: "enemies",
    when: "both",
    cells: [
      { x: 1, y: 1 },
      { x: 1, y: 2 },
    ],
    direction: "east",
    speed: 1,
    expires_round: 3,
    harmful: true,
    next_cells: [
      { x: 2, y: 1 },
      { x: 2, y: 2 },
    ],
    ...over,
  };
}

function hymn(): ZoneView {
  return fireWall({
    id: 2,
    skill_id: "skill_war_hymn",
    name_zh: "戰歌",
    anchor: "caster",
    affects: "allies",
    cells: [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
    ],
    direction: null,
    speed: 0,
    expires_round: 4,
    harmful: false,
    next_cells: null,
  });
}

function zoneView() {
  return smallView({ round: 2, zones: [fireWall(), hymn()] });
}

describe("zones", () => {
  it("counts the remaining rounds including this one", () => {
    const view = zoneView();
    expect(zoneRemaining(view, fireWall())).toBe(2);
    expect(zoneRemaining(view, hymn())).toBe(3);
  });

  it("draws every zone cell with its colour and an arrow for moving zones", () => {
    const model = buildDrawModel(zoneView(), "unit_0001");
    expect(model.zones).toEqual([
      { x: 1, y: 1, color: HIGHLIGHT.zone_harmful, arrow: "→" },
      { x: 1, y: 2, color: HIGHLIGHT.zone_harmful, arrow: "→" },
      { x: 0, y: 0, color: HIGHLIGHT.zone_helpful, arrow: null },
      { x: 1, y: 0, color: HIGHLIGHT.zone_helpful, arrow: null },
    ]);
    expect(zoneArrow(fireWall({ direction: "north" }))).toBe("↑");
    expect(zoneDraws(smallView())).toEqual([]);
  });

  it("describes a zone with its owner, rounds left and next position", () => {
    const view = zoneView();
    const names = unitNames(view);
    const line = zoneLine(view, fireWall(), names);
    expect(line).toContain("火牆（");
    expect(line).toContain("影響施放者的敵人，進入或回合開始時結算，每次環境回合向東前進 1 格");
    expect(line).toContain("剩 2 輪（第 3 輪結束時消失）");
    expect(zoneNextText(fireWall())).toBe("本輪結束時移到 (2, 1)、(2, 2)");
    expect(zoneNextText(fireWall({ next_cells: [] }))).toBe("本輪結束時撞上牆壁而消失");
    expect(zoneNextText(hymn())).toBe("");
    expect(zoneLine(view, hymn(), names)).toContain("跟著施放者移動");
  });

  it("lists the zones covering the hovered tile", () => {
    const view = zoneView();
    const names = unitNames(view);
    expect(zoneLinesAt(view, { x: 1, y: 1 }, names)).toHaveLength(1);
    expect(zoneLinesAt(view, { x: 1, y: 1 }, names)[0]).toContain("本輪結束時移到 (2, 1)");
    expect(zoneLinesAt(view, { x: 3, y: 2 }, names)).toEqual([]);
    expect(zoneLinesAt(view, null, names)).toEqual([]);
  });

  it("lists the zone a skill preview creates", () => {
    const events = [
      { type: "skill_used", text: "施放「火牆」" },
      { type: "zone_created", text: "    召喚師英雄 展開持續區域「火牆」：(0, 4)" },
    ];
    expect(zonePreviewLines(events)).toEqual(["區域：召喚師英雄 展開持續區域「火牆」：(0, 4)"]);
  });

  it("marks every tile a zone will move to in the telegraph", () => {
    const moved = {
      kind: "zone_moved",
      pos: null,
      before: "east",
      after: "skill_fire_wall",
      object_id: null,
      unit_id: null,
      amount: 1,
      tiles: [
        { x: 2, y: 1 },
        { x: 2, y: 2 },
      ],
      text: "「火牆」區域將向東前進到 (2, 1)、(2, 2)",
    } as TelegraphChange;
    const t: TelegraphOut = { round: 2, changes: [moved], burning: [], upcoming: [], bombs: [], charges: [] };
    const marks = telegraphMarks(t, zoneView());
    expect(marks.map((m) => [m.pos.x, m.pos.y, m.glyph])).toEqual([
      [2, 1, "域"],
      [2, 2, "域"],
    ]);
    expect(marksTextAt(marks, { x: 2, y: 2 })).toEqual([moved.text]);
  });
});
