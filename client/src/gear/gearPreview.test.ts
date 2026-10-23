// 手動組裝：預覽圖示跟著武器、玩家文字不露英文代號（Phase 3-48b）。
import { describe, expect, it } from "vitest";
import type { GearCatalog } from "../api/types";
import catalogFx from "./fixtures/catalog.json";
import { gearIconKey, resolveGear } from "../render/gearIcon";
import { affixBlocked, canPair, draftLook, draftProblems, emptyDraft, isAttrAffix, swapAffix, weaponClassZh, weaponOptionText, type CustomDraft } from "./gearDraft";

const catalog = catalogFx as unknown as GearCatalog;
const ENGLISH = /focus|melee|ranged|shield/;

function draft(patch: Partial<CustomDraft> = {}): CustomDraft {
  return { ...emptyDraft("武器"), ...patch };
}

describe("預覽圖示", () => {
  it("選了武器、外觀是「依欄位預設」：圖示依武器的外觀，換武器就換", () => {
    const staff = draftLook(draft({ weapon: "frost_staff" }), catalog);
    const sword = draftLook(draft({ weapon: "one_handed_sword" }), catalog);
    expect(staff.kind).toBe("staff");
    expect(sword.kind).toBe("sword");
  });

  it("沒選武器才看欄位；明確選了造型就用造型", () => {
    expect(draftLook(draft(), catalog).kind).toBeNull();
    expect(draftLook(draft({ weapon: "frost_staff", kind: "axe" }), catalog).kind).toBe("axe");
    expect(draftLook(draft({ legendary: true }), catalog).rarity).toBe("legendary");
  });
});

describe("玩家文字不露英文代號", () => {
  it("武器下拉是中文", () => {
    for (const w of catalog.weapons) {
      const text = weaponOptionText(w);
      expect(text).not.toMatch(ENGLISH);
      expect(text).toContain(w.weapon_class_zh);
    }
    const staff = catalog.weapons.find((w) => w.id === "frost_staff");
    expect(staff && weaponOptionText(staff)).toBe("冰霜法杖（法器・雙手）");
  });

  it("詞條限武器大類的原因是中文", () => {
    const classOnly = catalog.affixes.find((a) => a.weapon_class != null);
    if (classOnly?.weapon_class == null) return;
    const wrong = catalog.weapons.find((w) => w.weapon_class !== classOnly.weapon_class);
    expect(wrong).toBeDefined();
    const reason = affixBlocked(classOnly, "weapon", draft({ weapon: wrong?.id ?? "" }), catalog) ?? "";
    expect(reason).not.toMatch(ENGLISH);
    expect(reason).toContain(weaponClassZh(catalog, classOnly.weapon_class));
  });
});

describe("元素色與成對／屬性詞條（Phase 3-48g）", () => {
  it("draftLook 帶武器元素；換造型也沿用所選武器的元素", () => {
    expect(draftLook(draft({ weapon: "fire_staff" }), catalog).element).toBe("fire");
    expect(draftLook(draft({ weapon: "frost_staff" }), catalog).element).toBe("ice");
    expect(draftLook(draft({ weapon: "lightning_staff" }), catalog).element).toBe("lightning");
    expect(draftLook(draft({ weapon: "frost_staff", kind: "axe" }), catalog).element).toBe("ice");
    expect(draftLook(draft({ weapon: "one_handed_sword" }), catalog).element).toBeNull();
  });

  it("火焰、冰霜、雷電法杖的圖示快取鍵不同（顏色不同）；不認得的元素不套色", () => {
    const key = (w: string) => gearIconKey(draftLook(draft({ weapon: w }), catalog), 64);
    expect(new Set([key("fire_staff"), key("frost_staff"), key("lightning_staff")]).size).toBe(3);
    expect(resolveGear({ kind: "staff", element: "holy" }).keywords).toEqual([]);
  });

  it("成對勾選只對有成對版本的單手武器；雙手武器勾成對會被擋", () => {
    expect(canPair(catalog, "dagger")).toBe(true);
    expect(canPair(catalog, "one_handed_sword")).toBe(false);
    expect(canPair(catalog, "frost_staff")).toBe(false);
    const problems = draftProblems(draft({ weapon: "frost_staff", paired: true }), "weapon", catalog);
    expect(problems.some((p) => p.includes("雙手武器") && p.includes("成對"))).toBe(true);
  });

  it("屬性詞條換屬性：數值保留", () => {
    const str = catalog.affixes.find((a) => a.id === "affix_attr_str");
    expect(str).toBeTruthy();
    const dex = { ...(str as NonNullable<typeof str>), id: "affix_attr_dex", name_zh: "敏捷 +{n}" };
    const d = draft({ affixes: [{ affix: "affix_attr_str", value: 3 }] });
    expect(swapAffix(d, 0, dex).affixes).toEqual([{ affix: "affix_attr_dex", value: 3 }]);
    expect(isAttrAffix("affix_attr_wil")).toBe(true);
    expect(isAttrAffix("affix_max_hp")).toBe(false);
  });
});
