// 一輪的測試模式（Phase 3-39）的純函式：開局時挑的裝備（欄位 → 物品 ID）、可挑的物品清單、送給伺服器的欄位。
// 測試模式的回滿與挑裝備只存在這一輪的設定裡；不計入任何統計。
import type { CreateRunRequest, GearCatalog } from "../api/types";
import type { Selection } from "../gear/gearDraft";

/** 開局挑裝備只能用內容庫的物品（欄位 → 物品 ID）；自訂物品不收。 */
export function equipmentIds(selection: Selection): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [slot, pick] of Object.entries(selection)) {
    if (pick !== undefined && "item_id" in pick) out[slot] = pick.item_id;
  }
  return out;
}

/** 可挑的物品：主手的武器物品只留起始武器的那一種（一輪不會中途換武器）。 */
export function pickableCatalog(catalog: GearCatalog, weapon: string): GearCatalog {
  return { ...catalog, items: catalog.items.filter((i) => i.slot_type !== "weapon" || i.weapon === weapon) };
}

/** 換武器或換目錄後，把已經不能挑的物品拿掉。 */
export function keepPickable(selection: Selection, catalog: GearCatalog): Selection {
  const ids = new Set(catalog.items.map((i) => i.id));
  const out: Selection = {};
  for (const [slot, pick] of Object.entries(selection)) {
    if (pick !== undefined && "item_id" in pick && ids.has(pick.item_id)) out[slot] = pick;
  }
  return out;
}

/** 開局欄位加上測試模式：沒勾就原樣回傳（正式模式的請求不帶任何測試欄位）。 */
export function withTestMode<T extends Partial<CreateRunRequest>>(
  body: T,
  testMode: boolean,
  selection: Selection,
): T | (T & Pick<CreateRunRequest, "test_mode" | "test_equipment">) {
  if (!testMode) return body;
  return { ...body, test_mode: true, test_equipment: equipmentIds(selection) };
}

/** 一輪畫面上「戰鬥之間」的資源提示：測試模式戰後回滿。 */
export function resourceRuleText(testMode: boolean): string {
  return testMode ? "測試模式：每場戰鬥結束後 HP、法力自動回滿。" : "HP、法力不會在戰鬥之間回復，只有營火會回滿。";
}
