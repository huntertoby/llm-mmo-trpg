// 6F-14（美術 PM 驗收 6F-13：docs/archive/art/6F-13檢查.md，只換外觀與顯示）：
// 1. 朝向三角形一律要避開：狀態列（含「+N」）、蓄力與炸彈的數字都不壓到三角形（四個朝向 × 三種寬度）。
//    精簡列放不下時退到只留「+N」，還是放不下就換到三角形的另一側；800 寬蓄力的「1」先放右下或左下。
// 3、4.（「▲N」不蓋臉、徽章不蓋「▲N」的數字）：6F-18 起有人站的格子不畫「▲N」，拿掉。
// 5. 召喚物操控面板的「待施放」不拆開。
import { CanvasTextMetrics, Container, Graphics, Texture } from "pixi.js";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView, type Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { badgeShapes, NUM_CORNERS, ARROW_MAX_COVER, coverFraction, FIRM_STEPS, numberAt, STATUS_BADGE_R, STATUS_BADGE_LINE } from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, statusRowOf, unitMarksOf, INFUSED_BADGE_LABEL } from "../render/minMark";
import { circleHitsBox, ROW_ARROW_GAP, ROW_EDGE, rowShapes, shapesHitArrow, unitRowLayout, type Box, ROW_ICON_FEET, ROW_PLUS_OVERFLOW_MAX, slideClearOver, type RowPlan, mapEdgeOf, NO_EDGE, type MapEdge } from "../render/rowLayout";
import { ARROW_TOP_LABEL, arrowOf, badgeLayoutOf, buildUnitSprite, Pulses, rowModeOf, rowShapesOf, rowVariantsOf, ROW_Y_FEET, rowPlusTexts, arrowPolyOf, hpBoxOf } from "../render/unitSprite";
import { keepWords, splitKeepWords } from "./keepWords";
import { readSources, stripTsComments } from "../test/sourceScan";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const FACINGS: readonly Facing[] = ["east", "west", "north", "south"];

// 測試環境沒有畫布：量字寬改用估計（字級 × 0.62 × 字數 ＋ 描邊；實機量到「+2」9px 粗體加描邊 13.3，估計 13.2）
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
const HERO3: UnitDraw = { ...BASE, statusIds: ["burning", "slow", "defending"] };

