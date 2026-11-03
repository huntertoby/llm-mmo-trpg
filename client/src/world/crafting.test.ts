// 鐵匠與附魔台（Phase 5D-3）：打造表單的純函式與面板的靜態輸出。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldCraftGear, WorldCrafting } from "../api/types";
import { craftAction, draftProblem, initialDraft, toggleMaterial, withSlot } from "./crafting";
import { codeProblem, normalizeCode } from "./bagView";
import { SmithyPanel, smithyTabs, type SmithyTab } from "./SmithyPanel";

function gear(overrides: Partial<WorldCraftGear> = {}): WorldCraftGear {
  return {
    item: "item_craft_abc_1",
    name_zh: "稀有墜飾（1 級）",
    worn: false,
    description_zh: "你施加的燃燒 +1 回合",
    code: "ABCDEF0123",
    enhance: 0,
    can_enhance: false,
    enhance_zh: "強化到 +1：粗料 ×1、金幣 10（材料不夠：item_coarse_material（要 1，有 0））",
    can_salvage: true,
    salvage_zh: "分解得到精華 ×2",
    reroll_zh: "精華 ×1、金幣 20",
    imbue_zh: "精華 ×3、金幣 60",
    affixes: [
      { index: 0, text_zh: "你施加的燃燒 +1 回合", can_change: true, choices: [{ id: "affix_kw_shock_area", text_zh: "雷電技能範圍 +1" }] },
    ],
    ...overrides,
  };
}

function crafting(overrides: Partial<WorldCrafting> = {}): WorldCrafting {
  return {
    stations: [
      { station: "smithy_mist_ferry", kind: "smithy", name_zh: "石記鐵鋪", npc_name_zh: "石師傅" },
      { station: "enchanter_mist_ferry", kind: "enchanter", name_zh: "渡口附魔台", npc_name_zh: null },
    ],
    smithy: "smithy_mist_ferry",
    enchanter: "enchanter_mist_ferry",
    can_use: true,
    problem_zh: null,
    slots: [
      { slot_type: "weapon", name_zh: "武器", grade_amount: 3, affixes: [] },
      { slot_type: "neck", name_zh: "項鍊", grade_amount: 1, affixes: [{ id: "affix_kw_burn_duration", text_zh: "你施加的燃燒 +1 回合" }] },
      { slot_type: "body", name_zh: "身體", grade_amount: 2, affixes: [{ id: "affix_cond_still_defense", text_zh: "本回合沒有移動：防禦 +4%" }] },
    ],
    rarities: [
      { rarity: "rare", name_zh: "稀有", cost_zh: "金幣 10 × 物品等級" },
      { rarity: "epic", name_zh: "史詩", cost_zh: "金幣 20 × 物品等級＋任務幣 2" },
    ],
    materials: [
      { item: "item_coarse_material", name_zh: "粗料", count: 3, grade: true, level_cap: 1, leaning_zh: null, resonance_zh: null },
      { item: "item_mist_crystal", name_zh: "霧晶", count: 1, grade: false, level_cap: null, leaning_zh: "傾向：敏捷 +n", resonance_zh: "共鳴：隱蔽" },
    ],
    flavor_max: 3,
    recipes: [
      { code: "ABCDEF0123", name_zh: "稀有墜飾", summary_zh: "項鍊・稀有・物品等級 1・粗料", discoverer_name: "阿霧", mine: true, can_craft: false, problem_zh: "材料不夠" },
    ],
    gear: [gear()],
    essence: 0,
    note_zh: "沒人試過的材料組合只看得到傾向",
    ...overrides,
  };
}

