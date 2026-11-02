// 貨幣、背包、腰包與商店的純函式（Phase 5D-1；docs/phases/Phase5計畫.md 25.6）。
// 規則在後端（能不能買、價格、限量、門檻都由後端算好），這裡只處理文字與腰包的草稿。
import type { WorldAction, WorldInventory, WorldWallet } from "../api/types";

/** 右側角色狀態的一行（「金幣 15・任務幣 2」）；沒有經濟資料時空字串。 */
export function walletLine(wallet: WorldWallet | null | undefined): string {
  if (wallet == null) return "";
  return `金幣 ${wallet.gold}・任務幣 ${wallet.quest_coins}`;
}

/** 腰包的草稿：目前腰包的內容（物品 → 個數）。 */
export function pouchDraft(inventory: WorldInventory): Record<string, number> {
  const draft: Record<string, number> = {};
  for (const item of inventory.pouch) draft[item.item] = item.count;
  return draft;
}

/** 草稿合計幾個。 */
export function draftCount(draft: Readonly<Record<string, number>>): number {
  return Object.values(draft).reduce((sum, n) => sum + n, 0);
}

/**
 * 把草稿裡 `item` 改成 `count` 個：不超過持有數（背包＋腰包）與腰包上限（其他物品已佔的扣掉）；
 * 0 就拿掉。
 */
export function setDraft(
  draft: Readonly<Record<string, number>>,
  inventory: WorldInventory,
  item: string,
  count: number,
): Record<string, number> {
  const owned = inventory.consumables?.find((c) => c.item === item)?.count ?? 0;
  const others = draftCount(draft) - (draft[item] ?? 0);
  const value = Math.max(0, Math.min(count, owned, inventory.pouch_max - others));
  const next: Record<string, number> = { ...draft };
  if (value === 0) delete next[item];
  else next[item] = value;
  return next;
}

/** 送出的 `pouch` 動作（鍵依 ID 排序，方便比對）。 */
export function pouchAction(draft: Readonly<Record<string, number>>): WorldAction {
  const items: Record<string, number> = {};
  for (const key of Object.keys(draft).sort()) items[key] = draft[key] ?? 0;
  return { kind: "pouch", items };
}

/** 草稿和目前腰包一樣（確定鈕停用）。 */
export function samePouch(draft: Readonly<Record<string, number>>, inventory: WorldInventory): boolean {
  const now = pouchDraft(inventory);
  const keys = new Set([...Object.keys(draft), ...Object.keys(now)]);
  for (const key of keys) if ((draft[key] ?? 0) !== (now[key] ?? 0)) return false;
  return true;
}
