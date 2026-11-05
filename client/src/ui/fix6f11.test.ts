// 6F-11（美術 PM 驗收 6F-10b：docs/art/6F-10b檢查.md「下一段要修」，只換外觀與顯示）：
// 1. 800 寬（縮放 ≤ 70%）狀態列只顯示 1 個圖示＋一般大小的「+N」；召喚物回合數徽章畫面半徑 ≥ 7px、粗體深色描邊、整顆在格子裡。
// 2. 最上排的飄字往下 6～8px、留在戰場上緣以內。3. 一般單位的「+N」在 1600、1040 寬改成角標；800 寬照第 1 點。
// 4. 徽章數字畫面上至少 10px。
import { Container } from "pixi.js";
import { describe, expect, it } from "vitest";
import { capRise, FLOAT_TOP_SHIFT_PX, floatTopShift } from "../render/floatStack";
import { applyMarkScale, minMarkScale, MIN_BADGE_FONT_PX, MIN_STATUS_GLYPH_PX, registerMark, STATUS_ROW_LABEL, SUMMON_BADGE_LABEL, unitMarksOf } from "../render/minMark";
import {
  badgeOuterR,
  circleHitsBox,
  circleHitsCircle,
  compactPlusCount,
  isCompactRow,
  plusTextWidth,
  ROW_CORNER_GAP,
  ROW_EDGE,
  ROW_ICON_FEET,
  ROW_PLUS_FONT,
  rowShapes,
  rowSpan,
  SUMMON_MORE_DX_MAX,
  summonBadgeAlone,
  summonBadgeCorner,
  summonBadgeScale,
  summonRowLayout,
  unitRowLayout,
  type Box,
} from "../render/rowLayout";
import { SUMMON_BADGE_FONT, SUMMON_BADGE_RADIUS, summonBadgeOffset } from "../render/unitLook";
import { ROW_Y_FEET } from "../render/unitSprite";
import { readFile, readSources, SRC_DIR, stripTsComments } from "../test/sourceScan";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
const bottom = ROW_Y_FEET + ROW_ICON_FEET / 2;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const kOf = (s: number) => minMarkScale(ROW_ICON_FEET - 2, MIN_STATUS_GLYPH_PX, s);
const boxesHit = (a: Box, b: Box) => a.l < b.r - 1e-9 && b.l < a.r - 1e-9 && a.t < b.b - 1e-9 && b.t < a.b - 1e-9;
/** HP 條（含護盾條）上緣：`hpBar` 畫在 T × 0.36，護盾條在它上面 3px。 */
const HP_TOP = T * 0.36;

/** 召喚物 `total` 個狀態在縮放 `s` 時的排法（和 `statusRow` 一樣的參數）。 */
function summonLay(total: number, s: number, bomb = false) {
  const n = Math.min(2, total);
  const extra = total > 2;
  const k = kOf(s);
  const kb = summonBadgeScale(s);
  const plusW = compactPlusCount(total) > 0 ? plusTextWidth(compactPlusCount(total)) : 0;
  const lay = summonRowLayout(n, k, summonBadgeOffset({ bomb: bomb ? 2 : null }, T), bottom, extra, false, kb, isCompactRow(s), plusW);
  const shapes = rowShapes(lay, n, k, bottom, extra, lay.compact ? plusW : 0);
  const span = rowSpan(lay, n, k, extra, lay.compact ? plusW : 0);
  return { lay, n, k, kb, plusW, shapes, span, badge: { ...lay.badge, r: badgeOuterR(kb) } };
}

