// 6F-6（巡檢 bug 11）：技能列在 1040、800 寬時不截斷代價、冷卻時按鈕不變窄、長名字縮字或換行。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { SkillButton } from "../battle/targeting";
import { costParts, LONG_NAME_CHARS, SkillBar, skillNameClass, XLONG_NAME_CHARS } from "./SkillBar";

const button = (over: Partial<SkillButton>): SkillButton => ({ skillId: "s", name: "捕獸夾", costs: ["AP 2", "法力 5", "冷卻 2 回合"], cooldown: 0, actions: [], disabledReason: null, ...over });

const nodeFs = "node:fs"; // 同 hudFade.test.ts：tsc 沒有 node 型別，動態載入
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const css = readFileSync("src/styles/skill-bar.css", "utf-8");
/** 取 CSS 裡某個選擇器（完全相同）最後一次出現的規則內容。 */
function lastRule(selector: string): string {
  const re = new RegExp(`(^|\\n)${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`, "g");
  let body = "";
  for (const m of css.matchAll(re)) body = m[2] ?? "";
  return body;
}

describe("6F-6 skill bar text", () => {
  it("the cost line keeps each part whole; on cooldown it is one part", () => {
    expect(costParts(button({}))).toEqual(["AP 2", "法力 5", "冷卻 2 回合"]);
    expect(costParts(button({ cooldown: 2 }))).toEqual(["冷卻 2"]);
    expect(costParts(button({ costs: [] }))).toEqual(["…"]);
  });

  it("long names shrink (more than 6 chars), very long ones shrink again and wrap (more than 9)", () => {
    expect(skillNameClass("捕獸夾")).toBe("skill-name");
    expect(skillNameClass("一".repeat(LONG_NAME_CHARS))).toBe("skill-name");
    expect(skillNameClass("鐵顎深林獵手之夾")).toBe("skill-name long");
    expect(skillNameClass("一".repeat(XLONG_NAME_CHARS))).toBe("skill-name long");
    expect(skillNameClass("灰燼與霜雪交織的鎖鏈陷阱")).toBe("skill-name long xlong");
    // 字數照 Unicode 字元算（不是 UTF-16 長度）
    expect(skillNameClass("𠀋𠀋𠀋𠀋𠀋𠀋")).toBe("skill-name");
  });

  it("renders the parts as unbreakable spans with the dot before the part (RT-3b: a line never ends with ・)", () => {
    const html = renderToStaticMarkup(
      createElement(SkillBar, {
        basic: [],
        buttons: [button({ skillId: "a" }), button({ skillId: "b", name: "灰燼與霜雪交織的鎖鏈陷阱", cooldown: 2 })],
        cards: {},
        selectedKey: null,
        enabled: true,
        hint: "",
        onPickMode: () => undefined,
        onSelect: () => undefined,
      }),
    );
    // RT-3b（6F-7 檢查必修 1）：「・」接在下一段開頭；長名字由程式斷成「灰燼與霜雪交織的／鎖鏈陷阱」
    expect(html).toContain('<span class="skill-cost-part">AP 2</span><span class="skill-cost-part">・法力 5</span><span class="skill-cost-part">・冷卻 2 回合</span>');
    expect(html).toContain('<span class="skill-name long xlong" aria-label="灰燼與霜雪交織的鎖鏈陷阱"><span class="skill-name-line">灰燼與霜雪交織的</span><span class="skill-name-line">鎖鏈陷阱</span></span>');
    expect(html).toContain('<span class="skill-cost"><span class="skill-cost-part">冷卻 2</span></span>');
  });

  it("buttons have a fixed width (a skill going on cooldown does not shift the ones after it); cost wraps to at most 2 lines", () => {
    expect(lastRule(".skill-button")).toMatch(/width:\s*184px/);
    expect(lastRule(".skill-button")).toMatch(/max-width:\s*none/);
    const cost = lastRule(".skill-button .skill-cost");
    expect(cost).toMatch(/flex-wrap:\s*wrap/);
    expect(cost).toMatch(/max-height:\s*26px/);
    expect(cost).toMatch(/white-space:\s*normal/);
    expect(lastRule(".skill-cost-part")).toMatch(/white-space:\s*nowrap/);
    expect(lastRule(".skill-button .skill-name.long")).toMatch(/font-size:\s*12px/);
    expect(lastRule(".skill-button .skill-name.xlong ~ .skill-cost")).toMatch(/max-height:\s*13px/);
  });
});
