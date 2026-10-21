import { describe, expect, it } from "vitest";
import type { KeywordRef, SkillKeywords } from "../api/types";
import { keywordSide, keywordSummary, noKeywords } from "./keywords";

const ref = (id: string, name: string): KeywordRef => ({ id, name_zh: name, description_zh: `${name}的說明` });

describe("技能的關鍵字顯示", () => {
  it("一邊一個：製造：點燃｜利用：倒地", () => {
    const k: SkillKeywords = { makes: [ref("ignite", "點燃")], uses: [ref("prone", "倒地")] };
    expect(keywordSummary(k)).toBe("製造：點燃｜利用：倒地");
  });

  it("同一邊有多個用頓號連接", () => {
    const k: SkillKeywords = { makes: [ref("ignite", "點燃"), ref("marked", "標記")], uses: [] };
    expect(keywordSummary(k)).toBe("製造：點燃、標記｜利用：無");
  });

  it("兩邊都沒有時兩邊都寫無，並且 noKeywords 為真", () => {
    const k: SkillKeywords = { makes: [], uses: [] };
    expect(keywordSummary(k)).toBe("製造：無｜利用：無");
    expect(noKeywords(k)).toBe(true);
    expect(noKeywords({ makes: [ref("wet", "潮濕")], uses: [] })).toBe(false);
  });

  it("單邊文字", () => {
    expect(keywordSide([])).toBe("無");
    expect(keywordSide([ref("wet", "潮濕"), ref("frozen", "冰凍")])).toBe("潮濕、冰凍");
  });
});