describe("打造表單", () => {
  it("初值挑第一個有詞條的部位與第一種通用料", () => {
    const draft = initialDraft(crafting());
    expect(draft).toEqual({ slot: "neck", rarity: "rare", affix: "affix_kw_burn_duration", grade: "item_coarse_material", materials: [] });
    expect(draftProblem(draft)).toBeNull();
  });

  it("換部位時換成新部位的詞條；特色材料最多 flavor_max 種", () => {
    const draft = withSlot(initialDraft(crafting()), crafting(), "body");
    expect(draft.affix).toBe("affix_cond_still_defense");
    let picked = toggleMaterial(draft, "b", 2);
    picked = toggleMaterial(picked, "a", 2);
    expect(toggleMaterial(picked, "c", 2).materials).toEqual(["a", "b"]);
    expect(toggleMaterial(picked, "a", 2).materials).toEqual(["b"]);
  });

  it("沒有通用料時說原因；送出的動作帶表單的欄位", () => {
    const empty = initialDraft(crafting({ materials: [] }));
    expect(draftProblem(empty)).toContain("通用料");
    const action = craftAction({ ...initialDraft(crafting()), materials: ["item_mist_crystal"] }, "smithy_mist_ferry");
    expect(action).toMatchObject({ kind: "craft", station: "smithy_mist_ferry", slot_type: "neck", grade: "item_coarse_material", materials: ["item_mist_crystal"] });
  });
});

describe("SmithyPanel", () => {
  const render = (tab: SmithyTab, overrides: Partial<WorldCrafting> = {}) =>
    renderToStaticMarkup(createElement(SmithyPanel, { crafting: crafting(overrides), busy: false, onAct: () => undefined, initialTab: tab }));

  it("分頁：預設是打造表單；四個分頁都在", () => {
    const html = renderToStaticMarkup(createElement(SmithyPanel, { crafting: crafting(), busy: false, onAct: () => undefined }));
    expect(html).toContain("石記鐵鋪（石師傅）");
    expect(html).toContain('data-testid="world-craft-form"');
    for (const id of ["craft", "code", "gear", "enchant"]) expect(html).toContain(`data-testid="world-smithy-tab-${id}"`);
  });

  it("配方碼：輸入框與配方表（首位發現者）；空的輸入不能送", () => {
    const html = render("code");
    expect(html).toContain('data-testid="world-code-input"');
    expect(html).toMatch(/disabled[^>]*data-testid="world-code-submit"/);
    expect(html).toContain("首位發現者 阿霧");
    expect(html).toContain('data-testid="world-recipe-ABCDEF0123"');
    expect(html).toContain("每件裝備只列最新一筆");
  });

  it("強化與分解、附魔台：停用的按鈕保留原因", () => {
    const gearTab = render("gear");
    expect(gearTab).toMatch(/data-testid="world-enhance-item_craft_abc_1"[^>]*disabled|disabled[^>]*data-testid="world-enhance-item_craft_abc_1"/);
    expect(gearTab).toContain('data-testid="world-salvage-item_craft_abc_1"');
    const enchant = render("enchant");
    expect(enchant).toContain('data-testid="world-reroll-item_craft_abc_1-0"');
    expect(enchant).toContain("指定成…");
    expect(enchant).not.toContain("title="); // 說明用共用 Hint
  });

  it("不能用時顯示原因、沒有鐵匠就沒有打造與配方碼分頁", () => {
    const html = render("craft", { can_use: false, problem_zh: "還有沒處理的遭遇", smithy: null });
    expect(html).toContain("還有沒處理的遭遇");
    expect(html).not.toContain('data-testid="world-craft-form"');
    expect(smithyTabs({ smithy: null, enchanter: "x" })).toEqual(["enchant"]);
    expect(smithyTabs({ smithy: "s", enchanter: null })).toEqual(["craft", "code", "gear"]);
  });
});

describe("配方碼輸入", () => {
  it("去空白與連字號、轉大寫；長度與字元檢查", () => {
    expect(normalizeCode(" abcde-f0123 ")).toBe("ABCDEF0123");
    expect(codeProblem("")).toBe("輸入 10 碼的配方碼");
    expect(codeProblem("abc")).toContain("10 碼");
    expect(codeProblem("ABCDEFG123")).toContain("10 碼");
    expect(codeProblem("abcdef0123")).toBeNull();
  });
});