function sprite(u: UnitDraw, s: number): Container {
  const c = buildUnitSprite(art, new Pulses(), u, []);
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const arrowTopOf = (c: Container) => c.children.find((n) => n.label === ARROW_TOP_LABEL) ?? null;
const boxHit = (a: Box, b: Box, gap = 0) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
const visibleTexts = (c: Container) =>
  rowPlusTexts(statusRowOf(c)!);

/** 一顆徽章的數字方框（世界座標；灌注沒有數字，回傳水滴的外框）。 */
function badgeNumBox(c: Container, label: string, digits = 1): { circle: { x: number; y: number; r: number }; box: Box | null } | null {
  const n = unitMarksOf(c).find((k) => k.label === label);
  if (n === undefined) return null;
  const lay = badgeLayoutOf(n)!;
  const kind = label === BOMB_BADGE_LABEL ? "bomb" : label === CHARGE_BADGE_LABEL ? "charge" : "infused";
  return badgeShapes(kind, lay.at, lay.sc, digits, lay.corner);
}

describe("6F-14 第 1 項：狀態列避開朝向三角形", () => {
  it("主角 3 個狀態：四個朝向 × 三種寬度，狀態列（圖示、角標、「+N」）都不碰三角形；6F-15：1040、800 寬朝北時「+N」超出格子一點讓開，不另外畫三角形", () => {
    for (const facing of FACINGS)
      for (const s of SIZES) {
        const u = { ...HERO3, facing };
        const c = sprite(u, s);
        const sh = rowShapesOf(statusRowOf(c)!)!;
        const arrow = arrowOf(u)!;
        expect(shapesHitArrow(sh, arrow), `${facing} s=${s} ${JSON.stringify(sh)}`).toBe(false);
        expect(arrowTopOf(c), `${facing} ${s}`).toBeNull(); // 6F-15：拿掉另外畫的那一份三角形
        // 整排在格子裡（左右各留 1px）；朝北的 1040、800 寬（三角形在正中間，兩側都放不下）「+N」最多超出格子 6
        const over = facing === "north" && s !== S1600 ? T / 2 + 6 : ROW_EDGE;
        for (const b of sh.boxes) {
          expect(b.l, `${facing} ${s}`).toBeGreaterThanOrEqual(-over - 1e-6);
          expect(b.r, `${facing} ${s}`).toBeLessThanOrEqual(over + 1e-6);
        }
      }
  });

  it("朝東、3 個狀態：800、1040 寬精簡列放不下 1 個圖示＋「+2」時退到只留「+3」，在三角形左邊；1600 寬照舊 2 個圖示＋角標", () => {
    const u = { ...HERO3, facing: "east" as const };
    const arrow = arrowOf(u)!;
    const c800 = sprite(u, S800);
    expect(visibleTexts(c800)).toEqual(["+3"]);
    for (const b of rowShapesOf(statusRowOf(c800)!)!.boxes) expect(b.r).toBeLessThanOrEqual(arrow.l - ROW_ARROW_GAP + 1e-6);
    // 1040 寬：1 個圖示＋「+2」放得進三角形內側，就不退
    const c1040 = sprite(u, S1040);
    expect(visibleTexts(c1040)).toEqual(["+2"]);
    expect(rowShapesOf(statusRowOf(c1040)!)!.boxes).toHaveLength(2);
    const c1600 = sprite(u, S1600);
    // 6F-19：角標改成膠囊（方框，`cap`）：2 個圖示＋膠囊
    const sh1600 = rowShapesOf(statusRowOf(c1600)!)!;
    expect(sh1600.boxes).toHaveLength(3);
    expect(sh1600.cap).not.toBeNull();
    expect(sh1600.circles).toHaveLength(0);
  });

  it("「+N」在三角形內側放不下時換到另一側（純函式；三角形放在格子左半邊）", () => {
    const k = 10 / (9 * S800);
    const bottom = ROW_Y_FEET + ROW_ICON_FEET / 2;
    const plusW = 13.16;
    const arrow: Box = { l: -8, r: -2, t: 5, b: 15 };
    const lay = unitRowLayout(3, k, false, false, S800, plusW, arrow, { bottom, allW: () => plusW });
    expect(lay.plusOnly).toBe(true);
    const sh = rowShapes(lay, 3, k, bottom, false, plusW);
    expect(shapesHitArrow(sh, arrow)).toBe(false);
    expect(sh.boxes[0]!.l).toBeGreaterThanOrEqual(arrow.r + ROW_ARROW_GAP - 1e-6); // 三角形右邊
    // 沒給 bottom（舊的呼叫）照舊不看三角形的形狀
    expect(unitRowLayout(3, k, false, false, S800, plusW, arrow).plusOnly).toBeUndefined();
  });

  it("讓位的排法（靠右、靠左、只留「+N」）都不碰三角形；朝南時「+N」字往上提，不碰 HP 條上緣露出的三角形", () => {
    for (const facing of FACINGS)
      for (const s of SIZES) {
        const u = { ...BASE, facing, statusIds: ["defending", "slow"], charge: 1 };
        const c = sprite(u, s);
        const row = statusRowOf(c)!;
        const arrow = arrowOf(u)!;
        if (!shapesHitArrow(rowShapesOf(row)!, arrow))
          for (const [m, v] of Object.entries(rowVariantsOf(row))) expect(shapesHitArrow({ boxes: v!.boxes, circles: [] }, arrow), `${facing} ${s} ${m}`).toBe(false);
      }
    const south = sprite({ ...HERO3, facing: "south" }, S800);
    expect(visibleTexts(south)).toEqual(["+2"]);
    expect(shapesHitArrow(rowShapesOf(statusRowOf(south)!)!, arrowOf({ ...HERO3, facing: "south" }))).toBe(false);
  });

  it("蓄力、炸彈的數字：四個朝向 × 三種寬度都不碰三角形；圓也不碰（朝北時三角形在正中間，圓避不開，只讓數字避開）", () => {
    for (const facing of FACINGS)
      for (const s of SIZES)
        for (const [label, u] of [
          [CHARGE_BADGE_LABEL, { ...BASE, facing, statusIds: ["defending", "charging"], charge: 1 }],
          [BOMB_BADGE_LABEL, { ...BASE, facing, statusIds: ["time_bomb", "defending"], bomb: 2 }],
        ] as const) {
          const c = sprite(u as UnitDraw, s);
          const sh = badgeNumBox(c, label)!;
          const arrow = arrowOf(u as UnitDraw)!;
          expect(boxHit(sh.box!, arrow), `${label} ${facing} ${s}`).toBe(false);
          if (facing !== "north") expect(circleHitsBox(sh.circle, arrow), `${label} ${facing} ${s}`).toBe(false);
        }
  });

  it("800 寬盜賊1（蓄力＋防禦、朝西）：「1」在右下，不碰三角形、不碰防禦圖示；數字位置先試右下、左下，正下方最後", () => {
    expect(NUM_CORNERS).toEqual(["br", "bl", "b"]);
    const u = { ...BASE, facing: "west" as const, statusIds: ["defending", "charging"], charge: 1 };
    for (const s of SIZES) {
      const c = sprite(u, s);
      const lay = badgeLayoutOf(unitMarksOf(c).find((k) => k.label === CHARGE_BADGE_LABEL)!)!;
      expect(lay.tier, `s=${s}`).toBe(0);
      expect(lay.corner === "br" || lay.corner === "bl", `s=${s}`).toBe(true);
      const sh = badgeNumBox(c, CHARGE_BADGE_LABEL)!;
      for (const b of rowShapesOf(statusRowOf(c)!)!.boxes) expect(boxHit(sh.box!, b), `s=${s}`).toBe(false);
      expect(boxHit(sh.box!, arrowOf(u)!)).toBe(false);
    }
    expect(badgeLayoutOf(unitMarksOf(sprite(u, S800)).find((k) => k.label === CHARGE_BADGE_LABEL)!)!.corner).toBe("br");
  });

  it("確定性：同樣的輸入得到同樣的排法", () => {
    const run = () => {
      const c = sprite({ ...HERO3, facing: "north", charge: 1, statusIds: [...HERO3.statusIds!, "charging"] }, S800);
      return [rowModeOf(statusRowOf(c)!), JSON.stringify(rowShapesOf(statusRowOf(c)!)), JSON.stringify(badgeLayoutOf(unitMarksOf(c).find((k) => k.label === CHARGE_BADGE_LABEL)!))];
    };
    expect(run()).toEqual(run());
  });
});

// 6F-14 第 3、4 項（「▲N」不蓋到站著的人的臉、徽章不蓋「▲N」的數字）：6F-18 起有人站的格子不畫「▲N」（美術 PM 6F-17 檢查第 2 節），
// 測試拿掉，改由 fix6f18 鎖住「有人站不畫」。

describe("6F-14 第 5 項：「待施放」不拆開", () => {
  it("不可拆的詞包含「待施放」；操控面板的兩段文字都經過 keepWords", () => {
    expect(splitKeepWords("身上已經有待施放的「寒鎖」")).toEqual(["身上已經有", "待施放", "的「寒鎖」"]);
    expect(splitKeepWords("待施放：寒鎖（下回合開始時）")).toEqual(["", "待施放", "：寒鎖（下回合開始時）"]);
    const html = renderToStaticMarkup(createElement("div", null, keepWords("身上已經有待施放的「寒鎖」")));
    expect(html).toContain('<span class="keep-word">待施放</span>');
    const p = sources["ui/SummonPanel.tsx"]!;
    expect(p).toContain("{keepWords(pending)}");
    expect(p).toContain("{keepWords(infuseNo)}");
  });
});

describe("6F-14 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/badgeLayout.ts", "render/rowLayout.ts", "render/heightMark.ts", "render/unitSprite.ts", "render/BattleRenderer.ts", "ui/SummonPanel.tsx", "ui/keepWords.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
    // 畫在狀態列上面的那一份三角形和底圈上的三角形是同一個形狀
    const u = sources["render/unitSprite.ts"]!;
    expect(u).toContain("new Graphics().poly(ringArrow(u.facing, 0, cy, rx, ry, 5))");
    expect(Graphics).toBeDefined();
  });
});

