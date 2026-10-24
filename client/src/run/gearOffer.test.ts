import { describe, expect, it } from "vitest";
import type { GearCandidate, GearItemInfo, RunNode, RunResponse } from "../api/types";
import { itemSummary } from "../gear/gearDraft";
import { displayOrder, runView, saveLabel } from "./flow";
import {
  compareText,
  compareTone,
  equipChoice,
  gearPickChoice,
  itemLines,
  itemSubtitle,
  itemTipLines,
  noteLines,
  rarityClass,
  wornGear,
} from "./gearOffer";

function item(over: Partial<GearItemInfo> = {}): GearItemInfo {
  return {
    id: "item_gen_body_1",
    name_zh: "稀有外套",
    slot_type: "body",
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

function cand(over: Partial<GearCandidate> = {}): GearCandidate {
  return { item: item(), slot: "body", slot_zh: "身體", current: null, notes_zh: [], ...over } as GearCandidate;
}

describe("裝備卡的文字", () => {
  it("詞條行：普通物品先寫基礎加成，再寫副手特性與詞條", () => {
    const plain = item({ affixes: [], base_bonus_zh: "基礎加成：防禦值 +2%", rarity: "common", rarity_zh: "普通" });
    expect(itemLines(plain)).toEqual(["基礎加成：防禦值 +2%"]);
    const shield = item({
      slot_type: "offhand",
      offhand_name_zh: "圓盾",
      offhand_traits_zh: ["格擋多減傷"],
      affixes: [{ affix_id: "a", text_zh: "體質 +2" }],
    } as Partial<GearItemInfo>);
    expect(itemLines(shield)).toEqual(["圓盾：格擋多減傷", "體質 +2"]);
    expect(itemSummary(plain)).toBe("基礎加成：防禦值 +2%");
  });

  it("沒有任何內容的物品，說明卡寫「沒有詞條」", () => {
    expect(itemTipLines(item({ affixes: [] }))).toEqual([{ text: "（沒有詞條）", note: null }]);
  });

  it("副標題：稀有度・物品等級・武器資訊", () => {
    const sword = item({ weapon_name_zh: "巨劍", two_handed: true, slot_type: "weapon" } as Partial<GearItemInfo>);
    expect(itemSubtitle(sword)).toBe("稀有・Lv3・巨劍・雙手");
    expect(itemSubtitle(item({ rarity_zh: null, rarity: null, legendary: true, item_level: null }))).toBe("傳說");
  });

  it("稀有度 class：沒標稀有度的傳說物品當傳說", () => {
    expect(rarityClass(item())).toBe("gear-rarity-rare");
    expect(rarityClass({ rarity: null, legendary: true })).toBe("gear-rarity-legendary");
    expect(rarityClass({ rarity: null, legendary: false })).toBe("gear-rarity-common");
  });
});

describe("和目前裝備的比較", () => {
  it("有目前裝備：寫兩邊的預算分數與差", () => {
    const c = cand({ current: item({ points: 8 }) });
    expect(compareText(c)).toBe("預算分數 8 → 12（+4）");
    expect(compareTone(c)).toBe("up");
    const worse = cand({ item: item({ points: 6.5 }), current: item({ points: 8 }) });
    expect(compareText(worse)).toBe("預算分數 8 → 6.5（−1.5）");
    expect(compareTone(worse)).toBe("down");
  });

  it("欄位空著：寫目前沒有裝備", () => {
    expect(compareText(cand())).toBe("預算分數 12（目前沒有裝備）");
    expect(compareTone(cand())).toBe("up");
  });

  it("連帶效果直接取後端給的行", () => {
    expect(noteLines(cand({ notes_zh: ["副手「圓盾」被占用，收進背包"] }))).toEqual(["副手「圓盾」被占用，收進背包"]);
  });
});

describe("送出的請求", () => {
  it("三選一：索引或跳過；營火換裝帶物品 id（與欄位）", () => {
    expect(gearPickChoice(1)).toEqual({ kind: "gear_pick", pick: 1 });
    expect(gearPickChoice(null)).toEqual({ kind: "gear_pick", pick: null });
    expect(equipChoice("x")).toEqual({ kind: "equip", item_id: "x" });
    expect(equipChoice("x", "ring_2")).toEqual({ kind: "equip", item_id: "x", slot: "ring_2" });
  });
});

describe("角色面板的穿戴裝備", () => {
  it("基礎武器（base_ 開頭）與空欄位不算", () => {
    const hero = {
      equipment: [
        { slot: "main_hand", slot_zh: "主手", item: item({ id: "base_one_handed_sword" }) },
        { slot: "head", slot_zh: "頭", item: null },
        { slot: "body", slot_zh: "身體", item: item() },
      ],
    };
    expect(wornGear(hero as never).map((s) => s.slot)).toEqual(["body"]);
    expect(wornGear({} as never)).toEqual([]);
  });
});

describe("runView：裝備三選一節點", () => {
  const node = {
    kind: "gear_offer",
    gear: { after_battle: 2, candidates: [cand(), cand({ slot: "head", slot_zh: "頭" })] },
  } as unknown as RunNode;
  const res = { run_id: "a", seed: 7, node, hero: { level: 1, skills: [] }, plan: [], history: [], battles_done: 2 } as unknown as RunResponse;

  it("畫面是 gear_offer，帶場次與候選", () => {
    const v = runView(res);
    expect(v.screen).toBe("gear_offer");
    if (v.screen === "gear_offer") {
      expect(v.afterBattle).toBe(2);
      expect(v.candidates).toHaveLength(2);
    }
  });

  it("缺少候選時拋錯（畫面顯示錯誤而不是空白）", () => {
    expect(() => runView({ ...res, node: { kind: "gear_offer" } as unknown as RunNode })).toThrow("裝備三選一");
  });

  it("顯示順序由種子決定、同一組固定", () => {
    expect(displayOrder(7, "gear:2", 3)).toEqual(displayOrder(7, "gear:2", 3));
    expect([...displayOrder(7, "gear:2", 3)].sort()).toEqual([0, 1, 2]);
  });

  it("存檔列表寫得出裝備三選一", () => {
    expect(saveLabel({ node: "gear_offer", battles_done: 2, battles_total: 6, in_battle: false, level: 1 })).toContain(
      "裝備三選一",
    );
  });
});
