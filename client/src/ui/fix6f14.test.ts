// 6F-14（美術 PM 驗收 6F-13：docs/archive/art/6F-13檢查.md，只換外觀與顯示）：
// 1. 朝向三角形一律要避開：狀態列（含「+N」）、蓄力與炸彈的數字都不壓到三角形（四個朝向 × 三種寬度）。
//    精簡列放不下時退到只留「+N」，還是放不下就換到三角形的另一側；800 寬蓄力的「1」先放右下或左下。
// 3、4.（「▲N」不蓋臉、徽章不蓋「▲N」的數字）：6F-18 起有人站的格子不畫「▲N」，拿掉。
// 5. 召喚物操控面板的「待施放」不拆開。
import { CanvasTextMetrics, Container, Graphics, Texture } from "pixi.js";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { badgeShapes, NUM_CORNERS } from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { circleHitsBox, ROW_ARROW_GAP, ROW_EDGE, rowShapes, shapesHitArrow, unitRowLayout, type Box } from "../render/rowLayout";
import { ARROW_TOP_LABEL, arrowOf, badgeLayoutOf, buildUnitSprite, Pulses, rowModeOf, rowShapesOf, rowVariantsOf, ROW_Y_FEET, rowPlusTexts } from "../render/unitSprite";
import { ROW_ICON_FEET } from "../render/rowLayout";
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
