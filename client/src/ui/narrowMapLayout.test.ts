// 6F-8（美術 PM 驗收 RT-3b：docs/archive/art/RT-3b檢查.md 第 2 節的 6 項，只換外觀與顯示）：
// 1. 戰鬥地圖讓開右欄與行動順序列（地圖不能被蓋）；2. 反應詢問的段落 balance；3. 捲到底時下緣漸隱 0；
// 4. 上緣漸隱實色 70%；5. 技能長名卡只縮到放得下、冷卻至少「冷卻 2」；6.（報告，不是程式）。
import { describe, expect, it } from "vitest";
import { MIN_SCALE, fitScale, HUD_COLUMNS, hudSideInsets, scaledSize } from "../battle/stageLayout";
import { type HeightGrid } from "../battle/elevation";
import { MAP_COVER_SELECTORS, mapCoverIssues, type Box } from "../dev/layoutSmoke";
import { readSources, readStyleFiles, stripCssComments, stripTsComments, BATTLE_RENDERER_FILES, battleRendererSource } from "../test/sourceScan";
import { atEndFlag, BOTTOM_FADE_PX, overflowFlag } from "./PopupFrame";
import { abbrevCost, abbrevOrder, COST_LINE_EM, costLines, costPieces, fitCost, keepsCost } from "./skillCost";
import { Container } from "pixi.js";
import { type Action, type SkillCard } from "../api/types";
import { actionHintKind, actionHintText, modeBarHint, reachText } from "../battle/skillTray";
import { emptyTargets, type ActionMode, type TargetSet } from "../battle/targeting";
import { applyMarkScale, markSpecOf, MIN_HEIGHT_BADGE_FONT_PX, MIN_STATUS_GLYPH_PX, minMarkScale, registerMark, STATUS_ROW_LABEL, statusRowOf } from "../render/minMark";
import { ROW_ICON_FEET } from "../render/unitSprite";
import { keepWords, splitKeepWords } from "./keepWords";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
/** 某個選擇器（可以是選擇器清單裡的一個）的規則內容（全部串起來）。 */
function ruleOf(file: string, selector: string): string {
  const re = /([^{}]+)\{([^}]*)\}/g;
  let out = "";
  const text = styles[file] ?? "";
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    if (m[1]!.split(",").map((s) => s.trim()).includes(selector)) out += m[2]!;
  }
  return out;
}

const nodeFs = "node:fs"; // tsc 沒有 node 型別，動態載入
const fs = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: URL, enc: string) => string; readdirSync: (p: URL) => string[] };
const MAPS = new URL("../../../content/maps/", import.meta.url);

/** content/maps 每張地圖的大小與高度（只讀 `size:` 與 `heights:`）。 */
function contentMaps(): [string, HeightGrid][] {
  return fs
    .readdirSync(MAPS)
    .filter((f) => f.endsWith(".yaml"))
    .sort()
    .map((f) => {
      const text = fs.readFileSync(new URL(f, MAPS), "utf8");
      const [w, h] = JSON.parse(/^size: (\[.*\])/m.exec(text)![1]!) as [number, number];
      const rows = /^heights: \|\n((?: +\S+\n)+)/m.exec(text)?.[1]?.trim().split("\n").map((r) => r.trim()) ?? [];
      const tiles = Array.from({ length: w * h }, (_, i) => ({ height: Number(rows[Math.floor(i / w)]?.[i % w] ?? "0") || 0 }));
      return [f, { width: w, height: h, tiles }];
    });
}

/** 三個驗收尺寸的捲動區（地圖可用區）大小：實測 1600×900 → 1600×724、1040×624 → 1040×481、800×600 → 800×405。 */
const BOARDS = [
  { w: 1600, h: 724 },
  { w: 1040, h: 481 },
  { w: 800, h: 405 },
] as const;

