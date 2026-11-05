// 6F-10b（美術 PM 驗收 6F-10：docs/art/6F-10檢查.md 第 3 節，只換外觀與顯示）：
// 1. 推回畫面內的浮動字也照「同一格往上堆疊」錯開；4. 800 寬召喚物的「+N」與回合數徽章；5. 召喚物操控面板名字和 HP 分開。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { FLOAT_SLIDE_MS, FLOAT_STACK_GAP, FloatStack } from "../render/floatStack";
import { minMarkScale, MIN_STATUS_GLYPH_PX } from "../render/minMark";
import { FLOAT_RISE_MAX } from "../render/uiAnim";
import { SUMMON_BADGE_RADIUS, summonBadgeOffset } from "../render/unitLook";
import { isCompactRow, plusTextWidth, rowSpan, summonBadgeCorner, summonBadgeScale, MORE_CAP_OUT } from "../render/rowLayout";
import { ROW_BADGE_GAP, ROW_EDGE, ROW_ICON_FEET, ROW_Y_FEET, SUMMON_MORE_DX_MAX, SUMMON_MORE_OUT_Y, SUMMON_MORE_R, summonMoreAt, summonRowLayout } from "../render/unitSprite";
import { readFile, readSources, SRC_DIR, stripTsComments } from "../test/sourceScan";
import { SummonTitle } from "./SummonPanel";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));

/** 一組字停住時（還沒飄）每個字的下緣、上緣（從頭頂線往上算）。 */
function spans(heights: readonly number[], offsets: readonly number[], shift: number): Array<{ lo: number; hi: number }> {
  const c0 = (heights[0] ?? 0) / 2;
  return heights.map((h, i) => {
    const c = c0 + (offsets[i] ?? 0) - shift;
    return { lo: c - h / 2, hi: c + h / 2 };
  });
}
const disjoint = (a: { lo: number; hi: number }, b: { lo: number; hi: number }) => a.hi <= b.lo + 1e-9 || b.hi <= a.lo + 1e-9;

describe("6F-10b 第 1 項：推回畫面內的浮動字也照同一格往上堆疊錯開", () => {
  // 主角在左緣 (0,3) 撞到地圖邊緣兩次：「撞擊！」（放大字，較高）＋「−3」，接著「撞擊！」＋「−7」
  const BIG = 36;
  const NUM = 28;

  it("兩組的第一個字高度不同時也對得齊：舊組（含飄高）和新組之間照樣留空隙", () => {
    const st = new FloatStack();
    const a = st.placeGroup("0,3", 0, 900, [NUM, BIG]);
    const b = st.placeGroup("0,3", 300, 1200, [BIG, NUM]);
    const old = spans([NUM, BIG], a.offsets, 0).map((s) => ({ lo: s.lo + FLOAT_RISE_MAX, hi: s.hi + FLOAT_RISE_MAX })); // 舊組飄到最高
    const neu = spans([BIG, NUM], b.offsets, 0);
    for (const o of old) for (const n of neu) expect(disjoint(o, n)).toBe(true);
    expect((neu[0]?.lo ?? 0) - (old[1]?.hi ?? 0)).toBeCloseTo(FLOAT_STACK_GAP, 9);
  });

  it("頭頂放不下時這一格整疊一起往下推：舊組滑到和新組一樣的位置，同一格的字都不重疊、都在範圍內", () => {
    for (const room of [60, 100, 140]) {
      const st = new FloatStack();
      const a = st.placeGroup("0,3", 0, 2000, [BIG, NUM], room);
      const b = st.placeGroup("0,3", 500, 2500, [BIG, NUM], room);
      expect(b.waitMs).toBe(FLOAT_SLIDE_MS); // 舊組要滑下來：新組等它滑完才出現
      const after = 500 + FLOAT_SLIDE_MS;
      expect(a.shiftAt(after)).toBeCloseTo(b.shiftAt(after), 9);
      // 滑完以後：舊組飄到最高、新組剛出現（還沒飄），兩組四個字彼此不重疊
      const old = spans([BIG, NUM], a.offsets, a.shiftAt(after)).map((s) => ({ lo: s.lo + FLOAT_RISE_MAX, hi: s.hi + FLOAT_RISE_MAX }));
      const neu = spans([BIG, NUM], b.offsets, b.shiftAt(after));
      const all = [...old, ...neu];
      for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++) expect(disjoint(all[i]!, all[j]!), `room=${room} ${i}/${j}`).toBe(true);
      // 新組停住時的上緣剛好在 room（放得下的就不推）
      expect(Math.max(...neu.map((s) => s.hi))).toBeLessThanOrEqual(room + 1e-9);
    }
  });

  it("滑動途中舊組從原位平順滑下來，新組一開始就在推過的位置", () => {
    const st = new FloatStack();
    const a = st.placeGroup("0,3", 0, 2000, [BIG, NUM], 80);
    const before = a.shiftAt(400);
    const b = st.placeGroup("0,3", 400, 2400, [BIG, NUM], 80);
    const target = b.shiftAt(400);
    expect(target).toBeGreaterThan(before);
    expect(a.shiftAt(400)).toBeCloseTo(before, 9);
    const mid = a.shiftAt(400 + FLOAT_SLIDE_MS / 2);
    expect(mid).toBeGreaterThan(before);
    expect(mid).toBeLessThan(target);
    expect(a.shiftAt(400 + FLOAT_SLIDE_MS)).toBeCloseTo(target, 9);
  });

  it("放得下時不推、不等；另一格不受影響；舊字播完後從頭算", () => {
    const st = new FloatStack();
    const a = st.placeGroup("2,2", 0, 900, [NUM], 500);
    const b = st.placeGroup("2,2", 300, 1200, [NUM], 500);
    expect([a.shiftAt(300), b.shiftAt(300), b.waitMs]).toEqual([0, 0, 0]);
    expect(b.offsets[0]).toBe(NUM + FLOAT_RISE_MAX + FLOAT_STACK_GAP);
    const c = st.placeGroup("3,2", 300, 1200, [NUM], 10);
    expect(c.shiftAt(300)).toBe(NUM - 10);
    expect(a.shiftAt(300)).toBe(0);
    expect(st.placeGroup("2,2", 1300, 2000, [NUM], 500).offsets).toEqual([0]);
  });

  it("接線：每一格的字照頭頂空間放（floatRoom），每一幀加上整疊往下推的量，新組照 waitMs 延後出現", () => {
    const s = sources["render/BattleRenderer.ts"]!;
    expect(s).toContain("this.floatStack.placeGroup(k, now, now + durationMs, heights, room)");
    expect(s).toContain("this.floatRoom(first.pos)");
    expect(s).toContain("floatBaseY(c.y, this.floatTopY(item.pos), at.firstH, 0) - at.offset");
    expect(s).toContain("y + at.shiftAt(this.realClock)");
    expect(s).toContain("const delay = at.waitMs + delayFrac * (durationMs - at.waitMs);");
    expect(s).toContain("this.floatBounds().top + FLOAT_RISE_MAX + FLOAT_EDGE_PAD");
  });
});

