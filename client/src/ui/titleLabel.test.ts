import { describe, expect, it } from "vitest";
import { accountTitlesLabel } from "./titleLabel";

describe("accountTitlesLabel（5F-3c）", () => {
  it("沒有稱號時是空字串", () => {
    expect(accountTitlesLabel(undefined)).toBe("");
    expect(accountTitlesLabel(null)).toBe("");
    expect(accountTitlesLabel([])).toBe("");
  });

  it("每個稱號加引號、用頓號隔開", () => {
    expect(accountTitlesLabel(["碎晶的終結者（s1）"])).toBe("「碎晶的終結者（s1）」");
    expect(accountTitlesLabel(["碎晶的終結者（s1）", "碎晶的終結者（s2）"])).toBe(
      "「碎晶的終結者（s1）」、「碎晶的終結者（s2）」",
    );
  });
});
