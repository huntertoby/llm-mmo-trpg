import { describe, expect, it } from "vitest";
import type { OfferTag, StartKeywordOption } from "../api/types";
import { canStart, isDevMode, keepAvailable, offerTagHint, offerTagText, startBody, toggleKeyword } from "./startFlow";

function kw(id: string, name: string) {
  return { id, name_zh: name, description_zh: "", variant: false, general: false };
}

function option(id: string, available: boolean): StartKeywordOption {
  return {
    keyword: kw(id, id),
    selected: false,
    skill: available ? ({ id: `skill_${id}` } as StartKeywordOption["skill"]) : null,
  };
}

const OPTIONS = [option("ignite", true), option("wet", false), option("marked", true)];

describe("新開局：選關鍵字", () => {
  it("點選加到最後、再點取消、滿了不變", () => {
    expect(toggleKeyword([], "ignite", 2)).toEqual(["ignite"]);
    expect(toggleKeyword(["ignite"], "marked", 2)).toEqual(["ignite", "marked"]);
    expect(toggleKeyword(["ignite", "marked"], "wet", 2)).toEqual(["ignite", "marked"]);
    expect(toggleKeyword(["ignite", "marked"], "ignite", 2)).toEqual(["marked"]);
  });

  it("湊不到起始技能的關鍵字不能開始，換武器時被拿掉", () => {
    expect(canStart("bow", ["ignite", "marked"], 2, OPTIONS)).toBe(true);
    expect(canStart("bow", ["ignite", "wet"], 2, OPTIONS)).toBe(false);
    expect(canStart("bow", ["ignite"], 2, OPTIONS)).toBe(false);
    expect(canStart("", ["ignite", "marked"], 2, OPTIONS)).toBe(false);
    expect(keepAvailable(["wet", "marked"], OPTIONS)).toEqual(["marked"]);
  });
});

describe("三選一卡片的標示", () => {
  const tag = (kind: OfferTag["kind"], label: string, names: string[], fallback = false): OfferTag => ({
    kind,
    label_zh: label,
    keywords: names.map((n) => kw(n, n)),
    fallback,
    source: "pool",
  });

  it("加深／橋接／新方向與帶的關鍵字", () => {
    expect(offerTagText(tag("deepen", "加深", ["點燃"]))).toBe("加深：點燃");
    expect(offerTagText(tag("bridge", "橋接", ["點燃", "標記"]))).toBe("橋接：點燃＋標記");
    expect(offerTagText(tag("new", "新方向", ["撞擊"]))).toBe("新方向：撞擊");
    expect(offerTagHint(tag("bridge", "橋接", ["點燃", "標記"]))).toContain("兩個");
    expect(offerTagHint(tag("bridge", "橋接", ["點燃", "撞擊"], true))).toContain("從持有的接到新的");
    expect(offerTagText(tag("new", "新方向", []))).toBe("新方向：基礎技能");
    expect(offerTagHint(tag("new", "新方向", []))).toContain("不和其他技能協同");
  });
});

describe("開發者模式", () => {
  it("只有 ?dev=1 才顯示開發者起始包", () => {
    expect(isDevMode("")).toBe(false);
    expect(isDevMode("?dev=0")).toBe(false);
    expect(isDevMode("?dev=1")).toBe(true);
    expect(isDevMode("?x=2&dev=true")).toBe(true);
  });
});

describe("單場戰鬥開局（3-28）", () => {
  it("送武器＋關鍵字，或只送開發者起始包；不送 build", () => {
    expect(startBody({ weapon: "bow", keywords: ["ignite", "marked"] })).toEqual({ weapon: "bow", keywords: ["ignite", "marked"] });
    expect(startBody({ devPack: "dev_a" })).toEqual({ keywords: [], dev_pack: "dev_a" });
  });

  it("?dev=1 才開啟開發者模式（起始包只在那時出現）", () => {
    expect(isDevMode("")).toBe(false);
    expect(isDevMode("?dev=0")).toBe(false);
    expect(isDevMode("?dev=1")).toBe(true);
  });
});
