// UI-E3 面板圖示化（docs/art/全遊戲一致性巡檢.md #7、#8、#9；偷懶自查 G2～G4）：背包格子、技能面板用技能卡、遇敵卡頭像。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { SkillCard, WorldBagItem, WorldInventory, WorldView } from "../api/types";
import cards from "../ui/fixtures/skillCards.json";
import { cardCosts } from "../ui/SkillTile";
import { HudSkillsPanel } from "./HudPanels";
import { bagCells, BAG_COLS, cellHint, pickedCell, pouchCells, tileName } from "./bagGrid";
import { BagContents } from "./BagScreen";
import { HIRE_ICON_MAX, matchSkills, themeSkillIds } from "./hireSkills";
import { SkillIconRow } from "./PartyPanel";

function row(item: string, over: Partial<WorldBagItem> = {}): WorldBagItem {
  return {
    item,
    name_zh: item,
    kind_zh: "材料",
    count: 1,
    description_zh: "",
    sell_price: 1,
    sellable: true,
    tradable: false,
    field_usable: false,
    gear: false,
    can_equip: false,
    ...over,
  } as WorldBagItem;
}

function inv(over: Partial<WorldInventory> = {}): WorldInventory {
  return {
    bag: [row("a"), row("b", { gear: true, kind_zh: "裝備", cross_class_zh: "別大類：可交易", cross_class_lost_zh: "換上後不能用：戰歌" })],
    slots_used: 2,
    slots_max: 30,
    pouch: [row("p", { count: 2 })],
    pouch_count: 2,
    pouch_max: 3,
    can_pouch: true,
    pouch_problem_zh: null,
    consumables: [],
    equipped_zh: [],
    resonance_zh: [],
    equipment: [],
    gear_cards: [],
    ...over,
  } as WorldInventory;
}

describe("背包格子（#7、G2）", () => {
  it("6 欄 × 5 列：每一筆一格，空格補到上限", () => {
    const cells = bagCells(inv());
    expect(BAG_COLS).toBe(6);
    expect(cells).toHaveLength(30);
    expect(cells.filter((c) => c.kind === "thing").map((c) => c.key)).toEqual(["bag:a", "bag:b"]);
  });

  it("一種物品佔多格（超過疊數）時空格照伺服器的格數少畫，但補滿整列；超出上限時照樣全部畫出", () => {
    expect(bagCells(inv({ slots_used: 4 }))).toHaveLength(30); // 2 筆＋26 空＝28 → 補滿到 30
    const over = bagCells(inv({ bag: Array.from({ length: 31 }, (_, i) => row(`x${i}`)), slots_used: 31 }));
    expect(over.filter((c) => c.kind === "thing")).toHaveLength(31);
    expect(over.length % BAG_COLS).toBe(0);
  });

  it("腰包補到上限；選取找不到時退回第一格有東西的", () => {
    const pouch = pouchCells(inv());
    expect(pouch.map((c) => c.kind)).toEqual(["thing", "empty", "empty"]);
    const all = [...bagCells(inv()), ...pouch];
    expect(pickedCell(all, "pouch:p")?.key).toBe("pouch:p");
    expect(pickedCell(all, "nope")?.key).toBe("bag:a");
    expect(pickedCell(bagCells(inv({ bag: [], slots_used: 0 })), null)).toBeNull();
  });

  it("格子上的名字最多 4 個字（括號拿掉），滑過的說明寫全名與個數", () => {
    expect(tileName("小回復藥")).toBe("小回復藥");
    expect(tileName("稀有戒指（3 級）")).toBe("稀有戒指");
    expect(tileName("源晶碎片精華")).toBe("源晶碎…");
    expect(cellHint(row("a", { name_zh: "小回復藥", kind_zh: "消耗品", count: 2 }))).toBe("小回復藥・消耗品・×2");
  });

  it("別大類的武器：格子有角標，選了之後詳情照舊有兩行字（6T-1b）", () => {
    const card = { item: { id: "b", name_zh: "鐵劍", slot_type: "weapon", affixes: [], tags: [] }, slot: "main_hand", slot_zh: "主手", current: null, notes_zh: [] };
    const html = renderToStaticMarkup(
      createElement(BagContents, { inventory: inv({ gear_cards: [card] } as unknown as Partial<WorldInventory>), busy: false, onAct: () => undefined, canUse: true, initialPick: "bag:b" }),
    );
    expect(html).toMatch(/class="world-bag-cell picked gear cross"/);
    expect(html).toContain("別大類：可交易");
    expect(html).toContain("換上後不能用：戰歌");
    expect(html).toContain('data-testid="world-equip-b"');
    expect(html).toContain('data-testid="world-pouch-toggle"');
  });
});

