// 背包滿了：戰後結算選要丟哪件（Phase 5D-2b）：純函式與面板的靜態輸出。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldBagItem, WorldPendingLoot } from "../api/types";
import { LootChoicePanel } from "./LootChoicePanel";
import { draftKey, lootChooseAction } from "./lootChoice";

function row(item: string, name_zh: string, count: number, gear = false): WorldBagItem {
  return {
    item,
    name_zh,
    kind_zh: gear ? "裝備" : "材料",
    count,
    description_zh: `${name_zh}的說明`,
    sell_price: 0,
    sellable: false,
    gear,
    can_equip: false,
    field_usable: false,
  };
}

const FANG = row("item_wolf_fang", "狼牙", 2);
const ARMOR = row("item_abc", "稀有皮甲（1 級）", 1, true);
const POTION = row("item_hp_potion_small", "小回復藥", 10);
const OLD = row("item_old", "優良頭巾（1 級）", 1, true);

const PENDING: WorldPendingLoot = { items: [FANG, ARMOR], over_slots: 2, hint_zh: "背包滿了：勾選要丟的。" };

describe("lootChooseAction", () => {
  const rows = [
    { side: "new" as const, item: FANG },
    { side: "new" as const, item: ARMOR },
    { side: "bag" as const, item: POTION },
    { side: "bag" as const, item: OLD },
  ];

  it("沒勾選時送空的動作（背包有空位時收下）", () => {
    expect(lootChooseAction({}, rows)).toEqual({ kind: "loot_choose", drop_items: {}, drop_gear: [] });
  });

  it("新拿到的與原本的都可以丟；個數不超過持有", () => {
    const draft = {
      [draftKey("new", "item_abc")]: 1,
      [draftKey("bag", "item_old")]: 1,
      [draftKey("bag", "item_hp_potion_small")]: 99,
      [draftKey("new", "item_wolf_fang")]: 0,
    };
    expect(lootChooseAction(draft, rows)).toEqual({
      kind: "loot_choose",
      drop_items: { item_hp_potion_small: 10 },
      drop_gear: ["item_abc", "item_old"],
    });
  });
});

describe("LootChoicePanel", () => {
  it("列出新拿到的與背包裡的，並有決定按鈕", () => {
    const html = renderToStaticMarkup(
      createElement(LootChoicePanel, {
        pending: PENDING,
        inventory: {
          bag: [POTION, OLD],
          slots_used: 30,
          slots_max: 30,
          pouch: [],
          pouch_count: 0,
          pouch_max: 3,
          can_pouch: true,
          pouch_problem_zh: null,
          consumables: [],
          equipped_zh: [],
          resonance_zh: [],
          equipment: [],
          gear_cards: [],
        },
        busy: false,
        onAct: () => undefined,
      }),
    );
    expect(html).toContain("背包滿了：選要丟哪件");
    expect(html).toContain("world-loot-row-new:item_wolf_fang");
    expect(html).toContain("world-loot-row-bag:item_old");
    expect(html).toContain("新拿到");
    expect(html).toContain("背包裡");
    expect(html).toContain('data-testid="world-loot-choose"');
  });
});
