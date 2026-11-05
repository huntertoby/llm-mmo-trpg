// 6F-13（美術 PM 驗收 6F-12：docs/art/6F-12檢查.md，只換外觀與顯示）：
// 1. 灌注徽章：「灌」字 12px 還是讀不出來 → 改成程式繪製的小水滴，畫面上至少高 10px。
// 2. 800 寬擁擠的召喚物：有灌注時狀態列只留「+N」；灌注不蓋「+N」；回合數徽章和灌注分在左右，身體至少露出一半。
// 3. 跨格避臉：南邊（含站在高處）的單位伸進這一格的臉也要避開；避不開時徽章畫在那個單位的下層；徽章畫在「▲N」之上。
// 4. 召喚物操控面板顯示技能名稱，不顯示內容 ID。
// 5. 800 寬右上整欄停在縮放列上面。
// 6. 蓄力的數字不蓋狀態列的圖示（數字可換到正下方、狀態列可讓位或只留「+N」）。
// 7. 狀態列（含「+N」）不貼到朝向三角形。
import { CanvasTextMetrics, Container, Graphics, Text, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, UnitView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { infusedSkillName, infuseBlocked, pendingInfusionText } from "../battle/summonControl";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import {
  badgeScales,
  badgeShapes,
  chooseRowMode,
  FACE,
  INFUSED_DROP_H,
  layoutBadges,
  MIN_INFUSED_ICON_PX,
  neighborFaces,
  type BadgeReq,
} from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, HEIGHT_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, SUMMON_BADGE_LABEL, unitMarksOf } from "../render/minMark";
import { RowStack, UNIT_MARK_LABELS } from "../render/rowLayers";
import { arrowLimits, BADGE_CELL_PAD, circleHitsBox, circleHitsCircle, ROW_ARROW_GAP, ROW_EDGE, type Box, type Circle } from "../render/rowLayout";
import { infusedBadge, statusBadges } from "../render/unitLook";
import { arrowOf, badgeLayoutOf, buildUnitSprite, FEET, Pulses, rowModeOf, rowShapesOf } from "../render/unitSprite";
import { readFile, readSources, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const LIM = T / 2 - BADGE_CELL_PAD;

// 測試環境沒有畫布：量字寬改用估計（字級 × 0.62 × 字數 ＋ 描邊）
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
const SUMMON: UnitDraw = { ...BASE, summon: true, remaining: 3, totem: false };

/** 建一個單位圖層，照繪製器的順序套用縮放（`unitMarksOf`）。 */
function sprite(u: UnitDraw, s: number, faces: Circle[] = []): Container {
  const c = buildUnitSprite(art, new Pulses(), u, faces);
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
const child = (c: Container, label: string) => unitMarksOf(c).find((n) => n.label === label) ?? null;

function inCell(c: Circle, b: Box | null): boolean {
  const e = 1e-6;
  const ok = c.x - c.r >= -LIM - e && c.x + c.r <= LIM + e && c.y - c.r >= -LIM - e && c.y + c.r <= LIM + e;
  return ok && (b === null || (b.l >= -LIM - e && b.r <= LIM + e && b.t >= -LIM - e && b.b <= LIM + e));
}
const boxHit = (a: Box, b: Box) => a.l < b.r - 1e-9 && b.l < a.r - 1e-9 && a.t < b.b - 1e-9 && b.t < a.b - 1e-9;
const shapeHitsBox = (sh: { circle: Circle; box: Box | null }, b: Box) => circleHitsBox(sh.circle, b) || (sh.box !== null && boxHit(sh.box, b));
const shapeHitsCircle = (sh: { circle: Circle; box: Box | null }, c: Circle) => circleHitsCircle(sh.circle, c) || (sh.box !== null && circleHitsBox(c, sh.box));

/**
 * 狀態列目前畫出來的形狀（世界座標，`rowShapesOf`）：圖示的方框、「+N」（字或角標）的方框，與看得到的字。
 * 測試環境沒有狀態圖示的貼圖，圖示的位置只看排法算出來的形狀。
 */
function rowBoxesOf(c: Container): { icons: Box[]; plus: Box[]; texts: string[] } {
  const row = statusRowOf(c);
  if (row === null) return { icons: [], plus: [], texts: [] };
  const sh = rowShapesOf(row)!;
  const mode = rowModeOf(row)!;
  const texts = row.children.filter((n): n is Text => n instanceof Text && n.visible).map((t) => t.text);
  const tags = sh.circles.map((k) => ({ l: k.x - k.r, r: k.x + k.r, t: k.y - k.r, b: k.y + k.r }));
  if (mode.startsWith("plus-")) return { icons: [], plus: sh.boxes, texts };
  const compactPlus = texts.length > 0 && sh.circles.length === 0 && sh.boxes.length === 2;
  return { icons: compactPlus ? sh.boxes.slice(0, 1) : sh.boxes, plus: compactPlus ? sh.boxes.slice(1) : tags, texts };
}

describe("6F-13 第 1 項：灌注徽章改成小水滴", () => {
  it("下限：水滴的高在畫面上至少 10px（1600、1040、800 寬），地圖縮小時整顆反向放大；1600 寬照原尺寸", () => {
    expect(MIN_INFUSED_ICON_PX).toBe(10);
    for (const s of SIZES) expect(INFUSED_DROP_H * badgeScales("infused", s).ki * s, `s=${s}`).toBeGreaterThanOrEqual(10 - 1e-9);
    expect(badgeScales("infused", S1600).ki).toBe(1); // 1600 寬 12 × 1.275 ≈ 15px
    // 實際的節點：倍率照 badgeScales，沒有「灌」字（沒有 Text），是一個 Graphics
    for (const s of SIZES) {
      const n = child(sprite({ ...BASE, infused: true }, s), INFUSED_BADGE_LABEL)!;
      expect(n.scale.x, `s=${s}`).toBeCloseTo(badgeScales("infused", s).ki);
      expect(n.children.some((k) => k instanceof Text), `s=${s}`).toBe(false);
      expect(n.children.some((k) => k instanceof Graphics), `s=${s}`).toBe(true);
    }
  });

  it("水滴的外框（排位置用的形狀）包住畫出來的水滴", () => {
    const n = child(sprite({ ...BASE, infused: true }, S800), INFUSED_BADGE_LABEL)!;
    const g = n.children.find((k) => k instanceof Graphics) as Graphics;
    const b = g.getLocalBounds();
    const sh = badgeShapes("infused", { x: 0, y: 0 }, { ki: 1, kn: 1 });
    expect(sh.box!.l).toBeLessThanOrEqual(b.minX + 0.05); // 描邊的估計誤差 0.05 以內
    expect(sh.box!.r).toBeGreaterThanOrEqual(b.maxX - 0.05);
    expect(sh.box!.t).toBeLessThanOrEqual(b.minY + 0.05);
    expect(sh.box!.b).toBeGreaterThanOrEqual(b.maxY - 0.05);
  });

  it("接線：灌注不再畫「灌」字，改用 dropPath；排位置用水滴的高", () => {
    const s = sources["render/unitSprite.ts"]!;
    expect(s).toContain("dropPath(new Graphics())");
    expect(s).not.toContain("label(badge.glyph");
    expect(s).toContain('{ base: INFUSED_DROP_H, min: MIN_INFUSED_ICON_PX }');
  });
});

describe("6F-13 第 2 項：800 寬擁擠的召喚物", () => {
  const crowded: UnitDraw = { ...SUMMON, infused: true, statusIds: ["guarded", "empowered", "weaken"] };

  it("擁擠時只留「+N」：精簡列（1040、800 寬）有灌注時，狀態列沒有圖示，只顯示「+3」", () => {
    for (const s of [S1040, S800]) {
      const c = sprite(crowded, s);
      expect(rowModeOf(statusRowOf(c)!)?.startsWith("plus-"), `s=${s}`).toBe(true);
      const row = rowBoxesOf(c);
      expect(row.icons, `s=${s}`).toHaveLength(0);
      expect(row.texts, `s=${s}`).toEqual(["+3"]);
    }
    // 1600 寬（不是精簡列）照舊有圖示
    expect(rowModeOf(statusRowOf(sprite(crowded, S1600))!)).toBe("normal");
    // 一般單位只有 1 個狀態也一樣（「+1」）
    const one = sprite({ ...BASE, infused: true, statusIds: ["guarded"] }, S800);
    expect(rowBoxesOf(one).texts).toEqual(["+1"]);
  });

  it("灌注徽章不蓋到「+N」；整顆在格子裡、不碰臉", () => {
    for (const s of SIZES) {
      const c = sprite(crowded, s);
      const n = child(c, INFUSED_BADGE_LABEL)!;
      const lay = badgeLayoutOf(n)!;
      const sh = badgeShapes("infused", lay.at, lay.sc);
      for (const p of rowBoxesOf(c).plus) expect(shapeHitsBox(sh, p), `s=${s}`).toBe(false);
      expect(inCell(sh.circle, sh.box), `s=${s}`).toBe(true);
      expect(shapeHitsCircle(sh, FACE), `s=${s}`).toBe(false);
    }
  });

  it("兩顆徽章的位置：灌注在左上、回合數徽章在右上，互不重疊；身體（人形的外接框）至少露出一半", () => {
    // 人形的身體：寬約 ±10、腳底到頭頂約 44（世界座標，`inkDoll` 的比例）
    const body: Box = { l: -10, r: 10, t: FEET - 44, b: FEET };
    for (const s of [S1040, S800]) {
      const c = sprite(crowded, s);
      const inf = child(c, INFUSED_BADGE_LABEL)!;
      const turns = child(c, SUMMON_BADGE_LABEL)!;
      const lay = badgeLayoutOf(inf)!;
      const sh = badgeShapes("infused", lay.at, lay.sc);
      const tc: Circle = { x: turns.x, y: turns.y, r: turns.scale.x * 7.5 };
      expect(lay.at.x, `s=${s}`).toBeLessThan(0);
      expect(lay.at.y, `s=${s}`).toBeLessThan(0);
      expect(tc.x, `s=${s}`).toBeGreaterThan(0);
      expect(tc.y, `s=${s}`).toBeLessThan(0);
      expect(shapeHitsCircle(sh, tc), `s=${s}`).toBe(false);
      // 身體被兩顆徽章蓋住的比例（0.25 的格點取樣）
      let all = 0;
      let hid = 0;
      for (let y = body.t; y <= body.b; y += 0.25)
        for (let x = body.l; x <= body.r; x += 0.25) {
          all++;
          const inDrop = sh.box !== null && x >= sh.box.l && x <= sh.box.r && y >= sh.box.t && y <= sh.box.b;
          const inTurn = Math.hypot(x - tc.x, y - tc.y) <= tc.r;
          if (inDrop || inTurn) hid++;
        }
      expect(hid / all, `s=${s}`).toBeLessThan(0.5);
    }
  });
});

describe("6F-13 第 3 項：跨格避臉、圖層順序", () => {
  it("相鄰格的臉：只有南邊的單位頭會伸進來；站在高處（▲1）時再往上 6；倒下的、北邊、左右的不算", () => {
    const self = { x: 4, y: 3, height: 0 };
    const flat = neighborFaces(self, [{ x: 4, y: 4, height: 0, downed: false }]);
    expect(flat).toHaveLength(1);
    expect(flat[0]!.y).toBeCloseTo(T + FACE.y);
    const high = neighborFaces(self, [{ x: 4, y: 4, height: 1, downed: false }]);
    expect(high[0]!.y).toBeCloseTo(T + FACE.y - 6);
    expect(neighborFaces(self, [{ x: 4, y: 4, height: 0, downed: true }])).toHaveLength(0);
    expect(neighborFaces(self, [{ x: 4, y: 2, height: 0, downed: false }])).toHaveLength(0);
    expect(neighborFaces(self, [{ x: 5, y: 3, height: 0, downed: false }])).toHaveLength(0);
    // 自己站得比較高時，南邊的頭伸進來得少
    expect(neighborFaces({ ...self, height: 1 }, [{ x: 4, y: 4, height: 1, downed: false }])[0]!.y).toBeCloseTo(T + FACE.y);
    // 很高的格子（▲7）上的人，頭會伸到更北邊一排（兩格）；▲5 還伸不到
    expect(neighborFaces(self, [{ x: 4, y: 5, height: 7, downed: false }])).toHaveLength(1);
    expect(neighborFaces(self, [{ x: 4, y: 5, height: 5, downed: false }])).toHaveLength(0);
  });

  it("跨格避臉：南邊 ▲1 上的人伸進來的臉，炸彈、蓄力、灌注三種寬度都避開（含數字），也不碰自己的臉", () => {
    const faces = neighborFaces({ x: 4, y: 3, height: 0 }, [{ x: 4, y: 4, height: 1, downed: false }]);
    const reqs: BadgeReq[] = [
      { kind: "bomb", at: statusBadges({ bomb: 2 })[0]!.at, digits: 1 },
      { kind: "charge", at: statusBadges({ bomb: null, charge: 1 })[0]!.at, digits: 1 },
      { kind: "infused", at: infusedBadge({ infused: true, downed: false })!.at, digits: 1 },
    ];
    for (const s of SIZES)
      for (const r of reqs) {
        const [lay] = layoutBadges([r], s, [], [], { faces });
        const sh = badgeShapes(r.kind, lay!.at, lay!.sc, 1, lay!.corner);
        const tag = `${r.kind} s=${s}`;
        expect(lay!.faceOk, tag).toBe(true);
        for (const f of [...faces, FACE]) expect(shapeHitsCircle(sh, f), tag).toBe(false);
        expect(inCell(sh.circle, sh.box), tag).toBe(true);
      }
    // 實際的單位圖層：炸彈在原位會碰到南邊的臉，排開後不碰
    const pref = badgeShapes("bomb", { x: 0.3 * T, y: 0.12 * T }, badgeScales("bomb", S1600));
    expect(shapeHitsCircle(pref, faces[0]!)).toBe(true);
    for (const s of SIZES) {
      const n = child(sprite({ ...BASE, bomb: 2 }, s, faces), BOMB_BADGE_LABEL)!;
      const lay = badgeLayoutOf(n)!;
      expect(shapeHitsCircle(badgeShapes("bomb", lay.at, lay.sc, 1, lay.corner), faces[0]!), `s=${s}`).toBe(false);
    }
  });

  it("避不開時：不管相鄰的臉（faceOk false），自己的臉照樣優先", () => {
    // 假想南邊的臉大到蓋住整個下半格（避不開）
    const huge: Circle[] = [{ x: 0, y: 30, r: 40 }];
    const [lay] = layoutBadges([{ kind: "bomb", at: { x: 0.3, y: 0.12 }, digits: 1 }], S800, [], [], { faces: huge });
    expect(lay!.faceOk).toBe(false);
    expect(shapeHitsCircle(badgeShapes("bomb", lay!.at, lay!.sc, 1, lay!.corner), FACE)).toBe(false);
  });

  it("圖層順序：徽章在同一排的「▲N」之上（marks 在 badges 之後、上層霧之前），南邊一排整排在上面（避不開時畫在那個單位的下層）", () => {
    const rows = new RowStack();
    rows.reset(3);
    const r1 = rows.row(1);
    const order = r1.root.children;
    expect(order.indexOf(r1.marks)).toBeGreaterThan(order.indexOf(r1.badges));
    expect(order.indexOf(r1.marks)).toBeGreaterThan(order.indexOf(r1.units));
    expect(order.indexOf(r1.marks)).toBeLessThan(order.indexOf(r1.veil));
    expect(rows.root.children.indexOf(r1.root)).toBeLessThan(rows.root.children.indexOf(rows.row(2).root));
    // 單位圖層放進第 1 排後：炸彈、蓄力、灌注徽章改在 marks 層畫（還是單位圖層的子節點，位置跟著單位）
    const c = buildUnitSprite(art, new Pulses(), { ...BASE, bomb: 2, charge: 1, infused: true, statusIds: ["guarded"] });
    r1.units.addChild(c);
    rows.attachMarks(c);
    for (const label of [BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL]) {
      const n = c.children.find((k) => k.label === label)!;
      expect(n.parentRenderLayer, label).toBe(r1.marks);
      expect(n.parent, label).toBe(c);
    }
    expect(UNIT_MARK_LABELS).not.toContain(HEIGHT_BADGE_LABEL);
    // 走路換排：換到第 2 排的 units 後再接一次，徽章跟著換到第 2 排的 marks
    rows.row(2).units.addChild(c);
    rows.attachMarks(c);
    expect(c.children.find((k) => k.label === BOMB_BADGE_LABEL)!.parentRenderLayer).toBe(rows.row(2).marks);
  });

  it("接線：繪製器算相鄰格的臉、放進排之後接到 marks 層（重畫、轉身、走路換排）", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("const faces = neighborFaces({ x: u.x, y: u.y, height: heightAt(model, u) }");
    expect(r).toContain("const sprite = buildUnitSprite(this.art, this.pulses, u, faces, { heightDigits: this.heightDigitsAt(model, u) });"); // 6F-14
    expect(r).toContain("this.rows.attachMarks(sprite);");
    expect(r).toContain("const fresh = buildUnitSprite(this.art, this.pulses, next, this.facesOf.get(unitId) ?? [], {"); // 6F-14：加上「▲N」的位數
    expect(r).toContain("this.rows.attachMarks(fresh);");
    expect(r.match(/this\.rows\.attachMarks\(s\);/g)?.length).toBe(2);
  });
});

describe("6F-13 第 4 項：召喚物操控面板顯示技能名稱", () => {
  const summon = (over: Partial<UnitView>) => ({ ...unit("unit_0009", "ally", 1, 1, { owner_id: "unit_0001", summon_expires_round: 3 }), ...over }) as UnitView;
  const cards = { skill_frost_shackle: { name_zh: "寒鎖" } };

  it("伺服器給的名稱 → 技能卡的名稱 →「灌注的技能」；一律不顯示內容 ID", () => {
    expect(infusedSkillName(summon({ infused_skill_id: "skill_frost_shackle", infused_skill_name_zh: "寒鎖" }))).toBe("寒鎖");
    expect(infusedSkillName(summon({ infused_skill_id: "skill_frost_shackle", infused_skill_name_zh: null }), cards)).toBe("寒鎖");
    expect(infusedSkillName(summon({ infused_skill_id: "skill_ignite", infused_skill_name_zh: null }))).toBe("灌注的技能");
    expect(infusedSkillName(summon({ infused_skill_id: null }))).toBeNull();
    const text = pendingInfusionText(summon({ infused_skill_id: "skill_ignite", infused_skill_name_zh: null }));
    expect(text).toBe("待施放：灌注的技能（下回合開始時）");
    expect(text).not.toContain("skill_");
    expect(pendingInfusionText(summon({ infused_skill_id: "skill_frost_shackle", infused_skill_name_zh: null }), cards)).toBe("待施放：寒鎖（下回合開始時）");
    const v = { summon_infuse_ap_cost: 1 } as unknown as BattleView;
    const hero = unit("unit_0001", "ally", 0, 0) as UnitView;
    expect(infuseBlocked(v, hero, summon({ infused_skill_id: "skill_ignite", infused_skill_name_zh: null }), true)).toBe("身上已經有待施放的「灌注的技能」");
  });

  it("接線：面板把技能卡傳給文字；技能卡會去抓待施放技能的卡片", () => {
    const p = sources["ui/SummonPanel.tsx"]!;
    expect(p).toContain("infuseBlocked(view, hero, s, enabled, props.cards)");
    expect(p).toContain("pendingInfusionText(s, props.cards)");
    expect(sources["screens/battle/useBattleData.ts"]).toContain("if (u.infused_skill_id != null) ids.add(u.infused_skill_id);");
    expect(sources["battle/summonControl.ts"]).not.toMatch(/\?\? summon\.infused_skill_id/);
  });
});

describe("6F-13 第 5 項：右上整欄停在縮放列上面", () => {
  it("沒有打開彈出面板時，.bhud-right 的最大高度扣掉縮放列的高度；打開時照 AU-1", () => {
    const css = stripCssComments(readFile(SRC_DIR, "styles/battle-hud.css"));
    expect(css).toMatch(/--zoom-bar-h:\s*28px/);
    const rule = /\.battle-screen\.hud-a \.bhud-right:not\(:has\(\.top-popup\)\)\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toContain("- var(--zoom-bar-h) - 6px");
    expect(css).toMatch(/\.bhud-right:has\(\.top-popup\)\s*\{\s*z-index:\s*20;/);
  });
});

describe("6F-13 第 6 項：蓄力的數字不蓋狀態列的圖示", () => {
  const charged: UnitDraw = { ...BASE, charge: 1, statusIds: ["defending"] };

  it("三種寬度：蓄力的圓和數字都不碰看得到的狀態列（圖示與「+N」）、不碰臉、在格子裡", () => {
    for (const s of SIZES) {
      const c = sprite(charged, s);
      const lay = badgeLayoutOf(child(c, CHARGE_BADGE_LABEL)!)!;
      const sh = badgeShapes("charge", lay.at, lay.sc, 1, lay.corner);
      const row = rowBoxesOf(c);
      for (const b of [...row.icons, ...row.plus]) expect(shapeHitsBox(sh, b), `s=${s}`).toBe(false);
      expect(shapeHitsCircle(sh, FACE), `s=${s}`).toBe(false);
      expect(inCell(sh.circle, sh.box), `s=${s}`).toBe(true);
      expect(lay.tier, `s=${s}`).toBe(0);
    }
    // 1600、800 寬：圖示照舊、整排往右讓（照原本置中的排法一定會碰到）
    expect(rowModeOf(statusRowOf(sprite(charged, S1600))!)).toBe("shift-r");
    expect(rowBoxesOf(sprite(charged, S1600)).icons).toHaveLength(1);
    expect(rowModeOf(statusRowOf(sprite(charged, S800))!)).not.toBe("normal");
    expect(rowModeOf(statusRowOf(sprite(charged, S800))!)).toBe("shift-r"); // 800 寬圖示也放得下（靠右）
  });

  it("chooseRowMode：沒有徽章或照原本放得下時 normal；確定性", () => {
    expect(chooseRowMode([], S800, [], {}, true)).toBe("normal");
    const reqs: BadgeReq[] = [{ kind: "bomb", at: { x: 0.3, y: 0.12 }, digits: 1 }];
    expect(chooseRowMode(reqs, S800, [], { normal: { boxes: [], plus: [] }, "plus-c": { boxes: [], plus: [] } }, true)).toBe("normal");
    const a = sprite(charged, S800);
    const b = sprite(charged, S800);
    expect([child(a, CHARGE_BADGE_LABEL)!.x, child(a, CHARGE_BADGE_LABEL)!.y]).toEqual([child(b, CHARGE_BADGE_LABEL)!.x, child(b, CHARGE_BADGE_LABEL)!.y]);
  });
});

describe("6F-13 第 7 項：狀態列不貼朝向三角形", () => {
  it("朝東：1600 寬 2 個圖示＋「+1」角標在三角形左緣 − 空隙以內；精簡列放得下時也是；朝南不變", () => {
    const u: UnitDraw = { ...BASE, facing: "east", statusIds: ["guarded", "empowered", "weaken"] };
    const arrow = arrowOf(u)!;
    expect(arrow.l).toBeGreaterThan(T * 0.25);
    const row = rowBoxesOf(sprite(u, S1600));
    expect(row.icons).toHaveLength(2);
    expect(row.plus).toHaveLength(1);
    for (const b of [...row.icons, ...row.plus]) expect(b.r).toBeLessThanOrEqual(arrow.l - ROW_ARROW_GAP + 1e-6);
    // 原本（不看三角形）角標會碰到三角形
    const before = rowBoxesOf(sprite({ ...u, facing: "south" }, S1600));
    expect(before.plus[0]!.r).toBeGreaterThan(arrow.l);
    // 精簡列只有 1 個狀態（沒有「+N」）時放得下，也夾在三角形內側
    for (const s of [S1040, S800]) for (const b of rowBoxesOf(sprite({ ...u, statusIds: ["guarded"] }, s)).icons) expect(b.r, `s=${s}`).toBeLessThanOrEqual(arrow.l - ROW_ARROW_GAP + 1e-6);
    expect(arrowLimits(arrowOf({ ...u, facing: "south" }), -ROW_EDGE, ROW_EDGE)).toEqual({ left: -ROW_EDGE, right: ROW_EDGE });
    const west = arrowOf({ ...u, facing: "west" })!;
    expect(arrowLimits(west, -ROW_EDGE, ROW_EDGE).left).toBeCloseTo(west.r + ROW_ARROW_GAP);
    expect(arrowOf({ ...u, downed: true })).toBeNull();
  });
});

describe("6F-13 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/badgeLayout.ts", "render/rowLayout.ts", "render/rowLayers.ts", "render/unitSprite.ts", "render/minMark.ts", "render/BattleRenderer.ts", "battle/summonControl.ts", "ui/SummonPanel.tsx", "screens/battle/useBattleData.ts"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
