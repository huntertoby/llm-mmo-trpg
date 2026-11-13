// UI-E3 面板圖示化（docs/art/全遊戲一致性巡檢.md #7、#8、#9；偷懶自查 G2～G4）：背包格子、技能面板用技能卡、遇敵卡頭像。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { type SkillCard, type WorldBagItem, type WorldInventory, type WorldView } from "../api/types";
import { cardCosts } from "../ui/SkillTile";
import { HudSkillsPanel } from "./HudPanels";
import { bagCells, BAG_COLS, cellHint, pickedCell, pouchCells, TILE_LINE_CHARS, tileLines } from "./bagGrid";
import { BagContents } from "./BagScreen";
import { HIRE_ICON_MAX, pairSkills } from "./hireSkills";
import { SkillIconRow } from "./PartyPanel";
import { alphaBounds, ENEMY_THUMB_SIZE, enemyThumbUrl, thumbDraw, thumbRing, type EncounterEnemy, type EnemyLook } from "./enemyThumb";
import { EncounterPanel } from "./WorldPanel";
import cards from "../ui/fixtures/skillCards.json";
import boss from "../dev/fixtures/encounterBoss.json";

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

  it("滑過的說明寫全名與個數", () => {
    expect(cellHint(row("a", { name_zh: "小回復藥", kind_zh: "消耗品", count: 2 }))).toBe("小回復藥・消耗品・×2");
    const shield = row("g", { name_zh: "稀有塔盾（5 級）", kind_zh: "裝備", gear: true });
    expect(cellHint(shield)).toBe("稀有塔盾（5 級）・裝備");
    expect(cellHint(shield, "雲紋碑盾")).toBe("稀有塔盾（5 級）・雲紋碑盾・裝備"); // RG-8 K-1
  });

  it("名字小牌（UI-E3c #11）：每行最多 3 字、最多 2 行，只在詞與詞之間換行（不拆詞）", () => {
    expect(TILE_LINE_CHARS).toBe(3);
    expect(tileLines("狼皮")).toEqual(["狼皮"]);
    expect(tileLines("鐵礦石")).toEqual(["鐵礦石"]);
    expect(tileLines("小回復藥")).toEqual(["小", "回復藥"]);
    expect(tileLines("霧青染料")).toEqual(["霧青", "染料"]);
    expect(tileLines("稀有戒指（3 級）")).toEqual(["稀有", "戒指"]);
    for (const name of ["小回復藥", "霧青染料", "大回復藥水", "源晶碎片精華", "一二三四五六七八"]) {
      const lines = tileLines(name);
      expect(lines.length).toBeLessThanOrEqual(2);
      for (const l of lines) expect([...l].length).toBeLessThanOrEqual(TILE_LINE_CHARS);
    }
    expect(tileLines("小回復藥").join("")).toBe("小回復藥");
    expect(tileLines("一二三四五六七八")[1]).toMatch(/…$/);
  });

  // QI-7：名字小牌只剩物品圖示表裡沒有的 id 在用（"p" 不在表裡），斷言照舊
  it("名字小牌（圖示表裡沒有的物品）：個數放在小牌外面（不壓框）", () => {
    const html = renderToStaticMarkup(
      createElement(BagContents, { inventory: inv({ bag: [row("p", { name_zh: "小回復藥", count: 3 })], slots_used: 1 }), busy: false, onAct: () => undefined, canUse: true }),
    );
    expect(html).toContain('<span class="world-bag-tile-line">小</span><span class="world-bag-tile-line">回復藥</span>');
    expect(html).toMatch(/<\/span><b class="world-bag-count">3<\/b>/);
  });

  it("QI-7：圖示表裡有的物品畫 42 的 Q 版圖示（背包框、畫布 84），不畫名字小牌；個數照現行", () => {
    const html = renderToStaticMarkup(
      createElement(BagContents, { inventory: inv({ bag: [row("item_hp_potion_small", { name_zh: "小回復藥", count: 3 })], slots_used: 1, pouch: [] }), busy: false, onAct: () => undefined, canUse: true }),
    );
    expect(html).toMatch(/<canvas class="item-icon item-icon-bag" width="84" height="84" style="width:42px;height:42px" data-item-icon="item_hp_potion_small"[^>]*><\/canvas><b class="world-bag-count">3<\/b>/);
    expect(html).not.toContain("world-bag-tile");
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

describe("雇用面板的技能圖示列（RT-4 檢查第 20 行；UI-E3b 改用 skill_ids）", () => {
  it("照 skill_ids 一一配對卡片，最多 8 個，其餘「+N」；查不到卡片的照舊寫字", () => {
    const a = card("skill_ash_harvest");
    const b = card("skill_gale_kick");
    const cards = { [a.id]: a, [b.id]: b };
    const names = [a.name_zh, "影子的生成招", b.name_zh, ...Array.from({ length: 8 }, (_, i) => `招${i}`)];
    const ids = [a.id, "gen_x", b.id, ...Array.from({ length: 8 }, (_, i) => `id${i}`)];
    const m = pairSkills(names, ids, cards);
    expect(HIRE_ICON_MAX).toBe(8);
    expect(m.shown).toHaveLength(8);
    expect(m.shown[0]?.card?.id).toBe("skill_ash_harvest");
    expect(m.shown[1]?.card).toBeNull();
    expect(m.shown[2]?.card?.id).toBe("skill_gale_kick");
    expect(m.rest).toHaveLength(3);
    const html = renderToStaticMarkup(createElement(SkillIconRow, { ...pairSkills(names.slice(0, 3), ids.slice(0, 3), cards), testId: "row" }));
    expect(html.match(/class="skill-icon"/g)).toHaveLength(2);
    expect(html).toContain(`aria-label="${a.name_zh}"`);
    expect(html).toContain("影子的生成招");
    expect(html).not.toContain("技能：");
    expect(html).not.toContain("title=");
  });

  it("用 ID 配對、不看名字：同名不同 ID 不會畫錯圖示；ID 比名字少時多的名字寫字", () => {
    const a = card("skill_ash_harvest");
    const m = pairSkills([a.name_zh, a.name_zh], ["other_id", a.id], { [a.id]: a });
    expect(m.shown.map((s) => s.card?.id ?? null)).toEqual([null, "skill_ash_harvest"]);
    expect(pairSkills(["甲", "乙"], ["skill_ash_harvest"], { skill_ash_harvest: a }).shown[1]?.card).toBeNull();
  });
});

// --- 原 uiE3b.test.ts ---
describe("原 uiE3b.test.ts", () => {
// UI-E3b（巡檢 #9、偷懶自查 G4）：遇敵卡每名敵人前面的小頭像（戰場紙娃娃縮圖）與精英、Boss 金環。

const enemies = boss.enemies as unknown as EncounterEnemy[];
const hound: EnemyLook = {
  template_id: "ash_hound",
  doll_look: { creature: { body: "hound", size: "medium" } } as EnemyLook["doll_look"],
  weapon_id: "unarmed",
  weapon_class: "melee",
  race_look: null,
  equipment: [],
};

describe("縮圖要畫的東西", () => {
  it("人形照戰場的紙娃娃規格（Boss 帶外光 rarity）；異形照戰場的異形外觀", () => {
    const master = enemies.find((e) => e.rank === "boss");
    expect(master?.look).toBeTruthy();
    const d = thumbDraw(master!.look!, "boss");
    expect(d.kind).toBe("doll");
    if (d.kind === "doll") expect(d.spec.rarity).toBe(master!.look!.doll_look?.rarity);
    const c = thumbDraw(hound, "normal");
    expect(c.kind).toBe("creature");
    if (c.kind === "creature") expect(c.creature.body).toBe("hound");
  });

  it("精英的異形照戰場放大（裁邊後大小一樣，只是解法和戰場一致）", () => {
    const a = thumbDraw(hound, "normal");
    const b = thumbDraw(hound, "elite");
    if (a.kind === "creature" && b.kind === "creature") expect(b.creature.size).toBeGreaterThan(a.creature.size);
  });

  it("框：Boss、精英金環，第三方紫，其他一般", () => {
    expect(thumbRing({ rank: "boss", third: false })).toBe("boss");
    expect(thumbRing({ rank: "elite", third: false })).toBe("elite");
    expect(thumbRing({ rank: "normal", third: true })).toBe("third");
    expect(thumbRing({ rank: "normal", third: false })).toBe("normal");
  });

  it("裁邊：不透明像素的外框；全透明是 null", () => {
    const w = 4;
    const h = 3;
    const data = new Uint8ClampedArray(w * h * 4);
    expect(alphaBounds(data, w, h)).toBeNull();
    data[(1 * w + 2) * 4 + 3] = 255;
    data[(2 * w + 1) * 4 + 3] = 200;
    expect(alphaBounds(data, w, h)).toEqual({ x: 1, y: 1, w: 2, h: 2 });
  });

  it("沒有 DOM（伺服器輸出、測試）時沒有圖片網址", () => {
    expect(enemyThumbUrl(hound, "normal")).toBeNull();
  });
});

describe("遇敵卡", () => {
  it("每名敵人前面一個頭像框，Boss 金環＋外光、其餘一般；名字照舊是字", () => {
    const view = { encounter: boss } as unknown as WorldView;
    const html = renderToStaticMarkup(createElement(EncounterPanel, { view, busy: false, onAct: () => undefined, onBattle: () => undefined }));
    expect(html.match(/class="enemy-thumb /g)).toHaveLength(enemies.length);
    expect(html).toContain('class="enemy-thumb boss" data-ring="boss"');
    expect(html.match(/data-ring="normal"/g)).toHaveLength(enemies.filter((e) => e.rank === "normal").length);
    expect(html).toContain(`width:${ENEMY_THUMB_SIZE}px`);
    expect(html).toContain("霧鎖真人");
    expect(html).toContain('<span class="world-elite-tag">頭目</span>');
    expect(html).toContain('data-rank="boss"');
    expect(html).not.toContain("title=");
  });
});
});
