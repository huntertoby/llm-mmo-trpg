// 6F-12（美術 PM 驗收 6F-11：docs/archive/art/6F-11檢查.md「下一段」，只換外觀與顯示）：
// 1. 炸彈、蓄力、灌注徽章：數字畫面上至少 10px、地圖縮小時反向放大；整顆在格子裡，不蓋到臉和眼睛。
// 2. 角標「+N」的字畫面上至少 9px；1040 寬改用 800 寬的做法（1 個圖示＋一般大小的「+N」）。
// 3. 戰場震動、鏡頭偏移時，飄字夾在看得到的戰場裡（不超出左緣）。
// 4. 閃現畫面左側面板：「技能」和「主動 2/6」分開；「可以閃現了」不斷行。
import { Container, Text, Texture, CanvasTextMetrics, Graphics } from "pixi.js";
import { describe, expect, it, afterAll, beforeAll, vi } from "vitest";
import { type BattleView, type UnitView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { type ArtTextures } from "../render/artTextures";
import { badgeScales, badgeShapes, EYES, FACE, FACE_CORE, FACE_LEGACY, FIRM_STEPS, INFUSED_DROP_H, layoutBadges, STATUS_BADGE_FONT, STATUS_BADGE_ICON, type BadgeKind, type BadgeReq, chooseRowMode, MIN_INFUSED_ICON_PX, neighborFaces } from "../render/badgeLayout";
import { DOLL_SCALE } from "../render/paperdoll";
import { clampFloatCenter, FLOAT_EDGE_PAD, visibleFieldBounds } from "../render/floatStack";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, minMarkScale, MIN_STATUS_GLYPH_PX, STATUS_ROW_LABEL, SUMMON_BADGE_LABEL, unitMarksOf, HEIGHT_BADGE_LABEL, statusRowOf } from "../render/minMark";
import { BADGE_CELL_PAD, badgeOuterR, circleHitsBox, circleHitsCircle, compactPlusCount, isCompactRow, MIN_MORE_FONT_PX, plusTextWidth, ROW_EDGE, ROW_ICON_FEET, ROW_PLUS_FONT, rowShapes, rowSpan, SUMMON_MORE_DX_MAX, summonBadgeCorner, summonBadgeScale, summonRowLayout, unitRowLayout, type Box, type Circle, PLUS_CAP_FONT, arrowLimits, ROW_ARROW_GAP } from "../render/rowLayout";
import { infusedBadge, statusBadges, summonBadgeOffset } from "../render/unitLook";
import { badgeOptsOf, buildUnitSprite, FEET, Pulses, ROW_Y_FEET, arrowOf, badgeLayoutOf, rowModeOf, rowShapesOf, rowPlusTexts } from "../render/unitSprite";
import { readFile, readSources, SRC_DIR, stripCssComments, stripTsComments, BATTLE_RENDERER_FILES, battleRendererSource } from "../test/sourceScan";
import { infusedSkillName, infuseBlocked, pendingInfusionText } from "../battle/summonControl";
import { RowStack, UNIT_MARK_LABELS } from "../render/rowLayers";

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

/**
 * QK-9b：臉照 Q 版的頭（`FACE`）。排法回報退到只避開眼睛一帶（`faceCore`）時改看 `FACE_CORE`；
 * 退到 C 版的頭（`faceLegacy`，只有連眼睛一帶也一定要壓到 HP 條時）看 `FACE_LEGACY`。眼睛照舊一律不碰（C 版那一步除外）。
 */
