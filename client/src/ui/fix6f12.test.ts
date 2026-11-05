// 6F-12（美術 PM 驗收 6F-11：docs/art/6F-11檢查.md「下一段」，只換外觀與顯示）：
// 1. 炸彈、蓄力、灌注徽章：數字畫面上至少 10px、地圖縮小時反向放大；整顆在格子裡，不蓋到臉和眼睛。
// 2. 角標「+N」的字畫面上至少 9px；1040 寬改用 800 寬的做法（1 個圖示＋一般大小的「+N」）。
// 3. 戰場震動、鏡頭偏移時，飄字夾在看得到的戰場裡（不超出左緣）。
// 4. 閃現畫面左側面板：「技能」和「主動 2/6」分開；「可以閃現了」不斷行。
import { Container, Text, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import {
  badgeScales,
  badgeShapes,
  EYES,
  FACE,
  FIRM_STEPS,
  INFUSED_DROP_H,
  layoutBadges,
  STATUS_BADGE_FONT,
  STATUS_BADGE_ICON,
  type BadgeKind,
  type BadgeReq,
} from "../render/badgeLayout";
import { clampFloatCenter, FLOAT_EDGE_PAD, visibleFieldBounds } from "../render/floatStack";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, minMarkScale, MIN_STATUS_GLYPH_PX, STATUS_ROW_LABEL, SUMMON_BADGE_LABEL, unitMarksOf } from "../render/minMark";
import {
  BADGE_CELL_PAD,
  badgeOuterR,
  circleHitsBox,
  circleHitsCircle,
  compactPlusCount,
  isCompactRow,
  MIN_MORE_FONT_PX,
  plusTextWidth,
  ROW_EDGE,
  ROW_ICON_FEET,
  ROW_PLUS_FONT,
  rowShapes,
  rowSpan,
  SUMMON_MORE_DX_MAX,
  SUMMON_MORE_FONT,
  summonBadgeCorner,
  summonBadgeScale,
  summonRowLayout,
  unitRowLayout,
  type Box,
  type Circle,
} from "../render/rowLayout";
import { infusedBadge, statusBadges, summonBadgeOffset } from "../render/unitLook";
import { badgeOptsOf, buildUnitSprite, FEET, Pulses, ROW_Y_FEET } from "../render/unitSprite";
import { readFile, readSources, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const LIM = T / 2 - BADGE_CELL_PAD;
const kRow = (s: number) => minMarkScale(ROW_ICON_FEET - 2, MIN_STATUS_GLYPH_PX, s);

function inCell(c: Circle, b: Box | null): boolean {
  const e = 1e-6;
  const ok = c.x - c.r >= -LIM - e && c.x + c.r <= LIM + e && c.y - c.r >= -LIM - e && c.y + c.r <= LIM + e;
  return ok && (b === null || (b.l >= -LIM - e && b.r <= LIM + e && b.t >= -LIM - e && b.b <= LIM + e));
}

function hitsFace(c: Circle, b: Box | null): boolean {
  for (const f of [FACE, ...EYES]) {
    if (circleHitsCircle(c, f)) return true;
    if (b !== null && circleHitsBox(f, b)) return true;
  }
  return false;
}

/** 徽章的原位（`unitLook` 給的比例）。 */
const BOMB: BadgeReq = { kind: "bomb", at: statusBadges({ bomb: 2 })[0]!.at, digits: 1 };
const CHARGE: BadgeReq = { kind: "charge", at: statusBadges({ bomb: null, charge: 1 })[0]!.at, digits: 1 };
const INFUSED: BadgeReq = { kind: "infused", at: infusedBadge({ infused: true, downed: false })!.at, digits: 1 };

describe("6F-12 第 1 項：炸彈、蓄力、灌注徽章", () => {
  it("數字（灌注是「灌」字）畫面上至少 10px，地圖縮小時反向放大；炸彈、蓄力的圖示畫面上至少 10px；1600 寬照原尺寸", () => {
    for (const s of SIZES) {
      for (const kind of ["bomb", "charge"] as BadgeKind[]) {
        const sc = badgeScales(kind, s);
        expect(STATUS_BADGE_FONT * sc.kn * s, `${kind} s=${s}`).toBeGreaterThanOrEqual(10 - 1e-9);
        expect(STATUS_BADGE_ICON * sc.ki * s, `${kind} s=${s}`).toBeGreaterThanOrEqual(10 - 1e-9);
      }
      const inf = badgeScales("infused", s);
      expect(INFUSED_DROP_H * inf.kn * s, `infused s=${s}`).toBeGreaterThanOrEqual(10 - 1e-9); // 6F-13：灌注改成水滴，水滴的高畫面上 ≥ 10px
    }
    expect(badgeScales("bomb", S1600)).toEqual({ ki: 1, kn: 1 });
    expect(badgeScales("infused", S1600)).toEqual({ ki: 1, kn: 1 });
    expect(badgeScales("bomb", S800).kn).toBeGreaterThan(1.5); // 800 寬：數字放大約 1.55 倍
    expect(badgeScales("infused", S800).ki).toBeGreaterThan(1.25); // 6F-13：水滴（高 12）約 1.29 倍
  });

  it("臉和眼睛的位置和人形一致：頭在腳底（FEET）往上 42 的地方，眼睛在頭裡面", () => {
    const px = (T / 52) * 0.92;
    expect(FACE.y).toBeCloseTo(FEET - 42 * px);
    for (const e of EYES) expect(Math.hypot(e.x - FACE.x, e.y - FACE.y) + e.r).toBeLessThanOrEqual(FACE.r);
  });

  it("三種各自單獨出現：1600、1040、800 寬都整顆（含數字與描邊）在格子裡、不蓋到臉和眼睛", () => {
    for (const s of SIZES)
      for (const req of [BOMB, CHARGE, INFUSED]) {
        const [lay] = layoutBadges([req], s);
        const sh = badgeShapes(req.kind, lay!.at, lay!.sc, req.digits, lay!.corner);
        expect(inCell(sh.circle, sh.box), `${req.kind} s=${s}`).toBe(true);
        expect(hitsFace(sh.circle, sh.box), `${req.kind} s=${s}`).toBe(false);
      }
  });

  it("兩位數（炸彈 10 次以上）也在格子裡", () => {
    for (const s of SIZES) {
      const req = { ...BOMB, digits: 2 };
      const [lay] = layoutBadges([req], s);
      const sh = badgeShapes("bomb", lay!.at, lay!.sc, 2, lay!.corner);
      expect(inCell(sh.circle, sh.box), `s=${s}`).toBe(true);
      expect(hitsFace(sh.circle, sh.box), `s=${s}`).toBe(false);
    }
  });

  it("召喚物：灌注、炸彈徽章避開回合數徽章（800、1040 寬在右上角），也不蓋到臉", () => {
    for (const s of [S1040, S800]) {
      const kb = summonBadgeScale(s);
      const turns: Circle = { ...summonBadgeCorner(kb), r: badgeOuterR(kb) };
      for (const reqs of [[INFUSED], [BOMB], [BOMB, INFUSED]]) {
        const lays = layoutBadges(reqs, s, [turns]);
        const shapes = reqs.map((r, i) => badgeShapes(r.kind, lays[i]!.at, lays[i]!.sc, r.digits, lays[i]!.corner));
        const tag = `s=${s} ${reqs.map((r) => r.kind).join("+")}`;
        for (const sh of shapes) {
          expect(inCell(sh.circle, sh.box), tag).toBe(true);
          expect(hitsFace(sh.circle, sh.box), tag).toBe(false);
          expect(circleHitsCircle(sh.circle, turns), tag).toBe(false);
          if (sh.box !== null) expect(circleHitsBox(turns, sh.box), tag).toBe(false);
        }
        // 兩顆（炸彈＋灌注）加上回合數徽章：1040 寬互不重疊；800 寬格子只有 31px 放不下三顆，允許炸彈和灌注重疊（報告待決）
        if (shapes.length === 2 && s === S1040) expect(circleHitsCircle(shapes[0]!.circle, shapes[1]!.circle), tag).toBe(false);
      }
    }
  });

  it("炸彈＋蓄力同時在身上：互不重疊；三種都在（800 寬放不下）時臉仍優先、整顆在格子裡", () => {
    for (const s of SIZES) {
      const lays = layoutBadges([BOMB, CHARGE], s);
      const [a, b] = [BOMB, CHARGE].map((r, i) => badgeShapes(r.kind, lays[i]!.at, lays[i]!.sc, 1, lays[i]!.corner));
      expect(circleHitsCircle(a!.circle, b!.circle), `s=${s}`).toBe(false);
      expect(circleHitsBox(b!.circle, a!.box!), `s=${s}`).toBe(false);
      const all = layoutBadges([BOMB, CHARGE, INFUSED], s);
      [BOMB, CHARGE, INFUSED].forEach((r, i) => {
        const sh = badgeShapes(r.kind, all[i]!.at, all[i]!.sc, 1, all[i]!.corner);
        expect(inCell(sh.circle, sh.box), `${r.kind} s=${s}`).toBe(true);
        expect(hitsFace(sh.circle, sh.box), `${r.kind} s=${s}`).toBe(false);
      });
    }
  });

  it("腳邊狀態列：放得下時避開狀態列的圖示（數字不被蓋住）；6F-17 起放不下時也不蓋圖示（回報放不下）", () => {
    const boxHit = (a: Box, b: Box) => a.l < b.r - 1e-9 && b.l < a.r - 1e-9 && a.t < b.b - 1e-9 && b.t < a.b - 1e-9;
    for (const s of SIZES) {
      // 放得下：狀態列只佔格子左下角（例如召喚物靠左的精簡列）；800 寬時蓄力（在左邊）放不下，只看炸彈
      const corner: Box = { l: -T / 2 + 1.5, r: -T / 2 + 1.5 + ROW_ICON_FEET * kRow(s), t: 13.3 - ROW_ICON_FEET * kRow(s), b: 13.3 };
      for (const req of s === S800 ? [BOMB] : [BOMB, CHARGE]) {
        const [b] = layoutBadges([req], s, [], [corner]);
        const sh = badgeShapes(req.kind, b!.at, b!.sc, 1, b!.corner);
        const tag = `${req.kind} s=${s}`;
        expect(inCell(sh.circle, sh.box), tag).toBe(true);
        expect(hitsFace(sh.circle, sh.box), tag).toBe(false);
        expect(circleHitsBox(sh.circle, corner), tag).toBe(false);
        expect(boxHit(sh.box!, corner), tag).toBe(false);
      }
      // 1 個圖示置中（一般單位）：6F-17 起徽章一律不蓋圖示（美術 PM 6F-16 檢查必修 1）；
      // 放不下時 `layoutBadges` 回報放不下（`firm` ＝ FIRM_STEPS.length），由狀態列換顯示方式讓位（`chooseRowLayout`，見 fix6f17）
      const k = kRow(s);
      const row = rowShapes(unitRowLayout(1, k, false, false, s, 0), 1, k, ROW_Y_FEET + ROW_ICON_FEET / 2, false).boxes;
      for (const req of [BOMB, CHARGE]) {
        const [b] = layoutBadges([req], s, [], row);
        const sh = badgeShapes(req.kind, b!.at, b!.sc, 1, b!.corner);
        if (b!.firm >= FIRM_STEPS.length) continue;
        expect(inCell(sh.circle, sh.box), `${req.kind} s=${s}`).toBe(true);
        expect(hitsFace(sh.circle, sh.box), `${req.kind} s=${s}`).toBe(false);
        for (const r of row) expect(circleHitsBox(sh.circle, r) || boxHit(sh.box!, r), `${req.kind} s=${s}`).toBe(false);
      }
    }
  });

  it("確定性：同樣的輸入每次同樣的位置", () => {
    expect(layoutBadges([BOMB, CHARGE, INFUSED], S800)).toEqual(layoutBadges([BOMB, CHARGE, INFUSED], S800));
  });

  it("實際的單位圖層：三種徽章登記成標記、排在回合數徽章與狀態列後面；套用縮放後位置與倍率照 layoutBadges", () => {
    const view = (): BattleView =>
      ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
    const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;
    const base: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: 2, charge: 1, infused: true };
    // 有狀態列時：套用順序是狀態列在前（徽章要避開排好的狀態列），徽章畫在狀態列與 HP 條上面
    const withRow = buildUnitSprite(art, new Pulses(), { ...base, statusIds: ["guarded"] });
    expect(unitMarksOf(withRow).map((n) => n.label)).toEqual([STATUS_ROW_LABEL, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL]);
    const idx = (label: string) => withRow.children.findIndex((n) => n.label === label);
    expect(idx(BOMB_BADGE_LABEL)).toBeGreaterThan(idx(STATUS_ROW_LABEL));
    const sprite = buildUnitSprite(art, new Pulses(), { ...base, statusIds: [] });
    const marks = unitMarksOf(sprite);
    expect(marks.map((n) => n.label)).toEqual([BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL]);
    for (const s of SIZES) {
      for (const n of marks) applyMarkScale(n, s, s);
      const want = layoutBadges([BOMB, CHARGE, INFUSED], s, [], [], badgeOptsOf(base)); // 6F-14：避開朝向三角形；6F-15：也避開 HP 條
      marks.forEach((n, i) => {
        expect(n.position.x, `s=${s} ${n.label}`).toBeCloseTo(want[i]!.at.x);
        expect(n.position.y, `s=${s} ${n.label}`).toBeCloseTo(want[i]!.at.y);
        expect(n.scale.x, `s=${s} ${n.label}`).toBeCloseTo(want[i]!.sc.ki);
      });
      // 炸彈的數字：節點放大 ki，數字自己再放大 kn ÷ ki，畫面上 ≥ 10px
      const num = (marks[0] as Container).children.find((c) => c instanceof Text) as Text;
      expect(STATUS_BADGE_FONT * marks[0]!.scale.x * num.scale.x * s, `s=${s}`).toBeGreaterThanOrEqual(10 - 1e-6);
    }
    expect(SUMMON_BADGE_LABEL).not.toBe(BOMB_BADGE_LABEL);
  });

  it("接線：unitSprite 用 badgeLayout 的常數與 layoutBadges，三種都 registerMark；繪製器照舊用 unitMarksOf", () => {
    const s = sources["render/unitSprite.ts"]!;
    expect(s).toContain("if (badges.length > 0) registerBadges(badges, turns, row, faces, badgeMarks(u));"); // 6F-13：加上相鄰格的臉；6F-14：朝向三角形（6F-18：「▲N」拿掉）
    expect(s).toContain("const lay = compute(s)[i]!;"); // 6F-13：同一個縮放只算一次（含只留「+N」）
    expect(s).toContain("const sh = shapesOf(lay);"); // 6F-13：只留「+N」時的字寬另外算
    expect(s).toContain("rowShapesNow.set(row, sh);");
    expect(s).toContain("registerMark(b.node, spec, inner, relayout);");
    expect(s).toContain("new Graphics().circle(0, 0, STATUS_BADGE_R)");
    expect(s).toContain("dropPath(new Graphics())"); // 6F-13：灌注改成水滴
    expect(sources["render/minMark.ts"]).toContain("const names = [SUMMON_BADGE_LABEL, STATUS_ROW_LABEL, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL];");
    expect(sources["render/BattleRenderer.ts"]).toContain("for (const n of unitMarksOf(unit)) this.scaleMark(n);");
  });
});

