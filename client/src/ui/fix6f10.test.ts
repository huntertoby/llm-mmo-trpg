// 6F-10（美術 PM 驗收 6F-9：docs/art/6F-9檢查.md 第 2 節，只換外觀與顯示）：
// 1. 高度標記畫在單位之上；2. 浮動字夾在戰場裡（四個邊）；3. 指格子一律「格」；4. 召喚物的狀態列與回合數徽章不重疊、不超出。
import { Container } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { Action } from "../api/types";
import { compositePrompt } from "../battle/composite";
import { pickCountText, splitCompositeKeys, tileCount, unitCount } from "../battle/pickCount";
import { modeBarHint } from "../battle/skillTray";
import { emptyTargets, hurlPromptText, type ActionMode, type TargetSet } from "../battle/targeting";
import { clampFloatCenter, FLOAT_EDGE_PAD, type FloatBounds } from "../render/floatStack";
import { applyMarkScale, minMarkScale, MIN_STATUS_GLYPH_PX, registerMark } from "../render/minMark";
import { RowStack } from "../render/rowLayers";
import { SUMMON_BADGE_RADIUS, summonBadgeOffset } from "../render/unitLook";
import { ROW_BADGE_GAP, ROW_EDGE, ROW_ICON_FEET, ROW_MAX_ICONS, ROW_MORE_OUT, ROW_Y_FEET, summonRowLayout } from "../render/unitSprite";
import { readSources, stripTsComments } from "../test/sourceScan";
import { modeHint } from "./ActionPanel";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const A = { type: "skill" } as unknown as Action;
const T = 48;

function mode(kind: ActionMode["kind"], label: string, patch: Partial<TargetSet>): ActionMode {
  return { key: `skill:${label}`, kind, label, skillId: label, actions: [A], targets: { ...emptyTargets(), ...patch } };
}
const units = (n: number) => new Map(Array.from({ length: n }, (_, i) => [`u${i}`, A]));
const tiles = (n: number) => new Map(Array.from({ length: n }, (_, i) => [`${i},0`, A]));

describe("6F-10 第 1 項：高度標記畫在單位圖層之上", () => {
  it("每一排的圖層順序：陷阱 < 單位 < 高度徽章 < 上層霧", () => {
    const rows = new RowStack();
    rows.reset(3);
    const r = rows.row(1);
    const at = (c: Container) => r.root.children.indexOf(c);
    expect(at(r.units)).toBeGreaterThan(at(r.traps));
    expect(at(r.badges)).toBeGreaterThan(at(r.units));
    expect(at(r.veil)).toBeGreaterThan(at(r.badges));
    expect(at(r.badges)).toBeGreaterThan(at(r.objects));
  });

  it("仍在南邊一排之下（南邊的人照常蓋過來）", () => {
    const rows = new RowStack();
    rows.reset(3);
    expect(rows.root.children.indexOf(rows.row(2).root)).toBeGreaterThan(rows.root.children.indexOf(rows.row(1).root));
  });

  it("接線：高度標記加在那一排的 badges", () => {
    expect(sources["render/BattleRenderer.ts"]).toContain("this.rows.row(t.y).badges.addChild(node);");
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
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("clampFloatCenter(x, y, (t.width * scale) / 2, (t.height * scale) / 2, this.floatBounds())");
    expect(r.match(/put\(baseY - rise\(p\), f\.scale \* fit\);/g)?.length).toBe(2);
    expect(r).toContain("top: -this.worldBaseY - this.cam.y");
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
  type Box = { l: number; r: number; t: number; b: number };
  const R = SUMMON_BADGE_RADIUS + ROW_BADGE_GAP - 0.5; // 徽章（含外框線 0.5）外再留 1.5px 才算不重疊
  function boxes(n: number, k: number, bomb: boolean, extra: boolean): { row: Box; badge: Box } {
    const at = summonBadgeOffset({ bomb: bomb ? 2 : null }, T);
    const lay = summonRowLayout(n, k, at, bottom, extra, false);
    const half = ((n - 1) * lay.pitch) / 2 + ROW_ICON_FEET / 2;
    const out = extra ? ROW_MORE_OUT : 0;
    return {
      row: { l: lay.shift - k * half, r: lay.shift + k * (half + out), t: bottom - k * (ROW_ICON_FEET + out), b: bottom },
      badge: { l: lay.badge.x - R, r: lay.badge.x + R, t: lay.badge.y - R, b: lay.badge.y + R },
    };
  }
  const overlap = (a: Box, b: Box) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
  // 1600 寬（128%）倍率 1、1040 寬（80%）、800 寬（65%）、手動縮到 50%
  const ks = [1, 0.8, 0.65, 0.5].map((s) => minMarkScale(ROW_ICON_FEET - 2, MIN_STATUS_GLYPH_PX, s));

  it("各種倍率、圖示數、有沒有「+N」、有沒有炸彈：都不重疊，狀態列不超出格子左右", () => {
    for (const k of ks)
      for (let n = 1; n <= ROW_MAX_ICONS; n++)
        for (const bomb of [false, true])
          for (const extra of [false, true]) {
            const { row, badge } = boxes(n, k, bomb, extra);
            const tag = `k=${k.toFixed(2)} n=${n} bomb=${bomb} extra=${extra}`;
            expect(overlap(row, badge), tag).toBe(false);
            expect(row.l, tag).toBeGreaterThanOrEqual(-ROW_EDGE - 1e-9);
            expect(row.r, tag).toBeLessThanOrEqual(ROW_EDGE + 1e-9);
            expect(badge.r - R + SUMMON_BADGE_RADIUS, tag).toBeLessThanOrEqual(T / 2 + 1); // 徽章本身（原本就貼著格子右緣）
          }
  });

  it("1600 寬（倍率 1）與 800 寬（約 1.71）：2 個圖示時徽章留在原位（狀態列往左讓）", () => {
    const at = summonBadgeOffset({ bomb: null }, T);
    for (const k of [ks[0]!, ks[2]!]) {
      const lay = summonRowLayout(2, k, at, bottom, false, false);
      expect(lay.badge).toEqual(at);
      expect(lay.pitch).toBeGreaterThanOrEqual(6);
    }
  });

  it("放不下時徽章搬到狀態列上方", () => {
    const at = summonBadgeOffset({ bomb: 2 }, T);
    const lay = summonRowLayout(2, ks[2]!, at, bottom, false, false);
    expect(lay.badge.y).toBeLessThan(at.y);
    expect(lay.badge.x).toBe(at.x);
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
    expect(s).toContain("const row = statusRow(u, turns);");
    expect(s).toContain("registerMark(row, { base: ROW_ICON_FEET - 2, min: MIN_STATUS_GLYPH_PX }, inner, relayout);");
  });
});

describe("6F-10 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/rowLayers.ts", "render/floatStack.ts", "render/BattleRenderer.ts", "render/unitSprite.ts", "render/minMark.ts", "battle/pickCount.ts", "battle/skillTray.ts", "battle/targeting.ts", "battle/composite.ts", "ui/ActionPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
