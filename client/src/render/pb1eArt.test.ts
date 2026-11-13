// PB-1e：頭目部位的戰場畫法（頭頂小格節點、朝南三角形、HUD 掛層、亮起像素、演出格、外觀旗標到 Q 版人物、選單點擊冒泡）。
import { CanvasTextMetrics, Container, RenderLayer, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, PartView, UnitView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { stripLayout } from "../battle/partStrip";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "./artTextures";
import { BREAK_MS, breakFrameAt, breakFxOf, glowRgba, popScale, STRIP_BASE_SCALE } from "./bossPartArt";
import { applyMarkScale, HP_BAR_LABEL, MIN_BREAK_POP_FONT_PX, PART_STRIP_LABEL, SOUTH_ARROW_LABEL } from "./minMark";
import { qUnitOf } from "./qSpec";
import { HUD_LABELS, RowStack } from "./rowLayers";
import { buildUnitSprite, facingArrowPoly, hpBoxOf, PART_DEBRIS_LABEL, PART_HUD_UP_ARROW, PART_HUD_UP_ARROW_MIN_PX, Pulses, specOfUnit } from "./unitSprite";
import { readFile, SRC_DIR } from "../test/sourceScan";

const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null, canvas: () => null, figureRes: () => 2 } as unknown as ArtTextures;
beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const part = (id: string, o: Partial<PartView> = {}): PartView => ({ id, name_zh: id, hp: 24, max_hp: 24, broken: false, exposed: true, reach: "any", break_lines_zh: [], ...o });
function viewWith(units: UnitView[]): BattleView {
  const tiles = [];
  for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) tiles.push(tile(x, y));
  return { team: "ally", map_id: "t", width: 4, height: 4, tiles, objects: [], units, traps: [], turn_order: [], active_unit: null, round: 1, max_rounds: 30, objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
const bossDraw = (o: Partial<UnitView> = {}, south = false): UnitDraw => {
  const b = unit("b", "enemy", 1, 1, { facing: "south", parts: [part("whisk"), part("dantian"), part("sword", { broken: true })], ...o } as Partial<UnitView>);
  const units = south ? [b, unit("h", "ally", 1, 2)] : [b];
  return buildDrawModel(viewWith(units), "h").units.find((u) => u.id === "b")!;
};

describe("頭頂部位小格", () => {
  it("有部位的單位多一個部位小格節點（跟著 HP 條掛同一層）；沒有部位、倒下的沒有", () => {
    const c = buildUnitSprite(art, new Pulses(), bossDraw());
    expect(c.children.some((n) => n.label === PART_STRIP_LABEL)).toBe(true);
    expect(HUD_LABELS).toContain(PART_STRIP_LABEL);
    const plain = buildUnitSprite(art, new Pulses(), buildDrawModel(viewWith([unit("u", "enemy", 1, 1)]), "h").units[0]!);
    expect(plain.children.some((n) => n.label === PART_STRIP_LABEL)).toBe(false);
  });
  it("hpBoxOf 包進部位小格；朝南三角形的上緣離部位小格下緣 0.5", () => {
    const u = bossDraw();
    const L = stripLayout(3, STRIP_BASE_SCALE);
    expect(hpBoxOf(u)!.b).toBeCloseTo(L.bottom);
    const p = facingArrowPoly(u);
    expect(Math.min(p[1]!, p[3]!, p[5]!) - 0.5).toBeCloseTo(L.bottom + 0.5);
  });
  it("地圖縮小時重畫部位小格，朝南三角形跟著往下挪（pivot）；地圖夠大時不挪", () => {
    const c = buildUnitSprite(art, new Pulses(), bossDraw());
    const strip = c.children.find((n) => n.label === PART_STRIP_LABEL) as Container;
    const arrow = c.children.find((n) => n.label === SOUTH_ARROW_LABEL)!;
    applyMarkScale(strip, 1.31, 1.31);
    expect(arrow.pivot.y).toBeCloseTo(0);
    applyMarkScale(strip, 0.53, 0.53);
    expect(arrow.pivot.y).toBeCloseTo(-(stripLayout(3, 0.53).bottom - stripLayout(3, STRIP_BASE_SCALE).bottom));
    expect(strip.scale.x).toBe(1);
  });
  it("南邊有人：朝南三角形以上緣中點縮小（移植需求第 4 節第 4 點）", () => {
    const up = facingArrowPoly(bossDraw({}, true));
    const base = facingArrowPoly(bossDraw());
    const w = (p: number[]) => Math.max(p[0]!, p[2]!, p[4]!) - Math.min(p[0]!, p[2]!, p[4]!);
    expect(w(up) / w(base)).toBeCloseTo(PART_HUD_UP_ARROW);
    expect(Math.min(up[1]!, up[3]!, up[5]!)).toBeCloseTo(Math.min(base[1]!, base[3]!, base[5]!));
  });
  it("金菱形伸進南邊一排時，HP 條＋部位小格改掛同一層、排在金菱形之後（不被蓋住）", () => {
    const rows = new RowStack();
    rows.reset(4);
    const c = buildUnitSprite(art, new Pulses(), { ...bossDraw(), elite: true });
    rows.row(1).units.addChild(c);
    rows.attachMarks(c);
    const south = rows.row(2).under;
    const hp = c.children.find((n) => n.label === HP_BAR_LABEL)!;
    const strip = c.children.find((n) => n.label === PART_STRIP_LABEL)!;
    expect(hp.parentRenderLayer).toBe(south);
    expect(strip.parentRenderLayer).toBe(south);
    expect(south).toBeInstanceOf(RenderLayer);
  });
});

describe("外觀旗標接到 Q 版人物", () => {
  it("拂塵剪短、劍斷掛在那件手持物上；氣海的氣旋／裂痕掛在單位上；沒有部位的單位不變", () => {
    const spec = specOfUnit(bossDraw({ doll_look: { gear: { off_hand: { kind: "whisk", material: "wood" } } } as unknown as UnitView["doll_look"], weapon_id: "one_handed_sword", parts: [part("whisk", { broken: true }), part("sword", { broken: true }), part("dantian")] }));
    expect(spec.parts).toEqual({ whisk: true, sword: true, dantian: "qi" });
    const q = qUnitOf(spec);
    expect(q.gear.off_hand?.cut).toBe(true);
    expect(q.gear.main_hand?.broken).toBe(true);
    expect(q.dantian).toBe("qi");
    const plain = specOfUnit(buildDrawModel(viewWith([unit("u", "enemy", 1, 1)]), "h").units[0]!);
    expect("parts" in plain).toBe(false);
  });
  it("破了的部位：地上有掉落物節點（演出前三格沒有）", () => {
    const canvasArt = { ...art, canvas: () => Texture.WHITE } as unknown as ArtTextures;
    const u = bossDraw();
    expect(buildUnitSprite(canvasArt, new Pulses(), u).children.some((n) => n.label === PART_DEBRIS_LABEL)).toBe(true);
    expect(buildUnitSprite(canvasArt, new Pulses(), { ...u, partFx: { part: "sword", k: "fly" } }).children.some((n) => n.label === PART_DEBRIS_LABEL)).toBe(false);
  });
});

describe("亮起與演出", () => {
  it("亮起：部位上 35% 同色；往外先亮青白、再外框色；遠處透明", () => {
    const w = 9;
    const a = new Uint8Array(w * w);
    a[4 * w + 4] = 255;
    const px = glowRgba(a, w, w, 1.4, 0.9);
    const at = (x: number, y: number) => Array.from(px.slice((y * w + x) * 4, (y * w + x) * 4 + 4));
    expect(at(4, 4)).toEqual([0xa8, 0xf4, 0xff, Math.round(255 * 0.35)]);
    expect(at(5, 4).slice(0, 3)).toEqual([0xa8, 0xf4, 0xff]);
    expect(at(5, 4)[3]).toBe(255);
    expect(at(0, 0)[3]).toBe(0);
  });
  it("5 格的時間：80、80、160、160 之後定格；前三格蓋過人物，落地起回到伺服器的樣子", () => {
    expect(BREAK_MS).toBe(480);
    expect([0, 79, 80, 159, 160, 319, 320, 479, 480].map(breakFrameAt)).toEqual([0, 0, 1, 1, 2, 2, 3, 3, 4]);
    expect([0, 1, 2, 3].map((f) => breakFxOf("whisk", f)?.k ?? null)).toEqual(["flash", "crack", "fly", null]);
  });
});

describe("接線", () => {
  it("選單打開時淡化狀態列與蓄力徽章 40%、滑過的部位亮起；重畫場景後再套一次", () => {
    const r = readFile(SRC_DIR, "render/battle/unitLayer.ts");
    expect(r).toMatch(/STATUS_ROW_LABEL \|\| n\.label === CHARGE_BADGE_LABEL/);
    expect(r).toMatch(/PART_MENU_DIM = 0\.4/);
    expect(readFile(SRC_DIR, "render/BattleRenderer.ts")).toMatch(/this\.applyPartFocus\(\);/);
    expect(readFile(SRC_DIR, "screens/BattleScreen.tsx")).toMatch(/setPartFocus\(/);
  });
  it("選單列的點擊只認列裡面的元素（portal 的說明卡冒泡上來不算選了這一列）", () => {
    expect(readFile(SRC_DIR, "ui/PartMenu.tsx")).toMatch(/e\.currentTarget\.contains\(e\.target\)/);
  });
});

describe("PB-1f：「破」字記號最小尺寸、800 寬朝南三角形不縮（美術 PM PB-1e 驗收裁定）", () => {
  it("「破」字畫面上 ≥ 12 px：倍率 max(1, 12 ／ (14 × 地圖縮放))", () => {
    expect(MIN_BREAK_POP_FONT_PX).toBe(12);
    expect(popScale(1.31)).toBe(1);
    expect(popScale(12 / 14)).toBeCloseTo(1);
    expect(popScale(0.53)).toBeCloseTo(1.617, 2); // 約 ×1.62
    expect(14 * popScale(0.53) * 0.53).toBeCloseTo(12);
  });
  it("演出接上地圖縮放：倍率進貼圖快取鍵，圓、外圈、字一起放大，位置不放大", () => {
    const fx = readFile(SRC_DIR, "render/partBreakFx.ts");
    expect(fx).toMatch(/popScale\(host\.boardScale\?\.\(\) \?\? 1\)/);
    expect(fx).toMatch(/popK\.toFixed\(3\)/);
    const src = readFile(SRC_DIR, "render/bossPartArt.ts");
    expect(src).toMatch(/POP_STYLE\.r \* k/);
    expect(src).toMatch(/POP_STYLE\.ringW \* k/);
    expect(src).toMatch(/POP_STYLE\.font \* k/);
    expect(src).toMatch(/center\.x \+ px \* sd, center\.y \+ py, 1, f\.popK \?\? 1/);
    expect(readFile(SRC_DIR, "render/battle/vfxLayer.ts")).toMatch(/boardScale: \(\) => this\.scale/);
  });
  it("南邊有人：1600 寬（1.31、1.03）朝南三角形縮 0.6；800 寬（0.53）不縮", () => {
    const up = bossDraw({}, true);
    const w = (p: number[]) => Math.max(p[0]!, p[2]!, p[4]!) - Math.min(p[0]!, p[2]!, p[4]!);
    const full = w(facingArrowPoly(bossDraw()));
    expect(w(facingArrowPoly(up, 1.31)) / full).toBeCloseTo(PART_HUD_UP_ARROW);
    expect(w(facingArrowPoly(up, 1.03)) / full).toBeCloseTo(PART_HUD_UP_ARROW);
    expect(w(facingArrowPoly(up, 0.53)) / full).toBeCloseTo(1);
    expect((full * PART_HUD_UP_ARROW + 1) * 0.53).toBeLessThan(PART_HUD_UP_ARROW_MIN_PX);
  });
  it("地圖縮放改變時三角形節點跟著重畫（部位小格的重排）", () => {
    const c = buildUnitSprite(art, new Pulses(), bossDraw({}, true));
    const strip = c.children.find((n) => n.label === PART_STRIP_LABEL) as Container;
    const arrow = c.children.find((n) => n.label === SOUTH_ARROW_LABEL) as Container;
    applyMarkScale(strip, 1.31, 1.31);
    const big = arrow.getLocalBounds().width;
    applyMarkScale(strip, 0.53, 0.53);
    const small = arrow.getLocalBounds().width;
    expect(small).toBeGreaterThan(big * 1.4);
    applyMarkScale(strip, 1.31, 1.31);
    expect(arrow.getLocalBounds().width).toBeCloseTo(big);
  });
});