/** 模擬 useBoardViewport＋CSS：捲動區加內距，畫布在剩下那一塊置中（`margin: auto`）。 */
function canvasBox(board: { w: number; h: number }, grid: HeightGrid): Box & { scale: number } {
  const ins = hudSideInsets(board.w);
  const scale = fitScale({ width: board.w - ins.left - ins.right - 16, height: board.h - ins.top - 16 }, grid);
  const size = scaledSize(grid, scale);
  const left = ins.left + Math.max(0, (board.w - ins.left - ins.right - size.width) / 2);
  const top = ins.top + Math.max(0, (board.h - ins.top - size.height) / 2);
  return { left, top, right: left + size.width, bottom: top + size.height, scale };
}

/** 疊在地圖上的 HUD 塊（照 battle-hud.css 的欄寬、間距；高度取實測的最大值，右欄整欄、左欄整欄、順序列整條寬）。 */
function hudBoxes(board: { w: number; h: number }): Partial<Record<keyof typeof MAP_COVER_SELECTORS, Box>> {
  const c = HUD_COLUMNS;
  const narrow = board.w < c.narrowBelow;
  const lw = narrow ? c.narrowLeft : c.left;
  const rw = narrow ? c.narrowRight : c.right;
  return {
    hero: { left: c.gap, top: c.gap, right: c.gap + lw, bottom: board.h },
    order: { left: c.gap + lw + c.gap, top: c.gap, right: board.w - rw - 2 * c.gap, bottom: c.top },
    corner: { left: board.w - c.gap - rw, top: c.gap, right: board.w - c.gap, bottom: board.h },
  };
}

describe("第 1 項：自動填滿時地圖讓開左右兩欄與行動順序列（做法 a：安全區算進縮放）", () => {
  it("讓開的寬度：左欄、右欄各加兩邊間距，上方＝行動順序列下緣＋間距；和 CSS 一致", () => {
    expect(hudSideInsets(800)).toEqual({ left: 8 + 230 + 8, right: 8 + 210 + 8, top: 52 + 8 });
    expect(hudSideInsets(1600)).toEqual({ left: 8 + 252 + 8, right: 8 + 224 + 8, top: 60 });
    const hud = styles["styles/battle-hud.css"] ?? "";
    expect(hud).toMatch(new RegExp(`--hud-top: ${HUD_COLUMNS.top}px;`));
    // 順序列高 44（--hud-top 52 ＝ 間距 8 ＋ 44）
    expect(HUD_COLUMNS.top - HUD_COLUMNS.gap).toBe(44);
  });

  it("content/maps 每張地圖、三個尺寸：畫布整張在安全區裡，不碰任何 HUD 欄；縮放不低於下限", () => {
    const maps = contentMaps();
    expect(maps.length).toBeGreaterThanOrEqual(15);
    for (const board of BOARDS) {
      for (const [name, grid] of maps) {
        const box = canvasBox(board, grid);
        const where = `${name} @${board.w}`;
        expect(box.scale, where).toBeGreaterThanOrEqual(MIN_SCALE);
        expect(mapCoverIssues(box, hudBoxes(board)), where).toEqual([]);
        expect(box.bottom, where).toBeLessThanOrEqual(board.h);
      }
    }
  });

  it("RT-3b 的版面（只讓左欄）在 800 寬會被蓋，6F-8 之後不會（open_plain 實測數字）", () => {
    const before = { left: 340, top: 8, right: 707, bottom: 397 };
    const after = { left: 255, top: 68, right: 565, bottom: 397 };
    const hud = { order: { left: 291, top: 8, right: 529, bottom: 52 }, corner: { left: 582, top: 8, right: 792, bottom: 105 }, zoom: { left: 606, top: 369, right: 792, bottom: 397 } };
    expect(mapCoverIssues(before, hud)).toEqual(["order 189×44", "corner 125×97", "zoom 101×28"]);
    expect(mapCoverIssues(after, hud)).toEqual([]);
  });

  it("接線：捲動區上內距、縮放扣掉上方；手動縮放時不讓", () => {
    expect(sources["screens/BattleScreen.tsx"]).toMatch(/paddingTop: board\.insets\.top/);
    expect(sources["screens/battle/useBoardViewport.ts"]).toMatch(/height: boardSize\.height - insets\.top - 16/);
    expect(sources["screens/battle/useBoardViewport.ts"]).toMatch(/layout\.zoom === null && boardSize !== null \? hudSideInsets\(boardSize\.width\) : NO_INSETS/);
  });

  it("排版煙霧檢查量「地圖格不被 HUD 蓋到」：平時一次、選取技能時一次", () => {
    const smoke = sources["dev/layoutSmoke.ts"] ?? "";
    expect(smoke).toContain('result("map-clear"');
    expect(smoke).toContain('result("map-clear-select"');
    expect(smoke).toMatch(/mapCover: collectMapCover\(doc\)/);
    expect(Object.keys(MAP_COVER_SELECTORS)).toEqual(["hero", "mode", "order", "corner", "telegraph", "summon", "pin", "log", "zoom"]);
  });
});

