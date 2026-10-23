// 裝備測試（Phase 3G-G4）：手動組物品的合法性、整組穿戴的問題、請求格式、加成數值顯示。
// fixtures 是 3G-G4 後端的真實回應（重新產生見 docs/phases/Phase3G-4報告.md）。
import { describe, expect, it } from "vitest";
import type { GearAffixInfo, GearCatalog, GearCheck } from "../api/types";
import catalogFx from "./fixtures/catalog.json";
import cappedFx from "./fixtures/check_capped.json";
import illegalFx from "./fixtures/check_illegal.json";
import {
  affixBlocked,
  affixOptions,
  affixText,
  clampValue,
  defaultValue,
  draftProblems,
  emptyDraft,
  itemSummary,
  occupiesOffHand,
  parseSelection,
  rangeText,
  sanitizeSelection,
  selectionProblems,
  toEquipment,
  totalLine,
  type CustomDraft,
  type Selection,
} from "./gearDraft";

const catalog = catalogFx as unknown as GearCatalog;
const capped = cappedFx as unknown as GearCheck;
const illegal = illegalFx as unknown as GearCheck;

function affix(id: string): GearAffixInfo {
  const found = catalog.affixes.find((a) => a.id === id);
  if (found === undefined) throw new Error(`no affix ${id}`);
  return found;
}

function draft(slotTypeZh: string, patch: Partial<CustomDraft> = {}): CustomDraft {
  return { ...emptyDraft(slotTypeZh), ...patch };
}

describe("詞條文字與數值範圍", () => {
  it("{n} 換成數值；千分比顯示為百分比", () => {
    expect(affixText(affix("affix_attr_str"), 3)).toBe("力量 +3");
    expect(affixText(affix("affix_resist_fire"), 150)).toBe("火焰抗性 +15%");
    expect(affixText(affix("affix_cost_glass"), null)).toBe(affix("affix_cost_glass").name_zh);
  });

  it("範圍文字與預設值取初值範圍的下限", () => {
    expect(rangeText(affix("affix_attr_str"))).toBe("1～4");
    expect(rangeText(affix("affix_resist_fire"))).toBe("5%～15%");
    expect(rangeText(affix("affix_cost_glass"))).toBe("");
    expect(defaultValue(affix("affix_attr_str"))).toBe(1);
    expect(defaultValue(affix("affix_cost_glass"))).toBeNull();
  });

  it("數值限制在初值範圍內，NaN 退回下限", () => {
    const str = affix("affix_attr_str");
    expect(clampValue(str, 99)).toBe(4);
    expect(clampValue(str, -3)).toBe(1);
    expect(clampValue(str, 2.6)).toBe(3);
    expect(clampValue(str, Number.NaN)).toBe(1);
    expect(clampValue(affix("affix_cost_glass"), 7)).toBe(7);
  });
});

describe("手動組物品：只能從白名單選、不合法時顯示原因", () => {
  it("白名單有 31 條、11 類", () => {
    expect(catalog.affixes).toHaveLength(31);
    expect(new Set(catalog.affixes.map((a) => a.category_number)).size).toBe(11);
  });

  it("選單依物品種類標出不能掛的詞條與原因", () => {
    const options = affixOptions(catalog, "ring", draft("戒指"));
    const trig = options.find((o) => o.info.id === "affix_attr_str");
    expect(trig?.blocked).toBeNull();
    const shield = options.find((o) => o.info.id === "affix_act_shield_wall");
    expect(shield?.blocked).toContain("不能出現在");
    const rule = options.find((o) => o.info.id === "affix_rule_fire_mends");
    expect(rule?.blocked).toContain("傳說");
    const legendary = affixOptions(catalog, "ring", draft("戒指", { legendary: true }));
    expect(legendary.find((o) => o.info.id === "affix_rule_fire_mends")?.blocked).toBeNull();
  });

  it("限盾的詞條只能掛在盾上；限定武器的詞條看武器", () => {
    const wall = affix("affix_act_shield_wall");
    expect(affixBlocked(wall, "offhand", draft("副手"), catalog)).toContain("盾");
    expect(affixBlocked(wall, "offhand", draft("副手", { shield: true }), catalog)).toBeNull();
    const hammer = affix("affix_trait_hammer_knockback");
    expect(affixBlocked(hammer, "weapon", draft("武器", { weapon: "one_handed_sword" }), catalog)).toContain("特定武器");
    expect(affixBlocked(hammer, "weapon", draft("武器", { weapon: "hammer" }), catalog)).toBeNull();
  });

  it("沒有詞條、超過上限、重複、數值超出範圍都有中文原因", () => {
    expect(draftProblems(draft("頭"), "head", catalog)).toContain("自訂頭：至少要掛 1 條詞條");
    const five = ["str", "dex", "con", "int", "wis"].map((a) => ({ affix: `affix_attr_${a}`, value: 1 }));
    const tooMany = draftProblems(draft("頭", { affixes: five }), "head", catalog).join("；");
    expect(tooMany).toContain("詞條最多 4 條");
    const dup = draftProblems(
      draft("頭", { affixes: [{ affix: "affix_attr_str", value: 1 }, { affix: "affix_attr_str", value: 2 }] }),
      "head",
      catalog,
    );
    expect(dup.join("；")).toContain("不可重複");
    const range = draftProblems(draft("頭", { affixes: [{ affix: "affix_attr_str", value: 9 }] }), "head", catalog);
    expect(range.join("；")).toContain("超出範圍 1～4");
    const missing = draftProblems(draft("頭", { affixes: [{ affix: "affix_attr_str", value: null }] }), "head", catalog);
    expect(missing.join("；")).toContain("需要數值");
    const unknown = draftProblems(draft("頭", { affixes: [{ affix: "affix_made_up", value: 1 }] }), "head", catalog);
    expect(unknown.join("；")).toContain("不在白名單");
  });

  it("合法的自訂物品沒有問題；主手要選武器", () => {
    const ok = draft("頭", { affixes: [{ affix: "affix_attr_str", value: 4 }] });
    expect(draftProblems(ok, "head", catalog)).toEqual([]);
    const weapon = draft("武器", { affixes: [{ affix: "affix_attr_str", value: 1 }] });
    expect(draftProblems(weapon, "weapon", catalog)).toContain("主手物品要選一種武器");
    expect(draftProblems({ ...weapon, weapon: "one_handed_sword" }, "weapon", catalog)).toEqual([]);
  });
});

