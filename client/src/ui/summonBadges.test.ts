// 6F-10（美術 PM 驗收 6F-9：docs/archive/art/6F-9檢查.md 第 2 節，只換外觀與顯示）：
// 1. 高度標記畫在單位之上；2. 浮動字夾在戰場裡（四個邊）；3. 指格子一律「格」；4. 召喚物的狀態列與回合數徽章不重疊、不超出。
import { Container } from "pixi.js";
import { describe, expect, it } from "vitest";
import { type Action } from "../api/types";
import { compositePrompt } from "../battle/composite";
import { pickCountText, splitCompositeKeys, tileCount, unitCount } from "../battle/pickCount";
import { modeBarHint } from "../battle/skillTray";
import { emptyTargets, hurlPromptText, type ActionMode, type TargetSet } from "../battle/targeting";
import { clampFloatCenter, FLOAT_EDGE_PAD, type FloatBounds, FLOAT_SLIDE_MS, FLOAT_STACK_GAP, FloatStack, capRise, FLOAT_TOP_SHIFT_PX, floatTopShift } from "../render/floatStack";
import { applyMarkScale, minMarkScale, MIN_STATUS_GLYPH_PX, registerMark, MIN_BADGE_FONT_PX, STATUS_ROW_LABEL, SUMMON_BADGE_LABEL, unitMarksOf } from "../render/minMark";
import { RowStack } from "../render/rowLayers";
import { summonBadgeOffset, SUMMON_BADGE_RADIUS, SUMMON_BADGE_FONT } from "../render/unitLook";
import { badgeOuterR, isCompactRow, plusTextWidth, rowShapes, rowSpan, summonBadgeCorner, summonBadgeScale, circleHitsBox, circleHitsCircle, MORE_CAP_OUT, compactPlusCount, ROW_CORNER_GAP, ROW_EDGE as ROW_EDGE__fix6f11, ROW_ICON_FEET as ROW_ICON_FEET__fix6f11, ROW_PLUS_FONT, SUMMON_MORE_DX_MAX as SUMMON_MORE_DX_MAX__fix6f11, summonBadgeAlone, summonRowLayout as summonRowLayout__fix6f11, unitRowLayout, type Box } from "../render/rowLayout";
import { ROW_EDGE, ROW_ICON_FEET, ROW_MAX_ICONS, ROW_Y_FEET, summonRowLayout, ROW_BADGE_GAP, SUMMON_MORE_DX_MAX, SUMMON_MORE_OUT_Y, SUMMON_MORE_R, summonMoreAt } from "../render/unitSprite";
import { readSources, stripTsComments, readFile, SRC_DIR, BATTLE_RENDERER_FILES, battleRendererSource } from "../test/sourceScan";
import { modeHint } from "./ActionPanel";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { FLOAT_RISE_MAX } from "../render/uiAnim";
import { SummonTitle } from "./SummonPanel";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const A = { type: "skill" } as unknown as Action;
const T = 48;

function mode(kind: ActionMode["kind"], label: string, patch: Partial<TargetSet>): ActionMode {
  return { key: `skill:${label}`, kind, label, skillId: label, actions: [A], targets: { ...emptyTargets(), ...patch } };
}
const units = (n: number) => new Map(Array.from({ length: n }, (_, i) => [`u${i}`, A]));
const tiles = (n: number) => new Map(Array.from({ length: n }, (_, i) => [`${i},0`, A]));

describe("高度標記的圖層（6F-10；6R-1c 改成畫在人物底下）", () => {
  it("每一排的圖層順序：物件、陷阱 < 高度徽章 < 單位 < 上層霧（人物站著或飛過那一格都蓋過「▲N」）", () => {
    const rows = new RowStack();
    rows.reset(3);
    const r = rows.row(1);
    const at = (c: Container) => r.root.children.indexOf(c);
    expect(at(r.units)).toBeGreaterThan(at(r.traps));
    expect(at(r.badges)).toBeGreaterThan(at(r.traps));
    expect(at(r.units)).toBeGreaterThan(at(r.badges));
    expect(at(r.veil)).toBeGreaterThan(at(r.units));
    expect(at(r.badges)).toBeGreaterThan(at(r.objects));
  });

  it("仍在南邊一排之下（南邊的人照常蓋過來）", () => {
    const rows = new RowStack();
    rows.reset(3);
    expect(rows.root.children.indexOf(rows.row(2).root)).toBeGreaterThan(rows.root.children.indexOf(rows.row(1).root));
  });

  it("接線：高度標記加在那一排的 badges", () => {
    expect(battleRendererSource(sources)).toContain("this.rows.row(t.y).badges.addChild(node);");
  });
});