// --- 原 fix6f15.test.ts ---
describe("原 fix6f15.test.ts", () => {
// 6F-15（美術 PM 驗收 6F-14：docs/archive/art/6F-14檢查.md，只換外觀與顯示）：
// 1. 必修：1040 寬蓄力徽章把弓手朝東的三角形整個蓋住 → 徽章改放別處；任何尺寸、朝向，徽章都不能蓋住三角形的大部分。
// 2. 朝北避不開時：拿掉 6F-14 另外重畫的三角形，「+N」超出格子 4～6px 讓開三角形。
// 3. 徽章不蓋到 HP 條：數字型徽章的數字不壓在 HP 條上。
// 6F-18：有人站的格子不畫「▲N」（美術 PM 6F-17 檢查第 2 節），「▲N」的部分拿掉（改由 fix6f18 鎖住）。
// 4. 朝北時蓄力、炸彈的圓蓋到三角形：照收（數字不蓋到）。

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

function sprite(u: UnitDraw, s: number): Container {
  const c = buildUnitSprite(art, new Pulses(), u, []);
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
  it("必修：1040 寬弓手朝東、身上有蓄力：徽章不碰三角形（6F-18：有人站的格子不畫「▲N」）", () => {
    const u = { ...BASE, facing: "east" as const, charge: 1, statusIds: ["charging"] } as UnitDraw;
    const c = sprite(u, S1040);
    const [b] = badgesOf(c);
    const arrow = arrowOf(u)!;
    expect(circleHitsBox(b!.circle, arrow), JSON.stringify(b)).toBe(false);
    expect(boxHit(b!.box!, arrow)).toBe(false);
    expect(badgeLayoutOf(unitMarksOf(c).find((n) => n.label === CHARGE_BADGE_LABEL)!)!.firm).toBe(0);
  });

  it("任何尺寸、任何朝向、有沒有狀態列：徽章的圓都不蓋住三角形的大部分（≤ 40%），數字不碰三角形；朝北照收（美術 PM：圓可以蓋到）", { timeout: 120_000 }, () => {
    let checked = 0;
    for (const facing of FACINGS)
      for (const s of SIZES)
        for (const [name, load] of LOADS) {
            const u = { ...BASE, facing, ...load } as UnitDraw;
            const c = sprite(u, s);
            const arrow = arrowOf(u)!;
            for (const b of badgesOf(c)) {
              const tag = `${name} ${b.label} ${facing} s=${s}`;
              if (b.label !== INFUSED_BADGE_LABEL) expect(boxHit(b.box!, arrow), tag).toBe(false); // 數字
              if (facing !== "north") expect(triCover(b.circle, u), tag).toBeLessThanOrEqual(ARROW_MAX_COVER + 1e-9);
              checked++;
            }
          }
    expect(checked).toBeGreaterThan(100);
    expect(ARROW_MAX_COVER).toBeLessThan(0.5);
  });

  it("三種寬度朝東弓手：三角形完全不被徽章碰到", () => {
    for (const s of SIZES) {
      const u = { ...BASE, facing: "east" as const, charge: 1, statusIds: ["charging"] } as UnitDraw;
      const [b] = badgesOf(sprite(u, s));
      expect(circleHitsBox(b!.circle, arrowOf(u)!), `s=${s}`).toBe(false);
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
    // 三角形先放寬（圓蓋一小部分 → 只讓數字避開），之後才放寬 HP 條（6F-18：「▲N」的 keep／touch 拿掉）
    expect(FIRM_STEPS.map((f) => f.arrow)).toEqual(["full", "partial", "num", "num", "off", "off"]);
    expect(FIRM_STEPS.map((f) => f.hp)).toEqual(["full", "full", "full", "num", "num", "off"]);
  });
});

describe("6F-15 第 2 項：朝北避不開時「+N」超出格子一點，不另外畫三角形", () => {
  it("主角 3 個狀態朝北：1040、800 寬只留「+3」、不碰三角形、超出格子不到 6；沒有另外畫的三角形", () => {
    for (const s of [S1040, S800]) {
      const u = { ...BASE, facing: "north" as const, statusIds: ["burning", "slow", "defending"] } as UnitDraw;
      const c = sprite(u, s);
      const row = statusRowOf(c)!;
      const sh = rowShapesOf(row)!;
      expect(rowPlusTexts(row), `s=${s}`).toEqual(["+3"]);
      expect(shapesHitArrow(sh, arrowOf(u)), `s=${s}`).toBe(false);
      const out = Math.max(0, ...sh.boxes.map((b) => Math.max(-T / 2 - b.l, b.r - T / 2)));
      expect(out, `s=${s}`).toBeLessThanOrEqual(ROW_PLUS_OVERFLOW_MAX + 1e-6);
      if (s === S800) expect(out).toBeGreaterThan(3); // 800 寬約 5.3（畫面約 3.4px）；6F-19 膠囊比字窄，約 3.9
      for (const b of sh.boxes) expect(b.l, `s=${s}`).toBeGreaterThan(arrowOf(u)!.r); // 和 6F-14 一樣放在三角形右邊
      expect(c.children.some((n) => n.label === ARROW_TOP_LABEL)).toBe(false);
    }
  });

  it("slideClearOver：格子裡放得下就不超出；放不下才超出，最多 ROW_PLUS_OVERFLOW_MAX，先放三角形右邊；有字母標記的那一邊不超出", () => {
    const k = 1;
    const bottom = 13;
    const shapesW = (w: number) => (p: RowPlan) => rowShapes(p, 3, k, bottom, false, w);
    const plan: RowPlan = { shift: 0, pitch: 12, moreDx: 0, compact: true, plusOnly: true };
    const arrow: Box = { l: -5, r: 5, t: 0, b: 14 };
    const narrow = slideClearOver(plan, shapesW(10), arrow, -ROW_EDGE)!;
    for (const b of rowShapes(narrow, 3, k, bottom, false, 10).boxes) expect(b.r).toBeLessThanOrEqual(ROW_EDGE + 1e-6);
    const wide = slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE)!;
    const wb = rowShapes(wide, 3, k, bottom, false, 22).boxes[0]!;
    expect(wb.r).toBeGreaterThan(ROW_EDGE); // 先放三角形右邊
    expect(wb.l).toBeGreaterThanOrEqual(arrow.r + 1.5 - 1e-6);
    const lw = rowShapes(slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE, "l")!, 3, k, bottom, false, 22).boxes[0]!;
    expect(lw.r).toBeLessThanOrEqual(arrow.l - 1.5 + 1e-6); // 指定左邊
    expect(lw.l).toBeLessThan(-ROW_EDGE);
    expect(Math.max(-T / 2 - wb.l, wb.r - T / 2)).toBeLessThanOrEqual(ROW_PLUS_OVERFLOW_MAX + 1e-6);
    // 字母標記在左邊：只能往右超出
    const marked = slideClearOver(plan, shapesW(22), arrow, -8)!;
    expect(rowShapes(marked, 3, k, bottom, false, 22).boxes[0]!.l).toBeGreaterThanOrEqual(-8 - 1e-6);
    expect(slideClearOver(plan, shapesW(40), arrow, -ROW_EDGE)).toBeNull();
  });

  it("原始碼：拿掉 6F-14 另外畫三角形的程式", () => {
    const u = sources["render/unitSprite.ts"]!;
    expect(u).not.toContain("arrowTop");
    expect(u).toContain("const row = statusRow(u, turns, opts.edge);"); // 6F-16：地圖邊緣
  });
});

