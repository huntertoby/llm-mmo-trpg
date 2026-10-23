import { describe, expect, it } from "vitest";
import type { GearCatalog } from "../api/types";
import { equipmentIds, keepPickable, pickableCatalog, withTestMode } from "./testMode";

const item = (id: string, slot_type: string, weapon: string | null = null) => ({ id, slot_type, weapon }) as GearCatalog["items"][number];
const catalog = {
  items: [item("sword", "weapon", "one_handed_sword"), item("bow", "weapon", "bow"), item("armor", "body")],
} as unknown as GearCatalog;

describe("測試模式的裝備", () => {
  it("只收內容庫物品，自訂物品略過", () => {
    const custom = { name: "x", weapon: "", paired: false, shield: false, legendary: false, kind: "", affixes: [] };
    expect(equipmentIds({ body: { item_id: "armor" }, head: { custom } })).toEqual({ body: "armor" });
  });

  it("主手的武器物品只留起始武器那一種", () => {
    expect(pickableCatalog(catalog, "bow").items.map((i) => i.id)).toEqual(["bow", "armor"]);
  });

  it("換武器後拿掉不能再挑的物品", () => {
    const picked = { main_hand: { item_id: "sword" }, body: { item_id: "armor" } };
    expect(keepPickable(picked, pickableCatalog(catalog, "bow"))).toEqual({ body: { item_id: "armor" } });
  });
});

describe("開局請求", () => {
  it("沒勾測試模式：請求原樣，不帶任何測試欄位", () => {
    const body = { weapon: "bow", keywords: ["a", "b"], seed: 1 };
    expect(withTestMode(body, false, { body: { item_id: "armor" } })).toBe(body);
  });

  it("勾了測試模式：帶 test_mode 與挑的裝備；可以不挑", () => {
    const body = { weapon: "bow", keywords: ["a", "b"], seed: 1 };
    expect(withTestMode(body, true, { body: { item_id: "armor" } })).toEqual({ ...body, test_mode: true, test_equipment: { body: "armor" } });
    expect(withTestMode(body, true, {})).toEqual({ ...body, test_mode: true, test_equipment: {} });
  });
});