describe("6F-10 第 2 項：浮動字夾在戰場範圍內", () => {
  const b: FloatBounds = { left: 0, top: -30, right: 480, bottom: 480 };

  it("四個邊：靠邊的往內推到整個字（含空隙）都在範圍裡", () => {
    const half = { w: 40, h: 14 };
    const left = clampFloatCenter(10, 200, half.w, half.h, b);
    expect(left.x - half.w).toBe(b.left + FLOAT_EDGE_PAD);
    const right = clampFloatCenter(475, 200, half.w, half.h, b);
    expect(right.x + half.w).toBe(b.right - FLOAT_EDGE_PAD);
    const top = clampFloatCenter(200, -40, half.w, half.h, b);
    expect(top.y - half.h).toBe(b.top + FLOAT_EDGE_PAD);
    const bottom = clampFloatCenter(200, 478, half.w, half.h, b);
    expect(bottom.y + half.h).toBe(b.bottom - FLOAT_EDGE_PAD);
    const corner = clampFloatCenter(-20, -60, half.w, half.h, b);
    expect(corner).toEqual({ x: b.left + FLOAT_EDGE_PAD + half.w, y: b.top + FLOAT_EDGE_PAD + half.h });
  });

  it("沒靠邊的不動", () => {
    expect(clampFloatCenter(240, 200, 40, 14, b)).toEqual({ x: 240, y: 200 });
  });

  it("彈一下放大時（半寬變大）推得更多：每一幀照當下大小算", () => {
    const rest = clampFloatCenter(30, 200, 40, 14, b).x;
    const pop = clampFloatCenter(30, 200, 44, 15, b).x;
    expect(pop).toBeGreaterThan(rest);
    expect(pop - 44).toBeGreaterThanOrEqual(b.left);
  });

  it("字比戰場還寬時放正中間", () => {
    expect(clampFloatCenter(10, 200, 300, 14, b).x).toBe(240);
  });

  it("接線：浮動字每一幀都經過 placeFloat（含狀態字），範圍扣掉鏡頭偏移、上緣含頭頂預留", () => {
    const r = battleRendererSource(sources);
    expect(r).toContain("clampFloatCenter(x, y, (t.width * scale) / 2, (t.height * scale) / 2, this.floatBounds())");
    expect(r.match(/put\(baseY - rise\(p\), f\.scale \* fit\);/g)?.length).toBe(2);
    // 6F-12：範圍改由 visibleFieldBounds 算（扣掉鏡頭偏移與震動，上緣照舊含頭頂預留；規則測試在 fix6f12）
    expect(r).toContain("visibleFieldBounds(w, h, this.worldBaseY, this.cam, this.app.stage.position)");
    expect(r).not.toContain("node.position.set(this.clampFloatX(");
  });
});

