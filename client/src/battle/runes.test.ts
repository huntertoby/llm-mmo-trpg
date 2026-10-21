import { describe, expect, it } from "vitest";
import type { RuneView } from "../api/types";
import { liftedCenter, tileLift } from "./elevation";
import { TILE_SIZE } from "./geometry";
import { buildDrawModel } from "./drawModel";
import { LABEL_RUNE, tileSections } from "./tileInfo";
import { smallView, tile } from "./testFixtures";
import { ownerNameOf, runeColor, runeDraws, runeLine, runesAt, runesOf, TAG_RUNE_COLOR } from "./runes";
import { ELEMENT_COLORS, hexToNumber } from "./vfxPalette";
import { TEAM_COLORS } from "./glossary";

function rune(over: Partial<RuneView> = {}): RuneView {
  return {
    id: 1,
    owner_id: "unit_0001",
    team: "ally",
    pos: { x: 0, y: 0 },
    element: "lightning",
    tag: null,
    name_zh: "雷紋",
    remaining: 2,
    ...over,
  };
}

const withRunes = (runes: RuneView[]) => ({ ...smallView(), runes });

describe("rune draw data", () => {
  it("older recordings without runes draw nothing", () => {
    const view = smallView();
    delete (view as { runes?: RuneView[] }).runes;
    expect(runesOf(view)).toEqual([]);
    expect(runeDraws(view)).toEqual([]);
    expect(buildDrawModel(view, "unit_0001").runes).toEqual([]);
  });

  it("team color for the frame, element color for the pattern", () => {
    const [ally, enemy, tagged] = runeDraws(
      withRunes([
        rune({ id: 1 }),
        rune({ id: 2, team: "enemy", pos: { x: 2, y: 0 }, element: "fire", name_zh: "火紋" }),
        rune({ id: 3, pos: { x: 0, y: 2 }, element: null, tag: "hunt", name_zh: "hunt紋" }),
      ]),
    );
    expect(ally).toMatchObject({ x: 0, y: 0, teamColor: TEAM_COLORS.ally, color: hexToNumber(ELEMENT_COLORS.lightning!.accent) });
    expect(enemy).toMatchObject({ teamColor: TEAM_COLORS.enemy, color: hexToNumber(ELEMENT_COLORS.fire!.accent) });
    expect(tagged?.color).toBe(TAG_RUNE_COLOR);
    expect(runeColor(rune({ element: null, tag: "x" }))).toBe(TAG_RUNE_COLOR);
  });

  it("several runes on one cell take separate slots, in id order", () => {
    const draws = runeDraws(
      withRunes([
        rune({ id: 5, owner_id: "unit_0003", team: "enemy" }),
        rune({ id: 2 }),
        rune({ id: 3, pos: { x: 1, y: 0 } }),
      ]),
    );
    expect(draws.map((d) => d.id)).toEqual([2, 3, 5]);
    const cell = draws.filter((d) => d.x === 0 && d.y === 0);
    expect(cell.map((d) => [d.slot, d.slots])).toEqual([
      [0, 2],
      [1, 2],
    ]);
    expect(draws.find((d) => d.id === 3)).toMatchObject({ slot: 0, slots: 1 });
  });

  it("the last round is drawn faded", () => {
    const [a, b] = runeDraws(withRunes([rune({ id: 1, remaining: 1 }), rune({ id: 2, remaining: 2 })]));
    expect([a?.fading, b?.fading]).toEqual([true, false]);
  });

  it("the draw model carries the runes and they lift with the tile height", () => {
    const view = withRunes([rune({ pos: { x: 1, y: 0 } })]);
    const model = buildDrawModel(view, "unit_0001");
    expect(model.runes).toHaveLength(1);
    // smallView 的 (1, 0) 高度 2：符文畫在抬高後的頂面中心（與單位、陷阱同一套 tileLift）
    const h = model.tiles.find((t) => t.x === 1 && t.y === 0)?.height ?? 0;
    expect(h).toBeGreaterThan(0);
    const c = liftedCenter({ x: 1, y: 0 }, h);
    expect(c.y).toBe(TILE_SIZE / 2 - tileLift(h));
    expect(c.x).toBe(TILE_SIZE + TILE_SIZE / 2);
  });
});

describe("rune text", () => {
  it("line and owner name", () => {
    const view = withRunes([rune()]);
    const r = runesOf(view)[0] as RuneView;
    expect(ownerNameOf(view, r)).toBe(view.units.find((u) => u.id === "unit_0001")?.name_zh);
    expect(runeLine(r, "刻印流英雄")).toBe("刻印流英雄的雷紋，剩 2 輪");
    expect(runesAt(view, { x: 0, y: 0 })).toHaveLength(1);
    expect(runesAt(view, { x: 3, y: 3 })).toHaveLength(0);
  });

  it("the tile card lists each rune with owner, name and remaining rounds", () => {
    const view = withRunes([rune(), rune({ id: 2, owner_id: "unit_0003", team: "enemy", element: "fire", name_zh: "火紋", remaining: 1 })]);
    const sections = tileSections(view, { x: 0, y: 0 }, {});
    const runeSections = sections.filter((s) => s.kind === "rune");
    expect(runeSections.map((s) => s.title)).toEqual([
      `${LABEL_RUNE}：${view.units[0]?.name_zh}的雷紋，剩 2 輪`,
      `${LABEL_RUNE}：${view.units.find((u) => u.id === "unit_0003")?.name_zh}的火紋，剩 1 輪`,
    ]);
    // 沒有符文的格子沒有符文段落
    expect(tileSections(view, { x: 2, y: 0 }, {}).some((s) => s.kind === "rune")).toBe(false);
    expect(tile(0, 0).height).toBe(0);
  });
});
