// 手動組裝：預覽圖示跟著武器、玩家文字不露英文代號（Phase 3-48b）。
import { describe, expect, it } from "vitest";
import type { GearCatalog } from "../api/types";
import catalogFx from "./fixtures/catalog.json";
import { affixBlocked, draftLook, emptyDraft, weaponClassZh, weaponOptionText, type CustomDraft } from "./gearDraft";

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
