// HID-1：隱蔽中的敵人只藏資訊（05 5.1.2，玩法決定 #144）。伺服器給 `hidden_info: true`、`hp`／`shield` 為 null、
// `statuses`／`stacks` 為空；前端在 HUD（Pixi HP 條）、滑過資訊卡與單位卡（`UnitInfo`）、行動順序列寫「？」，身體照畫。
import { CanvasTextMetrics, Texture, type Text } from "pixi.js";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, UnitView } from "../api/types";
import { type ArtTextures } from "../render/artTextures";
import { HIDDEN_HP_LABEL, HP_BAR_LABEL, STATUS_ROW_LABEL, unitMarksOf } from "../render/minMark";
import { HUD_LABELS } from "../render/rowLayers";
import { buildUnitSprite, HIDDEN_HP_FILL, HIDDEN_HP_GLYPH, Pulses } from "../render/unitSprite";
import { barData, unitChips } from "../ui/statusCard";
import { TurnBar } from "../ui/TurnBar";
import { UnitInfo } from "../ui/UnitInfo";
import { buildDrawModel } from "./drawModel";
import { HIDDEN_INFO_HINT, hpValueText, isHiddenInfo, standing, UNKNOWN_MARK } from "./hiddenInfo";
import { smallView, unit } from "./testFixtures";
import type { UnitNames } from "./units";

beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;
const names: UnitNames = { name: (id) => id, marker: (id) => id.slice(-1), label: (id) => id } as UnitNames;

const hero = unit("unit_0001", "ally", 0, 2, { template_id: "hero_fighter" });
/** 伺服器遮過的隱蔽敵人。 */
const hidden: UnitView = unit("unit_0002", "enemy", 3, 2, { hp: null, shield: null, max_hp: 30, hidden_info: true, statuses: [], stacks: {} });
/** 同一個敵人，相鄰或被揭露後（完整資訊）。 */
const shown: UnitView = unit("unit_0002", "enemy", 1, 2, {
  hp: 12,
  shield: 4,
  max_hp: 30,
  statuses: [{ status_id: "burning", name_zh: "燃燒", remaining: 2, source_id: null, amount: null }] as never,
});
const viewWith = (foe: UnitView): BattleView => ({ ...smallView(), units: [hero, foe], turn_order: [hero.id, foe.id], active_unit: hero.id });

describe("HID-1：隱蔽中的敵人只藏資訊", () => {
  it("小工具：看不到 HP 的人算站著、HP 寫「？」", () => {
    expect(isHiddenInfo(hidden)).toBe(true);
    expect(isHiddenInfo(shown)).toBe(false);
    expect(standing(hidden)).toBe(true);
    expect(standing({ hp: 0, downed: false })).toBe(false);
    expect(hpValueText(hidden)).toBe(UNKNOWN_MARK);
    expect(hpValueText(shown)).toBe("12");
  });

  it("畫法資料：HP 條灰色整條、沒有護盾條、沒有狀態；完整時照舊", () => {
    const h = buildDrawModel(viewWith(hidden), hero.id).units.find((u) => u.id === hidden.id)!;
    expect(h).toMatchObject({ hiddenInfo: true, hpRatio: 1, shieldRatio: 0, statusIds: [], x: 3, y: 2, name: hidden.name_zh });
    const s = buildDrawModel(viewWith(shown), hero.id).units.find((u) => u.id === shown.id)!;
    expect(s.hiddenInfo).toBe(false);
    expect(s.hpRatio).toBeCloseTo(12 / 30);
    expect(s.statusIds).toEqual(["burning"]);
  });

  it("戰場 HUD：HP 條上畫「？」（HUD 層一起換、地圖縮小時反向放大），沒有狀態列；完整時沒有「？」", () => {
    const d = buildDrawModel(viewWith(hidden), hero.id).units.find((u) => u.id === hidden.id)!;
    const c = buildUnitSprite(art, new Pulses(), d);
    const mark = c.children.find((k) => k.label === HIDDEN_HP_LABEL);
    expect(mark).toBeDefined();
    expect((mark!.children[1] as Text).text).toBe(HIDDEN_HP_GLYPH);
    expect(c.children.some((k) => k.label === HP_BAR_LABEL)).toBe(true);
    expect(c.children.some((k) => k.label === STATUS_ROW_LABEL)).toBe(false);
    expect(HUD_LABELS).toContain(HIDDEN_HP_LABEL);
    expect(unitMarksOf(c).map((n) => n.label)).toContain(HIDDEN_HP_LABEL);
    expect(HIDDEN_HP_FILL).toBe(0xb4b4c0);
    const s = buildDrawModel(viewWith(shown), hero.id).units.find((u) => u.id === shown.id)!;
    expect(buildUnitSprite(art, new Pulses(), s).children.some((k) => k.label === HIDDEN_HP_LABEL)).toBe(false);
  });

  it("單位卡與滑過資訊卡（UnitInfo）：HP「？ / 最大」、護盾「？」、狀態「？」，說明卡寫原因", () => {
    const bar = barData("hp", hidden);
    expect(bar).toMatchObject({ text: `HP ${UNKNOWN_MARK} / 30`, unknown: true, shield: 0, value: 30, max: 30 });
    expect(bar.hint).toContain(HIDDEN_INFO_HINT);
    const shield = unitChips(hidden).find((c) => c.key === "shield");
    expect(shield?.label).toBe(UNKNOWN_MARK);
    const html = renderToStaticMarkup(createElement(UnitInfo, { unit: hidden, names, heroId: hero.id, skills: {}, view: viewWith(hidden) }));
    expect(html).toContain(`HP ${UNKNOWN_MARK} / 30`);
    expect(html).toContain("stat-bar hp unknown");
    expect(html).toContain('data-testid="status-unknown"');
    expect(html).not.toContain("null");
  });

  it("相鄰或揭露後（完整資訊）：卡片照舊寫數字與狀態，沒有「？」", () => {
    expect(barData("hp", shown).text).toBe("HP 12 / 30");
    expect(unitChips(shown).find((c) => c.key === "shield")?.label).toBe("4");
    const html = renderToStaticMarkup(createElement(UnitInfo, { unit: shown, names, heroId: hero.id, skills: {}, view: viewWith(shown) }));
    expect(html).not.toContain(UNKNOWN_MARK);
    expect(html).not.toContain("status-unknown");
  });

  it("行動順序列：看不到 HP 的條灰色整條、說明寫「HP ？」", () => {
    const html = renderToStaticMarkup(createElement(TurnBar, { view: viewWith(hidden), names, acting: null }));
    expect(html).toContain("turn-chip enemy");
    expect(html).toMatch(/turn-chip enemy[^"]*unknown/);
    expect(html).not.toContain("null");
  });
});