describe("6F-10b 第 4 項：800 寬召喚物的「+N」角標與回合數徽章", () => {
  const T = 48;
  const bottom = ROW_Y_FEET + ROW_ICON_FEET / 2;
  // 1600 寬（128%）、100%、1040 寬（80%）、800 寬（65%）、手動縮到 50%
  const scales = [1.28, 1, 0.8, 0.65, 0.5];
  const kOf = (s: number) => minMarkScale(ROW_ICON_FEET - 2, MIN_STATUS_GLYPH_PX, s);
  const k800 = kOf(0.65);

  /** 「+N」角標（含白邊）蓋到第 2 個圖示的面積占圖示的比例（數值積分，0.1px 格點）。 */
  function moreCover(dx: number): number {
    const half = ROW_ICON_FEET / 2;
    const m = summonMoreAt(0, dx);
    const r = SUMMON_MORE_R + 0.5;
    let hit = 0;
    let all = 0;
    for (let x = -half; x < half; x += 0.1)
      for (let y = -half; y < half; y += 0.1) {
        all++;
        if ((x - m.x) ** 2 + (y - m.y) ** 2 <= r * r) hit++;
      }
    return hit / all;
  }

  it("「+N」不蓋到前一個圖示：放得下時完全不重疊（1600 寬約 2%）；800 寬 6F-11 起改成精簡列（fix6f11）", () => {
    const old = (() => {
      // 6F-10 的位置：圓心在圖示右上角往左下 2px、半徑 4.5（含白邊 5）
      const half = ROW_ICON_FEET / 2;
      let hit = 0;
      let all = 0;
      for (let x = -half; x < half; x += 0.1)
        for (let y = -half; y < half; y += 0.1) {
          all++;
          if ((x - (half - 2)) ** 2 + (y - (-half + 2)) ** 2 <= 25) hit++;
        }
      return hit / all;
    })();
    expect(old).toBeGreaterThan(0.12);
    expect(moreCover(SUMMON_MORE_DX_MAX)).toBe(0);
    const at = summonBadgeOffset({ bomb: null }, T);
    const lay1600 = summonRowLayout(2, kOf(1.28), at, bottom, true, false);
    // 6F-12：角標放大（半徑 5.5）後，1600 寬召喚物放不到完全在圖示外，改成 1 個圖示＋一般大小的「+N」字（不蓋圖示）
    expect(lay1600.compact).toBe(true);
    expect(lay1600.badge).toEqual(at);
    const lay800 = summonRowLayout(2, k800, at, bottom, true, false, summonBadgeScale(0.65), isCompactRow(0.65));
    expect(lay800.compact).toBe(true);
  });

  it("1600 寬：角標加進寬度後，狀態列仍在格子裡、和原位的徽章不重疊（其他縮放見 fix6f10、fix6f11）", () => {
    const R = SUMMON_BADGE_RADIUS + ROW_BADGE_GAP - 0.5;
    for (const s of [1.28, 1])
      for (const bomb of [false, true])
        for (const n of [1, 2]) {
          const k = kOf(s);
          const at = summonBadgeOffset({ bomb: bomb ? 2 : null }, T);
          const lay = summonRowLayout(n, k, at, bottom, true, false);
          const half = lay.compact ? ROW_ICON_FEET / 2 : ((n - 1) * lay.pitch) / 2 + ROW_ICON_FEET / 2;
          // 6F-12：放不下角標時是精簡列（1 個圖示＋「+N」字），右緣用 rowSpan 算
          const right = lay.compact ? rowSpan(lay, n, k, true, plusTextWidth(n)).r : lay.shift + k * (half + lay.moreDx + MORE_CAP_OUT);
          const tag = `s=${s} bomb=${bomb} n=${n}`;
          expect(lay.shift - k * half, tag).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-6);
          expect(right, tag).toBeLessThanOrEqual(ROW_EDGE + 1e-6);
          const rowTop = bottom - k * (ROW_ICON_FEET + SUMMON_MORE_OUT_Y);
          const apart = right <= lay.badge.x - R + 1e-6 || rowTop >= lay.badge.y + R - 1e-6;
          expect(apart, tag).toBe(true);
        }
    void scales;
  });

  it("800 寬：徽章放到格子右上角、整顆在格子裡（6F-11 取代 6F-10b 的「靠右緣、壓出 3px」）；1600 寬照舊在原位", () => {
    const at = summonBadgeOffset({ bomb: null }, T);
    const kb = summonBadgeScale(0.65);
    const lay = summonRowLayout(2, k800, at, bottom, true, false, kb, true);
    expect(lay.badge).toEqual(summonBadgeCorner(kb));
    expect(summonRowLayout(2, kOf(1.28), at, bottom, true, false).badge).toEqual(at);
  });

  it("接線：「+N」角標用 SUMMON_MORE_R 與 summonMoreAt，重排時照 moreDx 搬（6F-11 起一般單位也用）", () => {
    const s = sources["render/unitSprite.ts"]!;
    // 6F-19：角標改成「+N」膠囊（左緣 ＝ 圖示右緣 ＋ moreDx − SUMMON_MORE_DX_MAX，排法見 rowLayout 的 moreCapBox）
    expect(s).toContain("const more = extra > 0 ? plusCapsule(extra) : null;");
    expect(s).toContain("const m = moreCapBox(x0 + (n - 1) * lay.pitch, lay.moreDx, extra);");
  });
});

