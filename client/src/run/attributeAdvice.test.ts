// 建議屬性、屬性影響的招、有效屬性與營火屬性重配（Phase 3H-3）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero } from "../api/types";
import { AttributeAllocator } from "./AttributeAllocator";
import { AttributeRespecSection } from "./AttributeRespecSection";
import { RunHeroPanel } from "./RunHeroPanel";
import { affectsOf, affectsText, baseAttributes, suggestionText } from "./flow";

const affects = [
  { attr: "str", lines_zh: ["單手劍的普攻與武器技", "烈焰斬"] },
  { attr: "wil", lines_zh: [] },
] as const;

describe("affectsOf / affectsText / suggestionText", () => {
  it("取出某屬性影響的招，沒有資料時為空", () => {
    expect(affectsOf(affects, "str")).toEqual(["單手劍的普攻與武器技", "烈焰斬"]);
    expect(affectsOf(affects, "dex")).toEqual([]);
    expect(affectsOf(undefined, "str")).toEqual([]);
  });

  it("沒有影響任何招時不顯示", () => {
    expect(affectsText([])).toBeNull();
    expect(affectsText(["烈焰斬", "震地"])).toBe("影響：烈焰斬、震地");
  });

  it("建議主屬性一行", () => {
    expect(suggestionText(null)).toBeNull();
    expect(suggestionText({ attr: "wil", reason_zh: "你的起始技能 魂爆 吃意志" })).toBe(
      "建議主屬性：意志（你的起始技能 魂爆 吃意志）",
    );
  });
});

describe("配點畫面", () => {
  it("標出建議的屬性並寫出影響的招", () => {
    const html = renderToStaticMarkup(
      createElement(AttributeAllocator, {
        base: baseAttributes(10),
        points: 4,
        alloc: {},
        onChange: () => {},
        suggestion: { attr: "str", reason_zh: "武器吃力量" },
        affects,
      }),
    );
    expect(html).toContain("建議主屬性：力量（武器吃力量）");
    expect(html).toContain('data-testid="attr-affects-str"');
    expect(html).toContain("影響：單手劍的普攻與武器技、烈焰斬");
    expect(html).not.toContain('data-testid="attr-affects-wil"');
    expect(html).toContain("run-alloc-row suggested");
  });
});

describe("角色面板的有效屬性", () => {
  const hero = {
    name_zh: "主角",
    level: 1,
    xp: 0,
    xp_next: 10,
    hp: 30,
    max_hp: 30,
    mana: 5,
    max_mana: 5,
    source: 0,
    source_max: 3,
    weapon: "one_handed_sword",
    weapon_class: "melee",
    weapon_name_zh: "單手劍",
    hp_per_con_point: 3,
    hp_con_base: 10,
    attributes: { str: 12, dex: 10, con: 10, int: 10, wis: 10, wil: 10 },
    effective_attributes: { str: 14, dex: 10, con: 10, int: 10, wis: 10, wil: 10 },
    attribute_affects: affects,
    attribute_perks: [],
    skills: [],
  } as unknown as RunHero;

  it("顯示有效屬性與裝備加成，並寫出影響的招", () => {
    const html = renderToStaticMarkup(createElement(RunHeroPanel, { hero: { ...hero, attribute_perks: [{ attr: "str", tier: 1, per_tier_zh: "撞擊 +1／階", now_zh: "撞擊 +1", next_at: 18 }] as RunHero["attribute_perks"] } }));
    expect(html).toContain("<b>14</b>");
    expect(html).toContain("基礎 12，裝備 +2");
    expect(html).toContain("影響：單手劍的普攻與武器技、烈焰斬");
  });

  it("舊回應沒有有效屬性時退回基礎屬性", () => {
    const old = { ...hero, effective_attributes: undefined, attribute_affects: undefined } as unknown as RunHero;
    const html = renderToStaticMarkup(createElement(RunHeroPanel, { hero: old }));
    expect(html).toContain("<b>12</b>");
    expect(html).not.toContain("基礎 12");
  });
});

describe("營火屬性重配", () => {
  const hero = {
    attributes: { str: 10, dex: 10, con: 10, int: 10, wis: 10, wil: 10 },
    hp_per_con_point: 3,
    attribute_points: 0,
    attribute_spent: { str: 4, wis: 2 },
  } as unknown as RunHero;
  const noop = async () => null;

  it("營火有免費重配按鈕，寫出會退回幾點", () => {
    const html = renderToStaticMarkup(createElement(AttributeRespecSection, { hero, busy: false, onChoose: noop, campfire: true }));
    expect(html).toContain("免費重配屬性點（退回 6 點）");
    expect(html).not.toContain("確認分配");
  });

  it("重配後有未分配的點數才出現分配區；非營火且沒有點數時不顯示", () => {
    const refunded = { ...hero, attribute_points: 6, attribute_spent: {} } as unknown as RunHero;
    const html = renderToStaticMarkup(createElement(AttributeRespecSection, { hero: refunded, busy: false, onChoose: noop, campfire: true }));
    expect(html).toContain("分配屬性點");
    expect(html).toContain("確認分配");
    expect(renderToStaticMarkup(createElement(AttributeRespecSection, { hero, busy: false, onChoose: noop }))).toBe("");
  });
});
