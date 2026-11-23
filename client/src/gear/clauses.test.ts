// E6-b2 美術小修（docs/art/E6-b2驗收.md）：用「；」接起來之前先拿掉每段結尾的「。」，比較區「目前」那行不會出現「。；」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { GearCandidate, GearItemInfo } from "../api/types";
import { GearCardView } from "../ui/gear/GearCardView";
import { joinClauses } from "./clauses";
import { itemSummary } from "./gearDraft";

const TERRAIN = "走過的格子結 1 回合冰，你自己踩上去不會滑倒。";

function item(over: Partial<GearItemInfo> = {}): GearItemInfo {
  return {
    id: "item_e6b2b_boots",
    name_zh: "霜行靴",
    slot_type: "feet",
    base_bonus_zh: "基礎加成：防禦 +2%",
    affixes: [
      { affix_id: "affix_terrain_frost", text_zh: TERRAIN, signature: "terrain", signature_zh: "招牌・地形規則", off_zh: "身上已經有 3 個招牌效果生效，這個沒有效果，可以在角色面板換選" },
      { affix_id: "affix_attr_dex", text_zh: "敏捷 +2。" },
    ],
    offhand_traits_zh: [],
    tags: [],
    two_handed: false,
    paired: false,
    legendary: false,
    rarity: "rare",
    rarity_zh: "稀有",
    item_level: 5,
    points: 10,
    ...over,
  } as unknown as GearItemInfo;
}

describe("joinClauses", () => {
  it("先拿掉每段結尾的「。」再用「；」接起來；中間的「。」不動", () => {
    expect(joinClauses(["……不會滑倒。", "基礎加成：防禦 +2%"])).toBe("……不會滑倒；基礎加成：防禦 +2%");
    expect(joinClauses(["一。二。", "三。。"])).toBe("一。二；三");
    expect(joinClauses(["力量 +3"])).toBe("力量 +3");
    expect(joinClauses([])).toBe("");
  });

  it("沒有「。」結尾時和原本的 join 逐字相同", () => {
    const parts = ["基礎加成：攻擊 +2%", "力量 +3", "你施加的燃燒 +1 回合"];
    expect(joinClauses(parts)).toBe(parts.join("；"));
  });
});

describe("比較區「目前」那行（標灰卡、背包詳情共用 GearCardView）", () => {
  it("目前那件的招牌說明以「。」結尾：接起來不會出現「。；」", () => {
    const cand = { item: item({ id: "item_new" }), slot: "feet", slot_zh: "腳", current: item(), notes_zh: [] } as unknown as GearCandidate;
    const html = renderToStaticMarkup(createElement(GearCardView, { cand }));
    const line = /data-testid="gear-card-current-lines">([^<]*)</u.exec(html)?.[1] ?? "";
    expect(line).toBe("基礎加成：防禦 +2%；走過的格子結 1 回合冰，你自己踩上去不會滑倒；敏捷 +2");
    expect(html).not.toContain("。；");
  });

  it("物品摘要（測試物品清單）也一樣", () => {
    expect(itemSummary(item())).toBe("基礎加成：防禦 +2%；走過的格子結 1 回合冰，你自己踩上去不會滑倒；敏捷 +2");
  });
});
