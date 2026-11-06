// 6F-22b（美術 PM 6F-22 檢查第 2 節）：
// - 第 2 題（資訊洩漏）：單位因煙霧、黑暗、隱匿而不顯示（或只顯示「?」）時，HUD（HP 條、護盾、狀態列、三角形、徽章）也不能畫；
//   單位本身看得到時照畫。現況：伺服器的 `UnitView` 沒有「看不見」的欄位（隱蔽 `concealed` 只是戰鬥修正，所有在場單位都完整送來），
//   前端也沒有藏起單位身體的情況（煙霧、黑暗只在單位下半身疊一層霧，隱蔽畫成半透明），所以沒有洩漏。
//   這裡鎖住：① 掛在高台之上全域層（`hudTop`）的 HUD 仍是單位圖層的子節點，身體藏起來（`visible`／`alpha`）時 HUD 跟著不畫（包含移動途中回原層後）；
//   ② `UnitView` 一旦多了「看不見」的欄位，這裡會失敗，提醒要一起處理 HUD。
// - 第 3 題：護盾條加一圈深色外框（高度維持 2px）。第 4 題：「▲N」被北邊單位的 HUD 蓋住時改放左下角。
import { CanvasTextMetrics, Container, Graphics, RenderLayer, Texture, updateRenderGroupTransforms } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { HEIGHT_MARK_BG, heightMarkAtCorner, heightMarkCornerDrop } from "../render/heightMark";
import { BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, FACING_ARROW_LABEL, HP_BAR_LABEL, INFUSED_BADGE_LABEL, STATUS_ROW_LABEL } from "../render/minMark";
import { RowStack } from "../render/rowLayers";
import { CONCEALED } from "../render/statusIcon";
import { buildUnitSprite, hpBoxOf, Pulses, SHIELD_OUTLINE } from "../render/unitSprite";
import { readFile, SRC_DIR } from "../test/sourceScan";

beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const T = TILE_SIZE;
const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;

