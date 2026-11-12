// LW-2b：說明卡上方「現在不能用：…」那一行自帶底色（移植需求 3.7 第 2 條）：和「本場不成立」同一個深藍底，
// 框改琥珀實線、「現在不能用」四個字琥珀粗體；同一張卡兩條都有時「現在不能用」在上。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { NowOffNote } from "../ui/ConditionOffNote";

/** 取出 CSS 裡某個選擇器（逗號分組也算）的宣告區塊。 */
function cssBlocks(css: string, selector: string): string[] {
  const out: string[] = [];
  for (const m of css.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    const sels = m[1]!.split(",").map((s) => s.replace(/\/\*[^]*?\*\//g, "").trim());
    if (sels.includes(selector)) out.push(m[2]!);
  }
  return out;
}

describe("NowOffNote", () => {
  it("沒有原因＝不畫；有原因＝「現在不能用」包粗體", () => {
    expect(renderToStaticMarkup(createElement(NowOffNote, { reason: null }))).toBe("");
    expect(renderToStaticMarkup(createElement(NowOffNote, { reason: undefined }))).toBe("");
    expect(renderToStaticMarkup(createElement(NowOffNote, { reason: "目標超出射程" }))).toBe(
      '<div class="skill-card-reason now-off-note" data-testid="now-off-note"><b>現在不能用</b>：目標超出射程</div>',
    );
  });

  it("接線：技能鈕、種族技、技能小卡都用 NowOffNote，不再各自拼字；技能鈕裡排在 ConditionOffNote 前面", () => {
    const bar = readFile(SRC_DIR, "ui/SkillBar.tsx");
    const tile = readFile(SRC_DIR, "ui/SkillTile.tsx");
    for (const src of [bar, tile]) expect(src).not.toMatch(/>現在不能用：\{/);
    expect(bar.match(/<NowOffNote reason=\{/g)?.length).toBe(2);
    expect(tile.match(/<NowOffNote reason=\{blockedReason\} \/>/g)?.length).toBe(1);
    const now = bar.indexOf("<NowOffNote reason={b.disabledReason} />");
    const cond = bar.indexOf("<ConditionOffNote mark={b.conditionOff} />");
    expect(now).toBeGreaterThan(-1);
    expect(now).toBeLessThan(cond);
  });

  it("CSS：和本場不成立共用深藍底；框改琥珀實線、四個字琥珀粗體", () => {
    const css = readFile(SRC_DIR, "styles/skill-bar.css");
    const shared = cssBlocks(css, ".now-off-note").join("\n");
    expect(cssBlocks(css, ".cond-off-note").join("\n")).toContain("background: var(--ui-navy)");
    expect(shared).toContain("background: var(--ui-navy)");
    expect(shared).toContain("padding: 5px 9px");
    expect(shared).toContain("border-radius: 6px");
    expect(shared).toMatch(/border: 1px solid #e8b45a/);
    const bold = cssBlocks(css, ".now-off-note > b").join("\n");
    expect(bold).toContain("color: #e8b45a");
    expect(bold).toContain("font-weight: 700");
  });
});
