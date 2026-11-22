// HC-8：屬性點的兩句說明改從資料組字（成長面板「升級時每級 +2」、配點教學的範例）。
import { describe, expect, it } from "vitest";
import { gameRules } from "../battle/glossary";
import { allocateExampleText } from "./OpeningDialog";
import { attrPerLevelText, attributeShown } from "./growthPanel";

describe("HC-8 屬性點說明組字", () => {
  it("目前的值：兩句和原本寫死的字逐字相同", () => {
    expect(attrPerLevelText()).toBe("升級時每級 +2");
    expect(allocateExampleText()).toBe(
      "例：兩招看智力和力量 → 開局 4 點各給 2 點（智力 12、力量 12）；升級的 2 點給比較低的那個，一樣高就給第 1 招的 → 智力 14、力量 12。",
    );
  });

  it("數字來自伺服器的規則（量類 ÷ quantity_scale）", () => {
    const r = gameRules();
    expect(r.quantity_scale).toBe(10);
    expect(attributeShown(r.attribute_points_per_level)).toBe(2);
    expect(attributeShown(r.start_free_points)).toBe(4);
    expect(attributeShown(r.base_attribute)).toBe(10);
  });

  it("改過的值（每級 3 點、開局 6 點）：字和例子裡的數字跟著變", () => {
    expect(attrPerLevelText(30, 10)).toBe("升級時每級 +3");
    expect(allocateExampleText({ start: 60, base: 100, perLevel: 30, scale: 10 })).toBe(
      "例：兩招看智力和力量 → 開局 6 點各給 3 點（智力 13、力量 13）；升級的 3 點給比較低的那個，一樣高就給第 1 招的 → 智力 16、力量 13。",
    );
  });

  it("開局點數是奇數：多的給第 1 招（同 recommended_allocation），升級給比較低的那個", () => {
    expect(allocateExampleText({ start: 5, base: 10, perLevel: 2, scale: 1 })).toBe(
      "例：兩招看智力和力量 → 開局 5 點給智力 3 點、力量 2 點（智力 13、力量 12）；升級的 2 點給比較低的那個，一樣高就給第 1 招的 → 智力 13、力量 14。",
    );
  });

  it("量尺 1（不放大）時照原值顯示", () => {
    expect(attrPerLevelText(2, 1)).toBe("升級時每級 +2");
  });
});