describe("第 2 項：反應詢問的說明句改成 text-wrap: balance（「標示）。」不再單獨一行）", () => {
  it("段落 balance；其他說明句照舊 pretty", () => {
    expect(ruleOf("styles/base.css", ".decision-card p")).toMatch(/text-wrap: balance/);
    expect(ruleOf("styles/base.css", ".decision-card p")).not.toMatch(/pretty/);
    for (const sel of [".op-hint", ".part-tip-text", ".skill-hint"]) expect(ruleOf("styles/base.css", sel), sel).toMatch(/text-wrap: pretty/);
  });
  it("下內距 16px：「拒絕」離框底 ≥ 22px，不壓右下飾件（RT-3b 拿掉漸隱後只剩 20px）", () => {
    const pad = /padding: 12px 16px (\d+)px/.exec(ruleOf("styles/battle-panels.css", ".decision-card"))?.[1];
    expect(Number(pad)).toBeGreaterThanOrEqual(16);
    // 框線 2 ＋ 下內距 ＋ 按鈕列和框底之間 4（實測 RT-3b：12 → 離框底 20）
    expect(2 + Number(pad) + 4 + 2).toBeGreaterThanOrEqual(22);
  });
});

describe("第 3 項：捲到最下面時，下緣漸隱高度 0", () => {
  it("atEndFlag：最後一行到下緣就算到底；扣掉漸隱自己的高度，拿掉漸隱後照樣成立（不來回跳）", () => {
    const ch = 300;
    const sh0 = 500; // 內容本身的高度（不含漸隱）
    // 漸隱在：捲動區高 = 內容 + 32
    expect(atEndFlag(0, ch, sh0 + BOTTOM_FADE_PX, true)).toBe("0");
    expect(atEndFlag(sh0 - ch - 10, ch, sh0 + BOTTOM_FADE_PX, true)).toBe("0");
    expect(atEndFlag(sh0 - ch, ch, sh0 + BOTTOM_FADE_PX, true)).toBe("1"); // 最後一行碰到下緣
    expect(atEndFlag(sh0 - ch + BOTTOM_FADE_PX, ch, sh0 + BOTTOM_FADE_PX, true)).toBe("1"); // 捲到最底
    // 拿掉漸隱後：瀏覽器把 scrollTop 夾回 sh0 − ch，照樣是到底
    expect(atEndFlag(sh0 - ch, ch, sh0, false)).toBe("1");
    // 往上捲一點：不到底，漸隱回來；回來後 scrollTop 不變，條件照樣不成立
    expect(atEndFlag(sh0 - ch - 1.5, ch, sh0, false)).toBe("0");
    expect(atEndFlag(sh0 - ch - 1.5, ch, sh0 + BOTTOM_FADE_PX, true)).toBe("0");
  });

  it("到底時 overflow 照樣是 1（量 overflow 時看漸隱現在有沒有佔高度，不會因為拿掉漸隱就翻成 0）", () => {
    // 內容只超出 10px：漸隱拿掉後 sh = 310
    expect(overflowFlag(310, 300, false)).toBe("1");
    expect(sources["ui/PopupFrame.tsx"]).toMatch(/function fadeShown\(el: HTMLElement\): boolean \{\s*return el\.dataset\.overflow === "1" && el\.dataset\.end !== "1";/);
    expect(sources["ui/PopupFrame.tsx"]).toMatch(/overflowFlag\(el\.scrollHeight, el\.clientHeight, fadeShown\(el\)\)/);
  });

  it("捲動、重量時都標 data-end；CSS 在 data-end=\"1\" 時漸隱高度 0（事件卡、大世界面板、戰鬥詢問視窗）", () => {
    const src = sources["ui/PopupFrame.tsx"] ?? "";
    expect(src).toMatch(/function markScrolled[\s\S]*?markEnd\(el\);/);
    expect(src).toMatch(/function markOverflow[\s\S]*?markEnd\(el\);/);
    for (const sel of [
      '.world-hud-center > .world-event > .ui-popup-body[data-end="1"]::after',
      '.ui-popup-hud > .ui-popup-body[data-end="1"]::after',
      '.ui-popup-dialog > .ui-popup-body[data-end="1"]::after',
    ])
      expect(ruleOf("styles/theme.css", sel), sel).toMatch(/height: 0/);
  });
});

describe("第 4 項：上緣漸隱實色段 70%", () => {
  it("56px，下面 30% 才漸到透明（實色約 39px，被切的那一行整行落在實色裡）", () => {
    for (const sel of [".ui-popup-hud > .ui-popup-body::before", ".ui-popup-dialog > .ui-popup-body::before", ".world-hud-center > .world-event > .ui-popup-body::before"]) {
      const r = ruleOf("styles/theme.css", sel);
      expect(r, sel).toContain("height: 56px");
      // 由下往上：0% 透明 → 15%（離上緣約 48px）70% 不透明 → 30%（約 39px）起實色
      expect(r, sel).toMatch(/linear-gradient\(0deg, rgb\(30 34 54 \/ 0%\), rgb\(30 34 54 \/ 70%\) 15%, var\(--ui-navy\) 30%, var\(--ui-navy\)\)/);
    }
    expect(Math.round(56 * 0.7)).toBe(39);
    // 被切的那一行（頂端在捲動區上緣之外）最多一個行高（事件卡、設定面板 ≤ 30px）：整行落在 39px 實色裡
    expect(30).toBeLessThan(56 * 0.7);
  });
});

describe("第 5 項：技能長名卡只縮到放得下；冷卻至少「冷卻 2」", () => {
  const TRAP = ["AP 2", "法力 5", "冷卻 2 回合"];
  it("冷卻的縮寫是「冷卻 N」（和冷卻中的鈕一致），不再是「冷N」", () => {
    expect(abbrevCost("冷卻 2 回合")).toBe("冷卻 2");
    expect(abbrevCost("冷卻 12")).toBe("冷卻 12");
    expect(keepsCost("冷卻 2")).toBe(true);
  });
  it("縮寫的順序：先冷卻，再從後面往前", () => {
    expect(abbrevOrder(TRAP)).toEqual([2, 1, 0]);
    expect(abbrevOrder(["AP 1", "冷卻 3 回合", "法力 4", "耐力 2"])).toEqual([1, 3, 2, 0]);
  });
  it("一行時：「AP 2・法力 5・冷卻 2」放得下，就不縮 AP 和法力", () => {
    expect(fitCost(TRAP, 1)).toEqual({ parts: ["AP 2", "法力 5", "冷卻 2"], more: false });
    expect(costPieces(fitCost(TRAP, 1)).join("")).toBe("AP 2・法力 5・冷卻 2");
    // 兩行放得下：完全不縮
    expect(fitCost(TRAP, 2)).toEqual({ parts: TRAP, more: false });
    // 再多一段才需要縮法力
    expect(costPieces(fitCost(["AP 2", "法力 12", "冷卻 12 回合"], 1)).join("")).toBe("AP 2・法12・冷卻 12");
  });
  it("任何組合：放得下、有冷卻就一定有「冷卻 N」、沒放不下就不縮", () => {
    const pool = ["AP 1", "AP 3", "法力 12", "耐力 8", "HP 10%", "冷卻 4 回合", "每場 2 次", "源力 2", "傳說啟動", "代價：施放後自己下一個回合少 1 AP（換 10% 預算；代價狀態，無法淨化）"];
    for (let mask = 1; mask < 1 << pool.length; mask += 5) {
      const parts = pool.filter((_, i) => (mask >> i) & 1);
      for (const lines of [1, 2]) {
        const fit = fitCost(parts, lines);
        const text = costPieces(fit).join("");
        expect(costLines(costPieces(fit), COST_LINE_EM, ""), text).toBeLessThanOrEqual(lines);
        if (parts.includes("冷卻 4 回合")) expect(text, text).toMatch(/冷卻 4/);
        if (costLines(parts) <= lines) expect(fit.parts, text).toEqual(parts);
        // 沒拿掉段時：少縮一段就會放不下（只縮到放得下）
        if (!fit.more) {
          const changed = abbrevOrder(parts).filter((i) => fit.parts[i] !== parts[i]);
          if (changed.length > 0) {
            const last = changed[changed.length - 1]!; // 最後縮的那一段
            const lessShort = fit.parts.map((p, i) => (i === last ? parts[i]! : p));
            expect(costLines(lessShort), text).toBeGreaterThan(lines);
          }
        }
      }
    }
  });
});

describe("6F-8 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["battle/stageLayout.ts", "screens/battle/useBoardViewport.ts", "screens/BattleScreen.tsx", "dev/layoutSmoke.ts", "ui/PopupFrame.tsx", "ui/skillCost.ts"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});

// --- 原 fix6f9.test.ts ---
describe("原 fix6f9.test.ts", () => {
// 6F-9（美術 PM 驗收 6F-8：docs/archive/art/6F-8檢查.md 第 2、3 節，只換外觀與顯示）：
// 1. 狀態圖示、高度標記有最小畫面尺寸；3. 選了技能後技能列上方換成該技能的提示；4. 選取面板「Esc／右鍵」不拆、balance。
// （2. 是重拍截圖，不是程式。）

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
    const r = battleRendererSource(sources);
    expect(r).toMatch(/registerMark\(node, \{ base: HEIGHT_BADGE_FONT, min: MIN_HEIGHT_BADGE_FONT_PX \}/);
    expect(r).toContain("this.scaleMarks();");
    // 6F-11：徽章和狀態列一起套用（unitMarksOf：徽章先、狀態列後）
    expect(r.match(/this\.scaleUnitMarks\((sprite|fresh)\)/g)?.length).toBe(2);
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
      "「火焰爆」（射程 4・半徑 1）：點選紅框格子當範圍中心（12 格）；右鍵或 Esc 取消選取。",
    );
    expect(modeBarHint(mode("skill", "捕獸夾", { tiles: tiles(6) }), card({ range: 3 }))).toBe("「捕獸夾」（射程 3）：點選紅框格子當目標格（6 格）；右鍵或 Esc 取消選取。");
    expect(modeBarHint(mode("skill", "射擊", { units: units(1) }), card({ range_weapon: true }))).toContain("（武器射程）");
    expect(modeBarHint(mode("skill", "戰吼", { self: A }), card({}))).toBe("「戰吼」對自身施放：按左側的「施放」；右鍵或 Esc 取消選取。");
    const dir = modeBarHint(mode("skill", "橫掃", { directions: new Map([["north", A]]) }), card({}));
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

  it("「紅框」也不拆（balance 之後 1600 寬曾拆成「紅」「框」）", () => {
    expect(splitKeepWords("點選格子上的目標（紅框 19 個）。")).toEqual(["點選格子上的目標（", "紅框", " ", "19 個", "）。"]);
    expect(splitKeepWords("移動（25 格），冷卻 2 回合")).toEqual(["移動（", "25 格", "），冷卻 ", "2 回合", ""]);
  });

  it("選取面板的說明句用 balance；其他說明句照舊 pretty", () => {
    expect(ruleOf("styles/base.css", ".mode-help .op-hint")).toMatch(/text-wrap: balance/);
    expect(ruleOf("styles/base.css", ".op-hint")).toMatch(/text-wrap: pretty/);
    expect(ruleOf("styles/base.css", ".skill-hint")).toMatch(/text-wrap: pretty/);
  });
});

describe("6F-9 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/minMark.ts", "render/unitSprite.ts", ...BATTLE_RENDERER_FILES, "battle/skillTray.ts", "screens/battle/BattleBottomBar.tsx", "ui/keepWords.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
});