describe("整組穿戴", () => {
  const item = (id: string) => ({ item_id: id });

  it("雙手武器占用副手", () => {
    const sel: Selection = { main_hand: item("item_test_hammer"), off_hand: item("item_test_shield") };
    expect(occupiesOffHand(sel, catalog)).toBe(true);
    expect(selectionProblems(sel, catalog).join("；")).toContain("副手被占用");
    const sword: Selection = { main_hand: item("item_test_sword"), off_hand: item("item_test_shield") };
    expect(occupiesOffHand(sword, catalog)).toBe(false);
    expect(selectionProblems(sword, catalog)).toEqual([]);
  });

  it("成對武器與自訂的雙手武器也占用副手", () => {
    expect(occupiesOffHand({ main_hand: item("item_test_twin_daggers") }, catalog)).toBe(true);
    const custom = draft("武器", { weapon: "hammer", affixes: [{ affix: "affix_attr_str", value: 1 }] });
    expect(occupiesOffHand({ main_hand: { custom } }, catalog)).toBe(true);
    const paired = draft("武器", { weapon: "dagger", paired: true, affixes: [{ affix: "affix_attr_str", value: 1 }] });
    expect(occupiesOffHand({ main_hand: { custom: paired } }, catalog)).toBe(true);
  });

  it("同一枚戒指不能裝兩次；兩枚不同的戒指可以", () => {
    const twice: Selection = { ring_1: item("item_test_ring_str"), ring_2: item("item_test_ring_str") };
    expect(selectionProblems(twice, catalog).join("；")).toContain("同一枚戒指不能裝兩次");
    const two: Selection = { ring_1: item("item_test_ring_str"), ring_2: item("item_test_ring_hp") };
    expect(selectionProblems(two, catalog)).toEqual([]);
  });

  it("代價型詞條全身最多 2 條", () => {
    const sel: Selection = {
      feet: item("item_test_boots"), // swift
      main_hand: item("item_test_hammer"), // glass
      ring_1: item("item_test_ring_fire"), // glass
    };
    expect(selectionProblems(sel, catalog).join("；")).toContain("代價型詞條全身最多 2 條（目前 3 條）");
    const { ring_1: _drop, ...two } = sel;
    expect(selectionProblems(two, catalog)).toEqual([]);
  });

  it("物品種類不符欄位", () => {
    const sel: Selection = { head: item("item_test_boots") };
    expect(selectionProblems(sel, catalog).join("；")).toContain("頭只能放頭類物品");
  });

  it("自訂物品的問題也算進整組檢查", () => {
    const bad = draft("頭", { affixes: [{ affix: "affix_attr_str", value: 9 }] });
    expect(selectionProblems({ head: { custom: bad } }, catalog).join("；")).toContain("超出範圍");
  });
});

