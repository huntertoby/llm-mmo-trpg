// HC-8：屬性點的兩句說明改從資料組字（成長面板「升級時每級 +20」、配點教學的範例）。
// 屬性一律照 ×10 後的原值顯示（玩法 PM 定案，05 5.4.1「開局屬性 100、每級配點 20」）。
import { describe, expect, it } from "vitest";
import { gameRules } from "../battle/glossary";
import { allocateExampleText } from "./OpeningDialog";
import { attrPerLevelText } from "./growthPanel";

describe("HC-8 屬性點說明組字", () => {
  it("目前的值：照原值組字", () => {
    expect(attrPerLevelText()).toBe("升級時每級 +20");
    expect(allocateExampleText()).toBe(
      "例：兩招看智力和力量 → 開局 40 點各給 20 點（智力 120、力量 120）；升級的 20 點給比較低的那個，一樣高就給第 1 招的 → 智力 140、力量 120。",
    );
  });

  it("數字來自伺服器的規則（原值，不換算）", () => {
    const r = gameRules();
    expect(r.attribute_points_per_level).toBe(20);
    expect(r.start_free_points).toBe(40);
    expect(r.base_attribute).toBe(100);
  });

  it("改過的值（每級 30 點、開局 60 點）：字和例子裡的數字跟著變", () => {
    expect(attrPerLevelText(30)).toBe("升級時每級 +30");
    expect(allocateExampleText({ start: 60, base: 100, perLevel: 30 })).toBe(
      "例：兩招看智力和力量 → 開局 60 點各給 30 點（智力 130、力量 130）；升級的 30 點給比較低的那個，一樣高就給第 1 招的 → 智力 160、力量 130。",
    );
  });

  it("開局點數是奇數：多的給第 1 招（同 recommended_allocation），升級給比較低的那個", () => {
    expect(allocateExampleText({ start: 45, base: 100, perLevel: 20 })).toBe(
      "例：兩招看智力和力量 → 開局 45 點給智力 23 點、力量 22 點（智力 123、力量 122）；升級的 20 點給比較低的那個，一樣高就給第 1 招的 → 智力 123、力量 142。",
    );
  });
});