describe("6F-11 第 1 項：800 寬（縮放 ≤ 70%）的狀態列與召喚物回合數徽章", () => {
  it("精簡列只在縮放 ≤ 70% 時：800 寬是，1040、1600 寬不是", () => {
    expect(isCompactRow(S800)).toBe(true);
    expect(isCompactRow(0.7)).toBe(true);
    expect(isCompactRow(S1040)).toBe(false);
    expect(isCompactRow(S1600)).toBe(false);
  });

  it("800 寬：狀態列只顯示 1 個圖示，後面接「+N」（N ＝ 總數 − 1），字不蓋到圖示、不縮成角標", () => {
    for (const total of [2, 3, 4]) {
      const { lay, shapes } = summonLay(total, S800);
      expect(lay.compact, `total=${total}`).toBe(true);
      expect(shapes.circles, `total=${total}`).toHaveLength(0); // 沒有角標
      expect(shapes.boxes, `total=${total}`).toHaveLength(2); // 1 個圖示＋「+N」字
      const [icon, plus] = shapes.boxes as [Box, Box];
      expect(plus.l, `total=${total}`).toBeGreaterThan(icon.r); // 字在圖示右邊、不重疊
      expect(boxesHit(icon, plus)).toBe(false);
      // 一般大小：畫面上的字級和圖示的圖案一樣 ≥ 10px
      expect(ROW_PLUS_FONT * kOf(S800) * S800).toBeGreaterThanOrEqual(10 - 1e-9);
    }
    expect(compactPlusCount(3)).toBe(2);
    expect(compactPlusCount(1)).toBe(0);
    // 只有 1 個狀態：只有圖示，沒有「+N」
    expect(summonLay(1, S800).shapes.boxes).toHaveLength(1);
  });

  it("800 寬：徽章畫面上的半徑 ≥ 7px、數字 ≥ 10px", () => {
    const kb = summonBadgeScale(S800);
    expect(SUMMON_BADGE_RADIUS * kb * S800).toBeGreaterThanOrEqual(7 - 1e-9);
    expect(SUMMON_BADGE_FONT * kb * S800).toBeGreaterThanOrEqual(10 - 1e-9);
  });

  it("800 寬：徽章整顆在格子裡（不壓格線、不跨進隔壁格），和狀態列（含「+N」字與描邊）至少留空隙；狀態列在格子裡、在 HP 條之上", () => {
    for (const total of [0, 1, 2, 3, 4]) {
      const tag = `total=${total}`;
      const kb = summonBadgeScale(S800);
      const at = summonBadgeOffset({ bomb: null }, T);
      const badge = total === 0 ? { ...summonBadgeAlone(at, kb, true), r: badgeOuterR(kb) } : summonLay(total, S800).badge;
      expect(badge.x + badge.r, tag).toBeLessThanOrEqual(T / 2 - 1);
      expect(badge.y - badge.r, tag).toBeGreaterThanOrEqual(-T / 2 + 1);
      expect(badge.x - badge.r, tag).toBeGreaterThanOrEqual(-T / 2 + 1);
      expect(badge.y + badge.r, tag).toBeLessThanOrEqual(T / 2 - 1);
      if (total === 0) continue;
      const { shapes, span } = summonLay(total, S800);
      for (const b of shapes.boxes) {
        expect(circleHitsBox(badge, b, ROW_CORNER_GAP), tag).toBe(false);
        expect(b.b, tag).toBeLessThanOrEqual(HP_TOP);
      }
      expect(span.l, tag).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
      expect(span.r, tag).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
    }
  });

  it("1600 寬照 6F-10b：徽章在原位、2 個圖示＋角標", () => {
    const { lay } = summonLay(3, S1600);
    expect(lay.compact).toBe(false);
    expect(lay.badge).toEqual(summonBadgeOffset({ bomb: null }, T));
    expect(summonBadgeScale(S1600)).toBe(1);
  });

  it("1040 寬：徽章放大後放右上角、整顆在格子裡；2 個狀態照樣 2 個圖示，放不下角標時改成 1 個圖示＋「+N」", () => {
    const two = summonLay(2, S1040);
    expect(two.lay.compact).toBe(false);
    expect(two.lay.badge).toEqual(summonBadgeCorner(two.kb));
    for (const total of [1, 2, 3, 4]) {
      const { badge, shapes, span } = summonLay(total, S1040);
      expect(badge.x + badge.r).toBeLessThanOrEqual(T / 2 - 1);
      expect(badge.y - badge.r).toBeGreaterThanOrEqual(-T / 2 + 1);
      for (const b of shapes.boxes) expect(circleHitsBox(badge, b, ROW_CORNER_GAP), `total=${total}`).toBe(false);
      for (const c of shapes.circles) expect(circleHitsCircle(badge, c, ROW_CORNER_GAP), `total=${total}`).toBe(false);
      expect(span.r).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
      expect(span.l).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
    }
  });

  it("有炸彈（徽章原位往左）時一樣：放大了就到右上角，不重疊", () => {
    for (const s of [S1040, S800])
      for (const total of [1, 2, 3]) {
        const { badge, shapes } = summonLay(total, s, true);
        for (const b of shapes.boxes) expect(circleHitsBox(badge, b, ROW_CORNER_GAP), `s=${s} total=${total}`).toBe(false);
      }
  });
});

