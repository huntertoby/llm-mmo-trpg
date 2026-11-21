// HC-6b 第 4 項（HC-6a 裁定 1）：許願畫面寫死的「三選一」「三招」改讀 `rules.wish_cards`。
// 目前值 3 組出來和改前逐字相同；張數改成 2、5 時字也通順（中文數字規則見 `ui/rulesText.ts` 的 `countZh`）。
import { describe, expect, it } from "vitest";
import { gameRules } from "../battle/glossary";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { countZh } from "../ui/rulesText";
import { WISH_ZH } from "./wish";

describe("HC-6b 許願張數（wish.ts、WishPanel）", () => {
  it("目前的值（3 張、關鍵字最多 2 個）和改前逐字相同", () => {
    expect(gameRules().wish_cards).toBe(3);
    expect(WISH_ZH.textLead(2)).toBe("用一句話說出想要的力量；池子會從裡面聽出 1～2 個關鍵字，給你三招挑一招。");
    expect(WISH_ZH.menuLead(2)).toBe("挑 1～2 個關鍵字：三招都會帶第 1 個，第 2 個會盡量出現在其中一招。");
    expect(WISH_ZH.gain()).toBe("技能三選一");
    expect(WISH_ZH.refundNote(2)).toBe("三招都不拿也算一次，退回 2 任務幣。");
    expect(WISH_ZH.tagTextLead()).toBe("用一句話說出想要的招式；池子會聽出你要的標籤（關鍵字、元素、效果…），照標籤找三招給你挑。");
    expect(WISH_ZH.tagMenuLead()).toBe("點選想要的標籤（每一類有上限、都可以不選，至少選一個）：池子照標籤找三招給你挑。");
  });

  it("2 張：接量詞寫「兩招」，固定說法寫「二選一」", () => {
    expect(WISH_ZH.textLead(2, 2)).toBe("用一句話說出想要的力量；池子會從裡面聽出 1～2 個關鍵字，給你兩招挑一招。");
    expect(WISH_ZH.menuLead(2, 2)).toBe("挑 1～2 個關鍵字：兩招都會帶第 1 個，第 2 個會盡量出現在其中一招。");
    expect(WISH_ZH.gain(2)).toBe("技能二選一");
    expect(WISH_ZH.refundNote(2, 2)).toBe("兩招都不拿也算一次，退回 2 任務幣。");
    expect(WISH_ZH.tagMenuLead(2)).toContain("照標籤找兩招給你挑。");
  });

  it("5 張", () => {
    expect(WISH_ZH.textLead(2, 5)).toContain("給你五招挑一招。");
    expect(WISH_ZH.menuLead(3, 5)).toBe("挑 1～3 個關鍵字：五招都會帶第 1 個，第 2 個會盡量出現在其中一招。");
    expect(WISH_ZH.gain(5)).toBe("技能五選一");
    expect(WISH_ZH.refundNote(1, 5)).toBe("五招都不拿也算一次，退回 1 任務幣。");
    expect(WISH_ZH.tagTextLead(5)).toContain("照標籤找五招給你挑。");
  });

  it("中文數字規則：0～10 寫中文、超過寫阿拉伯數字；接量詞時 2 寫「兩」", () => {
    expect([1, 2, 3, 4, 5, 10].map((n) => countZh(n))).toEqual(["一", "二", "三", "四", "五", "十"]);
    expect(countZh(2, true)).toBe("兩");
    expect(countZh(4, true)).toBe("四");
    expect(countZh(12)).toBe("12");
  });

  it("許願面板改用這些函式（關鍵字上限照伺服器的 max_keywords）", () => {
    const panel = readFile(SRC_DIR, "world/WishPanel.tsx");
    expect(panel).toContain("WISH_ZH.textLead(w.max_keywords)");
    expect(panel).toContain("WISH_ZH.menuLead(w.max_keywords)");
    expect(panel).toContain("WISH_ZH.tagMenuLead()");
  });
});
