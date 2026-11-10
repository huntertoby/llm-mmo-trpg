// HID-1b（美術 PM 11-07，`docs/art/HID-1檢查.md`）：
// 1. 「？」與所有 HUD（HP 條、狀態列、徽章）畫在霧上面，人物本身留在霧下面；
// 2. HP 條、「？」畫在攻擊紅框上面：紅框在單位層之下、HUD 之下，不縮框。
import { CanvasTextMetrics, Container, RenderLayer, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { HIDDEN_HP_LABEL, HP_BAR_LABEL, STATUS_ROW_LABEL, BOMB_BADGE_LABEL, FACING_ARROW_LABEL } from "../render/minMark";
import { ROW_HUD_LABELS, RowStack, UNIT_MARK_LABELS } from "../render/rowLayers";
import { BODY_LABEL, buildUnitSprite, Pulses } from "../render/unitSprite";
import { readFile, SRC_DIR } from "../test/sourceScan";

beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;
const view = (): BattleView =>
  ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
const BASE: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: null, charge: null, infused: false, statusIds: [], marker: "", facing: "east" };
const find = (c: Container, label: string) => c.children.find((k) => k.label === label) ?? null;

function setup(u: UnitDraw): { rows: RowStack; c: Container } {
  const rows = new RowStack();
  rows.reset(3);
  const c = buildUnitSprite(art, new Pulses(), u);
  rows.row(1).units.addChild(c);
  rows.attachMarks(c);
  return { rows, c };
}

describe("HID-1b：HUD 在霧之上、人物在霧之下", () => {
  it("圖層順序：紅框 < 單位 < 霧 < HUD（marks）；紅框在物件、高度徽章之上", () => {
    const rows = new RowStack();
    rows.reset(1);
    const r = rows.row(0);
    const at = (n: Container) => r.root.children.indexOf(n);
    expect(at(r.frames)).toBeGreaterThan(at(r.objects));
    expect(at(r.frames)).toBeGreaterThan(at(r.badges));
    expect(at(r.frames)).toBeLessThan(at(r.units));
    expect(at(r.units)).toBeLessThan(at(r.veil));
    expect(at(r.veil)).toBeLessThan(at(r.marks));
  });

  it("HP 條、「？」、狀態列、徽章都掛在該排 marks（霧之上），身體不掛（留在霧下）；仍是單位圖層的子節點", () => {
    const { rows, c } = setup({ ...BASE, shieldRatio: 0.5, hiddenInfo: true, bomb: 2, statusIds: ["burning"] });
    expect(find(c, HIDDEN_HP_LABEL)!.parent).toBe(c); // HID-1c：「？」掛南邊一排的 under，測試在 hid1cLayers
    for (const l of [HP_BAR_LABEL, STATUS_ROW_LABEL, BOMB_BADGE_LABEL]) {
      const n = find(c, l)!;
      expect(n.parentRenderLayer, l).toBe(rows.row(1).marks);
      expect(n.parent, l).toBe(c);
    }
    const body = c.children.find((n) => n.label === BODY_LABEL);
    expect(body?.parentRenderLayer ?? null).toBeNull();
  });

  it("順序照子節點：徽章在 HP 條、狀態列之上（marks 的掛載順序）", () => {
    const { rows, c } = setup({ ...BASE, bomb: 2, statusIds: ["burning"] });
    const order = rows.row(1).marks.renderLayerChildren;
    expect(order.indexOf(find(c, HP_BAR_LABEL)!)).toBeLessThan(order.indexOf(find(c, BOMB_BADGE_LABEL)!));
    expect(order.indexOf(find(c, STATUS_ROW_LABEL)!)).toBeLessThan(order.indexOf(find(c, BOMB_BADGE_LABEL)!));
  });

  it("朝向三角形不在霧上（畫在身體之下的那種要被身體蓋）；被高台擋住時照舊跟其他 HUD 一起上去", () => {
    const { rows, c } = setup(BASE);
    const arrow = find(c, FACING_ARROW_LABEL)!;
    expect(arrow.parentRenderLayer ?? null).toBeNull();
    expect(ROW_HUD_LABELS).not.toContain(FACING_ARROW_LABEL);
    const hud = new RenderLayer();
    rows.attachHud(c, hud);
    expect(arrow.parentRenderLayer).toBe(hud);
    rows.attachMarks(c);
    expect(arrow.parentRenderLayer ?? null).toBeNull();
    for (const l of [HP_BAR_LABEL, ...UNIT_MARK_LABELS.filter((x) => find(c, x) !== null)]) expect(find(c, l)!.parentRenderLayer, l).toBe(rows.row(1).marks);
  });

  it("走路換排：HUD 跟到新那一排的 marks", () => {
    const { rows, c } = setup({ ...BASE, hiddenInfo: true });
    rows.row(2).units.addChild(c);
    rows.attachMarks(c);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(rows.row(2).marks);
    expect(rows.row(1).marks.renderLayerChildren).toHaveLength(0);
  });

  it("clearFrames 清掉每一排的紅框", () => {
    const rows = new RowStack();
    rows.reset(2);
    rows.row(0).frames.addChild(new Container());
    rows.row(1).frames.addChild(new Container());
    rows.clearFrames();
    expect(rows.row(0).frames.children).toHaveLength(0);
    expect(rows.row(1).frames.children).toHaveLength(0);
  });
});

describe("HID-1b：攻擊紅框的接線", () => {
  const highlight = readFile(SRC_DIR, "render/battle/highlightLayer.ts");

  it("紅框畫在該排 frames（單位之下）；被高台、屋頂擋住的格子改在 attackTop（看得到框）", () => {
    expect(highlight).toContain("this.rows.row(p.y).frames");
    expect(highlight).toContain("occluded(model, p) || roofCovers(model.scenery, p)");
    expect(highlight).toContain("this.attackTop");
  });

  it("紅框沒有縮小（維持 T − 4 的圓角框，線寬 3）", () => {
    expect(highlight).toContain("roundRect(o.x + 2, o.y + 2, T - 4, T - 4, 8).stroke({ width: 3, color: HIGHLIGHT.attack })");
  });

  it("draw 之後重畫紅框（rows.reset 會清掉）；attackTop 在 marks 之後、hudTop 之前", () => {
    const src = readFile(SRC_DIR, "render/BattleRenderer.ts");
    expect(src).toContain("this.drawAttackFrames()");
    const line = src.split("\n").find((l) => l.includes("this.world.addChild(this.rows.root"))!;
    expect(line.indexOf("this.attackTop")).toBeGreaterThan(line.indexOf("this.marks"));
    expect(line.indexOf("this.attackTop")).toBeLessThan(line.indexOf("this.hudTop"));
  });
});
