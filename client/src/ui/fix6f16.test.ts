// 6F-16（美術 PM 驗收 6F-15：docs/art/6F-15檢查.md，只換外觀與顯示）：
// 1. 徽章的數字在自己的圓外、緊貼著圓（6F-18 照這個位置：美術 PM 6F-17 檢查必修 3）。
// 3. 「+N」不能超出地圖：最右欄的單位「+N」改放在三角形左邊；左右兩邊的地圖邊緣都處理。
// 6F-18：有人站的格子不畫「▲N」（美術 PM 6F-17 檢查第 2 節），第 1 項「和 ▲N 的數字分開」、第 2 項「▲N 不蓋狀態列」拿掉
// （有人站的格子沒有「▲N」，改由 fix6f18 鎖住）。
import { CanvasTextMetrics, Container, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { badgeShapes, numberAt, NUM_CORNERS, STATUS_BADGE_R, STATUS_BADGE_LINE } from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { mapEdgeOf, NO_EDGE, ROW_EDGE, rowShapes, slideClearOver, type Box, type MapEdge, type RowPlan } from "../render/rowLayout";
import { arrowOf, badgeLayoutOf, buildUnitSprite, Pulses, rowShapesOf, rowPlusTexts } from "../render/unitSprite";
import { readSources, stripTsComments } from "../test/sourceScan";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const FACINGS: readonly Facing[] = ["east", "west", "north", "south"];

beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const view = (): BattleView =>
  ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;
const BASE: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: null, charge: null, infused: false, statusIds: [], marker: "", facing: "south" };

