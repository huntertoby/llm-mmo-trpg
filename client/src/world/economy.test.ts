// 貨幣、背包、腰包與商店（Phase 5D-1）：純函式與面板的靜態輸出。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldBagItem, WorldInventory, WorldShop } from "../api/types";
import { InventoryPanel, ShopPanel } from "./EconomyPanel";
import { draftCount, pouchAction, pouchDraft, samePouch, setDraft, walletLine } from "./economy";

function bag(item: string, name_zh: string, count: number, field = false): WorldBagItem {
  return {
    item,
    name_zh,
    kind_zh: "消耗品",
    count,
    description_zh: `${name_zh}的說明`,
    sell_price: 7,
    sellable: true,
    tradable: false,
    gear: false,
    can_equip: false,
    field_usable: field,
    use_zh: field ? "HP +30%" : null,
    battle_zh: "放進腰包：戰鬥中花 1 AP 使用，每個用一次（不佔技能欄位）",
  };
}

function inventory(overrides: Partial<WorldInventory> = {}): WorldInventory {
  return {
    bag: [bag("item_hp_potion_small", "小回復藥", 2, true)],
    slots_used: 1,
    slots_max: 30,
    pouch: [bag("item_oil_flask", "油瓶", 1)],
    pouch_count: 1,
    pouch_max: 3,
    can_pouch: true,
    pouch_problem_zh: null,
    consumables: [bag("item_oil_flask", "油瓶", 1), bag("item_hp_potion_small", "小回復藥", 2, true)],
    equipped_zh: [],
    resonance_zh: [],
    equipment: [],
    gear_cards: [],
    ...overrides,
  };
}

const SHOP: WorldShop = {
  shop: "shop_liu",
  name_zh: "柳記雜貨",
  npc: "shopkeeper_liu",
  npc_name_zh: "柳掌櫃",
  rank_zh: "中立",
  affinity_zh: "每次消費柳掌櫃好感度 +2（每天最多 +4，今天還能 +4）",
  can_trade: true,
  trade_problem_zh: null,
  price_notes_zh: [],
  items: [
    {
      item: "item_hp_potion_small",
      name_zh: "小回復藥",
      kind_zh: "消耗品",
      description_zh: "回 HP",
      price: 15,
      weekly: false,
      stock_zh: null,
      locked: false,
      lock_zh: null,
      can_buy: false,
      problem_zh: "金幣不夠（要 20，有 0）",
    },
    {
      item: "item_mist_flask",
      name_zh: "霧瓶",
      kind_zh: "消耗品",
      description_zh: "煙霧",
      price: 25,
      weekly: false,
      stock_zh: null,
      locked: true,
      lock_zh: "柳掌櫃好感度到友善才賣",
      can_buy: false,
      problem_zh: "店主好感度到友善才賣",
    },
    {
      item: "item_green_bamboo",
      name_zh: "青竹節",
      kind_zh: "材料",
      description_zh: "特產",
      price: 30,
      weekly: true,
      stock_zh: "本週剩 3 個",
      locked: false,
      lock_zh: null,
      can_buy: true,
      problem_zh: null,
    },
  ],
};

const noop = () => undefined;

describe("walletLine", () => {
  it("shows gold and quest coins", () => {
    expect(walletLine({ gold: 15, quest_coins: 2 })).toBe("金幣 15・任務幣 2");
    expect(walletLine(null)).toBe("");
  });
});

describe("pouch draft", () => {
  it("starts from the current pouch and respects owned count and the 3-item cap", () => {
    const inv = inventory();
    const draft = pouchDraft(inv);
    expect(draft).toEqual({ item_oil_flask: 1 });
    expect(samePouch(draft, inv)).toBe(true);
    const more = setDraft(draft, inv, "item_hp_potion_small", 5);
    expect(more).toEqual({ item_oil_flask: 1, item_hp_potion_small: 2 }); // 只有 2 顆
    expect(draftCount(more)).toBe(3);
    expect(setDraft(more, inv, "item_oil_flask", 3)).toEqual({ item_oil_flask: 1, item_hp_potion_small: 2 }); // 上限 3
    expect(setDraft(more, inv, "item_oil_flask", 0)).toEqual({ item_hp_potion_small: 2 });
    expect(samePouch(more, inv)).toBe(false);
    expect(pouchAction({ item_hp_potion_small: 2, item_oil_flask: 1 })).toEqual({
      kind: "pouch",
      items: { item_oil_flask: 1, item_hp_potion_small: 2 },
    });
  });
});

