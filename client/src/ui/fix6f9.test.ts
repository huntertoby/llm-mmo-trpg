// 6F-9（美術 PM 驗收 6F-8：docs/art/6F-8檢查.md 第 2、3 節，只換外觀與顯示）：
// 1. 狀態圖示、高度標記有最小畫面尺寸；3. 選了技能後技能列上方換成該技能的提示；4. 選取面板「Esc／右鍵」不拆、balance。
// （2. 是重拍截圖，不是程式。）
import { Container } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { Action, SkillCard } from "../api/types";
import { actionHintKind, actionHintText, modeBarHint, reachText } from "../battle/skillTray";
import { emptyTargets, type ActionMode, type TargetSet } from "../battle/targeting";
import { applyMarkScale, markSpecOf, MIN_HEIGHT_BADGE_FONT_PX, MIN_STATUS_GLYPH_PX, minMarkScale, registerMark, STATUS_ROW_LABEL, statusRowOf } from "../render/minMark";
import { ROW_ICON_FEET } from "../render/unitSprite";
import { readSources, readStyleFiles, stripCssComments, stripTsComments } from "../test/sourceScan";
import { keepWords, splitKeepWords } from "./keepWords";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
function ruleOf(file: string, selector: string): string {
  const re = /([^{}]+)\{([^}]*)\}/g;
  let out = "";
  const text = styles[file] ?? "";
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    if (m[1]!.split(",").map((s) => s.trim()).includes(selector)) out += m[2]!;
  }
  return out;
}

const A = { type: "skill" } as unknown as Action;

