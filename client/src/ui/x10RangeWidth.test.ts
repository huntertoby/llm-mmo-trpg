// X10-3b 第 5 項：範圍變寬（最多 4 位數，例如「130–1060」）。效果數字那一行放不下時整格往下換行，字級不低於 10 px，
// 不用「…」截掉範圍；傷害範圍前面是效果圖示（`damage`），不是骰子圖示（骰子圖示只留給 d20 判定）。
import { describe, expect, it } from "vitest";
import { readStyleFiles, stripCssComments } from "../test/sourceScan";
import { effectLine } from "./skillCardLines";
import type { SkillCard } from "../api/types";
import cards from "./fixtures/skillCards.json";

/** 所有樣式檔裡某個選擇器的宣告（把同一個選擇器出現的每一段接起來）。 */
function rules(selector: string): string {
  const out: string[] = [];
  for (const [, text] of readStyleFiles()) {
    const css = stripCssComments(text);
    const re = /([^{}]+)\{([^{}]*)\}/g;
    for (let m = re.exec(css); m !== null; m = re.exec(css)) {
      if (m[1]!.split(",").some((s) => s.trim() === selector)) out.push(m[2]!);
    }
  }
  return out.join(";");
}

function px(decl: string): number | null {
  const m = /font-size:\s*(\d+)px/.exec(decl);
  return m === null ? null : Number(m[1]);
}

describe("效果數字的寬度", () => {
  it("效果那一行可以換行；範圍本身不截斷", () => {
    expect(rules(".skill-card-effline")).toMatch(/flex-wrap:\s*wrap/);
    for (const sel of [".skill-eff", ".skill-eff-num", ".skill-eff-tag"]) {
      expect(rules(sel)).not.toMatch(/text-overflow|overflow:\s*hidden/);
    }
  });

  it("字級不低於 10 px", () => {
    for (const sel of [".skill-eff", ".skill-eff-tag"]) {
      const size = px(rules(sel));
      expect(size).not.toBeNull();
      expect(size!).toBeGreaterThanOrEqual(10);
    }
  });

  it("傷害範圍前面是傷害圖示，不是骰子", () => {
    const card = cards.skill_ash_harvest as unknown as SkillCard;
    const item = effectLine(card).items[0]!;
    expect(item.icon).toBe("damage");
    expect(item.label).toMatch(/^\d+–\d+$/);
  });
});
