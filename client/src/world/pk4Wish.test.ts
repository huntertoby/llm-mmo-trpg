// PK-4：許願池「願望驅動」（07 7.6）——從清單點選五類標籤、送出的動作帶 `tags`、三選一卡上的回應願望與「做不到」那一行、
// 魔導書扉頁。伺服器沒給標籤清單（開關關掉）時照 WP-3 的關鍵字選單（`wp3Wish.test.ts`）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero, RunOffer, SkillCard } from "../api/types";
import { OfferPicker } from "../run/OfferPicker";
import cards from "../ui/fixtures/skillCards.json";
import { GRIMOIRE_ZH, SkillCardView } from "../ui/SkillCardView";
import { WishPanel } from "./WishPanel";
import { pickedTagNames, tagCount, tagMode, toggleTag, WISH_ZH, wishAction, wishSubmitBlock, type WishData } from "./wish";

const GROUPS: WishData["tag_groups"] = [
  { id: "keywords", label_zh: "關鍵字", max: 2, items: [{ id: "frozen", name_zh: "冰凍", description_zh: "寒冰凍結目標。" }] },
  { id: "elements", label_zh: "元素", max: 1, items: [{ id: "fire", name_zh: "火焰", description_zh: "" }, { id: "ice", name_zh: "冰霜", description_zh: "" }] },
  { id: "effects", label_zh: "效果類型", max: 2, items: [{ id: "summon", name_zh: "召喚", description_zh: "" }] },
  { id: "shapes", label_zh: "形狀", max: 1, items: [{ id: "cone", name_zh: "錐形", description_zh: "" }] },
  { id: "kinds", label_zh: "種類", max: 1, items: [{ id: "reaction", name_zh: "反應", description_zh: "" }] },
];

function wishData(over: Partial<WishData> = {}): WishData {
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
    tag_groups: GROUPS,
    ...over,
  };
}

describe("PK-4 標籤點選", () => {
  it("有標籤清單才是願望驅動", () => {
    expect(tagMode(wishData())).toBe(true);
    expect(tagMode(wishData({ tag_groups: [] }))).toBe(false);
  });

  it("每類有上限、點兩次拿掉", () => {
    let t = toggleTag({}, "elements", "fire", 1);
    expect(t).toEqual({ elements: ["fire"] });
    t = toggleTag(t, "elements", "ice", 1); // 滿了不變
    expect(t).toEqual({ elements: ["fire"] });
    t = toggleTag(t, "effects", "summon", 2);
    expect(tagCount(t)).toBe(2);
    expect(pickedTagNames(wishData(), ["frozen"], t)).toEqual(["冰凍", "火焰", "召喚"]);
    expect(tagCount(toggleTag(t, "elements", "fire", 1))).toBe(1);
  });

  it("至少選一個才能送；送出的動作帶五類 tags", () => {
    const w = wishData();
    expect(wishSubmitBlock(w, "menu", "", [], {})).toBe(WISH_ZH.needTag);
    expect(wishSubmitBlock(w, "menu", "", ["frozen"], {})).toBeNull();
    expect(wishSubmitBlock(w, "menu", "", [], { kinds: ["reaction"] })).toBeNull();
    expect(wishAction("menu", "", ["frozen"], { elements: ["fire"], kinds: ["reaction", "bogus"] })).toEqual({
      kind: "wish",
      keywords: [],
      tags: { keywords: ["frozen"], elements: ["fire"], effects: [], shapes: [], kinds: ["reaction"] },
    });
    // 文字許願照舊；沒有 tags 時照舊送關鍵字
    expect(wishAction("text", " 火 ", [], {})).toEqual({ kind: "wish", text: "火", keywords: [] });
    expect(wishAction("menu", "", ["frozen"])).toEqual({ kind: "wish", keywords: ["frozen"] });
  });

  it("面板：選單分頁改成「從清單點選」五類", () => {
    const html = renderToStaticMarkup(createElement(WishPanel, { wish: wishData(), busy: false, fallback: null, onWish: () => {} }));
    expect(html).toContain('data-testid="wish-tag-pane"');
    for (const g of GROUPS) expect(html).toContain(`data-testid="wish-tags-${g.id}"`);
    expect(html).toContain(WISH_ZH.tagMax(2));
    expect(html).not.toContain('data-testid="wish-menu-pane"');
    const old = renderToStaticMarkup(createElement(WishPanel, { wish: wishData({ tag_groups: [] }), busy: false, fallback: null, onWish: () => {} }));
    expect(old).toContain('data-testid="wish-menu-pane"');
  });
});

const CARD = (cards as unknown as Record<string, SkillCard>)["skill_ash_harvest"]!;

function offer(): RunOffer {
  return {
    reason: "complete",
    tier: 2,
    top_attribute: "int",
    candidates: [CARD],
    off_route: [],
    tags: [
      {
        kind: "new",
        label_zh: "新方向",
        keywords: [],
        fallback: false,
        source: "composer",
        pick: "llm",
        wish_reply_zh: "你想要冰與火——這招先凍住再點燃。",
        wish_miss_zh: "最接近你願望的一招：有冰凍；火焰這次做不到。",
      },
    ],
  } as unknown as RunOffer;
}

describe("PK-4 三選一與扉頁", () => {
  it("許願卡畫回應願望與做不到那一行，不畫加深／橋接／新方向", () => {
    const props = { offer: offer(), hero: { skills: [] } as unknown as RunHero, runSeed: 0, groupKey: "g", pick: null, replace: null, onPick: () => {}, onReplace: () => {} };
    const html = renderToStaticMarkup(createElement(OfferPicker, { ...props, wish: true }));
    expect(html).toContain("你想要冰與火——這招先凍住再點燃。");
    expect(html).toContain("最接近你願望的一招：有冰凍；火焰這次做不到。");
    expect(html).not.toContain('data-testid="offer-kind"');
    const plain = renderToStaticMarkup(createElement(OfferPicker, props));
    expect(plain).toContain('data-testid="offer-kind"');
    expect(plain).not.toContain('data-testid="offer-wish"');
  });

  it("扉頁的字", () => {
    expect(GRIMOIRE_ZH.wish("想把敵人凍在火裡")).toBe("你的願望：「想把敵人凍在火裡」");
    const html = renderToStaticMarkup(createElement(SkillCardView, { card: CARD, wish: "<b>想把敵人凍在火裡</b>" }));
    expect(html).toContain('data-testid="skill-card-grimoire"');
    expect(html).toContain("&lt;b&gt;想把敵人凍在火裡&lt;/b&gt;"); // 願望原文只當文字
    expect(renderToStaticMarkup(createElement(SkillCardView, { card: CARD }))).not.toContain("skill-card-grimoire");
  });
});
