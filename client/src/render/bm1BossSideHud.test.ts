// BM-1：800 寬有部位的頭目，狀態列移到 HP 條右邊、炸彈／蓄力／灌注徽章移到左邊（美術 PM PB-1e 驗收裁定待決 3；PB-1f 待決 3）。
// 1600 寬照原本；沒有部位的單位不變；站最右欄左右對調；3×3 巨型頭目同一套。
import { CanvasTextMetrics, Container, RenderLayer, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, PartView, UnitView } from "../api/types";
import { buildDrawModel, unitDrawOf, type UnitDraw } from "../battle/drawModel";
import { HP_W, HP_Y, stripLayout } from "../battle/partStrip";
import { smallView, tile, unit } from "../battle/testFixtures";
import dolls from "./fixtures/unitDolls.json";
import type { ArtTextures } from "./artTextures";
import { badgeShapes } from "./badgeLayout";
import { BOSS_SIDE_GAP_PX, bossSideHudOn, sideBadgeLayouts, sideBlock, sideRowShift } from "./bossSideHud";
import { applyMarkScale, BOSS_RING_FRONT_LABEL, CHARGE_BADGE_LABEL, STATUS_ROW_LABEL, unitMarksOf } from "./minMark";
import { RowStack } from "./rowLayers";
import { COMPACT_ROW_MAX_SCALE, NO_EDGE } from "./rowLayout";
import { bossHudDy, buildUnitSprite, isGiantUnit, Pulses, rowShapesOf, SHIELD_OUTLINE } from "./unitSprite";

