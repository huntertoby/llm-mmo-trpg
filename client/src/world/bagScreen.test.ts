// 背包、商店畫面與戰鬥道具欄（Phase 5D-4；docs/phases/Phase5計畫.md 33.2、33.4）：純函式與靜態輸出。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { GearCandidate, GearItemInfo, SkillCard, WorldBagItem, WorldInventory, WorldStory, WorldView } from "../api/types";
import { isItemSkill, splitSkills } from "../battle/skillTray";
import type { SkillButton } from "../battle/targeting";
import { WorldBagScreen } from "./BagScreen";
import { InventorySummary } from "./EconomyPanel";
import { StoryBlock } from "./EventCard";
import { WorldShopScreen } from "./ShopScreen";
import { bagSummary, equipAction, equipState, nonGear, otherRingSlot } from "./bagView";
import { leftPane, togglePane } from "./growth";

function info(over: Partial<GearItemInfo> = {}): GearItemInfo {
  return {
    id: "item_gen_ring_1",
    name_zh: "稀有戒指（3 級）",
    slot_type: "ring",
    affixes: [{ affix_id: "affix_attr_str", text_zh: "力量 +3" }],
    offhand_traits_zh: [],
    tags: [],
    two_handed: false,
    paired: false,
    legendary: false,
    rarity: "rare",
    rarity_zh: "稀有",
    item_level: 3,
    points: 12,
    ...over,
  } as unknown as GearItemInfo;
}

function gearRow(id: string, can = true): WorldBagItem {
  return {
    item: id,
    name_zh: "稀有戒指（3 級）",
    kind_zh: "裝備",
    count: 1,
    description_zh: "戒指",
    sell_price: 10,
    sellable: true,
    tradable: false,
    field_usable: false,
    gear: true,
    can_equip: can,
    equip_problem_zh: can ? null : "只有城鎮與營火能換裝備",
  };
}

const POTION: WorldBagItem = {
  item: "item_hp_potion_small",
  name_zh: "小回復藥",
  kind_zh: "消耗品",
  count: 2,
  description_zh: "回 HP",
  sell_price: 7,
  sellable: true,
  tradable: false,
  field_usable: true,
  use_zh: "HP +30%",
  gear: false,
  can_equip: false,
};

function inventory(over: Partial<WorldInventory> = {}): WorldInventory {
  const card: GearCandidate = { item: info(), slot: "ring_1", slot_zh: "戒指 1", current: null, notes_zh: [] } as GearCandidate;
  return {
    bag: [POTION, gearRow("item_gen_ring_1")],
    slots_used: 2,
    slots_max: 30,
    pouch: [],
    pouch_count: 0,
    pouch_max: 3,
    can_pouch: true,
    pouch_problem_zh: null,
    consumables: [POTION],
    equipped_zh: [],
    resonance_zh: ["潛影共鳴（隱蔽 2 件）：敏捷 +2"],
    equipment: [
      { slot: "main_hand", slot_zh: "主手", item: info({ id: "w", name_zh: "法杖", slot_type: "weapon" }) },
      { slot: "ring_1", slot_zh: "戒指 1", item: null },
    ],
    gear_cards: [card],
    ...over,
  };
}

function view(over: Partial<WorldView> = {}): WorldView {
  return {
    inventory: inventory(),
    wallet: { gold: 15, quest_coins: 2 },
    encounter: null,
    battle_id: null,
    pending_loot: null,
    shop: null,
    crafting: null,
    pending_flash: null,
    pending_offer: null,
    ...over,
  } as unknown as WorldView;
}

describe("bagView", () => {
  it("換上：照後端的能不能與原因；戒指可以改戴另一隻", () => {
    const inv = inventory();
    expect(equipState(inv, "item_gen_ring_1")).toEqual({ ok: true, reason: "" });
    expect(equipState(inventory({ bag: [gearRow("x", false)] }), "x").reason).toBe("只有城鎮與營火能換裝備");
    expect(equipState(inv, "nope").ok).toBe(false);
    expect(otherRingSlot("ring_1")).toBe("ring_2");
    expect(otherRingSlot("body")).toBeNull();
    const cand = inv.gear_cards[0] as GearCandidate;
    expect(equipAction(cand)).toEqual({ kind: "equip", item: "item_gen_ring_1" });
    expect(equipAction(cand, "ring_2")).toEqual({ kind: "equip", item: "item_gen_ring_1", slot: "ring_2" });
    expect(nonGear(inv).map((b) => b.item)).toEqual(["item_hp_potion_small"]);
    expect(bagSummary(inv)).toBe("2／30 格・裝備 1 件・腰包 0／3");
  });

  it("左欄：商店、鐵匠只在有店或設施時開；再點同一個回到地點圖", () => {
    expect(leftPane(view(), "shop")).toBe("map");
    expect(leftPane(view({ shop: {} } as Partial<WorldView>), "shop")).toBe("shop");
    expect(leftPane(view(), "smithy")).toBe("map");
    expect(leftPane(view(), "bag")).toBe("bag");
    expect(leftPane(view({ inventory: null }), "bag")).toBe("map");
    expect(togglePane("bag", "bag")).toBe("map");
    expect(togglePane("map", "shop")).toBe("shop");
  });
});

