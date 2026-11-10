// HID-1c（美術 PM HID-1b 驗收，`docs/art/HID-1b檢查.md`）：
// 1. 「？」徽章的圓底超出格子下緣，改掛南邊一排的 `under`：地面蓋不到、南邊一排的人蓋得過；
// 2. 掃描會超出格子下緣的 HUD：同因的（精英金菱形）一併掛南邊一排，其他節點都不超出。
import { CanvasTextMetrics, Container, RenderLayer, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { applyMarkScale, BOSS_RING_FRONT_LABEL, HIDDEN_HP_LABEL, HP_BAR_LABEL, SOUTH_ARROW_LABEL, unitMarksOf } from "../render/minMark";
import { RowStack, type RowLayer } from "../render/rowLayers";
import { BODY_LABEL, buildUnitSprite, Pulses } from "../render/unitSprite";

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
const BASE: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: null, charge: null, infused: false, statusIds: [], marker: "", facing: "east", hero: false, active: false };
const HIDDEN: UnitDraw = { ...BASE, hiddenInfo: true };
const find = (c: Container, label: string) => c.children.find((k) => k.label === label) ?? null;

function placed(u: UnitDraw, y: number, n = 3): { rows: RowStack; c: Container } {
  const rows = new RowStack();
  rows.reset(n);
  const c = buildUnitSprite(art, new Pulses(), u);
  rows.row(y).units.addChild(c);
  rows.attachMarks(c);
  return { rows, c };
}

/** 南邊一排畫的順序：`root` 子節點的索引（越大越上層）。 */
const zOf = (r: RowLayer, n: Container) => r.root.children.indexOf(n);

describe("HID-1c：「？」徽章", () => {
  it("掛在南邊一排的 under，仍是單位圖層的子節點（位置、透明度跟著單位）；HP 條留在自己那排的 marks", () => {
    const { rows, c } = placed(HIDDEN, 1);
    const q = find(c, HIDDEN_HP_LABEL)!;
    expect(q.parentRenderLayer).toBe(rows.row(2).under);
    expect(q.parent).toBe(c);
    expect(find(c, HP_BAR_LABEL)!.parentRenderLayer).toBe(rows.row(1).marks);
  });

  it("南邊一排是地磚時徽章在地磚之上；站著人時人在徽章之上（under 在 ground、deco 之上，objects、units 之下）", () => {
    const { rows, c } = placed(HIDDEN, 1);
    const south = rows.row(2);
    const under = zOf(south, south.under);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(south.under);
    expect(under).toBeGreaterThan(zOf(south, south.ground));
    expect(under).toBeGreaterThan(zOf(south, south.deco));
    expect(under).toBeLessThan(zOf(south, south.objects));
    expect(under).toBeLessThan(zOf(south, south.units));
    // 南邊一排整排在自己那排之後畫，所以徽章仍在自己那排的霧之上（HID-1b）
    expect(rows.root.children.indexOf(south.root)).toBeGreaterThan(rows.root.children.indexOf(rows.row(1).root));
  });

  it("最南一排：沒有南邊，留在自己那排的 marks（霧之上）", () => {
    const { rows, c } = placed(HIDDEN, 2);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(rows.row(2).marks);
  });

  it("走路換排時跟著換；走到最南一排回到 marks", () => {
    const { rows, c } = placed(HIDDEN, 0);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(rows.row(1).under);
    rows.row(1).units.addChild(c);
    rows.attachMarks(c);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(rows.row(2).under);
    rows.row(2).units.addChild(c);
    rows.attachMarks(c);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(rows.row(2).marks);
  });

  it("被高台擋住（attachHud）時照舊整組上 hud；回到一般時回到南邊一排的 under", () => {
    const { rows, c } = placed(HIDDEN, 1);
    const hud = new RenderLayer();
    rows.attachHud(c, hud);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(hud);
    rows.attachMarks(c);
    expect(find(c, HIDDEN_HP_LABEL)!.parentRenderLayer).toBe(rows.row(2).under);
  });

  it("不在徽章之下的東西不受影響：身體不掛任何 RenderLayer", () => {
    const { c } = placed(HIDDEN, 1);
    expect(c.children.find((n) => n.label === BODY_LABEL)?.parentRenderLayer ?? null).toBeNull();
  });
});

describe("HID-1c：精英金菱形（同因）", () => {
  it("一般大小的精英有伸進南邊一排的那一份，掛南邊一排的 under；最南一排跟著單位畫", () => {
    const elite: UnitDraw = { ...BASE, elite: true };
    const { rows, c } = placed(elite, 1);
    const front = find(c, BOSS_RING_FRONT_LABEL)!;
    expect(front.parentRenderLayer).toBe(rows.row(2).under);
    expect(front.parent).toBe(c);
    rows.row(2).units.addChild(c);
    rows.attachMarks(c);
    expect(front.parentRenderLayer ?? null).toBeNull();
  });

  it("一般敵人沒有這一份", () => {
    expect(find(buildUnitSprite(art, new Pulses(), BASE), BOSS_RING_FRONT_LABEL)).toBeNull();
  });
});

describe("HID-1c 掃描：會超出格子下緣的節點都有處理", () => {
  const CASES: Record<string, Partial<UnitDraw>> = {
    plain: {},
    north: { facing: "north" },
    west: { facing: "west" },
    south: { facing: "south" },
    hero: { hero: true },
    active: { active: true },
    shield: { shieldRatio: 0.5 },
    marker: { marker: "A" },
    hidden: { hiddenInfo: true },
    elite: { elite: true },
    bomb: { bomb: 12 },
    charge: { charge: 2 },
    badges: { bomb: 2, charge: 2, infused: true },
    statuses: { statusIds: ["burning", "poisoned", "slowed", "stunned"] },
    busy: { statusIds: ["burning", "poisoned", "slowed", "stunned"], bomb: 2, charge: 3 },
    summon: { summon: true, remaining: 3 },
    totem: { summon: true, totem: true, statusIds: ["burning", "poisoned"] },
  };
  const LIMIT = TILE_SIZE / 2 + 0.01;
  /** 超出下緣、已經掛到南邊一排的節點。 */
  const HANDLED: readonly string[] = [SOUTH_ARROW_LABEL, HIDDEN_HP_LABEL, BOSS_RING_FRONT_LABEL];

  for (const scale of [1, 0.7, 0.5]) {
    it(`地圖縮放 ${scale}：HUD 超出下緣的只有朝南三角形、「？」與精英金菱形（都掛南邊一排）`, () => {
      const over: string[] = [];
      for (const [name, draw] of Object.entries(CASES)) {
        const c = buildUnitSprite(art, new Pulses(), { ...BASE, ...draw });
        for (const n of unitMarksOf(c)) applyMarkScale(n, scale, 1);
        for (const n of c.children) {
          const b = n.getBounds();
          if (b.y + b.height <= LIMIT || HANDLED.includes(n.label)) continue;
          // 底圈本體（第一個子節點）：超出的金菱形尖端另有一份掛南邊一排
          if (n === c.children[0] && find(c, BOSS_RING_FRONT_LABEL) !== null) continue;
          over.push(`${name}:${n.label}`);
        }
      }
      expect(over).toEqual([]);
    });
  }
});
