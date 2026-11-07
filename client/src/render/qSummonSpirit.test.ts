// QK-3b（docs/art/QK-3檢查.md、QK-3 待決 4）：元素之靈——火冰雷水以外的元素不再畫成火靈。
import { describe, expect, it } from "vitest";
import { GLYPH } from "./statusIcon";
import { SPIRIT_GLYPH, spiritKind } from "./qSummon";
import { SUMMON_KEYWORDS } from "./summonArt";

describe("元素之靈的樣子", () => {
  it("火冰雷水照四套專屬畫法、沒有頭頂圖示", () => {
    expect(spiritKind("ignite")).toMatchObject({ shape: "ignite", glyph: null });
    expect(spiritKind("frozen")).toMatchObject({ shape: "freeze", glyph: null });
    expect(spiritKind("charged")).toMatchObject({ shape: "shock", glyph: null });
    expect(spiritKind("wet")).toMatchObject({ shape: "wet", glyph: null });
  });

  it("沒有元素照舊是火靈", () => {
    expect(spiritKind(undefined)).toMatchObject({ shape: "ignite", glyph: null });
  });

  it("其他元素：水滴身體、整隻是該元素色、頭頂有狀態圖示同一套的圖樣（每個都認得）", () => {
    const others = SUMMON_KEYWORDS.filter((k) => !["ignite", "frozen", "charged", "wet"].includes(k));
    expect(others.length).toBeGreaterThan(0);
    const colors = new Set<string>();
    for (const k of others) {
      const s = spiritKind(k);
      expect(s.shape, k).toBe("wet");
      expect(s.shape).not.toBe("ignite");
      expect(s.glyph, k).not.toBeNull();
      expect(GLYPH[s.glyph!], `${k} → ${s.glyph}`).toBeDefined();
      colors.add(s.pal.c);
    }
    expect(colors.size).toBe(others.length);
    for (const g of Object.values(SPIRIT_GLYPH)) expect(GLYPH[g], g).toBeDefined();
  });
});
