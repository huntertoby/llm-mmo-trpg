// 重複詞條標灰與裝備比較預測（Phase 3-32b）。
import { describe, expect, it } from "vitest";
import type { AffixLineView, GearCatalog, GearItemInfo } from "../api/types";
import catalogFx from "./fixtures/catalog.json";
import { compareItem, inactiveNote, tipLines } from "./affixStatus";
import { emptyDraft, type Selection } from "./gearDraft";

const catalog = catalogFx as unknown as GearCatalog;

function line(over: Partial<AffixLineView>): AffixLineView {
  return { affix_id: "affix_attack_mark", category: "attack", category_zh: "普攻附加", text_zh: "普攻標記", active: true, weight_permille: 1000, ...over };
}

function candidate(affixIds: string[]): GearItemInfo {
  return {
    id: "test_item",
    name_zh: "測試物",
    slot_type: "head",
    two_handed: false,
    offhand_traits_zh: [],
    paired: false,
    tags: [],
    legendary: false,
    affixes: affixIds.map((id) => ({ affix_id: id, text_zh: `詞條 ${id}` })),
    appearance: { rarity: "common", keywords: [] },
  } as GearItemInfo;
}

function custom(slotTypeZh: string, affixIds: string[]) {
  return { custom: { ...emptyDraft(slotTypeZh), affixes: affixIds.map((affix) => ({ affix, value: null })) } };
}

describe("沒生效的詞條標灰", () => {
  it("生效中的沒有註記", () => {
    expect(inactiveNote(line({}))).toBeNull();
    expect(tipLines([line({})])).toEqual([{ text: "普攻標記", note: null }]);
  });

  it("重複詞條註明和哪一條重複", () => {
    const dup = line({ active: false, weight_permille: 0, duplicate_of: "主手的每第 2 次普攻命中：造成 5 點傷害" });
    expect(inactiveNote(dup)).toBe("和主手的每第 2 次普攻命中：造成 5 點傷害重複，沒有效果");
    expect(tipLines([dup])[0]?.note).toContain("重複，沒有效果");
  });

  it("遞減到 0 權重但不是重複（沒有 duplicate_of）也有說明", () => {
    expect(inactiveNote(line({ active: false, weight_permille: 0 }))).toContain("沒有效果");
  });

  it("授予的技能在這名角色身上沒有效果（E5）時標灰並寫原因", () => {
    const off = line({ category: "action", off_zh: "這把武器不能套用" });
    expect(inactiveNote(off)).toBe("這把武器不能套用");
    expect(tipLines([off])[0]?.note).toBe("這把武器不能套用");
  });

  it("地形規則和種族重複（E2）：標灰並寫種族被動", () => {
    const dup = line({ category: "terrain", active: false, weight_permille: 0, duplicate_of: "種族被動「炎膚」" });
    expect(tipLines([dup])[0]?.note).toBe("和種族被動「炎膚」重複，沒有效果");
  });

  it("地形規則部分重疊（E2）：不標灰，另外註明重疊的部分", () => {
    const part = line({ category: "terrain", text_zh: "冰上水上不滑倒", overlap_zh: "冰的部分和種族重複" });
    expect(tipLines([part])).toEqual([{ text: "冰上水上不滑倒", note: null, aside: "冰的部分和種族重複" }]);
  });
});

describe("裝備比較預測", () => {
  const mark = "affix_attack_mark";

  it("換上和別的欄位同 id 的非數值詞條 → 標灰並指出是哪一格", () => {
    const selection: Selection = { main_hand: custom("武器", [mark]) };
    const changes = compareItem(catalog, selection, "head", candidate([mark]));
    expect(changes).toHaveLength(1);
    expect(changes[0]?.kind).toBe("gray");
    expect(changes[0]?.note).toContain("主手");
  });

  it("數值類詞條不預測（遞減由伺服器裁決）", () => {
    const numeric = catalog.affixes.find((a) => a.category === "stat");
    expect(numeric).toBeDefined();
    const id = numeric?.id ?? "";
    const selection: Selection = { main_hand: custom("武器", [id]) };
    expect(compareItem(catalog, selection, "head", candidate([id]))).toEqual([]);
  });

  it("換掉原本重複的那件 → 另一條恢復生效", () => {
    const selection: Selection = { main_hand: custom("武器", [mark]), head: custom("頭部", [mark]) };
    const changes = compareItem(catalog, selection, "head", candidate([]));
    expect(changes).toHaveLength(1);
    expect(changes[0]?.kind).toBe("restore");
    expect(changes[0]?.note).toContain("恢復生效");
  });

  it("換成同樣有該詞條的物品，重複不變 → 不列恢復", () => {
    const selection: Selection = { main_hand: custom("武器", [mark]), head: custom("頭部", [mark]) };
    const kinds = compareItem(catalog, selection, "head", candidate([mark])).map((c) => c.kind);
    expect(kinds).toEqual(["gray"]);
  });

  it("沒有重複 → 沒有變化", () => {
    expect(compareItem(catalog, {}, "head", candidate([mark]))).toEqual([]);
  });
});