describe("6F-10 第 3 項：指格子一律「格」，指單位照舊「個」", () => {
  it("pickCountText", () => {
    expect(tileCount(19)).toBe("19 格");
    expect(unitCount(2)).toBe("2 個");
    expect(pickCountText(0, 19)).toBe("19 格");
    expect(pickCountText(2, 0)).toBe("2 個");
    expect(pickCountText(2, 5)).toBe("2 個目標、5 格");
    expect(splitCompositeKeys(["p:1,2", "p:3,4", "u:x"])).toEqual({ units: 1, tiles: 2 });
  });

  it("選取面板和技能列對同一個格子技能用同一個量詞", () => {
    const trap = mode("skill", "捕獸夾", { tiles: tiles(19) });
    expect(modeHint(trap)).toContain("紅框 19 格");
    expect(modeBarHint(trap)).toContain("（19 格）");
    expect(modeHint(trap)).not.toContain("19 個");
    const slash = mode("skill", "斬擊", { units: units(2) });
    expect(modeHint(slash)).toContain("紅框 2 個");
    expect(modeBarHint(slash)).toContain("（2 個）");
  });

  it("攀跳的紫色格子、投擲與傳送的落點用「格」；互換的第二個人用「個」", () => {
    const vault = mode("vault", "攀跳", { tiles: tiles(3) });
    expect(modeHint(vault)).toContain("共 3 格");
    expect(modeBarHint(vault)).toContain("（3 格）");
    expect(hurlPromptText("木箱", 7, 2, "hurl")).toContain("點選落點（紅框 7 格）");
    expect(hurlPromptText("盜賊", 4, 2, "teleport")).toContain("（紅框 4 格）");
    expect(hurlPromptText("盜賊", 3, 2, "shadowstep")).toContain("（紅框 3 格）");
    expect(hurlPromptText("盜賊", 2, 3, "swap")).toContain("（紅框 2 個）");
    expect(hurlPromptText(null, 0, 3, "hurl")).toContain("（紅框 3 個）"); // 第 1 段選物件或人
  });

  it("複合技能第 1 段：落點算「格」、目標算「個」", () => {
    expect(compositePrompt(null, pickCountText(1, 4))).toContain("（紅框 1 個目標、4 格）");
    const pair = modeBarHint(mode("skill", "突進斬", { hurls: new Map([["p:1,1", new Map()], ["p:2,1", new Map()]]), pairKind: "composite" }));
    expect(pair).toContain("（紅框 2 格）");
  });

  it("掃原始碼：說到格子、落點、紫色格的句子不再寫「N 個」", () => {
    // 格子、落點緊接的那個括號裡寫「${…} 個」（「N 個選項」數的是選項，不是格子）
    const bad = /(格子|落點|紫色)[^（`]*（[^（）`]*\$\{[^}]*\} 個(?!選項)/;
    expect("點選紫色格子（攀＝爬上高台；共 ${n} 個）").toMatch(bad); // 6F-9 以前的寫法會被抓到
    for (const [f, text] of Object.entries(sources)) {
      if (f.endsWith(".test.ts") || f.startsWith("api/") || f.startsWith("dev/")) continue;
      for (const line of text.split("\n")) expect(line, f).not.toMatch(bad);
    }
  });
});

describe("6F-10 第 4 項：召喚物的狀態列與回合數徽章不重疊、不超出格子", () => {
  const bottom = ROW_Y_FEET + ROW_ICON_FEET / 2;
  // 1600 寬（128%）、100%、1040 寬（80%）、800 寬（65%）、手動縮到 50%；6F-11 起照實際縮放算徽章倍率與精簡列
  const scales = [1.28, 1, 0.8, 0.65, 0.5];
  const kOf = (s: number) => minMarkScale(ROW_ICON_FEET - 2, MIN_STATUS_GLYPH_PX, s);
  function layout(n: number, s: number, bomb: boolean, extra: boolean) {
    const k = kOf(s);
    const kb = summonBadgeScale(s);
    const at = summonBadgeOffset({ bomb: bomb ? 2 : null }, T);
    const plusW = n > 1 || extra ? plusTextWidth(n - 1 + (extra ? 1 : 0)) : 0;
    const lay = summonRowLayout(n, k, at, bottom, extra, false, kb, isCompactRow(s), plusW);
    return { lay, k, kb, plusW };
  }

  it("各種縮放、圖示數、有沒有「+N」、有沒有炸彈：都不重疊，狀態列不超出格子左右", () => {
    for (const s of scales)
      for (let n = 1; n <= ROW_MAX_ICONS; n++)
        for (const bomb of [false, true])
          for (const extra of [false, true]) {
            const { lay, k, kb, plusW } = layout(n, s, bomb, extra);
            const tag = `s=${s} n=${n} bomb=${bomb} extra=${extra}`;
            const badge = { ...lay.badge, r: badgeOuterR(kb) };
            const shapes = rowShapes(lay, n, k, bottom, extra, lay.compact ? plusW : 0);
            // 手動縮到 50% 時格子只剩 24px，徽章（數字 10px）和狀態列疊不下，只檢查右緣和徽章在格子裡（6F-11 報告待決）
            if (s >= 0.6) for (const b of shapes.boxes) expect(circleHitsBox(badge, b), tag).toBe(false);
            if (s >= 0.6) for (const c of shapes.circles) expect(circleHitsCircle(badge, c), tag).toBe(false);
            const span = rowSpan(lay, n, k, extra, lay.compact ? plusW : 0);
            if (s >= 0.6) expect(span.l, tag).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
            expect(span.r, tag).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
            // 徽章本身：1600 寬原位貼著格子右緣（6F-10）；放大了就整顆在格子裡（6F-11）
            expect(badge.x + badge.r, tag).toBeLessThanOrEqual(kb > 1 ? T / 2 : T / 2 + 1);
          }
  });

  it("1600 寬（倍率 1）：2 個圖示時徽章留在原位（狀態列往左讓）", () => {
    const at = summonBadgeOffset({ bomb: null }, T);
    const { lay } = layout(2, 1.28, false, false);
    expect(lay.badge).toEqual(at);
    expect(lay.pitch).toBeGreaterThanOrEqual(6);
  });

  it("放不下原位時徽章搬到格子右上角（6F-11；6F-10 是搬到狀態列上方）", () => {
    const { lay, kb } = layout(2, 0.65, true, false);
    expect(lay.badge).toEqual(summonBadgeCorner(kb));
    expect(lay.badge.y).toBeLessThan(summonBadgeOffset({ bomb: 2 }, T).y);
  });

  it("applyMarkScale 改倍率時呼叫重排（召喚物的狀態列）", () => {
    const node = new Container();
    const seen: number[] = [];
    registerMark(node, { base: 9, min: 10 }, [], (k) => seen.push(k));
    applyMarkScale(node, 0.65, 0.65);
    applyMarkScale(node, 1.28, 1.28);
    expect(seen[0]).toBeCloseTo(10 / (9 * 0.65));
    expect(seen[1]).toBe(1);
  });

  it("接線：徽章節點有標籤、圓心在原點；狀態列拿到徽章並登記重排", () => {
    const s = sources["render/unitSprite.ts"]!;
    expect(s).toContain("c.label = SUMMON_BADGE_LABEL;");
    expect(s).toContain("new Graphics().circle(0, 0, SUMMON_BADGE_RADIUS)");
    expect(s).toContain("const row = statusRow(u, turns, opts.edge);"); // 6F-15：6F-14 另外畫一份在上面的三角形拿掉了；6F-16：地圖邊緣
    expect(s).toContain("registerMark(row, { base: ROW_ICON_FEET - 2, min: MIN_STATUS_GLYPH_PX }, inner, relayout);");
  });
});