describe("6F-12 第 2 項：角標「+N」的可讀性", () => {
  const bottom = ROW_Y_FEET + ROW_ICON_FEET / 2;

  it("1040 寬改用 800 寬的做法：精簡列（1 個圖示＋一般大小的「+N」字）；1600 寬照舊是角標", () => {
    expect(isCompactRow(S800)).toBe(true);
    expect(isCompactRow(S1040)).toBe(true);
    expect(isCompactRow(S1600)).toBe(false);
    const plusW = plusTextWidth(1);
    const lay = unitRowLayout(2, kRow(S1040), true, false, S1040, plusW);
    expect(lay.compact).toBe(true);
    const { boxes, circles } = rowShapes(lay, 2, kRow(S1040), bottom, true, plusW);
    expect(circles).toHaveLength(0); // 沒有角標
    expect(boxes).toHaveLength(2); // 1 個圖示＋「+N」字
    const span = rowSpan(lay, 2, kRow(S1040), true, plusW);
    expect(span.l).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
    expect(span.r).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
  });

  it("畫面上的字至少 9px：精簡列的「+N」（800、1040）、角標的「+N」（縮放 > 85% 的每一個縮放，含 1600 寬）", () => {
    for (const s of [S800, S1040]) expect(ROW_PLUS_FONT * kRow(s) * s, `s=${s}`).toBeGreaterThanOrEqual(MIN_MORE_FONT_PX);
    for (let s = 0.851; s <= 2.0; s += 0.01) expect(SUMMON_MORE_FONT * kRow(s) * s, `s=${s}`).toBeGreaterThanOrEqual(MIN_MORE_FONT_PX);
    expect(SUMMON_MORE_FONT * kRow(S1600) * S1600).toBeGreaterThan(10.5); // 1600 寬約 10.8px
  });

  it("1600 寬一般單位：放大的角標仍完全在第 2 個圖示外面、整排在格子裡", () => {
    const k = kRow(S1600);
    const lay = unitRowLayout(2, k, true, false, S1600, plusTextWidth(2));
    expect(lay.compact).toBe(false);
    expect(lay.moreDx).toBe(SUMMON_MORE_DX_MAX);
    const { boxes, circles } = rowShapes(lay, 2, k, bottom, true);
    for (const b of boxes) expect(circleHitsBox(circles[0]!, b)).toBe(false);
    const span = rowSpan(lay, 2, k, true);
    expect(span.l).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
    expect(span.r).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
  });

  it("1600 寬召喚物（徽章在原位）：角標放不到完全在圖示外時改成精簡列，不和徽章重疊、在格子裡", () => {
    for (const total of [3, 4])
      for (const bomb of [false, true]) {
        const k = kRow(S1600);
        const at = summonBadgeOffset({ bomb: bomb ? 2 : null }, T);
        const plusW = plusTextWidth(compactPlusCount(total));
        const lay = summonRowLayout(2, k, at, bottom, true, false, 1, false, plusW);
        const tag = `total=${total} bomb=${bomb}`;
        expect(lay.compact || lay.moreDx >= SUMMON_MORE_DX_MAX - 1e-9, tag).toBe(true);
        const badge: Circle = { ...lay.badge, r: badgeOuterR(1) };
        const shapes = rowShapes(lay, 2, k, bottom, true, lay.compact ? plusW : 0);
        for (const b of shapes.boxes) expect(circleHitsBox(badge, b), tag).toBe(false);
        for (const c of shapes.circles) expect(circleHitsCircle(badge, c), tag).toBe(false);
        const span = rowSpan(lay, 2, k, true, lay.compact ? plusW : 0);
        expect(span.l, tag).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
      }
  });

  it("接線：角標用 SUMMON_MORE_FONT", () => {
    expect(sources["render/unitSprite.ts"]).toContain("label(`+${extra}`, SUMMON_MORE_FONT, 0xffffff, true)");
  });
});