describe("6F-15 第 3 項：徽章不蓋到 HP 條", () => {
  it("任何尺寸、朝向、徽章組合：數字型徽章的數字不壓在 HP 條上，圓也不碰", { timeout: 120_000 }, () => {
    for (const facing of FACINGS)
      for (const s of SIZES)
        for (const [name, load] of LOADS)
          for (const shield of [0, 0.5]) {
            const u = { ...BASE, facing, shieldRatio: shield, ...load } as UnitDraw;
            const c = sprite(u, s);
            const hp = hpBoxOf(u)!;
            for (const b of badgesOf(c)) {
              const tag = `${name} ${b.label} ${facing} s=${s} shield=${shield}`;
              expect(boxHit(b.box!, hp), tag).toBe(false);
              expect(circleHitsBox(b.circle, hp), tag).toBe(false);
            }
          }
  });

  it("800 寬盜賊1 朝北蓄力＋防禦：「1」不壓在 HP 條上（6F-14 剛好蓋在綠黑交界上）", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    const c = sprite(u, S800);
    const [b] = badgesOf(c);
    expect(boxHit(b!.box!, hpBoxOf(u)!)).toBe(false);
    expect(boxHit(b!.box!, arrowOf(u)!)).toBe(false);
  });

});

describe("6F-15：確定性與原始碼", () => {
  it("同樣的輸入得到同樣的排法", () => {
    const run = () => {
      const u = { ...BASE, facing: "west" as const, charge: 1, bomb: 2, statusIds: ["time_bomb", "charging", "defending"] } as UnitDraw;
      const c = sprite(u, S800);
      return JSON.stringify([badgesOf(c), rowShapesOf(statusRowOf(c)!)]);
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
});

// --- 原 fix6f16.test.ts ---
describe("原 fix6f16.test.ts", () => {
// 6F-16（美術 PM 驗收 6F-15：docs/archive/art/6F-15檢查.md，只換外觀與顯示）：
// 1. 徽章的數字在自己的圓外、緊貼著圓（6F-18 照這個位置：美術 PM 6F-17 檢查必修 3）。
// 3. 「+N」不能超出地圖：最右欄的單位「+N」改放在三角形左邊；左右兩邊的地圖邊緣都處理。
// 6F-18：有人站的格子不畫「▲N」（美術 PM 6F-17 檢查第 2 節），第 1 項「和 ▲N 的數字分開」、第 2 項「▲N 不蓋狀態列」拿掉
// （有人站的格子沒有「▲N」，改由 fix6f18 鎖住）。

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

function sprite(u: UnitDraw, s: number, edge: MapEdge = NO_EDGE): Container {
  const c = buildUnitSprite(art, new Pulses(), u, [], { edge });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const KIND = { [BOMB_BADGE_LABEL]: "bomb", [CHARGE_BADGE_LABEL]: "charge", [INFUSED_BADGE_LABEL]: "infused" } as const;

function badgesOf(c: Container) {
  return unitMarksOf(c)
    .filter((n) => n.label in KIND)
    .map((n) => {
      const lay = badgeLayoutOf(n)!;
      const kind = KIND[n.label as keyof typeof KIND];
      return { kind, lay, ...badgeShapes(kind, lay.at, lay.sc, 1, lay.corner) };
    });
}
function rowBoxesOf(c: Container): Box[] {
  const row = statusRowOf(c);
  const sh = row === null ? null : rowShapesOf(row);
  if (sh === null) return [];
  return [...sh.boxes, ...sh.circles.map((q) => ({ l: q.x - q.r, r: q.x + q.r, t: q.y - q.r, b: q.y + q.r }))];
}

/** 徽章的組合（6F-15 同）＋只有狀態列的（第 2 項）。 */
const LOADS: Array<[string, Partial<UnitDraw>]> = [
  ["charge", { charge: 1, statusIds: ["charging"] }],
  ["bomb", { bomb: 2, statusIds: ["time_bomb"] }],
  ["infused", { infused: true }],
  ["charge+defending", { charge: 1, statusIds: ["defending", "charging"] }],
  ["bomb+defending", { bomb: 2, statusIds: ["time_bomb", "defending"] }],
  ["charge+3", { charge: 1, statusIds: ["burning", "slow", "defending", "charging"] }],
  ["all", { bomb: 2, charge: 1, infused: true, statusIds: ["time_bomb", "charging"] }],
];
const ROW_ONLY: Array<[string, Partial<UnitDraw>]> = [
  ["row1", { statusIds: ["defending"] }],
  ["row2", { statusIds: ["defending", "slow"] }],
  ["row3", { statusIds: ["burning", "slow", "defending"] }],
];
const sizeName = (s: number) => (s === S1600 ? "1600" : s === S1040 ? "1040" : "800");

// 6F-17 的 `NUM_CLASH`、`ROW_CLASH`：6F-18 起有人站的格子不畫「▲N」，清單拿掉（fix6f18 鎖住 0）。

describe("6F-16 第 1 項：徽章的數字的位置", () => {
  it("數字一律在自己的圓外、緊貼著圓（數字中心離圓心不超過圓的半徑 ＋ 1，也不在圓心）", () => {
    for (const corner of NUM_CORNERS) {
      // 6F-19：正下方照倍率放（數字方框的上緣貼著圓的外緣，見 fix6f19）
      if (corner === "b") continue;
      const o = numberAt(corner);
      expect(Math.hypot(o.x, o.y), corner).toBeLessThanOrEqual(STATUS_BADGE_R + STATUS_BADGE_LINE / 2 + 1);
      expect(Math.hypot(o.x, o.y), corner).toBeGreaterThan(STATUS_BADGE_R / 2);
    }
  });
});

describe("6F-16 第 3 項：「+N」不超出地圖", () => {
  it("mapEdgeOf：最左欄、最右欄", () => {
    expect(mapEdgeOf({ width: 8 }, { x: 0 })).toEqual({ left: true, right: false });
    expect(mapEdgeOf({ width: 8 }, { x: 7 })).toEqual({ left: false, right: true });
    expect(mapEdgeOf({ width: 8 }, { x: 3 })).toEqual({ left: false, right: false });
  });

  it("最右欄、朝北、3 個狀態：「+3」放在三角形左邊、不超出格子右緣（地圖右緣）；最左欄不超出格子左緣", () => {
    for (const s of [S1040, S800]) {
      const u = { ...BASE, facing: "north" as const, statusIds: ["burning", "slow", "defending"] } as UnitDraw;
      const right = rowShapesOf(statusRowOf(sprite(u, s, { left: false, right: true }))!)!;
      for (const b of right.boxes) {
        expect(b.r, `s=${s}`).toBeLessThanOrEqual(T / 2 + 1e-6);
        expect(b.r, `s=${s}`).toBeLessThanOrEqual(arrowOf(u)!.l); // 三角形左邊
      }
      const left = rowShapesOf(statusRowOf(sprite(u, s, { left: true, right: false }))!)!;
      for (const b of left.boxes) expect(b.l, `s=${s}`).toBeGreaterThanOrEqual(-T / 2 - 1e-6);
      // 不在邊緣時照 6F-15（三角形右邊、超出格子一點）
      const mid = rowShapesOf(statusRowOf(sprite(u, s))!)!;
      for (const b of mid.boxes) expect(b.l, `s=${s}`).toBeGreaterThan(arrowOf(u)!.r);
    }
  });

  it("一般規則：所有寬度 × 朝向 × 狀態數 × 站在最左、最右欄：狀態列不超出地圖那一邊", { timeout: 120_000 }, () => {
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...ROW_ONLY, ...LOADS])
          for (const edge of [{ left: true, right: false }, { left: false, right: true }]) {
            const u = { ...BASE, facing, ...load } as UnitDraw;
            const c = sprite(u, s, edge);
            for (const b of rowBoxesOf(c)) {
              const tag = `${sizeName(s)} ${facing} ${name} ${JSON.stringify(edge)}`;
              if (edge.left) expect(b.l, tag).toBeGreaterThanOrEqual(-T / 2 - 1e-6);
              if (edge.right) expect(b.r, tag).toBeLessThanOrEqual(T / 2 + 1e-6);
            }
          }
  });

  it("slideClearOver：最右欄先放三角形左邊、最左欄先放右邊，都不超出地圖", () => {
    const shapesW = (w: number) => (p: RowPlan) => rowShapes(p, 3, 1, 13, false, w);
    const plan: RowPlan = { shift: 0, pitch: 12, moreDx: 0, compact: true, plusOnly: true };
    const arrow: Box = { l: -5, r: 5, t: 0, b: 14 };
    const r = rowShapes(slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE, "r", { left: false, right: true })!, 3, 1, 13, false, 22).boxes[0]!;
    expect(r.r).toBeLessThanOrEqual(arrow.l - 1.5 + 1e-6);
    expect(r.l).toBeLessThan(-ROW_EDGE);
    const l = rowShapes(slideClearOver(plan, shapesW(22), arrow, -ROW_EDGE, "l", { left: true, right: false })!, 3, 1, 13, false, 22).boxes[0]!;
    expect(l.l).toBeGreaterThanOrEqual(arrow.r + 1.5 - 1e-6);
  });

  it("接線：繪製器照單位所在的欄傳地圖邊緣（重畫、轉身）", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("edge: mapEdgeOf(model, u)");
    expect(r).toContain("edge: this.model === null ? NO_EDGE : mapEdgeOf(this.model, next)");
    const u = sources["render/unitSprite.ts"]!;
    expect(u).toContain("const row = statusRow(u, turns, opts.edge);");
    expect(u).toContain('slideClearOver(p, shapesOf, arrow, rowLeft, m === "plus-l" ? "l" : "r", edge)');
  });
});

describe("6F-16 確定性", () => {
  it("同一個單位排兩次結果一樣", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    const a = sprite(u, S800);
    const b = sprite(u, S800);
    expect(badgesOf(a).map((x) => x.lay)).toEqual(badgesOf(b).map((x) => x.lay));
    const texts = (c: Container) => rowPlusTexts(statusRowOf(c)!);
    expect(texts(a)).toEqual(texts(b));
  });
});
});