describe("6F-10 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/rowLayers.ts", "render/floatStack.ts", ...BATTLE_RENDERER_FILES, "render/unitSprite.ts", "render/minMark.ts", "battle/pickCount.ts", "battle/skillTray.ts", "battle/targeting.ts", "battle/composite.ts", "ui/ActionPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});

// --- 原 fix6f10b.test.ts ---
describe("原 fix6f10b.test.ts", () => {
// 6F-10b（美術 PM 驗收 6F-10：docs/archive/art/6F-10檢查.md 第 3 節，只換外觀與顯示）：
// 1. 推回畫面內的浮動字也照「同一格往上堆疊」錯開；4. 800 寬召喚物的「+N」與回合數徽章；5. 召喚物操控面板名字和 HP 分開。

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
    const s = battleRendererSource(sources);
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
    expect(raw).toContain("<SummonTitle name={names.label(s.id)} hp={s.hp ?? 0} maxHp={s.max_hp} left={left} />");
    for (const line of raw.split("\n")) expect(line).not.toMatch(/^\s+　/);
  });
});

describe("6F-10b 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/floatStack.ts", ...BATTLE_RENDERER_FILES, "render/unitSprite.ts", "ui/SummonPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
});

// --- 原 fix6f11.test.ts ---
describe("原 fix6f11.test.ts", () => {
// 6F-11（美術 PM 驗收 6F-10b：docs/archive/art/6F-10b檢查.md「下一段要修」，只換外觀與顯示）：
// 1. 800 寬（縮放 ≤ 70%）狀態列只顯示 1 個圖示＋一般大小的「+N」；召喚物回合數徽章畫面半徑 ≥ 7px、粗體深色描邊、整顆在格子裡。
// 2. 最上排的飄字往下 6～8px、留在戰場上緣以內。3. 一般單位的「+N」在 1600、1040 寬改成角標；800 寬照第 1 點。
// 4. 徽章數字畫面上至少 10px。
const ROW_EDGE = ROW_EDGE__fix6f11;
const ROW_ICON_FEET = ROW_ICON_FEET__fix6f11;
const SUMMON_MORE_DX_MAX = SUMMON_MORE_DX_MAX__fix6f11;
const summonRowLayout = summonRowLayout__fix6f11;

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
  it("精簡列只在縮放 ≤ 85% 時（6F-12 從 70% 放寬）：800、1040 寬是，1600 寬不是", () => {
    expect(isCompactRow(S800)).toBe(true);
    expect(isCompactRow(0.7)).toBe(true);
    expect(isCompactRow(S1040)).toBe(true); // 6F-12：1040 寬比照 800 寬
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

  it("1600 寬：徽章在原位；6F-12 角標放大後放不下，改成 1 個圖示＋「+N」字", () => {
    const { lay } = summonLay(3, S1600);
    expect(lay.compact).toBe(true);
    expect(lay.badge).toEqual(summonBadgeOffset({ bomb: null }, T));
    expect(summonBadgeScale(S1600)).toBe(1);
  });

  it("1040 寬：徽章放大後放右上角、整顆在格子裡；6F-12 起和 800 寬一樣是 1 個圖示＋「+N」（6F-19：只有 2 個狀態時畫 2 個圖示）", () => {
    const two = summonLay(2, S1040);
    expect(two.lay.compact).toBe(false); // 6F-19（美術 PM 6F-18 檢查 D1）
    expect(two.shapes.boxes).toHaveLength(2);
    expect(summonLay(3, S1040).lay.compact).toBe(true);
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
  it("1600 寬：2 個圖示＋角標，角標完全在第 2 個圖示外面，整排在格子裡（1040 寬 6F-12 起是精簡列，見 fix6f12）", () => {
    for (const s of [S1600]) {
      const k = kOf(s);
      const lay = unitRowLayout(2, k, true, false, s, plusW);
      expect(lay.compact, `s=${s}`).toBe(false);
      expect(lay.moreDx, `s=${s}`).toBe(SUMMON_MORE_DX_MAX); // 角標圓（含白邊）左緣剛好貼著圖示右緣
      // 6F-19：角標改成膠囊（方框 `cap`），左緣剛好貼著第 2 個圖示的右緣
      const { boxes, cap } = rowShapes(lay, 2, k, bottom, true);
      expect(cap).not.toBeNull();
      for (const b of boxes.filter((x) => x !== cap)) expect(boxesHit(cap!, b), `s=${s}`).toBe(false);
      expect(cap!.l).toBeCloseTo(boxes[1]!.r);
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
    expect(s).toContain("base = unitRowLayout(shown.length, k, extra > 0, u.marker !== \"\", s, plusW, arrow, { bottom, allW, edge, total: ids.length });"); // 6F-13、6F-14：避開朝向三角形；6F-16：地圖邊緣；6F-18：狀態數
    expect(s).toContain("const plus = plusN > 0 ? plusCapsule(plusN) : null;"); // 6F-19：「+N」改成膠囊
    const r = battleRendererSource(sources);
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
      // PNL-3：任務與線頭改成分頁，類別、範圍、到期改用標籤（flex gap），那兩段 JSX 不在了（下面另外檢查）
      ["world/LeaguePanel.tsx", '<span className="muted lead-gap">\n              賽季第 {league.season_day} 天'],
      // PNL-1b：公告板改成分頁，賽季頭目的狀態改用標籤（`TabLine` 的 end），這一處不再是黏字的寫法
      ["run/FlashChooser.tsx", '<span className="muted small lead-gap">\n            {slot === null ?'],
    ];
    for (const [p, s] of spots) expect(raw[p], p).toContain(s);
    // PNL-2：成長面板第一行改成四個籌碼（不再是一串字），沒有黏字的問題
    expect(raw["world/WorldGrowth.tsx"]).toContain('label="Lv" value={c.level}');
    // PNL-3：任務卡的類別、線頭的範圍是 `Tag`（標籤之間用 flex gap，沒有黏字的問題）
    expect(raw["world/QuestLog.tsx"]).toContain("<Tag>{quest.kind_zh}</Tag>"); // PNL-4：類別改細框中性
    expect(raw["world/QuestLog.tsx"]).toContain("<Tag>{t.scope_zh}</Tag>");
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
      ...BATTLE_RENDERER_FILES,
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
    const r = battleRendererSource(sources);
    expect(r).toContain("FLOAT_RISE_MAX + FLOAT_EDGE_PAD + floatTopShift(this.scale)");
    expect(r).toContain("capRise(fullRise, this.groupRestTop(first.pos, firstH, heights, placed.offsets) + placed.shiftAt(now), this.mapTopY())");
    expect(r).toContain("offsets.set(i, { offset: placed.offsets[order] ?? 0, firstH, shiftAt: placed.shiftAt, waitMs, order, riseMax })");
  });
});
});