describe("6F-11 第 3 項：一般單位的「+N」", () => {
  const plusW = plusTextWidth(2);
  it("1600、1040 寬：2 個圖示＋角標，角標完全在第 2 個圖示外面，整排在格子裡", () => {
    for (const s of [S1600, S1040]) {
      const k = kOf(s);
      const lay = unitRowLayout(2, k, true, false, s, plusW);
      expect(lay.compact, `s=${s}`).toBe(false);
      expect(lay.moreDx, `s=${s}`).toBe(SUMMON_MORE_DX_MAX); // 角標圓（含白邊）左緣剛好貼著圖示右緣
      const { boxes, circles } = rowShapes(lay, 2, k, bottom, true);
      expect(circles).toHaveLength(1);
      for (const b of boxes) expect(circleHitsBox(circles[0]!, b), `s=${s}`).toBe(false);
      const span = rowSpan(lay, 2, k, true);
      expect(span.l).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
      expect(span.r).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
    }
  });

  it("800 寬：照第 1 點，1 個圖示＋一般大小的「+N」字，整組置中、在格子裡", () => {
    const k = kOf(S800);
    const lay = unitRowLayout(2, k, true, false, S800, plusW);
    expect(lay.compact).toBe(true);
    const { boxes, circles } = rowShapes(lay, 2, k, bottom, true, plusW);
    expect(circles).toHaveLength(0);
    expect(boxes).toHaveLength(2);
    expect(boxesHit(boxes[0]!, boxes[1]!)).toBe(false);
    const span = rowSpan(lay, 2, k, true, plusW);
    expect(span.l).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
    expect(span.r).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
    expect(Math.abs(span.l + span.r)).toBeLessThan(1e-6); // 置中
    // 只有 1 個狀態：1 個圖示置中（和 6F-10b 一樣）
    expect(unitRowLayout(1, k, false, false, S800, 0).shift).toBeCloseTo(0);
  });
});

describe("6F-11 第 4 項：徽章數字畫面上至少 10px", () => {
  it("各種縮放：數字 ≥ 10px、半徑 ≥ 7px（地圖夠大時不縮小）", () => {
    for (const s of [1.5, S1600, 1, S1040, S800, 0.5]) {
      const kb = summonBadgeScale(s);
      expect(SUMMON_BADGE_FONT * kb * s, `s=${s}`).toBeGreaterThanOrEqual(MIN_BADGE_FONT_PX - 1e-9);
      expect(SUMMON_BADGE_RADIUS * kb * s, `s=${s}`).toBeGreaterThanOrEqual(7 - 1e-9);
      expect(kb).toBeGreaterThanOrEqual(1);
    }
  });

  it("徽章是自己的標記：applyMarkScale 放大、文字解析度跟著提高；單位圖層裡徽章先套用、狀態列後套用", () => {
    const unit = new Container();
    const row = new Container();
    row.label = STATUS_ROW_LABEL;
    const badge = new Container();
    badge.label = SUMMON_BADGE_LABEL;
    unit.addChild(row, new Container(), badge);
    expect(unitMarksOf(unit)).toEqual([badge, row]);
    const seen: Array<[number, number]> = [];
    registerMark(badge, { base: SUMMON_BADGE_FONT, min: MIN_BADGE_FONT_PX }, [], (k, s) => seen.push([k, s]));
    expect(applyMarkScale(badge, S800, S800)).toBeCloseTo(1 / S800);
    expect(badge.scale.x).toBeCloseTo(1 / S800);
    expect(seen[0]?.[1]).toBe(S800); // 重排拿得到地圖縮放（精簡列要用）
  });

  it("接線：徽章登記成標記、數字粗體加深色描邊；狀態列重排時照縮放算徽章倍率與精簡列；繪製器套用徽章與狀態列", () => {
    const s = sources["render/unitSprite.ts"]!;
    expect(s).toContain("registerMark(c, { base: SUMMON_BADGE_FONT, min: MIN_BADGE_FONT_PX }, [badgeLabel],");
    expect(s).toContain("badgeLabel.style.stroke = { color: 0x000000, width: SUMMON_BADGE_STROKE };");
    expect(s).toContain("label(badgeText, SUMMON_BADGE_FONT, HIGHLIGHT.summon, true)"); // 粗體
    expect(s).toContain("const kb = summonBadgeScale(s);");
    expect(s).toContain("summonRowLayout(shown.length, k, summonBadgeOffset(u, T), bottom, extra > 0, u.marker !== \"\", kb, compact, plusW)");
    expect(s).toContain("apply(unitRowLayout(shown.length, k, extra > 0, u.marker !== \"\", s, plusW))");
    expect(s).toContain("t.style.stroke = { color: 0x000000, width: ROW_PLUS_STROKE };");
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("for (const n of unitMarksOf(unit)) this.scaleMark(n);");
    expect(sources["render/minMark.ts"]).toContain("relayouts.get(node)?.(k, boardScale);");
  });
});