describe("請求格式", () => {
  it("欄位 → 物品 id 或自訂物品（依欄位固定順序）", () => {
    const sel: Selection = {
      neck: { custom: draft("項鍊", { name: "護符", affixes: [{ affix: "affix_max_hp", value: 8 }] }) },
      main_hand: { custom: draft("武器", { weapon: "hammer", kind: "hammer", affixes: [{ affix: "affix_attr_str", value: 2 }] }) },
      head: { item_id: "item_test_helm" },
    };
    const eq = toEquipment(sel, catalog);
    expect(Object.keys(eq)).toEqual(["main_hand", "head", "neck"]);
    expect(eq["head"]).toEqual({ item_id: "item_test_helm" });
    expect(eq["neck"]?.custom).toMatchObject({ name_zh: "護符", weapon: null, paired: false, tags: [], kind: null });
    expect(eq["main_hand"]?.custom).toMatchObject({ weapon: "hammer", kind: "hammer", affixes: [{ affix: "affix_attr_str", value: 2 }] });
  });

  it("副手的盾標籤只送給副手；武器欄位以外不送 weapon", () => {
    const off = draft("副手", { shield: true, weapon: "hammer", affixes: [{ affix: "affix_max_hp", value: 4 }] });
    const eq = toEquipment({ off_hand: { custom: off } }, catalog);
    expect(eq["off_hand"]?.custom).toMatchObject({ tags: ["shield"], weapon: null });
  });

  it("物品清單的摘要把詞條接在一起", () => {
    const sword = catalog.items.find((i) => i.id === "item_test_sword");
    expect(sword && itemSummary(sword)).toBe("力量 +2；站在高處時命中 +1");
  });
});

describe("暫存", () => {
  it("壞掉的暫存不會讓畫面壞掉；目錄不認得的物品會被丟掉", () => {
    expect(parseSelection(null)).toEqual({});
    expect(parseSelection("{not json")).toEqual({});
    expect(parseSelection("[1]")).toEqual({});
    const sel: Selection = { head: { item_id: "item_test_helm" }, neck: { item_id: "item_gone" }, bogus: { item_id: "item_test_ring_hp" } };
    expect(sanitizeSelection(sel, catalog)).toEqual({ head: { item_id: "item_test_helm" } });
  });
});

describe("加成來源的數值顯示（後端的真實回應）", () => {
  it("不合法的回應有中文原因、沒有英雄", () => {
    expect(illegal.legal).toBe(false);
    expect(illegal.hero ?? null).toBeNull();
    expect(illegal.problems.join("；")).toContain("超出範圍");
  });

  it("傷害加成超過上限：合計那一行標出截斷前與截斷後的實際值", () => {
    expect(capped.legal).toBe(true);
    const totals = capped.hero?.gear_totals ?? [];
    const total = totals.find((t) => t.key === "damage_permille:total");
    expect(total).toBeDefined();
    if (total === undefined) return;
    expect(total.value).toBe(500);
    expect(total.before_cap).toBeGreaterThan(500);
    expect(total.capped).toBe(true);
    const line = totalLine(total);
    expect(line.badge).toBe("已截斷");
    expect(line.main).toContain("+50%");
    expect(line.main).toContain(`截斷前 +${total.before_cap / 10}%`);
  });

  it("條件數值標出條件；遞減在來源裡標出權重", () => {
    const totals = capped.hero?.gear_totals ?? [];
    const cond = totals.find((t) => t.condition_zh != null && t.key.startsWith("damage_permille"));
    expect(cond && totalLine(cond).main).toContain("條件：自身血量低於 50%");
    expect(cond?.sources_zh.some((s) => s.includes("遞減：50%"))).toBe(true);
    expect(cond?.sources_zh.some((s) => s.includes("遞減：不生效"))).toBe(true);
  });

  it("每一行都有來源（合計行除外）與說明", () => {
    for (const t of capped.hero?.gear_totals ?? []) {
      expect(totalLine(t).main.length).toBeGreaterThan(0);
      expect(t.note_zh).not.toBe("");
      if (t.key !== "damage_permille:total") {
        expect(t.note_zh).toContain("來自裝備");
        expect(t.sources_zh.length).toBeGreaterThan(0);
      }
    }
  });
});

describe("副手種類（3I-2）", () => {
  it("自訂副手送出 offhand，其他欄位不送", () => {
    const affixes = [{ affix: "affix_max_hp", value: 4 }];
    const sel: Selection = { off_hand: { custom: draft("副手", { offhand: "tower_shield", affixes }) } };
    expect((toEquipment(sel, catalog).off_hand?.custom as { offhand?: string | null }).offhand).toBe("tower_shield");
    const head: Selection = { head: { custom: draft("頭", { offhand: "tome", affixes }) } };
    expect((toEquipment(head, catalog).head?.custom as { offhand?: string | null }).offhand).toBeNull();
  });
});
