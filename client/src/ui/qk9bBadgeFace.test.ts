// QK-9b 第 1 項（美術 PM QK-9 檢查第 1 題）：徽章避臉改照 Q 版頭部圓（`FACE`：腳底往上 29、半徑 9.3、縮放 1.06）。
// 48px 格裡徽章（圓半徑 11）、HP 條、朝向三角形和較低的 Q 版頭常常擠不下，退的順序（`placeBadgeTier`）：
// 整顆頭（三角形可照 6F-15 第 ①～③ 步放寬）→ 只避開眼睛一帶（`FACE_CORE`）→ C 版的頭（`FACE_LEGACY`，最後手段）。
// 既有規則照舊：整顆在格子裡、HP 條（圓與數字）不碰、數字不碰三角形、圓蓋到三角形 ≤ 40%（朝北照收）。
// QK-9（C 版頭）同一組 216 顆徽章：圓碰到 Q 版頭 151 顆、碰到眼睛 97 顆；QK-9b：圓碰到頭 105 顆（含數字 107）、碰到眼睛 13 顆
// （10 顆朝北＝背面沒有臉；3 顆朝南 1040／800 寬蓄力＋3 個狀態，C 版那一步）。
import { CanvasTextMetrics, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView, type Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { ARROW_MAX_COVER, badgeShapes, coverFraction, EYES, FACE, FACE_TIER } from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, unitMarksOf } from "../render/minMark";
import { BADGE_CELL_PAD, circleHitsBox, circleHitsCircle, type Box, type Circle } from "../render/rowLayout";
import { arrowOf, arrowPolyOf, badgeLayoutOf, buildUnitSprite, hpBoxOf, Pulses } from "../render/unitSprite";

beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const T = 48;
const LIM = T / 2 - BADGE_CELL_PAD;
const SIZES: Array<[string, number]> = [["1600", 1.275], ["1040", 0.796], ["800", 0.646]];
const FACINGS: readonly Facing[] = ["east", "west", "north", "south"];
const view = (): BattleView =>
  ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;
const BASE: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: null, charge: null, infused: false, statusIds: [], marker: "", facing: "south" };
const KIND = { [BOMB_BADGE_LABEL]: "bomb", [CHARGE_BADGE_LABEL]: "charge", [INFUSED_BADGE_LABEL]: "infused" } as const;
const LOADS: Array<[string, Partial<UnitDraw>]> = [
  ["charge", { charge: 1, statusIds: ["charging"] }],
  ["bomb", { bomb: 2, statusIds: ["time_bomb"] }],
  ["infused", { infused: true }],
  ["charge+def", { charge: 1, statusIds: ["defending", "charging"] }],
  ["bomb+def", { bomb: 2, statusIds: ["time_bomb", "defending"] }],
  ["charge+3", { charge: 1, statusIds: ["burning", "slow", "defending", "charging"] }],
  ["all", { bomb: 2, charge: 1, infused: true, statusIds: ["time_bomb", "charging"] }],
];
const boxHit = (a: Box, b: Box) => a.l < b.r - 1e-9 && b.l < a.r - 1e-9 && a.t < b.b - 1e-9 && b.t < a.b - 1e-9;
const shapeHits = (sh: { circle: Circle; box: Box | null }, c: Circle) => circleHitsCircle(sh.circle, c) || (sh.box !== null && circleHitsBox(c, sh.box));
const inCell = (c: Circle, b: Box | null) => {
  const e = 1e-6;
  const ok = c.x - c.r >= -LIM - e && c.x + c.r <= LIM + e && c.y - c.r >= -LIM - e && c.y + c.r <= LIM + e;
  return ok && (b === null || (b.l >= -LIM - e && b.r <= LIM + e && b.t >= -LIM - e && b.b <= LIM + e));
};

describe("QK-9b 第 1 項：徽章避開 Q 版頭部圓", () => {
  it("216 顆徽章（4 朝向 × 3 寬度 × 7 組合 × 有無護盾）：既有規則照舊；眼睛只在朝北（背面）與 3 個朝南的最後手段碰到", { timeout: 120_000 }, () => {
    let n = 0;
    let head = 0;
    const eyes: string[] = [];
    for (const facing of FACINGS)
      for (const [w, s] of SIZES)
        for (const [name, load] of LOADS)
          for (const shield of [0, 0.5]) {
            const u = { ...BASE, facing, shieldRatio: shield, ...load } as UnitDraw;
            const c = buildUnitSprite(art, new Pulses(), u, []);
            for (const k of unitMarksOf(c)) applyMarkScale(k, s, s);
            const hp = hpBoxOf(u)!;
            const arrow = arrowOf(u)!;
            for (const node of unitMarksOf(c).filter((m) => m.label in KIND)) {
              const kind = KIND[node.label as keyof typeof KIND];
              const lay = badgeLayoutOf(node)!;
              const sh = badgeShapes(kind, lay.at, lay.sc, 1, lay.corner);
              const tag = `${w} ${facing} ${name} shield=${shield} ${kind}`;
              n++;
              expect(inCell(sh.circle, sh.box), tag).toBe(true);
              expect(circleHitsBox(sh.circle, hp), `${tag} 圓碰到 HP 條`).toBe(false);
              if (sh.box !== null) expect(boxHit(sh.box, hp), `${tag} 數字碰到 HP 條`).toBe(false);
              if (kind !== "infused") expect(boxHit(sh.box!, arrow), `${tag} 數字碰到三角形`).toBe(false);
              if (facing !== "north") expect(coverFraction(sh.circle, { circle: null, box: arrow, poly: arrowPolyOf(u)! }), tag).toBeLessThanOrEqual(ARROW_MAX_COVER + 1e-9);
              if (shapeHits(sh, FACE)) {
                head++;
                expect(lay.faceCore, `${tag} 碰到頭但沒有回報退到眼睛一帶`).toBe(true);
                expect(lay.tier, tag).toBeGreaterThanOrEqual(FACE_TIER);
              }
              if (EYES.some((e) => shapeHits(sh, e))) {
                eyes.push(`${w} ${facing} ${name} ${shield}`);
                expect(lay.faceLegacy, `${tag} 碰到眼睛只能是 C 版那一步`).toBe(true);
              }
            }
          }
    expect(n).toBe(216);
    expect(head).toBeLessThanOrEqual(107);
    expect(eyes.filter((e) => !e.includes(" north "))).toEqual(["1040 south charge+3 0.5", "800 south charge+3 0", "800 south charge+3 0.5"]);
    expect(eyes.length).toBeLessThanOrEqual(13);
  });

  it("單獨一顆、沒有狀態列與護盾時，完全不碰 Q 版頭（不用退）；例外只有 800 寬朝北（三角形在正中間）", () => {
    const hit: string[] = [];
    for (const facing of FACINGS)
      for (const [w, s] of SIZES)
        for (const [name, load] of LOADS.slice(0, 3)) {
          const c = buildUnitSprite(art, new Pulses(), { ...BASE, facing, ...load } as UnitDraw, []);
          for (const k of unitMarksOf(c)) applyMarkScale(k, s, s);
          for (const node of unitMarksOf(c).filter((m) => m.label in KIND)) {
            const lay = badgeLayoutOf(node)!;
            const sh = badgeShapes(KIND[node.label as keyof typeof KIND], lay.at, lay.sc, 1, lay.corner);
            if (shapeHits(sh, FACE)) hit.push(`${w} ${facing} ${name}`);
          }
        }
    expect(hit).toEqual(["800 north charge", "800 north bomb"]);
  });
});
