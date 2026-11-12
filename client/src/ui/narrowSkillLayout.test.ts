// 6F-7（美術 PM 驗收 UI-E1b 與 6F-6：docs/archive/art/UI-E1b與6F-6檢查.md 第 3 節）：只換外觀與顯示。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { type SkillButton } from "../battle/targeting";
import { FADE_BLOCKS, FADE_SELECTORS } from "../battle/hudFade";
import { percent } from "../battle/previewText";
import { fitScale, HUD_COLUMNS, hudSideInsets } from "../battle/stageLayout";
import { EFFECT_LAYER_ORDER, effectLayerOf } from "../render/effectLayer";
import { COMPLETE_BONUS_PERMILLE, COMPLETE_INTRO } from "../run/flash";
import { HudBarIcon, SNEAK_MOON, HUD_BACKING, HUD_BACKING_EDGE, HUD_BACKING_R, HUD_BAR_ORDER, type HudBarKey } from "../world/HudBarIcons";
import { BAR_ICON_ID } from "../render/hudIcon";
import { setQCanvasFactory } from "../render/qIcon/core";
import * as QH from "../render/qIcon/hud";
import { fakeCanvasFactory, fakeCtx } from "../test/fakeCanvas";
import { costMaxLines, SkillBar, SkillName } from "./SkillBar";
import { abbrevCost, COST_LINE_EM, costLines, costPieces, fitCost, keepsCost, textEm, COST_SEP, NAME_LINE_EM, NAME_MIN_LINE, NAME_TIGHT_LINE_EM, skillNameLines } from "./skillCost";
import { readSources, readStyleFiles, stripCssComments, BATTLE_RENDERER_FILES } from "../test/sourceScan";
import { clampAxis, HUG_GAP } from "../world/camera";
import { keepWords, splitKeepWords } from "./keepWords";
import { BOTTOM_FADE_PX, overflowFlag } from "./PopupFrame";

const nodeFs = "node:fs"; // 同 hudFade.test.ts：tsc 沒有 node 型別，動態載入
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const read = (p: string) => readFileSync(p, "utf-8");

/** 取 CSS 裡某個選擇器（完全相同）最後一次出現的規則內容。 */
function lastRule(css: string, selector: string): string {
  const re = new RegExp(`(^|\\n)${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`, "g");
  let body = "";
  for (const m of css.matchAll(re)) body = m[2] ?? "";
  return body;
}

const LONG = "灰燼與霜雪交織的鎖鏈陷阱";
const TRAP = ["AP 2", "法力 5", "冷卻 2 回合"];

