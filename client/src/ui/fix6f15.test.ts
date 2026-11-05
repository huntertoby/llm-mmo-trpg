// 6F-15（美術 PM 驗收 6F-14：docs/art/6F-14檢查.md，只換外觀與顯示）：
// 1. 必修：1040 寬蓄力徽章把弓手朝東的三角形整個蓋住 → 標記移到下緣（或徽章改放左上）；任何尺寸、朝向，徽章都不能蓋住三角形的大部分。
// 2. 朝北避不開時：拿掉 6F-14 另外重畫的三角形，「+N」超出格子 4～6px 讓開三角形。
// 3. 徽章和「▲N」都不蓋到 HP 條：移到下緣的「▲N」放在 HP 條上方；數字型徽章的數字不壓在 HP 條上。
// 4. 朝北時蓄力、炸彈的圓蓋到三角形：照收（數字不蓋到）。
import { CanvasTextMetrics, Container, Text, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { ARROW_MAX_COVER, badgeShapes, coverFraction, FIRM_STEPS, layoutBadges, type BadgeReq } from "../render/badgeLayout";
import { heightMarkBoxes, heightMarkCandidates, heightMarkDrop, heightMarkScale, HP_BAR_TOP } from "../render/heightMark";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { circleHitsBox, ROW_EDGE, ROW_PLUS_OVERFLOW_MAX, rowShapes, shapesHitArrow, slideClearOver, type Box, type RowPlan } from "../render/rowLayout";
import { ARROW_TOP_LABEL, arrowOf, arrowPolyOf, badgeLayoutOf, buildUnitSprite, heightMarkDropOf, heightMarkShiftOf, hpBoxOf, Pulses, rowShapesOf, unitFaceBox } from "../render/unitSprite";
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

function sprite(u: UnitDraw, s: number, heightDigits = 0): Container {
  const c = buildUnitSprite(art, new Pulses(), u, [], { heightDigits });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const boxHit = (a: Box, b: Box, gap = 0) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
const KIND = { [BOMB_BADGE_LABEL]: "bomb", [CHARGE_BADGE_LABEL]: "charge", [INFUSED_BADGE_LABEL]: "infused" } as const;

/** 單位身上每一顆徽章畫出來的形狀（圓與數字的方框；灌注是水滴的外框）。 */
function badgesOf(c: Container): Array<{ label: string; circle: { x: number; y: number; r: number }; box: Box | null }> {
  return unitMarksOf(c)
    .filter((n) => n.label in KIND)
    .map((n) => {
      const lay = badgeLayoutOf(n)!;
      return { label: n.label, ...badgeShapes(KIND[n.label as keyof typeof KIND], lay.at, lay.sc, 1, lay.corner) };
    });
}
/** 站在「▲1」上時標記實際畫的位置（單位決定的，沒有就是只讓開臉的位置）。 */
function markOf(c: Container, u: UnitDraw, s: number) {
  const k = heightMarkScale(s);
  return heightMarkBoxes(k, heightMarkDropOf(c, s) ?? heightMarkDrop(k, unitFaceBox(u)), 1, heightMarkShiftOf(c, s) ?? 0);
}
const triCover = (circle: { x: number; y: number; r: number }, u: UnitDraw) => coverFraction(circle, { circle: null, box: arrowOf(u)!, poly: arrowPolyOf(u)! });

/** 徽章的組合：只有徽章、和狀態列一起（盜賊1 蓄力＋防禦）、三種一起。 */
const LOADS: Array<[string, Partial<UnitDraw>]> = [
  ["charge", { charge: 1, statusIds: ["charging"] }],
  ["bomb", { bomb: 2, statusIds: ["time_bomb"] }],
  ["infused", { infused: true }],
  ["charge+defending", { charge: 1, statusIds: ["defending", "charging"] }],
  ["bomb+defending", { bomb: 2, statusIds: ["time_bomb", "defending"] }],
  ["charge+3", { charge: 1, statusIds: ["burning", "slow", "defending", "charging"] }],
  ["all", { bomb: 2, charge: 1, infused: true, statusIds: ["time_bomb", "charging"] }],
];

describe("6F-15 第 1 項：徽章不蓋住朝向三角形", () => {
  it("必修：1040 寬弓手朝東、身上有蓄力、站在 ▲1 上：徽章不碰三角形，標記移到下緣（HP 條上方），兩個數字都看得到", () => {
    const u = { ...BASE, facing: "east" as const, charge: 1, statusIds: ["charging"] } as UnitDraw;
    const c = sprite(u, S1040, 1);
    const [b] = badgesOf(c);
    const arrow = arrowOf(u)!;
    expect(circleHitsBox(b!.circle, arrow), JSON.stringify(b)).toBe(false);
    expect(boxHit(b!.box!, arrow)).toBe(false);
    expect(badgeLayoutOf(unitMarksOf(c).find((n) => n.label === CHARGE_BADGE_LABEL)!)!.firm).toBe(0);
    const m = markOf(c, u, S1040);
    expect(heightMarkDropOf(c, S1040)!).toBeGreaterThan(heightMarkDrop(heightMarkScale(S1040), unitFaceBox(u)) + 1); // 移到下緣
    expect(m.box.b).toBeLessThanOrEqual(HP_BAR_TOP - 1 + 1e-6);
    expect(circleHitsBox(b!.circle, m.num) || boxHit(b!.box!, m.num)).toBe(false);
    // 6F-14 的排法（只看數字有沒有被蓋到）在這裡會把三角形整個蓋住：原位的標記數字擋住了左上
    const k = heightMarkScale(S1040);
    const req: BadgeReq = { kind: "charge", at: { x: -0.37, y: -0.2 }, digits: 1 };
    const [old] = layoutBadges([req], S1040, [], [], { firmBoxes: [arrow], keepBoxes: [heightMarkBoxes(k, heightMarkDrop(k, unitFaceBox(u)), 1).num] });
    expect(triCover({ ...old!.at, r: 11 * old!.sc.ki }, u)).toBeGreaterThan(0.5);
  });

  it("任何尺寸、任何朝向、有沒有「▲N」、有沒有狀態列：徽章的圓都不蓋住三角形的大部分（≤ 40%），數字不碰三角形；朝北照收（美術 PM：圓可以蓋到）", { timeout: 120_000 }, () => {
    let checked = 0;
    for (const facing of FACINGS)
      for (const s of SIZES)
        for (const hd of [0, 1])
          for (const [name, load] of LOADS) {
            const u = { ...BASE, facing, ...load } as UnitDraw;
            const c = sprite(u, s, hd);
            const arrow = arrowOf(u)!;
            for (const b of badgesOf(c)) {
              const tag = `${name} ${b.label} ${facing} s=${s} h=${hd}`;
              if (b.label !== INFUSED_BADGE_LABEL) expect(boxHit(b.box!, arrow), tag).toBe(false); // 數字
              if (facing !== "north") expect(triCover(b.circle, u), tag).toBeLessThanOrEqual(ARROW_MAX_COVER + 1e-9);
              checked++;
            }
          }
    expect(checked).toBeGreaterThan(200);
    expect(ARROW_MAX_COVER).toBeLessThan(0.5);
  });

  it("三種寬度朝東弓手（有／沒有 ▲1）：三角形完全不被徽章碰到", () => {
    for (const s of SIZES)
      for (const hd of [0, 1]) {
        const u = { ...BASE, facing: "east" as const, charge: 1, statusIds: ["charging"] } as UnitDraw;
        const [b] = badgesOf(sprite(u, s, hd));
        expect(circleHitsBox(b!.circle, arrowOf(u)!), `s=${s} h=${hd}`).toBe(false);
      }
  });

  it("圓蓋到三角形多少：取樣點、確定性；放寬的順序先讓圓蓋一小部分，才只讓數字避開", () => {
    const u = { ...BASE, facing: "east" as const };
    const a = arrowOf(u)!;
    const cx = (a.l + a.r) / 2;
    const cy = (a.t + a.b) / 2;
    expect(triCover({ x: cx, y: cy, r: 30 }, u)).toBe(1);
    expect(triCover({ x: cx - 40, y: cy, r: 5 }, u)).toBe(0);
    const half = triCover({ x: a.l - 11 + (a.r - a.l) / 2, y: cy, r: 11 }, u);
    expect(half).toBeGreaterThan(0);
    expect(half).toBeLessThan(1);
    expect(triCover({ x: 1, y: 2, r: 11 }, u)).toBe(triCover({ x: 1, y: 2, r: 11 }, u));
    expect(FIRM_STEPS.map((f) => f.arrow)).toEqual(["full", "partial", "num", "num", "off", "off", "off"]);
    expect(FIRM_STEPS.map((f) => f.keep).indexOf("off")).toBe(FIRM_STEPS.length - 1);
  });
});

describe("6F-15 第 2 項：朝北避不開時「+N」超出格子一點，不另外畫三角形", () => {
  it("主角 3 個狀態朝北：1040、800 寬只留「+3」、不碰三角形、超出格子不到 6；沒有另外畫的三角形", () => {
    for (const s of [S1040, S800]) {
      const u = { ...BASE, facing: "north" as const, statusIds: ["burning", "slow", "defending"] } as UnitDraw;
      const c = sprite(u, s);
      const row = statusRowOf(c)!;
      const sh = rowShapesOf(row)!;
      expect(row.children.filter((n): n is Text => n instanceof Text && n.visible).map((t) => t.text), `s=${s}`).toEqual(["+3"]);
      expect(shapesHitArrow(sh, arrowOf(u)), `s=${s}`).toBe(false);
      const out = Math.max(0, ...sh.boxes.map((b) => Math.max(-T / 2 - b.l, b.r - T / 2)));
      expect(out, `s=${s}`).toBeLessThanOrEqual(ROW_PLUS_OVERFLOW_MAX + 1e-6);
      if (s === S800) expect(out).toBeGreaterThan(4); // 800 寬約 5.3（畫面約 3.4px）
      expect(c.children.some((n) => n.label === ARROW_TOP_LABEL)).toBe(false);
    }
  });

  it("slideClearOver：格子裡放得下就不超出；放不下才超出，最多 ROW_PLUS_OVERFLOW_MAX；有字母標記的那一邊不超出", () => {
    const k = 1;
    const bottom = 13;
    const shapesW = (w: number) => (p: RowPlan) => rowShapes(p, 3, k, bottom, false, w);
    const plan: RowPlan = { shift: 0, pitch: 12, moreDx: 0, compact: true, plusOnly: true };
    const arrow: Box = { l: -5, r: 5, t: 0, b: 14 };
    const narrow = slideClearOver(plan, shapesW(10), arrow, -ROW_EDGE)!;
    for (const b of rowShapes(narrow, 3, k, bottom, false, 10).boxes) expect(b.r).toBeLessThanOrEqual(ROW_EDGE + 1e-6);
    const wide = slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE)!;
    const wb = rowShapes(wide, 3, k, bottom, false, 22).boxes[0]!;
    expect(wb.l < -ROW_EDGE || wb.r > ROW_EDGE).toBe(true);
    expect(Math.max(-T / 2 - wb.l, wb.r - T / 2)).toBeLessThanOrEqual(ROW_PLUS_OVERFLOW_MAX + 1e-6);
    // 字母標記在左邊：只能往右超出
    const marked = slideClearOver(plan, shapesW(22), arrow, -8)!;
    expect(rowShapes(marked, 3, k, bottom, false, 22).boxes[0]!.l).toBeGreaterThanOrEqual(-8 - 1e-6);
    expect(slideClearOver(plan, shapesW(40), arrow, -ROW_EDGE)).toBeNull();
  });

  it("原始碼：拿掉 6F-14 另外畫三角形的程式", () => {
    const u = sources["render/unitSprite.ts"]!;
    expect(u).not.toContain("arrowTop");
    expect(u).toContain("const row = statusRow(u, turns);");
  });
});

describe("6F-15 第 3 項：徽章和「▲N」都不蓋到 HP 條", () => {
  it("任何尺寸、朝向、徽章組合、有沒有「▲N」：數字型徽章的數字不壓在 HP 條上，圓也不碰；「▲N」不碰 HP 條", { timeout: 120_000 }, () => {
    for (const facing of FACINGS)
      for (const s of SIZES)
        for (const hd of [0, 1])
          for (const [name, load] of LOADS)
            for (const shield of [0, 0.5]) {
              const u = { ...BASE, facing, shieldRatio: shield, ...load } as UnitDraw;
              const c = sprite(u, s, hd);
              const hp = hpBoxOf(u)!;
              for (const b of badgesOf(c)) {
                const tag = `${name} ${b.label} ${facing} s=${s} h=${hd} shield=${shield}`;
                expect(boxHit(b.box!, hp), tag).toBe(false);
                expect(circleHitsBox(b.circle, hp), tag).toBe(false);
              }
              if (hd > 0) expect(boxHit(markOf(c, u, s).box, hp), `${name} mark ${facing} s=${s} shield=${shield}`).toBe(false);
            }
  });

  it("800 寬移到下緣的「▲N」在 HP 條上方、圓盤下緣；HP 條整條露出來（右邊 2/3 以上）", () => {
    const u = { ...BASE, facing: "east" as const, charge: 1, statusIds: ["charging"] } as UnitDraw;
    const c = sprite(u, S800, 1);
    const m = markOf(c, u, S800);
    const k = heightMarkScale(S800);
    expect(heightMarkDropOf(c, S800)!).toBeGreaterThan(heightMarkDrop(k, unitFaceBox(u)) + 1);
    expect(m.box.b).toBeCloseTo(HP_BAR_TOP - 1);
    // 圓盤下緣（底圈 cy ＝ FEET − 1、半徑 T × 0.15）
    expect(Math.abs(m.box.b - (T * 0.23 - 1 + T * 0.15))).toBeLessThan(1.5);
    const [b] = badgesOf(c);
    expect(circleHitsBox(b!.circle, m.num) || boxHit(b!.box!, m.num)).toBe(false);
    expect(boxHit(m.box, arrowOf(u)!, 0.5 - 1e-6)).toBe(false);
  });

  it("800 寬盜賊1 朝北蓄力＋防禦：「1」不壓在 HP 條上（6F-14 剛好蓋在綠黑交界上）", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    const c = sprite(u, S800);
    const [b] = badgesOf(c);
    expect(boxHit(b!.box!, hpBoxOf(u)!)).toBe(false);
    expect(boxHit(b!.box!, arrowOf(u)!)).toBe(false);
  });

  it("標記的位置候選：原位、下緣（HP 條上方）、下緣左右平移；下緣的不碰朝東、西的三角形與臉，在格子裡", () => {
    for (const facing of ["east", "west"] as const)
      for (const s of SIZES) {
        const u = { ...BASE, facing };
        const k = heightMarkScale(s);
        const face = unitFaceBox(u);
        const cands = heightMarkCandidates(k, face, arrowOf(u), hpBoxOf(u)!.t);
        expect(cands[0]).toEqual({ dx: 0, dy: heightMarkDrop(k, face) });
        for (const p of cands.slice(1)) {
          const m = heightMarkBoxes(k, p.dy, 1, p.dx);
          expect(m.box.b).toBeCloseTo(HP_BAR_TOP - 1);
          expect(boxHit(m.box, arrowOf(u)!, 0.5 - 1e-6), `${facing} ${s} ${p.dx}`).toBe(false);
          expect(boxHit(m.box, face!), `${facing} ${s} ${p.dx}`).toBe(false);
          expect(m.box.l).toBeGreaterThanOrEqual(-T / 2 + 1.5 - 1e-6);
          expect(m.box.r).toBeLessThanOrEqual(T / 2 - 1.5 + 1e-6);
        }
        // 離原位近的先
        const dxs = cands.slice(1).map((p) => Math.abs(p.dx));
        expect([...dxs].sort((a, b) => a - b)).toEqual(dxs);
      }
  });

  it("接線：繪製器照單位決定的位置畫標記（往下、左右平移）", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("body.position.x = (sprite === undefined ? 0 : (heightMarkShiftOf(sprite, s) ?? 0)) / k;");
    expect(r).toContain("body.position.y = (chosen ?? heightMarkDrop(k, face)) / k;");
  });
});

describe("6F-15：確定性與原始碼", () => {
  it("同樣的輸入得到同樣的排法", () => {
    const run = () => {
      const u = { ...BASE, facing: "west" as const, charge: 1, bomb: 2, statusIds: ["time_bomb", "charging", "defending"] } as UnitDraw;
      const c = sprite(u, S800, 1);
      return JSON.stringify([badgesOf(c), heightMarkDropOf(c, S800), heightMarkShiftOf(c, S800), rowShapesOf(statusRowOf(c)!)]);
    };
    expect(run()).toEqual(run());
  });

  it("這次動到的檔案不用 Math.random、不用原生 title=", () => {
    for (const f of ["render/badgeLayout.ts", "render/rowLayout.ts", "render/heightMark.ts", "render/unitSprite.ts", "render/BattleRenderer.ts"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
