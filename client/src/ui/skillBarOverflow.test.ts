// 3-28：技能列招數多時按鈕那一排可以捲動（底部區固定高度，不能撐出頁面捲軸）；屬性配點列不再被說明文字擠歪。
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf-8");

function block(selector: string): string {
  const start = css.indexOf(`\n${selector} {`);
  expect(start).toBeGreaterThanOrEqual(0);
  return css.slice(start, css.indexOf("}", start));
}

describe("layout rules (3-28)", () => {
  it("lets the skill button row scroll inside the fixed-height bottom area", () => {
    expect(block(".skill-row")).toContain("overflow-y: auto");
    expect(block(".skill-bar")).toContain("flex-direction: column");
    expect(block(".battle-bottom")).toContain("height: var(--bottom-h");
  });

  it("keeps attribute rows on fixed grid columns with unwrapped labels", () => {
    expect(block(".run-alloc-row")).toContain("grid-template-columns");
    expect(block(".run-alloc-name")).toContain("white-space: nowrap");
    expect(block(".run-alloc-hp")).toContain("grid-column");
  });
});
