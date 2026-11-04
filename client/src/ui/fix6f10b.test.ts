// 6F-10b（美術 PM 驗收 6F-10：docs/art/6F-10檢查.md 第 3 節，只換外觀與顯示）：
// 1. 推回畫面內的浮動字也照「同一格往上堆疊」錯開；4. 800 寬召喚物的「+N」與回合數徽章；5. 召喚物操控面板名字和 HP 分開。
import { describe, expect, it } from "vitest";
import { FLOAT_SLIDE_MS, FLOAT_STACK_GAP, FloatStack } from "../render/floatStack";
import { FLOAT_RISE_MAX } from "../render/uiAnim";
import { readSources, stripTsComments } from "../test/sourceScan";

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