describe("WorldBagScreen", () => {
  it("穿戴中 9 格（空的畫空槽）、背包與腰包是格子；選裝備看裝備卡與換上、選物品看說明與使用", () => {
    const html = renderToStaticMarkup(createElement(WorldBagScreen, { view: view(), busy: false, onAct: () => undefined, onClose: () => undefined }));
    expect(html).toContain("背包與裝備");
    expect(html).toContain('data-testid="world-worn-main_hand"');
    expect(html).toMatch(/data-testid="world-worn-ring_1" data-empty="1"[^]*戒指 1：空/);
    expect(html).toContain('data-testid="world-bag"');
    expect(html).toContain('data-testid="world-bag-cell-bag:item_hp_potion_small"');
    expect(html).toContain('data-testid="world-bag-cell-bag:item_gen_ring_1"');
    // 預設選第一格（小回復藥）：說明與「使用」
    expect(html).toContain('data-testid="world-use-item_hp_potion_small"');
    expect(html).toContain("潛影共鳴");
    expect(html).not.toContain("title=");
    const gear = renderToStaticMarkup(
      createElement(WorldBagScreen, { view: view(), busy: false, onAct: () => undefined, onClose: () => undefined, initialPick: "bag:item_gen_ring_1" }),
    );
    expect(gear).toContain('data-testid="gear-card"'); // 一輪的裝備卡（和目前裝備比較）
    expect(gear).toContain('data-testid="world-equip-item_gen_ring_1"');
    expect(gear).toContain("改戴戒指 2");
  });

  it("背包滿時最上方是選要丟哪件；不能換時停用", () => {
    const pending = { items: [POTION], over_slots: 1, hint_zh: "還差 1 格" };
    const v = view({ pending_loot: pending, inventory: inventory({ bag: [POTION, gearRow("item_gen_ring_1", false)] }) } as Partial<WorldView>);
    const html = renderToStaticMarkup(createElement(WorldBagScreen, { view: v, busy: false, onAct: () => undefined, onClose: () => undefined, initialPick: "bag:item_gen_ring_1" }));
    expect(html.indexOf("world-loot-choice")).toBeLessThan(html.indexOf("world-equipped"));
    expect(html).toMatch(/disabled[^>]*data-testid="world-equip-item_gen_ring_1"/);
  });
});

describe("InventorySummary 與商店畫面", () => {
  it("右側摘要：格數、腰包、等著決定的戰利品、打開背包", () => {
    const html = renderToStaticMarkup(createElement(InventorySummary, { inventory: inventory(), pendingLoot: true, open: false, onOpen: () => undefined }));
    expect(html).toContain("2／30 格・裝備 1 件");
    expect(html).toContain('data-testid="world-loot-alert"');
    expect(html).toContain("打開背包（選要丟哪件）");
  });

  it("沒有店時說明；有店時列出商品", () => {
    const none = renderToStaticMarkup(createElement(WorldShopScreen, { view: view(), busy: false, onAct: () => undefined, onClose: () => undefined }));
    expect(none).toContain("這裡沒有店");
    expect(none).toContain("金幣 15・任務幣 2");
  });
});

describe("戰鬥道具欄（8.17）", () => {
  const button = (skillId: string): SkillButton => ({ skillId, name: skillId, costs: [], cooldown: 0, actions: [], disabledReason: null });
  const card = (kind_id: string, tags: string[] = []) => ({ kind_id, tags }) as unknown as SkillCard;
  it("標籤有 item 的技能放進道具欄，不在主動列", () => {
    const cards = { a: card("active"), potion: card("active", ["item", "support"]), p: card("passive") };
    const { main, minor, items } = splitSkills(["a", "potion", "p"].map(button), cards);
    expect(main.map((b) => b.skillId)).toEqual(["a"]);
    expect(items.map((b) => b.skillId)).toEqual(["potion"]);
    expect(minor.map((b) => b.skillId)).toEqual(["p"]);
    expect(isItemSkill(undefined)).toBe(false);
  });
});

describe("事件卡的模板標示（5B-4e #4）", () => {
  const story = (source: WorldStory["source"]): WorldStory => ({ text_zh: "古松樹皮上的焦痕還在發燙。", more_zh: "", source });
  it("只有降級模板標「（模板文字）」；保底的專用旁白不標", () => {
    expect(renderToStaticMarkup(createElement(StoryBlock, { story: story("fallback") }))).toContain("模板文字");
    expect(renderToStaticMarkup(createElement(StoryBlock, { story: story("authored") }))).not.toContain("模板文字");
    expect(renderToStaticMarkup(createElement(StoryBlock, { story: story("llm") }))).not.toContain("模板文字");
  });
});