describe("6F-11 第 5 項：世界畫面 6 處黏字（JSX 行首的全形空白被去掉）改用 CSS 間距", () => {
  const raw = Object.fromEntries(readSources().map(([p, t]) => [p, t]));
  it("原始碼掃描：所有 .tsx 不再有「行首（縮排後）是全形空白」的行（JSX 會把它和縮排一起去掉，字就黏在一起）", () => {
    const bad: string[] = [];
    for (const [p, text] of Object.entries(raw)) {
      if (!p.endsWith(".tsx")) continue;
      text.split("\n").forEach((line, i) => {
        if (/^[ \t]*　/.test(line)) bad.push(`${p}:${i + 1}`);
      });
    }
    expect(bad).toEqual([]);
  });

  it("6 處都改成 lead-gap（margin-inline-start），CSS 有這條規則", () => {
    const spots: Array<[string, string]> = [
      ["world/QuestLog.tsx", '<span className="muted small lead-gap">\n                {q.kind_zh}'],
      ["world/QuestLog.tsx", '<span className="muted lead-gap">\n                {t.scope_zh}・{t.expires_zh}'],
      ["world/WorldGrowth.tsx", '<span className="muted small lead-gap">\n            Lv {view.character.level}'],
      ["world/LeaguePanel.tsx", '<span className="muted lead-gap">\n              賽季第 {league.season_day} 天'],
      ["world/BoardPanel.tsx", '<span className={`lead-gap ${board.season_boss.status === "open" ? "world-board-open" : "muted"}`}>\n                  {board.season_boss.status_zh}'],
      ["run/FlashChooser.tsx", '<span className="muted small lead-gap">\n            {slot === null ?'],
    ];
    for (const [p, s] of spots) expect(raw[p], p).toContain(s);
    const css = readFile(SRC_DIR, "styles/base.css");
    expect(/\.lead-gap\s*\{([^}]*)\}/.exec(css)?.[1] ?? "").toMatch(/margin-inline-start:\s*0\.75em/);
  });
});

describe("6F-11 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of [
      "render/rowLayout.ts",
      "render/unitSprite.ts",
      "render/minMark.ts",
      "render/floatStack.ts",
      "render/BattleRenderer.ts",
      "world/QuestLog.tsx",
      "world/WorldGrowth.tsx",
      "world/LeaguePanel.tsx",
      "world/BoardPanel.tsx",
      "run/FlashChooser.tsx",
    ]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});

describe("6F-11 第 2 項：最上排的飄字往下 6～8px、留在戰場上緣以內", () => {
  it("頭頂空間的上限再往下 7px（畫面 px）：1600、1040、800 寬都是 7px", () => {
    expect(FLOAT_TOP_SHIFT_PX).toBeGreaterThanOrEqual(6);
    expect(FLOAT_TOP_SHIFT_PX).toBeLessThanOrEqual(8);
    for (const s of [S1600, S1040, S800]) expect(floatTopShift(s) * s).toBeCloseTo(FLOAT_TOP_SHIFT_PX);
  });

  it("停住時在戰場上緣以內的字，飄到最高也不超出上緣（離上緣不到 pad 的不往上飄）；本來就在上緣外的照舊", () => {
    // 地圖上緣 y = 0、pad 2
    expect(capRise(22, 1.5, 0, 2)).toBe(0); // 最上排的「−7」：停住時離上緣 1.5 → 不往上飄
    expect(capRise(22, 10, 0, 2)).toBe(8); // 離上緣 10 → 最多飄 8，上緣停在 2
    expect(capRise(16, 40, 0, 2)).toBe(16); // 空間夠：照常飄
    expect(capRise(22, -5, 0, 2)).toBe(22); // 第一排的人：字本來就在頭頂預留裡，照舊（6F-10 的上界是畫布上緣）
    for (const top of [0, 0.5, 3, 7, 12, 30]) expect(top - capRise(22, top, 0, 2)).toBeGreaterThanOrEqual(Math.min(top, 2) - 1e-9);
  });

  it("接線：頭頂空間扣掉 floatTopShift；每一組照 capRise 算飄的距離（停住時的上緣含整疊往下推的量）", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("FLOAT_RISE_MAX + FLOAT_EDGE_PAD + floatTopShift(this.scale)");
    expect(r).toContain("capRise(fullRise, this.groupRestTop(first.pos, firstH, heights, placed.offsets) + placed.shiftAt(now), this.mapTopY())");
    expect(r).toContain("offsets.set(i, { offset: placed.offsets[order] ?? 0, firstH, shiftAt: placed.shiftAt, waitMs, order, riseMax })");
  });
});
