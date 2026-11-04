// 6F-7（美術 PM 驗收 UI-E1b 與 6F-6：docs/art/UI-E1b與6F-6檢查.md 第 3 節）：只換外觀與顯示。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { SkillButton } from "../battle/targeting";
import { FADE_BLOCKS, FADE_SELECTORS } from "../battle/hudFade";
import { percent } from "../battle/previewText";
import { fitScale, HUD_COLUMNS, hudSideInsets } from "../battle/stageLayout";
import { EFFECT_LAYER_ORDER, effectLayerOf } from "../render/effectLayer";
import { COMPLETE_BONUS_PERMILLE, COMPLETE_INTRO } from "../run/flash";
import { HudBarIcon, SNEAK_MOON } from "../world/HudBarIcons";
import { costMaxLines, SkillBar } from "./SkillBar";
import { abbrevCost, COST_LINE_EM, costLines, costPieces, fitCost, keepsCost, textEm } from "./skillCost";

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
  it("縮寫：AP2、法5、冷2；不認得的段照原樣", () => {
    expect(TRAP.map(abbrevCost)).toEqual(["AP2", "法5", "冷2"]);
    expect(abbrevCost("耐力 10")).toBe("耐10");
    expect(abbrevCost("源力 1")).toBe("源1");
    expect(abbrevCost("HP 5%")).toBe("HP5%");
    expect(abbrevCost("每場 2 次")).toBe("每場2");
    expect(abbrevCost("傳說啟動")).toBe("傳說");
    expect(abbrevCost("代價：施放後自己暈眩，到你下個回合結束（換 20% 預算；代價狀態，無法淨化）")).toBe("代價");
    expect(abbrevCost("失手（含自然 1）時：你獲得「暈眩」 1 回合")).toBe("反噬");
    expect(abbrevCost("冷卻 3")).toBe("冷3");
    expect(abbrevCost("某個新段")).toBe("某個新段");
  });

  it("估寬：中文 1em、半形 0.6em、空白 0.3em", () => {
    expect(textEm("法力")).toBe(2);
    expect(textEm("AP 2")).toBeCloseTo(2.1);
    expect(textEm("・")).toBe(1);
  });

  it("兩行放得下就照原樣（6F-6 已驗收的畫面不變）；一行（長名字）時縮寫成「AP2・法5・冷2」", () => {
    expect(costLines(TRAP)).toBe(2);
    expect(fitCost(TRAP, 2)).toEqual({ parts: TRAP, more: false });
    expect(fitCost(TRAP, 1)).toEqual({ parts: ["AP2", "法5", "冷2"], more: false });
    expect(costPieces(fitCost(TRAP, 1)).join("")).toBe("AP2・法5・冷2");
  });

  it("縮寫後還放不下：從後面拿掉不是 AP、冷卻的段，最後一段加「…」；AP 與冷卻一定留著", () => {
    const parts = ["AP 2", "法力 5", "耐力 10", "HP 5%", "代價：施放後自己暈眩", "冷卻 2 回合", "每場 1 次", "源力 1"];
    const fit = fitCost(parts, 1);
    expect(fit.more).toBe(true);
    expect(fit.parts).toContain("AP2");
    expect(fit.parts).toContain("冷2");
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
    expect(html).toContain('<span class="skill-cost-part">AP2</span><span class="skill-cost-part">・法5</span><span class="skill-cost-part">・冷2</span>');
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
    // RT-3b（美術 PM 回覆待決 1）：只讓左欄，右欄 0
    expect(hudSideInsets(800)).toEqual({ left: 246, right: 0 });
    expect(hudSideInsets(1600)).toEqual({ left: 268, right: 0 });
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
    expect(read("src/screens/BattleScreen.tsx")).toMatch(/paddingLeft: board\.insets\.left, paddingRight: board\.insets\.right/);
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

describe("小修 5：工具列 R 鈕（潛行）看得見", () => {
  it("圖示墊淺色圓底；停用時不透明度 0.6", () => {
    const html = renderToStaticMarkup(createElement(HudBarIcon, { k: "R" }));
    expect(html).toContain(`fill="${SNEAK_MOON}"`);
    expect(html.indexOf("sneak-moon")).toBeGreaterThan(0);
    expect(html.indexOf("sneak-moon")).toBeLessThan(html.indexOf("<path")); // 圓底在最下面
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
    const src = read("src/render/BattleRenderer.ts");
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
