// 6F-21（美術 PM 6F-14 檢查第 3 節）：朝南時朝向三角形幾乎整個被 HP 條蓋住（舊畫法）→ 移到 HP 條下面；
// 「+N」不再為看不到的三角形讓位（6F-14 的 `plusLift` 拿掉）；其他三個朝向照舊。
import { CanvasTextMetrics, Container, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView, type Facing } from "../api/types";
import { ringArrow } from "../battle/facing";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { applyMarkScale, statusRowOf, unitMarksOf } from "../render/minMark";
import { type Box, plusCapsuleY, ROW_ICON_FEET, ROW_PLUS_OVERFLOW_MAX, rowShapes, shapesHitArrow, unitRowLayout } from "../render/rowLayout";
import { arrowOf, arrowPolyOf, buildUnitSprite, FEET, facingArrowPoly, hpBoxOf, Pulses, rowModeOf, rowShapesOf, ROW_Y_FEET, SOUTH_ARROW_GAP } from "../render/unitSprite";
import { readSources, stripTsComments } from "../test/sourceScan";

const T = 48;
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const OTHERS: readonly Facing[] = ["east", "west", "north"];

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

function sprite(u: UnitDraw, s: number): Container {
  const c = buildUnitSprite(art, new Pulses(), u, []);
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const overlap = (a: Box, b: Box) => a.l < b.r - 1e-9 && b.l < a.r - 1e-9 && a.t < b.b - 1e-9 && b.t < a.b - 1e-9;
const original = (f: Facing) => ringArrow(f, 0, FEET - 1, T * 0.36, T * 0.15, 5);

describe("6F-21：朝南的三角形在 HP 條外面", () => {
  it("有 HP 條（含護盾條）時：三角形整個在 HP 條下緣之下、不重疊，空隙 SOUTH_ARROW_GAP；超出格子下緣 ≤ 6", () => {
    for (const shieldRatio of [0, 0.5]) {
      const u = { ...BASE, facing: "south" as const, shieldRatio };
      const hp = hpBoxOf(u)!;
      const a = arrowOf(u)!;
      expect(overlap(a, hp)).toBe(false);
      expect(a.t).toBeCloseTo(hp.b + SOUTH_ARROW_GAP, 6); // 外框含描邊（0.5）
      expect(a.b - T / 2).toBeLessThanOrEqual(ROW_PLUS_OVERFLOW_MAX + 1e-9);
      expect(a.b - T / 2).toBeGreaterThan(0); // 確實在格子下緣外一點（說明用）
    }
  });

  it("只移位置、不改形狀：和原本的三角形只差一個垂直平移，尖端朝下、左右位置不變", () => {
    const p = facingArrowPoly({ ...BASE, facing: "south" });
    const o = original("south");
    const dy = p[1]! - o[1]!;
    expect(dy).toBeGreaterThan(0);
    p.forEach((v, i) => expect(v, `${i}`).toBeCloseTo(i % 2 === 0 ? o[i]! : o[i]! + dy, 9));
    expect(p[1]!).toBeGreaterThan(Math.max(p[3]!, p[5]!)); // 尖端（第一組）在最下面
    expect(arrowPolyOf({ ...BASE, facing: "south" })).toEqual(p);
  });

  it("沒有 HP 條（noBar）時朝南照原位；倒下照舊不畫", () => {
    expect(facingArrowPoly({ ...BASE, facing: "south", noBar: true })).toEqual(original("south"));
    expect(arrowOf({ ...BASE, facing: "south", downed: true })).toBeNull();
  });

  it("其他三個朝向不變（和 6F-20 的位置一樣）", () => {
    for (const f of OTHERS) {
      expect(facingArrowPoly({ ...BASE, facing: f }), f).toEqual(original(f));
      expect(arrowPolyOf({ ...BASE, facing: f }), f).toEqual(original(f));
    }
  });
});

describe("6F-21：「+N」不再為朝南的三角形讓位", () => {
  it("純函式：朝南的三角形傳進去和不傳，排法一樣（1～4 個狀態 × 三種寬度）", () => {
    const arrow = arrowOf({ ...BASE, facing: "south" })!;
    const bottom = ROW_Y_FEET + ROW_ICON_FEET / 2;
    for (const s of SIZES)
      for (const n of [1, 2, 3, 4]) {
        const k = 10 / (9 * s);
        const plusW = 13.16;
        const shown = Math.min(n, 2);
        const extra = n > 2;
        const opts = { bottom, allW: () => plusW, total: n };
        const withArrow = unitRowLayout(shown, k, extra, false, s, plusW, arrow, opts);
        expect(withArrow, `s=${s} n=${n}`).toEqual(unitRowLayout(shown, k, extra, false, s, plusW, null, opts));
        expect(shapesHitArrow(rowShapes(withArrow, shown, k, bottom, extra, plusW), arrow)).toBe(false);
      }
  });

  it("實際畫出來：朝南 1～4 個狀態 × 三種寬度（沒有徽章）都是原本的排法，狀態列不碰三角形、也不碰 HP 條", () => {
    const ids = ["burning", "slow", "defending", "poisoned"];
    for (const s of SIZES)
      for (const n of [1, 2, 3, 4]) {
        const u = { ...BASE, facing: "south" as const, statusIds: ids.slice(0, n) };
        const row = statusRowOf(sprite(u, s))!;
        expect(rowModeOf(row), `s=${s} n=${n}`).toBe("normal");
        const sh = rowShapesOf(row)!;
        expect(shapesHitArrow(sh, arrowOf(u)!)).toBe(false);
        for (const b of sh.boxes) expect(overlap(b, hpBoxOf(u)!), `s=${s} n=${n}`).toBe(false);
      }
  });

  it("「+N」膠囊的位置沒有往上提的選項（plusCapsuleY 不收參數；原始碼沒有 plusLift）", () => {
    expect(plusCapsuleY.length).toBe(0);
    const src = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
    for (const f of ["render/rowLayout.ts", "render/unitSprite.ts"]) {
      expect(src[f], f).not.toMatch(/plusLift|ROW_PLUS_LIFT/);
    }
    expect(src["render/unitSprite.ts"]).toContain("new Graphics().poly(facingArrowPoly(u))");
  });
});
