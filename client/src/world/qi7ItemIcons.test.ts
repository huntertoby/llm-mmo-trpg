// Phase QI-7：物品圖示接到遊戲畫面——飛進背包、清單列（商店買／賣、整理腰包、背包滿了、鐵匠特色材料）、信件附件。
// 需求 docs/art/Q版小圖示-物品移植需求.md 第 1.1 節；背包格在 `panelIcons.test.ts`。畫法本身在 `render/qIcon/qIconItems.test.ts`。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { MailView, WorldBagItem, WorldCrafting, WorldInventory, WorldPendingLoot, WorldShop } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { PouchEditor, ShopPanel } from "./EconomyPanel";
import { GainFlyIcon, GainIcon } from "./GainEffects";
import { gainedItems, gainIconOf } from "./gainFx";
import { LootChoicePanel } from "./LootChoicePanel";
import { MailPanel, type MailApi } from "./MailPanel";
import { SmithyPanel } from "./SmithyPanel";

const NOOP = (): void => undefined;
function row(item: string, over: Partial<WorldBagItem> = {}): WorldBagItem {
  return { item, name_zh: item, kind_zh: "材料", count: 2, description_zh: "", sell_price: 3, sellable: true, field_usable: false, gear: false, can_equip: false, tradable: true, ...over } as WorldBagItem;
}
const gearRow = (id: string): WorldBagItem => row(id, { gear: true, kind_zh: "裝備", count: 1 });
function inv(over: Partial<WorldInventory> = {}): WorldInventory {
  return { bag: [], slots_used: 0, slots_max: 30, pouch: [], pouch_count: 0, pouch_max: 3, can_pouch: true, pouch_problem_zh: null, consumables: [], equipped_zh: [], resonance_zh: [], equipment: [], gear_cards: [], ...over } as WorldInventory;
}
/** `<canvas … data-item-icon="id">` 的屬性。 */
const iconTag = (html: string, id: string): string | undefined => html.match(new RegExp(`<canvas class="item-icon[^>]*data-item-icon="${id}"[^>]*>`))?.[0];

describe("飛進背包（gainFx、GainEffects）", () => {
  it("物品：表裡有的畫自己的圖示（帶後端的 color、rare）；表裡沒有的用通用布袋；裝備照 6Q-1", () => {
    const g = gainedItems(inv({ bag: [] }), inv({ bag: [row("item_dye_jade", { color: "#3E8E6A" }), row("item_living_bone", { rare: true }), row("ghost")] }));
    expect(g.map((x) => [x.item, x.color ?? null, x.rare ?? null])).toEqual([["ghost", null, null], ["item_dye_jade", "#3E8E6A", null], ["item_living_bone", null, true]]);
    expect(gainIconOf(null, g[1]!)).toEqual({ kind: "item", item: "item_dye_jade", color: "#3E8E6A", rare: null });
    expect(gainIconOf(null, g[2]!)).toEqual({ kind: "item", item: "item_living_bone", color: null, rare: true });
    expect(gainIconOf(null, g[0]!)).toEqual({ kind: "generic", gear: false });
    expect(gainIconOf(null, { item: "item_dye_new", gear: false, color: "#123456" })).toMatchObject({ kind: "item", item: "item_dye_new" });
  });
  it("畫法：物品與通用圖示是 28 的畫布（飛行圓含在畫布裡，不另包 .gain-gear）；通用 SVG 拿掉了", () => {
    const item = renderToStaticMarkup(createElement(GainFlyIcon, { choice: { kind: "item", item: "item_living_bone", color: null, rare: true } }));
    expect(iconTag(item, "item_living_bone")).toMatch(/class="item-icon item-icon-fly" width="56" height="56" style="width:28px;height:28px"/);
    expect(item).not.toContain("gain-gear");
    expect(iconTag(renderToStaticMarkup(createElement(GainIcon, { gear: true })), "gain_gear")).toBeDefined();
    expect(iconTag(renderToStaticMarkup(createElement(GainIcon, { gear: false })), "gain_item")).toBeDefined();
    const src = readFile(SRC_DIR, "world/GainEffects.tsx");
    expect(src).not.toContain("<svg");
    expect(src).toMatch(/和裝備的 32 不同/);
  });
});

