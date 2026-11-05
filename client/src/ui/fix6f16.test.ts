// 6F-16（美術 PM 驗收 6F-15：docs/art/6F-15檢查.md，只換外觀與顯示）：
// 1. 兩種數字不能混在一起：徽章的數字在自己的圓裡或緊貼著圓；和「▲N」的數字水平、垂直都至少隔 2px，不上下、不左右對齊。
// 2. 「▲N」不能蓋到狀態列（含「+N」）。
// 3. 「+N」不能超出地圖：最右欄的單位「+N」改放在三角形左邊；左右兩邊的地圖邊緣都處理。
// 4. 照收（不改壞）：下緣 ▲N 左右平移、朝北南時碰到三角形、圓蓋三角形上限 40%（6F-15 的測試照舊跑）。
//
// 格子太小、規則互相衝突放不下的組合（都是身上有狀態列的；800 寬的格子畫面只有 31px）照最保守的做法排，
// 列在 `NUM_CLASH`、`ROW_CLASH`，數量鎖住（變多就失敗），細節見 docs/phases/Phase6F-16報告.md「待 PM 決定」。
import { CanvasTextMetrics, Container, Text, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { badgeShapes, FIRM_HP_FIRST, numberAt, numbersApart, NUM_CORNERS, NUM_CORNERS_ABOVE, NUM_SEP_PX, STATUS_BADGE_R, STATUS_BADGE_LINE } from "../render/badgeLayout";
import { heightMarkBoxes, heightMarkDrop, heightMarkInk, heightMarkScale } from "../render/heightMark";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { mapEdgeOf, NO_EDGE, ROW_EDGE, rowShapes, slideClearOver, type Box, type MapEdge, type RowPlan } from "../render/rowLayout";
import { arrowOf, badgeLayoutOf, buildUnitSprite, heightMarkDropOf, heightMarkShiftOf, MARK_FALLBACK_TRIES, Pulses, rowShapesOf, unitFaceBox } from "../render/unitSprite";
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

function sprite(u: UnitDraw, s: number, heightDigits = 0, edge: MapEdge = NO_EDGE): Container {
  const c = buildUnitSprite(art, new Pulses(), u, [], { heightDigits, edge });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const boxHit = (a: Box, b: Box, gap = 0) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
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
/** 站在「▲1」上時標記實際畫的位置。 */
function markOf(c: Container, u: UnitDraw, s: number) {
  const k = heightMarkScale(s);
  const dy = heightMarkDropOf(c, s) ?? heightMarkDrop(k, unitFaceBox(u));
  const dx = heightMarkShiftOf(c, s) ?? 0;
  return { ...heightMarkBoxes(k, dy, 1, dx), ink: heightMarkInk(k, dy, dx) };
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

/**
 * 放不下、兩個數字只能做到「不碰到」（6F-15 的規則）的組合：全部都有狀態列（第 2 項優先讓「▲N」不碰狀態列），
 * 沒有狀態列的組合一律分得開。
 */
const NUM_CLASH = [
  "1040 east charge+3",
  "1040 west charge+defending",
  "1040 west bomb+defending",
  "1040 west charge+3",
  "1040 south charge+3",
  "800 east charge+defending",
  "800 east bomb+defending",
  "800 east charge+3",
  "800 south charge+3",
];

describe("6F-16 第 1 項：徽章的數字和「▲N」的數字分得開", () => {
  it("規則：水平、垂直都至少隔 NUM_SEP_PX（畫面像素）；只在斜對角，不上下、不左右對齊", () => {
    expect(NUM_SEP_PX).toBe(2);
    const a: Box = { l: 0, r: 10, t: 0, b: 10 };
    expect(numbersApart(a, { l: 12, r: 20, t: 12, b: 20 }, 2)).toBe(true);
    expect(numbersApart(a, { l: 12, r: 20, t: 0, b: 10 }, 2)).toBe(false); // 左右對齊
    expect(numbersApart(a, { l: 0, r: 10, t: 12, b: 20 }, 2)).toBe(false); // 上下對齊
    expect(numbersApart(a, { l: 11, r: 20, t: 12, b: 20 }, 2)).toBe(false); // 左右只差 1
  });

  it("數字一律在自己的圓上或緊貼著圓（數字中心離圓心不超過圓的半徑 ＋ 1）", () => {
    for (const corner of [...NUM_CORNERS, ...NUM_CORNERS_ABOVE]) {
      const o = numberAt(corner);
      expect(Math.hypot(o.x, o.y), corner).toBeLessThanOrEqual(STATUS_BADGE_R + STATUS_BADGE_LINE / 2 + 1);
    }
  });

  it("所有寬度 × 朝向 × 徽章組合 × 有沒有「▲N」：分得開；放不下的只列在 NUM_CLASH（數字也不碰到）", { timeout: 300_000 }, () => {
    const clash: string[] = [];
    let checked = 0;
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const hd of [0, 1])
          for (const [name, load] of LOADS) {
            const u = { ...BASE, facing, ...load } as UnitDraw;
            const c = sprite(u, s, hd);
            if (hd === 0) {
              expect(heightMarkDropOf(c, s), `${name} ${facing}`).toBeNull();
              continue;
            }
            const m = markOf(c, u, s);
            let apart = true;
            for (const b of badgesOf(c)) {
              const tag = `${sizeName(s)} ${facing} ${name} ${b.kind}`;
              expect(boxHit(b.box!, m.num), `${tag} 數字碰到`).toBe(false);
              expect(b.lay.firm, `${tag} HP`).toBeLessThan(FIRM_HP_FIRST);
              if (b.kind === "infused") continue;
              checked++;
              if (!numbersApart(b.box!, m.num, NUM_SEP_PX / s)) apart = false;
            }
            if (!apart) clash.push(`${sizeName(s)} ${facing} ${name}`);
          }
    expect(checked).toBeGreaterThan(80);
    expect(clash).toEqual(NUM_CLASH);
    for (const k of clash) expect(k, "放不下的都有狀態列").toMatch(/defending|\+3/);
  });

  it("美術 PM 指定的情境：弓手朝東、站在 ▲1 上、身上有蓄力：三種寬度都分得開；800 寬朝北蓄力＋防禦也分得開", () => {
    for (const s of SIZES) {
      const u = { ...BASE, facing: "east" as const, charge: 1, statusIds: ["charging"] } as UnitDraw;
      const c = sprite(u, s, 1);
      const [b] = badgesOf(c);
      expect(numbersApart(b!.box!, markOf(c, u, s).num, NUM_SEP_PX / s), sizeName(s)).toBe(true);
    }
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    const c = sprite(u, S800, 1);
    const [b] = badgesOf(c);
    expect(numbersApart(b!.box!, markOf(c, u, S800).num, NUM_SEP_PX / S800)).toBe(true);
  });

  it("效能：最擠的情況（800 寬、有狀態列、站在 ▲1 上）一個單位不到 0.5 秒", () => {
    let worst = 0;
    for (const facing of FACINGS)
      for (const [, load] of LOADS) {
        const u = { ...BASE, facing, ...load } as UnitDraw;
        // 全量並行時機器很忙：每種組合取 3 次中最快的，量的是排法本身，不是排程雜訊
        let best = Infinity;
        for (let i = 0; i < 3; i++) {
          const t0 = performance.now();
          sprite(u, S800, 1);
          best = Math.min(best, performance.now() - t0);
        }
        worst = Math.max(worst, best);
      }
    expect(worst).toBeLessThan(500);
    expect(MARK_FALLBACK_TRIES).toBeGreaterThan(0);
  });
});

/** 「▲N」的底蓋到狀態列的組合（格子放不下）：只有 800 寬與 1040 寬有狀態列的。 */
const ROW_CLASH_800 = 24;
const ROW_CLASH_1040 = 2;

describe("6F-16 第 2 項：「▲N」不蓋到狀態列（含「+N」）", () => {
  it("1600 寬一律不碰；1040、800 寬放不下的數量鎖住；「▲」和數字被狀態列蓋到的只在 800 寬", { timeout: 300_000 }, () => {
    const clash: Record<string, string[]> = { "1600": [], "1040": [], "800": [] };
    const inkClash: string[] = [];
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          const c = sprite(u, s, 1);
          const boxes = rowBoxesOf(c);
          if (boxes.length === 0) continue;
          const m = markOf(c, u, s);
          if (boxes.some((b) => boxHit(b, m.box))) clash[sizeName(s)]!.push(`${facing} ${name}`);
          if (boxes.some((b) => boxHit(b, m.ink))) inkClash.push(`${sizeName(s)} ${facing} ${name}`);
        }
    expect(clash["1600"]).toEqual([]);
    expect(clash["1040"]!.length).toBe(ROW_CLASH_1040);
    expect(clash["800"]!.length).toBeLessThanOrEqual(ROW_CLASH_800);
    for (const k of inkClash) expect(k.startsWith("800 "), k).toBe(true);
  });

  it("美術 PM 指定的情境：1040 寬同一格有下緣的「▲N」和狀態列（弓手朝北蓄力＋防禦）：「▲N」整個不碰狀態列", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    const c = sprite(u, S1040, 1);
    const m = markOf(c, u, S1040);
    expect(heightMarkDropOf(c, S1040)!).toBeGreaterThan(heightMarkDrop(heightMarkScale(S1040), unitFaceBox(u)) + 1); // 下緣
    for (const b of rowBoxesOf(c)) expect(boxHit(b, m.box)).toBe(false);
  });

  it("沒有徽章、只有狀態列的人站在「▲N」上：狀態列重排完也決定標記的位置（1040 寬不碰狀態列）", () => {
    for (const facing of FACINGS)
      for (const [name, load] of ROW_ONLY) {
        const u = { ...BASE, facing, ...load } as UnitDraw;
        const c = sprite(u, S1040, 1);
        expect(heightMarkDropOf(c, S1040), `${facing} ${name}`).not.toBeNull();
        const m = markOf(c, u, S1040);
        for (const b of rowBoxesOf(c)) expect(boxHit(b, m.box), `${facing} ${name}`).toBe(false);
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
      const right = rowShapesOf(statusRowOf(sprite(u, s, 0, { left: false, right: true }))!)!;
      for (const b of right.boxes) {
        expect(b.r, `s=${s}`).toBeLessThanOrEqual(T / 2 + 1e-6);
        expect(b.r, `s=${s}`).toBeLessThanOrEqual(arrowOf(u)!.l); // 三角形左邊
      }
      const left = rowShapesOf(statusRowOf(sprite(u, s, 0, { left: true, right: false }))!)!;
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
            const c = sprite(u, s, 0, edge);
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
    const a = sprite(u, S800, 1);
    const b = sprite(u, S800, 1);
    expect(markOf(a, u, S800)).toEqual(markOf(b, u, S800));
    expect(badgesOf(a).map((x) => x.lay)).toEqual(badgesOf(b).map((x) => x.lay));
    const texts = (c: Container) => statusRowOf(c)!.children.filter((n): n is Text => n instanceof Text && n.visible).map((t) => t.text);
    expect(texts(a)).toEqual(texts(b));
  });
});