describe("6F-10b 第 5 項：召喚物操控面板的名字和 HP 分開", () => {
  it("名字和 HP 是兩個元素，HP 那段不靠行首空白（JSX 會吃掉），CSS 用 column-gap 隔開", () => {
    const html = renderToStaticMarkup(createElement(SummonTitle, { name: "骷髏戰士1", hp: 46, maxHp: 46, left: 3 }));
    expect(html).toBe('<div class="summon-title"><b>骷髏戰士1</b><span class="muted small summon-title-hp">HP 46/46・剩 3 輪</span></div>');
    expect(renderToStaticMarkup(createElement(SummonTitle, { name: "石像", hp: 9, maxHp: 30, left: null }))).toContain(">HP 9/30</span>");
    const css = readFile(SRC_DIR, "styles/battle-panels.css");
    const rule = /\.summon-title\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(rule).toContain("display: flex");
    expect(rule).toMatch(/column-gap:\s*0\.75em/);
  });

  it("接線：操控面板每一隻都用 SummonTitle；SummonPanel 不再有行首全形空白的 JSX 文字", () => {
    const raw = readSources().find(([p]) => p === "ui/SummonPanel.tsx")?.[1] ?? "";
    expect(raw).toContain("<SummonTitle name={names.label(s.id)} hp={s.hp} maxHp={s.max_hp} left={left} />");
    for (const line of raw.split("\n")) expect(line).not.toMatch(/^\s+　/);
  });
});

describe("6F-10b 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/floatStack.ts", "render/BattleRenderer.ts", "render/unitSprite.ts", "ui/SummonPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