describe("ShopPanel", () => {
  it("lists prices, weekly stock, gates and disables what cannot be bought", () => {
    const html = renderToStaticMarkup(createElement(ShopPanel, { shop: SHOP, inventory: inventory(), busy: false, onAct: noop }));
    expect(html).toContain("柳記雜貨");
    expect(html).toContain("15 金幣");
    expect(html).toContain("本週剩 3 個");
    expect(html).toContain("柳掌櫃好感度到友善才賣");
    expect(html).toContain("今天還能 +4");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*data-testid="world-buy-item_hp_potion_small"/);
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*data-testid="world-buy-item_green_bamboo"/);
    expect(html).toContain('data-testid="world-sell-item_hp_potion_small"'); // 背包裡的可以賣
    expect(html).not.toContain("title="); // 說明用共用 Hint，不用原生 title
    expect(html).not.toContain("world-shop-price-note");
  });

  it("explains a world event surcharge (5F-5c)", () => {
    const shop = { ...SHOP, price_notes_zh: ["熔岩潰堤失守：買價 +20%"] };
    const html = renderToStaticMarkup(createElement(ShopPanel, { shop, inventory: inventory(), busy: false, onAct: noop }));
    expect(html).toContain('data-testid="world-shop-price-note"');
    expect(html).toContain("熔岩潰堤失守：買價 +20%");
  });
});

describe("InventoryPanel", () => {
  it("shows bag slots, pouch and the use button for field potions", () => {
    const html = renderToStaticMarkup(createElement(InventoryPanel, { inventory: inventory(), busy: false, onAct: noop, canUse: true }));
    expect(html).toContain("1／30 格");
    expect(html).toContain("1／3 個");
    expect(html).toContain('data-testid="world-use-item_hp_potion_small"');
    expect(html).not.toContain('data-testid="world-use-item_oil_flask"'); // 投擲瓶野外不能用
    expect(html).toContain('data-testid="world-pouch-toggle"');
  });

  it("lists dropped gear with the equip button and what is worn (5D-2)", () => {
    const sword: WorldBagItem = {
      ...bag("item_gen_weapon_0000abcd", "稀有短劍（1 級）", 1),
      kind_zh: "裝備",
      gear: true,
      can_equip: false,
      equip_problem_zh: "只有城鎮與營火能換裝備",
      battle_zh: null,
    };
    const html = renderToStaticMarkup(
      createElement(InventoryPanel, {
        inventory: inventory({ bag: [sword], equipped_zh: ["身體：稀有布衣（3 級）"] }),
        busy: false,
        onAct: noop,
        canUse: true,
      }),
    );
    expect(html).toContain("稀有短劍（1 級）");
    expect(html).toContain('data-testid="world-equip-item_gen_weapon_0000abcd"');
    expect(html).toMatch(/data-testid="world-equip-item_gen_weapon_0000abcd"[^>]*disabled|disabled[^>]*data-testid="world-equip-item_gen_weapon_0000abcd"/);
    expect(html).toContain("身體：稀有布衣（3 級）");
  });

  it("explains why the pouch cannot be changed in the field", () => {
    const html = renderToStaticMarkup(
      createElement(InventoryPanel, {
        inventory: inventory({ can_pouch: false, pouch_problem_zh: "只有城鎮與營火能整理腰包" }),
        busy: false,
        onAct: noop,
        canUse: true,
      }),
    );
    expect(html).toContain("整理腰包：只有城鎮與營火能整理腰包");
    expect(html).not.toContain('data-testid="world-pouch-toggle"');
  });
});