function hitsFace(c: Circle, b: Box | null, lay?: { faceCore?: boolean; faceLegacy?: boolean }): boolean {
  const faces = lay?.faceLegacy === true ? [FACE_LEGACY] : lay?.faceCore === true ? [FACE_CORE, ...EYES] : [FACE, ...EYES];
  for (const f of faces) {
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

  it("臉和眼睛的位置和人形一致：QK-9b 起照 Q 版頭（腳底往上 29、半徑 9.3，縮放 1.06），眼睛在頭裡面、也在「眼睛一帶」裡面", () => {
    const px = (T / 52) * DOLL_SCALE;
    expect(DOLL_SCALE).toBe(1.06);
    expect(FACE.y).toBeCloseTo(FEET - 29 * px);
    expect(FACE.r).toBeCloseTo(9.3 * px);
    for (const e of EYES) expect(Math.hypot(e.x - FACE.x, e.y - FACE.y) + e.r).toBeLessThanOrEqual(FACE.r);
    for (const e of EYES) expect(Math.hypot(e.x - FACE_CORE.x, e.y - FACE_CORE.y) + e.r).toBeLessThanOrEqual(FACE_CORE.r + 1e-9);
    // C 版的頭（最後手段）照 6F-12：腳底往上 42、縮放 0.92
    expect(FACE_LEGACY.y).toBeCloseTo(FEET - 42 * (T / 52) * 0.92);
  });

  it("三種各自單獨出現：1600、1040、800 寬都整顆（含數字與描邊）在格子裡、不蓋到臉和眼睛", () => {
    for (const s of SIZES)
      for (const req of [BOMB, CHARGE, INFUSED]) {
        const [lay] = layoutBadges([req], s);
        const sh = badgeShapes(req.kind, lay!.at, lay!.sc, req.digits, lay!.corner);
        expect(inCell(sh.circle, sh.box), `${req.kind} s=${s}`).toBe(true);
        expect(hitsFace(sh.circle, sh.box, lay!), `${req.kind} s=${s}`).toBe(false);
      }
  });

  it("兩位數（炸彈 10 次以上）也在格子裡", () => {
    for (const s of SIZES) {
      const req = { ...BOMB, digits: 2 };
      const [lay] = layoutBadges([req], s);
      const sh = badgeShapes("bomb", lay!.at, lay!.sc, 2, lay!.corner);
      expect(inCell(sh.circle, sh.box), `s=${s}`).toBe(true);
      expect(hitsFace(sh.circle, sh.box, lay!), `s=${s}`).toBe(false);
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
        for (const [i, sh] of shapes.entries()) {
          expect(inCell(sh.circle, sh.box), tag).toBe(true);
          expect(hitsFace(sh.circle, sh.box, lays[i]!), tag).toBe(false);
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
      // QK-9b：800 寬時 Q 版的頭比較低，兩顆加上「眼睛一帶」放不下，臉優先（同三種都在時）：允許重疊（`level` ≥ 1），眼睛照樣不碰
      if (s === S800) {
        expect(lays[1]!.level ?? 0, `s=${s}`).toBeGreaterThanOrEqual(1);
        [a!, b!].forEach((sh, i) => expect(hitsFace(sh.circle, sh.box, lays[i]!), `s=${s}`).toBe(false));
      } else {
        expect(circleHitsCircle(a!.circle, b!.circle), `s=${s}`).toBe(false);
        expect(circleHitsBox(b!.circle, a!.box!), `s=${s}`).toBe(false);
      }
      const all = layoutBadges([BOMB, CHARGE, INFUSED], s);
      [BOMB, CHARGE, INFUSED].forEach((r, i) => {
        const sh = badgeShapes(r.kind, all[i]!.at, all[i]!.sc, 1, all[i]!.corner);
        expect(inCell(sh.circle, sh.box), `${r.kind} s=${s}`).toBe(true);
        expect(hitsFace(sh.circle, sh.box, all[i]!), `${r.kind} s=${s}`).toBe(false);
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
        expect(hitsFace(sh.circle, sh.box, b!), tag).toBe(false);
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
        expect(hitsFace(sh.circle, sh.box, b!), `${req.kind} s=${s}`).toBe(false);
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
    expect(s).toContain("if (badges.length > 0) registerBadges(badges, turns, row, faces, badgeMarks(u), hudDy);"); // 6F-13：加上相鄰格的臉；6F-14：朝向三角形（6F-18：「▲N」拿掉）；QK-4b：頭目整組 HUD 平移
    expect(s).toContain("const lay = compute(s)[i]!;"); // 6F-13：同一個縮放只算一次（含只留「+N」）
    expect(s).toContain("const sh = shapesOf(lay);"); // 6F-13：只留「+N」時的字寬另外算
    expect(s).toContain("rowShapesNow.set(row, sh);");
    expect(s).toContain("registerMark(b.node, spec, inner, relayout);");
    expect(s).toContain("new Graphics().circle(0, 0, STATUS_BADGE_R)");
    expect(s).toContain("dropPath(new Graphics())"); // 6F-13：灌注改成水滴
    expect(sources["render/minMark.ts"]).toContain("const names = [SUMMON_BADGE_LABEL, STATUS_ROW_LABEL, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, HIDDEN_HP_LABEL];");
    expect(battleRendererSource(sources)).toContain("for (const n of unitMarksOf(unit)) this.scaleMark(n);");
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
    // 6F-19：角標改成膠囊，數字的字級 PLUS_CAP_FONT（9）
    for (let s = 0.851; s <= 2.0; s += 0.01) expect(PLUS_CAP_FONT * kRow(s) * s, `s=${s}`).toBeGreaterThanOrEqual(MIN_MORE_FONT_PX);
    expect(PLUS_CAP_FONT * kRow(S1600) * S1600).toBeGreaterThan(10.5); // 1600 寬約 11.5px
  });

  it("1600 寬一般單位：放大的角標仍完全在第 2 個圖示外面、整排在格子裡", () => {
    const k = kRow(S1600);
    const lay = unitRowLayout(2, k, true, false, S1600, plusTextWidth(2));
    expect(lay.compact).toBe(false);
    expect(lay.moreDx).toBe(SUMMON_MORE_DX_MAX);
    const { boxes, cap } = rowShapes(lay, 2, k, bottom, true);
    expect(cap).not.toBeNull();
    for (const b of boxes.filter((x) => x !== cap)) expect(cap!.l >= b.r - 1e-9 || cap!.b <= b.t + 1e-9).toBe(true);
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

  it("接線：角標用「+N」膠囊（6F-19；數字字級 PLUS_CAP_FONT）", () => {
    expect(sources["render/unitSprite.ts"]).toContain("const text = label(digits, PLUS_CAP_FONT, 0xffffff, true);");
    expect(sources["render/unitSprite.ts"]).toContain("const more = extra > 0 ? plusCapsule(extra) : null;");
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
    const r = battleRendererSource(sources);
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
    for (const f of ["render/badgeLayout.ts", "render/rowLayout.ts", "render/unitSprite.ts", "render/minMark.ts", "render/floatStack.ts", ...BATTLE_RENDERER_FILES, "run/RunHeroPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});

// --- 原 fix6f13.test.ts ---
describe("原 fix6f13.test.ts", () => {
// 6F-13（美術 PM 驗收 6F-12：docs/archive/art/6F-12檢查.md，只換外觀與顯示）：
// 1. 灌注徽章：「灌」字 12px 還是讀不出來 → 改成程式繪製的小水滴，畫面上至少高 10px。
// 2. 800 寬擁擠的召喚物：有灌注時狀態列只留「+N」；灌注不蓋「+N」；回合數徽章和灌注分在左右，身體至少露出一半。
// 3. 跨格避臉：南邊（含站在高處）的單位伸進這一格的臉也要避開；避不開時徽章畫在那個單位的下層；徽章畫在「▲N」之上。
// 4. 召喚物操控面板顯示技能名稱，不顯示內容 ID。
// 5. 800 寬右上整欄停在縮放列上面。
// 6. 蓄力的數字不蓋狀態列的圖示（數字可換到正下方、狀態列可讓位或只留「+N」）。
// 7. 狀態列（含「+N」）不貼到朝向三角形。

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
  const texts = rowPlusTexts(row);
  // 6F-19：「+N」一律是膠囊（`cap`，也在 `boxes` 裡）
  const cap = sh.cap;
  if (mode.startsWith("plus-")) return { icons: [], plus: sh.boxes, texts };
  return { icons: sh.boxes.filter((b) => b !== cap), plus: cap === null ? [] : [cap], texts };
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
    // 6F-18（美術 PM 6F-17 檢查必修 2）：狀態 2 個以內不為了徽章只留「+N」：一般單位只有 1 個狀態時照舊畫圖示，灌注徽章不蓋到它
    const one = sprite({ ...BASE, infused: true, statusIds: ["guarded"] }, S800);
    expect(rowBoxesOf(one).texts).toEqual([]);
    expect(rowBoxesOf(one).icons).toHaveLength(1);
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
    // 很高的格子（▲8）上的人，頭會伸到更北邊一排（兩格）；▲7 還伸不到（QK-9b：Q 版的頭比 C 版低約 7，C 版時 ▲7 就伸到）
    expect(neighborFaces(self, [{ x: 4, y: 5, height: 8, downed: false }])).toHaveLength(1);
    expect(neighborFaces(self, [{ x: 4, y: 5, height: 7, downed: false }])).toHaveLength(0);
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
    // QK-9b：Q 版的頭比 C 版低約 7，▲1 的臉碰不到炸彈的原位了（C 版時會碰到、要排開）
    const pref = badgeShapes("bomb", { x: 0.3 * T, y: 0.12 * T }, badgeScales("bomb", S1600));
    expect(shapeHitsCircle(pref, faces[0]!)).toBe(false);
    // ▲2 的臉會碰到原位；自己的 Q 版頭優先，炸彈、蓄力讓不開南邊的臉（`faceOk` false，畫在那個單位的下層），灌注讓得開
    const faces2 = neighborFaces({ x: 4, y: 3, height: 0 }, [{ x: 4, y: 4, height: 2, downed: false }]);
    expect(shapeHitsCircle(pref, faces2[0]!)).toBe(true);
    for (const s of SIZES)
      for (const r of reqs) {
        const [lay] = layoutBadges([r], s, [], [], { faces: faces2 });
        expect(lay!.faceOk, `${r.kind} s=${s}`).toBe(r.kind === "infused");
        expect(shapeHitsCircle(badgeShapes(r.kind, lay!.at, lay!.sc, 1, lay!.corner), FACE), `${r.kind} s=${s}`).toBe(false);
      }
    for (const s of SIZES) {
      const n = child(sprite({ ...BASE, bomb: 2 }, s, faces), BOMB_BADGE_LABEL)!;
      const lay = badgeLayoutOf(n)!;
      // QK-9b：800 寬時（HP 條、三角形之外還要讓開較低的 Q 版頭）讓不開南邊的臉，畫在那個單位的下層（`faceOk` false）
      expect(lay.faceOk, `s=${s}`).toBe(s !== S800);
      if (lay.faceOk) expect(shapeHitsCircle(badgeShapes("bomb", lay.at, lay.sc, 1, lay.corner), faces[0]!), `s=${s}`).toBe(false);
    }
  });

  it("避不開時：不管相鄰的臉（faceOk false），自己的臉照樣優先", () => {
    // 假想南邊的臉大到蓋住整個下半格（避不開）
    const huge: Circle[] = [{ x: 0, y: 30, r: 40 }];
    const [lay] = layoutBadges([{ kind: "bomb", at: { x: 0.3, y: 0.12 }, digits: 1 }], S800, [], [], { faces: huge });
    expect(lay!.faceOk).toBe(false);
    expect(shapeHitsCircle(badgeShapes("bomb", lay!.at, lay!.sc, 1, lay!.corner), FACE)).toBe(false);
  });

  it("圖層順序：徽章在同一排的「▲N」之上（marks 在 badges 之後；HID-1b 起在上層霧之後），南邊一排整排在上面（避不開時畫在那個單位的下層）", () => {
    const rows = new RowStack();
    rows.reset(3);
    const r1 = rows.row(1);
    const order = r1.root.children;
    expect(order.indexOf(r1.marks)).toBeGreaterThan(order.indexOf(r1.badges));
    expect(order.indexOf(r1.marks)).toBeGreaterThan(order.indexOf(r1.units));
    expect(order.indexOf(r1.marks)).toBeGreaterThan(order.indexOf(r1.veil));
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
    const r = battleRendererSource(sources);
    expect(r).toContain("const faces = neighborFaces({ x: u.x, y: u.y, height: heightAt(model, u) }");
    expect(r).toContain("const sprite = buildUnitSprite(this.art, this.pulses, u, faces, { edge: mapEdgeOf(model, u) });"); // 6F-16：地圖邊緣（6F-18：「▲N」的位數拿掉）
    expect(r).toContain("this.rows.attachMarks(sprite, this.southArrowTop(model, u, sprite));"); // 6F-21b：朝南三角形的圖層
    expect(r).toContain("const fresh = buildUnitSprite(this.art, this.pulses, next, this.facesOf.get(unitId) ?? [], {");
    expect(r).toContain("this.rows.attachMarks(fresh, this.model === null ? null : this.southArrowTop(this.model, next, fresh));");
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
    for (const f of ["render/badgeLayout.ts", "render/rowLayout.ts", "render/rowLayers.ts", "render/unitSprite.ts", "render/minMark.ts", ...BATTLE_RENDERER_FILES, "battle/summonControl.ts", "ui/SummonPanel.tsx", "screens/battle/useBattleData.ts"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
});
