// 6F-22（美術 PM 11-06，`docs/art/6F-21檢查.md` 第 5 節）：被南邊高台擋住的單位，身體照舊被擋、畫剪影虛線；
// HP 條（含護盾條）、狀態列（含「+N」膠囊）、朝向三角形、徽章改在高台之上的全域層（剪影之後）畫。沒被擋時不變。
import { CanvasTextMetrics, Container, RenderLayer, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView, type Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import {
  BOMB_BADGE_LABEL,
  CHARGE_BADGE_LABEL,
  DOWNED_BADGE_LABEL,
  FACING_ARROW_LABEL,
  HP_BAR_LABEL,
  INFUSED_BADGE_LABEL,
  SOUTH_ARROW_LABEL,
  STATUS_ROW_LABEL,
  SUMMON_BADGE_LABEL,
} from "../render/minMark";
import { HUD_LABELS, RowStack, UNIT_MARK_LABELS } from "../render/rowLayers";
import { buildUnitSprite, PLUS_CAP_LABEL, Pulses } from "../render/unitSprite";
import { readSources, stripTsComments, battleRendererSource } from "../test/sourceScan";

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
const BASE: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: null, charge: null, infused: false, statusIds: [], marker: "", facing: "east" };
// 狀態 4 個（2 個圖示＋「+N」膠囊）、護盾、炸彈、蓄力、灌注
const FULL: UnitDraw = { ...BASE, shieldRatio: 0.5, bomb: 2, charge: 1, infused: true, statusIds: ["burning", "slow", "defending", "poisoned"] };

const find = (c: Container, label: string) => c.children.find((k) => k.label === label) ?? null;
const HUD = [HP_BAR_LABEL, STATUS_ROW_LABEL, FACING_ARROW_LABEL, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL];

function setup(): { rows: RowStack; hud: RenderLayer; c: Container } {
  const rows = new RowStack();
  rows.reset(3);
  const hud = new RenderLayer();
  const c = buildUnitSprite(art, new Pulses(), FULL);
  rows.row(1).units.addChild(c);
  rows.attachMarks(c);
  return { rows, hud, c };
}

describe("6F-22：被高台擋住的單位，HUD 畫在高台之上", () => {
  it("HUD 節點都有標籤：HP 條、狀態列（「+N」膠囊在狀態列裡）、朝向三角形、徽章", () => {
    const c = buildUnitSprite(art, new Pulses(), FULL);
    for (const l of HUD) expect(find(c, l), l).not.toBeNull();
    const row = find(c, STATUS_ROW_LABEL) as Container;
    expect(row.children.some((k) => k.label === PLUS_CAP_LABEL && k.visible)).toBe(true);
    for (const l of [HP_BAR_LABEL, STATUS_ROW_LABEL, FACING_ARROW_LABEL, SUMMON_BADGE_LABEL, DOWNED_BADGE_LABEL]) expect(HUD_LABELS).toContain(l);
    // 朝南、有 HP 條的三角形照 6F-21b（另有圖層），不在這一組
    expect(HUD_LABELS).not.toContain(SOUTH_ARROW_LABEL);
    for (const f of ["east", "west", "north"] as Facing[]) expect(find(buildUnitSprite(art, new Pulses(), { ...BASE, facing: f }), FACING_ARROW_LABEL), f).not.toBeNull();
  });

  it("擋住：HP 條、狀態列、三角形、徽章都掛在高台之上的層（仍是單位圖層的子節點）；身體不動；順序照子節點（徽章在 HP 條、狀態列之上）", () => {
    const { rows, hud, c } = setup();
    rows.attachHud(c, hud);
    for (const l of HUD) {
      const n = find(c, l)!;
      expect(n.parentRenderLayer, l).toBe(hud);
      expect(n.parent, l).toBe(c);
    }
    for (const n of c.children) if (!HUD_LABELS.includes(n.label) && !UNIT_MARK_LABELS.includes(n.label)) expect(n.parentRenderLayer ?? null, n.label).toBeNull();
    const order = hud.renderLayerChildren;
    expect(order.indexOf(find(c, HP_BAR_LABEL)!)).toBeLessThan(order.indexOf(find(c, STATUS_ROW_LABEL)!));
    expect(order.indexOf(find(c, STATUS_ROW_LABEL)!)).toBeLessThan(order.indexOf(find(c, BOMB_BADGE_LABEL)!));
  });

  it("沒被擋（hud ＝ null）：照舊——HP 條、狀態列、三角形跟著單位畫，徽章在那一排的 marks", () => {
    const { rows, c } = setup();
    rows.attachHud(c, null);
    expect(find(c, FACING_ARROW_LABEL)!.parentRenderLayer ?? null).toBeNull();
    for (const l of [HP_BAR_LABEL, STATUS_ROW_LABEL, ...UNIT_MARK_LABELS]) expect(find(c, l)!.parentRenderLayer, l).toBe(rows.row(1).marks); // HID-1b：HP 條、狀態列在霧上
  });

  it("移動途中（attachMarks 重接）：HUD 回到跟著單位畫、徽章回到所在那一排的 marks", () => {
    const { rows, hud, c } = setup();
    rows.attachHud(c, hud);
    rows.row(2).units.addChild(c);
    rows.attachMarks(c);
    expect(find(c, FACING_ARROW_LABEL)!.parentRenderLayer ?? null).toBeNull();
    for (const l of [HP_BAR_LABEL, STATUS_ROW_LABEL, ...UNIT_MARK_LABELS]) expect(find(c, l)!.parentRenderLayer, l).toBe(rows.row(2).marks);
  });

  it("召喚物回合數、倒下徽章也一起上去", () => {
    const rows = new RowStack();
    rows.reset(2);
    const hud = new RenderLayer();
    const down = buildUnitSprite(art, new Pulses(), { ...BASE, downed: true, revivable: true });
    rows.row(0).units.addChild(down);
    rows.attachMarks(down);
    rows.attachHud(down, hud);
    expect(find(down, DOWNED_BADGE_LABEL)!.parentRenderLayer).toBe(hud);
    expect(find(down, HP_BAR_LABEL)!.parentRenderLayer).toBe(hud);
    const sum = buildUnitSprite(art, new Pulses(), { ...BASE, summon: true, summonTurns: 2 } as UnitDraw);
    rows.row(0).units.addChild(sum);
    rows.attachMarks(sum);
    rows.attachHud(sum, hud);
    expect(find(sum, SUMMON_BADGE_LABEL)!.parentRenderLayer).toBe(hud);
  });

  it("接線：全域層排在剪影之後、游標之前；畫單位與轉身時只在 occluded（或 6F-22b 屋頂蓋住）才給層；朝南三角形照 6F-21b", () => {
    const src = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
    const r = battleRendererSource(src);
    expect(r).toContain("this.silhouettes, this.hudTop, this.hover,");
    expect(r).toContain("return occluded(model, u) || roofCovers(model.scenery, u) ? this.hudTop : null;"); // 6F-22b：屋頂比照
    expect(r).toContain("this.rows.attachHud(sprite, this.hudLayerOf(model, u));");
    expect(r).toContain("this.rows.attachHud(fresh, this.model === null ? null : this.hudLayerOf(this.model, next));");
    expect(r.match(/this\.rows\.attachHud\(/g)?.length).toBe(2);
  });
});