function sprite(u: UnitDraw, s: number, edge: MapEdge = NO_EDGE): Container {
  const c = buildUnitSprite(art, new Pulses(), u, [], { edge });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const KIND = { [BOMB_BADGE_LABEL]: "bomb", [CHARGE_BADGE_LABEL]: "charge", [INFUSED_BADGE_LABEL]: "infused" } as const;

function badgesOf(c: Container) {
  return unitMarksOf(c)
    .filter((n) => n.label in KIND)
    .map((n) => {
      const lay = badgeLayoutOf(n)!;
      const kind = KIND[n.label as keyof typeof KIND];
      return { kind, lay, ...badgeShapes(kind, lay.at, lay.sc, 1, lay.corner) };
    });
}
function rowBoxesOf(c: Container): Box[] {
  const row = statusRowOf(c);
  const sh = row === null ? null : rowShapesOf(row);
  if (sh === null) return [];
  return [...sh.boxes, ...sh.circles.map((q) => ({ l: q.x - q.r, r: q.x + q.r, t: q.y - q.r, b: q.y + q.r }))];
}

/** 徽章的組合（6F-15 同）＋只有狀態列的（第 2 項）。 */
const LOADS: Array<[string, Partial<UnitDraw>]> = [
  ["charge", { charge: 1, statusIds: ["charging"] }],
  ["bomb", { bomb: 2, statusIds: ["time_bomb"] }],
  ["infused", { infused: true }],
  ["charge+defending", { charge: 1, statusIds: ["defending", "charging"] }],
  ["bomb+defending", { bomb: 2, statusIds: ["time_bomb", "defending"] }],
  ["charge+3", { charge: 1, statusIds: ["burning", "slow", "defending", "charging"] }],
  ["all", { bomb: 2, charge: 1, infused: true, statusIds: ["time_bomb", "charging"] }],
];
const ROW_ONLY: Array<[string, Partial<UnitDraw>]> = [
  ["row1", { statusIds: ["defending"] }],
  ["row2", { statusIds: ["defending", "slow"] }],
  ["row3", { statusIds: ["burning", "slow", "defending"] }],
];
const sizeName = (s: number) => (s === S1600 ? "1600" : s === S1040 ? "1040" : "800");

// 6F-17 的 `NUM_CLASH`、`ROW_CLASH`：6F-18 起有人站的格子不畫「▲N」，清單拿掉（fix6f18 鎖住 0）。

describe("6F-16 第 1 項：徽章的數字的位置", () => {
  it("數字一律在自己的圓外、緊貼著圓（數字中心離圓心不超過圓的半徑 ＋ 1，也不在圓心）", () => {
    for (const corner of NUM_CORNERS) {
      const o = numberAt(corner);
      expect(Math.hypot(o.x, o.y), corner).toBeLessThanOrEqual(STATUS_BADGE_R + STATUS_BADGE_LINE / 2 + 1);
      expect(Math.hypot(o.x, o.y), corner).toBeGreaterThan(STATUS_BADGE_R / 2);
    }
  });
});

describe("6F-16 第 3 項：「+N」不超出地圖", () => {
  it("mapEdgeOf：最左欄、最右欄", () => {
    expect(mapEdgeOf({ width: 8 }, { x: 0 })).toEqual({ left: true, right: false });
    expect(mapEdgeOf({ width: 8 }, { x: 7 })).toEqual({ left: false, right: true });
    expect(mapEdgeOf({ width: 8 }, { x: 3 })).toEqual({ left: false, right: false });
  });

  it("最右欄、朝北、3 個狀態：「+3」放在三角形左邊、不超出格子右緣（地圖右緣）；最左欄不超出格子左緣", () => {
    for (const s of [S1040, S800]) {
      const u = { ...BASE, facing: "north" as const, statusIds: ["burning", "slow", "defending"] } as UnitDraw;
      const right = rowShapesOf(statusRowOf(sprite(u, s, { left: false, right: true }))!)!;
      for (const b of right.boxes) {
        expect(b.r, `s=${s}`).toBeLessThanOrEqual(T / 2 + 1e-6);
        expect(b.r, `s=${s}`).toBeLessThanOrEqual(arrowOf(u)!.l); // 三角形左邊
      }
      const left = rowShapesOf(statusRowOf(sprite(u, s, { left: true, right: false }))!)!;
      for (const b of left.boxes) expect(b.l, `s=${s}`).toBeGreaterThanOrEqual(-T / 2 - 1e-6);
      // 不在邊緣時照 6F-15（三角形右邊、超出格子一點）
      const mid = rowShapesOf(statusRowOf(sprite(u, s))!)!;
      for (const b of mid.boxes) expect(b.l, `s=${s}`).toBeGreaterThan(arrowOf(u)!.r);
    }
  });

  it("一般規則：所有寬度 × 朝向 × 狀態數 × 站在最左、最右欄：狀態列不超出地圖那一邊", { timeout: 120_000 }, () => {
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...ROW_ONLY, ...LOADS])
          for (const edge of [{ left: true, right: false }, { left: false, right: true }]) {
            const u = { ...BASE, facing, ...load } as UnitDraw;
            const c = sprite(u, s, edge);
            for (const b of rowBoxesOf(c)) {
              const tag = `${sizeName(s)} ${facing} ${name} ${JSON.stringify(edge)}`;
              if (edge.left) expect(b.l, tag).toBeGreaterThanOrEqual(-T / 2 - 1e-6);
              if (edge.right) expect(b.r, tag).toBeLessThanOrEqual(T / 2 + 1e-6);
            }
          }
  });

  it("slideClearOver：最右欄先放三角形左邊、最左欄先放右邊，都不超出地圖", () => {
    const shapesW = (w: number) => (p: RowPlan) => rowShapes(p, 3, 1, 13, false, w);
    const plan: RowPlan = { shift: 0, pitch: 12, moreDx: 0, compact: true, plusOnly: true };
    const arrow: Box = { l: -5, r: 5, t: 0, b: 14 };
    const r = rowShapes(slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE, "r", { left: false, right: true })!, 3, 1, 13, false, 22).boxes[0]!;
    expect(r.r).toBeLessThanOrEqual(arrow.l - 1.5 + 1e-6);
    expect(r.l).toBeLessThan(-ROW_EDGE);
    const l = rowShapes(slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE, "l", { left: true, right: false })!, 3, 1, 13, false, 22).boxes[0]!;
    expect(l.l).toBeGreaterThanOrEqual(arrow.r + 1.5 - 1e-6);
  });

  it("接線：繪製器照單位所在的欄傳地圖邊緣（重畫、轉身）", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("edge: mapEdgeOf(model, u)");
    expect(r).toContain("edge: this.model === null ? NO_EDGE : mapEdgeOf(this.model, next)");
    const u = sources["render/unitSprite.ts"]!;
    expect(u).toContain("const row = statusRow(u, turns, opts.edge);");
    expect(u).toContain('slideClearOver(p, shapesOf, arrow, rowLeft, m === "plus-l" ? "l" : "r", edge)');
  });
});

describe("6F-16 確定性", () => {
  it("同一個單位排兩次結果一樣", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    const a = sprite(u, S800);
    const b = sprite(u, S800);
    expect(badgesOf(a).map((x) => x.lay)).toEqual(badgesOf(b).map((x) => x.lay));
    const texts = (c: Container) => rowPlusTexts(statusRowOf(c)!);
    expect(texts(a)).toEqual(texts(b));
  });
});