describe("清單列的 24 圖示（需求 1.1 第 5 列；裝備列與表裡沒有的物品留 24 空位）", () => {
  const shop = {
    shop: "s", name_zh: "柳記雜貨", npc: "n", npc_name_zh: "柳掌櫃", rank_zh: "普通", affinity_zh: null, can_trade: true, trade_problem_zh: null, price_notes_zh: [],
    items: [{ item: "item_hp_potion_small", name_zh: "小回復藥", kind_zh: "消耗品", description_zh: "回血", price: 20, weekly: false, stock_zh: null, locked: false, lock_zh: null, can_buy: true, problem_zh: null }],
  } as unknown as WorldShop;
  it("商店買：圖示和名字包在同一個 Hint 的元素裡（滑過圖示也出說明）", () => {
    const html = renderToStaticMarkup(createElement(ShopPanel, { shop, inventory: inv(), busy: false, onAct: NOOP }));
    expect(html).toMatch(/<span class="world-shop-thing"><canvas class="item-icon item-icon-bag" width="48" height="48" style="width:24px;height:24px" data-item-icon="item_hp_potion_small"[^>]*><\/canvas><span class="world-shop-name">小回復藥<\/span><\/span>/);
  });
  it("賣東西：物品畫圖示、裝備列放 24 寬的空位", () => {
    const html = renderToStaticMarkup(createElement(ShopPanel, { shop, inventory: inv({ bag: [row("item_fire_flask"), gearRow("g_sword")] }), busy: false, onAct: NOOP }));
    expect(iconTag(html, "item_fire_flask")).toBeDefined();
    expect(html).toMatch(/<span class="world-shop-thing"><span class="item-icon-pad" style="width:24px;height:24px" aria-hidden="true"><\/span><span class="world-shop-name">g_sword<\/span>/);
  });
  it("背包滿了：物品與裝備混排，裝備列與表裡沒有的物品留空位", () => {
    const pending = { items: [gearRow("g_new"), row("item_wolf_fang")], over_slots: 1, hint_zh: "" } as unknown as WorldPendingLoot;
    const html = renderToStaticMarkup(createElement(LootChoicePanel, { pending, inventory: inv({ bag: [row("ghost")] }), busy: false, onAct: NOOP }));
    expect(iconTag(html, "item_wolf_fang")).toBeDefined();
    expect(html.match(/class="item-icon-pad"/g)).toHaveLength(2);
  });
  it("整理腰包：消耗品畫圖示", () => {
    const html = renderToStaticMarkup(createElement(PouchEditor, { inventory: inv({ consumables: [row("item_oil_flask"), row("item_mana_potion")] }), busy: false, onAct: NOOP, onDone: NOOP }));
    expect(iconTag(html, "item_oil_flask")).toBeDefined();
    expect(iconTag(html, "item_mana_potion")).toBeDefined();
  });
  it("鐵匠特色材料：圖示在 checkbox 和名字之間；通用料的 <select> 照舊沒有圖", () => {
    const crafting = {
      stations: [], smithy: "smithy", enchanter: null, can_use: true, problem_zh: null,
      slots: [{ slot_type: "weapon", name_zh: "武器", grade_amount: 3, affixes: [] }], rarities: [{ rarity: "rare", name_zh: "稀有", cost_zh: "" }],
      materials: [
        { item: "item_coarse_material", name_zh: "粗料", count: 3, grade: true, level_cap: 1, leaning_zh: null, resonance_zh: null },
        { item: "item_mist_crystal", name_zh: "霧晶", count: 1, grade: false, level_cap: null, leaning_zh: "傾向", resonance_zh: null },
      ],
      flavor_max: 3, recipes: [], gear: [], essence: 0, note_zh: "",
    } as unknown as WorldCrafting;
    const html = renderToStaticMarkup(createElement(SmithyPanel, { crafting, busy: false, onAct: NOOP, initialTab: "craft" }));
    expect(html).toMatch(/<label class="world-craft-material"><input type="checkbox"[^>]*data-testid="world-craft-material-item_mist_crystal"\/><canvas class="item-icon item-icon-bag"[^>]*data-item-icon="item_mist_crystal"[^>]*><\/canvas>霧晶 ×1<\/label>/);
    expect(iconTag(html, "item_coarse_material")).toBeUndefined();
  });
});

describe("信件附件（32、背包框；小牌高度照現行 32）", () => {
  const NEVER = (): Promise<never> => new Promise(() => undefined);
  const api: MailApi = { mail: NEVER, recipients: NEVER, quote: NEVER, send: NEVER, claim: NEVER, refuse: NEVER };
  it("信上的物品附件：表裡有的畫 32 的圖示（.has-icon），表裡沒有的照舊金色小方塊", () => {
    const letter = {
      id: "m1", sender: "a", sender_name: "老鐵", recipient: "b", recipient_name: "阿霧", from_zh: "", sent_at: 0, expires_at: 0, days_left: 2, note: "",
      items: [{ item: "item_scorched_iron", name_zh: "焦鐵", count: 3, rare: false }, { item: "ghost", name_zh: "ghost", count: 1 }], gear: [], gold: 0, tax: 0, status_zh: "可以領", action: "claim", can_act: true,
    };
    const mail = { postman: null, here: true, inbox: [letter], returned: [], outgoing: [], sendable: [], gold: 0, mailbox_count: 1, mailbox_max: 20, max_attachments: 3, note_max: 40, tax_permille: 100, min_level: 3, level_ok: true, return_days: 3, footer_zh: "", send_note_zh: "" } as unknown as MailView;
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: api, inventory: null, tab: "inbox", initial: { mail } }));
    expect(html).toMatch(/<span class="mail-thing mail-thing-chip has-icon"><canvas class="item-icon item-icon-bag" width="64" height="64" style="width:32px;height:32px" data-item-icon="item_scorched_iron"/);
    expect(html).toMatch(/<span class="mail-thing mail-thing-chip"><span class="mail-thing-mark" aria-hidden="true"><\/span><span class="mail-thing-name">ghost<\/span>/);
  });
  it("寄東西的背包格（Thing）：物品畫 32 的圖示", () => {
    const mail = { postman: null, here: true, inbox: [], returned: [], outgoing: [], sendable: [row("item_dye_indigo", { color: "#2E4A7D" })], gold: 0, mailbox_count: 0, mailbox_max: 20, max_attachments: 3, note_max: 40, tax_permille: 100, min_level: 3, level_ok: true, return_days: 3, footer_zh: "", send_note_zh: "" } as unknown as MailView;
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: api, inventory: null, tab: "send", initial: { mail } }));
    expect(iconTag(html, "item_dye_indigo")).toMatch(/width="64"/);
  });
  it("CSS：小牌的圖示蓋住上下左的 1px 框線（不撐高）", () => {
    const css = readFile(SRC_DIR, "world/mail.css");
    expect(css).toMatch(/\.mail-thing-chip > \.item-icon \{\s*margin: -1px 0 -1px -1px;/);
  });
});