describe("6F-12 第 3 項：戰場震動、鏡頭偏移時飄字不超出戰場", () => {
  const W = 10 * T;
  const H = 10 * T;
  const R = 40;

  it("沒有震動、沒有鏡頭偏移：和 6F-10 一樣（左右是地圖兩緣，上面是畫布上緣含頭頂預留，下面是地圖下緣）", () => {
    expect(visibleFieldBounds(W, H, R, { x: 0, y: 0 }, { x: 0, y: 0 })).toEqual({ left: 0, top: -R, right: W, bottom: H });
  });

  it("地圖往右移（鏡頭或震動）：左緣跟著地圖，字不會貼在畫布左邊露出來的底色上", () => {
    for (const [cam, shake] of [
      [{ x: 3, y: 0 }, { x: 0, y: 0 }],
      [{ x: 0, y: 0 }, { x: 3, y: 0 }],
      [{ x: 2, y: 0 }, { x: 3.5, y: 0 }],
    ] as const) {
      const b = visibleFieldBounds(W, H, R, cam, shake);
      expect(b.left).toBe(0); // 地圖左緣（世界座標 0）
      expect(b.right).toBeCloseTo(W - cam.x - shake.x); // 地圖右邊被推出畫布的部分不算
      // 「撞擊！」放在最左邊：夾完以後整個字在地圖裡，畫面上也在畫布裡
      const p = clampFloatCenter(-20, 100, 30, 10, b);
      const screenLeft = p.x - 30 + cam.x + shake.x;
      expect(p.x - 30).toBeGreaterThanOrEqual(FLOAT_EDGE_PAD - 1e-9);
      expect(screenLeft).toBeGreaterThanOrEqual(0);
    }
  });

  it("地圖往左移：左緣是畫布左緣（地圖被推出去的部分看不到），字不被切掉", () => {
    const b = visibleFieldBounds(W, H, R, { x: -2, y: 0 }, { x: -3, y: 0 });
    expect(b.left).toBe(5);
    expect(b.right).toBe(W);
    const p = clampFloatCenter(0, 100, 30, 10, b);
    expect(p.x - 30 + -5).toBeGreaterThanOrEqual(FLOAT_EDGE_PAD - 1e-9); // 畫面上離畫布左緣 ≥ pad
  });

  it("上下：上緣照舊是畫布上緣（扣掉震動）；下緣不超過地圖下緣", () => {
    const b = visibleFieldBounds(W, H, R, { x: 0, y: 4 }, { x: 0, y: -2 });
    expect(b.top).toBe(-R - 2);
    expect(b.bottom).toBe(H - 2);
    expect(visibleFieldBounds(W, H, R, { x: 0, y: -4 }, { x: 0, y: 0 }).bottom).toBe(H);
  });

  it("接線：floatBounds 用 visibleFieldBounds，帶入鏡頭與場景的震動位移；每一幀的 placeFloat 都重算", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("return visibleFieldBounds(w, h, this.worldBaseY, this.cam, this.app.stage.position);");
    expect(r).toContain("clampFloatCenter(x, y, (t.width * scale) / 2, (t.height * scale) / 2, this.floatBounds())");
    // 震動是整個場景的位移（浮動字和地圖在同一個場景裡）
    expect(r).toContain("impactShakeEffect(vfx.shakes ?? [], now, (x, y) => stage.position.set(x / this.scale, y / this.scale))");
  });
});

describe("6F-12 第 4 項：閃現畫面左側面板", () => {
  it("「技能」和「主動 2/6・…」中間用 lead-gap 分開（不用全形空白）", () => {
    const s = sources["run/RunHeroPanel.tsx"]!;
    expect(s).toMatch(/技能\s*<span className="muted small lead-gap" data-testid="run-skill-slots">/);
  });

  it("「可以閃現了」不斷行：.skill-flash-ready 是 inline-block、white-space: nowrap", () => {
    const css = stripCssComments(readFile(SRC_DIR, "styles/flash.css"));
    const rule = /\.skill-flash-ready\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toMatch(/white-space:\s*nowrap/);
    expect(rule).toMatch(/display:\s*inline-block/);
  });
});

describe("6F-12 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/badgeLayout.ts", "render/rowLayout.ts", "render/unitSprite.ts", "render/minMark.ts", "render/floatStack.ts", "render/BattleRenderer.ts", "run/RunHeroPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
