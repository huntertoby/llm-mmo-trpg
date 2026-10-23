// 規則句裡的可滑過小段（Phase 3H-5）：標記由後端產生，前端只切段與排版。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { plainRule, RuleText, ruleParts } from "./ruleText";

const LINE = "普攻：1d8＋力量 × 0.3（⟦目前 +4｜實際 4.2，和其他加成合計後才捨去⟧）";

describe("ruleText", () => {
  it("切出標記段（顯示整數、說明寫實際值）", () => {
    expect(ruleParts(LINE)).toEqual([
      { text: "普攻：1d8＋力量 × 0.3（", hint: null },
      { text: "目前 +4", hint: "實際 4.2，和其他加成合計後才捨去" },
      { text: "）", hint: null },
    ]);
  });

  it("純文字還原只留顯示字", () => {
    expect(plainRule(LINE)).toBe("普攻：1d8＋力量 × 0.3（目前 +4）");
    expect(plainRule("沒有標記")).toBe("沒有標記");
  });

  it("排版時顯示整數、不把標記字元印出來", () => {
    const html = renderToStaticMarkup(createElement(RuleText, { text: LINE }));
    expect(html).toContain("目前 +4");
    expect(html).not.toContain("⟦");
    expect(html).not.toContain("4.2");
  });
});