describe("必修 1：技能長名的代價列保留冷卻、不留結尾的「・」", () => {
  it("縮寫：AP2、法5、冷卻 2（6F-8：冷卻最短「冷卻 2」）；不認得的段照原樣", () => {
    expect(TRAP.map(abbrevCost)).toEqual(["AP2", "法5", "冷卻 2"]);
    expect(abbrevCost("耐力 10")).toBe("耐10");
    expect(abbrevCost("源力 1")).toBe("源1");
    expect(abbrevCost("HP 5%")).toBe("HP5%");
    expect(abbrevCost("每場 2 次")).toBe("每場2");
    expect(abbrevCost("傳說啟動")).toBe("傳說");
    expect(abbrevCost("代價：施放後自己暈眩，到你下個回合結束（換 20% 預算；代價狀態，無法淨化）")).toBe("代價");
    expect(abbrevCost("失手（含自然 1）時：你獲得「暈眩」 1 回合")).toBe("反噬");
    expect(abbrevCost("冷卻 3")).toBe("冷卻 3");
    expect(abbrevCost("某個新段")).toBe("某個新段");
  });

  it("估寬：中文 1em、半形 0.6em、空白 0.3em", () => {
    expect(textEm("法力")).toBe(2);
    expect(textEm("AP 2")).toBeCloseTo(2.1);
    expect(textEm("・")).toBe(1);
  });

  it("兩行放得下就照原樣（6F-6 已驗收的畫面不變）；一行（長名字）時只縮到放得下（6F-8：「AP 2・法力 5・冷卻 2」）", () => {
    expect(costLines(TRAP)).toBe(2);
    expect(fitCost(TRAP, 2)).toEqual({ parts: TRAP, more: false });
    expect(fitCost(TRAP, 1)).toEqual({ parts: ["AP 2", "法力 5", "冷卻 2"], more: false });
    expect(costPieces(fitCost(TRAP, 1)).join("")).toBe("AP 2・法力 5・冷卻 2");
  });

  it("縮寫後還放不下：從後面拿掉不是 AP、冷卻的段，最後一段加「…」；AP 與冷卻一定留著", () => {
    const parts = ["AP 2", "法力 5", "耐力 10", "HP 5%", "代價：施放後自己暈眩", "冷卻 2 回合", "每場 1 次", "源力 1"];
    const fit = fitCost(parts, 1);
    expect(fit.more).toBe(true);
    expect(fit.parts).toContain("AP2");
    expect(fit.parts).toContain("冷卻 2");
    expect(costLines(costPieces(fit), COST_LINE_EM, "")).toBeLessThanOrEqual(1);
    const text = costPieces(fit).join("");
    expect(text.endsWith("…")).toBe(true);
    expect(text).not.toMatch(/・…|・$/);
    expect(parts.filter(keepsCost)).toEqual(["AP 2", "冷卻 2 回合"]);
  });

  it("任何組合、任何行數：都放得下、不以「・」結尾、有冷卻就留著冷卻", () => {
    const pool = ["AP 1", "AP 3", "法力 12", "耐力 8", "HP 10%", "冷卻 4 回合", "每場 2 次", "源力 2", "傳說啟動", "代價：施放後自己下一個回合少 1 AP（換 10% 預算；代價狀態，無法淨化）"];
    for (let mask = 1; mask < 1 << pool.length; mask += 7) {
      const parts = pool.filter((_, i) => (mask >> i) & 1);
      for (const lines of [1, 2]) {
        const pieces = costPieces(fitCost(parts, lines));
        const text = pieces.join("");
        expect(costLines(pieces, COST_LINE_EM, ""), text).toBeLessThanOrEqual(lines);
        expect(text.endsWith("・"), text).toBe(false);
        if (parts.includes("冷卻 4 回合")) expect(text, text).toMatch(/冷(卻 )?4/);
      }
    }
    expect(COST_LINE_EM).toBeLessThan(11.3); // 184px 鈕扣掉內距、圖示、間距後約 124px ÷ 11px
  });

  it("技能列：長名字（兩行）時代價一行、縮寫；冷卻中只有「冷卻 N」", () => {
    expect(costMaxLines(LONG)).toBe(1);
    expect(costMaxLines("捕獸夾")).toBe(2);
    const button = (over: Partial<SkillButton>): SkillButton => ({ skillId: "s", name: "捕獸夾", costs: TRAP, cooldown: 0, actions: [], disabledReason: null, ...over });
    const html = renderToStaticMarkup(
      createElement(SkillBar, {
        basic: [],
        buttons: [button({ skillId: "a" }), button({ skillId: "b", name: LONG }), button({ skillId: "c", name: LONG, cooldown: 2 })],
        cards: {},
        selectedKey: null,
        enabled: true,
        hint: "",
        onPickMode: () => undefined,
        onSelect: () => undefined,
      }),
    );
    // RT-3b：「・」接在下一段的開頭（換行點在「・」之前，行尾不留「・」）
    expect(html).toContain('<span class="skill-cost-part">AP 2</span><span class="skill-cost-part">・法力 5</span><span class="skill-cost-part">・冷卻 2 回合</span>');
    expect(html).toContain('<span class="skill-cost-part">AP 2</span><span class="skill-cost-part">・法力 5</span><span class="skill-cost-part">・冷卻 2</span>');
    expect(html).toContain('<span class="skill-cost"><span class="skill-cost-part">冷卻 2</span></span>');
  });
});