describe("6F-9 第 1 項：狀態圖示與高度標記的最小顯示尺寸", () => {
  it("倍率：畫面上不到下限時放大到剛好下限，夠大時 1（不縮小）", () => {
    expect(minMarkScale(9, 10, 0.65)).toBeCloseTo(10 / (9 * 0.65));
    expect(9 * 0.65 * minMarkScale(9, 10, 0.65)).toBeCloseTo(10);
    expect(minMarkScale(9, 10, 1.28)).toBe(1); // 1600 寬：和原本一樣
    expect(minMarkScale(10, 10, 1)).toBe(1);
    expect(minMarkScale(10, 10, 0)).toBe(1);
    expect(minMarkScale(0, 10, 0.5)).toBe(1);
  });

  it("下限：狀態圖示的圖案 10px、高度標記的數字 10px", () => {
    expect(MIN_STATUS_GLYPH_PX).toBe(10);
    expect(MIN_HEIGHT_BADGE_FONT_PX).toBe(10);
  });

  it("800 寬（65%）與 1040 寬（80%）：畫面上的大小都到下限；1600 寬（128%）不變", () => {
    const glyph = ROW_ICON_FEET - 2;
    for (const s of [0.5, 0.65, 0.8]) {
      expect(glyph * s * minMarkScale(glyph, MIN_STATUS_GLYPH_PX, s)).toBeGreaterThanOrEqual(MIN_STATUS_GLYPH_PX - 1e-9);
      expect(10 * s * minMarkScale(10, MIN_HEIGHT_BADGE_FONT_PX, s)).toBeGreaterThanOrEqual(MIN_HEIGHT_BADGE_FONT_PX - 1e-9);
    }
    expect(minMarkScale(glyph, MIN_STATUS_GLYPH_PX, 1.28)).toBe(1);
    expect(minMarkScale(10, MIN_HEIGHT_BADGE_FONT_PX, 1.28)).toBe(1);
  });

  it("applyMarkScale：設定節點倍率，文字解析度跟著提高；沒登記的節點不動", () => {
    const node = new Container();
    const text = { destroyed: false, resolution: 1 } as unknown as import("pixi.js").Text;
    registerMark(node, { base: 9, min: 10 }, [text]);
    expect(markSpecOf(node)).toEqual({ base: 9, min: 10 });
    const k = applyMarkScale(node, 0.65, 0.65);
    expect(node.scale.x).toBeCloseTo(k);
    expect(node.scale.y).toBeCloseTo(k);
    expect(text.resolution).toBeCloseTo(0.65 * k);
    expect(applyMarkScale(node, 1.28, 1.28)).toBe(1);
    expect(node.scale.x).toBe(1);
    const other = new Container();
    expect(applyMarkScale(other, 0.65, 0.65)).toBe(1);
    expect(other.scale.x).toBe(1);
  });

  it("statusRowOf：找單位圖層裡標了 status-row 的子節點", () => {
    const unit = new Container();
    expect(statusRowOf(unit)).toBeNull();
    const row = new Container();
    row.label = STATUS_ROW_LABEL;
    unit.addChild(new Container(), row);
    expect(statusRowOf(unit)).toBe(row);
  });

  it("接線：狀態列與高度標記都登記、繪製器在建立與縮放時套用", () => {
    const sprite = sources["render/unitSprite.ts"]!;
    expect(sprite).toContain("row.label = STATUS_ROW_LABEL");
    expect(sprite).toMatch(/registerMark\(row, \{ base: ROW_ICON_FEET - 2, min: MIN_STATUS_GLYPH_PX \}/);
    expect(sprite).toContain("row.pivot.set(0, ROW_ICON_FEET / 2)"); // 往上長，和 HP 條的空隙不變
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toMatch(/registerMark\(node, \{ base: HEIGHT_BADGE_FONT, min: MIN_HEIGHT_BADGE_FONT_PX \}/);
    expect(r).toContain("this.scaleMarks();");
    expect(r.match(/this\.scaleMark\(statusRowOf\((sprite|fresh)\)\)/g)?.length).toBe(2);
  });
});

function mode(kind: ActionMode["kind"], label: string, patch: Partial<TargetSet>): ActionMode {
  return { key: `skill:${label}`, kind, label, skillId: label, actions: [A], targets: { ...emptyTargets(), ...patch } };
}
function card(stats: Partial<SkillCard["stats"]>): Pick<SkillCard, "stats"> {
  return { stats: { ap: 2, cooldown: null, range: null, range_weapon: false, radius: null, size: null, timing: null, costs: [], effects: [], scaling_attrs: [], ...stats } };
}
const units = (n: number) => new Map(Array.from({ length: n }, (_, i) => [`u${i}`, A]));
const tiles = (n: number) => new Map(Array.from({ length: n }, (_, i) => [`${i},0`, A]));

describe("6F-9 第 3 項：選了技能後，技能列上方換成該技能自己的提示", () => {
  const base = { copying: false, canAct: true, ended: false, moveCount: 5, attackCount: 2 };

  it("移動、技能、待機三種狀態的提示不同", () => {
    const moveText = actionHintText(base);
    expect(moveText).toContain("點選藍色格子移動");
    const picked = modeBarHint(mode("skill", "捕獸夾", { tiles: tiles(6) }), card({ range: 3 }));
    const skillText = actionHintText({ ...base, picked });
    expect(skillText).toBe(picked);
    expect(skillText).not.toContain("藍色格子");
    expect(actionHintText({ ...base, canAct: false, picked })).toBe("等待中……");
    expect(actionHintText({ ...base, ended: true, picked })).toBe("戰鬥結束。");
    expect(actionHintText({ ...base, copying: true, picked })).toContain("複製的技能");
  });

  it("選取中的提示每次完整顯示（不收成「?」）；沒選取時照舊是移動說明", () => {
    expect(actionHintKind(base)).toBe("move");
    expect(actionHintKind({ ...base, picked: "x" })).toBeNull();
    expect(actionHintKind({ ...base, picked: null })).toBe("move");
  });

  it("依目標種類與射程、半徑產生", () => {
    expect(modeBarHint(mode("skill", "斬擊", { units: units(2) }), card({ range: 1 }))).toBe("「斬擊」（射程 1）：點選紅框目標（2 個）；右鍵或 Esc 取消選取。");
    expect(modeBarHint(mode("skill", "火焰爆", { tiles: tiles(12) }), card({ range: 4, radius: 1 }))).toBe(
      "「火焰爆」（射程 4・半徑 1）：點選格子當範圍中心（12 格）；右鍵或 Esc 取消選取。",
    );
    expect(modeBarHint(mode("skill", "捕獸夾", { tiles: tiles(6) }), card({ range: 3 }))).toBe("「捕獸夾」（射程 3）：點選格子當目標格（6 格）；右鍵或 Esc 取消選取。");
    expect(modeBarHint(mode("skill", "射擊", { units: units(1) }), card({ range_weapon: true }))).toContain("（武器射程）");
    expect(modeBarHint(mode("skill", "戰吼", { self: A }), card({}))).toBe("「戰吼」對自身施放：按左側的「施放」；右鍵或 Esc 取消選取。");
    const dir = modeBarHint(mode("skill", "橫掃", { directions: new Map([["n", A]]) }), card({}));
    expect(dir).toBe("「橫掃」：選擇方向（主角旁的箭頭格或左側方向鈕）；右鍵或 Esc 取消選取。");
    const both = modeBarHint(mode("skill", "治療", { units: units(2), self: A }), card({ range: 3 }));
    expect(both).toContain("點選紅框目標（2 個），也可以按左側的「施放於自身」");
    const pair = modeBarHint(mode("skill", "投擲", { hurls: new Map([["o1", new Map()]]), pairKind: "hurl" }), card({ range: 3 }));
    expect(pair).toBe("「投擲」（射程 3）分兩段：先點要投擲的物件或人（紅框 1 個），再點落點；右鍵或 Esc 取消選取。");
    expect(modeBarHint(mode("vault", "攀跳", { tiles: tiles(2) }))).toContain("紫色格子");
    expect(modeBarHint(mode("defend", "守護", { self: A, units: units(1) }))).toContain("相鄰的隊友（紅框 1 個）");
    // 每一種都說怎麼取消，都不提「藍色格子移動」
    for (const m of [mode("skill", "a", { units: units(1) }), mode("skill", "b", { self: A }), mode("shove_aside", "c", {})]) {
      const t = modeBarHint(m);
      expect(t).toMatch(/右鍵或 Esc 取消選取。$/);
      expect(t).not.toContain("藍色格子");
    }
  });

  it("reachText", () => {
    expect(reachText(undefined)).toBe("");
    expect(reachText(card({}).stats)).toBe("");
    expect(reachText(card({ range: 4, radius: 2 }).stats)).toBe("射程 4・半徑 2");
    expect(reachText(card({ range: 4, range_weapon: true }).stats)).toBe("武器射程");
    expect(reachText(card({ radius: 0 }).stats)).toBe("");
  });

  it("接線：技能列的提示用選取中的模式與卡片", () => {
    expect(sources["screens/battle/BattleBottomBar.tsx"]).toMatch(/picked: mode === null \? null : modeBarHint\(mode, /);
  });
});

describe("6F-9 第 4 項：選取面板的說明句", () => {
  it("「Esc／右鍵」整組不拆", () => {
    expect(splitKeepWords("點選格子上的目標。Esc／右鍵取消。")).toEqual(["點選格子上的目標。", "Esc／右鍵", "取消。"]);
    const html = renderToStaticMarkup(createElement("div", null, keepWords("點選格子上的目標（紅框 3 個）。Esc／右鍵取消。")));
    expect(html).toContain('<span class="keep-word">Esc／右鍵</span>取消。');
    expect(html).not.toMatch(/<span class="keep-word">Esc<\/span>／/);
  });

  it("選取面板的說明句用 balance；其他說明句照舊 pretty", () => {
    expect(ruleOf("styles/base.css", ".mode-help .op-hint")).toMatch(/text-wrap: balance/);
    expect(ruleOf("styles/base.css", ".op-hint")).toMatch(/text-wrap: pretty/);
    expect(ruleOf("styles/base.css", ".skill-hint")).toMatch(/text-wrap: pretty/);
  });
});

describe("6F-9 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/minMark.ts", "render/unitSprite.ts", "render/BattleRenderer.ts", "battle/skillTray.ts", "screens/battle/BattleBottomBar.tsx", "ui/keepWords.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