/** 敵人站在黑暗（或煙霧）裡、身上隱蔽，北邊是主角。 */
function hiddenView(surface: "darkness" | "smoke" | "none"): BattleView {
  const tiles = [tile(0, 0), tile(0, 1, { surface })];
  const units = [
    unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" }),
    unit("unit_0002", "enemy", 0, 1, { hp: 7, max_hp: 20, shield: 5, statuses: [{ status_id: CONCEALED, name_zh: "隱蔽", remaining: 2, stacks: 1 }] as never }),
  ];
  return { team: "ally", map_id: "m", map_name_zh: "m", width: 1, height: 2, tiles, objects: [], units, traps: [], turn_order: ["unit_0001", "unit_0002"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}

const FULL = (u: UnitDraw): UnitDraw => ({ ...u, shieldRatio: 0.5, bomb: 2, charge: 1, infused: true, statusIds: ["burning", "slow", "defending", "poisoned"], facing: "east" });
const HUD = [HP_BAR_LABEL, STATUS_ROW_LABEL, FACING_ARROW_LABEL, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL];
const find = (c: Container, label: string) => c.children.find((k) => k.label === label)!;
const VISIBLE = 0b111;

/** 和繪製器一樣的結構：根（render group）底下排的圖層、高台之上的 HUD 層。 */
function scene(): { stage: Container; rows: RowStack; hud: RenderLayer; c: Container } {
  const stage = new Container({ isRenderGroup: true });
  const rows = new RowStack();
  rows.reset(3);
  const hud = new RenderLayer();
  stage.addChild(rows.root, hud);
  const c = buildUnitSprite(art, new Pulses(), FULL(buildDrawModel(hiddenView("darkness"), "unit_0001").units[1]!));
  rows.row(1).units.addChild(c);
  rows.attachMarks(c);
  return { stage, rows, hud, c };
}
const update = (stage: Container) => updateRenderGroupTransforms(stage.renderGroup!, true);
/** Pixi 收集要畫的東西時跳過 `globalDisplayStatus < 0b111` 的節點；透明度乘上祖先的 `groupAlpha`。 */
const drawn = (n: Container) => n.globalDisplayStatus >= VISIBLE && n.groupAlpha > 0;

describe("6F-22b 第 1 項：看不見的單位不畫 HUD（資訊洩漏）", () => {
  it("現況：煙霧、黑暗裡隱蔽的敵人照常畫出（身體在、半透明），HUD 照畫——單位看得到", () => {
    for (const surface of ["darkness", "smoke"] as const) {
      const m = buildDrawModel(hiddenView(surface), "unit_0001");
      const e = m.units.find((u) => u.id === "unit_0002");
      expect(e, surface).toBeDefined();
      expect(e!.statusIds).toContain(CONCEALED);
      const c = buildUnitSprite(art, new Pulses(), e!);
      expect(c.visible && c.alpha > 0, surface).toBe(true);
      expect(c.children.some((k) => k.label === HP_BAR_LABEL), surface).toBe(true);
    }
  });

  it("伺服器的 UnitView 沒有「看不見」的欄位（多了這種欄位時這裡會失敗：要一起讓 HUD 跟著不畫）", () => {
    const schema = readFile(SRC_DIR, "api/schema.d.ts");
    const start = schema.indexOf("        UnitView: {");
    expect(start).toBeGreaterThan(0);
    const block = schema.slice(start, schema.indexOf("\n        };", start));
    expect(block).not.toMatch(/^\s+(hidden|visible|unseen|seen|revealed|unknown|obscured)\??:/m);
  });

  it("擋住時掛在 hudTop：身體藏起來（visible = false）或透明（alpha 0）時，HUD 跟著不畫；看得到時照畫", () => {
    const { stage, rows, hud, c } = scene();
    rows.attachHud(c, hud);
    update(stage);
    for (const l of HUD) expect(drawn(find(c, l)), l).toBe(true);
    c.visible = false;
    update(stage);
    for (const l of HUD) {
      expect(find(c, l).parentRenderLayer, l).toBe(hud);
      expect(drawn(find(c, l)), l).toBe(false);
    }
    c.visible = true;
    c.alpha = 0;
    update(stage);
    for (const l of HUD) expect(drawn(find(c, l)), l).toBe(false);
  });

  it("沒被擋（HUD 跟著單位、徽章在那一排的 marks）與移動途中回原層後，一樣跟著身體藏起來", () => {
    const { stage, rows, hud, c } = scene();
    rows.attachHud(c, null);
    c.visible = false;
    update(stage);
    for (const l of HUD) expect(drawn(find(c, l)), l).toBe(false);
    c.visible = true;
    rows.attachHud(c, hud);
    rows.row(2).units.addChild(c); // 走路途中換排：HUD 回原層
    rows.attachMarks(c);
    c.visible = false;
    update(stage);
    for (const l of HUD) expect(drawn(find(c, l)), l).toBe(false);
  });

  it("HUD 只用 RenderLayer.attach 換畫的順序，不搬到別的容器（父節點一律是單位圖層）", () => {
    const { rows, hud, c } = scene();
    rows.attachHud(c, hud);
    for (const l of HUD) expect(find(c, l).parent, l).toBe(c);
  });
});

describe("6F-22b 第 3 項：護盾條的深色外框", () => {
  const base = buildDrawModel(hiddenView("none"), "unit_0001").units[0]!;
  it("護盾條外面一圈 1px 深色外框，護盾條本身維持 2px；hpBoxOf 含外框", () => {
    const bar = find(buildUnitSprite(art, new Pulses(), { ...base, shieldRatio: 1, hpRatio: 1 }), HP_BAR_LABEL) as Graphics;
    const b = bar.getLocalBounds();
    const box = hpBoxOf({ shieldRatio: 1 })!;
    expect(SHIELD_OUTLINE).toBe(1);
    expect(b.minY).toBeCloseTo(T * 0.36 - 3 - SHIELD_OUTLINE);
    expect(b.minX).toBeCloseTo(-T * 0.4 - SHIELD_OUTLINE);
    expect(box.t).toBeCloseTo(b.minY);
    expect(box.l).toBeCloseTo(b.minX);
    expect(box.r).toBeCloseTo(b.maxX);
    expect(box.b).toBeCloseTo(b.maxY);
    const none = find(buildUnitSprite(art, new Pulses(), { ...base, shieldRatio: 0 }), HP_BAR_LABEL) as Graphics;
    expect(none.getLocalBounds().minY).toBeCloseTo(T * 0.36);
    expect(hpBoxOf({ shieldRatio: 0 })!.l).toBeCloseTo(-T * 0.4);
  });

  it("畫法：先畫深色外框、再畫 2px 淺藍（顏色不換）", () => {
    const src = readFile(SRC_DIR, "render/unitSprite.ts");
    expect(src).toContain("bar.rect(-w / 2 - o, T * 0.36 - 3 - o, w * u.shieldRatio + 2 * o, 2 + 2 * o).fill(0x000000);");
    expect(src).toContain("bar.rect(-w / 2, T * 0.36 - 3, w * u.shieldRatio, 2).fill(0x9fd8ff);");
  });
});

describe("6F-22b 第 4 項：「▲N」被北邊單位的 HUD 蓋住時改放左下角", () => {
  const grid = (hs: number[]) => ({ width: 1, height: hs.length, tiles: hs.map((height) => ({ height })) });
  it("北邊有人、而且被這一格擋住（這格比較高）才放左下角", () => {
    expect(heightMarkAtCorner(grid([0, 2]), [{ x: 0, y: 0 }], { x: 0, y: 1 })).toBe(true);
    expect(heightMarkAtCorner(grid([0, 3]), [{ x: 0, y: 0 }], { x: 0, y: 1 })).toBe(true);
    expect(heightMarkAtCorner(grid([0, 2]), [], { x: 0, y: 1 }), "北邊沒人").toBe(false);
    expect(heightMarkAtCorner(grid([2, 2]), [{ x: 0, y: 0 }], { x: 0, y: 1 }), "一樣高：沒被擋").toBe(false);
    expect(heightMarkAtCorner(grid([3, 2]), [{ x: 0, y: 0 }], { x: 0, y: 1 }), "北邊比較高").toBe(false);
    expect(heightMarkAtCorner(grid([2]), [], { x: 0, y: 0 }), "最北一排").toBe(false);
  });

  it("左下角：底離格子下緣和原本離上緣一樣（各種放大倍率）", () => {
    for (const k of [1, 1.25, 1.6]) {
      const dy = heightMarkCornerDrop(k);
      const bottom = k * (HEIGHT_MARK_BG.y + HEIGHT_MARK_BG.h + dy);
      expect(T - bottom, String(k)).toBeCloseTo(k * HEIGHT_MARK_BG.y);
    }
  });

  it("接線：畫「▲N」時照 heightMarkAtCorner 決定，底與數字一起往下移", () => {
    const src = readFile(SRC_DIR, "render/BattleRenderer.ts");
    expect(src).toContain("const corner = heightMarkAtCorner(model, model.units, t);");
    expect(src).toContain("g.y = heightMarkCornerDrop(k);");
    expect(src).toContain("num.y = HEIGHT_MARK_NUM.y + g.y;");
  });
});
