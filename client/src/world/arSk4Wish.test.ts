// AR-SK4（WC-2b 待決 2）：許願元素面板當場擋第二個非物理元素；物理不佔名額；上限照伺服器的 `max`（已多給物理 1 格）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { WishPanel } from "./WishPanel";
import { PHYSICAL_TAG, physicalSlot, tagRoom, tagShownMax, toggleTag, WISH_ZH, type WishData } from "./wish";

const ELEMENTS = [
  { id: "physical", name_zh: "物理", description_zh: "" },
  { id: "fire", name_zh: "火焰", description_zh: "" },
  { id: "ice", name_zh: "冰霜", description_zh: "" },
  { id: "poison", name_zh: "毒素", description_zh: "" },
];

function wishData(elementMax: number): WishData {
  return {
    title_zh: "許願池",
    speaker: null,
    line_zh: null,
    cost: 4,
    refund: 2,
    coins: 9,
    left: 2,
    per_week: 2,
    available: true,
    blocked_zh: null,
    llm: false,
    text_max_chars: 60,
    max_keywords: 2,
    menu: [],
    tag_groups: [
      { id: "keywords", label_zh: "關鍵字", max: 2, items: [{ id: "frozen", name_zh: "冰凍", description_zh: "" }] },
      { id: "elements", label_zh: "元素", max: elementMax, items: ELEMENTS },
      { id: "effects", label_zh: "效果類型", max: 2, items: [{ id: "summon", name_zh: "召喚", description_zh: "" }] },
    ],
  };
}

describe("AR-SK4 元素名額：物理不佔名額", () => {
  it("只有元素類、而且清單裡有物理時才套用", () => {
    expect(physicalSlot("elements", ELEMENTS)).toBe(true);
    expect(physicalSlot("elements", ELEMENTS.slice(1))).toBe(false);
    expect(physicalSlot("effects", ELEMENTS)).toBe(false);
  });

  it("1 階（伺服器 max 2）：選了一個非物理元素，第二個非物理當場擋；物理還能點", () => {
    const max = 2;
    let t = toggleTag({}, "elements", "fire", max, true);
    expect(t.elements).toEqual(["fire"]);
    expect(tagRoom(t.elements ?? [], "ice", max, true)).toBe(false);
    t = toggleTag(t, "elements", "ice", max, true);
    expect(t.elements).toEqual(["fire"]); // 擋住
    expect(tagRoom(t.elements ?? [], PHYSICAL_TAG, max, true)).toBe(true);
    t = toggleTag(t, "elements", PHYSICAL_TAG, max, true);
    expect(t.elements).toEqual(["fire", "physical"]);
    // 已選的一律可以拿掉；拿掉火焰後冰霜就能點
    expect(tagRoom(t.elements ?? [], "fire", max, true)).toBe(true);
    t = toggleTag(t, "elements", "fire", max, true);
    expect(t.elements).toEqual(["physical"]);
    t = toggleTag(t, "elements", "ice", max, true);
    expect(t.elements).toEqual(["physical", "ice"]);
  });

  it("先點物理也不佔名額", () => {
    let t = toggleTag({}, "elements", PHYSICAL_TAG, 2, true);
    t = toggleTag(t, "elements", "fire", 2, true);
    expect(t.elements).toEqual(["physical", "fire"]);
    expect(tagRoom(t.elements ?? [], "ice", 2, true)).toBe(false);
  });

  it("2 階起照伺服器（max 3）：兩個非物理＋物理", () => {
    let t = toggleTag({}, "elements", "fire", 3, true);
    t = toggleTag(t, "elements", "ice", 3, true);
    expect(t.elements).toEqual(["fire", "ice"]);
    expect(tagRoom(t.elements ?? [], "poison", 3, true)).toBe(false);
    t = toggleTag(t, "elements", PHYSICAL_TAG, 3, true);
    expect(t.elements).toEqual(["fire", "ice", "physical"]);
  });

  it("沒有物理規則時照舊用總數", () => {
    let t = toggleTag({}, "elements", "fire", 2);
    t = toggleTag(t, "elements", "ice", 2);
    expect(t.elements).toEqual(["fire", "ice"]);
    expect(tagShownMax(2, false)).toBe(2);
    expect(tagShownMax(2, true)).toBe(1);
  });

  it("面板：元素類照定案字（1 階「最多 1 個（可另加物理）」、2 階起「最多 2 個（可另加物理）」），其他類照舊", () => {
    expect(WISH_ZH.tagMaxPhysical(1)).toBe("最多 1 個（可另加物理）");
    expect(WISH_ZH.tagMaxPhysical(2)).toBe("最多 2 個（可另加物理）");
    const html = renderToStaticMarkup(createElement(WishPanel, { wish: wishData(2), busy: false, fallback: null, onWish: () => {} }));
    expect(html).toContain("最多 1 個（可另加物理）");
    expect(html).not.toContain("物理另外算");
    expect(html).toContain(WISH_ZH.tagMax(2)); // 關鍵字、效果類型
    const tier2 = renderToStaticMarkup(createElement(WishPanel, { wish: wishData(3), busy: false, fallback: null, onWish: () => {} }));
    expect(tier2).toContain("最多 2 個（可另加物理）");
  });
});