describe("必修 2：開發頁的遇敵卡、反應詢問鋪滿視窗（照實際寬度拍）", () => {
  const src = read("src/dev/storyGallery.tsx");
  it("Stage 有 fill：100vw × 100vh；遇敵、反應兩個場景用 fill", () => {
    expect(src).toMatch(/width: fill \? "100vw" : 1040, height: fill \? "100vh" : 720/);
    expect(src).toMatch(/function EncounterScene\(\) \{[\s\S]*?<Stage fill>/);
    expect(src).toMatch(/function ReactionScene\(\) \{[\s\S]*?<Stage fill>/);
  });
});

describe("小修 3：戰鬥 800 寬地圖讓開主角卡與選取說明框；說明框不透明、照框寬換行", () => {
  const hud = read("src/styles/battle-hud.css");
  it("讓開的寬度和 CSS 的欄寬一致（寬、窄視窗）", () => {
    expect(hud).toMatch(new RegExp(`--hud-left-w: ${HUD_COLUMNS.left}px;`));
    expect(hud).toMatch(new RegExp(`--hud-right-w: ${HUD_COLUMNS.right}px;`));
    expect(hud).toMatch(new RegExp(`--hud-gap: ${HUD_COLUMNS.gap}px;`));
    expect(hud).toMatch(new RegExp(`@media \\(width < ${HUD_COLUMNS.narrowBelow}px\\) \\{[\\s\\S]*?--hud-left-w: ${HUD_COLUMNS.narrowLeft}px;[\\s\\S]*?--hud-right-w: ${HUD_COLUMNS.narrowRight}px;`));
    // 6F-8（美術 PM：地圖不能被蓋）：左右兩欄與上方行動順序列都讓開（RT-3b 時右欄是 0）
    expect(hudSideInsets(800)).toEqual({ left: 246, right: 226, top: 60 });
    expect(hudSideInsets(1600)).toEqual({ left: 268, right: 240, top: 60 });
  });
  it("800×600：地圖左緣在主角卡右邊（不再蓋到第一欄）", () => {
    const grid = { width: 10, height: 10 };
    const ins = hudSideInsets(800);
    const avail = { width: 800 - ins.left - ins.right - 16, height: 400 - 16 };
    const s = fitScale(avail, grid);
    const w = 10 * 48 * s;
    const left = ins.left + (800 - ins.left - ins.right - w) / 2;
    expect(left).toBeGreaterThanOrEqual(8 + HUD_COLUMNS.narrowLeft);
    expect(left + w).toBeLessThanOrEqual(800);
  });
  it("手動縮放時不讓（useBoardViewport 只在 zoom 為 null 時加內距）", () => {
    const src = read("src/screens/battle/useBoardViewport.ts");
    expect(src).toMatch(/layout\.zoom === null && boardSize !== null \? hudSideInsets\(boardSize\.width\) : NO_INSETS/);
    expect(read("src/screens/BattleScreen.tsx")).toMatch(/paddingLeft: board\.insets\.left, paddingRight: board\.insets\.right, paddingTop: board\.insets\.top/);
  });
  it("選取說明框不再跟著底下的單位變淡，底色不透明、文字換行", () => {
    expect(FADE_BLOCKS as readonly string[]).not.toContain("mode");
    expect(Object.values(FADE_SELECTORS).join(" ")).not.toContain("mode-panel");
    expect(hud).not.toMatch(/data-hud-faded~="mode"/);
    const rule = lastRule(hud, ".battle-screen.hud-a .bhud-left > .mode-panel");
    expect(rule).toMatch(/background: var\(--ui-navy\);/);
    expect(read("src/styles/theme.css")).toMatch(/--ui-navy: #[0-9a-f]{6};/); // 不透明的色
    expect(rule).toMatch(/box-sizing: border-box;/);
    expect(rule).toMatch(/overflow-wrap: break-word;/);
    expect(rule).toMatch(/white-space: normal;/);
  });
});

describe("小修 4：任務框標題兩行", () => {
  it("任務名最多兩行再加省略號", () => {
    const rule = lastRule(read("src/styles/world-hud.css"), ".world-hud-track .name");
    expect(rule).toMatch(/-webkit-line-clamp: 2;/);
    expect(rule).toMatch(/white-space: normal;/);
  });
});

/** QI-5：功能列圖示畫在假畫布上（35px、res 2）的呼叫紀錄。 */
function barPaintCalls(k: HudBarKey): string[] {
  const log = { calls: [] as string[] };
  setQCanvasFactory(fakeCanvasFactory({ calls: null }));
  try {
    QH.paint(fakeCtx(log), BAR_ICON_ID[k], 35, 2);
  } finally {
    setQCanvasFactory(null);
  }
  return log.calls;
}
/** 圓底（HUD_BACKING）的填色在第一張圖樣貼上之前。 */
function backingBeforeGlyph(k: HudBarKey): boolean {
  const calls = barPaintCalls(k);
  const fill = calls.indexOf(`fillStyle=${HUD_BACKING}`);
  const img = calls.findIndex((c) => c.startsWith("drawImage("));
  return fill >= 0 && img > fill && calls.slice(0, fill).every((c) => !c.startsWith("fill"));
}

describe("小修 5：工具列 R 鈕（潛行）看得見", () => {
  it("圖示墊淺色圓底；停用時不透明度 0.6", () => {
    // QI-5：Q 版 canvas，圓底畫在畫布最底層（先填圓底、再貼圖樣）
    const html = renderToStaticMarkup(createElement(HudBarIcon, { k: "R" }));
    expect(html).toMatch(/<canvas class="hud-icon hud-bar-icon"[^>]*data-bar-icon="R"/);
    expect(backingBeforeGlyph("R")).toBe(true);
    const lum = parseInt(SNEAK_MOON.slice(1, 3), 16) + parseInt(SNEAK_MOON.slice(3, 5), 16) + parseInt(SNEAK_MOON.slice(5, 7), 16);
    expect(lum / 3).toBeGreaterThan(180);
    expect(lastRule(read("src/styles/world-hud.css"), '.world-hud-btn[data-state="disabled"] .hud-bar-icon')).toMatch(/opacity: 0\.6;/);
  });
});

describe("小修 6：路線圖連線在節點圓下層", () => {
  it("節點 z-index 1 疊在連線上面；連線從上一個節點中心畫到這一個節點中心", () => {
    const css = read("src/styles/entry.css");
    expect(css).toMatch(/\n\.run-route-node \{\s*position: relative;\s*z-index: 1;\s*\}/);
    const line = lastRule(css, ".run-route-step + .run-route-step::before");
    expect(line).toMatch(/top: -50%;/);
    expect(line).toMatch(/height: 100%;/);
    expect(line).toMatch(/z-index: 0;/);
  });
});

describe("小修 7：停用的「繼續」、紫色光環", () => {
  it("停用的「繼續」不透明度至少 0.6", () => {
    const rule = lastRule(read("src/styles/entry.css"), ".entry-skin button.entry-continue:disabled");
    const m = /opacity: ([\d.]+);/.exec(rule);
    expect(Number(m?.[1])).toBeGreaterThanOrEqual(0.6);
  });
  it("圖層順序：地上特效 → 狀態光環 → 浮動字", () => {
    expect(EFFECT_LAYER_ORDER).toEqual(["groundFx", "floatRings", "effects"]);
    expect(effectLayerOf({ clip: "map" })).toBe("groundFx");
    expect(effectLayerOf({ layer: "under" })).toBe("floatRings");
    expect(effectLayerOf({})).toBe("effects");
    const src = BATTLE_RENDERER_FILES.map((f) => read(`src/${f}`)).join("\n");
    expect(src).toMatch(/this\.groundMask, \.\.\.EFFECT_LAYER_ORDER\.map\(\(id\) => this\.effectLayer\(id\)\)\);/);
    expect(src).toMatch(/node: ring,[\s\S]{0,120}layer: "under",/);
    expect(src).toMatch(/this\.effectLayer\(effectLayerOf\(e\)\)\.addChild\(e\.node\);/);
  });
});

describe("小修 8：給玩家看的千分比改成百分比（內部照舊千分比）", () => {
  it("四捨五入到一位小數、整數不寫小數", () => {
    expect(percent(120)).toBe("12%");
    expect(percent(125)).toBe("12.5%");
    expect(percent(1)).toBe("0.1%");
    expect(percent(1000)).toBe("100%");
  });
  it("完整技能三選一的說明寫「+12%」", () => {
    expect(COMPLETE_BONUS_PERMILLE).toBe(120);
    expect(COMPLETE_INTRO[0]).toContain("預算 +12%");
    expect(COMPLETE_INTRO.join("")).not.toContain("‰");
  });
  it("技能工坊的複合加成公式不再寫 ‰", () => {
    const src = read("src/ui/workshop/CheckPanel.tsx");
    expect(src).not.toMatch(/\}‰/);
    expect(src).toContain("× (100% ＋ {percent(b.composite_tax_permille)})");
  });
});

// --- 原 rt3b6f7.test.ts ---
describe("原 rt3b6f7.test.ts", () => {
// RT-3b 追加（美術 PM 驗收 6F-7：docs/archive/art/6F-7檢查.md，加上對 6F-7 待決 1、小修 5 的回覆）：
// 戰鬥地圖只讓左欄、工具列所有圖示墊淺色圓底、技能名斷點、代價「・」不留在行尾、戰鬥紀錄跟著左欄收窄、
// 窄視窗室內地圖避開工具列、選取中技能鈕的代價對比、「右鍵」不拆開、反應詢問不留孤字與框底空白。

const styles = Object.fromEntries(readStyleFiles().map(([p, t]) => [p, stripCssComments(t)]));
const sources = Object.fromEntries(readSources());
function ruleOf(file: string, selector: string): string {
  const text = styles[file] ?? "";
  const re = /([^{}]+)\{([^}]*)\}/g;
  let out = "";
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    if (m[1]!.split(",").map((s) => s.trim()).includes(selector)) out += m[2]!;
  }
  return out;
}

/** 照畫面的換行方式排代價（每段不拆、段與段之間換行）：回每一行的字。 */
function rows(pieces: readonly string[], lineEm = COST_LINE_EM): string[] {
  const out: string[] = [];
  let cur = "";
  for (const p of pieces) {
    if (cur !== "" && textEm(cur) + textEm(p) > lineEm) {
      out.push(cur);
      cur = "";
    }
    cur += p;
  }
  if (cur !== "") out.push(cur);
  return out;
}

describe("追加 1：800×600 戰鬥讓開左欄（6F-8 起右欄、上方也讓，見 narrowMapLayout.test.ts）", () => {
  it("左欄照舊讓開", () => {
    expect(hudSideInsets(800).left).toBeGreaterThan(200);
    expect(hudSideInsets(800).right).toBeGreaterThan(200);
  });
});

describe("追加 2／小修 3：工具列所有圖示墊淺色圓底", () => {
  it("每一顆（I K G J Y N R M）最下層都是同一個淺色圓底，圓在 8～40 之內", () => {
    const lum = (parseInt(HUD_BACKING.slice(1, 3), 16) + parseInt(HUD_BACKING.slice(3, 5), 16) + parseInt(HUD_BACKING.slice(5, 7), 16)) / 3;
    expect(lum).toBeGreaterThan(180);
    expect(24 - HUD_BACKING_R).toBeGreaterThanOrEqual(8);
    expect(24 + HUD_BACKING_R).toBeLessThanOrEqual(40);
    // QI-5：Q 版 canvas，每一顆畫布的第一筆填色就是圓底（半徑 15.5/48、細框 HUD_BACKING_EDGE），之後才貼圖樣
    for (const k of HUD_BAR_ORDER) {
      expect(backingBeforeGlyph(k), k).toBe(true);
      expect(barPaintCalls(k), k).toContain(`arc(17.500,17.500,${((HUD_BACKING_R / 48) * 35).toFixed(3)},0.000,${(Math.PI * 2).toFixed(3)})`);
      expect(barPaintCalls(k), k).toContain(`strokeStyle=${HUD_BACKING_EDGE}`);
    }
  });
  it("停用時不透明度 0.6（大世界、鐵匠鋪同一條功能列）", () => {
    expect(ruleOf("styles/world-hud.css", '.world-hud-btn[data-state="disabled"] .hud-bar-icon')).toMatch(/opacity: 0\.6/);
  });
});

describe("必修 1：技能名斷行", () => {
  it("「灰燼與霜雪交織的／鎖鏈陷阱」：斷在「的」後面，最後一行不只剩一個字", () => {
    expect(skillNameLines("灰燼與霜雪交織的鎖鏈陷阱")).toEqual({ lines: ["灰燼與霜雪交織的", "鎖鏈陷阱"], tight: false, cut: false });
    const html = renderToStaticMarkup(createElement(SkillName, { name: "灰燼與霜雪交織的鎖鏈陷阱" }));
    expect(html).toContain('<span class="skill-name-line">鎖鏈陷阱</span>');
    expect(renderToStaticMarkup(createElement(SkillName, { name: "捕獸夾" }))).toBe('<span class="skill-name">捕獸夾</span>');
  });
  it("任何長度：每行放得下、每行至少兩個字；兩行放不下縮字級，再不行加「…」", () => {
    const base = "灰燼與霜雪交織的鎖鏈陷阱之深林獵手古老誓約與雷霆的回聲";
    for (let n = 10; n <= base.length; n++) {
      const name = [...base].slice(0, n).join("");
      const r = skillNameLines(name);
      const em = r.tight ? NAME_TIGHT_LINE_EM : NAME_LINE_EM;
      expect(r.lines.length, name).toBeLessThanOrEqual(2);
      for (const l of r.lines) {
        expect(textEm(l), `${name}：${l}`).toBeLessThanOrEqual(em);
        if (r.lines.length === 2) expect([...l].length, `${name}：${l}`).toBeGreaterThanOrEqual(NAME_MIN_LINE);
      }
      if (r.cut) expect(r.lines[1]!.endsWith("…")).toBe(true);
      else expect(r.lines.join("")).toBe(name);
    }
    expect(skillNameLines(base).cut).toBe(true);
    expect(ruleOf("styles/skill-bar.css", ".skill-button .skill-name.xlong.tight")).toMatch(/font-size: 10px/);
    expect(ruleOf("styles/skill-bar.css", ".skill-button .skill-name.xlong .skill-name-line")).toMatch(/white-space: nowrap/);
  });
  it("代價換成兩行：換行點在「・」之前，行尾不留「・」", () => {
    const parts = ["AP 2", "法力 6", "冷卻 3 回合"];
    const pieces = costPieces(fitCost(parts, 2));
    expect(pieces).toEqual(["AP 2", "・法力 6", "・冷卻 3 回合"]);
    const pool = ["AP 1", "AP 3", "法力 12", "耐力 8", "HP 10%", "冷卻 4 回合", "每場 2 次", "源力 2", "傳說啟動"];
    for (let mask = 1; mask < 1 << pool.length; mask += 5) {
      const ps = pool.filter((_, i) => (mask >> i) & 1);
      for (const lines of [1, 2]) {
        const rs = rows(costPieces(fitCost(ps, lines)));
        expect(rs.length, rs.join("|")).toBeLessThanOrEqual(lines);
        for (const r of rs) expect(r.endsWith(COST_SEP), rs.join("|")).toBe(false);
      }
    }
  });
});

describe("必修 2：戰鬥紀錄跟著左欄收窄", () => {
  it("紀錄、每一條、展開的清單最寬都是左欄寬", () => {
    expect(ruleOf("styles/battle-hud.css", ".battle-screen.hud-a .log-dock")).toMatch(/max-width: var\(--hud-left-w\)/);
    for (const sel of [".battle-screen.hud-a .log-dock > .log-toasts", ".battle-screen.hud-a .log-dock .log-toast", ".battle-screen.hud-a .log-dock .log-dock-panel"]) {
      expect(ruleOf("styles/battle-hud.css", sel), sel).toMatch(/max-width: var\(--hud-left-w\)/);
    }
  });
});

describe("小修 4：窄視窗的室內地圖避開工具列", () => {
  it("比安全區大、但工具列上方放得下：下緣貼在工具列上方（往上對齊）", () => {
    // 800×600 鐵匠鋪：舞台 530、房間 412、上方主角卡 160、下方工具列 44
    const y = clampAxis(530, 412, 250, 160, 44, 24);
    expect(-y + 412).toBe(530 - 44 - HUG_GAP); // 房間下緣在工具列上方，留 HUG_GAP
    expect(-y).toBeGreaterThanOrEqual(0);
    // 空間不夠留 HUG_GAP：少留，但下緣不超過工具列
    expect(-clampAxis(530, 480, 300, 160, 44, 24) + 480).toBeLessThanOrEqual(530 - 44);
    // 主角在房間中下段走動時鏡頭不動（不再捲到工具列底下）
    expect(clampAxis(530, 412, 380, 160, 44, 24)).toBe(y);
    // 主角走到房間最上面、貼齊後會跑進主角卡那一帶：照舊跟著主角（6F-3：主角一定在安全區裡）
    const top = clampAxis(530, 412, 40, 160, 44, 24);
    expect(40 - top - 24).toBeGreaterThanOrEqual(160);
  });
  it("放得進安全區照舊置中；比畫面大照舊跟著主角", () => {
    expect(clampAxis(530, 200, 100, 160, 44)).toBe(-(160 + (530 - 204 - 200) / 2));
    expect(clampAxis(530, 1200, 600, 160, 44)).not.toBe(clampAxis(530, 1200, 900, 160, 44));
    expect(clampAxis(1000, 600, 0)).toBe(-200);
  });
});

describe("小修 5：選取中的技能鈕代價看得清楚", () => {
  const lin = (c: number): number => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const lumOf = (hex: string): number => 0.2126 * lin(parseInt(hex.slice(1, 3), 16)) + 0.7152 * lin(parseInt(hex.slice(3, 5), 16)) + 0.0722 * lin(parseInt(hex.slice(5, 7), 16));
  const contrast = (a: string, b: string): number => {
    const [x, y] = [lumOf(a), lumOf(b)].sort((p, q) => q - p) as [number, number];
    return (x + 0.05) / (y + 0.05);
  };
  it("淺色字在選取的藍底上對比 ≥ 4.5（原本灰字約 2.4）", () => {
    const color = /color: (#[0-9a-f]{6})/.exec(ruleOf("styles/skill-bar.css", ".skill-button.selected .skill-cost"))?.[1] ?? "";
    const bg = /background: (#[0-9a-f]{6})/.exec(ruleOf("styles/base.css", "button.selected"))?.[1] ?? "";
    expect(bg).toBe("#3d5a99");
    expect(contrast(color, bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#9a98a6", bg)).toBeLessThan(3);
  });
});

describe("小修 6：「右鍵」這類操作詞不拆成兩行", () => {
  it("包成不換行的小段；其他字照常可以換行", () => {
    expect(splitKeepWords("Esc／右鍵取消。")).toEqual(["", "Esc／右鍵", "取消。"]); // 6F-9：「Esc／右鍵」整組不拆
    expect(splitKeepWords("右鍵或 Esc 取消。")).toEqual(["", "右鍵", "或 ", "Esc", " 取消。"]);
    const html = renderToStaticMarkup(createElement("div", null, keepWords("點選格子。Esc／右鍵取消。")));
    expect(renderToStaticMarkup(createElement("div", null, keepWords("按右鍵取消。")))).toContain('<span class="keep-word">右鍵</span>');
    expect(html).toContain('<span class="keep-word">Esc／右鍵</span>');
    expect(keepWords("沒有操作詞")).toBe("沒有操作詞");
    expect(ruleOf("styles/base.css", ".keep-word")).toMatch(/white-space: nowrap/);
    for (const f of ["ui/OpHint.tsx", "ui/PartTip.tsx", "ui/SkillBar.tsx"]) expect(sources[f], f).toContain("keepWords(");
  });
});

describe("小修 7：反應詢問不留孤字、框底沒有多餘空白", () => {
  it("說明句不留孤字（6F-8 起反應詢問的段落改成 balance，見 narrowMapLayout.test.ts）", () => {
    expect(ruleOf("styles/base.css", ".decision-card p")).toMatch(/text-wrap: (pretty|balance)/);
  });
  it("內容沒有超出時，下緣漸隱高度 0（原本固定 32px 空白）；量的時候扣掉漸隱自己", () => {
    expect(overflowFlag(200, 300, false)).toBe("0");
    expect(overflowFlag(400, 300, false)).toBe("1");
    expect(overflowFlag(300 + BOTTOM_FADE_PX, 300, true)).toBe("0"); // 只是漸隱自己撐出來的：不算超出
    expect(overflowFlag(301 + BOTTOM_FADE_PX + 1, 300, true)).toBe("1");
    expect(ruleOf("styles/theme.css", '.ui-popup-dialog > .ui-popup-body:not([data-overflow="1"])::after')).toMatch(/height: 0/);
    expect(sources["ui/PopupFrame.tsx"]).toMatch(/<div ref=\{body\} className="ui-popup-body"/);
  });
});
});