const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null, canvas: () => null, figureRes: () => 2 } as unknown as ArtTextures;
beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const st = (s: string) => ({ status_id: s, remaining: 2, source_id: null, amount: null, blast_radius: null, charge_tiles: [], cost_status: false });
const part = (id: string): PartView => ({ id, name_zh: id, hp: 24, max_hp: 24, broken: false, exposed: true, reach: "any", break_lines_zh: [] });
function viewWith(units: UnitView[], w = 4): BattleView {
  const tiles = [];
  for (let y = 0; y < 4; y++) for (let x = 0; x < w; x++) tiles.push(tile(x, y));
  return { team: "ally", map_id: "t", width: w, height: 4, tiles, objects: [], units, traps: [], turn_order: [], active_unit: null, round: 1, max_rounds: 30, objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
const STATUSES = ["mist_return", "shielded", "burning", "charging"].map(st);
const drawOf = (o: Partial<UnitView> = {}, x = 1): UnitDraw => {
  const b = unit("b", "enemy", x, 1, { facing: "south", statuses: STATUSES, parts: [part("whisk"), part("dantian"), part("sword")], ...o } as Partial<UnitView>);
  return buildDrawModel(viewWith([b]), "h").units.find((u) => u.id === "b")!;
};

/** 建好節點、照縮放 `s` 套一次標記倍率（同繪製器 `scaleMark`），回傳狀態列的形狀與徽章位置。 */
function laidOut(u: UnitDraw, s: number, edge = NO_EDGE) {
  const c = buildUnitSprite(art, new Pulses(), u, [], { edge });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  const row = c.children.find((n) => n.label === STATUS_ROW_LABEL) as Container;
  const charge = c.children.find((n) => n.label === CHARGE_BADGE_LABEL) as Container;
  return { c, row, sh: rowShapesOf(row)!, charge };
}
const span = (boxes: ReadonlyArray<{ l: number; r: number; t: number; b: number }>) => ({ l: Math.min(...boxes.map((b) => b.l)), r: Math.max(...boxes.map((b) => b.r)), t: Math.min(...boxes.map((b) => b.t)), b: Math.max(...boxes.map((b) => b.b)) });

describe("什麼時候用兩側排法", () => {
  it("有部位、站著、有 HP 條，而且縮放 ≤ 精簡列門檻（800 寬）", () => {
    const u = drawOf();
    expect(bossSideHudOn(u, 0.53)).toBe(true);
    expect(bossSideHudOn(u, COMPACT_ROW_MAX_SCALE)).toBe(true);
    expect(bossSideHudOn(u, 1.03)).toBe(false); // 1600 寬照原本
    expect(bossSideHudOn(u, 1.31)).toBe(false);
    expect(bossSideHudOn({ ...u, parts: undefined }, 0.53)).toBe(false);
    expect(bossSideHudOn({ ...u, downed: true }, 0.53)).toBe(false);
    expect(bossSideHudOn({ ...u, noBar: true }, 0.53)).toBe(false);
  });
});

describe("800 寬：狀態列在 HP 條右邊、徽章在左邊", () => {
  const s = 0.53;
  it("狀態列整排在 HP 條右緣外（空隙畫面 2 px），垂直置中對齊 HP 條＋部位小格；不蓋到身體（HP 條上方）", () => {
    const { sh } = laidOut(drawOf(), s);
    const sp = span(sh.boxes);
    expect(sp.l).toBeGreaterThanOrEqual(HP_W / 2 + BOSS_SIDE_GAP_PX / s - 1e-6);
    const mid = (HP_Y + stripLayout(3, s).bottom) / 2;
    expect((sp.t + sp.b) / 2).toBeCloseTo(mid, 5);
    // 精簡列：1 個圖示＋「+N」膠囊（3 個狀態不再被擠成只留「+3」）
    expect(sh.cap).not.toBeNull();
    expect(sh.boxes.length).toBe(2);
  });
  it("蓄力徽章在 HP 條左緣外，圓心對齊同一條中線、數字在左下", () => {
    const { charge } = laidOut(drawOf(), s);
    const b = sideBlock(drawOf(), s, SHIELD_OUTLINE, NO_EDGE);
    const lay = sideBadgeLayouts([{ kind: "charge", at: { x: 0, y: 0 }, digits: 1 }], s, b)[0]!;
    expect(lay.corner).toBe("bl");
    expect(charge.position.x).toBeCloseTo(lay.at.x);
    expect(charge.position.y).toBeCloseTo(lay.at.y);
    const shape = badgeShapes("charge", lay.at, lay.sc, 1, "bl");
    expect(Math.max(shape.circle.x + shape.circle.r, shape.box!.r)).toBeCloseTo(-HP_W / 2 - BOSS_SIDE_GAP_PX / s, 5);
  });
  it("站最右欄：左右對調（狀態列在左、徽章在右）", () => {
    const { sh, charge } = laidOut(drawOf({}, 3), s, { left: false, right: true });
    expect(span(sh.boxes).r).toBeLessThanOrEqual(-HP_W / 2 - BOSS_SIDE_GAP_PX / s + 1e-6);
    expect(charge.position.x).toBeGreaterThan(HP_W / 2);
  });
  it("多顆徽章由內往外排、不重疊", () => {
    const b = sideBlock(drawOf(), s, SHIELD_OUTLINE, NO_EDGE);
    const lays = sideBadgeLayouts(
      [
        { kind: "bomb", at: { x: 0, y: 0 }, digits: 1 },
        { kind: "charge", at: { x: 0, y: 0 }, digits: 1 },
      ],
      s,
      b,
    );
    const [a, c] = lays.map((l, i) => badgeShapes(i === 0 ? "bomb" : "charge", l.at, l.sc, 1, "bl"));
    expect(c!.circle.x + c!.circle.r).toBeLessThan(Math.min(a!.circle.x - a!.circle.r, a!.box!.l));
  });
  it("朝東時讓開底圈外緣的三角形", () => {
    const u = drawOf({ facing: "east" });
    const { sh } = laidOut(u, s);
    const none = laidOut(drawOf(), s).sh;
    expect(span(sh.boxes).l).toBeGreaterThanOrEqual(span(none.boxes).l - 1e-6);
    expect(sideRowShift({ boxes: [] }, sideBlock(u, s, SHIELD_OUTLINE, NO_EDGE), s, null)).toEqual({ dx: 0, dy: 0 });
  });
});

describe("3×3 巨型灰燼之心同一套", () => {
  const P = (x: number, y: number) => ({ x, y });
  const tiles = [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => P(5 + dx, 3 + dy)));
  const heart = unit("heart", "enemy", 5, 3, {
    template_id: "ashen_heart",
    tags: ["boss", "elite"],
    facing: "south",
    doll_look: (dolls as Record<string, unknown>)["ashen_heart"] as UnitView["doll_look"],
    boss_phase: { index: 1, total: 3, name_zh: "x" } as UnitView["boss_phase"],
    statuses: ["molten_shell", "burning", "shielded", "charging"].map(st) as unknown as UnitView["statuses"],
    footprint: 3,
    tiles,
    parts: [part("core"), part("shell_seam"), part("vent")],
  } as Partial<UnitView>);
  const u = unitDrawOf(smallView({ width: 12, height: 12, units: [heart] }), heart, "", null, "h");
  it("800：狀態列在 HP 條右邊、蓄力徽章在左邊（都跟著頭目 HUD 搬到 3×3 上方）；1600 照原本", () => {
    expect(isGiantUnit(u)).toBe(true);
    const dy = bossHudDy(u);
    expect(dy).toBeLessThan(0);
    const { row, sh, charge } = laidOut(u, 0.531);
    expect(span(sh.boxes).l).toBeGreaterThanOrEqual(HP_W / 2);
    // 形狀是未加 `bossHudDy` 的本地座標；節點本身再加（整組在 3×3 頂上）
    expect(row.position.y).toBeLessThan(span(sh.boxes).b + dy + 1e-6);
    expect(charge.position.x).toBeLessThan(-HP_W / 2);
    expect(charge.position.y).toBeCloseTo((HP_Y + stripLayout(3, 0.531).bottom) / 2 + dy, 5);
    expect(span(laidOut(u, 1.308).sh.boxes).b).toBeLessThanOrEqual(HP_Y + 1e-6);
  });
});

describe("1600 寬與其他單位不變", () => {
  it("1600（1.31）：狀態列在 HP 條上方、不在右邊", () => {
    const { sh } = laidOut(drawOf(), 1.31);
    expect(span(sh.boxes).b).toBeLessThanOrEqual(HP_Y + 1e-6);
  });
  it("沒有部位的單位 800 寬照原本（狀態列在 HP 條上方）", () => {
    const { sh } = laidOut(drawOf({ parts: [] }), 0.53);
    expect(span(sh.boxes).b).toBeLessThanOrEqual(HP_Y + 1e-6);
  });
  it("同一個縮放重排多次結果一樣；縮放來回（800 → 1600 → 800）回到原位", () => {
    const u = drawOf();
    const c = buildUnitSprite(art, new Pulses(), u);
    const row = c.children.find((n) => n.label === STATUS_ROW_LABEL) as Container;
    const at = () => [row.position.x, row.position.y];
    for (const n of unitMarksOf(c)) applyMarkScale(n, 0.53, 0.53);
    const p800 = at();
    for (const n of unitMarksOf(c)) applyMarkScale(n, 1.31, 1.31);
    const p1600 = at();
    for (const n of unitMarksOf(c)) applyMarkScale(n, 0.53, 0.53);
    expect(at()).toEqual(p800);
    expect(p1600).not.toEqual(p800);
  });
});

describe("掛層：狀態列與徽章跟 HP 條同一層（南邊一排的地面蓋不到）", () => {
  it("有部位、有金菱形的頭目：狀態列、蓄力徽章掛在金菱形那一層", () => {
    const rows = new RowStack();
    rows.reset(4);
    const c = buildUnitSprite(art, new Pulses(), { ...drawOf(), elite: true });
    rows.row(1).units.addChild(c);
    rows.attachMarks(c);
    const front = c.children.find((n) => n.label === BOSS_RING_FRONT_LABEL)!;
    expect(front.parentRenderLayer).toBeInstanceOf(RenderLayer);
    for (const label of [STATUS_ROW_LABEL, CHARGE_BADGE_LABEL]) expect(c.children.find((n) => n.label === label)!.parentRenderLayer).toBe(front.parentRenderLayer);
  });
});