const card = (id: keyof typeof cards) => cards[id] as unknown as SkillCard;

describe("技能面板用技能卡（#8、G3）", () => {
  it("花費行同戰鬥底列：主動照卡片、被動／反應另標", () => {
    expect(cardCosts(card("skill_ash_harvest"))).toEqual(["AP 2", "法力 4", "冷卻 2 回合"]);
    expect(cardCosts(card("skill_counterspell"))[0]).toBe("被動／反應");
  });

  it("裝備中與備用都是技能卡（.skill-button＋組裝式圖示）；別大類不能用的灰掉，不再是條列文字", () => {
    const view = {
      character: {
        skills: [card("skill_ash_harvest"), card("skill_gale_kick")],
        bench: [card("skill_downpour")],
        slots_zh: "主動 6",
        weapon_blocked: ["skill_gale_kick"],
        weapon_blocked_zh: "主手別大類",
      },
      here: { can_loadout: false },
    } as unknown as WorldView;
    const html = renderToStaticMarkup(createElement(HudSkillsPanel, { view, busy: false, onAct: () => undefined }));
    expect(html).toContain('data-testid="world-skill-tiles"');
    expect(html.match(/class="skill-button( blocked)?"/g)).toHaveLength(3);
    expect(html.match(/class="skill-icon skill-button-icon"/g)).toHaveLength(3);
    expect(html).toMatch(/data-testid="world-skill-skill_gale_kick" data-blocked="1"/);
    expect(html).toContain('data-testid="world-bench-skill_downpour"');
    expect(html).not.toContain("<li");
    expect(html).not.toContain("title=");
  });
});

describe("雇用面板的技能圖示列（RT-4 檢查第 20 行）", () => {
  const builds = [
    { theme_zh: "火焰", skills: ["skill_ash_harvest", "skill_downpour"] },
    { theme_zh: "疾風", skills: ["skill_gale_kick", "skill_ash_harvest"] },
  ];
  it("同主題句的 build 的技能 ID（照順序、去重）", () => {
    expect(themeSkillIds(["火焰"], builds)).toEqual(["skill_ash_harvest", "skill_downpour"]);
    expect(themeSkillIds(["火焰", "疾風"], builds)).toEqual(["skill_ash_harvest", "skill_downpour", "skill_gale_kick"]);
    expect(themeSkillIds(["沒有"], builds)).toEqual([]);
  });

  it("名字對上卡片才畫圖示，最多 8 個，其餘「+N」；對不上的照舊寫字", () => {
    const all = [card("skill_ash_harvest"), card("skill_gale_kick")];
    const names = [all[0]!.name_zh, "不存在的招", all[1]!.name_zh, ...Array.from({ length: 8 }, (_, i) => `招${i}`)];
    const m = matchSkills(names, all);
    expect(HIRE_ICON_MAX).toBe(8);
    expect(m.shown).toHaveLength(8);
    expect(m.shown[0]?.card?.id).toBe("skill_ash_harvest");
    expect(m.shown[1]?.card).toBeNull();
    expect(m.rest).toHaveLength(3);
    const html = renderToStaticMarkup(createElement(SkillIconRow, { ...matchSkills(names.slice(0, 3), all), testId: "row" }));
    expect(html.match(/class="skill-icon"/g)).toHaveLength(2);
    expect(html).toContain(`aria-label="${all[0]!.name_zh}"`);
    expect(html).toContain("不存在的招");
    expect(html).not.toContain("技能：");
    expect(html).not.toContain("title=");
  });
});
