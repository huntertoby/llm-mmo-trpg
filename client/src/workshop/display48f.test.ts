// 3-48f：千分比欄位的玩家顯示（倍率 ×2、百分比 25%），內部仍存千分比。
import { describe, expect, it } from "vitest";
import type { FieldSpec } from "../api/types";
import { displayFactor, formatDisplay } from "../ui/workshop/FieldEditor";

const base = (display: FieldSpec["display"]): FieldSpec =>
  ({ field: "x", name_zh: "x", type: "int", display, min: 100, max: 10000 }) as FieldSpec;

describe("displayFactor / formatDisplay", () => {
  it("multiplier shows ×N", () => {
    expect(displayFactor(base("multiplier"))).toBe(1000);
    expect(formatDisplay(base("multiplier"), 2000)).toBe("×2");
    expect(formatDisplay(base("multiplier"), 1500)).toBe("×1.5");
  });
  it("percent shows N%", () => {
    expect(displayFactor(base("percent"))).toBe(10);
    expect(formatDisplay(base("percent"), 250)).toBe("25%");
  });
  it("plain fields are unchanged", () => {
    expect(displayFactor(base(null))).toBe(1);
    expect(formatDisplay(base(null), 7)).toBe("7");
  });
});
