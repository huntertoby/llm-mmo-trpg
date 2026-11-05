// 6F-17（美術 PM 驗收 6F-16：docs/art/6F-16檢查.md，只換外觀與顯示）：
// 1. 徽章的圓（與數字）不蓋任何狀態圖示：所有寬度 × 朝向 × 徽章組合 × 有沒有「▲N」。
// 2. (b) 角標：格子上有人站時「▲N」縮成角標（數字 8px）；數字和狀態列、徽章分開（6F-16 的規則：左右、上下都至少隔 2px，只在斜對角）；
//    角標不碰鄰格的單位；沒人站的格子照原樣。
// 4. 「+N」加深色的暈（最右欄的「+3」壓在主角圓盤的光圈上）。
// 照收（不改壞）：三角形 40% 上限、HP 條不被蓋、「+N」不超出地圖、數字分開（fix6f15、fix6f16 照舊跑）。
//
// 格子放不下、規則互相衝突的組合（都是 800、1040 寬身上有狀態列的）照最保守的順序排（`heightTag.tagBetter`），
// 列在下面的清單裡鎖住（變多、換人就失敗），原因見 docs/phases/Phase6F-17報告.md「待 PM 決定」。
import { CanvasTextMetrics, Container, Text, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { badgeShapes, FACE, FIRM_HP_FIRST, FIRM_STEPS, numberAt, numbersApart, NUM_SEP_PX, STATUS_BADGE_LINE, STATUS_BADGE_R } from "../render/badgeLayout";
import { HEIGHT_MARK_BG, HEIGHT_MARK_FONT, HEIGHT_TAG_BG, HEIGHT_TAG_FONT_PX, heightMarkBoxes, heightMarkScale, heightTagScale, HP_BAR_TOP } from "../render/heightMark";
import { TAG_MAX_SHIFT, tagShiftOk } from "../render/heightTag";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { circleHitsBox, type Box, type Circle } from "../render/rowLayout";
import { arrowOf, badgeLayoutOf, buildUnitSprite, PLUS_HALO, Pulses, rowModeOf, rowShapesOf, rowVariantsOf, standingMarkOf, unitFaceBox } from "../render/unitSprite";
import { readSources, stripTsComments } from "../test/sourceScan";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const FACINGS: readonly Facing[] = ["east", "west", "north", "south"];
const sizeName = (s: number) => (s === S1600 ? "1600" : s === S1040 ? "1040" : "800");

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

function sprite(u: UnitDraw, s: number, heightDigits = 0, faces: readonly Circle[] = []): Container {
  const c = buildUnitSprite(art, new Pulses(), u, faces, { heightDigits });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const boxHit = (a: Box, b: Box, gap = 0) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
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
/** 狀態列畫出來的形狀：`icons` 圖示，`nums` 「+N」字與「+N」角標（照目前的顯示方式）。 */
function rowOf(c: Container): { all: Box[]; icons: Box[]; nums: Box[] } {
  const row = statusRowOf(c);
  if (row === null) return { all: [], icons: [], nums: [] };
  const v = rowVariantsOf(row)[rowModeOf(row)!];
  const sh = rowShapesOf(row)!;
  const all = [...sh.boxes, ...sh.circles.map((q) => ({ l: q.x - q.r, r: q.x + q.r, t: q.y - q.r, b: q.y + q.r }))];
  const nums = v?.nums ?? [];
  const same = (a: Box, b: Box) => Math.abs(a.l - b.l) + Math.abs(a.r - b.r) + Math.abs(a.t - b.t) + Math.abs(a.b - b.b) < 1e-6;
  return { all, nums, icons: all.filter((b) => !nums.some((n) => same(n, b))) };
}

/** 徽章的組合（6F-15、6F-16 同）＋只有狀態列的。 */
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

describe("6F-17 第 1 項：徽章的圓不蓋任何狀態圖示", () => {
  it("所有寬度 × 朝向 × 徽章組合 × 有沒有「▲N」：徽章的圓與數字都不碰狀態圖示，每顆徽章都放得下；蓋到「+N」的只列在 PLUS_COVERED", { timeout: 300_000 }, () => {
    let checked = 0;
    const plusCovered: string[] = [];
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const hd of [0, 1])
          for (const [name, load] of LOADS) {
            const u = { ...BASE, facing, ...load } as UnitDraw;
            const c = sprite(u, s, hd);
            const row = rowOf(c);
            for (const b of badgesOf(c)) {
              const tag = `${sizeName(s)} ${facing} ${name} ${b.kind}${hd ? " ▲" : ""}`;
              expect(b.lay.firm, `${tag} 放不下`).toBeLessThan(FIRM_STEPS.length);
              for (const r of row.icons) {
                expect(circleHitsBox(b.circle, r), `${tag} 圓`).toBe(false);
                if (b.box !== null) expect(boxHit(b.box, r), `${tag} 數字`).toBe(false);
              }
              if (row.nums.some((r) => circleHitsBox(b.circle, r) || (b.box !== null && boxHit(b.box, r)))) plusCovered.push(tag);
              if (row.icons.length > 0) checked++;
            }
          }
    expect(checked).toBeGreaterThan(30);
    expect(plusCovered).toEqual(PLUS_COVERED);
  });

  it("美術 PM 指定的情境：1040、800 寬朝北、蓄力＋防禦的弓手：防禦圖示整個看得到（6F-16 被蓄力的紫圓擋住）", () => {
    for (const s of [S1040, S800]) {
      const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
      const c = sprite(u, s, 1);
      const [b] = badgesOf(c);
      for (const r of rowOf(c).all) expect(circleHitsBox(b!.circle, r), sizeName(s)).toBe(false);
    }
  });

  it("數字放在自己的圓正中間（最後的手段）也在自己的圓裡", () => {
    const o = numberAt("c");
    expect(Math.hypot(o.x, o.y)).toBeLessThanOrEqual(STATUS_BADGE_R + STATUS_BADGE_LINE / 2);
  });
});

/**
 * 格子放不下的組合（全部是 800、1040 寬身上有狀態列的；1600 寬一律做得到）：
 * - `NUM_CLASH`：角標的數字和徽章的數字不在斜對角（或不到 2px）。
 * - `PLUS_CLASH`：角標的數字和「+N」字不在斜對角（或不到 2px）。
 * - `ROW_CLASH`：角標的底碰到狀態列。
 */
const NUM_CLASH = [
  "1040 east charge+3",
  "1040 north charge+defending",
  "1040 north charge+3",
  "1040 south charge+3",
  "800 east charge+defending",
  "800 east bomb+defending",
  "800 east charge+3",
  "800 west charge+defending",
  "800 west bomb+defending",
  "800 west charge+3",
  "800 north charge+defending",
  "800 north bomb+defending",
  "800 north charge+3",
  "800 south charge+defending",
  "800 south bomb+defending",
  "800 south charge+3",
];
const PLUS_CLASH = [
  "1040 east charge+3",
  "1040 west charge+3",
  "1040 north charge+3",
  "1040 south charge+3",
  "800 east charge+defending",
  "800 east bomb+defending",
  "800 east charge+3",
  "800 west charge+defending",
  "800 west bomb+defending",
  "800 west charge+3",
  "800 north charge+defending",
  "800 north bomb+defending",
  "800 north charge+3",
  "800 south charge+defending",
  "800 south bomb+defending",
  "800 south charge+3",
  "800 south row2",
  "800 south row3",
];
/** 徽章蓋到角標的數字（格子放不下，看不到的東西裡最輕的；見報告）。 */
const DIGIT_COVERED: string[] = [];
/** 角標的「▲」或數字和狀態列互相壓到（格子放不下，看不到的東西裡的一種；見報告）。 */
const INK_ON_ROW: string[] = [];
/** 徽章蓋到「+N」字（狀態圖示一律不蓋）。 */
const PLUS_COVERED: string[] = [];
const ROW_CLASH = [
  "800 south charge+defending",
  "800 south bomb+defending",
  "800 south charge+3",
  "800 south row2",
  "800 south row3",
];

describe("6F-17 第 2 項：(b) 有人站時「▲N」縮成角標", () => {
  it("角標的大小：數字在畫面上剛好 HEIGHT_TAG_FONT_PX（8px），各種寬度一樣；底左右貼緊；沒人站時照原樣（10px 以上、原本的底）", () => {
    expect(HEIGHT_TAG_FONT_PX).toBe(8);
    for (const s of SIZES) {
      expect(HEIGHT_MARK_FONT * heightTagScale(s) * s).toBeCloseTo(HEIGHT_TAG_FONT_PX);
      expect(HEIGHT_MARK_FONT * heightMarkScale(s) * s).toBeGreaterThanOrEqual(10 - 1e-9);
    }
    expect(HEIGHT_TAG_BG.w).toBeLessThan(HEIGHT_MARK_BG.w);
    expect(HEIGHT_TAG_BG.h).toBe(HEIGHT_MARK_BG.h);
    // 底包住「▲」和數字
    const m = heightMarkBoxes(1, 0, 1, 0, HEIGHT_TAG_BG);
    expect(m.box.l).toBeLessThanOrEqual(m.tri.l);
    expect(m.box.r).toBeGreaterThanOrEqual(m.num.r);
  });

  it("所有寬度 × 朝向 × 組合：角標在格子裡、不碰臉、HP 條、朝東西三角形（「▲」和數字），平移不超過 13；放不下的只列在清單裡", { timeout: 300_000 }, () => {
    const num: string[] = [];
    const plus: string[] = [];
    const rowHit: string[] = [];
    const covered: string[] = [];
    const inkOnRow: string[] = [];
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          const c = sprite(u, s, 1);
          const m = standingMarkOf(c, u, s);
          const tag = `${sizeName(s)} ${facing} ${name}`;
          const lim = T / 2 - 1.5 + 1e-6;
          expect(m.box.l >= -lim && m.box.r <= lim && m.box.t >= -lim, `${tag} 格子`).toBe(true);
          expect(boxHit(m.box, unitFaceBox(u)!), `${tag} 臉`).toBe(false);
          expect(m.box.b, `${tag} HP`).toBeLessThanOrEqual(HP_BAR_TOP - 1 + 1e-6);
          if (facing === "east" || facing === "west") expect(boxHit(m.ink, arrowOf(u)!, 0.5 - 1e-6), `${tag} 三角形`).toBe(false);
          const geom = { box: (p: { dx: number; dy: number }) => heightMarkBoxes(m.k, p.dy, 1, p.dx, HEIGHT_TAG_BG).box, ink: () => m.ink, digit: () => m.num };
          expect(tagShiftOk(geom, { dx: m.dx, dy: m.dy }), `${tag} 平移`).toBe(true);
          const sep = NUM_SEP_PX / s;
          const badges = badgesOf(c);
          // 徽章不碰 HP 條；蓋到角標數字的只列在 DIGIT_COVERED
          for (const b of badges) expect(b.lay.firm, `${tag} ${b.kind} HP`).toBeLessThan(FIRM_HP_FIRST);
          if (badges.some((b) => circleHitsBox(b.circle, m.num) || (b.box !== null && boxHit(b.box, m.num)))) covered.push(tag);
          const row = rowOf(c);
          // 狀態列和角標的「▲」、數字互相壓到的只列在 INK_ON_ROW
          if (row.all.some((r) => boxHit(r, m.ink))) inkOnRow.push(tag);
          // 徽章的數字和整個「▲N」（「▲」和數字）分得開（6F-17：蓋到「▲」會讀成「1▲1」）
          if (badges.some((b) => b.kind !== "infused" && !numbersApart(b.box!, m.ink, sep))) num.push(tag);
          if (row.nums.some((r) => !numbersApart(r, m.num, sep))) plus.push(tag);
          if (row.all.some((r) => boxHit(r, m.box))) rowHit.push(tag);
        }
    expect(covered).toEqual(DIGIT_COVERED);
    expect(inkOnRow).toEqual(INK_ON_ROW);
    expect(num).toEqual(NUM_CLASH);
    expect(plus).toEqual(PLUS_CLASH);
    expect(rowHit).toEqual(ROW_CLASH);
    for (const k of [...num, ...plus, ...rowHit, ...covered, ...inkOnRow]) expect(k, "1600 寬一律做得到").not.toMatch(/^1600 /);
  });

  it("角標不碰鄰格的單位：南邊鄰格的頭伸進來時，角標避開", () => {
    // 南邊鄰格（同一欄、下一列）的頭：照 `neighborFaces` 的算法（同高度）
    const head: Circle = { x: FACE.x, y: T + FACE.y, r: FACE.r };
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          const c = sprite(u, s, 1, [head]);
          const m = standingMarkOf(c, u, s);
          expect(circleHitsBox(head, m.box), `${sizeName(s)} ${facing} ${name}`).toBe(false);
        }
  });

  it("平移上限：從左上角或右邊的角量起，13 以內", () => {
    expect(TAG_MAX_SHIFT).toBe(13);
    const k = heightTagScale(S800);
    const geom = { box: (p: { dx: number; dy: number }) => heightMarkBoxes(k, p.dy, 1, p.dx, HEIGHT_TAG_BG).box, ink: () => ({ l: 0, r: 0, t: 0, b: 0 }), digit: () => ({ l: 0, r: 0, t: 0, b: 0 }) };
    expect(tagShiftOk(geom, { dx: 0, dy: 0 })).toBe(true);
    expect(tagShiftOk(geom, { dx: 13, dy: 0 })).toBe(true);
    const k16 = heightTagScale(S1600);
    const g16 = { ...geom, box: (p: { dx: number; dy: number }) => heightMarkBoxes(k16, p.dy, 1, p.dx, HEIGHT_TAG_BG).box };
    expect(tagShiftOk(g16, { dx: 14, dy: 0 })).toBe(false); // 1600 寬：離左右兩個角都超過 13
    expect(tagShiftOk(g16, { dx: T - (HEIGHT_TAG_BG.x * 2 + HEIGHT_TAG_BG.w) * k16, dy: 0 })).toBe(true); // 右邊的角
  });

  it("效能：最擠的情況（800、1040 寬、有狀態列、站在 ▲1 上）一個單位不到 0.5 秒（3 次取最快）", { timeout: 120_000 }, () => {
    let worst = 0;
    for (const s of [S800, S1040])
      for (const facing of FACINGS)
        for (const [, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          let best = Infinity;
          for (let i = 0; i < 3; i++) {
            const t0 = performance.now();
            sprite(u, s, 1);
            best = Math.min(best, performance.now() - t0);
          }
          worst = Math.max(worst, best);
        }
    expect(worst).toBeLessThan(500);
  });

  it("確定性：同一個單位排兩次結果一樣", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    for (const s of SIZES) {
      const a = sprite(u, s, 1);
      const b = sprite(u, s, 1);
      expect(standingMarkOf(a, u, s)).toEqual(standingMarkOf(b, u, s));
      expect(badgesOf(a).map((x) => x.lay)).toEqual(badgesOf(b).map((x) => x.lay));
      const texts = (c: Container) => statusRowOf(c)!.children.filter((n): n is Text => n instanceof Text && n.visible).map((t) => t.text);
      expect(texts(a)).toEqual(texts(b));
    }
  });

  it("接線：繪製器有人站時畫角標（倍率 heightTagScale、底 HEIGHT_TAG_BG），沒人站照原樣", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("const bg = standing === null ? HEIGHT_MARK_BG : HEIGHT_TAG_BG;");
    expect(r).toContain("const kb = standing === null ? k : heightTagScale(s);");
    expect(r).toContain("body.scale.set(kb / k);");
    expect(r).toContain("body.position.y = (chosen ?? heightMarkDrop(kb, face, bg)) / k;");
    const u = sources["render/unitSprite.ts"]!;
    expect(u).toContain("const km = (s: number) => (u.downed ? heightMarkScale(s) : heightTagScale(s));");
    expect(u).toContain(": pickTag({");
  });
});

describe("6F-17 第 4 項：「+N」加深色的暈", () => {
  it("「+N」字（精簡列與只留「+N」）有深色、不偏移的暈；排版的方框不變", () => {
    expect(PLUS_HALO.color).toBe(0x000000);
    expect(PLUS_HALO.distance).toBe(0);
    expect(PLUS_HALO.alpha).toBeGreaterThanOrEqual(0.8);
    const u = { ...BASE, facing: "north" as const, statusIds: ["burning", "slow", "defending"] } as UnitDraw;
    const row = statusRowOf(sprite(u, S1040))!;
    const plus = row.children.filter((n): n is Text => n instanceof Text && n.text.startsWith("+"));
    expect(plus.length).toBeGreaterThan(0);
    for (const t of plus) expect(t.style.dropShadow).toBeTruthy();
  });
});
